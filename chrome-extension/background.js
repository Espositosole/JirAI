console.log("[Agent] background.js loaded");

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log("[Agent] Received message:", request);  // ✅ Log any incoming message

    if (request.action === "triggerAgent") {
        console.log(`[Agent] Triggering for ${request.issueKey} with status: ${request.status}`);
        fetch("http://localhost:5000/trigger-agent", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                issueKey: request.issueKey,
                status: request.status,
                hasTestedLabel: request.hasTestedLabel || false
            })
        })
        .then(res => res.json())
        .then(data => console.log("[Agent] ✅ Response from server:", data))
        .catch(err => console.error("[Agent] ❌ Error posting to agent:", err));
    }
});
