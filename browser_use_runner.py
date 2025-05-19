import subprocess
import json
import uuid
import os

from reporter import TestStepResult


def run_browser_use_test(steps, scenario_name="Unnamed Scenario"):
    scenario_id = scenario_name.replace(" ", "_").lower()
    run_id = uuid.uuid4().hex[:8]
    input_filename = f"browser_use_flow_{scenario_id}_{run_id}.json"
    output_dir = "screenshots"
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Normalize steps
    structured_steps = []
    for i, s in enumerate(steps, start=1):
        if isinstance(s, str):
            structured_steps.append(
                {
                    "action": "comment",  # fallback action for unstructured steps
                    "description": s,
                    "screenshot": True,
                    "screenshot_filename": f"{scenario_id}_step_{i}_comment.png",
                }
            )
        else:
            s["screenshot"] = True
            s["screenshot_filename"] = (
                f"{scenario_id}_step_{i}_{s.get('action', 'unknown')}.png"
            )
            structured_steps.append(s)

    # Step 2: Write test plan to .json
    with open(input_filename, "w", encoding="utf-8") as f:
        json.dump(structured_steps, f, indent=2)

    # Step 3: Build command
    command = [
        "browser-use",
        "run",
        input_filename,
        "--screenshot",
        output_dir,
        "--headless",
    ]

    print(f"[Runner] Executing scenario '{scenario_name}'")

    try:
        result = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )

        print("[Runner Output]", result.stdout)

        # Step 4: Collect results
        structured_results = []
        for i, step in enumerate(structured_steps, start=1):
            screenshot_file = os.path.join(output_dir, step.get("screenshot_filename"))
            structured_results.append(
                TestStepResult(
                    step=step,
                    status="passed",  # optionally parse actual status later
                    screenshot=screenshot_file if os.path.exists(screenshot_file) else None,
                )
            )

        return structured_results

    except subprocess.CalledProcessError as e:
        print("[Runner] ❌ Execution failed:", e)
        return [
            TestStepResult(
                step={"action": "browser-use"},
                status="failed",
                error=str(e),
                screenshot=None,
            )
        ]

