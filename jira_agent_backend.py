from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
import json
import logging
from pathlib import Path
from threading import Lock
from jira_reader import get_user_story, connect_to_jira
from nlp_parser import extract_test_steps
from jira_writer import post_results_to_jira
from browser_use_runner_lib import run_browser_use_test_hybrid
from jira_writer import (
    post_results_to_jira,
    create_subtask_with_scenarios,
    read_scenarios_from_subtask,
)
from browser_use_runner_lib import run_browser_use_test_hybrid
# Legacy functions from the old interactive workflow are still available in
# jira_test_selector, but the subtask-based flow does not require them here.

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
PENDING_DIR = Path("pending_tests")
PENDING_DIR.mkdir(exist_ok=True)


@app.route("/suggest-scenarios", methods=["POST"])
def suggest_scenarios():
    with agent_lock:
        try:
            data = request.json
            issue_key = data.get("issueKey")

            if not issue_key:
                logger.error("No issue key provided")
                return jsonify({"status": "error", "message": "Issue key is required"}), 400

            logger.info(f"Suggesting scenarios for issue: {issue_key}")

            story = get_user_story(issue_key)
            flows = extract_test_steps(story)
            if isinstance(flows, list) and all(isinstance(s, dict) and "action" in s for s in flows):
                flows = [{"scenario": "Unnamed scenario", "steps": flows}]

            subtask_key = create_subtask_with_scenarios(issue_key, flows)

            data_file = PENDING_DIR / f"{issue_key}.json"
            with open(data_file, "w") as f:
                json.dump({"subtask_key": subtask_key}, f)

            return jsonify({"status": "subtask_created", "issue_key": issue_key, "subtask_key": subtask_key})
        except Exception as e:
            logger.error(f"Error suggesting scenarios: {e}", exc_info=True)
            return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/run-tests", methods=["POST"])
def run_tests():
    with agent_lock:
        try:
            data = request.json
            issue_key = data.get("issueKey")

            if not issue_key:
                logger.error("No issue key provided")
                return jsonify({"status": "error", "message": "Issue key is required"}), 400

            logger.info(f"Running stored tests for issue: {issue_key}")

            data_file = PENDING_DIR / f"{issue_key}.json"
            if not data_file.exists():
                logger.error("No stored scenarios for this issue")
                return jsonify({"status": "error", "message": "No stored scenarios"}), 400

            with open(data_file) as f:
                info = json.load(f)

            subtask_key = info.get("subtask_key")
            if not subtask_key:
                logger.error("No subtask key stored for this issue")
                return jsonify({"status": "error", "message": "No subtask key"}), 400

            flows = read_scenarios_from_subtask(subtask_key)
            if not flows:
                logger.error("No scenarios found in subtask")
                return jsonify({"status": "error", "message": "No scenarios found"}), 400

            # Add "testing-in-progress" label
            try:
                current_issue = connect_to_jira().issue(issue_key)
                labels = current_issue.fields.labels or []
                if "testing-in-progress" not in labels:
                    labels.append("testing-in-progress")
                    current_issue.update(fields={"labels": labels})
                    logger.info(f"[JIRA] Added 'testing-in-progress' label to {issue_key}")
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
                    s if isinstance(s, str) else s.get("description") or s.get("action", "")
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

            post_results_to_jira(subtask_key, scenario_results, parent_issue_key=issue_key)
            logger.info(f"Results posted to Jira subtask: {subtask_key}")

            data_file.unlink(missing_ok=True)

            scenario_results_json = []
            for scenario, results in scenario_results:
                scenario_results_json.append(
                    (
                        scenario,
                        [r.to_dict() if hasattr(r, "to_dict") else r for r in results],
                    )
                )

            return jsonify({"status": "success", "issue_key": issue_key, "subtask_key": subtask_key, "scenarios_tested": len(flows), "results": scenario_results_json})
        except Exception as e:
            logger.error(f"Error running stored tests: {e}", exc_info=True)
            return jsonify({"status": "error", "message": str(e)}), 500

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

            subtask_key = create_subtask_with_scenarios(issue_key, flows)

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

            flows = read_scenarios_from_subtask(subtask_key)

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

            post_results_to_jira(subtask_key, scenario_results, parent_issue_key=issue_key)
            logger.info(f"Results posted to Jira subtask: {subtask_key}")

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
                    "subtask_key": subtask_key,
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
