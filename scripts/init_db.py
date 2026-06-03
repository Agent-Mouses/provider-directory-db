"""Create the provider directory database schema."""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'provider_directory.db')

SCHEMA = """
CREATE TABLE IF NOT EXISTS payers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_tin TEXT,
    org_name TEXT NOT NULL,
    note TEXT,
    plan_name TEXT,
    portal_url TEXT,
    api_base TEXT,
    endpoint_insurance_plan TEXT,
    endpoint_practitioner TEXT,
    endpoint_practitioner_role TEXT,
    endpoint_organization TEXT,
    endpoint_organization_affiliation TEXT,
    endpoint_location TEXT,
    endpoint_healthcare_service TEXT,
    endpoint_network TEXT,
    endpoint_endpoint TEXT,
    requires_registration INTEGER DEFAULT 0,
    requires_api_key INTEGER DEFAULT 0,
    auth_type TEXT,
    last_validated TEXT,
    last_validated_status TEXT,
    fhir_version TEXT,
    source TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(org_name, plan_name)
);

CREATE TABLE IF NOT EXISTS validation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payer_id INTEGER NOT NULL,
    endpoint_url TEXT NOT NULL,
    status_code INTEGER,
    response_time_ms INTEGER,
    fhir_version TEXT,
    is_valid INTEGER,
    error TEXT,
    checked_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (payer_id) REFERENCES payers(id)
);
"""

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print(f"Database created at {os.path.abspath(DB_PATH)}")

if __name__ == '__main__':
    init_db()
