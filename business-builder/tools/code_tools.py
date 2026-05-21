"""Code scaffold tool — creates starter repo directory structures from a dict specification."""

import json
import os
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs", "generated_code")


class CodeScaffoldInput(BaseModel):
    repo_name: str = Field(description="Name of the root directory to create inside outputs/generated_code/")
    structure: str = Field(
        description=(
            "JSON string representing the directory structure. "
            "Keys are file or folder paths relative to the repo root. "
            "String values are written as file contents; null values create empty files. "
            "Example: '{\"src/main.py\": \"# entrypoint\", \"README.md\": \"# Project\"}'"
        )
    )


class CodeScaffoldTool(BaseTool):
    name: str = "code_scaffold_tool"
    description: str = (
        "Creates a starter repository directory structure from a JSON specification. "
        "Pass a repo_name and a JSON structure dict mapping relative file paths to their contents."
    )
    args_schema: type[BaseModel] = CodeScaffoldInput

    def _run(self, repo_name: str, structure: str) -> str:
        try:
            spec: dict = json.loads(structure)
        except json.JSONDecodeError as e:
            return f"Error parsing structure JSON: {e}"

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
