import time
import re
from dateutil.parser import parse as parse_date
from jira_reader import connect_to_jira

def post_scenario_suggestions(issue_key: str, scenarios: list[str]):
    jira = connect_to_jira()

    comment = "🧠 Suggested Test Scenarios:\n\n"
    for i, scenario in enumerate(scenarios, start=1):
        comment += f"{i}. {scenario}\n"
    comment += "\n💡 To run selected tests, reply to this issue with:\n"
    comment += "`run 1,3` or `run all`"

    comment_obj = jira.add_comment(issue_key, comment)
    print(f"[JIRA] ✅ Posted scenario suggestions for {issue_key}")
    return comment_obj.created  # Return timestamp

def wait_for_test_selection(issue_key: str, since_time: str, timeout_seconds=300, poll_interval=10):
    jira = connect_to_jira()
    seen_comments = set()
    deadline = time.time() + timeout_seconds

    print(f"[JIRA] 🕒 Waiting for run reply on {issue_key} for up to {timeout_seconds}s...")
    since = parse_date(since_time)

    while time.time() < deadline:
        comments = jira.comments(issue_key)
        for c in comments:
            if parse_date(c.created) <= since or c.id in seen_comments:
                continue
            seen_comments.add(c.id)

            body = c.body.lower().strip()
            if body.startswith("run"):
                print(f"[JIRA] ✅ Found test selection comment: {body}")
                return parse_test_selection(body)

        time.sleep(poll_interval)

    print("[JIRA] ⚠️ No test selection received in time.")
    return []

def parse_test_selection(comment_text: str):
    if "run all" in comment_text:
        return "all"
    match = re.search(r"run\s+([0-9, ]+)", comment_text)
    if match:
        try:
            indexes = [int(i.strip()) - 1 for i in match.group(1).split(",")]
            print(f"[JIRA] 🎯 Parsed selection indexes: {indexes}")
            return indexes
        except ValueError:
            pass
    print("[JIRA] ⚠️ Could not parse selection. Ignoring.")
    return []
