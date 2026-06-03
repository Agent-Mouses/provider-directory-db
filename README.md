# Provider Directory API Database

A SQLite database tracking **all CMS-regulated payer Provider Directory FHIR API endpoints** — their availability, compliance status, and verification results.

> **Read [AGENTS.md](AGENTS.md) before making changes.**

## Overview

The CMS Interoperability and Patient Access Final Rule (CMS-9115-F) requires Medicare Advantage organizations, Medicaid programs, and CHIP plans to publish Provider Directory APIs using FHIR R4. This repo collects, validates, and monitors those endpoints across the entire regulated universe.

## Database

`data/provider_directory.db` — SQLite

**533 records | 408 unique organizations | 100% validated**

## Coverage

| Category | Count |
|----------|-------|
| State Medicaid FFS programs | 51 (all 50 + DC) |
| Medicare Advantage organizations | 174 |
| Medicaid MCOs (national + regional) | ~200 |
| CHIP programs | 15 |
| Federal (CMS, VA) | 2 |

## Compliance Status

| Status | Count | % |
|--------|-------|---|
| ✅ Compliant (open access) | 69 | 13% |
| ✅ Compliant (with registration) | 395 | 74% |
| ⚠️ Non-compliant | 68 | 13% |
| ❓ Unknown | 1 | <1% |

## Validation Results (all 533 probed)

| Status | Count | Meaning |
|--------|-------|---------|
| `cms_sma_confirmed` | 41 | Official CMS directory says Active |
| `valid` | 6 | CapabilityStatement returned (open access) |
| `exists_needs_auth` | 268 | Server responds 401/403 |
| `unreachable_from_probe` | 126 | IP-restricted |
| `not_found` | 46 | URL may have changed |
| `no_endpoint_to_test` | 28 | No API published |
| `error`/`timeout` | 18 | Server issues |

## Violations Tracked

| Violation | Count | Meaning |
|-----------|-------|---------|
| `MISSING_CRITICAL_DATA` | 39 | API exists but missing required data |
| `NO_API` | 13 | No API published at all |
| `REGISTRATION_BLOCKS_ACCESS` | 8 | Registration broken/blocked |
| `NOT_QUERYABLE` | 5 | Search parameters missing |
| `NOT_MACHINE_READABLE` | 3 | Web HTML only, no FHIR API |

## Usage

```bash
pip install -r requirements.txt

# Initialize database (first time)
python scripts/init_db.py

# Import Defacto 2024 data
python scripts/import_defacto.py

# Validate all endpoints
python scripts/validate_endpoints.py

# Deep discovery (background)
nohup python scripts/discover_all.py > data/discovery.log 2>&1 &
```

## Query Examples

```python
import sqlite3
conn = sqlite3.connect('data/provider_directory.db')

# All verified live endpoints
conn.execute("SELECT org_name, api_base FROM payers WHERE last_validated_status='valid'")

# Non-compliant payers
conn.execute("SELECT org_name, violation_type, violation_detail FROM payers WHERE compliance_flag='NON_COMPLIANT'")

# All state Medicaid APIs
conn.execute("SELECT org_name, api_base, last_validated_status FROM payers WHERE source='cms_sma_directory'")
```

## Data Sources

See [SOURCES.md](SOURCES.md) for full citations.

1. **CMS SMA Endpoint Directory** (official) — State Medicaid FHIR API URLs
2. **CMS MA Plan Directory 2026-05** (official) — All MA organizations
3. **Defacto Health 2024** — Top 137 payers with compliance scores
4. **CMS Universe Expansion** — MCOs, CHIP, supplementary state data
5. **Automated Discovery** — FHIR /metadata probing and validation

## Regulatory Reference

| CFR | Applies to |
|-----|-----------|
| 42 CFR § 422.120 | Medicare Advantage |
| 42 CFR § 431.70 | Medicaid FFS |
| 42 CFR § 438.242(b)(6) | Medicaid managed care |
| 42 CFR § 457.760 | CHIP FFS |
| 42 CFR § 457.1233(d) | CHIP managed care |

## Technical Standard

- HL7 FHIR R4 (Release 4.0.1)
- HL7 US Core IG STU 6.1.0
- HL7 Da Vinci PDex Plan Net IG STU 1.2.0
