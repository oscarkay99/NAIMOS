# Demo Guide

All data is synthetic (`is_demo=true`), clearly banner-labeled in the UI as
**DEMO ENVIRONMENT - DATA IS SIMULATED**. Regions/districts and named rivers/
forest reserves use real, public Ghanaian geography; incidents, evidence,
field reports and AI detections are entirely synthetic.

## Accounts (password: `Demo@1234` for all)

| Email | Role |
|---|---|
| admin@naimos.gov.gh | SUPER_ADMIN |
| national.admin@naimos.gov.gh | NATIONAL_ADMIN |
| ops.manager@naimos.gov.gh | OPERATIONS_MANAGER |
| supervisor@naimos.gov.gh | FIELD_SUPERVISOR |
| officer@naimos.gov.gh | FIELD_OFFICER |
| officer2@naimos.gov.gh | FIELD_OFFICER |
| analyst@naimos.gov.gh | INTELLIGENCE_ANALYST |
| env.analyst@naimos.gov.gh | ENVIRONMENTAL_ANALYST |
| pro@naimos.gov.gh | PRO |
| viewer@naimos.gov.gh | REPORT_VIEWER |
| auditor@naimos.gov.gh | AUDITOR |

## Primary walkthrough (mirrors spec section 43)

1. **Log in** as `admin@naimos.gov.gh` → National dashboard.
2. **Map** → the Ankobra River hotspot near Tarkwa-Nsuaem (Western Region) is
   the flagship demo location - click it.
3. Location Intelligence panel shows **risk score 68 (HIGH)**.
4. Open the incident (`NAIMOS-2026-000101`) → click **"Show breakdown"** on
   the risk panel to see the explainable factors (recent field reports,
   AI-detected signals, proximity to water body, activity trend).
5. Review the **Intelligence Timeline** and existing evidence/AI object
   detection on the seeded photo placeholder.
6. **AI Risk Map** → the full ranked leaderboard across every monitored
   area (score, week-over-week Change%, river proximity, priority) - the
   Ankobra cluster sits at the top. Click **"Recalculate risk scores"** to
   show the score genuinely updating live from a fresh pass, not a canned
   number.
7. As `analyst@naimos.gov.gh` → **Satellite Monitoring** → pick a fresh AOI
   (e.g. click anywhere away from existing hotspots on the imagery) → **Run
   AI Change Detection Scan**. See the live "HIGH-RISK AREA DETECTED" card
   computed by the real risk engine, then click through to pre-fill a new
   field incident from the detected coordinates.
8. Log in as `officer@naimos.gov.gh` → **Field Reporting** → submit a new
   incident, or use **Voice-to-Report**: upload any audio file, review the
   AI-drafted transcript + structured extraction, and approve it.
9. Log in as `analyst@naimos.gov.gh` or `supervisor@naimos.gov.gh` → open the
   incident → **Change Status** to `VERIFIED` with a reason (writes to the
   timeline and audit log).
10. Log in as `pro@naimos.gov.gh` → **Communications** → generate an
    **Executive Brief** - note the VERIFIED FACTS / AI-GENERATED
    INTERPRETATION / SOURCE RECORDS separation.
11. **Intelligence Assistant** → ask "Show emerging hotspots" or "Which
    high-risk areas have not been field verified?" and see it answer strictly
    from the database.
12. **Audit Logs** (as `auditor@naimos.gov.gh`) → see every action from the
    walkthrough recorded, including the satellite scan and risk recalculation.

## Seeded scenarios (spec section 42)

1. Suspected hotspot near a water body - the Ankobra River cluster above.
2. Existing hotspot expands - `NAIMOS-2026-000102`/`000103` near Prestea
   Huni-Valley (older report, then a follow-up showing expansion).
3. Voice-to-report - a pre-approved field report is seeded on the Ankobra
   incident; submit a new one via the Field Reporting page to see the live
   flow.
4. Evidence upload - a placeholder evidence file with a mock AI object-
   detection result is seeded on the Ankobra incident.
5. Investigation assignment - Team Alpha (Western) is assigned to the
   Ankobra investigation.
6. Field verification changes status - `NAIMOS-2026-000104` (Amansie West)
   has a full NEW→VERIFIED history.
7. PRO weekly briefing - Communications Centre.
8. AI detects an anomaly - two `PENDING` `ai_detections` on the Ankobra
   incident.
9. Human rejects an AI detection - a `REJECTED` detection on
   `NAIMOS-2026-000102`, reviewed by the environmental analyst.
10. National risk map - Map page, all layers.

## Resetting demo data

```bash
docker exec naimos-postgres psql -U naimos -d naimos -c \
  "TRUNCATE TABLE roles, permissions, users, regions, water_bodies, protected_areas, forest_reserves CASCADE;"
cd apps/api && source .venv/bin/activate && python -m app.seeds.seed_data
```
