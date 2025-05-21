# JirAI

JirAI is a small experiment that connects Jira, OpenAI and the [`browser-use`](https://github.com/browser-use/browser-use) agent to automatically generate and run end to end test scenarios. It reads user stories from Jira, asks OpenAI to create test flows, executes them with `browser-use` and posts the results back to the Jira issue.

## Objective
The goal of this project is to streamline QA efforts by letting an AI system interpret new Jira stories and immediately validate them through automated browser runs. This repository contains the prototype backend used to trigger the process and collect the test results.

## Prerequisites
- Python 3.8 or newer
- A Jira account with API token
- An OpenAI API key
- The `browser-use` command line tool installed and accessible in your `PATH`

You will also need network access to reach Jira, OpenAI and download Python packages.

## Installation
1. Clone this repository.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Add a `.env` file in the project root with your credentials:
   ```bash
   JIRA_EMAIL=your-email@example.com
   JIRA_API_TOKEN=your-jira-token
   OPENAI_API_KEY=your-openai-key
   ```
4. Make sure the `browser-use` executable is installed. See the [browser-use project](https://github.com/browser-use/browser-use) for installation instructions.

## Usage
Start the Flask backend:
```bash
python jira_agent_backend.py
```
This exposes a `/trigger-agent` endpoint. Send a POST request containing the Jira issue key to run the agent:
```bash
curl -X POST http://localhost:5000/trigger-agent -H "Content-Type: application/json" -d '{"issueKey": "ABC-123"}'
```
The agent will parse the issue, generate test flows and execute them with `browser-use`. Logs are stored locally and the results are posted back to Jira.

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
- `browser_use_runner.py` – runs the generated flows using `browser-use`
- `jira_agent_backend.py` – Flask server exposing the `/trigger-agent` route

## Contributing
Pull requests are welcome! Feel free to open issues or suggestions.
