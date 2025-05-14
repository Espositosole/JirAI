from jira import JIRA
import os
from dotenv import load_dotenv
import json
from pathlib import Path

# Load environment variables from .env
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


# Connect to Jira
def connect_to_jira():
    jira_options = {"server": "https://agentjirai.atlassian.net"}
    print(jira_options)
    jira = JIRA(
        options=jira_options,
        basic_auth=(os.getenv("JIRA_EMAIL"), os.getenv("JIRA_API_TOKEN")),
    )
    return jira


# Extract first URL from story description
def extract_url(description):
    for line in description.split("\n"):
        if "http" in line:
            return line.strip()
    return None


# Extract raw steps listed under a "steps" heading in the story
def extract_steps(description):
    steps = []
    capture = False
    for line in description.split("\n"):
        if "steps" in line.lower():
            capture = True
        elif capture and line.strip():
            steps.append(line.strip())
    return steps


# Get all stories in a specific Jira project/status (e.g., QA column)
def get_stories_by_status(project_key, status_name):
    jira = connect_to_jira()
    jql = (
        f'project = "{project_key}" AND status = "{status_name}" AND issuetype = Story'
    )
    issues = jira.search_issues(jql, maxResults=20)
    stories = []
    for issue in issues:
        stories.append(
            {
                "key": issue.key,
                "summary": issue.fields.summary,
                "description": issue.fields.description,
                "labels": issue.fields.labels,  # Include labels in returned data
                "customfields": {
                    "url": extract_url(issue.fields.description),
                    "steps": extract_steps(issue.fields.description),
                },
            }
        )
    return stories


# Get issue labels
def get_issue_labels(issue_key):
    jira = connect_to_jira()
    issue = jira.issue(issue_key)
    return issue.fields.labels


# For testing: print stories in QA column
if __name__ == "__main__":
    issues = get_stories_by_status(
        "JAI", "QA"
    )  # Replace with your project key and QA column name
    for i in issues:
        print(i["key"], "-", i["summary"], "Labels:", i.get("labels", []))


def get_user_story(issue_key):
    jira = connect_to_jira()
    issue = jira.issue(issue_key)
    story = {
        "key": issue.key,
        "summary": issue.fields.summary,
        "description": issue.fields.description,
        "labels": issue.fields.labels,  # Include labels in returned data
        "customfields": {
            "url": extract_url(issue.fields.description),
            "steps": extract_steps(issue.fields.description),
        },
    }
    return story
