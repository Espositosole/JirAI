from jira_reader import connect_to_jira
import os

def post_results_to_jira(issue_key, results):
    if issue_key == "DUMMY-123":
        print("[Mock Mode] Skipping Jira comment post.")
        return

    jira = connect_to_jira()
    summary = "### Automated Test Results\n"
    for i, result in enumerate(results):
        step = result["step"]
        status = result["status"]
        screenshot = result.get("screenshot", "")
        error = result.get("error", "")

        summary += f"\n**Step {i+1}: {step.get('action')} - {step.get('target')}**\n"
        summary += f"Status: {status}\n"
        if error:
            summary += f"Error: {error}\n"
        if screenshot and os.path.exists(screenshot):
            with open(screenshot, 'rb') as image_file:
                jira.add_attachment(issue=issue_key, attachment=image_file, filename=screenshot)
            summary += f"Screenshot attached: {screenshot}\n"

    jira.add_comment(issue_key, summary)