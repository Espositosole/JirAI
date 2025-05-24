#!/bin/bash

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the server
gunicorn \
    --workers 2 \
    --bind 0.0.0.0:5000 \
    --log-level info \
    --capture-output \
    jira_agent_backend:app