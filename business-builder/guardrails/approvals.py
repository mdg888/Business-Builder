"""Human approval gate logic — CLI prompts between pipeline phases."""

import json
from pydantic import BaseModel

YELLOW = "\033[93m"
GREEN = "\033[92m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _print_output_summary(phase_name: str, output: BaseModel) -> None:
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  PHASE COMPLETE: {phase_name.upper()}{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}\n")

    data = output.model_dump()
    for key, value in data.items():
        label = key.replace("_", " ").title()
        if isinstance(value, list):
            print(f"{BOLD}{label}:{RESET}")
            for item in value:
                if isinstance(item, dict):
                    print(f"  - {json.dumps(item, indent=4)}")
                else:
                    print(f"  - {item}")
        elif isinstance(value, dict):
            print(f"{BOLD}{label}:{RESET}")
            for k, v in value.items():
                print(f"  {k}: {v}")
        else:
            print(f"{BOLD}{label}:{RESET} {value}")
        print()


def _print_warnings(warnings: list[str]) -> None:
    if not warnings:
        print(f"{GREEN}No warnings.{RESET}\n")
        return
    print(f"{YELLOW}{BOLD}!! WARNINGS ({len(warnings)}){RESET}")
    for w in warnings:
        print(f"{YELLOW}  ! {w}{RESET}")
    print()


def run_approval_gate(
    phase_name: str, output: BaseModel, warnings: list[str]
) -> tuple[bool, str]:
    _print_output_summary(phase_name, output)
    _print_warnings(warnings)

    print(f"{BOLD}{'-' * 60}{RESET}")
    print(f"{BOLD}HUMAN GATE -- {phase_name.upper()}{RESET}")
    print("Options:")
    print("  [a] Approve and continue")
    print("  [r] Reject and re-run this phase with feedback")
    print(f"{BOLD}{'-' * 60}{RESET}\n")

    while True:
        choice = input("Your decision (a/r): ").strip().lower()
        if choice in ("a", "approve"):
            print(f"\n{GREEN}Approved. Continuing to next phase.{RESET}\n")
            return True, ""
        elif choice in ("r", "reject"):
            print(f"\n{RED}Rejected.{RESET}")
            feedback = input("Provide feedback for the agent (what to fix or improve):\n> ").strip()
            if not feedback:
                feedback = "No specific feedback provided — please improve the output quality."
            print(f"\n{YELLOW}Phase will be re-run with your feedback.{RESET}\n")
            return False, feedback
        else:
            print("Please enter 'a' to approve or 'r' to reject.")
