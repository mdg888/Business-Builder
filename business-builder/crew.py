"""CrewAI orchestration for the Business Builder pipeline."""

import os
import sys
from typing import Any

import yaml
from crewai import Agent, Crew, Process, Task
from crewai_tools import ScrapeWebsiteTool
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

from guardrails.approvals import run_approval_gate
from guardrails.schemas import (
    ExecutionOutput,
    ProductOutput,
    ResearchOutput,
    StrategyOutput,
)
from guardrails.validation import (
    validate_phase_output,
    validate_product_output,
    validate_research_output,
    validate_strategy_output,
)
from state.pipeline_state import PipelineState
from tools.code_tools import code_scaffold_tool
from tools.file_tools import file_tool
from tools.search_tools import search_tool

load_dotenv()

BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "config")


def _load_yaml(filename: str) -> dict:
    with open(os.path.join(CONFIG_DIR, filename), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _make_llm() -> ChatAnthropic:
    return ChatAnthropic(
        model="claude-sonnet-4-20250514",
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        max_tokens=8096,
    )


def _build_agent(name: str, cfg: dict, tools: list) -> Agent:
    return Agent(
        role=cfg["role"],
        goal=cfg["goal"],
        backstory=cfg["backstory"],
        verbose=cfg.get("verbose", True),
        allow_delegation=cfg.get("allow_delegation", False),
        tools=tools,
        llm=_make_llm(),
    )


def _build_task(cfg: dict, agent: Agent, description_override: str | None = None) -> Task:
    return Task(
        description=description_override or cfg["description"],
        expected_output=cfg["expected_output"],
        agent=agent,
    )


def _abort(message: str) -> None:
    print(f"\n{RED}{BOLD}PIPELINE ABORTED: {message}{RESET}\n")
    sys.exit(1)


class BusinessBuilderCrew:
    def __init__(self, state: PipelineState):
        self.state = state
        self._agents_cfg = _load_yaml("agents.yaml")
        self._tasks_cfg = _load_yaml("tasks.yaml")
        scraper_tool = ScrapeWebsiteTool()

        # Build agents with their assigned tools
        self.research_agent = _build_agent(
            "research_agent",
            self._agents_cfg["research_agent"],
            tools=[search_tool, scraper_tool],
        )
        self.strategy_agent = _build_agent(
            "strategy_agent",
            self._agents_cfg["strategy_agent"],
            tools=[],
        )
        self.product_agent = _build_agent(
            "product_agent",
            self._agents_cfg["product_agent"],
            tools=[],
        )
        self.execution_agent = _build_agent(
            "execution_agent",
            self._agents_cfg["execution_agent"],
            tools=[file_tool, code_scaffold_tool],
        )

    # ------------------------------------------------------------------
    # Phase runners
    # ------------------------------------------------------------------

    def _run_single_task(self, agent: Agent, task_cfg: dict, description: str) -> Any:
        task = _build_task(task_cfg, agent, description_override=description)
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)
        result = crew.kickoff()
        return result.raw if hasattr(result, "raw") else str(result)

    def _run_phase_with_gate(
        self,
        phase_name: str,
        agent: Agent,
        task_key: str,
        description: str,
        schema_class: type,
        validator,
        has_gate: bool,
    ) -> Any:
        task_cfg = self._tasks_cfg[task_key]

        for attempt in range(1, 3):  # max 2 attempts (original + 1 retry)
            print(f"\n{BOLD}--- Running {phase_name} (attempt {attempt}/2) ---{RESET}\n")
            raw = self._run_single_task(agent, task_cfg, description)

            parsed, errors = validate_phase_output(raw, schema_class)
            if errors:
                print(f"{YELLOW}Schema validation errors:{RESET}")
                for e in errors:
                    print(f"  - {e}")
                if attempt == 1:
                    print(f"{YELLOW}Retrying {phase_name} with schema error context...{RESET}")
                    description += (
                        f"\n\nPREVIOUS ATTEMPT FAILED SCHEMA VALIDATION. Errors:\n"
                        + "\n".join(f"- {e}" for e in errors)
                        + "\nFix these and return valid JSON."
                    )
                    continue
                _abort(f"{phase_name} failed schema validation after 2 attempts.")

            warnings = validator(parsed)

            if not has_gate:
                return parsed

            approved, feedback = run_approval_gate(phase_name, parsed, warnings)
            self.state.human_decisions[f"gate_{phase_name.lower()}"] = "approved" if approved else "rejected"
            self.state.warnings.extend(warnings)

            if approved:
                return parsed

            # Rejected
            if attempt == 2:
                _abort(
                    f"{phase_name} was rejected twice by the human reviewer. "
                    "Restart the pipeline with a revised brief."
                )
            print(f"{YELLOW}Re-running {phase_name} with feedback...{RESET}")
            description += f"\n\nHUMAN REVIEWER FEEDBACK (incorporate this):\n{feedback}"

        # Should never reach here
        _abort(f"{phase_name} exceeded retry limit.")

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self) -> PipelineState:
        brief = self.state.user_brief

        # ── Phase 1: Research ──────────────────────────────────────────
        if self.state.current_phase in ("intake", "research"):
            self.state.current_phase = "research"
            research_description = self._tasks_cfg["research_task"]["description"].format(
                user_brief=brief
            )
            research_output = self._run_phase_with_gate(
                phase_name="Research",
                agent=self.research_agent,
                task_key="research_task",
                description=research_description,
                schema_class=ResearchOutput,
                validator=validate_research_output,
                has_gate=True,
            )
            self.state.research_output = research_output
            self.state.selected_idea = research_output.selected_business_idea
            self.state.phase_history.append({"phase": "research", "status": "complete"})
            self.state.current_phase = "strategy"
            self.state.save_state()
            print(f"{GREEN}Phase 1 complete. State saved.{RESET}")

        # ── Phase 2: Strategy ──────────────────────────────────────────
        if self.state.current_phase == "strategy":
            strategy_description = self._tasks_cfg["strategy_task"]["description"].format(
                user_brief=brief,
                research_summary=self.state.research_output.summary,
            )
            strategy_output = self._run_phase_with_gate(
                phase_name="Strategy",
                agent=self.strategy_agent,
                task_key="strategy_task",
                description=strategy_description,
                schema_class=StrategyOutput,
                validator=validate_strategy_output,
                has_gate=True,
            )
            self.state.strategy_output = strategy_output
            self.state.phase_history.append({"phase": "strategy", "status": "complete"})
            self.state.current_phase = "product"
            self.state.save_state()
            print(f"{GREEN}Phase 2 complete. State saved.{RESET}")

        # ── Phase 3: Product ───────────────────────────────────────────
        if self.state.current_phase == "product":
            product_description = self._tasks_cfg["product_task"]["description"].format(
                user_brief=brief,
                strategy_summary=self.state.strategy_output.summary,
            )
            product_output = self._run_phase_with_gate(
                phase_name="Product",
                agent=self.product_agent,
                task_key="product_task",
                description=product_description,
                schema_class=ProductOutput,
                validator=validate_product_output,
                has_gate=True,
            )
            self.state.product_output = product_output
            self.state.phase_history.append({"phase": "product", "status": "complete"})
            self.state.current_phase = "execution"
            self.state.save_state()
            print(f"{GREEN}Phase 3 complete. State saved.{RESET}")

        # ── Phase 4: Execution (no gate) ───────────────────────────────
        if self.state.current_phase == "execution":
            execution_description = self._tasks_cfg["execution_task"]["description"].format(
                user_brief=brief,
                product_summary=self.state.product_output.summary,
            )
            execution_output = self._run_phase_with_gate(
                phase_name="Execution",
                agent=self.execution_agent,
                task_key="execution_task",
                description=execution_description,
                schema_class=ExecutionOutput,
                validator=lambda _: [],  # no guardrail checks on execution output
                has_gate=False,
            )
            self.state.execution_output = execution_output
            self.state.phase_history.append({"phase": "execution", "status": "complete"})
            self.state.current_phase = "done"
            self.state.save_state()
            print(f"{GREEN}Phase 4 complete. State saved.{RESET}")

        print(f"\n{BOLD}{GREEN}Pipeline complete.{RESET}")
        return self.state
