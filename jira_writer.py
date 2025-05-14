from datetime import datetime
from jira_reader import connect_to_jira
import os


def post_results_to_jira(issue_key, scenario_results: list):
    print(f"[JIRA] Posting grouped results to issue: {issue_key}")
    if issue_key == "DUMMY-123":
        print("[Mock Mode] Skipping Jira comment post.")
        return

    jira = connect_to_jira()
    summary = f"## 🧪 Automated Test Report\n"
    summary += f"_Tested on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n"

    all_passed = True

    for s_idx, (scenario, results) in enumerate(scenario_results, start=1):
        summary += f"\n\n🔹 Scenario {s_idx}: {scenario}\n"
        scenario_passed = True

        for i, result in enumerate(results, start=1):
            step = result["step"]
            status = result["status"]
            screenshot = result.get("screenshot", "")
            error = result.get("error", "")
            step_name = step.get("action", f"step {i}")
            emoji = "✅" if status == "passed" else "❌"

            summary += f"\n{i}. *{step_name}*\n"
            summary += f"   - {emoji} Status: {status}\n"

            if error:
                summary += f"   - ❗ Error: {error}\n"
            if screenshot and os.path.exists(screenshot):
                with open(screenshot, "rb") as image_file:
                    jira.add_attachment(
                        issue=issue_key, attachment=image_file, filename=screenshot
                    )
                summary += f"   - 📎 Screenshot: `{os.path.basename(screenshot)}`\n"

            if status != "passed":
                scenario_passed = False
                all_passed = False

        summary += (
            "\n✅ Scenario Passed\n" if scenario_passed else "\n❌ Scenario Failed\n"
        )

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
        if "auto-tested" not in labels:
            labels.append("auto-tested")
            current_issue.update(fields={"labels": labels})
            print(f"[JIRA] ✅ Added 'auto-tested' label to {issue_key}")

    except Exception as e:
        print(f"[JIRA] ❌ Failed to update issue: {e}")
