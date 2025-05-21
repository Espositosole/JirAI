from datetime import datetime
from jira_reader import connect_to_jira


def post_results_to_jira(issue_key, scenario_results: list):
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
        summary += f"\n\n🔹 Scenario {s_idx}: {scenario}"

        # Optional: if ScenarioResult is a Pydantic model with .final_result
        if hasattr(results, "final_result") and results.final_result:
            summary += f"\n🧠 Final Result: {results.final_result}"

        scenario_failed = False
        failed_steps = []

        for i, result in enumerate(results, start=1):
            if result["status"] != "passed":
                failed_steps.append((i, result))
                scenario_failed = True
                all_passed = False

        if scenario_failed:
            for i, result in failed_steps:
                step = result["step"]
                status = result["status"]
                step_name = (
                    step.get("description")
                    or step.get("action")
                    or step.get("step", f"Step {i}")
                )
                error = result.get("error", "")
                summary += f"\n{i}. *{step_name}*\n"
                summary += f"   - ❌ Status: {status}\n"
                if error:
                    summary += f"   - ❗ Error: {error}\n"


            summary += "\n❌ Scenario Failed\n"
        else:
            summary += "\n✅ PASSED — all steps succeeded\n"

    summary += (
        "\n## ✅ Overall: All Tests Passed\n"
        if all_passed
        else "\n## ⚠️ Overall: Some Tests Failed\n"
    )

    try:
        jira.add_comment(issue_key, summary)
        print(f"[JIRA] ✅ Comment added to {issue_key}")



        current_issue = jira.issue(issue_key)
        labels = current_issue.fields.labels
        if "testing-in-progress" in labels:
            labels.remove("testing-in-progress")
        if "auto-tested" not in labels:
            labels.append("auto-tested")
        current_issue.update(fields={"labels": labels})
        print(f"[JIRA] 🏷️ Labels updated for {issue_key}")

    except Exception as e:
        print(f"[JIRA] ❌ Failed to update issue: {e}")
