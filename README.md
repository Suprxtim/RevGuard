# RevGuard: Autonomous Revenue Recovery Agent

An intelligent, closed-loop agent that detects revenue at risk (payment failures and checkout abandonments), diagnoses the root cause via LLM, and safely executes bounded recovery workflows through a strict, deterministic policy gate.

## 🏗️ Architecture Diagram

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
    
    subgraph PolicyGate["Policy Gate (Safety Spine)"]
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
    
    subgraph Audit["Audit & Metrics"]
        B --> L[FastAPI App]
        L -->|Server-Sent Events| M[Next.js / Tremor Dashboard]
    end
```

## 🌟 Core Features & Capabilities

### 1. The "Always-On" Autonomous Agent
Toggle the agent active in the dashboard and watch it sweep the database in real-time. It processes events sequentially, utilizing **PostgreSQL Advisory Locks** to ensure thread-safety and prevent race conditions (like duplicate retries).

### 2. Live Agent Activity Feed (SSE)
We built a real-time, terminal-style Activity Feed right in the Next.js dashboard. Powered by **Server-Sent Events (SSE)**, every thought the agent has—from detecting an event, to diagnosing the root cause via LLM, to validating it against the safety policy—is streamed live to the UI.

### 3. AI-Powered Diagnosis & Generation
- **LLM Root Cause Analysis:** Uses fast Groq models (Llama 3.1) to deterministically categorize failures and recommend an action (Retry, Nudge, Escalate). If the API rate limits, it fails over to a robust deterministic fallback.
- **Dynamic Message Generation:** Automatically generates personalized, context-aware recovery copy (e.g., Conversational Hinglish SMS for abandoned checkouts).

### 4. Deterministic Policy Guardrails (The "Safety Spine")
The LLM does not execute actions directly. All AI recommendations must pass through a strict, deterministic Python Policy Gate evaluating 5 rules:
- **Max Retry Cap:** Limits retries to 3 attempts maximum per event.
- **Retry Storm Prevention:** Detects abuse (>10 retries/hr per user), blocking the action and escalating it automatically to protect the merchant account.
- **Spend/Exposure Cap:** Auto-escalates any event over ₹5,000 to manual human review.
- **Nudge Cooldown:** Ensures users are not spammed (max 1 nudge per 24 hours).
- **Idempotency:** Prevents duplicate executions of the exact same action for the same event.

### 5. Chain-of-Thought Visualizer
Click on any event row in the Next.js dashboard to open a beautiful timeline panel displaying the complete audit trail: the exact AI rationale, the specific policy rules triggered, and the recovery outcome.

---

## 🚀 Setup Instructions (Local Deployment)

This project requires **Python 3.11+**, **Node.js 18+**, and **PostgreSQL**. 

### 1. Clone the Repository & Configure Environment
Create a `.env` file in the root of the project with your API keys:
```env
GROQ_API_KEY=your_groq_api_key_here
RAZORPAY_KEY_ID=test_id
RAZORPAY_KEY_SECRET=test_secret
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/revguard
```
*(Note: If you use Docker for Postgres, ensure your `DATABASE_URL` matches your local setup.)*

### 2. Quick Start (Windows)
We have provided a one-click PowerShell script that handles everything: creating the virtual environment, installing Python/Node dependencies, running database migrations, and booting both servers concurrently.
```powershell
.\start_app.ps1
```

### 3. Manual Setup (Mac / Linux / Custom)
If you prefer to start the services manually or are on Mac/Linux, follow these steps:

**Start PostgreSQL Database**
```bash
docker-compose up -d
```

**Start the FastAPI Backend (Port 8000)**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Start the Next.js Frontend (Port 3000)**
```bash
# In a new terminal window
cd template-overview-main
npm install
npm run dev
```

### 4. Run the Demo
1. Open your browser to **http://localhost:3000**.
2. Click **Simulate Batch** to inject failed payments into the database.
3. Toggle the **Agent: ACTIVE** switch in the top right.
4. Watch the real-time activity feed as the agent diagnoses and recovers revenue!

---

## 🏆 Success Criteria / Grading Bar

| Requirement | How this repository satisfies it |
|---|---|
| **Detects revenue at risk** | Three event types (failures, abandonments, B2B invoices) flowing into the Postgres detection pipeline. |
| **Diagnoses root cause** | LLM call with strictly constrained taxonomy + stored rationale (with deterministic fallbacks). |
| **Bounded recovery** | Retry cap, spend cap, cooldowns enforced entirely in deterministic Python code. |
| **Compliant escalation** | Retry-storm immediately causes a pause + escalate action to protect the merchant. |
| **Stopping rules** | Explicit, testable rules isolating the LLM from execution (`app/core/policy_gate.py`). |
| **Measured money recovered** | Real-time live chart displaying ₹ recovered vs ₹ at risk. |
| **Audit trail** | Four linked relational tables, viewable via a premium Next.js Slide-out Timeline UI. |
