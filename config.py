import os
from dotenv import load_dotenv

load_dotenv()

INDEX_URL = "https://www.superfinanciera.gov.co/publicaciones/10829/sala-de-prensa/comunicados-de-prensa-interes-bancario-corriente-10829/"

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT"))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")