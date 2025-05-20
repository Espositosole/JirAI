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
            history = await agent.run()
            final_result = getattr(agent, "final_result", None)
            if callable(final_result):
                final_result = final_result()
            else:
                final_result = "No summary available"

            results = []
            for step in history:
                command = step[0]
                evals = step[1] if isinstance(step[1], list) else [step[1]]

                for ev in evals:
                    passed = getattr(ev, "passed", None)
                    reason = getattr(ev, "reason", "No reason provided.")
                    status = "passed" if passed else "failed"

                    print(f"[ACTION] {command} — {status.upper()} — {reason}")

                    results.append(
                        StepResult(
                            step=command,
                            status=status,
                            error=None if passed else reason,
                        )
                    )

            return ScenarioResult(
                scenario=scenario, results=results, final_result=final_result
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
