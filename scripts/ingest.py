import os, sqlite3, time, argparse
import xml.etree.ElementTree as ET
from datetime import datetime
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

BASE = "https://apis.deutschebahn.com/db-api-marketplace/apis/timetables/v1"
HEADERS = {
    "DB-Client-Id": os.environ["DB_CLIENT_ID"],
    "DB-Api-Key": os.environ["DB_API_KEY"],
    "accept": "application/xml",
}
STATIONS = {"8000183": "Ingolstadt Hbf", "8000261": "Muenchen Hbf", "8000284": "Nuernberg Hbf"}
DB_PATH = os.path.join(os.path.dirname(__file__), "delays.sqlite")

def db():
    conn = sqlite3.connect(DB_PATH)
    with open(os.path.join(os.path.dirname(__file__), "..", "references", "schema.sql")) as f:
        conn.executescript(f.read())
    return conn

def parse_ts(raw):
    if not raw:
        return None
    return datetime.strptime(raw, "%y%m%d%H%M").isoformat()

def upsert_stop(conn, eva, s):
    tl = s.find("tl")
    dp, ar = s.find("dp"), s.find("ar")
    row = {
        "stop_id": s.get("id"),
        "station_eva": eva,
        "train_category": tl.get("c") if tl is not None else None,
        "train_number": tl.get("n") if tl is not None else None,
        "line": (dp.get("l") if dp is not None else None) or (ar.get("l") if ar is not None else None),
        "planned_departure": parse_ts(dp.get("pt")) if dp is not None else None,
        "planned_arrival": parse_ts(ar.get("pt")) if ar is not None else None,
        "changed_departure": parse_ts(dp.get("ct")) if dp is not None else None,
        "changed_arrival": parse_ts(ar.get("ct")) if ar is not None else None,
    }
    conn.execute(
        """INSERT INTO stops (stop_id, station_eva, train_category, train_number, line,
               planned_departure, planned_arrival, changed_departure, changed_arrival)
           VALUES (:stop_id,:station_eva,:train_category,:train_number,:line,
               :planned_departure,:planned_arrival,:changed_departure,:changed_arrival)
           ON CONFLICT(stop_id, station_eva) DO UPDATE SET
               changed_departure=COALESCE(excluded.changed_departure, changed_departure),
               changed_arrival=COALESCE(excluded.changed_arrival, changed_arrival),
               last_updated=datetime('now')""",
        row,
    )

def fetch_plan(conn, eva):
    now = datetime.now()
    url = f"{BASE}/plan/{eva}/{now:%y%m%d}/{now:%H}"
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    for s in ET.fromstring(r.content).findall("s"):
        upsert_stop(conn, eva, s)

def fetch_changes(conn, eva):
    r = requests.get(f"{BASE}/fchg/{eva}", headers=HEADERS, timeout=15)
    r.raise_for_status()
    for s in ET.fromstring(r.content).findall("s"):
        upsert_stop(conn, eva, s)

def run_once():
    conn = db()
    for eva in STATIONS:
        try:
            fetch_plan(conn, eva)
            fetch_changes(conn, eva)
            print(f"[{datetime.now():%H:%M}] OK {STATIONS[eva]}")
        except Exception as e:
            print(f"[{datetime.now():%H:%M}] FAIL {STATIONS[eva]}: {e}")
        time.sleep(2)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    if args.once:
        run_once()
    else:
        while True:
            run_once()
            time.sleep(300)
