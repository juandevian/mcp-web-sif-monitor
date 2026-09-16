import httpx
import re
import mysql.connector
from datetime import datetime
from bs4 import BeautifulSoup
from config import INDEX_URL, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

BASE_URL = "https://www.superfinanciera.gov.co"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MCP-Monitor/1.0)"}

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
}


def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        ssl_disabled=False
    )


def get_last_record():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT idfile, fecha_certificado, fecha_desde, fecha_hasta, ibc "
        "FROM ibc_certificaciones ORDER BY id DESC LIMIT 1"
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row


def save_record(idfile, fecha_certificado, fecha_desde, fecha_hasta, ibc):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO ibc_certificaciones "
        "(idfile, fecha_certificado, fecha_desde, fecha_hasta, ibc) "
        "VALUES (%s, %s, %s, %s, %s)",
        (idfile, fecha_certificado, fecha_desde, fecha_hasta, ibc)
    )
    conn.commit()
    cursor.close()
    conn.close()


async def get_html(url):
    async with httpx.AsyncClient(timeout=20, headers=HEADERS) as client:
        r = await client.get(url, follow_redirects=True)
        r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def extract_latest_docx_link(soup):
    max_id = 0
    best_href = None
    for a in soup.find_all("a", href=True):
        href = a["href"]
        texto = a.get_text(strip=True).lower()
        if "idFile=" in href and "consumo" in texto and "ordinario" in texto:
            match = re.search(r"idFile=(\d+)", href)
            if match:
                file_id = int(match.group(1))
                if file_id > max_id:
                    max_id = file_id
                    best_href = href
    if best_href:
        full_url = BASE_URL + best_href if best_href.startswith("/") else best_href
        return str(max_id), full_url
    return None, None


def parse_fecha_certificado(texto):
    # Ej: "Bogotá, 31 de agosto de 2026."
    match = re.search(r"(\d{1,2}) de (\w+) de (\d{4})", texto, re.IGNORECASE)
    if match:
        dia = int(match.group(1))
        mes_texto = match.group(2).lower()
        anio = int(match.group(3))
        mes = MESES.get(mes_texto)
        if mes:
            return datetime(anio, mes, dia).date()
    return None


def parse_vigencia(texto, fecha_certificado):
    # Ej: "vigencia entre el 1 y el 30 de septiembre de 2026"
    match = re.search(
        r"vigencia entre el (\d{1,2}) y el (\d{1,2}) de (\w+) de (\d{4})",
        texto, re.IGNORECASE
    )
    if match:
        dia_desde = int(match.group(1))
        dia_hasta = int(match.group(2))
        mes_texto = match.group(3).lower()
        anio = int(match.group(4))
        mes = MESES.get(mes_texto)
        if mes:
            fecha_desde = datetime(anio, mes, dia_desde).date()
            fecha_hasta = datetime(anio, mes, dia_hasta).date()
            return fecha_desde, fecha_hasta
    return None, None


async def download_and_parse_docx(url):
    import docx
    import io

    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        r = await client.get(url, follow_redirects=True)
        r.raise_for_status()

    doc = docx.Document(io.BytesIO(r.content))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    fecha_certificado = None
    ibc = None
    fecha_desde = None
    fecha_hasta = None

    for i, para in enumerate(paragraphs):
        if fecha_certificado is None and "bogotá" in para.lower():
            fecha_certificado = parse_fecha_certificado(para)

        if "consumo" in para.lower() and "ordinario" in para.lower():
            if i + 1 < len(paragraphs):
                siguiente = paragraphs[i + 1]
                match_pct = re.search(r"([\d,\.]+)%", siguiente)
                if match_pct:
                    ibc = float(match_pct.group(1).replace(",", "."))
                fecha_desde, fecha_hasta = parse_vigencia(siguiente, fecha_certificado)
            break

    return {
        "fecha_certificado": fecha_certificado,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "ibc": ibc
    }


async def fetch_page_content():
    soup = await get_html(INDEX_URL)
    file_id, docx_url = extract_latest_docx_link(soup)

    if not file_id:
        return {"ok": False, "msg": "No se encontró link de descarga."}

    ultimo = get_last_record()

    if ultimo and ultimo["idfile"] == file_id:
        return {
            "ok": True,
            "cambio": False,
            "msg": "Sin cambios. Se retorna el último registro guardado.",
            "idfile": ultimo["idfile"],
            "fecha_certificado": str(ultimo["fecha_certificado"]),
            "fecha_desde": str(ultimo["fecha_desde"]),
            "fecha_hasta": str(ultimo["fecha_hasta"]),
            "ibc": float(ultimo["ibc"])
        }

    datos = await download_and_parse_docx(docx_url)

    if not datos["ibc"] or not datos["fecha_certificado"]:
        return {"ok": False, "msg": "No se pudo extraer la información del documento."}

    save_record(
        file_id,
        datos["fecha_certificado"],
        datos["fecha_desde"],
        datos["fecha_hasta"],
        datos["ibc"]
    )

    return {
        "ok": True,
        "cambio": True,
        "idfile": file_id,
        "fecha_certificado": str(datos["fecha_certificado"]),
        "fecha_desde": str(datos["fecha_desde"]),
        "fecha_hasta": str(datos["fecha_hasta"]),
        "ibc": datos["ibc"]
    }
