"""Code scaffold tool — creates starter repo directory structures from a dict specification."""

import ast
import json
import os
from crewai.tools import BaseTool
from pydantic import BaseModel, Field, field_validator

OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs", "generated_code")


class CodeScaffoldInput(BaseModel):
    repo_name: str = Field(description="Name of the root directory to create inside outputs/generated_code/")
    structure: dict = Field(
        description=(
            "A JSON object mapping relative file paths to their string contents. "
            "Keys are paths relative to the repo root; values are the file contents as strings. "
            'Example: {"src/main.py": "# entrypoint", "README.md": "# Project"}'
        )
    )

    @field_validator("structure", mode="before")
    @classmethod
    def coerce_structure(cls, v):
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
            try:
                parsed = ast.literal_eval(v)
                if isinstance(parsed, dict):
                    return parsed
            except (ValueError, SyntaxError):
                pass
            raise ValueError(f"Could not parse structure as JSON object: {v[:200]}")
        raise ValueError(f"structure must be a dict or JSON string, got {type(v).__name__}")


class CodeScaffoldTool(BaseTool):
    name: str = "code_scaffold_tool"
    description: str = (
        "Creates a starter repository directory structure. "
        "Pass repo_name (string) and structure (a JSON object mapping file paths to their contents)."
    )
    args_schema: type[BaseModel] = CodeScaffoldInput

    def _run(self, repo_name: str, structure: dict) -> str:
        if not isinstance(structure, dict):
            return f"Error: structure must be a JSON object, got {type(structure).__name__}"
        spec = structure

        try:
            root = os.path.join(OUTPUTS_DIR, repo_name)
            created = []
            for relative_path, content in spec.items():
                full_path = os.path.join(root, relative_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    if content:
                        f.write(content)
                created.append(full_path)
            return f"Scaffolded {len(created)} files under {root}:\n" + "\n".join(created)
        except Exception as e:
            return f"Error scaffolding repo '{repo_name}': {e}"


code_scaffold_tool = CodeScaffoldTool()
