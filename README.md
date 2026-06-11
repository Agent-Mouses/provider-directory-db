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

We tested every payer in two steps:

### Step 1: Does the server exist?

We sent an HTTP request to each payer's published API address.

| Result | Count | Meaning |
|--------|:-----:|---------|
| ✅ Yes, server responds | 533 (98.7%) | The URL is real and the server is running |
| ❌ No server found | 7 (1.3%) | No working URL exists (US territories + defunct plans) |

### Step 2: Can you actually get provider data?

For the 533 that responded, we tried to query real provider records.

| Result | Count | Meaning |
|--------|:-----:|---------|
| ✅ Real data returned | 11 (2%) | We received real doctor names/NPIs and verified them against the national registry |
| 🔒 Blocked — login required | 516 (96%) | Server is there but demands OAuth credentials before showing any data |
| ⚠️ Server errors or empty | 6 (1%) | Server broke (4) or returned nothing (2 — New Jersey) |

**Bottom line:** 98.7% of payers technically have a server running. But only **2% actually let you see provider data without registering for credentials first.** The other 96% put real data behind an authentication wall.

### What authentication methods are payers using?

CMS rule (85 FR 25543) says Provider Directory APIs **must be publicly accessible without requiring user authentication**. App-level registration (e.g., registering as a developer to get a client ID) is permitted — but individual user login is not.

| Auth Method | Count | CMS Compliant? | What It Means |
|-------------|:-----:|:--------------:|---------------|
| Open (no auth) | 46 | ✅ Yes | Anyone can query immediately |
| API Key | 52 | ✅ Yes | Register app, get key, query freely |
| OAuth2 Client Credentials | 403 | ✅ Yes | Register app, get client_id/secret, no user login |
| OAuth2/SMART on FHIR | 21 | ❌ No | Requires individual user login — designed for patient access, not public directory |
| None (no data served) | 12 | ⚠️ Unclear | Server responds but no data accessible |
| N/A (no API) | 6 | ❌ Non-compliant | No endpoint exists |

**Summary:**
- **501 payers (93%)** use CMS-allowed auth (open + API key + client credentials)
- **21 payers (4%)** use SMART on FHIR — **likely non-compliant** for Provider Directory (user-level auth)
- **18 payers (3%)** have no functional access

**The real issue isn't auth type — it's friction.** Even with CMS-compliant OAuth2 Client Credentials, developers must:
1. Find the payer's developer portal
2. Register an application (often requires manual approval)
3. Wait for credentials (hours to weeks)
4. Implement OAuth2 token flow

This is technically allowed by CMS but creates a massive barrier compared to the 46 payers where you can query immediately with zero setup.

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

For the complete data dictionary with all 41 columns, see **[SCHEMA.md](SCHEMA.md)**.

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

Our database covers four types of CMS-regulated payers. Each type has a **listing source** (how we know the payer exists and must comply) and an **API source** (how we found their FHIR endpoint URL).

### By Payer Type

| Payer Type | Count | Listing Source (who must comply) | API Endpoint Source (where's their FHIR URL) |
|------------|:-----:|----------------------------------|----------------------------------------------|
| **Medicare Advantage** | 152 | CMS MA Plan Directory PUF (primary) — [cms.gov](https://www.cms.gov/data-research/statistics-trends-and-reports/medicare-advantagepart-d-contract-and-enrollment-data/ma-plan-directory) | Availity platform discovery + DeFACTO 2024 |
| **Medicaid MCO** | 194 | CMS Managed Care Enrollment Report — [data.medicaid.gov](https://data.medicaid.gov) | Edifecs/Availity/Conduent platform discovery |
| **CHIP** | 15 | CMS Universe (42 CFR § 457.1233) | Same as Medicaid (often shared infrastructure) |
| **Dual (MA + Medicaid)** | 55 | Both CMS MA Directory + Medicaid enrollment data | DeFACTO 2024 + platform discovery |
| **State Medicaid FFS** | ~50 | CMS SMA Endpoint Directory (official) — [GitHub](https://cmsgov.github.io/SMA-Endpoint-Directory/) | CMS SMA Directory provides URLs directly |
| **Other** | ~74 | DeFACTO Health 2024 research | DeFACTO 2024 + manual verification |

### Primary Sources Explained

| Source | What It Is | Authority Level |
|--------|------------|:---------------:|
| [CMS MA Plan Directory](https://www.cms.gov/files/zip/ma-plan-directory.zip) | Official list of all MA/Cost/PACE/Demo contracts (923 contracts, 312 parent orgs) — updated monthly | 🏛️ Official CMS |
| [CMS SMA Endpoint Directory](https://cmsgov.github.io/SMA-Endpoint-Directory/) | Official state Medicaid FHIR endpoints with URLs, auth info, FHIR versions | 🏛️ Official CMS |
| [CMS Managed Care Enrollment](https://data.medicaid.gov) | All Medicaid MCO contracts with enrollment counts | 🏛️ Official CMS |
| [DeFACTO Health 2024](https://defacto.health/2024/06/24/state-of-provider-directory-apis-2024/) | Industry research testing top 137 payer APIs | 📊 Industry Research |
| Availity/Edifecs/Conduent Discovery | Platform-level endpoint verification (2026-06-11) | 🔬 Our verification |

### Why the listing source matters

The **listing source** establishes legal obligation. If a payer appears in the CMS MA Plan Directory, they are **legally required** by 42 CFR § 422.120 to publish a Provider Directory API. Our database documents whether they are meeting that obligation.

See [SOURCES.md](SOURCES.md) for full citations and methodology.

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
