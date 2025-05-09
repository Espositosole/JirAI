import os
import json
import re
import ast
from dotenv import load_dotenv
from openai import OpenAI

from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / "ai-jira-ui-tester/.env"
print("[DEBUG] Using .env path:", env_path)
load_dotenv(dotenv_path=env_path)
print("[DEBUG] Loaded API Key:", os.getenv("OPENAI_API_KEY"))
client = OpenAI(api_key="MYAPIKEY")

SYSTEM_PROMPT = """
You are an expert QA automation assistant. Given a user story, your job is to create multiple structured test flows.

If the story describes only a general scenario, create 2 or 3 realistic flows that test the same feature from different angles.

For each flow, return:
- a 'scenario' name (e.g., "Add one item", "Add multiple items")
- a list of test steps under 'steps'

Each step must include:
- action (e.g., login, add_to_cart, view_cart, verify_items)
- optional context like username, password, item name, or URL

Return a JSON array of objects like:
[
  {
    "scenario": "Add one item",
    "steps": [
      { "action": "navigate", "context": { "url": "..." } },
      { "action": "login", ... },
      { "action": "add_to_cart", ... },
      ...
    ]
  },
  {
    "scenario": "Add multiple items",
    "steps": [
      ...
    ]
  }
]
"""


def extract_test_steps(story):
    USER_PROMPT = f"""
Story:
{story['description']}

If the story doesn't describe test flows clearly, invent 2–3 possible flows that match the feature described.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content
        print("\n[DEBUG] GPT Response:\n", content)

        match = re.search(r"```json\s*(\[.*?\])\s*```", content, re.DOTALL)
        if not match:
            match = re.search(r"\[.*\]", content, re.DOTALL)
        if match:
            json_data = match.group(0)
            try:
                return json.loads(json_data)
            except json.JSONDecodeError:
                return ast.literal_eval(json_data)

        raise ValueError("No valid JSON array found in GPT response")

    except Exception as e:
        print(f"Error parsing test steps: {e}")
        return []
