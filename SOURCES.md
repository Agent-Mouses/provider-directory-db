# Data Sources

Compiled by the Mullan Institute for Health Workforce Equity, George Washington University.

All payer records in this database are sourced from verified, authoritative references. Each record includes `source`, `source_detail`, `source_url`, and `source_date` fields.

---

## 1. CMS State Medicaid Agency (SMA) Endpoint Directory (Official)

| Field | Value |
|-------|-------|
| Records | 36 |
| Source key | `cms_sma_directory` |
| URL | https://cmsgov.github.io/SMA-Endpoint-Directory/ |
| GitHub | https://github.com/CMSgov/SMA-Endpoint-Directory |
| Data file | [SMAEndpointDirectory.csv](https://raw.githubusercontent.com/CMSgov/SMA-Endpoint-Directory/main/SMAEndpointDirectory.csv) |
| Last updated | May 15, 2025 |
| Publisher | CMS Center for Medicaid and CHIP Services (CMCS) |

**What it provides:** Production FHIR API base URLs, implementation dates, FHIR versions, authentication protocols, data refresh frequency, developer contact info, and sandbox URLs for all state Medicaid FFS programs.

**Authority:** This is the official CMS registry for state Medicaid interoperability endpoints, developed under the MITA initiative.

---

## 2. CMS Medicare Advantage Plan Directory (Official)

| Field | Value |
|-------|-------|
| Records | 105 |
| Source key | `cms_ma_directory_2026` |
| URL | https://www.cms.gov/data-research/statistics-trends-and-reports/medicare-advantagepart-d-contract-and-enrollment-data/ma-plan-directory |
| Download | https://www.cms.gov/files/zip/ma-plan-directory.zip |
| Report period | May 2026 |
| Publisher | CMS Office of Medicare |

**What it provides:** All active MA, Cost, PACE, and Demo organization contracts including: legal entity name, marketing name, contract number, plan type, enrollment counts, parent organization, tax status, and contact information.

**Authority:** Official CMS administrative data. The definitive list of all Medicare Advantage organizations operating in the US.

---

## 3. Defacto Health — State of Provider Directory APIs 2024

| Field | Value |
|-------|-------|
| Records | 230 |
| Source key | `defacto_2024` |
| Report URL | https://defacto.health/2024/06/24/state-of-provider-directory-apis-2024/ |
| Spreadsheet | [Google Sheet](https://docs.google.com/spreadsheets/d/1tiuZfmq1qPtZGoIdYkjxwxlhJc_TZxay/) |
| Published | June 24, 2024 |
| Publisher | Defacto Health (Ron Urwongse) |

**What it provides:** API compliance scores (0-4), issue categories, vendor identification, and status descriptions for the top 137 CMS-regulated payers (>100k public sector covered lives).

**Authority:** Industry research organization that actively tests and monitors payer Provider Directory APIs. Collaborated with payers since July 2021 compliance deadline. Referenced by CMS in interoperability discussions.

**Scoring rubric:**
- 4: API available and regularly queried
- 3: API available with intermittent downtimes
- 2: API has issues, payer actively resolving
- 1: API has issues, payer not resolving
- 0: No API available

---

## 4. CMS Universe Expansion (Compiled)

| Field | Value |
|-------|-------|
| Records | 160 |
| Source key | `cms_universe_expansion` |
| Date compiled | June 3, 2026 |

**Component sources:**
1. **State Medicaid FFS programs** — All 50 states + DC + territories per 42 CFR 431.70 / 457.760
2. **Medicaid Managed Care Organizations** — From CMS Managed Care Enrollment Report (https://data.medicaid.gov)
3. **CHIP programs** — Per 42 CFR 457.1233(d)
4. **KFF Medicaid MCO enrollment data** — https://www.kff.org/medicaid/state-indicator/medicaid-enrollment-by-mco/
5. **CMS Medicaid.gov state contacts** — https://www.medicaid.gov/about-us/where-can-people-get-help-medicaid-chip/

**Purpose:** Ensure complete coverage of ALL CMS-regulated entities, including smaller regional MCOs and state programs not covered by Defacto's top-137 analysis.

---

## 5. Automated Endpoint Discovery & Correction (2026-06-11)

| Field | Value |
|-------|-------|
| Records corrected | 110+ |
| Source key | `availity_discovery`, `edifecs_discovery`, `conduent_discovery` |
| Date | June 11, 2026 |

**Key finding:** The DeFACTO 2024 URLs were largely incorrect/outdated. Most payers have migrated to hosted FHIR platforms:

| Platform | Payers | URL Pattern |
|----------|--------|-------------|
| **Availity** | ~60 | `apps.availity.com/availity/public-fhir/fhir/v1/{payer}/r4` |
| **Edifecs** | ~50 | `fdp.edifecsfedcloud.com/fhir/{tenant}.*` or `us120.fhir.m3.edifecsfedcloud.com/{state}_pd` |
| **1upHealth** | ~255 | `api.1up.health/fhir/r4/{tenant}` |
| **Conduent** | ~5 | `iox.{state}.conduent.com/providerDirectory/api/R4` |
| **Innovaccer** | 1 | `{payer}.innovaccer.com/fhir/r4` |

**Methodology:**
1. Systematic Availity public FHIR directory probing (`/fhir/v1/{payer_slug}/r4/metadata`)
2. Edifecs Federal Cloud state Medicaid tenant discovery
3. Conduent IOX platform pattern matching for state programs
4. Payer official website interoperability page scraping for citations
5. All corrected URLs verified with live HTTP request (200 or 403 = confirmed)

---

## Validation Methodology (updated 2026-06-11)

Every endpoint was tested individually with a real HTTP GET request using Python `urllib`:

- Target: `{api_base}/metadata` with `Accept: application/fhir+json`
- Timeout: 12 seconds
- User-Agent: `FHIR-Directory-Validator/2.0`
- Delay: 0.25s between requests
- TLS: Certificate verification disabled (some payers use self-signed certs)

Classification based on actual HTTP response:
- `valid` (60) — HTTP 200 + JSON with `resourceType: CapabilityStatement`
- `valid_non_fhir` (129) — HTTP 200 but not a standard CapabilityStatement (server confirmed live)
- `auth_required` (344) — HTTP 401 or 403 (server confirmed, needs credentials)
- `no_api` (6) — No api_base URL exists (plan never published a FHIR endpoint)
- `ip_restricted` (1) — Connection timeout/refused (server blocks external access)

**Confirmation rate: 533/540 (98.7%)**

---

## Regulatory Authority

The Provider Directory API requirement comes from:

| Regulation | Applies to |
|------------|-----------|
| 42 CFR § 422.120 | Medicare Advantage organizations |
| 42 CFR § 431.70 | Medicaid FFS state agencies |
| 42 CFR § 438.242(b)(6) | Medicaid managed care plans |
| 42 CFR § 457.760 | CHIP FFS state agencies |
| 42 CFR § 457.1233(d) | CHIP managed care entities |

Originating rules:
- **CMS-9115-F** (2020): CMS Interoperability and Patient Access Final Rule (85 FR 25510)
- **CMS-0057-F** (2024): CMS Interoperability and Prior Authorization Final Rule
- **CMS-0062-P** (2026): Proposed updates to standards and reporting requirements
