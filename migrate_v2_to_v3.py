#!/usr/bin/env python3
"""One-click upgrade: v2.1 -> v3.0"""
import sys
from pathlib import Path
import shutil
import sqlite3

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

from database.db import DB_PATH

V3_SCHEMA = """
CREATE TABLE IF NOT EXISTS clinvar_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    record_count INTEGER,
    version_tag TEXT
);

CREATE TABLE IF NOT EXISTS variant_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id INTEGER NOT NULL,
    snapshot_id INTEGER,
    clinvar_significance TEXT,
    clinvar_review_status TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    change_type TEXT,
    previous_significance TEXT,
    FOREIGN KEY (variant_id) REFERENCES variants(id),
    FOREIGN KEY (snapshot_id) REFERENCES clinvar_snapshots(id)
);

CREATE TABLE IF NOT EXISTS user_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_name TEXT NOT NULL,
    variant_id INTEGER,
    alert_type TEXT,
    title TEXT,
    message TEXT,
    severity TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (variant_id) REFERENCES variants(id)
);

CREATE TABLE IF NOT EXISTS timeline_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_name TEXT NOT NULL,
    event_date TEXT NOT NULL,
    event_type TEXT,
    source TEXT,
    title TEXT,
    description TEXT,
    data_json TEXT,
    related_variant_id INTEGER,
    FOREIGN KEY (related_variant_id) REFERENCES variants(id)
);

CREATE TABLE IF NOT EXISTS family_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proband_sample TEXT NOT NULL,
    relation TEXT NOT NULL,
    name TEXT,
    sex TEXT,
    affected INTEGER DEFAULT 0,
    conditions TEXT,
    has_genome INTEGER DEFAULT 0,
    sample_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS family_risks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proband_sample TEXT NOT NULL,
    family_member_id INTEGER,
    gene_symbol TEXT,
    variant_id INTEGER,
    risk_type TEXT,
    probability REAL,
    recommendation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (variant_id) REFERENCES variants(id),
    FOREIGN KEY (family_member_id) REFERENCES family_members(id)
);

CREATE TABLE IF NOT EXISTS user_medications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_name TEXT NOT NULL,
    drug_name TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    dosage TEXT,
    frequency TEXT,
    prescribed_by TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lab_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_name TEXT NOT NULL,
    test_date TEXT NOT NULL,
    test_name TEXT NOT NULL,
    value REAL,
    unit TEXT,
    reference_range TEXT,
    is_abnormal INTEGER DEFAULT 0,
    source_file TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def migrate():
    # 1. Backup
    backup = DB_PATH.with_suffix('.db.v2_backup')
    if DB_PATH.exists():
        shutil.copy(DB_PATH, backup)
        print(f"Backed up old database: {backup}")

    # 2. Apply the canonical v3 schema.  Keeping this in one file prevents
    # future schema changes from drifting from the application startup path.
    print("Applying v3.0 schema...")
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript((BASE / "database" / "schema_v3.sql").read_text(encoding="utf-8"))
    conn.commit()

    # Verify tables were created
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    required = {'clinvar_snapshots', 'variant_history', 'user_alerts',
                'timeline_events', 'family_members', 'family_risks'}
    missing = required - tables
    if missing:
        conn.close()
        raise RuntimeError(f"Schema application failed. Missing tables: {missing}")
    conn.close()
    print("v3.0 schema applied successfully")

    # 3. Create initial snapshot
    from database.db import get_conn
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM variants").fetchone()[0]

    from engine.longitudinal_memory import LongitudinalMemory
    snap_id = LongitudinalMemory.record_snapshot(count, version_tag="v3.0_initial")
    print(f"Initial snapshot recorded: {count} variants (snapshot #{snap_id})")

    print("\nUpgrade complete. Start the server with:")
    print("  python web_api_v3.py")


if __name__ == "__main__":
    migrate()
