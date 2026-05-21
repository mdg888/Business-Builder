# Business Builder

Business Builder is an AI-assisted business planning system that takes a freeform business idea and runs it through a sequential four-phase pipeline — Research, Strategy, Product Planning, and Execution — producing a full suite of launch-ready artifacts. Each phase is handled by a specialised AI agent built on CrewAI and powered by Claude (Anthropic). A human approval gate sits between every phase, so you review and confirm the direction before the next agent runs. The system generates documents, plans, and starter code — it does not autonomously deploy, spend money, or launch anything.

---

## Prerequisites

- Python 3.11+
- [Anthropic API key](https://console.anthropic.com/) — for all LLM calls
- [Serper API key](https://serper.dev/) — for live web search in the Research phase

---

## Setup

```bash
# 1. Clone the repo and enter the project directory
cd business-builder

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux
```

Edit `.env` and fill in your keys:

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
SERPER_API_KEY=your_serper_api_key_here
```

---

## Usage

**Basic run — idea as an argument:**
```bash
python main.py "AI-powered meal prep service for busy professionals"
```

**Basic run — interactive prompt:**
```bash
python main.py
```

**Resume a previous run from where it left off:**
```bash
python main.py --resume
```

The pipeline will pause at each phase gate and ask you to approve, reject, or provide feedback before continuing. If you reject a phase, the agent re-runs once with your feedback incorporated. If rejected twice, the pipeline aborts with a clear message.

---

## Project Structure

```
business-builder/
├── main.py                    # CLI entrypoint
├── crew.py                    # CrewAI orchestration and phase logic
├── config/
│   ├── agents.yaml            # Agent role, goal, and backstory definitions
│   └── tasks.yaml             # Task descriptions and expected outputs
├── agents/                    # Agent module placeholders
├── tasks/                     # Task helpers
├── state/
│   └── pipeline_state.py      # PipelineState dataclass + JSON save/load
├── guardrails/
│   ├── schemas.py             # Pydantic output models for all phases
│   ├── validation.py          # Per-phase guardrail checks and warnings
│   └── approvals.py           # Human gate CLI logic
├── tools/
│   ├── search_tools.py        # SerperDev search tool
│   ├── file_tools.py          # Markdown file writer
│   └── code_tools.py          # Starter repo scaffolder
├── outputs/
│   ├── reports/               # Business plan, deployment guide
│   ├── plans/                 # Landing page copy, pitch deck, brand guidelines, launch checklist
│   └── generated_code/        # Starter repository scaffold
├── requirements.txt
└── .env.example
```

---

## What the system produces

After a complete run you will find the following artifacts in `outputs/`:

| Artifact | Location |
|---|---|
| Market research report | saved to pipeline state |
| Business strategy + financial estimates | saved to pipeline state |
| MVP feature list + tech stack recommendation | saved to pipeline state |
| Business plan document | `outputs/reports/business_plan.md` |
| Landing page copy | `outputs/plans/landing_page_copy.md` |
| Pitch deck copy (10 slides) | `outputs/plans/pitch_deck_copy.md` |
| Brand guidelines | `outputs/plans/brand_guidelines.md` |
| Launch checklist | `outputs/plans/launch_checklist.md` |
| Starter repository scaffold | `outputs/generated_code/<repo-name>/` |
| Deployment guide | `outputs/reports/deployment_guide.md` |
| Full pipeline state (JSON) | `outputs/pipeline_state.json` |

---

## What this system does NOT do

- **No autonomous deployment** — the deployment guide is a human-readable checklist, not an automated script
- **No payment configuration** — Stripe or other payment providers must be set up manually
- **No live launches** — nothing is published, pushed, or made public without you doing it
- **No spending on your behalf** — no ad accounts, cloud resources, or third-party services are created
- **No legal or financial advice** — all projections and recommendations are starting points for your own due diligence

---

## Build Stage Roadmap

| Stage | Description | Status |
|---|---|---|
| 1 | Research + Strategy generation | Complete |
| 2 | MVP planning + documentation generation | Complete |
| 3 | Starter code scaffolding | Complete |
| 4 | Optional integrations and automation | Planned |

Stage 4 candidates: Stripe setup guides, domain registration instructions, analytics integration templates, CRM starter configs, and social media launch templates.
