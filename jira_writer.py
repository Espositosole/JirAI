from datetime import datetime
from jira_reader import connect_to_jira
import json
import re


def _extract_json_block(text: str):
    """Return first JSON array found in ``text``."""
    if not text:
        return None
    match = re.search(r"```json\s*(\[.*?\])\s*```", text, re.DOTALL)
    if not match:
        match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1) or match.group(0))
        except Exception:
            return None
    return None


def create_subtask_with_scenarios(parent_issue_key: str, scenarios: list[dict]) -> str:
    """Create a subtask under ``parent_issue_key`` containing the given scenarios.

    Returns the new subtask key.
    """
    jira = connect_to_jira()
    parent_issue = jira.issue(parent_issue_key)
    project_key = parent_issue.fields.project.key

    description = (
        "Edit the JSON below to update the test scenarios before moving the parent issue to QA.\n\n"
        "```json\n" + json.dumps(scenarios, indent=2) + "\n```"
    )
    # Determine the correct subtask issue type for this project
    issue_type_id = None
    try:
        meta = jira.createmeta(projectKeys=project_key)
        project_meta = meta.get("projects", [{}])[0]
        for itype in project_meta.get("issuetypes", []):
            if itype.get("subtask"):
                issue_type_id = itype.get("id")
                break
    except Exception:
        pass

    issue_type = {"id": issue_type_id} if issue_type_id else {"name": "Subtask"}

    subtask = jira.create_issue(
        project={"key": project_key},
        summary="Automated Test Scenarios",
        description=description,
        issuetype=issue_type,
        parent={"key": parent_issue_key},
    )
    return subtask.key


def read_scenarios_from_subtask(subtask_key: str) -> list[dict]:
    """Return test scenarios stored in the subtask description."""
    jira = connect_to_jira()
    issue = jira.issue(subtask_key)
    scenarios = _extract_json_block(issue.fields.description)
    if isinstance(scenarios, list):
        return scenarios
    return []


def post_results_to_jira(
    issue_key, scenario_results: list, parent_issue_key: str | None = None
):
    """Post test results as a comment on ``issue_key`` and update labels on ``parent_issue_key`` if provided."""
    print(f"[JIRA] Posting grouped results to issue: {issue_key}")
    if issue_key == "DUMMY-123":
        print("[Mock Mode] Skipping Jira comment post.")
        return

    jira = connect_to_jira()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary = f"## 🧪 Automated Test Report\n"
    summary += f"_Tested on: {timestamp}_\n"

    all_passed = True

    for s_idx, (scenario, results) in enumerate(scenario_results, start=1):
        summary += f"\\nScenario {s_idx}: {scenario}\\n"
        scenario_passed = all(r["status"] == "passed" for r in results)
        emoji = "✅" if scenario_passed else "❌"
        summary += f"Status: {'passed' if scenario_passed else 'failed'} {emoji}\\n"

        # If result_obj contains a 'final_result' field, include it
        final_result = next(
            (r.get("final_result") for r in results if r.get("final_result")), None
        )
        if final_result:
            summary += f"Result: {final_result}\\n"

        # Only show steps if it failed
        if not scenario_passed:
            for i, r in enumerate(results, 1):
                step = r["step"]
                desc = step.get("description") or step.get("action", f"Step {i}")
                status = r["status"]
                summary += f"- {desc} → {'✅' if status == 'passed' else '❌'}\\n"

        summary += "\\n"

    summary += (
        "\n## ✅ Overall: All Tests Passed\n"
        if all_passed
        else "\n## ⚠️ Overall: Some Tests Failed\n"
    )

    try:
        jira.add_comment(issue_key, summary)
        print(f"[JIRA] ✅ Comment added to {issue_key}")

        label_issue_key = parent_issue_key or issue_key
        current_issue = jira.issue(label_issue_key)
        labels = current_issue.fields.labels
        if "testing-in-progress" in labels:
            labels.remove("testing-in-progress")
        if "auto-tested" not in labels:
            labels.append("auto-tested")
        current_issue.update(fields={"labels": labels})
        print(f"[JIRA] 🏷️ Labels updated for {label_issue_key}")

    except Exception as e:
        print(f"[JIRA] ❌ Failed to update issue: {e}")
