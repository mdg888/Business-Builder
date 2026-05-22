"""CLI entrypoint for Business Builder pipeline."""

import argparse
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

PREPROCESS_PROMPT = """\
Extract structured fields from the following business idea description.
Return ONLY a valid JSON object with exactly these keys:
- idea: a one-sentence summary of the core business idea
- industry: the primary industry or sector
- target_market: the primary target customer segment
- budget_range: estimated budget range if mentioned, otherwise "unspecified"
- timeline: desired timeline if mentioned, otherwise "unspecified"

Business idea: {raw_input}

Return only the JSON object, no explanation, no markdown fences."""


def _require_api_key() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(f"{BOLD}Error:{RESET} ANTHROPIC_API_KEY is not set.")
        print("Copy .env.example to .env and add your key, then re-run.")
        sys.exit(1)


def _preprocess_brief(raw_input: str) -> dict:
    """Call the LLM once to extract structured fields from freeform input."""
    from langchain_anthropic import ChatAnthropic

    llm = ChatAnthropic(
        model="claude-sonnet-4-5",
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        max_tokens=512,
    )
    prompt = PREPROCESS_PROMPT.format(raw_input=raw_input)
    response = llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)

    # Strip markdown fences if present
    import re
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", content)
    if match:
        content = match.group(1)

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        print(f"{YELLOW}Warning: Could not parse structured brief from LLM. Using raw input.{RESET}")
        return {
            "idea": raw_input,
            "industry": "unspecified",
            "target_market": "unspecified",
            "budget_range": "unspecified",
            "timeline": "unspecified",
        }


def _confirm_brief(fields: dict) -> tuple[bool, str]:
    """Print the extracted fields and ask the user to confirm or edit."""
    print(f"\n{BOLD}Extracted brief:{RESET}")
    print(f"  Idea:          {fields.get('idea', '')}")
    print(f"  Industry:      {fields.get('industry', '')}")
    print(f"  Target market: {fields.get('target_market', '')}")
    print(f"  Budget range:  {fields.get('budget_range', '')}")
    print(f"  Timeline:      {fields.get('timeline', '')}")
    print()

    while True:
        choice = input("Confirm brief? [y = yes / e = edit / q = quit]: ").strip().lower()
        if choice in ("y", "yes"):
            structured = (
                f"Idea: {fields['idea']}\n"
                f"Industry: {fields['industry']}\n"
                f"Target market: {fields['target_market']}\n"
                f"Budget range: {fields['budget_range']}\n"
                f"Timeline: {fields['timeline']}"
            )
            return True, structured
        elif choice in ("e", "edit"):
            print("Enter corrections (press Enter to keep existing value):")
            for key in ("idea", "industry", "target_market", "budget_range", "timeline"):
                val = input(f"  {key} [{fields[key]}]: ").strip()
                if val:
                    fields[key] = val
            return _confirm_brief(fields)
        elif choice in ("q", "quit"):
            print("Aborted.")
            sys.exit(0)
        else:
            print("Please enter y, e, or q.")


def _print_final_summary(state) -> None:
    print(f"\n{BOLD}{GREEN}{'=' * 60}{RESET}")
    print(f"{BOLD}{GREEN}  PIPELINE COMPLETE{RESET}")
    print(f"{BOLD}{GREEN}{'=' * 60}{RESET}\n")

    print(f"{BOLD}Business idea:{RESET} {state.selected_idea}")
    print(f"{BOLD}Phases completed:{RESET} {len(state.phase_history)}/4")
    print()

    if state.execution_output:
        docs = state.execution_output.generated_documents
        if docs:
            print(f"{BOLD}Generated documents ({len(docs)}):{RESET}")
            for doc in docs:
                print(f"  - {doc}")
            print()

        assets = state.execution_output.launch_assets
        if assets:
            print(f"{BOLD}Launch assets:{RESET}")
            for asset in assets:
                print(f"  - {asset}")
            print()

    if state.warnings:
        print(f"{YELLOW}{BOLD}Warnings raised during pipeline:{RESET}")
        for w in state.warnings:
            print(f"{YELLOW}  ! {w}{RESET}")
        print()

    print(f"{CYAN}All outputs saved to:{RESET} business-builder/outputs/")
    print(f"{CYAN}State file:{RESET}         business-builder/outputs/pipeline_state.json\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Business Builder — AI-assisted business planning pipeline."
    )
    parser.add_argument(
        "idea",
        nargs="?",
        help="Your business idea as a string. If omitted, you will be prompted.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from the last saved pipeline state.",
    )
    args = parser.parse_args()

    _require_api_key()

    # Lazy imports — only after API key is confirmed
    from crew import BusinessBuilderCrew
    from state.pipeline_state import PipelineState, STATE_FILE

    # ── Resume path ───────────────────────────────────────────────────
    if args.resume:
        if not os.path.exists(STATE_FILE):
            print(f"{YELLOW}No saved state found at {STATE_FILE}. Starting fresh.{RESET}\n")
            args.resume = False
        else:
            print(f"{CYAN}Resuming from saved state...{RESET}")
            state = PipelineState.load_state()
            print(f"  Current phase: {state.current_phase}")
            print(f"  Idea: {state.selected_idea or state.user_brief[:60]}")
            print()
            crew = BusinessBuilderCrew(state)
            final_state = crew.run()
            _print_final_summary(final_state)
            return

    # ── Fresh run path ────────────────────────────────────────────────
    raw_idea = args.idea
    if not raw_idea:
        print(f"{BOLD}Business Builder{RESET} — AI-assisted business planning\n")
        raw_idea = input("Describe your business idea: ").strip()
        if not raw_idea:
            print("No idea provided. Exiting.")
            sys.exit(0)

    print(f"\n{CYAN}Analysing your brief...{RESET}")
    fields = _preprocess_brief(raw_idea)
    confirmed, structured_brief = _confirm_brief(fields)

    state = PipelineState(user_brief=structured_brief)
    crew = BusinessBuilderCrew(state)
    final_state = crew.run()
    _print_final_summary(final_state)


if __name__ == "__main__":
    main()
