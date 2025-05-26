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
        self.captured_logs = []
        self.original_handlers = {}
        self.string_io = io.StringIO()
        self.handler = logging.StreamHandler(self.string_io)
        # Capture logs at INFO level and above
        self.handler.setLevel(logging.INFO)

        # Create a custom formatter to ensure we get all the info
        formatter = logging.Formatter("%(levelname)s     [%(name)s] %(message)s")
        self.handler.setFormatter(formatter)

    def __enter__(self):
        # Get the root logger and all browser_use related loggers
        loggers_to_capture = [
            "",  # Root logger
            "agent",
            "controller",
            "browser",
            "browser_use",
            "browser_use_runner_lib",
        ]

        for logger_name in loggers_to_capture:
            log = logging.getLogger(logger_name)
            # Store original handlers
            self.original_handlers[logger_name] = log.handlers.copy()
            # Add our capturing handler
            log.addHandler(self.handler)
            # Capture at INFO level by default
            if log.level > logging.INFO:
                log.setLevel(logging.INFO)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original handlers and levels
        for logger_name in self.original_handlers.keys():
            log = logging.getLogger(logger_name)
            log.removeHandler(self.handler)

        # Get all captured logs
        self.captured_logs = self.string_io.getvalue().split("\n")

    def get_logs(self):
        return self.captured_logs


def parse_agent_logs(
    logs: list[str], scenario: str
) -> tuple[list[StepResult], str, bool]:
    """Parse agent execution logs to extract detailed steps, final result, and success status"""
    results = []
    final_result = None
    current_step = None
    step_counter = 1
    task_completed_successfully = False
    task_failed = False

    # Log the amount of information captured for troubleshooting
    logger.info(f"[PARSE] Processing {len(logs)} log lines for scenario: {scenario}")

    for log_line in logs:
        if not log_line.strip():
            continue

        # PRIORITY 1: Check for definitive task completion indicators
        if "✅ Task completed successfully" in log_line:
            task_completed_successfully = True
            results.append(
                StepResult(step="Task completion", status="passed", error=None)
            )
            logger.info(f"[PARSE] Found successful task completion indicator")

        elif (
            "❌ Task failed" in log_line
            or "Task execution failed" in log_line
            or "❌ Task completed without success" in log_line
            or "Task completed without success" in log_line
        ):
            task_failed = True
            results.append(
                StepResult(
                    step="Task completion",
                    status="failed",
                    error="Task execution failed",
                )
            )
            logger.info(f"[PARSE] Found task failure indicator")

        # Extract step information
        elif "📍 Step" in log_line and "Evaluating page" in log_line:
            try:
                step_num = log_line.split("📍 Step ")[1].split(":")[0]
                current_step = f"Step {step_num}"
            except:
                current_step = f"Step {step_counter}"
                step_counter += 1

        elif "📍 Step" in log_line and "Ran" in log_line:
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
        elif "🔗" in log_line and ("Navigated to" in log_line or "Opened" in log_line):
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
            elif "button with index 1:" in log_line:
                results.append(
                    StepResult(
                        step="Navigation: Access cart", status="passed", error=None
                    )
                )
            elif "LOGIN" in log_line.upper():
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
            description = (
                log_line.split("👍 Eval: Success - ")[1]
                if "👍 Eval: Success - " in log_line
                else "Success evaluation"
            )
            results.append(
                StepResult(
                    step=f"Verification: {description}", status="passed", error=None
                )
            )

        elif "⚠️ Eval: Failed" in log_line or "❌ Eval: Failed" in log_line:
            description = "Failed evaluation"
            if "⚠️ Eval: Failed - " in log_line:
                description = log_line.split("⚠️ Eval: Failed - ")[1]
            elif "❌ Eval: Failed - " in log_line:
                description = log_line.split("❌ Eval: Failed - ")[1]

            # Only count as failure if task didn't ultimately succeed
            if not task_completed_successfully:
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

    # DETERMINE SUCCESS: Priority order matters!
    overall_success = False

    # 1. Explicit task completion (highest priority)
    if task_completed_successfully:
        overall_success = True
        logger.info(f"[PARSE] Overall success: TRUE (explicit task completion found)")
    elif task_failed:
        overall_success = False
        logger.info(f"[PARSE] Overall success: FALSE (explicit task failure found)")
    # 2. Final result analysis
    elif final_result:
        success_indicators = [
            "successfully",
            "completed",
            "verified",
            "added",
            "confirmed",
            "success",
            "accomplished",
        ]
        if any(indicator in final_result.lower() for indicator in success_indicators):
            overall_success = True
            logger.info(
                f"[PARSE] Overall success: TRUE (final result indicates success)"
            )
        else:
            # Check if it's just a neutral result description
            error_indicators = ["failed", "error", "could not", "unable", "timeout"]
            if any(indicator in final_result.lower() for indicator in error_indicators):
                overall_success = False
                logger.info(
                    f"[PARSE] Overall success: FALSE (final result indicates failure)"
                )
            else:
                # Neutral final result - check other indicators
                overall_success = True  # Default to success if no clear failure
                logger.info(
                    f"[PARSE] Overall success: TRUE (neutral final result, defaulting to success)"
                )
    # 3. Check for successful verification steps
    elif any("Verification:" in r.step and r.status == "passed" for r in results):
        overall_success = True
        logger.info(
            f"[PARSE] Overall success: TRUE (found successful verification steps)"
        )
    # 4. Step analysis (most lenient)
    else:
        passed_steps = sum(1 for r in results if r.status == "passed")
        failed_steps = sum(1 for r in results if r.status == "failed")

        if passed_steps > 0:
            overall_success = True
            logger.info(
                f"[PARSE] Overall success: TRUE (found {passed_steps} passed steps, {failed_steps} failed)"
            )
        else:
            overall_success = False
            logger.info(f"[PARSE] Overall success: FALSE (no successful steps found)")

    # Ensure we have at least one result
    if not results:
        status = "passed" if overall_success else "failed"
        error = None if overall_success else "No execution details captured"
        results.append(StepResult(step="Task execution", status=status, error=error))

    logger.info(
        f"[PARSE] Final determination - Success: {overall_success}, Steps: {len(results)}, Final result: '{final_result}'"
    )

    return results, final_result, overall_success


async def run_agent_with_browser_use(
    task_description: str, scenario: str
) -> ScenarioResult:
    """
    Enhanced runner that captures and parses detailed execution logs with proper success detection
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
                    logger.info(f"[BrowserUse] Agent execution completed successfully")
                except asyncio.TimeoutError:
                    logger.error(f"[BrowserUse] Agent execution timed out")
                    raise Exception("Agent execution timed out after 5 minutes")

            # Get captured logs
            captured_logs = log_capture.get_logs()
            logger.info(f"[BrowserUse] Captured {len(captured_logs)} log lines")

            # Parse logs to extract detailed steps and determine success
            results, final_result, execution_successful = parse_agent_logs(
                captured_logs, scenario
            )

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
                success=execution_successful,
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
        success=False,
    )


def run_browser_use_test_hybrid(prompt: str, scenario_name="Unnamed scenario"):
    """
    Synchronous wrapper with enhanced error handling
    """
    try:
        logger.info(f"[BrowserUse] Starting execution for: {scenario_name}")
        result = asyncio.run(run_agent_with_browser_use(prompt, scenario_name))
        logger.info(
            f"[BrowserUse] Completed execution for: {scenario_name} - Success: {result.success}"
        )
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
            success=False,
        )
