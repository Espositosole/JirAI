from jira_reader import get_stories_by_status
from nlp_parser import extract_test_steps
from executor import run_test_steps
from jira_writer import post_results_to_jira

if __name__ == "__main__":
    # Replace with your actual Jira project key
    stories = get_stories_by_status(project_key="JAI", status_name="QA")

    for story in stories:
        print(f"\nProcessing {story['key']} — {story['summary']}")
        steps = extract_test_steps(story)
        flows = steps.get(
            "flows", []
        )  # Assuming "flows" is part of the extracted steps

        scenario_results = []
        for flow in flows:
            scenario = flow.get("scenario", "Unnamed scenario")
            results = run_test_steps(flow.get("steps", []), scenario=scenario)
            scenario_results.append((scenario, results))

        post_results_to_jira(story["key"], scenario_results)
