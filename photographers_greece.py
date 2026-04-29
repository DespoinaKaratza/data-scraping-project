import time
from pathlib import Path

import pandas as pd
import requests

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

OUTPUT_BASENAME = "photographers_greece"

TAGS = [
    ("craft", "photographer"),
    ("shop", "photo"),
    ("shop", "photography"),
]

def build_query() -> str:
    tag_queries = []

    for key, value in TAGS:
        tag_queries.append(f'node["{key}"="{value}"](area.searchArea);')
        tag_queries.append(f'way["{key}"="{value}"](area.searchArea);')
        tag_queries.append(f'relation["{key}"="{value}"](area.searchArea);')

    tag_block = "\n  ".join(tag_queries)

    query = f"""
[out:json][timeout:300];
area["wikidata"="Q41"][boundary=administrative]->.searchArea;
(
  {tag_block}
);
out center tags;
"""
    return query

def fetch_overpass(query: str, max_retries: int = 5) -> dict:
    last_error = None

    for endpoint in OVERPASS_ENDPOINTS:
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    endpoint,
                    data={"data": query},
                    timeout=360,
                )

                if response.status_code in (429, 500, 502, 503, 504):
                    wait = min(20 * (attempt + 1), 90)
                    print(f"[{endpoint}] {response.status_code} — waiting {wait}s...")
                    time.sleep(wait)
                    continue

                if response.status_code == 400:
                    print(response.text[:500])

                response.raise_for_status()
                return response.json()

            except Exception as error:
                last_error = error
                time.sleep(5)

    raise RuntimeError(f"Overpass request failed: {last_error}")

def rows_from_elements(elements):
    rows = []

    for element in elements:
        tags = element.get("tags") or {}

        name = (tags.get("name") or "").strip() or None
        phone = (tags.get("phone") or tags.get("contact:phone") or "").strip() or None
        email = (tags.get("email") or tags.get("contact:email") or "").strip() or None
        website = (tags.get("website") or tags.get("contact:website") or "").strip() or None

        address_parts = [
            tags.get("addr:street"),
            tags.get("addr:housenumber"),
            tags.get("addr:city"),
            tags.get("addr:postcode"),
        ]
        address = ", ".join(part for part in address_parts if part) or None

        lat = element.get("lat") or (element.get("center") or {}).get("lat")
        lon = element.get("lon") or (element.get("center") or {}).get("lon")

        source_tag = None
        if tags.get("craft") == "photographer":
            source_tag = "craft=photographer"
        elif tags.get("shop") == "photo":
            source_tag = "shop=photo"
        elif tags.get("shop") == "photography":
            source_tag = "shop=photography"

        rows.append({
            "name": name,
            "phone": phone,
            "email": email,
            "website": website,
            "address": address,
            "latitude": lat,
            "longitude": lon,
            "source_tag": source_tag,
            "osm_type": element.get("type"),
            "osm_id": element.get("id"),
        })

    return rows

def main():
    print("Searching OSM for photographers in Greece...")

    query = build_query()
    data = fetch_overpass(query)

    elements = data.get("elements", [])
    print(f"Raw OSM elements found: {len(elements)}")

    rows = rows_from_elements(elements)
    df = pd.DataFrame(rows)

    if not df.empty:
        df = df[
            (df["name"].notna())
            | (df["phone"].notna())
            | (df["email"].notna())
            | (df["website"].notna())
        ]

        df = df.drop_duplicates(
            subset=["osm_type", "osm_id"],
            keep="first",
        )

        df = df.drop_duplicates(
            subset=["name", "phone", "website", "latitude", "longitude"],
            keep="first",
        )

    full_csv = OUTPUT_DIR / f"{OUTPUT_BASENAME}.csv"
    full_xlsx = OUTPUT_DIR / f"{OUTPUT_BASENAME}.xlsx"
    sample_xlsx = OUTPUT_DIR / f"sample_{OUTPUT_BASENAME}.xlsx"

    df.to_csv(full_csv, index=False, encoding="utf-8-sig")

    with pd.ExcelWriter(full_xlsx, engine="openpyxl", mode="w") as writer:
        df.to_excel(writer, index=False)

    with pd.ExcelWriter(sample_xlsx, engine="openpyxl", mode="w") as writer:
        df.head(50).to_excel(writer, index=False)

    print("Done.")
    print(f"Clean records: {len(df)}")
    print(f"Full CSV: {full_csv}")
    print(f"Full Excel: {full_xlsx}")
    print(f"Sample Excel: {sample_xlsx}")

if __name__ == "__main__":
    main()