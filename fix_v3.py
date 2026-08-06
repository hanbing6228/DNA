#!/usr/bin/env python3
"""
Emergency fix: apply v3 schema directly to existing database.
Run this if migrate_v2_to_v3.py fails with "no such table".
"""
import sqlite3
import shutil
from pathlib import Path

DB = Path(__file__).parent / "database" / "dna_knowledge.db"
BACKUP = DB.with_suffix('.db.v2_backup')

# Step 1: Restore from backup if available
if BACKUP.exists():
    shutil.copy(BACKUP, DB)
    print(f"[1/5] Restored database from: {BACKUP}")
else:
    print(f"[1/5] No backup found at {BACKUP}, using current DB")

# Step 2: Connect and inspect
conn = sqlite3.connect(str(DB))
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
existing = {row[0] for row in cursor.fetchall()}
print(f"[2/5] Existing tables ({len(existing)}): {sorted(existing)}")

# Step 3: Apply v3 schema
V3_SQL = """
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

conn.executescript(V3_SQL)
conn.commit()
print("[3/5] v3 schema executed")

# Step 4: Verify
cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
after = {row[0] for row in cursor.fetchall()}
new_tables = after - existing
print(f"[4/5] New tables created ({len(new_tables)}): {sorted(new_tables)}")

missing = {'clinvar_snapshots', 'variant_history', 'user_alerts',
           'timeline_events', 'family_members', 'family_risks'} - after
if missing:
    print(f"    ERROR: Still missing tables: {missing}")
    conn.close()
    raise SystemExit(1)

# Step 5: Insert initial snapshot
count = conn.execute("SELECT COUNT(*) FROM variants").fetchone()[0]
cur = conn.execute(
    "INSERT INTO clinvar_snapshots (record_count, version_tag) VALUES (?, ?)",
    (count, "v3.0_initial")
)
conn.commit()
conn.close()
print(f"[5/5] Initial snapshot recorded: {count} variants (snapshot #{cur.lastrowid})")
print("\nDone! Now run: python web_api_v3.py")
