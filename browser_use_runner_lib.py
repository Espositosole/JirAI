import asyncio
import time
import nest_asyncio
from pydantic import BaseModel
from browser_use import Agent, Controller
from langchain_openai import ChatOpenAI
from openai import RateLimitError
import logging
import io
import sys

nest_asyncio.apply()

# Configure logging for better debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StepResult(BaseModel):
    step: str
    status: str
    error: str | None = None


class ScenarioResult(BaseModel):
    scenario: str
    results: list[StepResult]
    final_result: str | None = None
    execution_time: float | None = None
    success: bool = False


class LogCapture:
    """Capture logs during agent execution"""

    def __init__(self):
        self.logs = []
        self.handler = None

    def __enter__(self):
        # Create a custom log handler to capture logs
        self.handler = logging.StreamHandler(io.StringIO())
        self.handler.setLevel(logging.INFO)

        # Add handler to capture logs from browser_use components
        loggers_to_capture = [
            "agent",
            "controller",
            "browser",
            "browser_use_runner_lib",
        ]

        self.original_handlers = {}
        for logger_name in loggers_to_capture:
            log = logging.getLogger(logger_name)
            self.original_handlers[logger_name] = log.handlers.copy()
            log.addHandler(self.handler)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original handlers
        for logger_name, handlers in self.original_handlers.items():
            log = logging.getLogger(logger_name)
            log.removeHandler(self.handler)

        # Get captured logs
        if self.handler and hasattr(self.handler.stream, "getvalue"):
            self.logs = self.handler.stream.getvalue().split("\n")

    def get_logs(self):
        return self.logs


def parse_agent_logs(logs: list[str], scenario: str) -> tuple[list[StepResult], str]:
    """Parse agent execution logs to extract detailed steps and final result"""
    results = []
    final_result = None
    current_step = None
    step_counter = 1

    for log_line in logs:
        if not log_line.strip():
            continue

        # Extract step information
        if "📍 Step" in log_line and "Evaluating page" in log_line:
            # New step detected
            if "Step" in log_line:
                try:
                    step_num = log_line.split("📍 Step ")[1].split(":")[0]
                    current_step = f"Step {step_num}"
                except:
                    current_step = f"Step {step_counter}"
                    step_counter += 1

        elif "📍 Step" in log_line and "Ran" in log_line:
            # Step completion with results
            try:
                if "✅" in log_line:
                    action_count = (
                        log_line.split("✅ ")[1].split()[0] if "✅" in log_line else "1"
                    )
                    step_name = current_step or f"Step {step_counter}"
                    results.append(
                        StepResult(
                            step=f"{step_name}: Executed {action_count} action(s)",
                            status="passed",
                            error=None,
                        )
                    )
                elif "❌" in log_line:
                    step_name = current_step or f"Step {step_counter}"
                    results.append(
                        StepResult(
                            step=f"{step_name}: Failed execution",
                            status="failed",
                            error="Step execution failed",
                        )
                    )
            except:
                pass

        # Extract specific actions
        elif "🔗  Opened new tab" in log_line:
            url = log_line.split("with ")[1] if "with " in log_line else "URL"
            results.append(
                StepResult(step="Navigation: Open page", status="passed", error=None)
            )

        elif "⌨️  Input" in log_line:
            if "standard_user" in log_line:
                results.append(
                    StepResult(
                        step="Authentication: Enter username",
                        status="passed",
                        error=None,
                    )
                )
            elif "secret_sauce" in log_line:
                results.append(
                    StepResult(
                        step="Authentication: Enter password",
                        status="passed",
                        error=None,
                    )
                )
            else:
                results.append(
                    StepResult(step="Input: Enter text", status="passed", error=None)
                )

        elif "🖱️  Clicked" in log_line:
            if "Add to cart" in log_line:
                results.append(
                    StepResult(
                        step="Shopping: Add product to cart",
                        status="passed",
                        error=None,
                    )
                )
            elif "button with index 1:" in log_line and log_line.endswith("1"):
                results.append(
                    StepResult(
                        step="Navigation: Access cart", status="passed", error=None
                    )
                )
            elif "LOGIN" in log_line.upper() or log_line.split(":")[-1].strip() == "":
                results.append(
                    StepResult(
                        step="Authentication: Submit login", status="passed", error=None
                    )
                )
            else:
                results.append(
                    StepResult(
                        step="Interaction: Click element", status="passed", error=None
                    )
                )

        # Extract evaluations
        elif "👍 Eval: Success" in log_line:
            description = log_line.split("👍 Eval: Success - ")[1]
            results.append(
                StepResult(
                    step=f"Verification: {description}", status="passed", error=None
                )
            )

        elif "⚠️ Eval: Failed" in log_line:
            description = log_line.split("⚠️ Eval: Failed - ")[1]
            results.append(
                StepResult(
                    step=f"Verification: {description}",
                    status="failed",
                    error=description,
                )
            )

        # Extract final result
        elif "📄 Result:" in log_line:
            final_result = log_line.split("📄 Result: ")[1].strip()

        # Extract task completion
        elif "✅ Task completed successfully" in log_line:
            results.append(
                StepResult(step="Task completion", status="passed", error=None)
            )

        elif "❌ Task failed" in log_line:
            results.append(
                StepResult(
                    step="Task completion",
                    status="failed",
                    error="Task execution failed",
                )
            )

    # If no detailed steps were found, create a basic result
    if not results:
        results.append(
            StepResult(
                step="task_execution",
                status="passed" if final_result else "failed",
                error=None if final_result else "No execution details available",
            )
        )

    return results, final_result


async def run_agent_with_browser_use(
    task_description: str, scenario: str
) -> ScenarioResult:
    """
    Enhanced runner that captures and parses detailed execution logs
    """
    start_time = time.time()

    # Standard LLM configuration
    llm = ChatOpenAI(model="gpt-4o", temperature=0, max_tokens=4000, request_timeout=60)

    controller = Controller()
    agent = Agent(task=task_description, controller=controller, llm=llm)

    max_retries = 3
    last_error = None

    for attempt in range(max_retries):
        try:
            logger.info(
                f"[BrowserUse] Attempt {attempt + 1}/{max_retries} for scenario: {scenario}"
            )

            # Capture logs during execution
            with LogCapture() as log_capture:
                try:
                    resp = await asyncio.wait_for(agent.run(), timeout=300)
                except asyncio.TimeoutError:
                    raise Exception("Agent execution timed out after 5 minutes")

            # Get captured logs
            captured_logs = log_capture.get_logs()

            # Parse logs to extract detailed steps
            results, final_result = parse_agent_logs(captured_logs, scenario)

            # Determine overall success
            task_success = any(
                r.step == "Task completion" and r.status == "passed" for r in results
            )

            # We ignore earlier failed evals if the final result was success
            execution_successful = task_success

            execution_time = time.time() - start_time

            logger.info(
                f"[BrowserUse] Scenario '{scenario}' completed in {execution_time:.2f}s"
            )
            logger.info(
                f"[BrowserUse] Results: {len(results)} steps, Overall success: {execution_successful}"
            )

            return ScenarioResult(
                scenario=scenario,
                results=results,
                final_result=final_result,
                execution_time=execution_time,
                success=execution_successful,  # ✅ NEW FIELD SET
            )

        except RateLimitError as e:
            last_error = e
            logger.warning(
                f"[BrowserUse] ⏳ Rate limit hit. Retry {attempt + 1}/{max_retries}..."
            )
            await asyncio.sleep(3)
        except Exception as e:
            last_error = e
            logger.error(
                f"[BrowserUse] ❌ Agent run failed on attempt {attempt + 1}: {e}",
                exc_info=True,
            )
            if attempt == max_retries - 1:
                break
            await asyncio.sleep(2)

    # All retries failed
    execution_time = time.time() - start_time
    error_msg = f"All {max_retries} attempts failed. Last error: {str(last_error)}"

    logger.error(f"[BrowserUse] {error_msg}")

    return ScenarioResult(
        scenario=scenario,
        results=[
            StepResult(
                step="browser-use agent execution",
                status="failed",
                error=error_msg,
            )
        ],
        final_result=None,
        execution_time=execution_time,
    )


def run_browser_use_test_hybrid(prompt: str, scenario_name="Unnamed scenario"):
    """
    Synchronous wrapper with enhanced error handling
    """
    try:
        logger.info(f"[BrowserUse] Starting execution for: {scenario_name}")
        result = asyncio.run(run_agent_with_browser_use(prompt, scenario_name))
        logger.info(f"[BrowserUse] Completed execution for: {scenario_name}")
        return result
    except Exception as e:
        logger.error(f"[BrowserUse] Wrapper execution failed: {e}", exc_info=True)
        return ScenarioResult(
            scenario=scenario_name,
            results=[
                StepResult(
                    step="test execution wrapper",
                    status="failed",
                    error=f"Wrapper execution failed: {str(e)}",
                )
            ],
            final_result=None,
            execution_time=0.0,
        )
