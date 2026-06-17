#!/usr/bin/env python3
from pathlib import Path
import gspread
from google.oauth2.service_account import Credentials

SHEET_ID   = '1LEBztjtgGCj0PzpRnpcZezQaM0rmdycHVCHr4aZTjmw'
CREDS_PATH = Path.home() / 'Documents' / '2. Inmobiliaria' / 'zonaprop_scraper' / 'google_credentials.json'
SCOPES     = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

creds = Credentials.from_service_account_file(str(CREDS_PATH), scopes=SCOPES)
gc    = gspread.authorize(creds)
ws    = gc.open_by_key(SHEET_ID).worksheet('Fichas')

headers = ws.row_values(1)
print(f'Conexión OK — {len(headers)} columnas encontradas:')
for i, h in enumerate(headers, 1):
    print(f'  {i:>2}. {h}')
