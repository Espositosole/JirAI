const JIRA_BOARD_COLUMN_SELECTOR = '.js-column[data-column-name="QA"]';
const AGENT_BACKEND_URL = 'http://localhost:5000/trigger-agent';

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url.includes('atlassian.net')) {
        chrome.tabs.sendMessage(tabId, { action: 'checkQAColumn' });
    }
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'triggerAgent') {
        fetch(AGENT_BACKEND_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                issueKey: request.issueKey
            })
        })
        .then(response => response.json())
        .then(data => {
            console.log('Agent triggered successfully', data);
        })
        .catch(error => {
            console.error('Error triggering agent:', error);
        });
    }
});