# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the pipeline

```bash
# From inside business-builder/
python main.py "Your business idea here"   # pass idea as argument
python main.py                              # interactive prompt
python main.py --resume                    # resume from last saved state
```

Environment setup (one-time):
```bash
cp .env.example .env   # then fill in ANTHROPIC_API_KEY and SERPER_API_KEY
pip install -r requirements.txt
# or with uv:
uv sync
```

## Architecture

The pipeline runs four sequential phases, each backed by a single CrewAI agent. Every phase follows the same pattern: agent runs → output validated against a Pydantic schema → business guardrails checked → human approval gate → next phase. Phase 4 (Execution) skips the gate.

```
main.py          CLI: preprocesses raw idea via LLM, confirms with user, starts crew
crew.py          BusinessBuilderCrew: owns the phase loop and retry logic (max 2 attempts per phase)
```

**Phase → Agent → Schema:**
1. Research → `research_agent` (SerperDev + ScrapeWebsite) → `ResearchOutput`
2. Strategy → `strategy_agent` (no tools) → `StrategyOutput`
3. Product → `product_agent` (no tools) → `ProductOutput`
4. Execution → `execution_agent` (file_tool + code_scaffold_tool) → `ExecutionOutput`

**Key data flow:**
- Agent configs (role/goal/backstory) live in `config/agents.yaml`; task prompts in `config/tasks.yaml`. `crew.py` loads these via `_load_yaml()` and injects phase outputs as `{user_brief}`, `{research_summary}`, etc.
- `PipelineState` (`state/pipeline_state.py`) is a dataclass that serialises to `outputs/pipeline_state.json` after each phase. `--resume` rehydrates this and skips already-completed phases by checking `state.current_phase`.
- `validate_phase_output()` (`guardrails/validation.py`) strips markdown fences, parses JSON, and validates against the Pydantic schema. On failure, the error list is appended to the task description and the agent retries once. After two failures `_abort()` calls `sys.exit(1)` — no state is saved mid-phase.
- `run_approval_gate()` (`guardrails/approvals.py`) prints the phase output and any guardrail warnings, then blocks on user input (a/r). Rejection feedback is appended to the task description for the retry.

**Tools (tools/):**
- `search_tool` — thin wrapper around `SerperDevTool`, used by the research agent
- `file_tool` — writes markdown to `outputs/<filepath>`; used by execution agent
- `code_scaffold_tool` — takes a JSON dict of `{relative_path: content}` and writes the starter repo under `outputs/generated_code/<repo_name>/`

**Guardrails (guardrails/):**
- `schemas.py` — Pydantic models for all four phase outputs. `StrategyOutput` has `field_validator` coercions that convert dicts/lists returned by the LLM into JSON strings for fields that must be `str`.
- `validation.py` — per-phase business rule checks (e.g. confidence < 0.7, break-even > 36 months, CAC/LTV missing, feature count > 8, build scope > 12 weeks). Returns a list of warning strings; warnings are displayed at the gate but do not block approval.

**Outputs written to disk:**

All file output happens only in Phase 4 (Execution Agent). Phases 1–3 only write `outputs/pipeline_state.json`. If the pipeline aborts before Phase 4, `outputs/` will be empty except for the state file.

| File | Written by |
|------|-----------|
| `outputs/pipeline_state.json` | `PipelineState.save_state()` after each phase |
| `outputs/reports/business_plan.md` | execution agent via `file_tool` |
| `outputs/reports/deployment_guide.md` | execution agent via `file_tool` |
| `outputs/plans/landing_page_copy.md` | execution agent via `file_tool` |
| `outputs/plans/pitch_deck_copy.md` | execution agent via `file_tool` |
| `outputs/plans/brand_guidelines.md` | execution agent via `file_tool` |
| `outputs/plans/launch_checklist.md` | execution agent via `file_tool` |
| `outputs/generated_code/<name>/` | execution agent via `code_scaffold_tool` |

## Known failure modes

- **Schema validation loop**: If the LLM returns structured objects for string fields (common in `StrategyOutput`), `validate_phase_output` fails and triggers a retry. The `field_validator` coercions in `schemas.py` handle this for `StrategyOutput` but not yet for other schemas.
- **Tool argument dropping**: The execution agent runs 7 file writes + a scaffold in one task. Deep into the sequence, it sometimes calls `file_tool` with only `filepath` and omits `content`, causing a tool validation error. The file is skipped but may appear in `ExecutionOutput.generated_documents` anyway.
- **No mid-phase resume**: State is only saved after a full phase completes. If the process crashes mid-phase, `--resume` restarts from the beginning of that phase.
