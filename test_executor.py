from playwright.sync_api import sync_playwright
import time
import os


def run_test_steps(steps):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        for index, step in enumerate(steps):
            step_result = {"step": step, "status": "", "screenshot": ""}
            try:
                action = step.get("action")
                target = step.get("target")
                element_type = step.get("element_type")
                expected = step.get("expected")
                value = step.get("value") or step.get("expected")

                print(f"Executing Step {index+1}: {action} -> {target}")

                if action == "go_to":
                    page.goto(target)
                    time.sleep(2)
                elif action == "click":
                    if target.lower() == "login":
                        page.click("#login-button")
                    elif "cart" in target.lower():
                        try:
                            page.click("#shopping_cart_container")
                        except:
                            page.locator("a.shopping_cart_link").click()
                    elif "add to cart" in target.lower():
                        try:
                            page.click("#add-to-cart-sauce-labs-backpack")
                        except:
                            page.locator("button:has-text('Add to cart')").first.click()
                    else:
                        page.locator(f"text={target}").first.click()
                    time.sleep(1)
                elif action == "input":
                    if "username" in target.lower():
                        page.fill("#user-name", value)
                    elif "password" in target.lower():
                        page.fill("#password", value)
                    else:
                        page.fill("input", value)
                elif action == "assert":
                    if target.lower() == "item" or (
                        element_type and "cart" in element_type.lower()
                    ):
                        page.wait_for_timeout(1000)  # wait briefly for UI to render
                        page.wait_for_selector(
                            "#cart_contents_container .cart_list .cart_item .cart_quantity",
                            timeout=5000,
                        )
                        quantity = page.locator(
                            "#cart_contents_container .cart_list .cart_item .cart_quantity"
                        ).first.inner_text()
                        assert (
                            quantity.strip() == "1"
                        ), f"Expected 1 item in cart, but found {quantity.strip()}"
                    else:
                        assert page.get_by_text(
                            target
                        ).is_visible(), f"Assertion failed: {target} not visible"

                screenshot_path = f"screenshot_step_{index+1}.png"
                time.sleep(1)
                page.screenshot(path=screenshot_path)
                print(
                    f"✅ Step {index+1} succeeded, screenshot saved to {screenshot_path}"
                )
                step_result["status"] = "passed"
                step_result["screenshot"] = screenshot_path

            except Exception as e:
                print(f"❌ Step {index+1} failed: {e}")
                step_result["status"] = "failed"
                step_result["error"] = str(e)

            results.append(step_result)

        browser.close()
    return results
