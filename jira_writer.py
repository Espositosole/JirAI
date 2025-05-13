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

    for scenario, results in scenario_results:
        summary += f"\n### 🔹 Scenario: *{scenario}*\n"
        for i, result in enumerate(results):
            step = result["step"]
            status = result["status"]
            screenshot = result.get("screenshot", "")
            error = result.get("error", "")

            summary += f"\n**Step {i+1}: {step.get('action')}**\n"
            summary += f"Status: {status}\n"
            if error:
                summary += f"Error: {error}\n"
            if screenshot and os.path.exists(screenshot):
                with open(screenshot, "rb") as image_file:
                    jira.add_attachment(
                        issue=issue_key, attachment=image_file, filename=screenshot
                    )
                summary += f"Screenshot attached: {screenshot}\n"

    try:
        jira.add_comment(issue_key, summary)
        print(f"[JIRA] ✅ Comment added to {issue_key}")
    except Exception as e:
        print(f"[JIRA] ❌ Failed to post comment: {e}")
