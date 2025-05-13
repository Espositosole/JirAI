from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
import logging
from main import get_user_story, extract_test_steps, run_test_steps, post_results_to_jira

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler('jira_agent_backend.log'),
                        logging.StreamHandler(sys.stdout)
                    ])
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/trigger-agent', methods=['POST'])
def trigger_agent():
    try:
        # Extract issue key from the request
        data = request.json
        issue_key = data.get('issueKey')
        
        if not issue_key:
            logger.error("No issue key provided")
            return jsonify({
                "status": "error",
                "message": "Issue key is required"
            }), 400
        
        logger.info(f"Triggering agent for issue: {issue_key}")
        
        # Fetch user story
        story = get_user_story(issue_key)
        logger.info(f"Story fetched: {story}")
        
        # Generate test steps
        steps = extract_test_steps(story)
        logger.info(f"Generated {len(steps)} test steps")
        
        # Run test steps
        results = run_test_steps(steps)
        logger.info(f"Test execution completed with {len(results)} results")
        
        # Post results to Jira
        post_results_to_jira(issue_key, results)
        logger.info(f"Results posted to Jira for issue: {issue_key}")
        
        return jsonify({
            "status": "success",
            "issue_key": issue_key,
            "steps_executed": len(steps),
            "results": results
        })
    
    except Exception as e:
        logger.error(f"Error in agent execution: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "version": "1.0.0"
    })

def run_server(host='0.0.0.0', port=5000):
    logger.info(f"Starting Jira Agent Backend on {host}:{port}")
    app.run(host=host, port=port, debug=True)

if __name__ == '__main__':
    run_server()