from mcp.server.fastmcp import FastMCP
import asyncio
from scraper import fetch_page_content

mcp = FastMCP("ibc-monitor")

@mcp.tool()
async def revisar_certificacion_ibc() -> str:
    """Monitorea la Superfinanciera y extrae el IBC de consumo/ordinario vigente.
    Compara contra el último registro en la base de datos MySQL (Aiven) y, si hay
    un documento nuevo, lo descarga, extrae los datos y los guarda. Si no hay
    cambios, retorna el último registro guardado."""
    result = await fetch_page_content()
    return str(result)

if __name__ == "__main__":
    mcp.run()
