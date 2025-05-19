from datetime import datetime
from dataclasses import asdict, is_dataclass
from jira_reader import connect_to_jira
import os
import zipfile


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
    screenshots_to_zip = []

    for s_idx, (scenario, results) in enumerate(scenario_results, start=1):
        summary += f"\n\n🔹 Scenario {s_idx}: {scenario}"
        scenario_failed = False
        failed_steps = []

        for i, result in enumerate(results, start=1):
            r_dict = asdict(result) if is_dataclass(result) else result
            if r_dict["status"] != "passed":
                failed_steps.append((i, r_dict))
                scenario_failed = True
                all_passed = False

        if scenario_failed:
            for i, result in failed_steps:
                step = result["step"]
                status = result["status"]
                step_name = step.get("description") or step.get("action", f"Step {i}")
                error = result.get("error", "")
                screenshot = result.get("screenshot", "")

                summary += f"\n{i}. *{step_name}*\n"
                summary += f"   - ❌ Status: {status}\n"
                if error:
                    summary += f"   - ❗ Error: {error}\n"
                if screenshot and os.path.exists(screenshot):
                    screenshots_to_zip.append(screenshot)
                    summary += f"   - 📎 Screenshot: `{os.path.basename(screenshot)}`\n"

            summary += "\n❌ Scenario Failed\n"
        else:
            summary += "\n✅ PASSED — all steps succeeded\n"

    zip_filename = f"screenshots/test_results_{issue_key}_{timestamp}.zip"
    if screenshots_to_zip:
        summary += (
            f"\n📦 Screenshots are bundled in `{os.path.basename(zip_filename)}`\n"
        )
        with zipfile.ZipFile(zip_filename, "w") as zipf:
            for file in screenshots_to_zip:
                arcname = os.path.basename(file)
                zipf.write(file, arcname=arcname)

    summary += (
        "\n## ✅ Overall: All Tests Passed\n"
        if all_passed
        else "\n## ⚠️ Overall: Some Tests Failed\n"
    )

    try:
        jira.add_comment(issue_key, summary)
        print(f"[JIRA] ✅ Comment added to {issue_key}")

        if screenshots_to_zip and os.path.exists(zip_filename):
            with open(zip_filename, "rb") as zip_file:
                jira.add_attachment(
                    issue=issue_key,
                    attachment=zip_file,
                    filename=os.path.basename(zip_filename),
                )
            print(f"[JIRA] 📎 Attached ZIP: {zip_filename}")

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

