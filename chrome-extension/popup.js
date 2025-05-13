document.getElementById('configButton').addEventListener('click', () => {
    chrome.tabs.create({ url: 'options.html' });
});