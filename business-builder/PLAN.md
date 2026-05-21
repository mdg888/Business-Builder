# Business Builder — Architecture Plan

## Overview
AI-assisted business planning system. Sequential multi-agent pipeline using CrewAI.
Human remains responsible for all legal, financial, spending, deployment, and launch decisions.
System generates artifacts (reports, plans, specs, templates) — it does NOT autonomously execute.

---

## Agents (4 total)

| Agent | Role | Responsibility |
|-------|------|----------------|
| Research Agent | Market Analyst | Idea validation, market research, competitor analysis, TAM/SAM/SOM, personas, pricing benchmarks |
| Strategy Agent | Business Strategist | Business model, pricing strategy, positioning, GTM strategy, financial projections |
| Product Agent | Product Manager | MVP definition, feature prioritisation (MoSCoW), tech stack recommendations, user stories, roadmap |
| Execution Agent | Documentation Generator | Business plan docs, landing page copy, pitch deck copy, brand guidelines, starter code templates, launch checklists, deployment instructions |

---

## Pipeline (Sequential)

```
User Brief → [Validate Brief] → Phase 1 → Gate 1 → Phase 2 → Gate 2 → Phase 3 → Gate 3 → Phase 4 → Done
```

### Phase 1 — Research
- Agent: Research Agent
- Input: structured user brief
- Output: `ResearchOutput`
- Gate 1: Human approves business idea + target market direction

### Phase 2 — Strategy
- Agent: Strategy Agent
- Input: approved idea + research summary (≤500 tokens)
- Output: `StrategyOutput`
- Guardrails: revenue assumptions must reference SOM, CAC/LTV must be explained, break-even >36mo triggers warning
- Gate 2: Human approves pricing + financial assumptions + GTM direction

### Phase 3 — Product Planning
- Agent: Product Agent
- Input: approved strategy + strategy summary (≤500 tokens)
- Output: `ProductOutput`
- Guardrails: MVP must stay under 12 weeks estimated effort, feature creep warnings, stack recommendations justified
- Gate 3: Human approves MVP scope

### Phase 4 — Execution Assets
- Agent: Execution Agent
- Input: approved MVP spec + product summary (≤500 tokens)
- Output: `ExecutionOutput`
- Constraint: scaffolds code, generates templates, produces guides. Does NOT deploy, configure payments, or execute live launches.

---

## Schemas

### PipelineState
```python
@dataclass
class PipelineState:
    user_brief: str
    selected_idea: str | None = None
    research_output: ResearchOutput | None = None
    strategy_output: StrategyOutput | None = None
    product_output: ProductOutput | None = None
    execution_output: ExecutionOutput | None = None
    current_phase: str = "intake"
    phase_history: list[dict] = field(default_factory=list)
    human_decisions: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
```

### ResearchOutput
```python
class ResearchOutput(BaseModel):
    selected_business_idea: str
    competitor_summary: list[Competitor]
    personas: list[Persona]
    pricing_summary: str
    tam_sam_som: dict
    risks: list[str]
    go_no_go_recommendation: str
    confidence: float  # 0-1, surfaced at gate if < 0.7
    summary: str  # ≤500 tokens for next phase
```

### StrategyOutput
```python
class StrategyOutput(BaseModel):
    revenue_model: str
    pricing_strategy: str
    acquisition_channels: list[str]
    launch_plan: str
    financial_estimates: dict
    confidence: float
    summary: str
```

### ProductOutput
```python
class ProductOutput(BaseModel):
    must_have_features: list[str]
    should_have_features: list[str]
    user_stories: list[str]
    tech_stack: dict
    estimated_build_scope: str
    confidence: float
    summary: str
```

### ExecutionOutput
```python
class ExecutionOutput(BaseModel):
    generated_documents: list[str]  # file paths
    starter_repo_structure: dict
    deployment_guide: str
    launch_assets: list[str]
```

### Supporting Models
```python
class Competitor(BaseModel):
    name: str
    pricing: str
    differentiation: str

class Persona(BaseModel):
    name: str
    description: str
    pain_points: list[str]
    willingness_to_pay: str
```

---

## Project Structure
```
business-builder/
├── main.py                    # CLI entrypoint
├── crew.py                    # CrewAI orchestration
├── config/
│   ├── agents.yaml            # Agent definitions
│   └── tasks.yaml             # Task definitions
├── agents/
│   ├── research_agent.py
│   ├── strategy_agent.py
│   ├── product_agent.py
│   └── execution_agent.py
├── tasks/
│   └── task_definitions.py
├── state/
│   └── pipeline_state.py      # PipelineState + serialisation
├── guardrails/
│   ├── schemas.py             # Pydantic models
│   ├── validation.py          # Inter-phase validation
│   └── approvals.py           # Human gate logic (CLI)
├── outputs/
│   ├── reports/
│   ├── plans/
│   └── generated_code/
├── tools/
│   ├── search_tools.py        # SerperDev wrapper
│   ├── file_tools.py          # Markdown/PDF export
│   └── code_tools.py          # Starter repo scaffolding
├── requirements.txt
├── .env.example
└── README.md
```

---

## Orchestration
- `process=Process.sequential` (CrewAI)
- No hierarchical orchestration in v1
- Pydantic validation between every phase transition
- JSON state persistence after each phase (for resumability)
- 1 automatic retry on failure, then escalate to human

---

## Tooling (v1 only)
| Tool | Purpose |
|------|---------|
| Search Tool | Market research (SerperDev) |
| Scraper Tool | Competitor analysis |
| File Generator | Markdown/PDF exports |
| Code Scaffold | Starter repo generation |

No live integrations (Stripe, Ads, CRM, deployment automation) in v1.
Generate setup instructions + integration guides instead.

---

## Cost Management
- Premium model (Sonnet) for synthesis/reasoning
- Small model (Haiku) for formatting/cleanup
- Single provider (Anthropic) for v1
- Each phase produces full artifact (disk) + structured summary (≤500 tokens) passed forward
- Never pass full prior outputs into later phases

---

## Build Stages
1. Research + Strategy generation
2. MVP planning + documentation generation
3. Starter code scaffolding
4. Optional integrations and automation
