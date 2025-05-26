from playwright.sync_api import sync_playwright

from reporter import TestStepResult

def run_test_steps(steps, scenario="Unnamed scenario"):
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 720}, device_scale_factor=1
        )
        page = context.new_page()

        for index, step in enumerate(steps):
            step_result = TestStepResult(step=step, status="")
            try:
                action = step.get("action")
                context_data = step.get("context", {})
                print(f"Executing Step {index+1}: {action} -> {context_data}")

                if action in ["go_to", "navigate"]:
                    url = context_data.get("url", "")
                    page.goto(url, wait_until="networkidle")
                    page.wait_for_load_state("load")

                elif action == "login":
                    page.fill("#user-name", context_data.get("username", ""))
                    page.fill("#password", context_data.get("password", ""))
                    page.click("#login-button")
                    page.wait_for_timeout(1000)

                elif action == "add_to_cart":
                    item = context_data.get("item_name", "").lower()
                    if "backpack" in item:
                        page.click("#add-to-cart-sauce-labs-backpack")
                    elif "bike light" in item:
                        page.click("#add-to-cart-sauce-labs-bike-light")
                    else:
                        page.locator("button:has-text('Add to cart')").first.click()

                elif action == "remove_from_cart":
                    item = context_data.get("item_name", "").lower()
                    if "backpack" in item:
                        page.click("#remove-sauce-labs-backpack")
                    elif "bike light" in item:
                        page.click("#remove-sauce-labs-bike-light")

                elif action in ["view_cart", "click_cart_icon"]:
                    page.click(".shopping_cart_link")
                    page.wait_for_timeout(1000)

                elif action in ["verify_items", "verify_cart"]:
                    expected_items = context_data.get("expected_items", [])
                    found_items = page.locator(
                        ".cart_item .inventory_item_name"
                    ).all_text_contents()
                    for item in expected_items:
                        assert item in found_items, f"'{item}' not found in cart"

                step_result.status = "passed"
                print(f"✅ Step {index+1} succeeded")

                if index == len(steps) - 1:
                    page.wait_for_timeout(1000)

            except Exception as e:
                print(f"❌ Step {index+1} failed: {e}")
                step_result.status = "failed"
                step_result.error = str(e)


            results.append(step_result)

        browser.close()
    return results
