from jira_reader import get_user_story
from nlp_parser import extract_test_steps
from test_executor import run_test_steps
from jira_writer import post_results_to_jira

if __name__ == "__main__":
    issue_key = "DUMMY-123"  # Replace with real Jira key if testing live
    story = get_user_story(issue_key)
    print("Extracted Story:\n", story)

    steps = extract_test_steps(story)
    print("\nGenerated Test Steps:")
    for step in steps:
        print(step)

    results = run_test_steps(steps)
    post_results_to_jira(issue_key, results)
