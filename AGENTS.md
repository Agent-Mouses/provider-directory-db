# AGENTS.md — Rules for Working on This Repository

Read this file before making any changes.

## What This Repo Is

A SQLite database tracking **all CMS-regulated payer Provider Directory FHIR API endpoints** — their availability, compliance status, and verification results. Covers Medicare Advantage, Medicaid MCOs, state Medicaid FFS, and CHIP programs.

## Rules

1. **Never delete data.** Only append or update. If a record is wrong, update it with a note — don't remove it.

2. **Always record your source.** Every insert/update must set `source`, `source_detail`, `source_url`, and `source_date`. No unsourced data.

3. **Validate before marking compliant.** Don't mark `compliance_flag = 'COMPLIANT'` unless you've hit the endpoint or have official CMS confirmation. Use `'UNKNOWN'` if unsure.

4. **Use the existing schema.** Don't add columns without documenting them in README.md. The schema is intentionally flat for easy querying.

5. **Commit frequently with descriptive messages.** Each commit should say what changed and why (how many records affected, what source).

6. **Respect rate limits.** When probing endpoints, use ≤10 concurrent threads, 0.3s delay between sequential requests. Don't hammer payer servers.

7. **Keep SOURCES.md updated.** If you add a new data source, document it in SOURCES.md with full citation.

8. **CFR citations matter.** When flagging violations, always include the specific CFR section (42 CFR 422.120, 431.70, 438.242(b)(6), 457.760, or 457.1233(d)).

9. **Don't store secrets.** No API keys, OAuth tokens, or credentials in this repo. The `api_base` URLs are public by CMS mandate.

10. **Run validation after bulk imports.** After adding new records with `api_base` URLs, run `scripts/validate_endpoints.py` to verify them.

## Schema Quick Reference

```sql
payers (
    id, org_tin, org_name, note, plan_name,
    portal_url, api_base,
    endpoint_insurance_plan, endpoint_practitioner, endpoint_practitioner_role,
    endpoint_organization, endpoint_organization_affiliation, endpoint_location,
    endpoint_healthcare_service, endpoint_network, endpoint_endpoint,
    requires_registration, requires_api_key, auth_type,
    last_validated, last_validated_status, fhir_version,
    compliance_flag, violation_type, violation_detail,
    source, source_detail, source_url, source_date,
    created_at, updated_at
)
```

## Compliance Flags

| Flag | Meaning |
|------|---------|
| `COMPLIANT` | Open access, verified live |
| `COMPLIANT_WITH_REGISTRATION` | Works but needs app registration |
| `NON_COMPLIANT` | Violates CMS interoperability rule |
| `UNKNOWN` | Not yet determined |
| `NEEDS_ENDPOINT_UPDATE` | URL returns 404, needs new URL |

## Violation Types

| Type | CFR Violated |
|------|-------------|
| `NO_API` | 42 CFR 422.120 / 431.70 / 438.242(b)(6) |
| `NOT_MACHINE_READABLE` | Same — web-only, no FHIR |
| `REGISTRATION_BLOCKS_ACCESS` | 85 FR 25543 (must be publicly accessible) |
| `MISSING_CRITICAL_DATA` | 42 CFR 422.120 (names, addresses, phones, specialties) |
| `NOT_QUERYABLE` | 42 CFR 422.120 (must be accessible) |
| `MEMBER_LOGIN_REQUIRED` | 85 FR 25543 (no user auth allowed) |

## Validation Status Values

| Status | Count | Meaning |
|--------|-------|---------|
| `valid` | 12 | FHIR CapabilityStatement returned (200 + valid JSON) |
| `valid_non_fhir` | 3 | HTTP 200 but not a CapabilityStatement |
| `auth_required` | 270 | Server responds 401/403 (needs registration) |
| `client_error` | 17 | Server responds 4xx other (400/405/etc) |
| `unreachable` | 143 | Connection refused/reset/failed |
| `not_found` | 54 | HTTP 404 — URL has changed |
| `no_api` | 28 | No api_base URL in record |
| `timeout` | 3 | No response within 20 seconds |
| `ssl_error` | 2 | TLS certificate invalid/expired |
| `server_error` | 1 | HTTP 5xx — server broken |

## Scripts

| Script | Purpose | When to run |
|--------|---------|-------------|
| `scripts/init_db.py` | Create/reset schema | First setup only |
| `scripts/retest_all.py` | Real HTTP test ALL endpoints, update DB | Primary validation |
| `scripts/import_defacto.py` | Import Defacto 2024 spreadsheet | When Defacto updates |
| `scripts/collect_endpoints.py` | Seed known payer endpoints | Initial setup |
| `scripts/validate_endpoints.py` | Hit /metadata on all endpoints | Quick spot-check |
| `scripts/deep_scrape.py` | Discover endpoints via probing | Periodic discovery |
| `scripts/discover_all.py` | Background mass validation | When many unknowns exist |

## Technical Standards

- FHIR R4 (Release 4.0.1)
- HL7 US Core IG STU 6.1.0
- HL7 Da Vinci PDex Plan Net IG STU 1.2.0
- No user authentication on Provider Directory API (CMS rule)
- App registration/API key is permitted
