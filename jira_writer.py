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
    
    for scenario, results in scenario_results:
        summary += f"\n### 🔹 Scenario: *{scenario}*\n"
        scenario_passed = True
        
        for i, result in enumerate(results):
            step = result["step"]
            status = result["status"]
            screenshot = result.get("screenshot", "")
            error = result.get("error", "")

            summary += f"\n**Step {i+1}: {step.get('action')}**\n"
            summary += f"Status: {status}\n"
            
            if status != "passed":
                scenario_passed = False
                all_passed = False
                
            if error:
                summary += f"Error: {error}\n"
            if screenshot and os.path.exists(screenshot):
                with open(screenshot, "rb") as image_file:
                    jira.add_attachment(
                        issue=issue_key, attachment=image_file, filename=screenshot
                    )
                summary += f"Screenshot attached: {screenshot}\n"
        
        # Add scenario result
        if scenario_passed:
            summary += f"\n✅ **Scenario Passed**\n"
        else:
            summary += f"\n❌ **Scenario Failed**\n"

    # Add overall result
    if all_passed:
        summary += f"\n## ✅ Overall: All Tests Passed\n"
    else:
        summary += f"\n## ⚠️ Overall: Some Tests Failed\n"

    try:
        # Post the comment
        jira.add_comment(issue_key, summary)
        print(f"[JIRA] ✅ Comment added to {issue_key}")
        
        # Add the "auto-tested" label only if the tests were run
        current_issue = jira.issue(issue_key)
        labels = current_issue.fields.labels
        
        if "auto-tested" not in labels:
            labels.append("auto-tested")
            current_issue.update(fields={"labels": labels})
            print(f"[JIRA] ✅ Added 'auto-tested' label to {issue_key}")
            
    except Exception as e:
        print(f"[JIRA] ❌ Failed to update issue: {e}")