import gspread
from google.oauth2.service_account import Credentials
import re

scopes = ['https://www.googleapis.com/auth/spreadsheets']

creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
client = gspread.authorize(creds)

url = 'https://docs.google.com/spreadsheets/d/1Dxn1vYr6Ey3ZzGz4M0XsCUJMDcr7u2UiCvC5eEE3pzc/edit#gid=480225743'
text_blob = (re.split('spreadsheets/d/', url)[1])
sheet_id = re.split('/edit', text_blob)[0]

sheet = client.open_by_key(sheet_id)

values_list = sheet.sheet1.row_values(1)
print(values_list)