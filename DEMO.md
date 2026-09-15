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
8. Log in as `officer@naimos.gov.gh` → **Field Reporting** → click **"Record
   voice narrative"** and speak a report (e.g. "We arrived at the location
   and found two excavators operating close to the river"), **Transcribe**,
   review the AI draft, **"Use as officer statement & autofill fields"**, add
   a photo, then **Submit**. The AI-generated Preliminary Field Report
   appears immediately - location, equipment, environmental proximity,
   evidence, officer statement, and recommended classification, all pulled
   from the record just created.
9. Log in as `admin@naimos.gov.gh` (or any role with both evidence:upload and
   ai:analyze_image, e.g. SUPER_ADMIN/NATIONAL_ADMIN) → open an incident →
   **bulk-select several photos** in the Evidence uploader in one action →
   click **Generate** under **Evidence Package**. Watch it run AI detection
   across every photo and consolidate the results into one summary ("3
   excavators - seen in 6 file(s)") with a `PHOTO-001` style file index -
   never a sum across files, to avoid double-counting.
10. Log in as `analyst@naimos.gov.gh` or `supervisor@naimos.gov.gh` → open the
    incident → **Change Status** to `VERIFIED` with a reason (writes to the
    timeline and audit log).
11. Log in as `pro@naimos.gov.gh` → **Communications** → generate a **Press
    Briefing**, then a **Media Q&A** - compare the prose vs. the real
    question→answer pairs (note the seizure-count question, answered
    honestly with "not tracked" rather than a fabricated figure), then
    generate an **Executive Brief** to see the VERIFIED FACTS / AI-GENERATED
    INTERPRETATION / SOURCE RECORDS separation.
12. Still as `pro@naimos.gov.gh` → **National Situation Room** - a
    role-specific dashboard, not the same view every other role sees.
    National summary counts, then click through the **Top 10 Emerging
    Hotspots** list/map to see the per-hotspot detail card (risk, estimated
    affected area, distance to water, activity change, last field
    verification).
13. As `analyst@naimos.gov.gh` → **Predictive Intelligence** - ranked by AI
    expansion probability rather than current risk. The Tarkwa-Nsuaem
    cluster tops the list at 95% (CRITICAL) with five named factors
    including a real "New access route detected" signal; click
    **"Recalculate predictions"** to see it genuinely recompute.
14. **Intelligence Assistant** → ask "Which areas have experienced the
    fastest increase in suspected mining activity?" or "Summarise all
    incidents involving excavators in the Western Region" and see it answer
    strictly from the database.
15. **Audit Logs** (as `auditor@naimos.gov.gh`) → see every action from the
    walkthrough recorded, including the satellite scan, risk recalculation,
    and prediction recalculation.

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
