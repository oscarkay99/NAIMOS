# AI in NAIMOS Intelligence

## Guardrails (non-negotiable — section 44 of the spec)

The system never: fabricates facts or statistics, infers guilt, identifies an
individual as a criminal, performs facial/biometric recognition, makes
autonomous enforcement decisions, presents a prediction as a confirmed event,
or exposes restricted information. Every AI-touched output is labeled with
its source category — OBSERVED / REPORTED / AI-DETECTED / AI-PREDICTED /
HUMAN-VERIFIED — and, where applicable, a confidence score.

Concretely, in this codebase:

- Risk scores are always returned with a factor breakdown and explanation
  string ending in *"not confirmation of illegal activity"*
  (`services/risk/engine.py`).
- AI detections (`ai_detections` table) default `requires_verification=true`
  and carry a `review_status` that starts `PENDING` — nothing is auto-verified.
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

- **`MockLLMProvider`** (default, no API key needed) — deterministic,
  clearly-labeled `[DEMO AI OUTPUT]` text; a fixed sample transcript for
  voice notes; a deterministic subset of sample object-detection labels for
  images.
- **`OpenAILLMProvider`** (active once `OPENAI_API_KEY` is set) — real
  OpenAI-compatible `/chat/completions` calls for text generation. Voice
  transcription and image analysis still delegate to the mock implementation
  (see the module docstring for why).

Every AI-touched record stores `model_name` + `model_version` so outputs are
auditable and comparable across model versions (section 35).

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

## Human feedback loop (section 34)

`POST /api/ai/detections/{id}/feedback` lets an authorized user mark an AI
detection `USEFUL` / `NOT_USEFUL` / `CONFIRMED` / `REJECTED` / `NEEDS_REVIEW`;
this is recorded on the detection (`reviewed_by`, `reviewed_at`) and in the
audit log, so future model evaluation has real labels to compare against.
