# Data Scraping Project

This project demonstrates data extraction using Python from both web pages and APIs.

##  Projects

### 1. Photographers OSM Scraper (Main Project)
Scrapes real-world photographer data across Greece using the OpenStreetMap Overpass API.

**Features:**
- Fetches data via API (no manual input required)
- Extracts names, phones, emails, websites, and coordinates
- Cleans and deduplicates data
- Exports results to CSV and Excel

### 2. Demo Web Scraper
Simple example of scraping structured data from a website using HTML parsing.

---

##  Output

Sample outputs are included in the `output/` folder:
- `main_output.xlsx` → photographers data from OSM
- `demo_output.xlsx` → demo scraper output

---

##  Technologies

- Python
- requests (API calls)
- BeautifulSoup (HTML scraping)
- pandas (data processing)

---

##  How to run

Install dependencies:

```bash
pip install -r requirements.txt
