CREATE TABLE IF NOT EXISTS stops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stop_id TEXT NOT NULL,
    station_eva TEXT NOT NULL,
    train_category TEXT,
    train_number TEXT,
    line TEXT,
    planned_departure TEXT,
    planned_arrival TEXT,
    changed_departure TEXT,
    changed_arrival TEXT,
    planned_platform TEXT,
    changed_platform TEXT,
    is_cancelled INTEGER DEFAULT 0,
    first_seen TEXT DEFAULT (datetime('now')),
    last_updated TEXT DEFAULT (datetime('now')),
    UNIQUE(stop_id, station_eva)
);
CREATE INDEX IF NOT EXISTS idx_stops_station_time
    ON stops(station_eva, planned_departure);
