"""PipelineState dataclass with JSON serialisation/deserialisation."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from guardrails.schemas import (
    ExecutionOutput,
    ProductOutput,
    ResearchOutput,
    StrategyOutput,
)

OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
STATE_FILE = os.path.join(OUTPUTS_DIR, "pipeline_state.json")


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
    completed_subtasks: list[str] = field(default_factory=list)

    def save_state(self) -> str:
        os.makedirs(OUTPUTS_DIR, exist_ok=True)
        data: dict[str, Any] = {
            "user_brief": self.user_brief,
            "selected_idea": self.selected_idea,
            "current_phase": self.current_phase,
            "phase_history": self.phase_history,
            "human_decisions": self.human_decisions,
            "warnings": self.warnings,
            "completed_subtasks": self.completed_subtasks,
            "research_output": self.research_output.model_dump() if self.research_output else None,
            "strategy_output": self.strategy_output.model_dump() if self.strategy_output else None,
            "product_output": self.product_output.model_dump() if self.product_output else None,
            "execution_output": self.execution_output.model_dump() if self.execution_output else None,
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return STATE_FILE

    @classmethod
    def load_state(cls) -> "PipelineState":
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            user_brief=data["user_brief"],
            selected_idea=data.get("selected_idea"),
            current_phase=data.get("current_phase", "intake"),
            phase_history=data.get("phase_history", []),
            human_decisions=data.get("human_decisions", {}),
            warnings=data.get("warnings", []),
            completed_subtasks=data.get("completed_subtasks", []),
            research_output=ResearchOutput(**data["research_output"]) if data.get("research_output") else None,
            strategy_output=StrategyOutput(**data["strategy_output"]) if data.get("strategy_output") else None,
            product_output=ProductOutput(**data["product_output"]) if data.get("product_output") else None,
            execution_output=ExecutionOutput(**data["execution_output"]) if data.get("execution_output") else None,
        )
