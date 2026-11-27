from collections import defaultdict
import json
from pathlib import Path
import re

from pypdf import PdfReader


PDF_PATH = Path("C:/Users/Sanjay/Downloads/YOVAA_India_Bus_Routes_Collected.pdf")
JSON_PATH = Path(__file__).resolve().parent / "route_catalog.json"
JS_PATH = Path(__file__).resolve().parent.parent / "static/js/bus_routes.js"

STATE_ALIASES = {
    "Puducherry": "Puducherry (UT)",
    "Lakshadweep": "Lakshadweep (UT)",
    "Ladakh": "Ladakh (UT)",
    "Jammu & Kashmir": "Jammu and Kashmir (UT)",
    "Delhi (NCT)": "Delhi (UT)",
    "Dadra & Nagar Haveli and Daman & Diu": "Dadra and Nagar Haveli and Daman and Diu (UT)",
    "Chandigarh": "Chandigarh (UT)",
    "Andaman & Nicobar Islands": "Andaman and Nicobar Islands (UT)",
}

DISTRICT_ALIASES = {
    "North & Middle Andaman": "North and Middle Andaman",
}

KNOWN_STATES = set(STATE_ALIASES) | {
    "West Bengal", "Uttarakhand", "Uttar Pradesh", "Tripura", "Telangana",
    "Tamil Nadu", "Sikkim", "Rajasthan", "Punjab", "Odisha", "Nagaland",
    "Mizoram", "Meghalaya", "Manipur", "Maharashtra", "Madhya Pradesh",
    "Kerala", "Karnataka", "Jharkhand", "Himachal Pradesh", "Haryana",
    "Gujarat", "Goa", "Chhattisgarh", "Bihar", "Assam", "Arunachal Pradesh",
    "Andhra Pradesh",
}
HEADERS = {"State / UT", "District", "Bus Route", "Bus Stops Between"}

LEGACY_COIMBATORE_ROUTES = {
    "Singanallur to Gandhipuram": [
        "Singanallur Bus Terminus", "ESI Hospital", "Peelamedu / Hopes College",
        "Nava India", "Lakshmi Mills Junction", "G.P. Hospital / VOC Park",
        "Gandhipuram Town Bus Stand",
    ],
    "Somanur to Gandhipuram": [
        "Somanur Bus Stand", "Karumathampatti", "Kaniyur", "Arasur", "Neelambur",
        "Chinniampalayam", "SITRA", "Goldwins", "Hopes College", "Peelamedu",
        "Nava India", "Lakshmi Mills Junction", "Gandhipuram Town Bus Stand",
    ],
    "Singanallur to Ukkadam": [
        "Singanallur Bus Terminus", "Alamu Nagar / Stock Exchange",
        "Ramanathapuram Junction", "Sungam Junction",
        "Classic Towers / Trichy Road Junction", "Town Hall", "Ukkadam Bus Terminus",
    ],
    "Somanur to Ukkadam": [
        "Somanur Bus Stand", "Karumathampatti",
        "Vagaramalayampalayam / Sultanpet Pirivu", "Sulur Bus Stand",
        "Sulur Aero / Kangayampalayam", "Ondipudur", "Singanallur Bus Terminus",
        "Ramanathapuram Junction", "Sungam Junction", "Ukkadam Bus Terminus",
    ],
    "Karanampettai to Ukkadam": [
        "Karanampettai Junction", "Pallapalayam Pirivu", "Sulur Bus Stand",
        "Sulur Aero / Kangayampalayam", "Ondipudur", "Singanallur Bus Terminus",
        "Ramanathapuram Junction", "Sungam Junction", "Ukkadam Bus Terminus",
    ],
    "Karanampettai to Gandhipuram": [
        "Karanampettai Junction", "Pallapalayam Pirivu", "Sulur Bus Stand",
        "Neelambur Bypass / Chinniampalayam", "SITRA", "Hopes College", "Peelamedu",
        "Lakshmi Mills Junction", "Gandhipuram Town Bus Stand",
    ],
}


def parse_routes():
    lines = [
        line.strip()
        for page in PdfReader(str(PDF_PATH)).pages
        for line in (page.extract_text() or "").splitlines()
        if line.strip()
    ]
    routes = defaultdict(dict)
    index = 0
    while index < len(lines):
        if lines[index] in HEADERS:
            index += 1
            continue
        if lines[index] not in KNOWN_STATES:
            index += 1
            continue

        state = STATE_ALIASES.get(lines[index], lines[index])
        district = DISTRICT_ALIASES.get(lines[index + 1], lines[index + 1])
        route = lines[index + 2]
        index += 3
        stop_lines = []
        while index < len(lines) and lines[index] not in KNOWN_STATES:
            if lines[index] not in HEADERS:
                stop_lines.append(lines[index])
            index += 1
        stops = re.split(r"\s*\u2192\s*", " ".join(stop_lines))
        routes[state].setdefault(district, {})[route] = stops
    routes["Tamil Nadu"].setdefault("Coimbatore", {}).update(LEGACY_COIMBATORE_ROUTES)
    return routes


def main():
    if not PDF_PATH.exists():
        raise SystemExit(f"Route PDF not found: {PDF_PATH}")
    catalog = parse_routes()
    payload = json.dumps(catalog, ensure_ascii=False, indent=2)
    JSON_PATH.write_text(payload + "\n", encoding="utf-8")
    JS_PATH.write_text(
        "window.yovaaRoutes = "
        + json.dumps(catalog, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )
    print(
        f"Imported {sum(len(routes) for districts in catalog.values() for routes in districts.values())} routes "
        f"across {len(catalog)} states/UTs and "
        f"{sum(len(districts) for districts in catalog.values())} districts."
    )


if __name__ == "__main__":
    main()