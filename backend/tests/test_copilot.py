"""Copilot tool-calling loop, tools and endpoint."""

import json
from dataclasses import dataclass, field

from app.main import app
from app.services.copilot.engine import MAX_TOOL_ROUNDS
from app.services.copilot.llm_client import (
    LLMError,
    LLMMessage,
    LLMReply,
    ToolCall,
    ToolDefinition,
    get_llm_client,
)

CHAT = "/api/copilot/chat"


@dataclass
class ScriptedLLM:
    """Plays back fixed replies and records the messages it was sent."""

    replies: list[LLMReply | Exception]
    seen: list[list[LLMMessage]] = field(default_factory=list)

    async def complete(
        self, system: str, messages: list[LLMMessage], tools: list[ToolDefinition]
    ) -> LLMReply:
        self.seen.append(list(messages))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def use_llm(llm: ScriptedLLM) -> ScriptedLLM:
    app.dependency_overrides[get_llm_client] = lambda: llm
    return llm


def call(name: str, **arguments) -> ToolCall:
    return ToolCall(id=name, name=name, arguments=arguments)


async def make_experiment(client, name: str = "exp") -> int:
    response = await client.post("/api/experiments", json={"name": name})
    return response.json()["id"]


async def make_run(
    client, experiment_id: int, name: str, val_accuracy: float, val_loss: float, status="completed"
) -> int:
    response = await client.post(
        "/api/runs", json={"experiment_id": experiment_id, "run_name": name}
    )
    run_id = response.json()["id"]
    await client.post(
        f"/api/runs/{run_id}/metrics",
        json={
            "epoch": 1,
            "accuracy": 0.5,
            "loss": 0.5,
            "val_accuracy": val_accuracy,
            "val_loss": val_loss,
        },
    )
    if status != "running":
        await client.put(f"/api/runs/{run_id}", json={"status": status})
    return run_id


async def test_fake_llm_finds_best_run_and_returns_actions(client):
    exp = await make_experiment(client)
    await make_run(client, exp, "run-a", 0.80, 0.4)
    best = await make_run(client, exp, "run-b", 0.95, 0.2)

    response = await client.post(CHAT, json={"message": "Run nào tốt nhất?", "experiment_id": exp})

    assert response.status_code == 200
    body = response.json()
    assert "run-b" in body["message"] and "0.9500" in body["message"]
    assert body["actions"] == [
        {"type": "highlight_runs", "run_ids": [best]},
        {"type": "focus_camera", "run_id": best},
    ]


async def test_fake_llm_ranks_loss_lowest_first(client):
    exp = await make_experiment(client)
    await make_run(client, exp, "high-loss", 0.99, 0.9)
    best = await make_run(client, exp, "low-loss", 0.70, 0.1)

    body = (
        await client.post(CHAT, json={"message": "best val_loss?", "experiment_id": exp})
    ).json()

    assert "low-loss" in body["message"]
    assert body["actions"][1]["run_id"] == best


async def test_running_and_failed_runs_are_not_ranked(client):
    exp = await make_experiment(client)
    await make_run(client, exp, "still-running", 0.99, 0.1, status="running")
    await make_run(client, exp, "crashed", 0.98, 0.1, status="failed")
    finished = await make_run(client, exp, "finished", 0.60, 0.5)

    body = (await client.post(CHAT, json={"message": "best?", "experiment_id": exp})).json()

    assert body["actions"][1]["run_id"] == finished


async def test_ranking_is_scoped_to_the_experiment(client):
    first = await make_experiment(client, "first")
    second = await make_experiment(client, "second")
    await make_run(client, first, "other", 0.99, 0.1)
    mine = await make_run(client, second, "mine", 0.50, 0.5)

    body = (await client.post(CHAT, json={"message": "best?", "experiment_id": second})).json()

    assert body["actions"][1]["run_id"] == mine


async def test_no_completed_runs_gives_answer_without_actions(client):
    exp = await make_experiment(client)
    body = (await client.post(CHAT, json={"message": "best?", "experiment_id": exp})).json()
    assert body["actions"] == []
    assert "Chưa có run" in body["message"]


async def test_unknown_experiment_is_reported_not_raised(client):
    response = await client.post(CHAT, json={"message": "best?", "experiment_id": 999})
    assert response.status_code == 200
    assert "not found" in response.json()["message"]


async def test_fake_llm_declines_other_questions(client):
    body = (await client.post(CHAT, json={"message": "Xin chào"})).json()
    assert body["actions"] == []
    assert "tốt nhất" in body["message"]


async def test_invalid_arguments_are_returned_to_the_model(client):
    llm = use_llm(
        ScriptedLLM(
            [
                LLMReply(tool_calls=[call("find_best_runs", metric="f1")]),
                LLMReply(text="done"),
            ]
        )
    )

    body = (await client.post(CHAT, json={"message": "q"})).json()

    assert body == {"message": "done", "actions": []}
    assert "Invalid arguments" in llm.seen[1][-1].content


async def test_unknown_tool_is_returned_to_the_model(client):
    llm = use_llm(ScriptedLLM([LLMReply(tool_calls=[call("drop_tables")]), LLMReply(text="done")]))
    await client.post(CHAT, json={"message": "q"})
    assert "Unknown tool" in llm.seen[1][-1].content


async def test_nonexistent_runs_never_reach_the_frontend(client):
    exp = await make_experiment(client)
    real = await make_run(client, exp, "real", 0.9, 0.1)
    use_llm(
        ScriptedLLM(
            [
                LLMReply(
                    tool_calls=[
                        call("highlight_runs", run_ids=[real, 12345]),
                        call("focus_camera", run_id=12345),
                        call("open_inspector", run_id=12345),
                        call("highlight_runs", run_ids=[12345]),
                    ]
                ),
                LLMReply(text="done"),
            ]
        )
    )

    body = (await client.post(CHAT, json={"message": "q"})).json()

    assert body["actions"] == [{"type": "highlight_runs", "run_ids": [real]}]


async def test_open_inspector_action(client):
    exp = await make_experiment(client)
    run = await make_run(client, exp, "r", 0.9, 0.1)
    use_llm(
        ScriptedLLM(
            [LLMReply(tool_calls=[call("open_inspector", run_id=run)]), LLMReply(text="ok")]
        )
    )
    body = (await client.post(CHAT, json={"message": "q"})).json()
    assert body["actions"] == [{"type": "open_inspector", "run_id": run}]


async def test_tool_loop_is_bounded(client):
    looping = LLMReply(tool_calls=[call("find_best_runs")])
    llm = use_llm(ScriptedLLM([looping] * (MAX_TOOL_ROUNDS + 3)))

    response = await client.post(CHAT, json={"message": "q"})

    assert response.status_code == 200
    assert len(llm.seen) == MAX_TOOL_ROUNDS
    assert "quá nhiều" in response.json()["message"]


async def test_llm_failure_gives_friendly_message(client):
    use_llm(ScriptedLLM([LLMError("quota")]))

    response = await client.post(CHAT, json={"message": "q"})

    assert response.status_code == 200
    body = response.json()
    assert body["actions"] == []
    assert "quota" not in body["message"]


async def test_empty_reply_has_fallback_message(client):
    llm = use_llm(ScriptedLLM([LLMReply(), LLMReply()]))
    body = (await client.post(CHAT, json={"message": "q"})).json()
    assert body["message"]
    assert len(llm.seen) == 2  # asked again exactly once


async def test_silent_stop_after_tools_gets_nudged_for_the_answer(client):
    exp = await make_experiment(client)
    run = await make_run(client, exp, "r", 0.9, 0.1)
    use_llm(
        ScriptedLLM(
            [
                LLMReply(tool_calls=[call("focus_camera", run_id=run)]),
                LLMReply(),
                LLMReply(text="final answer"),
            ]
        )
    )

    body = (await client.post(CHAT, json={"message": "q"})).json()

    assert body == {
        "message": "final answer",
        "actions": [{"type": "focus_camera", "run_id": run}],
    }


async def test_find_best_runs_gives_context_to_explain_the_result(client):
    exp = await make_experiment(client)
    for name, accuracy in [("a", 0.6), ("b", 0.7), ("c", 0.9)]:
        await make_run(client, exp, name, accuracy, 0.3)
    llm = use_llm(ScriptedLLM([LLMReply(tool_calls=[call("find_best_runs")]), LLMReply(text="ok")]))

    await client.post(CHAT, json={"message": "q", "experiment_id": exp})

    result = json.loads(llm.seen[1][-1].content)
    assert result["completed_runs"] == 3
    assert result["median_value"] == 0.7
    assert [run["run_name"] for run in result["runs"]] == ["c"]


async def test_request_validation(client):
    assert (await client.post(CHAT, json={"message": "   "})).status_code == 422
    assert (await client.post(CHAT, json={})).status_code == 422
    assert (await client.post(CHAT, json={"message": "q", "extra": 1})).status_code == 422
