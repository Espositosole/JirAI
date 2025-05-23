from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
import logging
from threading import Lock
from jira_reader import get_user_story, connect_to_jira
from nlp_parser import extract_test_steps
from jira_writer import post_results_to_jira
from browser_use_runner_lib import run_browser_use_test_hybrid
from jira_test_selector import post_scenario_suggestions, wait_for_test_selection
from scenario_tracker import (
    save_selection,
    get_selection,
    mark_suggestions_posted,
    has_suggestions_been_posted,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("jira_agent_backend.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

agent_lock = Lock()


@app.route("/trigger-agent", methods=["POST"])
def trigger_agent():
    with agent_lock:
        try:
            data = request.json
            issue_key = data.get("issueKey")
            status = data.get("status", "").lower()

            if not issue_key:
                return (
                    jsonify({"status": "error", "message": "Issue key is required"}),
                    400,
                )

            logger.info(f"Triggering agent for issue: {issue_key} [status: {status}]")
            story = get_user_story(issue_key)
            logger.info(f"Story fetched: {story}")

            flows = extract_test_steps(story)
            if isinstance(flows, list) and all(
                isinstance(s, dict) and "action" in s for s in flows
            ):
                flows = [{"scenario": "Unnamed scenario", "steps": flows}]

            logger.info(f"Generated {len(flows)} test scenarios")

            if status == "in progress":
                if not has_suggestions_been_posted(issue_key):
                    scenario_titles = [
                        f.get("scenario", f"Scenario {i+1}")
                        for i, f in enumerate(flows)
                    ]
                    suggested_time = post_scenario_suggestions(
                        issue_key, scenario_titles
                    )
                    selection, _ = wait_for_test_selection(
                        issue_key, since_time=suggested_time
                    )

                    if selection:
                        save_selection(issue_key, selection)
                        mark_suggestions_posted(issue_key)

                        try:
                            jira = connect_to_jira()
                            issue = jira.issue(issue_key)
                            labels = issue.fields.labels or []
                            if "scenarios-selected" not in labels:
                                labels.append("scenarios-selected")
                            issue.update(fields={"labels": labels})
                            logger.info(
                                f"[JIRA] 🏷️ Added 'scenarios-selected' label to {issue_key}"
                            )
                        except Exception as e:
                            if "409" in str(e):
                                logger.warning(
                                    "[JIRA] Conflict updating 'scenarios-selected'. Retrying..."
                                )
                                issue = jira.issue(issue_key)
                                labels = issue.fields.labels or []
                                if "scenarios-selected" not in labels:
                                    labels.append("scenarios-selected")
                                issue.update(fields={"labels": labels})
                            else:
                                raise

                return jsonify({"status": "suggested", "issue_key": issue_key})

            if status == "qa":
                selection = get_selection(issue_key)
                if selection is None:
                    logger.warning(f"No saved selection for {issue_key}, skipping.")
                    return jsonify(
                        {"status": "skipped", "reason": "No selection stored"}
                    )

                if selection != "all":
                    flows = [flows[i] for i in selection]

                # ✅ Safe label update with 409 retry
                try:
                    jira = connect_to_jira()
                    current_issue = jira.issue(issue_key)
                    labels = current_issue.fields.labels or []

                    if "scenarios-selected" in labels:
                        labels.remove("scenarios-selected")
                        logger.info(
                            f"[JIRA] 🧹 Removed 'scenarios-selected' label from {issue_key}"
                        )

                    if "testing-in-progress" not in labels:
                        labels.append("testing-in-progress")

                    try:
                        current_issue.update(fields={"labels": labels})
                    except Exception as e:
                        if "409" in str(e):
                            logger.warning(
                                "[JIRA] Conflict updating QA labels. Retrying..."
                            )
                            current_issue = jira.issue(issue_key)
                            labels = current_issue.fields.labels or []
                            if "scenarios-selected" in labels:
                                labels.remove("scenarios-selected")
                            if "testing-in-progress" not in labels:
                                labels.append("testing-in-progress")
                            current_issue.update(fields={"labels": labels})
                        else:
                            raise

                except Exception as e:
                    logger.warning(f"[JIRA] Could not update labels: {e}")

                scenario_results = []

                for flow in flows:
                    scenario = flow.get("scenario", "Unnamed scenario")
                    raw_steps = flow.get("steps", [])
                    if isinstance(raw_steps, str):
                        raw_steps = [raw_steps]

                    logger.info(f"Running scenario: {scenario}")
                    steps_prompt = "\n".join(
                        (
                            s
                            if isinstance(s, str)
                            else s.get("description") or s.get("action", "")
                        )
                        for s in raw_steps
                    )
                    result_obj = run_browser_use_test_hybrid(steps_prompt, scenario)

                    results = [
                        {
                            "step": {"description": r.step},
                            "status": r.status,
                            "error": r.error,
                            "screenshot": None,
                        }
                        for r in result_obj.results
                    ]
                    scenario_results.append((scenario, results))

                post_results_to_jira(issue_key, scenario_results)
                logger.info(f"✅ Results posted to Jira for issue: {issue_key}")

                return jsonify(
                    {
                        "status": "success",
                        "issue_key": issue_key,
                        "scenarios_tested": len(flows),
                    }
                )

            return jsonify(
                {"status": "ignored", "reason": f"Unhandled status: {status}"}
            )

        except Exception as e:
            logger.error(f"Error in agent execution: {str(e)}", exc_info=True)
            return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "version": "1.0.0"})


def run_server(host="0.0.0.0", port=5000):
    logger.info(f"Starting Jira Agent Backend on {host}:{port}")
    app.run(host=host, port=port, debug=True)


if __name__ == "__main__":
    run_server()
