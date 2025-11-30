import pandas as pd
import requests
from io import StringIO

url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
headers = {'User-Agent': 'Mozilla/5.0'}
response = requests.get(url, headers=headers)
tables = pd.read_html(StringIO(response.text))

print(f"Found {len(tables)} tables\n")

for i, table in enumerate(tables):
    print(f"Table {i}: shape={table.shape}, columns={table.columns.tolist()[:5]}")
    if table.shape[0] > 400:  # S&P 500 should have ~500 rows
        print(f"  -> This looks like the S&P 500 table!")
        print(f"  First 3 tickers: {table.iloc[:3, 0].tolist()}")
