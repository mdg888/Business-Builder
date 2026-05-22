"""Pydantic models: Competitor, Persona, ResearchOutput, StrategyOutput, ProductOutput, ExecutionOutput."""

import json

from pydantic import BaseModel, Field, field_validator


def _coerce_to_str(v) -> str:
    """Coerce dicts/lists returned by the LLM into a JSON string."""
    if isinstance(v, str):
        return v
    return json.dumps(v)


class Competitor(BaseModel):
    name: str
    pricing: str
    differentiation: str


class Persona(BaseModel):
    name: str
    description: str
    pain_points: list[str]
    willingness_to_pay: str


class ResearchOutput(BaseModel):
    selected_business_idea: str
    competitor_summary: list[Competitor]
    personas: list[Persona]
    pricing_summary: str
    tam_sam_som: dict
    risks: list[str]
    go_no_go_recommendation: str
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str


class StrategyOutput(BaseModel):
    revenue_model: str
    pricing_strategy: str
    acquisition_channels: list[str]
    launch_plan: str
    financial_estimates: dict
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str

    @field_validator("revenue_model", "pricing_strategy", "launch_plan", "summary", mode="before")
    @classmethod
    def coerce_str_fields(cls, v) -> str:
        return _coerce_to_str(v)

    @field_validator("acquisition_channels", mode="before")
    @classmethod
    def coerce_channels(cls, v) -> list[str]:
        if isinstance(v, list):
            return [_coerce_to_str(item) for item in v]
        return [_coerce_to_str(v)]


class ProductOutput(BaseModel):
    must_have_features: list[str]
    should_have_features: list[str]
    user_stories: list[str]
    tech_stack: dict
    estimated_build_scope: str
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str


class ExecutionOutput(BaseModel):
    generated_documents: list[str]
    starter_repo_structure: dict
    deployment_guide: str
    launch_assets: list[str]
