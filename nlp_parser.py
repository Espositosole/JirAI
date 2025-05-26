import os
import json
import re
import ast
from dotenv import load_dotenv
from openai import OpenAI

from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / "ai-jira-ui-tester/.env"
load_dotenv(dotenv_path=env_path, override=True)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
You're a QA automation specialist working with browser-use. 

When I share a Jira user story, analyze it and generate 2-3 automated test scenarios that would thoroughly validate the feature described.

Return ONLY a JSON array containing the test scenarios in this format:
[
  {
    "scenario": "A descriptive test name based on the user story",
    "steps": "Complete natural language instructions for browser-use to execute this test"
  }
]

Your steps should be written as natural language instructions that browser-use can interpret directly. Extract relevant information from the user story (like URLs, user types, expected behaviors) and incorporate them into your test scenarios.

Focus on creating comprehensive test coverage that validates the feature works as described in the user story.
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
