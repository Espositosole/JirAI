from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
import logging
from threading import Lock
from jira_reader import get_user_story, get_issue_labels, connect_to_jira
from nlp_parser import extract_test_steps
from jira_writer import post_results_to_jira
from browser_use_runner_lib import run_browser_use_test_hybrid
from jira_test_selector import post_scenario_suggestions, wait_for_test_selection

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

            if not issue_key:
                logger.error("No issue key provided")
                return (
                    jsonify({"status": "error", "message": "Issue key is required"}),
                    400,
                )

            logger.info(f"Triggering agent for issue: {issue_key}")

            jira = connect_to_jira()
            issue = jira.issue(issue_key)
            labels = issue.fields.labels

            if "auto-tested" in labels:
                logger.info(
                    f"Issue {issue_key} already has auto-tested label, skipping test"
                )
                return jsonify(
                    {
                        "status": "skipped",
                        "issue_key": issue_key,
                        "message": "Issue already tested",
                    }
                )

            story = get_user_story(issue_key)
            logger.info(f"Story fetched: {story}")

            flows = extract_test_steps(story)
            if isinstance(flows, list) and all(
                isinstance(s, dict) and "action" in s for s in flows
            ):
                flows = [{"scenario": "Unnamed scenario", "steps": flows}]

            logger.info(f"Generated {len(flows)} test scenarios")

            # ✅ POST SUGGESTIONS
            scenario_titles = [
                f.get("scenario", f"Scenario {i+1}") for i, f in enumerate(flows)
            ]
            post_scenario_suggestions(issue_key, scenario_titles)

            # ✅ WAIT FOR SELECTION
            selection = wait_for_test_selection(issue_key)
            if selection == []:
                try:
                    # Remove label
                    current_issue = connect_to_jira().issue(issue_key)
                    labels = current_issue.fields.labels or []
                    if "testing-in-progress" in labels:
                        labels.remove("testing-in-progress")
                        current_issue.update(fields={"labels": labels})
                        print(
                            f"[JIRA] 🗑️ Removed 'testing-in-progress' label due to timeout"
                        )

                    # Post comment
                    jira.add_comment(
                        issue_key,
                        "⏳ No test selection was received within 5 minutes. You can retrigger this test by moving the issue back into the QA column.",
                    )
                except Exception as e:
                    print(
                        f"[JIRA] ⚠️ Could not update label or comment after timeout: {e}"
                    )

                return jsonify(
                    {
                        "status": "skipped",
                        "issue_key": issue_key,
                        "message": "No test selection received",
                    }
                )
            if selection != "all":
                flows = [flows[i] for i in selection]

            # Add "testing-in-progress" label
            try:
                current_issue = connect_to_jira().issue(issue_key)
                labels = current_issue.fields.labels or []
                if "testing-in-progress" not in labels:
                    labels.append("testing-in-progress")
                    current_issue.update(fields={"labels": labels})
                    logger.info(
                        f"[JIRA] Added 'testing-in-progress' label to {issue_key}"
                    )
            except Exception as e:
                logger.warning(f"[JIRA] Could not add 'testing-in-progress' label: {e}")

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
            logger.info(f"Results posted to Jira for issue: {issue_key}")

            scenario_results_json = []
            for scenario, results in scenario_results:
                scenario_results_json.append(
                    (
                        scenario,
                        [r.to_dict() if hasattr(r, "to_dict") else r for r in results],
                    )
                )

            return jsonify(
                {
                    "status": "success",
                    "issue_key": issue_key,
                    "scenarios_tested": len(flows),
                    "results": scenario_results_json,
                }
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
