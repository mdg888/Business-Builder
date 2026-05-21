# Claude Code Prompts — Business Builder

Copy these into Claude Code one at a time. Run and verify each step before moving to the next.

---

## PROMPT 0 — Project Scaffold

```
Read PLAN.md. Create the project structure defined under "Project Structure" with empty placeholder files (just a docstring or comment in each). Create requirements.txt with: crewai, crewai-tools, pydantic, python-dotenv, langchain-anthropic. Create .env.example with placeholders for ANTHROPIC_API_KEY and SERPER_API_KEY. Don't implement anything yet — just the skeleton.
```

**Verify:** Run `find business-builder -type f` and confirm the structure matches PLAN.md.

---

## PROMPT 1 — Schemas + State

```
Read PLAN.md. Implement guardrails/schemas.py with all Pydantic models: Competitor, Persona, ResearchOutput, StrategyOutput, ProductOutput, ExecutionOutput. Include the confidence: float field (0-1) and summary: str field on Research/Strategy/Product outputs. Then implement state/pipeline_state.py with the PipelineState dataclass including current_phase, phase_history, human_decisions, and warnings. Add save_state() and load_state() methods that serialise to/from JSON in the outputs/ directory. Use Pydantic's model_dump() for nested serialisation.
```

**Verify:** Write a quick test — instantiate PipelineState, save it, load it back, confirm round-trip works.

---

## PROMPT 2 — Agent Configs

```
Read PLAN.md. Define the 4 agents in config/agents.yaml using CrewAI's YAML format. Each agent needs: role, goal, backstory, verbose: true, allow_delegation: false. Keep backstories to 2-3 sentences focused on what the agent does, not aspirational fluff. Research Agent uses search + scraper tools. Strategy Agent uses no external tools (works from research output). Product Agent uses no external tools. Execution Agent uses file + code scaffold tools.
```

**Verify:** Read the YAML — each agent should have a clear, non-overlapping scope.

---

## PROMPT 3 — Task Definitions

```
Read PLAN.md. Define the sequential tasks in config/tasks.yaml using CrewAI's YAML format. 4 tasks, one per phase. Each task needs: description (detailed instructions for the agent including what to produce), expected_output (maps to the Pydantic schema for that phase), agent (references the agent from agents.yaml). The research task description should instruct the agent to validate demand, identify competitors, estimate TAM/SAM/SOM, build personas, and produce a go/no-go recommendation. Strategy task should reference the research summary. Product task should reference the strategy summary. Execution task should reference the product summary.
```

**Verify:** Confirm task descriptions are specific enough that the LLM knows exactly what to produce.

---

## PROMPT 4 — Tools

```
Read PLAN.md. Implement tools/search_tools.py with a SerperDev search tool using crewai_tools.SerperDevTool. Implement tools/file_tools.py with a custom tool that writes markdown content to a specified filepath in outputs/. Implement tools/code_tools.py with a custom tool that creates a starter directory structure from a dict specification (folder names + file templates). Keep all tools minimal — no error handling beyond basic try/except with clear error messages.
```

**Verify:** Test the file tool manually — call it to write a test markdown file and confirm it appears in outputs/.

---

## PROMPT 5 — Validation + Guardrails

```
Read PLAN.md. Implement guardrails/validation.py with functions: validate_research_output(output) -> list[str] (returns warnings), validate_strategy_output(output) -> list[str], validate_product_output(output) -> list[str]. Strategy validation should check: break-even > 36 months triggers warning, missing CAC/LTV triggers warning. Product validation should check: estimated effort > 12 weeks triggers warning, must_have_features > 8 triggers feature creep warning. All validators return a list of warning strings (empty = passed). Also add a validate_phase_output(output, schema_class) function that tries to parse raw LLM output into the Pydantic schema and returns (parsed_output, errors).
```

**Verify:** Test with deliberately bad data — confirm warnings fire correctly.

---

## PROMPT 6 — Human Approval Gates

```
Read PLAN.md. Implement guardrails/approvals.py with a run_approval_gate(phase_name: str, output: BaseModel, warnings: list[str]) -> tuple[bool, str] function. It should: print a formatted summary of the phase output, print any warnings in yellow, ask the user to approve/reject/provide feedback via CLI input, return (approved: bool, feedback: str). If rejected, the feedback string is passed back so the phase can be re-run with additional context. Keep it simple CLI — no TUI libraries.
```

**Verify:** Run it standalone with a mock ResearchOutput — confirm the approval flow works interactively.

---

## PROMPT 7 — Crew Orchestration

```
Read PLAN.md. Implement crew.py with a BusinessBuilderCrew class that: loads agents from config/agents.yaml, loads tasks from config/tasks.yaml, assigns tools to agents (search + scraper to Research, file + code to Execution), runs Process.sequential, and between each phase: (1) validates output with the Pydantic schema, (2) runs the guardrail validator, (3) runs the human approval gate (for phases 1-3), (4) saves state to JSON, (5) generates the ≤500 token summary for the next phase. If approval is rejected, re-run the phase with the human's feedback appended to the task description. Max 1 retry per phase — if rejected twice, abort with a clear message. Use langchain-anthropic with claude-sonnet-4-20250514 as the LLM.
```

**Verify:** Read through the orchestration logic — trace the flow mentally from phase 1 through 4.

---

## PROMPT 8 — Main Entrypoint

```
Read PLAN.md. Implement main.py as a CLI entrypoint that: (1) takes a business idea as a string argument (or prompts for it interactively), (2) runs a brief preprocessing step that extracts structured fields from the freeform input (industry, target_market, budget_range, timeline) using a single LLM call and confirms them with the user, (3) initialises PipelineState with the validated brief, (4) runs BusinessBuilderCrew, (5) saves all final outputs to outputs/, (6) prints a summary of what was generated. Support a --resume flag that loads existing state and continues from where it left off.
```

**Verify:** Run `python main.py "AI-powered meal prep service for busy professionals"` and confirm the brief preprocessing works correctly (it will fail at the crew stage if API keys aren't set — that's fine for now).

---

## PROMPT 9 — README

```
Read PLAN.md. Create a README.md that covers: what this project does (1 paragraph), prerequisites (Python 3.11+, API keys), setup instructions (venv, pip install, .env), usage (basic run command, resume command), project structure overview, what the system produces (list of artifacts), what it does NOT do (no autonomous deployment/spending/launching), and build stage roadmap.
```

---

## Running Order Checklist

- [ ] Prompt 0 — Scaffold
- [ ] Prompt 1 — Schemas + State
- [ ] Prompt 2 — Agent Configs
- [ ] Prompt 3 — Task Definitions
- [ ] Prompt 4 — Tools
- [ ] Prompt 5 — Validation
- [ ] Prompt 6 — Approval Gates
- [ ] Prompt 7 — Crew Orchestration
- [ ] Prompt 8 — Main Entrypoint
- [ ] Prompt 9 — README

---

## Tips

- Always start each prompt with "Read PLAN.md"
- If Claude Code generates something wrong, give it the specific error + the relevant file only
- Don't skip ahead — each prompt depends on the previous one being correct
- After Prompt 7, do a full read-through of crew.py before moving on — this is where bugs hide
- Set up your .env with real API keys before testing Prompt 8
- If a prompt produces too much code at once, ask it to split into smaller files