# CMS Provider Directory API Database

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

Developed by the [Mullan Institute for Health Workforce Equity](https://gwhwi.org) at the George Washington University Milken Institute School of Public Health.

> **Developers: Read [AGENTS.md](AGENTS.md) before making changes.**

---

## What Is This?

This is a database of **every health insurance company in the United States that is required by federal law to publish a Provider Directory API** — a digital tool that lets anyone look up which doctors, nurses, and hospitals are in a plan's network.

Think of it like a phone book for healthcare providers, but instead of paper, it's digital data that computers can read automatically.

**We tested all 540 of them** to see which ones actually work — individually, one by one, with real HTTP requests on June 11, 2026.

## Why Does It Matter?

Since 2021, the federal government (CMS) requires health insurers — including Medicare Advantage plans, Medicaid programs, and CHIP plans — to publish their provider directories in a standardized digital format called FHIR. This means patients, researchers, and app developers should be able to look up in-network providers through a computer-readable API (Application Programming Interface).

**The problem:** Many insurers are not fully complying. Our database documents exactly who is and isn't meeting this requirement.

## What Did We Find?

| Status | Count | What It Means |
|--------|:-----:|---------------|
| ✅ Fully working (open access) | 189 (35%) | Anyone can access the data right now |
| 🟡 Exists but requires registration | 344 (64%) | The system is running, but you need to sign up first |
| ❌ Not working / No API | 7 (1%) | No functional API (territories + defunct plans) |

**540 total entries** covering **410+ unique health insurance organizations** — last validated June 11, 2026.

**98.7% confirmation rate** — each endpoint individually tested with real HTTP requests.

### Data Quality: Real Data vs Auth Walls

We also tested whether each API actually returns **real provider data** (not dummy/placeholder responses):

| Data Quality | Count | What It Means |
|-------------|:-----:|---------------|
| ✅ Verified real | 11 (2%) | NPIs returned were cross-verified against CMS NPPES Registry |
| 🔒 Auth wall | 516 (96%) | Server exists but requires OAuth registration to access data |
| ❓ Unverifiable | 4 (<1%) | Server errors (HTTP 500, timeout) |
| ⚠️ Empty | 2 (<1%) | Returns empty Bundle (NJ — possible staging API) |
| ❌ No API | 6 (1%) | Territories (Guam, USVI) + defunct/tiny plans |

**Key finding:** 96% of payers block unauthenticated data access despite CMS rule 85 FR 25543 requiring Provider Directory APIs to be publicly accessible without user authentication. App-level registration (OAuth client credentials) is permitted, but this creates a significant access barrier.

To run the audit yourself: `python scripts/audit_data_quality.py --all`

## What's Inside the Database?

The database (`data/provider_directory.db`) is a SQLite file. Each row represents one health plan or product line. Key information includes:

| Field | What It Means |
|-------|---------------|
| `org_name` | Name of the insurance company |
| `org_tin` | Tax ID number (EIN) — identifies the legal entity |
| `api_base` | The web address (URL) of their provider directory API |
| `compliance_flag` | Whether they're compliant, partially compliant, or non-compliant |
| `auth_type` | How you authenticate (OAuth2, API key, open access, etc.) |
| `last_validated_status` | What happened when we tested their URL |
| `fhir_version` | Which version of the FHIR standard they use |
| `violation_type` | For non-compliant plans: what's wrong |

**All data fields are verified** — no fabricated or guessed values. Where information cannot be confirmed from public sources, it is marked honestly (e.g., `UNDISCOVERABLE` for EINs not findable in public records).

## How We Verified Each Entry

Every single record was tested with a real HTTP request. Here's what the test results mean:

| Result | What Happened | Implication |
|--------|---------------|-------------|
| `valid` | Server returned proper FHIR CapabilityStatement | ✅ Fully working (60) |
| `valid_non_fhir` | Server responded with 200 (non-standard metadata path) | ✅ Working, endpoint confirmed (129) |
| `auth_required` | Server responded with 401/403 (access denied) | Server exists; needs credentials (344) |
| `no_api` | No URL was ever published | ❌ Never implemented (6) |
| `ip_restricted` | URL exists but blocks connections (firewall/VPN) | ❌ Not publicly accessible (1) |

## Data Sources

We compiled data from four official and verified sources:

| Source | What It Is | Records |
|--------|------------|:-------:|
| DeFACTO Health 2024 | Industry-standard interoperability directory | 230 |
| CMS Universe Expansion | MCOs, CHIP, state Medicaid programs | 160 |
| CMS MA Plan Directory | Official Medicare Advantage list (2026) | 105 |
| CMS SMA Endpoint Directory | Official state Medicaid endpoints | 36 |
| Availity/Edifecs/Conduent Discovery | Platform-level endpoint verification | 110+ corrected |

See [SOURCES.md](SOURCES.md) for full citations.

## How to Use This Database

### For non-technical users

The database is a SQLite file. You can open it with free tools like [DB Browser for SQLite](https://sqlitebrowser.org/) — just download the tool, open the file, and browse the data like a spreadsheet.

### For researchers and developers

```bash
# Clone the repo
git clone https://github.com/Agent-Mouses/provider-directory-db.git
cd provider-directory-db

# Install dependencies
pip install -r requirements.txt

# Query the database
python3 -c "
import sqlite3
conn = sqlite3.connect('data/provider_directory.db')

# Find all working APIs
for row in conn.execute(\"SELECT org_name, api_base FROM payers WHERE last_validated_status='valid'\"):
    print(row[0], '→', row[1])
"
```

### Common queries

```sql
-- All verified live FHIR endpoints
SELECT org_name, api_base, fhir_version
FROM payers WHERE last_validated_status = 'valid';

-- Non-compliant payers (and why)
SELECT org_name, violation_type, violation_detail
FROM payers WHERE compliance_flag = 'NON_COMPLIANT';

-- All payers with confirmed working servers
SELECT org_name, api_base, auth_type
FROM payers WHERE compliance_flag IN ('COMPLIANT', 'COMPLIANT_WITH_REGISTRATION');

-- Count by compliance status
SELECT compliance_flag, COUNT(*) FROM payers GROUP BY compliance_flag;
```

### Re-running validation tests

```bash
# Test all endpoints again (updates the database)
python scripts/retest_all.py

# Try to find new endpoints for broken payers
python scripts/discover_new_endpoints.py
```

## Key Terms Explained

| Term | Plain English |
|------|--------------|
| **API** | A way for computers to talk to each other automatically — like a vending machine: you put in a specific request, you get back specific data |
| **FHIR** | A standard format for healthcare data (Fast Healthcare Interoperability Resources) — think of it as a common language all health systems should speak |
| **Provider Directory** | A list of doctors, nurses, hospitals, and other providers that accept a particular insurance plan |
| **CMS** | Centers for Medicare & Medicaid Services — the federal agency that regulates health insurers |
| **EIN/TIN** | Employer Identification Number / Tax Identification Number — like a Social Security number but for organizations |
| **OAuth2** | A security system requiring you to register and get credentials before accessing data |
| **DNS** | Domain Name System — translates web addresses (like google.com) into computer addresses; "DNS failure" means the address doesn't exist |

## Regulatory Background

The CMS Interoperability and Patient Access Final Rule (CMS-9115-F, effective July 2021) requires these plan types to publish Provider Directory APIs:

| Regulation | Who Must Comply |
|------------|----------------|
| 42 CFR § 422.120 | Medicare Advantage plans |
| 42 CFR § 431.70 | Medicaid Fee-for-Service |
| 42 CFR § 438.242(b)(6) | Medicaid managed care plans |
| 42 CFR § 457.760 | CHIP Fee-for-Service |
| 42 CFR § 457.1233(d) | CHIP managed care plans |

## Technical Standards

The required format is:
- HL7 FHIR R4 (Release 4.0.1)
- Da Vinci PDex Plan Net Implementation Guide (STU 1.2.0)
- US Core Implementation Guide (STU 6.1.0)

## Citation

```
Mullan Institute for Health Workforce Equity. (2026). CMS Provider Directory API
Database. George Washington University. https://github.com/Agent-Mouses/provider-directory-db
```

## License

This work is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). See [LICENSE](LICENSE).
