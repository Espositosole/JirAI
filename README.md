# JirAI

JirAI is an evolving project that connects Jira, OpenAI and the [`browser-use`](https://github.com/browser-use/browser-use) agent to automatically generate and run end to end test scenarios. It reads user stories from Jira, asks OpenAI to create test flows, executes them with `browser-use` and posts the results back to the Jira issue. What started as an experiment is quickly turning into a helpful assistant for busy QA teams.

## Objective
The goal of this project is to streamline QA efforts by letting an AI system interpret new Jira stories and immediately validate them through automated browser runs. This repository contains the prototype backend used to trigger the process and collect the test results.

## Workflow
1. When a story is moved to **In Progress**, the agent creates a subtask and posts suggested test scenarios for the team to review.
2. Once the story reaches **QA**, those scenarios are executed automatically and the results are posted back to Jira.

## Prerequisites
- Python 3.8 or newer
- Node.js 16+ (required by the `browser-use` CLI)
- A Jira account with API token
- An OpenAI API key
- The `browser-use` command line tool installed and accessible in your `PATH`

You will also need network access to reach Jira, OpenAI and download Python packages and Playwright browser binaries.

## Installation
1. Clone this repository.
2. Create a virtual environment and install Python dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   playwright install
   ```
   The last command downloads the browsers used by Playwright.
3. Install the `browser-use` CLI (requires Node.js):
   ```bash
   npm install -g browser-use
   ```
4. Add a `.env` file in the project root with your credentials:
   ```bash
   JIRA_EMAIL=your-email@example.com
   JIRA_API_TOKEN=your-jira-token
   OPENAI_API_KEY=your-openai-key
   BROWSER_USE_HEADLESS=true
   BROWSER_USE_VIEWPORT_WIDTH=1920
   BROWSER_USE_VIEWPORT_HEIGHT=1080
   ```

## Usage
Start the Flask backend:
```bash
python jira_agent_backend.py
```
The backend now exposes two endpoints:

- `/suggest-scenarios` – generate test scenarios for a Jira issue.
- `/run-tests` – execute previously generated scenarios.

Example request to suggest scenarios:
```bash
curl -X POST http://localhost:5000/suggest-scenarios -H "Content-Type: application/json" -d '{"issueKey": "ABC-123"}'
```
To later run the tests for that issue:
```bash
curl -X POST http://localhost:5000/run-tests -H "Content-Type: application/json" -d '{"issueKey": "ABC-123"}'
```
The agent stores generated flows locally, executes them with `browser-use` once triggered, and posts results back to Jira.

## Running Tests
Unit tests are provided and can be run with `pytest`:
```bash
pytest -q
```

## Next Steps
- Better error handling and retries
- Support for additional test runners
- Automatic scheduling or integration with CI/CD pipelines
- Screenshot capture and attachment to test results

## Acknowledgements
Huge thanks to the **browser-use** team for providing the automation engine that makes these experiments possible.

## Project Structure
- `jira_reader.py` / `jira_writer.py` – helpers for interacting with Jira
- `nlp_parser.py` – prompts OpenAI to generate test steps
- `browser_use_runner_lib.py` – runs the generated flows using `browser-use`
- `jira_agent_backend.py` – Flask server exposing `/suggest-scenarios` and `/run-tests`

## Contributing
Pull requests are welcome! Feel free to open issues or suggestions.

Before submitting a pull request, please make sure that no log files are
included in your commits. The repository's `.gitignore` already excludes `*.log`
files, so double-check `git status` to ensure no logs accidentally slip in.
