# JirAI

This project interacts with Jira and OpenAI to generate and manage test cases.
Configuration values are loaded from a `.env` file located in the project root.

## Required environment variables

- `JIRA_EMAIL` – Email address used to authenticate with Jira.
- `JIRA_API_TOKEN` – API token associated with your Jira account.
- `OPENAI_API_KEY` – Key for accessing the OpenAI API.

Create a `.env` file in the repository root with the following structure:

```bash
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your-jira-token
OPENAI_API_KEY=your-openai-key
```