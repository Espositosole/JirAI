from jira import JIRA
import os
from dotenv import load_dotenv
import json

from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / "ai-jira-ui-tester/.env"
load_dotenv(dotenv_path=env_path)


def connect_to_jira():
    jira_options = {"server": f"https://{os.getenv('JIRA_DOMAIN')}"}
    jira = JIRA(
        options=jira_options,
        basic_auth=(os.getenv("JIRA_EMAIL"), os.getenv("JIRA_API_TOKEN")),
    )
    return jira


def get_user_story(issue_key):
    if issue_key == "DUMMY-123":
        with open("tests/dummy_story.json", "r", encoding="utf-8") as f:
            return json.load(f)

    jira = connect_to_jira()
    issue = jira.issue(issue_key)
    story = {
        "key": issue.key,
        "summary": issue.fields.summary,
        "description": issue.fields.description,
        "customfields": {
            "url": extract_url(issue.fields.description),
            "steps": extract_steps(issue.fields.description),
        },
    }
    return story


def extract_url(description):
    for line in description.split("\n"):
        if "http" in line:
            return line.strip()
    return None


def extract_steps(description):
    steps = []
    capture = False
    for line in description.split("\n"):
        if "steps" in line.lower():
            capture = True
        elif capture and line.strip():
            steps.append(line.strip())
    return steps
