import asyncio
import time
import nest_asyncio
from pydantic import BaseModel
from browser_use import Agent, Controller
from langchain_openai import ChatOpenAI
from openai import RateLimitError

nest_asyncio.apply()


class StepResult(BaseModel):
    step: str
    status: str
    error: str | None = None


class ScenarioResult(BaseModel):
    scenario: str
    results: list[StepResult]
    final_result: str | None = None


async def run_agent_with_browser_use(
    task_description: str, scenario: str
) -> ScenarioResult:
    llm = ChatOpenAI(model="gpt-4o")
    controller = Controller()
    agent = Agent(task=task_description, controller=controller, llm=llm)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = await agent.run()

            history_entries = None
            if isinstance(resp, list):
                history_entries = resp
            elif isinstance(resp, dict) and isinstance(resp.get("history"), list):
                history_entries = resp.get("history")
            if history_entries is None:
                history_entries = getattr(agent, "history", [])

            results = []
            final_result = None

            for entry in history_entries:
                # Look for final result in 'done' action
                if isinstance(entry, dict) and "done" in entry:
                    done_block = entry["done"]
                    if isinstance(done_block, dict):
                        final_result = done_block.get("text")

                if isinstance(entry, (tuple, list)):
                    action = entry[0]
                    evals = entry[1] if len(entry) > 1 else []
                elif isinstance(entry, dict):
                    action = (
                        entry.get("command") or entry.get("action") or entry.get("step")
                    )
                    evals = entry.get("evals") or entry.get("evaluation") or []
                else:
                    continue

                if action in {"history", "DONE"}:
                    continue

                evals = evals if isinstance(evals, list) else [evals]

                for ev in evals:
                    passed = getattr(ev, "passed", None)
                    reason = getattr(ev, "reason", None)
                    if passed is None and isinstance(ev, dict):
                        passed = ev.get("passed")
                        reason = ev.get("reason") or ev.get("error")
                    status = "passed" if passed else "failed"
                    if not passed and not reason:
                        reason = "No reason provided."

                    print(f"[ACTION] {action} — {status.upper()} — {reason or 'OK'}")

                    results.append(
                        StepResult(
                            step=action,
                            status=status,
                            error=None if passed else reason,
                        )
                    )

            return ScenarioResult(
                scenario=scenario,
                results=results,
                final_result=final_result,
            )

        except RateLimitError as e:
            print(f"[Runner] ⏳ Rate limit hit. Retry {attempt + 1}/{max_retries}...")
            time.sleep(3)
        except Exception as e:
            print(f"[Runner] ❌ Agent run failed: {e}")
            return ScenarioResult(
                scenario=scenario,
                results=[
                    StepResult(
                        step="browser-use agent execution",
                        status="failed",
                        error=str(e),
                    )
                ],
                final_result=None,
            )

    return ScenarioResult(
        scenario=scenario,
        results=[
            StepResult(
                step="browser-use agent execution",
                status="failed",
                error="Rate limit exceeded after retries",
            )
        ],
        final_result=None,
    )


def run_browser_use_test_hybrid(prompt: str, scenario_name="Unnamed scenario"):
    return asyncio.run(run_agent_with_browser_use(prompt, scenario_name))
