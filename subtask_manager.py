from jira_reader import connect_to_jira


def create_subtask_with_steps(
    parent_key: str, summary: str, description: str, label: str = "scenarios-generated"
):
    jira = connect_to_jira()
    parent = jira.issue(parent_key)
    project_key = parent.fields.project.key

    # ✅ Hardcoded Subtask ID
    subtask_type_id = "10002"

    issue_dict = {
        "project": {"key": project_key},
        "summary": summary,
        "description": description,
        "issuetype": {"id": subtask_type_id},
        "parent": {"key": parent_key},
        "labels": [label],
    }

    new_issue = jira.create_issue(fields=issue_dict)
    print(f"[JIRA] ✅ Created subtask {new_issue.key} under {parent_key}")
    return new_issue.key


def get_subtask_with_label(parent_key: str, label: str):
    jira = connect_to_jira()
    jql = (
        f"parent = {parent_key} "
        f"AND issuetype in subTaskIssueTypes() "
        f'AND summary ~ "Suggested Test Scenarios"'
    )
    issues = jira.search_issues(jql)
    return issues[0] if issues else None


def add_label(issue_key: str, label: str):
    jira = connect_to_jira()
    issue = jira.issue(issue_key)
    labels = issue.fields.labels or []
    if label not in labels:
        labels.append(label)
        issue.update(fields={"labels": labels})
        print(f"[JIRA] 🏷️ Added label '{label}' to {issue_key}")


def remove_label(issue_key: str, label: str):
    jira = connect_to_jira()
    issue = jira.issue(issue_key)
    labels = issue.fields.labels or []
    if label in labels:
        labels.remove(label)
        issue.update(fields={"labels": labels})
        print(f"[JIRA] 🧹 Removed label '{label}' from {issue_key}")


def transition_subtask_to_done(issue_key: str):
    jira = connect_to_jira()
    transitions = jira.transitions(issue_key)
    for t in transitions:
        if "done" in t["name"].lower():
            jira.transition_issue(issue_key, t["id"])
            print(f"[JIRA] ✅ Transitioned {issue_key} to Done")
            return True
    print(f"[JIRA] ⚠️ No 'Done' transition found for {issue_key}")
    return False
