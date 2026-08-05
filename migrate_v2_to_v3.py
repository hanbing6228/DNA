#!/usr/bin/env python3
"""One-click upgrade: v2.1 -> v3.0"""
import sys
from pathlib import Path
import shutil

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

from database.db import DB_PATH

def migrate():
    # 1. Backup
    backup = DB_PATH.with_suffix('.db.v2_backup')
    if DB_PATH.exists():
        shutil.copy(DB_PATH, backup)
        print(f"Backed up old database: {backup}")

    # 2. Apply v3 schema
    schema_v3 = BASE / "database" / "schema_v3.sql"
    if schema_v3.exists():
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        conn.executescript(schema_v3.read_text())
        conn.close()
        print("v3.0 schema applied")

    # 3. Create initial snapshot
    from database.db import get_conn
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM variants").fetchone()[0]
    from engine.longitudinal_memory import LongitudinalMemory
    snap_id = LongitudinalMemory.record_snapshot(count, version_tag="v3.0_initial")
    print(f"Initial snapshot recorded: {count} variants (snapshot #{snap_id})")

    print("\nUpgrade complete. Restart with: python web_api_v3.py")

if __name__ == "__main__":
    migrate()