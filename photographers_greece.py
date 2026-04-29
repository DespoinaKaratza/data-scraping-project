import time
import requests
import pandas as pd

# Δοκιμάζουμε 2 Overpass endpoints (αν ένα ζορίζεται)
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

AREA_NAME = "Greece"         # όλη η χώρα
OUTPUT_BASENAME = "photographers_greece"

# Θέλουμε και craft=photographer ΚΑΙ shop=photo
TAGS = [("craft", "photographer"), ("shop", "photo")]

def build_query(area_name: str) -> str:
    """
    ΣΩΣΤΟ OverpassQL:
    - ΟΡΙΖΕΙ area ...
    - ΚΑΙ μετά κάνει ξεχωριστές εντολές για node/way/relation ανά tag,
      ΟΧΙ αλυσίδες στον ίδιο selector (εκεί ήταν το συντακτικό λάθος).
    """
    node_parts = "\n  ".join([f'node["{k}"="{v}"](area.searchArea);' for k, v in TAGS])
    way_parts  = "\n  ".join([f'way["{k}"="{v}"](area.searchArea);'  for k, v in TAGS])
    rel_parts  = "\n  ".join([f'relation["{k}"="{v}"](area.searchArea);' for k, v in TAGS])

    q = f"""
[out:json][timeout:300];
area[name="{area_name}"][boundary=administrative][admin_level=2]->.searchArea;
(
  {node_parts}
  {way_parts}
  {rel_parts}
);
out center tags;
"""
    return q

def fetch_overpass(query: str, max_retries: int = 5) -> dict:
    last_err = None
    for endpoint in OVERPASS_ENDPOINTS:
        for attempt in range(max_retries):
            try:
                r = requests.post(endpoint, data={"data": query}, timeout=360)
                if r.status_code in (429, 504) or r.status_code >= 500:
                    wait = min(20 * (attempt + 1), 90)
                    print(f"[{endpoint}] {r.status_code} — περιμένω {wait}s και ξαναδοκιμάζω…")
                    time.sleep(wait)
                    continue
                if r.status_code == 400:
                    # Εκτύπωσε και το σώμα για debugging αν πάει κάτι στραβά
                    print(f"[{endpoint}] 400 Bad Request\n{r.text[:500]}")
                    r.raise_for_status()
                r.raise_for_status()
                return r.json()
            except Exception as e:
                last_err = e
        # αν εξαντλήσαμε τα retries για το συγκεκριμένο endpoint, πάμε στο επόμενο
    raise RuntimeError(f"Overpass απέτυχε: {last_err}")

def rows_from_elements(elements, area_label):
    rows = []
    for el in elements:
        tags = el.get("tags") or {}

        name = (tags.get("name") or "").strip() or None
        phone = (tags.get("phone") or tags.get("contact:phone") or "").strip() or None
        email = (tags.get("email") or tags.get("contact:email") or "").strip() or None
        website = (tags.get("website") or tags.get("contact:website") or "").strip() or None

        street = tags.get("addr:street")
        housenumber = tags.get("addr:housenumber")
        city = tags.get("addr:city")
        postcode = tags.get("addr:postcode")
        address = ", ".join(x for x in [street, housenumber, city, postcode] if x)

        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")

        # Κρατάμε και την πηγή tag (craft=photographer/shop=photo) για πληροφόρηση
        src = None
        if tags.get("craft") == "photographer":
            src = "craft=photographer"
        elif tags.get("shop") == "photo":
            src = "shop=photo"

        rows.append({
            "name": name,
            "phone": phone,
            "email": email,
            "website": website,
            "address": address if address else None,
            "lat": lat,
            "lon": lon,
            "source_tag": src,
            "osm_type": el.get("type"),
            "osm_id": el.get("id"),
            "area": area_label,
        })
    return rows

def main():
    print(f"Αναζήτηση στο OSM για φωτογράφους: {AREA_NAME} …")
    query = build_query(AREA_NAME)
    data = fetch_overpass(query)
    elems = data.get("elements", [])
    print(f"Βρέθηκαν {len(elems)} στοιχεία. Εξαγωγή…")

    rows = rows_from_elements(elems, AREA_NAME)

    df = pd.DataFrame(rows)
    if not df.empty:
        # Ελάχιστο καθάρισμα + διπλότυπα
        df = df[(df["name"].notna()) | (df["phone"].notna()) | (df["email"].notna()) | (df["website"].notna())]
        df = df.drop_duplicates(subset=["name", "address", "phone", "lat", "lon"], keep="first")

    # Αποθήκευση σε CSV + XLSX (overwrite καθαρά)
    csv_path = f"{OUTPUT_BASENAME}.csv"
    xlsx_path = f"{OUTPUT_BASENAME}.xlsx"

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    with pd.ExcelWriter(xlsx_path, engine="openpyxl", mode="w") as writer:
        df.to_excel(writer, index=False)

    print(f"OK -> {csv_path}  +  {xlsx_path}")
    print(f"Σύνολο εγγραφών: {len(df)}")

if __name__ == "__main__":
    main()
