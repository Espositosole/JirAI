document.getElementById('saveSettings').addEventListener('click', () => {
    const backendUrl = document.getElementById('backendUrl').value;
    const jiraDomain = document.getElementById('jiraDomain').value;
    
    chrome.storage.sync.set({
        backendUrl: backendUrl,
        jiraDomain: jiraDomain
    }, () => {
        alert('Settings saved successfully!');
    });
});

// Load saved settings on page load
chrome.storage.sync.get(['backendUrl', 'jiraDomain'], (result) => {
    if (result.backendUrl) {
        document.getElementById('backendUrl').value = result.backendUrl;
    }
    if (result.jiraDomain) {
        document.getElementById('jiraDomain').value = result.jiraDomain;
    }
});