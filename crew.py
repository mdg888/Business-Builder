"""CrewAI orchestration for the Business Builder pipeline."""

import os
import sys
from typing import Any

import yaml
from crewai import Agent, Crew, Process, Task
from crewai.llm import LLM
from crewai_tools import ScrapeWebsiteTool
from dotenv import load_dotenv

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
CYAN = "\033[96m"
RESET = "\033[0m"

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "config")


def _load_yaml(filename: str) -> dict:
    with open(os.path.join(CONFIG_DIR, filename), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _make_llm(max_tokens: int = 4096) -> LLM:
    return LLM(
        model="anthropic/claude-sonnet-4-5",
        api_key=os.environ["ANTHROPIC_API_KEY"],
        max_tokens=max_tokens,
    )


def _build_agent(name: str, cfg: dict, tools: list, max_tokens: int = 4096) -> Agent:
    return Agent(
        role=cfg["role"],
        goal=cfg["goal"],
        backstory=cfg["backstory"],
        verbose=cfg.get("verbose", True),
        allow_delegation=cfg.get("allow_delegation", False),
        tools=tools,
        llm=_make_llm(max_tokens=max_tokens),
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
            tools=[code_scaffold_tool],
        )

    def _make_execution_agent(self, max_tokens: int = 4096) -> Agent:
        return _build_agent(
            "execution_agent",
            self._agents_cfg["execution_agent"],
            tools=[code_scaffold_tool],
            max_tokens=max_tokens,
        )

    # ------------------------------------------------------------------
    # Scaffold writer (bypasses agent — LLMs can't reliably emit large dicts)
    # ------------------------------------------------------------------

    def _write_scaffold(self, outputs_dir: str) -> None:
        import json as _json
        repo_root = os.path.join(outputs_dir, "generated_code", "medication_reminder_sms")
        structure = {
            "README.md": "# Medication Reminder SMS\n\nHIPAA-compliant SMS medication reminder service for Medicare Advantage plans.\n\n## Setup\n```\nnpm install\ncp .env.example .env\nnpm run dev\n```\n",
            ".env.example": "PORT=3000\nDATABASE_URL=postgresql://user:pass@localhost:5432/med_reminder\nTWILIO_ACCOUNT_SID=\nTWILIO_AUTH_TOKEN=\nTWILIO_PHONE_NUMBER=\nAUTH0_DOMAIN=\nAUTH0_CLIENT_ID=\nAUTH0_CLIENT_SECRET=\nREDIS_URL=redis://localhost:6379\n",
            "package.json": _json.dumps({
                "name": "medication-reminder-sms",
                "version": "0.1.0",
                "scripts": {"dev": "nodemon src/index.js", "start": "node src/index.js"},
                "dependencies": {
                    "express": "^4.18.2",
                    "twilio": "^4.19.0",
                    "pg": "^8.11.3",
                    "redis": "^4.6.10",
                    "node-cron": "^3.0.3",
                    "dotenv": "^16.3.1",
                    "express-openid-connect": "^2.17.1",
                },
                "devDependencies": {"nodemon": "^3.0.2"},
            }, indent=2),
            "src/index.js": "// Entry point — starts Express server and scheduler\nrequire('dotenv').config();\nconst app = require('./app');\nconst scheduler = require('./scheduler');\nconst { PORT = 3000 } = process.env;\n\nscheduler.start();\napp.listen(PORT, () => console.log(`Server running on port ${PORT}`));\n",
            "src/app.js": "// Express app — mounts all route handlers\nconst express = require('express');\nconst app = express();\napp.use(express.json());\napp.use('/api/members', require('./routes/members'));\napp.use('/api/schedules', require('./routes/schedules'));\napp.use('/api/reports', require('./routes/reports'));\napp.use('/webhooks/twilio', require('./routes/webhooks'));\nmodule.exports = app;\n",
            "src/scheduler.js": "// node-cron job — queries due reminders and dispatches SMS via Twilio\nconst cron = require('node-cron');\nconst { sendReminders } = require('./services/smsService');\n\nexports.start = () => {\n  // Run every minute; smsService filters members whose reminder is due now\n  cron.schedule('* * * * *', async () => {\n    await sendReminders();\n  });\n};\n",
            "src/routes/members.js": "// CRUD routes for plan member records and bulk CSV upload\nconst router = require('express').Router();\nconst membersController = require('../controllers/membersController');\nrouter.get('/', membersController.list);\nrouter.post('/', membersController.create);\nrouter.post('/bulk-upload', membersController.bulkUpload);\nrouter.put('/:id', membersController.update);\nrouter.delete('/:id', membersController.remove);\nmodule.exports = router;\n",
            "src/routes/schedules.js": "// Routes for medication reminder schedule management\nconst router = require('express').Router();\nconst schedulesController = require('../controllers/schedulesController');\nrouter.get('/:memberId', schedulesController.get);\nrouter.post('/', schedulesController.create);\nrouter.put('/:id', schedulesController.update);\nrouter.delete('/:id', schedulesController.remove);\nmodule.exports = router;\n",
            "src/routes/reports.js": "// Routes for adherence dashboard and MPR reporting\nconst router = require('express').Router();\nconst reportsController = require('../controllers/reportsController');\nrouter.get('/adherence', reportsController.adherenceSummary);\nrouter.get('/mpr', reportsController.mprByMember);\nmodule.exports = router;\n",
            "src/routes/webhooks.js": "// Twilio webhook — handles inbound YES/NO confirmation replies\nconst router = require('express').Router();\nconst { handleReply } = require('../services/smsService');\nrouter.post('/', async (req, res) => {\n  await handleReply(req.body);\n  res.status(200).send('<Response/>');\n});\nmodule.exports = router;\n",
            "src/controllers/membersController.js": "// Member management: list, create, update, delete, bulk CSV import\nconst db = require('../db');\nexports.list = async (req, res) => { /* query members table */ };\nexports.create = async (req, res) => { /* insert member, validate consent */ };\nexports.bulkUpload = async (req, res) => { /* parse CSV, upsert members */ };\nexports.update = async (req, res) => { /* update member record */ };\nexports.remove = async (req, res) => { /* soft-delete member */ };\n",
            "src/controllers/schedulesController.js": "// Medication schedule CRUD for care coordinators\nconst db = require('../db');\nexports.get = async (req, res) => { /* fetch schedules for member */ };\nexports.create = async (req, res) => { /* create reminder schedule */ };\nexports.update = async (req, res) => { /* update schedule */ };\nexports.remove = async (req, res) => { /* delete schedule */ };\n",
            "src/controllers/reportsController.js": "// Adherence reporting: confirmation rates and MPR calculation\nconst db = require('../db');\nexports.adherenceSummary = async (req, res) => { /* aggregate confirmation rates */ };\nexports.mprByMember = async (req, res) => { /* calculate MPR per member */ };\n",
            "src/services/smsService.js": "// Twilio SMS dispatch and inbound reply handling\nconst twilio = require('twilio');\nconst db = require('../db');\nconst client = twilio(process.env.TWILIO_ACCOUNT_SID, process.env.TWILIO_AUTH_TOKEN);\n\nexports.sendReminders = async () => {\n  // Fetch members with reminders due in current minute\n  // Send SMS via Twilio, log dispatch in confirmations table\n};\n\nexports.handleReply = async (body) => {\n  // Parse YES/NO from body.Body, record confirmation in DB\n  // Flag non-responders for care coordinator alert\n};\n",
            "src/db.js": "// PostgreSQL connection pool (pg)\nconst { Pool } = require('pg');\nmodule.exports = new Pool({ connectionString: process.env.DATABASE_URL });\n",
            "db/migrations/001_initial_schema.sql": (
                "-- Members: one row per plan member\n"
                "CREATE TABLE members (\n"
                "  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n"
                "  plan_id UUID NOT NULL,\n"
                "  phone_e164 TEXT NOT NULL,\n"
                "  name TEXT NOT NULL,\n"
                "  opted_in BOOLEAN DEFAULT FALSE,\n"
                "  opted_in_at TIMESTAMPTZ,\n"
                "  created_at TIMESTAMPTZ DEFAULT NOW()\n);\n\n"
                "-- Medication schedules: when to remind each member\n"
                "CREATE TABLE schedules (\n"
                "  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n"
                "  member_id UUID REFERENCES members(id),\n"
                "  medication_name TEXT NOT NULL,\n"
                "  remind_at TIME NOT NULL,\n"
                "  timezone TEXT NOT NULL DEFAULT 'UTC',\n"
                "  active BOOLEAN DEFAULT TRUE\n);\n\n"
                "-- Confirmations: delivery and reply log\n"
                "CREATE TABLE confirmations (\n"
                "  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n"
                "  schedule_id UUID REFERENCES schedules(id),\n"
                "  sent_at TIMESTAMPTZ NOT NULL,\n"
                "  confirmed BOOLEAN,\n"
                "  confirmed_at TIMESTAMPTZ\n);\n"
            ),
        }

        created = []
        for rel_path, content in structure.items():
            full_path = os.path.join(repo_root, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            created.append(rel_path)

        print(f"{GREEN}Scaffolded {len(created)} files under {repo_root}{RESET}")
        for p in created:
            print(f"  {p}")

    # ------------------------------------------------------------------
    # Phase runners
    # ------------------------------------------------------------------

    def _run_single_task(self, agent: Agent, task_cfg: dict, description: str) -> Any:
        task = _build_task(task_cfg, agent, description_override=description)
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)
        result = crew.kickoff()

        # Extract raw text — try multiple attributes CrewAI uses across versions
        raw = None
        for attr in ("raw", "output", "result"):
            val = getattr(result, attr, None)
            if val and str(val).strip():
                raw = str(val).strip()
                break
        if not raw:
            raw = str(result).strip()

        if not raw:
            print(f"{YELLOW}Warning: agent returned empty output.{RESET}")
            return ""

        print(f"\n{BOLD}Raw agent output ({len(raw)} chars):{RESET}\n{raw[:500]}{'...' if len(raw) > 500 else ''}\n")
        return raw

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

        # ── Phase 4: Execution (no gate, split into sub-tasks) ────────
        if self.state.current_phase == "execution":
            ctx = dict(user_brief=brief, product_summary=self.state.product_output.summary)
            outputs_dir = os.path.join(os.path.dirname(__file__), "outputs")

            # Each entry: (task_key, output filepath or None for scaffold)
            sub_tasks = [
                ("execution_task_business_plan", "reports/business_plan.md"),
                ("execution_task_marketing_landing", "plans/landing_page_copy.md"),
                ("execution_task_marketing_pitch", "plans/pitch_deck_copy.md"),
                ("execution_task_marketing_brand", "plans/brand_guidelines.md"),
                ("execution_task_launch", "plans/launch_checklist.md"),
                ("execution_task_deployment", "reports/deployment_guide.md"),
                ("execution_task_code_scaffold", None),
            ]

            sub_results: list[str] = []
            failures: list[str] = []
            for task_key, out_path in sub_tasks:
                if task_key in self.state.completed_subtasks:
                    print(f"\n{CYAN}Skipping completed sub-task: {task_key}{RESET}")
                    sub_results.append("")
                    continue

                print(f"\n{BOLD}--- Execution sub-task: {task_key} ---{RESET}\n")

                # Scaffold is written directly — agents can't reliably build large dicts
                if task_key == "execution_task_code_scaffold":
                    try:
                        self._write_scaffold(outputs_dir)
                        sub_results.append("scaffold written")
                        self.state.completed_subtasks.append(task_key)
                        self.state.save_state()
                        print(f"{GREEN}Checkpoint saved: {task_key}{RESET}")
                    except Exception as e:
                        import traceback
                        print(f"\n{RED}Sub-task {task_key} failed: {e}{RESET}")
                        print(f"{RED}Full traceback:\n{traceback.format_exc()}{RESET}")
                        failures.append(task_key)
                        sub_results.append("")
                    continue

                agent = self._make_execution_agent(max_tokens=4096)
                try:
                    description = self._tasks_cfg[task_key]["description"].format(**ctx)
                    raw = self._run_single_task(agent, self._tasks_cfg[task_key], description)

                    sub_results.append(raw)

                    if out_path and raw:
                        full_path = os.path.join(outputs_dir, out_path)
                        os.makedirs(os.path.dirname(full_path), exist_ok=True)
                        with open(full_path, "w", encoding="utf-8") as f:
                            f.write(raw)
                        print(f"{GREEN}Saved: {full_path}{RESET}")

                    self.state.completed_subtasks.append(task_key)
                    self.state.save_state()
                    print(f"{GREEN}Checkpoint saved: {task_key}{RESET}")
                except Exception as e:
                    import traceback
                    print(f"\n{RED}Sub-task {task_key} failed: {e}{RESET}")
                    print(f"{RED}Full traceback:\n{traceback.format_exc()}{RESET}")
                    failures.append(task_key)
                    sub_results.append("")
                    continue

            if failures:
                print(f"\n{YELLOW}{BOLD}Warning: {len(failures)} sub-task(s) failed: {', '.join(failures)}{RESET}")

            generated_documents = [p for _, p in sub_tasks if p]
            execution_output = ExecutionOutput(
                generated_documents=generated_documents,
                starter_repo_structure={"generated": "see outputs/generated_code/"},
                deployment_guide=sub_results[-2][:500] if len(sub_results) >= 2 else "",
                launch_assets=[
                    "Landing page copy",
                    "Pitch deck copy",
                    "Brand guidelines",
                    "Launch checklist",
                ],
            )

            self.state.execution_output = execution_output
            self.state.phase_history.append({"phase": "execution", "status": "complete"})
            self.state.current_phase = "done"
            self.state.save_state()
            print(f"{GREEN}Phase 4 complete. State saved.{RESET}")

        print(f"\n{BOLD}{GREEN}Pipeline complete.{RESET}")
        return self.state
