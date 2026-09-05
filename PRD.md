# Product Requirements Document: Recovery Loop

**Competition:** Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery
**Deadline:** September 5, 2026
**Builder:** Solo
**Stack constraint:** 100% free tools only

---

## 1. Problem Statement

Revenue loss rarely happens in one clean step. A payment degrades, a checkout gets abandoned, a subscription fails, or an invoice goes overdue. Today these losses are mostly detected manually or not at all, and even when detected, recovery (retries, nudges, escalation) is either blind (retry immediately, annoying the customer and wasting attempts) or absent entirely.

We are building an agent that closes this loop end-to-end: **detect** revenue at risk → **diagnose** the root cause → **decide** the right bounded intervention → **execute** it → **prove**, with real numbers, how much money was recovered.

The system must handle more than one shape of revenue loss to reflect reality — we are covering two: **failed payments** and **abandoned checkouts** — through one shared pipeline, not two separate products.

---

## 2. Goals

- Detect revenue-at-risk events from two categories: payment failures and checkout abandonment.
- Diagnose the root cause of each event using an LLM, constrained to a fixed, explainable taxonomy (not free-text guessing).
- Decide the correct recovery action through a deterministic policy gate — the LLM proposes, the gate disposes. No action reaches execution without passing gate validation.
- Execute bounded recovery actions (payment retries via Razorpay test-mode API; simulated recovery nudges for abandoned checkouts).
- Detect and gracefully handle one specific failure mode: a "retry storm" (too many retry attempts for one user in a short window), which pauses further action and escalates to a human-alert log entry.
- Maintain a complete, queryable, append-only audit trail of every event, diagnosis, decision, and action.
- Run a full synthetic batch and report honest, measured results: money recovered vs. money at risk, recovery rate by category, and an explicit list of what could not be recovered and why.

## 3. Non-Goals (explicitly out of scope)

- No real messaging integrations (no WhatsApp, SMS, or email sending — recovery "nudges" and "alerts" are logged as structured records, not actually sent anywhere).
- No production webhook infrastructure — failure/abandonment events are injected directly via a simulation function, not received via live Razorpay webhooks.
- No separate frontend framework or second deployment target. One backend service serves both the API and a minimal page for viewing the audit trail.
- No B2B receivables workflow, no voice/Hinglish feature, no promise-to-pay tracker — these are possible future extensions, not part of this build.
- No claim that recovery-rate numbers are validated against real production data. They are simulated using probabilities modeled on realistic, cited industry ranges, and must be labeled as such everywhere they appear.

---

## 4. Users & Context

This is a hackathon submission evaluated by judges reviewing a GitHub repo, a demo video, and (optionally) a live deployed instance. The primary "user" of the running system, for demo purposes, is the evaluator triggering batches of simulated events and inspecting the resulting audit trail and metrics. Secondary framing: a merchant relying on this agent to recover revenue without manual intervention.

---

## 5. Core Concepts & Data Model

The system is built around one unified event type so that both loss categories flow through the same pipeline. This is a deliberate design choice: it proves the architecture generalizes across loss types rather than being hardcoded to one.

**`revenue_event`**
- `id`
- `type`: `payment_failure` | `checkout_abandonment`
- `user_id`
- `amount`
- `context`: for payment failures, a decline code (`R01` insufficient funds, `R02` card expired, `R03` fraud suspected, `R04` network timeout); for checkout abandonment, cart contents and time since abandonment
- `detected_at`
- `status`: open | in_progress | recovered | unrecovered | escalated

**`diagnosis`**
- `event_id`
- `root_cause`
- `recommended_action`
- `confidence`
- `rationale` (plain-language explanation from the LLM call)
- `model_used`

**`policy_decision`**
- `event_id`
- `action_proposed`
- `action_approved` (boolean)
- `rule_triggered` (which specific policy rule made the call)
- `rationale`
- `timestamp`

**`recovery_action`**
- `event_id`
- `action_type`: retry | nudge | escalate | block
- `executed_at`
- `outcome`: success | failure | pending
- `attempt_number`

**`audit_log`**
An append-only, queryable view joining the above four tables end-to-end per event, so any single event's full journey (detected → diagnosed → decided → acted → outcome) can be inspected in one place.

---

## 6. Functional Requirements

### 6.1 Detection
- Generate a synthetic batch of ~60 payment-failure events across the four decline codes (realistic distribution — R01 and R04 most common, R03 rare) and ~15 checkout-abandonment events (varied cart values and abandonment windows).
- Each event is inserted as a `revenue_event` record with `status = open`.

### 6.2 Diagnosis
- For each open event, call the LLM (Groq, free tier) with the event's context.
- The LLM must return a structured response: `root_cause`, `recommended_action`, `confidence`, `rationale` — constrained to the fixed taxonomy below, not open-ended text.
- Store this as a `diagnosis` record linked to the event.

**Fixed taxonomy — payment failures:**
| Decline code | Root cause | Recommended action |
|---|---|---|
| R01 | Insufficient funds | Retry, scheduled next morning |
| R02 | Card expired | Nudge (payment method update) |
| R03 | Fraud suspected | Block + escalate, no retry |
| R04 | Network timeout | Retry immediately, up to 3 attempts |

**Fixed taxonomy — checkout abandonment:**
| Signal | Root cause | Recommended action |
|---|---|---|
| High cart value, recent abandonment | Likely price/hesitation | Nudge within 24h |
| Low cart value or old abandonment | Low recovery likelihood | No action / log only |

### 6.3 Policy Gate (deterministic — the safety spine of the system)
This is a pure, rule-based function. It receives the LLM's proposed action and either approves or rejects it, with a stated reason. The LLM's output never reaches an execution call directly.

Rules to implement:
1. **Max retry cap**: no more than 3 retry attempts per event (grounded in NACHA's real-world 3-attempt convention for failed mandates — cite this in documentation as the source of the rule, not as a claim that this system is NACHA-certified).
2. **Idempotency check**: a hash of `(user_id, event_id, attempt_number)` prevents duplicate execution of the same action.
3. **Retry-storm check**: if a user has more than 10 retry attempts logged within a rolling 1-hour window, all further retries for that user are paused and the event is escalated. **This is the system's one designated graceful-failure scenario** — it must be reliably reproducible on demand for the demo.
4. **Spend/exposure cap**: total attempted recovery value per session/user must not exceed ₹5,000; beyond this, the event is escalated for manual review rather than auto-actioned.
5. **Nudge cooldown**: no more than one nudge per cart within a 24-hour window (checkout-abandonment path).

Every gate decision (approved or rejected, and which specific rule fired) is stored as a `policy_decision` record.

### 6.4 Execution
- **Payment retries**: call Razorpay's test-mode payment retry endpoint. R01 retries are scheduled (a simple stored timestamp check is sufficient — no external scheduler library required). R04 retries fire immediately, up to the cap.
- **Checkout nudges**: simulated — record a structured `recovery_action` entry (`action_type = nudge`) representing "recovery link would be sent here." No real message is sent.
- **Escalations**: logged as a `recovery_action` entry (`action_type = escalate`) with the triggering rule and event context. No real alert (email/SMS) is sent — this is a log-based simulation of human handoff.
- Every execution attempt, regardless of outcome, is stored as a `recovery_action` record.

### 6.5 Audit Trail
- A single query/view (or simple endpoint/page) must be able to show, for any event, its full lifecycle: the original event, its diagnosis, the policy decision, and the resulting action and outcome — in chronological order.
- The audit trail is append-only. No record is ever deleted or overwritten.

### 6.6 Metrics & Reporting
After running the full batch, compute and display:
- Total ₹ at risk (sum of all event amounts)
- Total ₹ recovered (sum of amounts where outcome = success)
- Recovery rate, overall and broken down by decline code / event type
- Count and list of unrecovered events with their reason (exception list)
- One explicit, visible statement that recovery-rate figures are simulated using probabilities modeled on cited, realistic industry ranges (e.g., R01 ~70–75%, R04 ~80–85%), not claimed as validated real-world outcomes.

### 6.7 The Graceful Failure Demo
Must be independently triggerable (a specific script or endpoint) that simulates 15 retry attempts for one user within an hour, showing:
1. The retry-storm rule firing.
2. Further retries for that user being paused.
3. An escalation record being created.
4. This entire sequence visible in the audit trail afterward.

---

## 7. Architecture

- **Single backend service** (FastAPI or equivalent) serving both the API and a minimal HTML page for viewing the audit trail and metrics. No separate frontend framework, no second deployment target.
- **LLM calls**: Groq free tier, used only for the diagnosis step — never given direct access to execute payments or actions.
- **Database**: Postgres (Neon or Supabase free tier) for persistence of all four tables — chosen over local SQLite because free-tier hosting can wipe ephemeral disk on redeploy, and the audit trail must survive across the demo period.
- **Payments**: Razorpay test-mode API for the payment-retry path only.
- **No webhooks**, no message-queue/scheduler library, no third-party messaging integration, no charting library — all explicitly deferred as unnecessary for meeting the stated bar.

---

## 8. Success Criteria (the actual grading bar)

| Bar requirement | How this PRD satisfies it |
|---|---|
| Detects revenue at risk | Two event types flowing into one detection pipeline |
| Diagnoses root cause | LLM call with constrained taxonomy + stored rationale |
| Bounded recovery | Retry cap, spend cap, cooldowns — enforced in code |
| Compliant escalation | NACHA-grounded retry cap; retry-storm → pause + escalate |
| Stopping rules | Explicit, testable, independently triggerable |
| Measured money recovered | ₹ recovered / at risk, by category, honestly labeled as simulated |
| Audit trail | Four linked tables, one queryable view, append-only |

---

## 9. Build Phases (for incremental delivery — do not build all at once)

1. **Schema + synthetic data generator** — both event types, realistic distributions.
2. **Diagnosis layer** — LLM call, constrained taxonomy, rationale logging.
3. **Policy gate** — all five rules, testable in isolation from execution logic.
4. **Recovery executor** — Razorpay retry integration + simulated nudge/escalate actions.
5. **Retry-storm scenario** — the graceful-failure centerpiece, independently triggerable.
6. **Batch run + metrics** — compute and display all reporting figures, honestly labeled.
7. **Audit view** — the queryable end-to-end trail.
8. **Documentation** — README with architecture diagram and the bar-mapping table above.

Each phase should be completed, tested, and confirmed working before moving to the next. Do not add features outside this document without explicitly updating it first — scope discipline is a stated project requirement, not a suggestion.