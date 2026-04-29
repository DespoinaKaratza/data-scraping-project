import requests
import pandas as pd
from bs4 import BeautifulSoup

url = "https://www.scrapethissite.com/pages/simple/"
response = requests.get(url, timeout=30)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")

rows = []
for country in soup.select(".country"):
    rows.append({
        "country": country.select_one(".country-name").get_text(strip=True),
        "capital": country.select_one(".country-capital").get_text(strip=True),
        "population": country.select_one(".country-population").get_text(strip=True),
        "area_km2": country.select_one(".country-area").get_text(strip=True),
    })

df = pd.DataFrame(rows)
df.to_csv("countries_demo_output.csv", index=False, encoding="utf-8-sig")
df.to_excel("countries_demo_output.xlsx", index=False)

print("OK -> countries_demo_output.csv + countries_demo_output.xlsx")
print("Rows:", len(df))