from datetime import datetime
from browser_use_runner_lib import run_browser_use_test_hybrid
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
    summary = f"Automated Test Report\n"
    summary += f"_Tested on: {timestamp}_\n"

    all_passed = True

    for s_idx, (scenario, results) in enumerate(scenario_results, start=1):
        summary += f"\nScenario {s_idx}: {scenario}\n"
        scenario_passed = all(r["status"] == "passed" for r in results)
        emoji = "✅" if scenario_passed else "❌"
        summary += f"Status: {'passed' if scenario_passed else 'failed'} {emoji}\n"

        # If result_obj contains a 'final_result' field, include it
        final_result = next(
            (r.get("final_result") for r in results if r.get("final_result")), None
        )
        if final_result:
            summary += f"Result: {final_result}\n"

        # Only show steps if it failed
        if not scenario_passed:
            for i, r in enumerate(results, 1):
                step = r["step"]
                desc = step.get("description") or step.get("action", f"Step {i}")
                status = r["status"]
                summary += f"- {desc} → {'✅' if status == 'passed' else '❌'}\n"

        summary += "\n"
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
        "\n✅ Overall: All Tests Passed\n"
        if all_passed
        else "\n⚠️ Overall: Some Tests Failed\n"
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


def format_test_results(
    scenarios: list[dict], runner, subtask_key: str, parent_issue_key: str
):
    """Fixed version that correctly determines scenario success based on the ScenarioResult.success field"""
    from jira_reader import connect_to_jira
    import time

    jira = connect_to_jira()

    # Build simplified results
    all_results = []
    overall_summary = f"Automated Test Execution Report\n"
    overall_summary += (
        f"_Executed on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n\n"
    )

    overall_passed = True

    print(f"[JIRA] Starting test execution for {len(scenarios)} scenarios...")

    for i, scenario_data in enumerate(scenarios, 1):
        name = scenario_data["scenario"]
        context = scenario_data["steps"]

        print(f"[JIRA] Executing scenario {i}/{len(scenarios)}: {name}")

        try:
            # Run the test
            result_obj = runner(context, name)

            # Debug: Print the result_obj structure
            print(f"[DEBUG] Result object type: {type(result_obj)}")
            print(
                f"[DEBUG] Result object attributes: {dir(result_obj) if hasattr(result_obj, '__dict__') else 'N/A'}"
            )
            if hasattr(result_obj, "success"):
                print(f"[DEBUG] Success field value: {result_obj.success}")

            # Handle ScenarioResult object - FIXED LOGIC
            if hasattr(result_obj, "results"):
                scenario_results = result_obj.results
                final_result = (
                    getattr(result_obj, "final_result", None) or "No result available"
                )
            else:
                # Fallback if it's a different structure
                scenario_results = result_obj if isinstance(result_obj, list) else []
                final_result = "No result available"

            # CRITICAL FIX: Check for task completion success in logs
            # The logs show "✅ Task completed successfully" which should indicate success
            scenario_passed = False

            # Method 1: Check the success field if it exists
            if hasattr(result_obj, "success"):
                scenario_passed = result_obj.success
                print(f"[DEBUG] Using success field: {scenario_passed}")

            # Method 2: Check if final result indicates success
            elif final_result and "successfully" in final_result.lower():
                scenario_passed = True
                print(
                    f"[DEBUG] Using final_result success indicator: {scenario_passed}"
                )

            # Method 3: Check if there's a "Task completion" step with "passed" status
            elif scenario_results:
                for step in scenario_results:
                    step_name = getattr(step, "step", "")
                    step_status = getattr(step, "status", "")
                    if "Task completion" in step_name and step_status == "passed":
                        scenario_passed = True
                        print(f"[DEBUG] Found task completion step with passed status")
                        break

            # Method 4: Check logs for task completion indicators
            # This is a fallback that could be implemented if we had access to logs

            print(
                f"[JIRA] ✅ Scenario {i} completed: {name} - {'PASSED' if scenario_passed else 'FAILED'}"
            )

            if not scenario_passed:
                overall_passed = False

            # Build simplified result for this scenario (only name, final result, status)
            status_emoji = "✅" if scenario_passed else "❌"
            scenario_summary = f"**{name}**\n"
            scenario_summary += (
                f"Status: {status_emoji} {'PASSED' if scenario_passed else 'FAILED'}\n"
            )
            scenario_summary += f"Final Result: {final_result}\n\n"

            # Only show failed steps if scenario failed
            if not scenario_passed and scenario_results:
                scenario_summary += "Failed Steps:\n"
                for step in scenario_results:
                    if getattr(step, "status", "") != "passed":
                        step_desc = getattr(step, "step", "Unnamed Step")
                        error_msg = getattr(step, "error", "No error message")
                        scenario_summary += f"- ❌ {step_desc}: {error_msg}\n"
                scenario_summary += "\n"

            # Add to overall summary
            overall_summary += scenario_summary

            all_results.append(
                {"scenario": name, "passed": scenario_passed, "result_obj": result_obj}
            )

        except Exception as e:
            print(f"[JIRA] ❌ Error executing scenario {i}: {str(e)}")
            overall_passed = False

            # Simplified error format
            error_summary = f"**{name}**\n"
            error_summary += f"Status: ❌ EXECUTION ERROR\n"
            error_summary += f"Final Result: {str(e)}\n\n"

            overall_summary += error_summary

            all_results.append({"scenario": name, "passed": False, "error": str(e)})

    # Add final summary
    overall_summary += "---\n"
    overall_summary += f"**Summary:** {'✅ ALL TESTS PASSED' if overall_passed else '⚠️ SOME TESTS FAILED'}\n"
    passed_count = sum(1 for r in all_results if r["passed"])
    overall_summary += f"Total: {len(scenarios)} | Passed: {passed_count} | Failed: {len(scenarios) - passed_count}\n"

    # Post the simplified comment to the subtask
    try:
        print(f"[JIRA] Posting simplified results to subtask {subtask_key}...")
        jira.add_comment(subtask_key, overall_summary)
        print(f"[JIRA] ✅ Simplified results posted to {subtask_key}")

        # Brief delay to ensure comment is posted
        time.sleep(1)

    except Exception as e:
        print(f"[JIRA] ❌ Failed to post results to subtask: {str(e)}")

    # Mention QA user on parent issue
    try:
        qa_user_id = "70121:2fb0d5c3-a6a9-445b-a741-f0a2caf987fe"
        passed_count = sum(1 for r in all_results if r["passed"])
        mention = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "mention",
                            "attrs": {"id": qa_user_id, "text": "<@QA>"},
                        },
                        {
                            "type": "text",
                            "text": f" All test scenarios for {subtask_key} have been executed. "
                            f"Results: {passed_count}/{len(scenarios)} passed. Please review the detailed results in the subtask.",
                        },
                    ],
                }
            ],
        }
        jira._session.post(
            f"{jira._options['server']}/rest/api/3/issue/{parent_issue_key}/comment",
            json={"body": mention},
        )
        print(f"[JIRA] ✅ QA mention posted to parent issue {parent_issue_key}")

    except Exception as e:
        print(f"[JIRA] ⚠️ Failed to mention QA user: {str(e)}")

    return all_results
