# mcp-web-sif-monitor

Servidor MCP que monitorea la certificación mensual del **Interés Bancario Corriente (IBC)** publicada por la Superintendencia Financiera de Colombia, y guarda los datos estructurados en una base de datos MySQL.

## ¿Qué hace?

1. Busca en la página de comunicados de la Superfinanciera el documento `.docx` más reciente correspondiente a la modalidad **Crédito de Consumo y Ordinario**.
2. Compara ese documento contra el último registrado en base de datos.
3. Si es nuevo, lo descarga y extrae:
   - Fecha de certificación
   - Fecha de inicio y fin de vigencia
   - Tasa del IBC (efectivo anual)
4. Guarda el registro en MySQL.
5. Si no hay cambios, retorna el último registro guardado (nunca responde vacío).

Diseñado para ejecutarse bajo demanda como una única fuente de verdad que múltiples sistemas externos pueden consultar (`SELECT`) sin necesidad de implementar su propia lógica de scraping.

## Requisitos

- Python 3.10+
- Una base de datos MySQL accesible (probado con [Aiven](https://aiven.io), plan gratuito)

## Instalación

```bash
git clone https://github.com/juandevian/mcp-web-sif-monitor.git
cd mcp-web-sif-monitor
python -m venv venv
source venv/Scripts/activate   # Windows (Git Bash)
# source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
```

## Configuración

Crea un archivo `.env` en la raíz del proyecto con tus credenciales de base de datos:

```env
DB_HOST=tu-host.aivencloud.com
DB_PORT=puerto
DB_USER=tu-usuario
DB_PASSWORD=tu-password
DB_NAME=tu-base-de-datos
```

Crea la tabla en tu base de datos:

```sql
CREATE TABLE ibc_certificaciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    idfile VARCHAR(20) NOT NULL UNIQUE,
    fecha_certificado DATE NOT NULL,
    fecha_desde DATE NOT NULL,
    fecha_hasta DATE NOT NULL,
    ibc DECIMAL(5,2) NOT NULL,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Uso con Claude Code

```bash
claude mcp add ibc-monitor -- "/ruta/a/venv/Scripts/python.exe" "/ruta/a/server.py"
```

Dentro de una sesión de Claude Code:

```
Usa la herramienta revisar_certificacion_ibc
```

## Uso con Claude Desktop

Agrega a `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ibc-monitor": {
      "command": "/ruta/a/venv/Scripts/python.exe",
      "args": ["/ruta/a/server.py"]
    }
  }
}
```

## Flujo de datos

```
Ejecución manual (Claude Code / Claude Desktop)
        │
        ▼
Buscar documento más reciente en Superfinanciera
        │
        ▼
¿Ya está en la base de datos?
   │               │
  Sí              No
   │               │
   ▼               ▼
Retornar      Descargar .docx
último        Extraer 4 campos
registro      Guardar en MySQL
   │               │
   └───────┬───────┘
           ▼
   Respuesta al usuario
           │
           ▼
  Sistemas externos consultan
  la tabla directamente (SELECT)
```

## Estructura del proyecto

```
mcp-web-sif-monitor/
├── config.py       # Configuración y credenciales (vía .env)
├── scraper.py      # Lógica de scraping, parseo y base de datos
├── server.py       # Servidor MCP (expone la herramienta)
├── requirements.txt
└── .env            # Credenciales (no versionado)
```

## Notas técnicas

- El documento más reciente se identifica combinando el `idFile` numérico más alto con la presencia del texto "Crédito de Consumo y Ordinario" en el link — no depende de fechas o nombres de mes hardcodeados.
- Las fechas se parsean desde texto directamente del documento oficial.
- No hay restricción de día de ejecución: el proceso puede llamarse en cualquier momento y siempre refleja el estado más reciente disponible.