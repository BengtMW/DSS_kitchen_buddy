# A simple terminal app for testing the backend without a UI
import requests
from typing import List, Dict, Any

BASE_URL = "http://localhost:8000"  # FastAPI server URL


def parse_recipe(recipe_text: str) -> Dict[str, Any]:
    """Send recipe text to the backend and return the parsed steps."""
    resp = requests.post(
        f"{BASE_URL}/parse_recipe",
        json={"recipe_text": recipe_text},
        timeout=60,
    )
    resp.raise_for_status()      # Error if status != 200
    return resp.json()           # Parsed JSON as Python dict


def ask_question(
    question: str,
    current_step: Dict[str, Any],
    all_steps: List[Dict[str, Any]],
) -> str:
    """Send a question to the backend and return the answer text."""
    resp = requests.post(
        f"{BASE_URL}/ask",
        json={
            "question": question,
            "current_step": current_step,
            "all_steps": all_steps,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["answer"]


def main():
    print("=== KitchenBuddy CLI Demo ===")
    print("Paste your recipe below. Finish with an empty line.\n")

    # Collect recipe text line by line
    lines: List[str] = []
    while True:
        line = input()
        if not line.strip():     # Empty line = end of recipe input
            break
        lines.append(line)

    recipe_text = "\n".join(lines)

    print("\nSending recipe to backend...")
    data = parse_recipe(recipe_text)

    steps: List[Dict[str, Any]] = data["steps"]  # Extract steps list
    title = data.get("title") or "Untitled recipe"

    print(f"\nRecipe title: {title}")
    print(f"Total steps: {len(steps)}")

    # Start at the first step (index 0)
    i = 0
    while 0 <= i < len(steps):
        step = steps[i]

        # Show current step
        print(f"\nStep {step['number']}/{len(steps)}: {step['instruction']}")
        cmd = input("[n]ext, [p]revious, [q]uestion, [e]xit: ").strip().lower()

        if cmd == "n":
            # Go to next step
            i += 1
            continue

        elif cmd == "p":
            # Go to previous step
            i -= 1
            continue

        elif cmd == "q":
            # Ask KitchenBuddy a question about this step / recipe
            q = input("Ask KitchenBuddy: ")
            answer = ask_question(q, step, steps)
            print(f"\nKitchenBuddy: {answer}\n")
            # Do not change step index, stay on same step
            continue

        elif cmd == "e":
            # Exit the program
            print("Bye!")
            break

        else:
            # Invalid command
            print("Unknown command. Use n/p/q/e.")
            continue

    # This runs when we exit the while loop normally (finished steps)
    if i >= len(steps):
        print("\nYou have finished all the steps. Enjoy your meal! 😋")


if __name__ == "__main__":
    main()