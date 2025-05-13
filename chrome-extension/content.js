function checkQAColumn() {
    console.log("[Extension] Checking for QA cards (new layout)...");

    const cards = document.querySelectorAll('[data-testid="platform-board-kit.ui.card.card"]');
    console.log(`[Extension] Found ${cards.length} cards`);

    cards.forEach(card => {
        const columnContainer = card.closest('[data-testid^="platform-board-kit.ui.column"]');
        const columnTitleEl = columnContainer?.querySelector('[data-testid*="column-name"]');
        const columnTitle = columnTitleEl?.textContent?.trim();

        console.log("[Extension] Column title:", columnTitle);

        if (columnTitle === "QA") {
            const issueKey = card.getAttribute("data-issue-key") || card.textContent?.match(/[A-Z]+-\d+/)?.[0];
            console.log("[Extension] Raw issueKey:", issueKey);

            if (issueKey) {
                console.log("[Extension] Found issueKey in QA column:", issueKey);
                chrome.runtime.sendMessage({
                    action: 'triggerAgent',
                    issueKey: issueKey
                });
            } else {
                console.warn("[Extension] No issue key found in card");
            }
        }
    });
}


chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "checkQAColumn") {
        console.log("[Extension] checkQAColumn triggered");
        checkQAColumn();
    }
});

// Auto-trigger when the page loads
window.addEventListener("load", () => {
    console.log("[Extension] Auto-triggering QA column check");
    chrome.runtime.sendMessage({ action: "checkQAColumn" });
});
