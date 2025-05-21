import subprocess
import json
import uuid
import os
import re

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
    ]

    print(f"[Runner] Executing scenario '{scenario_name}'")

    try:
        result = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )

        print("[Runner Output]", result.stdout)

        # Step 4: Collect results
        match = re.search(r"(\{.*?\}|\[.*?\])", result.stdout, re.DOTALL)
        parsed = None
        if match:
            try:
                parsed = json.loads(match.group(1))
                if isinstance(parsed, dict) and "steps" in parsed:
                    parsed = parsed.get("steps")
            except json.JSONDecodeError:
                parsed = None
        
        structured_results = []
        if isinstance(parsed, list):
            for idx, step in enumerate(structured_steps):
                step_result = parsed[idx] if idx < len(parsed) else {}
                screenshot_filename = step_result.get("screenshot_filename")
                screenshot_file = (
                    os.path.join(output_dir, screenshot_filename)
                    if screenshot_filename
                    else None
                )
                if screenshot_file and not os.path.exists(screenshot_file):
                    screenshot_file = None
                structured_results.append(
                    TestStepResult(
                        step=step,
                        status=step_result.get("status", "failed"),
                        error=step_result.get("error"),
                        screenshot=screenshot_file,
                    )
                )
        else:
            error_msg = (
                result.stdout.strip().splitlines()[0]
                if result.stdout
                else "Unable to parse browser-use output"
            )
            for step in structured_steps:
                structured_results.append(
                    TestStepResult(
                        step=step,
                        status="failed",
                        error=error_msg,
                        screenshot=None,
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
