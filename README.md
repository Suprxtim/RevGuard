# RevGuard: AI Revenue Recovery Agent

An intelligent, closed-loop agent that detects revenue at risk (payment failures and checkout abandonments), diagnoses the root cause via LLM, and safely executes bounded recovery workflows through a strict, deterministic policy gate.

## Architecture Diagram

```mermaid
graph TD
    subgraph Detection
        A[Synthetic Data Generator] -->|Injects Events| B[(PostgreSQL Database)]
    end
    
    subgraph Diagnosis
        B -->|Fetch Open Event| C[Groq LLM]
        C -->|Outputs Strict JSON Taxonomy| D[Diagnosis Record]
        D --> B
    end
    
    subgraph Policy Gate (Safety Spine)
        D --> E{Deterministic Rules Engine}
        E -->|Check: Retry Cap| E
        E -->|Check: Idempotency| E
        E -->|Check: Spend Cap| E
        E -->|Check: Retry Storm| E
        E -->|Check: Nudge Cooldown| E
        E -->|Approved / Rejected| F[Policy Decision Record]
        F --> B
    end
    
    subgraph Execution
        F --> G[Recovery Executor]
        G -->|Call Razorpay Test API| H(Payment Retry)
        G -->|Log Simulated Action| I(Nudge via Email/SMS)
        G -->|Log Escalation| J(Human Handoff)
        H --> K[Recovery Action Record]
        I --> K
        J --> K
        K --> B
    end
    
    subgraph Audit & Metrics
        B --> L[FastAPI App]
        L --> M[Jinja2 / Tailwind HTML Dashboard]
    end
```

## Core Features & Capabilities

### 1. Multi-Channel Detection
- **Payment Failures:** Captures failed transactions across various decline codes (Insufficient Funds, Network Timeout, Fraud, Card Expired).
- **Checkout Abandonment:** Detects carts that were abandoned and evaluates recovery viability based on time and cart value.
- **B2B Receivables (Stretch Goal):** Monitors and detects high-value overdue B2B invoices.

### 2. AI-Powered Diagnosis & Generation
- **LLM Root Cause Analysis:** Uses `qwen3.6-27b` to deterministically categorize the failure and recommend an action (Retry, Nudge, Escalate, Block) with a plain-language rationale.
- **Dynamic Message Generation:** Uses `llama-3.1-8b-instant` to automatically generate personalized, context-aware recovery copy (e.g., Conversational Hinglish SMS for consumer checkouts, or Professional Email follow-ups for B2B invoices).

### 3. Deterministic Policy Guardrails (The "Safety Spine")
The LLM does not execute actions directly. All AI recommendations must pass through a strict, deterministic Python Policy Gate evaluating 5 rules:
- **Max Retry Cap:** Limits retries to 3 attempts maximum per event.
- **Retry Storm Prevention:** Detects abuse (>10 retries/hr per user), blocking the action and escalating it automatically to protect the merchant account.
- **Spend/Exposure Cap:** Auto-escalates any event over ₹5,000 to manual human review.
- **Nudge Cooldown:** Ensures users are not spammed (max 1 nudge per 24 hours).
- **Idempotency:** Prevents duplicate executions of the exact same action for the same event.

### 4. Strict Sequential Execution Pipeline
- **Sequential Determinism:** Processes events sequentially to strictly guarantee that `storm_count` rules and global limits are applied perfectly without database race conditions. Safety takes priority over premature speed optimizations.
- **Database Connection Pooling:** Utilizes SQLAlchemy connection pooling (`pool_size=20`) to eliminate network overhead while remaining thread-safe.
- **Simulated Execution:** Integrates with Razorpay's API SDK to simulate actual payment captures and network delays.

### 5. Premium Audit Dashboard UI
- **Action-Driven Interface:** Refreshes on demand instead of using fragile SSE logic, ensuring that the data you see is strictly verified and settled.
- **Slide-Out Details Panel:** Click on any event row to open a beautiful timeline panel displaying the complete audit trail: the exact AI rationale, the specific policy rules triggered, and the actual Hinglish SMS/Email generated (using Qwen3.6-27b).
- **Append-Only Audit Log:** All detections, diagnoses, policy decisions, and executions are stored in a rigid, append-only relational database schema for perfect traceability.

## Setup Instructions

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**
   Rename or edit `.env`:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   RAZORPAY_KEY_ID=test_id
   RAZORPAY_KEY_SECRET=test_secret
   ```

3. **Start Database**
   ```bash
   docker-compose up -d
   ```

4. **Run the Dashboard**
   ```bash
   uvicorn app.main:app --reload
   # Navigate to http://localhost:8000/audit
   ```
   *You can simulate all data directly from the UI buttons!*

## Deployment (Vercel)

RevGuard is designed to be easily deployed to serverless environments like Vercel.

1. **Prerequisites**: Ensure you have a managed PostgreSQL database (like Supabase or Neon) and update the `DATABASE_URL` in your environment variables.
2. **Configuration**: Create a `vercel.json` file in the root directory:
   ```json
   {
     "version": 2,
     "builds": [
       {
         "src": "app/main.py",
         "use": "@vercel/python"
       }
     ],
     "routes": [
       {
         "src": "/(.*)",
         "dest": "app/main.py"
       }
     ]
   }
   ```
3. **Deploy**: Run `vercel` from the CLI or connect your GitHub repository to Vercel for automatic deployments. Make sure to add `GROQ_API_KEY` and `DATABASE_URL` to your Vercel Environment Variables.

## Success Criteria / Grading Bar

| Bar requirement | How this repository satisfies it |
|---|---|
| Detects revenue at risk | Three event types (failures, abandonments, B2B invoices) flowing into the detection pipeline. |
| Diagnoses root cause | LLM call with strictly constrained taxonomy + stored rationale. |
| Bounded recovery | Retry cap, spend cap, cooldowns enforced entirely in deterministic Python code. |
| Compliant escalation | Retry-storm immediately causes a pause + escalate action to protect the merchant. |
| Stopping rules | Explicit, testable rules isolating the LLM from execution (`app/core/policy_gate.py`). |
| Measured money recovered | ₹ recovered / at risk calculated and visualized via Chart.js and deterministic refresh. |
| Audit trail | Four linked relational tables, viewable via a premium Slide-out Timeline UI. |
