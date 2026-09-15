# AI in NAIMOS Intelligence

## Guardrails (non-negotiable - section 44 of the spec)

The system never: fabricates facts or statistics, infers guilt, identifies an
individual as a criminal, performs facial/biometric recognition, makes
autonomous enforcement decisions, presents a prediction as a confirmed event,
or exposes restricted information. Every AI-touched output is labeled with
its source category - OBSERVED / REPORTED / AI-DETECTED / AI-PREDICTED /
HUMAN-VERIFIED - and, where applicable, a confidence score.

Concretely, in this codebase:

- Risk scores are always returned with a factor breakdown and explanation
  string ending in *"not confirmation of illegal activity"*
  (`services/risk/engine.py`).
- AI detections (`ai_detections` table) default `requires_verification=true`
  and carry a `review_status` that starts `PENDING` - nothing is auto-verified.
- Satellite change-detection results always carry a disclaimer stating the
  analysis is simulated and that it requires field verification, never
  confirmation of illegal activity (`schemas/satellite.py::SatelliteScanResult`).
- Image analysis results are explicitly labeled *"an observation aid, not
  legal proof"* with *"No facial recognition or biometric identification is
  performed"* (`schemas/evidence.py::ImageAnalysisOut`).
- Generated reports separate `VERIFIED FACTS` from `AI-GENERATED
  INTERPRETATION` and cite source incident IDs (`services/reports/generator.py`).
- The AI assistant answers *only* from database query results; if nothing
  matches, it says "Insufficient verified data" rather than guessing.

## LLMProvider abstraction

`services/ai/llm_provider.py` defines the interface; `get_llm_provider()`
returns:

- **`MockLLMProvider`** (default, no API key needed) - deterministic,
  clearly-labeled `[DEMO AI OUTPUT]` text; a fixed sample transcript for
  voice notes; a deterministic subset of sample object-detection labels for
  images.
- **`OpenAILLMProvider`** (active once `OPENAI_API_KEY` is set) - real
  OpenAI-compatible `/chat/completions` calls for text generation. Voice
  transcription and image analysis still delegate to the mock implementation
  (see the module docstring for why).

Every AI-touched record stores `model_name` + `model_version` so outputs are
auditable and comparable across model versions (section 35).

## SatelliteProvider abstraction

`services/satellite/provider.py` defines the interface (`detect_change(lat,
lon) -> ChangeDetectionResult`); `get_satellite_provider()` currently always
returns `MockSatelliteProvider`, which simulates a Sentinel-2-style
before/after pass deterministically per AOI per day (so re-scanning the same
spot the same day returns the same result, and a repeat scan the next day
draws a fresh one - standing in for a new satellite pass becoming
available). Every field a real provider would need to supply is modeled:
imagery provider, acquisition date, resolution, cloud coverage, detected
change type/confidence/area. The Satellite Monitoring page (`apps/web/src/app/(app)/satellite`)
shows this alongside real current satellite imagery for the same AOI (Esri
World Imagery), so the mechanism is genuine even though the change signal
itself is not - see ARCHITECTURE.md for what changes when a real time-series
provider is connected.

## Natural-language → database pipeline (section 20)

```
question → detect_intent() [regex]
         → run_intent() [ONE of a fixed set of hand-written, parametrized SQL queries]
         → executed on the naimos_readonly Postgres role, with statement_timeout + LIMIT
         → format_answer() [template, not free-form generation]
```

See `services/ai/nl_query.py` for the full intent list (districts with most
verified incidents, emerging hotspots, high-risk unverified areas, incidents
near water bodies, region summaries, incidents open >N days, today's
briefing). There is no code path that lets an LLM produce SQL that gets
executed. Every query is logged to `ai_queries` and to `audit_logs`.

## Preliminary field report generation

`services/reports/generator.py::generate_preliminary_report()` assembles a
per-incident report (Location, Date/time, Equipment, Environmental impact,
River/forest proximity, Evidence, Officer statement, Recommended
classification) - the field officer's counterpart to the PRO/analyst report
generator above. Almost every line is a direct field read or a real
geospatial query (nearest water body/protected area) - there is no LLM call
in the generation path. Two things are explicitly AI-touched and labeled as
such: the **officer statement**, which is the voice-to-report transcript
only after the officer has reviewed and approved it (never the raw AI
output silently), and the **recommended classification**, which is a
transparent, inspectable rule (`_recommended_classification()`) based on
`incident_type` and the existing risk score, not a model guess - and is
explicitly labeled "requires supervisor confirmation."

## Evidence Intelligence (consolidated evidence packages)

`services/evidence/aggregator.py::build_evidence_package()` runs the mock
image detector across every un-analyzed photo on an incident, then
consolidates the per-file results into one summary rather than leaving an
officer to read 30 separate detection lists. The aggregation rule is
deliberately conservative: for a countable class (e.g. "Excavator", which
the mock detector now returns with a `count`), the reported quantity is the
**maximum** seen in any single file, never a sum across files - summing
would risk claiming the same excavator was counted twice because it
appeared in two photos from different angles. Presence-only classes (e.g.
"Active mining pit") report only how many files detected them, no invented
count. `services/reports/generator.py::generate_evidence_package_report()`
formats this into Incident Summary / AI-detected evidence / `PHOTO-001`-style
Evidence Files sections, with the same "requires verification, not legal
proof" framing as single-image analysis - and explicitly states that
original evidence files and their audit trail remain authoritative and are
never replaced by the summary.

## Human feedback loop (section 34)

`POST /api/ai/detections/{id}/feedback` lets an authorized user mark an AI
detection `USEFUL` / `NOT_USEFUL` / `CONFIRMED` / `REJECTED` / `NEEDS_REVIEW`;
this is recorded on the detection (`reviewed_by`, `reviewed_at`) and in the
audit log, so future model evaluation has real labels to compare against.
