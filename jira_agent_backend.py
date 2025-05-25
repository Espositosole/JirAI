
from jira_writer import format_test_results
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import sys
from jira_reader import get_user_story, connect_to_jira
from nlp_parser import extract_test_steps
from browser_use_runner_lib import run_browser_use_test_hybrid
from subtask_manager import (
    create_subtask_with_steps,
    get_subtask_with_label,
    add_label,
    remove_label,
    transition_subtask_to_done,
)

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

# Runtime memory lock to avoid concurrent processing
recent_issues = set()

@app.route("/suggest-scenarios", methods=["POST"])
def suggest_scenarios():
    data = request.json
    issue_key = data.get("issueKey")
    if not issue_key:
        return jsonify({"status": "error", "message": "issueKey required"}), 400

    global recent_issues
    if issue_key in recent_issues:
        return jsonify({"status": "skipped", "message": "Already being processed"}), 200

    recent_issues.add(issue_key)
    try:
        story = get_user_story(issue_key)
        scenarios = extract_test_steps(story)

        seen = set()
        unique_scenarios = []
        for s in scenarios:
            key = s["scenario"].strip().lower()
            if key not in seen:
                seen.add(key)
                unique_scenarios.append(s)
        scenarios = unique_scenarios

        if isinstance(scenarios, list) and all("action" in s for s in scenarios):
            scenarios = [{"scenario": "Unnamed scenario", "steps": scenarios}]

        summary = "Suggested Test Scenarios"
        desc = "The following scenarios are generated for testing this story:\n\n"
        for idx, s in enumerate(scenarios, 1):
            desc += f"{idx}. {s['scenario']}\n"

        existing = get_subtask_with_label(issue_key, "scenarios-generated")
        if existing:
            logger.info(f"[JIRA] Subtask already exists for {issue_key}: {existing.key}")
            return jsonify({"status": "skipped", "subtask": existing.key})

        add_label(issue_key, "scenarios-generated")
        subtask_key = create_subtask_with_steps(issue_key, summary, desc)

        qa_user_id = "70121:2fb0d5c3-a6a9-445b-a741-f0a2caf987fe"
        jira = connect_to_jira()
        resp = jira._session.put(
            f"{jira._options['server']}/rest/api/3/issue/{subtask_key}/assignee",
            json={"accountId": qa_user_id},
        )
        print(f"[DEBUG] Assign issue response: {resp.status_code} - {resp.text}")
        print(f"[JIRA] 👤 Assigned subtask {subtask_key} to QA user.")

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
                            "text": f" Suggested test scenarios have been created in {subtask_key}. Please review or edit before moving to QA.",
                        },
                    ],
                }
            ],
        }
        jira._session.post(
            f"{jira._options['server']}/rest/api/3/issue/{issue_key}/comment",
            json={"body": mention},
        )

        return jsonify({"status": "success", "subtask": subtask_key, "scenarios": len(scenarios)})

    except Exception as e:
        logger.error(f"Error in /suggest-scenarios: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        recent_issues.discard(issue_key)


@app.route("/run-tests", methods=["POST"])
def run_tests():
    data = request.json
    issue_key = data.get("issueKey")
    if not issue_key:
        return jsonify({"status": "error", "message": "issueKey required"}), 400

    global recent_issues
    if issue_key in recent_issues:
        return jsonify({"status": "skipped", "message": "Tests already running"}), 200

    recent_issues.add(issue_key)
    try:
        subtask = get_subtask_with_label(issue_key, "scenarios-generated")
        if not subtask:
            return jsonify({"status": "skipped", "message": "No test subtask found."}), 200
        
        if subtask.fields.status.name.lower() == "done":
            return jsonify({"status": "skipped", "message": "Test subtask is already marked as Done."}), 200

        story = get_user_story(issue_key)
        context = story["description"]
        subtask_description = subtask.fields.description

        import re
        raw_steps = re.findall(r"\d+\.\s+(.*)", subtask_description.strip())
        scenarios = [
            {"scenario": f"Scenario {i}", "steps": f"{context}\n\n{step}"}
            for i, step in enumerate(raw_steps, 1)
            if step.strip()
        ]

        format_test_results(scenarios, run_browser_use_test_hybrid, subtask.key, issue_key)

        remove_label(issue_key, "scenarios-selected")
        add_label(issue_key, "auto-tested")
        remove_label(issue_key, "testing-in-progress")
        remove_label(issue_key, "scenarios-generated")

        transition_subtask_to_done(subtask.key)

        return jsonify({"status": "completed", "subtask": subtask.key, "results": len(scenarios)})

    except Exception as e:
        logger.error(f"Error in /run-tests: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        recent_issues.discard(issue_key)


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "version": "2.0.0"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
