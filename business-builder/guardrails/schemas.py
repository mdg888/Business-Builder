"""Pydantic models: Competitor, Persona, ResearchOutput, StrategyOutput, ProductOutput, ExecutionOutput."""

from pydantic import BaseModel, Field


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
