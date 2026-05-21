"""Inter-phase validation and guardrail checks for pipeline outputs."""

import json
import re
from typing import Any

from pydantic import BaseModel, ValidationError

from guardrails.schemas import ProductOutput, ResearchOutput, StrategyOutput


def validate_research_output(output: ResearchOutput) -> list[str]:
    warnings = []
    if output.confidence < 0.7:
        warnings.append(
            f"Low research confidence ({output.confidence:.2f}) — findings may be under-evidenced. "
            "Consider adding more data sources before proceeding."
        )
    if not output.competitor_summary:
        warnings.append("No competitors identified — market may be unvalidated or search was insufficient.")
    if not output.personas:
        warnings.append("No customer personas defined — target market is unclear.")
    if output.go_no_go_recommendation.strip().lower().startswith("no"):
        warnings.append("Research Agent recommends NO-GO — review findings carefully before approving.")
    return warnings


def validate_strategy_output(output: StrategyOutput) -> list[str]:
    warnings = []

    if output.confidence < 0.7:
        warnings.append(
            f"Low strategy confidence ({output.confidence:.2f}) — financial assumptions may be weak."
        )

    estimates = output.financial_estimates
    # Break-even check
    break_even = estimates.get("break_even_months") or estimates.get("break_even")
    if break_even is not None:
        try:
            if float(break_even) > 36:
                warnings.append(
                    f"Break-even is {break_even} months — exceeds 36-month threshold. "
                    "Reassess pricing or cost structure before proceeding."
                )
        except (TypeError, ValueError):
            warnings.append(
                f"Could not parse break_even_months value '{break_even}' — verify the financial estimates."
            )
    else:
        warnings.append(
            "Break-even timeline not found in financial_estimates — strategy is missing a key assumption."
        )

    # CAC check
    has_cac = any(k for k in estimates if "cac" in k.lower())
    if not has_cac:
        warnings.append(
            "CAC (Customer Acquisition Cost) not found in financial_estimates — "
            "unit economics are incomplete."
        )

    # LTV check
    has_ltv = any(k for k in estimates if "ltv" in k.lower())
    if not has_ltv:
        warnings.append(
            "LTV (Lifetime Value) not found in financial_estimates — "
            "unit economics are incomplete."
        )

    return warnings


def validate_product_output(output: ProductOutput) -> list[str]:
    warnings = []

    if output.confidence < 0.7:
        warnings.append(
            f"Low product confidence ({output.confidence:.2f}) — scope estimates may be unreliable."
        )

    # Must-have feature count
    if len(output.must_have_features) > 8:
        warnings.append(
            f"Feature creep detected: {len(output.must_have_features)} must-have features exceeds limit of 8. "
            "Trim to the features without which the product cannot launch."
        )

    # Build scope > 12 weeks
    scope = output.estimated_build_scope.lower()
    numbers = re.findall(r"\b(\d+(?:\.\d+)?)\s*(?:weeks?|wks?)\b", scope)
    if numbers:
        total_weeks = sum(float(n) for n in numbers)
        if total_weeks > 12:
            warnings.append(
                f"Estimated build scope (~{total_weeks:.0f} weeks) exceeds 12-week MVP limit. "
                "Identify what to cut from must-have features to fit within the constraint."
            )
    elif "week" in scope:
        # Couldn't parse a number but weeks are mentioned — flag for human review
        warnings.append(
            "Could not parse a total week count from estimated_build_scope — "
            "manually verify the estimate stays under 12 weeks."
        )

    return warnings


def validate_phase_output(
    raw_output: Any, schema_class: type[BaseModel]
) -> tuple[BaseModel | None, list[str]]:
    """Parse raw LLM output into a Pydantic schema. Returns (parsed, errors)."""
    errors = []

    # If already the right type, return as-is
    if isinstance(raw_output, schema_class):
        return raw_output, []

    # Try to extract JSON from string output (LLMs often wrap JSON in markdown)
    if isinstance(raw_output, str):
        # Strip markdown code fences if present
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw_output)
        if match:
            raw_output = match.group(1)
        try:
            raw_output = json.loads(raw_output)
        except json.JSONDecodeError as e:
            errors.append(f"JSON parse error: {e}")
            return None, errors

    # Try Pydantic validation
    if isinstance(raw_output, dict):
        try:
            return schema_class(**raw_output), []
        except ValidationError as e:
            for err in e.errors():
                field = " -> ".join(str(loc) for loc in err["loc"])
                errors.append(f"Field '{field}': {err['msg']}")
            return None, errors

    errors.append(f"Unexpected output type: {type(raw_output).__name__} — expected dict or JSON string.")
    return None, errors
