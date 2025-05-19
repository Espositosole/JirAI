from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
import logging
from jira_reader import get_user_story, get_issue_labels, connect_to_jira
from nlp_parser import extract_test_steps
from test_executor import run_test_steps
from jira_writer import post_results_to_jira
from browser_use_runner import run_browser_use_test

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
CORS(app)  # Enable CORS for all routes


@app.route("/trigger-agent", methods=["POST"])
def trigger_agent():
    try:
        data = request.json
        issue_key = data.get("issueKey")

        if not issue_key:
            logger.error("No issue key provided")
            return jsonify({"status": "error", "message": "Issue key is required"}), 400

        logger.info(f"Triggering agent for issue: {issue_key}")

        # Check if the issue already has the auto-tested label
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

        # Fetch the user story from Jira
        story = get_user_story(issue_key)
        logger.info(f"Story fetched: {story}")

        # Add testing-in-progress label
        try:
            current_issue = connect_to_jira().issue(issue_key)
            labels = current_issue.fields.labels or []
            if "testing-in-progress" not in labels:
                labels.append("testing-in-progress")
                current_issue.update(fields={"labels": labels})
                logger.info(f"[JIRA] Added 'testing-in-progress' label to {issue_key}")
        except Exception as e:
            logger.warning(f"[JIRA] Could not add 'testing-in-progress' label: {e}")

        # Generate test flows from GPT
        flows = extract_test_steps(story)

        # Normalize structure: wrap flat list of steps if needed
        if isinstance(flows, list) and all(
            isinstance(s, dict) and "action" in s for s in flows
        ):
            flows = [{"scenario": "Unnamed scenario", "steps": flows}]

        logger.info(f"Generated {len(flows)} test scenarios")

        scenario_results = []

        for flow in flows:
            scenario = flow.get("scenario", "Unnamed scenario")
            raw_steps = flow.get("steps", [])

            if isinstance(raw_steps, str):
                raw_steps = [raw_steps]
            
            logger.info(f"Running scenario: {scenario}")
            results = run_browser_use_test(raw_steps, scenario_name=scenario)
            scenario_results.append((scenario, results))

        # Post all results to Jira in one comment
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
