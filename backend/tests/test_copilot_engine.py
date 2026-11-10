"""Copilot tool-calling loop, tools, endpoint and answer accuracy.

The accuracy question set runs offline by default. To run it against the real LLM, which
spends quota (about 25 calls):

    COPILOT_LIVE=1 uv run pytest tests/test_copilot_engine.py -k live
"""

import asyncio
import json
import os
import re
from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from statistics import median
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.main import app
from app.models import Experiment, Run, RunStatus
from app.schemas.copilot import ChatRequest, ChatResponse
from app.services.copilot.engine import MAX_TOOL_ROUNDS, answer
from app.services.copilot.llm_client import (
    LLMClient,
    LLMError,
    LLMMessage,
    LLMRateLimitError,
    LLMReply,
    ToolCall,
    ToolDefinition,
    get_llm_client,
)
from app.utils.seed_data import PROFILES, seed_database

CHAT = "/api/copilot/chat"
CHAT_STREAM = "/api/copilot/chat/stream"


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

    async def stream(
        self, system: str, messages: list[LLMMessage], tools: list[ToolDefinition]
    ) -> AsyncIterator[str | LLMReply]:
        reply = await self.complete(system, messages, tools)
        if reply.text:
            yield reply.text
        yield reply


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


async def stream_events(client, message: str, experiment_id: int | None = None) -> list[dict]:
    response = await client.post(
        CHAT_STREAM, json={"message": message, "experiment_id": experiment_id}
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    return [json.loads(block[6:]) for block in response.text.split("\n\n") if block]


def streamed_text(events: list[dict]) -> str:
    return "".join(event["text"] for event in events if event["type"] == "delta")


async def test_stream_sends_text_in_pieces_then_the_same_answer_and_actions(client):
    exp = await make_experiment(client)
    best = await make_run(client, exp, "run-b", 0.95, 0.2)

    events = await stream_events(client, "Run nào tốt nhất?", exp)

    assert sum(event["type"] == "delta" for event in events) > 1
    assert events[-1]["type"] == "done"
    assert streamed_text(events) == events[-1]["message"]
    assert "0.9500" in events[-1]["message"]
    assert events[-1]["actions"][0] == {"type": "highlight_runs", "run_ids": [best]}


async def test_stream_retracts_text_written_alongside_a_tool_call(client):
    use_llm(
        ScriptedLLM(
            [
                LLMReply(text="Để tôi xem...", tool_calls=[call("list_experiments")]),
                LLMReply(text="Câu trả lời."),
            ]
        )
    )

    events = await stream_events(client, "q")

    assert [event["type"] for event in events] == ["delta", "reset", "delta", "done"]
    assert events[-1]["message"] == "Câu trả lời."


async def test_stream_reports_llm_failure_in_the_final_event(client):
    use_llm(ScriptedLLM([LLMError("boom")]))

    events = await stream_events(client, "q")

    assert [event["type"] for event in events] == ["done"]
    assert "sự cố" in events[0]["message"]


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
        {"type": "open_inspector", "run_id": best},
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


async def test_compare_question_gets_database_numbers_and_highlights(client):
    exp = await make_experiment(client)
    a = await make_run(client, exp, "run-001", 0.90, 0.3)
    b = await make_run(client, exp, "run-003", 0.80, 0.5)
    llm = use_llm(
        ScriptedLLM(
            [
                LLMReply(tool_calls=[call("find_runs_by_name", run_names=["run-001", "run-003"])]),
                LLMReply(tool_calls=[call("compare_runs", run_ids=[a, b])]),
                LLMReply(text="run-001 tốt hơn"),
            ]
        )
    )

    body = (
        await client.post(
            CHAT, json={"message": "So sánh run-001 và run-003", "experiment_id": exp}
        )
    ).json()

    assert body == {
        "message": "run-001 tốt hơn",
        "actions": [
            {"type": "highlight_runs", "run_ids": [a, b]},
            {"type": "focus_camera", "run_id": a},
            {"type": "open_inspector", "run_id": a},
        ],
    }
    lookup = json.loads(llm.seen[1][-1].content)
    assert [run["run_id"] for run in lookup["runs"]] == [a, b]
    compared = json.loads(llm.seen[2][-1].content)
    assert compared["best_by_metric"]["val_accuracy"] == {
        "run_id": a,
        "run_name": "run-001",
        "value": 0.90,
        "spread_to_worst": 0.1,
    }


async def test_diagnose_question_gets_verdict_from_code_and_focuses_the_run(client):
    exp = await make_experiment(client)
    response = await client.post("/api/runs", json={"experiment_id": exp, "run_name": "run-002"})
    run = response.json()["id"]
    curve = [
        (0.70, 0.9, 0.70, 0.9),
        (0.85, 0.5, 0.80, 0.6),
        (0.95, 0.2, 0.82, 0.7),
        (0.99, 0.1, 0.82, 0.9),
    ]
    for epoch, (accuracy, loss, val_accuracy, val_loss) in enumerate(curve, start=1):
        await client.post(
            f"/api/runs/{run}/metrics",
            json={
                "epoch": epoch,
                "accuracy": accuracy,
                "loss": loss,
                "val_accuracy": val_accuracy,
                "val_loss": val_loss,
            },
        )
    llm = use_llm(
        ScriptedLLM(
            [
                LLMReply(tool_calls=[call("find_runs_by_name", run_names=["run-002"])]),
                LLMReply(tool_calls=[call("detect_overfitting", run_id=run)]),
                LLMReply(text="Có"),
            ]
        )
    )

    body = (
        await client.post(CHAT, json={"message": "run-002 có overfit không?", "experiment_id": exp})
    ).json()

    assert body == {
        "message": "Có",
        "actions": [
            {"type": "highlight_runs", "run_ids": [run]},
            {"type": "focus_camera", "run_id": run},
            {"type": "open_inspector", "run_id": run},
        ],
    }
    diagnosis = json.loads(llm.seen[2][-1].content)
    assert diagnosis["verdict"] == "overfitting"
    assert diagnosis["val_loss_trend"]["lowest_epoch"] == 2


async def test_llm_timeout_keeps_the_friendly_message_after_tools_ran(client):
    exp = await make_experiment(client)
    run = await make_run(client, exp, "r", 0.9, 0.1)
    use_llm(
        ScriptedLLM(
            [
                LLMReply(tool_calls=[call("get_run", run_id=run)]),
                LLMError("Gemini request failed: ReadTimeout"),
            ]
        )
    )

    response = await client.post(CHAT, json={"message": "q"})

    assert response.status_code == 200
    assert "ReadTimeout" not in response.json()["message"]
    assert "sự cố" in response.json()["message"]


async def test_rate_limit_keeps_actions_already_collected(client):
    exp = await make_experiment(client)
    run = await make_run(client, exp, "r", 0.9, 0.1)
    use_llm(
        ScriptedLLM(
            [LLMReply(tool_calls=[call("focus_camera", run_id=run)]), LLMRateLimitError("quota")]
        )
    )

    body = (await client.post(CHAT, json={"message": "q"})).json()

    assert "giới hạn" in body["message"]
    assert body["actions"] == [{"type": "focus_camera", "run_id": run}]


async def test_highlight_tells_the_model_which_runs_do_not_exist(client):
    exp = await make_experiment(client)
    real = await make_run(client, exp, "real", 0.9, 0.1)
    llm = use_llm(
        ScriptedLLM(
            [
                LLMReply(tool_calls=[call("highlight_runs", run_ids=[real, 12345])]),
                LLMReply(text="done"),
            ]
        )
    )

    await client.post(CHAT, json={"message": "q"})

    assert json.loads(llm.seen[1][-1].content) == {"highlighted": [real], "not_found": [12345]}


async def test_all_tool_calls_of_one_round_run_and_are_answered(client):
    exp = await make_experiment(client)
    run = await make_run(client, exp, "r", 0.9, 0.1)
    llm = use_llm(
        ScriptedLLM(
            [
                LLMReply(
                    tool_calls=[
                        call("get_run", run_id=run),
                        call("highlight_runs", run_ids=[run]),
                        call("open_inspector", run_id=run),
                    ]
                ),
                LLMReply(text="done"),
            ]
        )
    )

    body = (await client.post(CHAT, json={"message": "q"})).json()

    assert [m.tool_name for m in llm.seen[1] if m.role == "tool"] == [
        "get_run",
        "highlight_runs",
        "open_inspector",
    ]
    assert [action["type"] for action in body["actions"]] == ["highlight_runs", "open_inspector"]


async def test_nothing_is_marked_when_no_tool_found_runs_to_show(client):
    exp = await make_experiment(client)
    run = await make_run(client, exp, "running", 0.9, 0.1, status="running")
    scripts = [
        call("find_best_runs"),  # no completed run to rank
        call("detect_overfitting", run_id=12345),  # error
        call("get_run", run_id=run),  # a plain lookup, not an answer about which run
    ]
    for tool_call in scripts:
        llm = use_llm(ScriptedLLM([LLMReply(tool_calls=[tool_call]), LLMReply(text="done")]))

        body = (await client.post(CHAT, json={"message": "q", "experiment_id": exp})).json()

        assert body["actions"] == []
        assert len(llm.seen) == 2


def chart_actions(run_ids: list[int], main: int) -> list[dict]:
    return [
        {"type": "highlight_runs", "run_ids": run_ids},
        {"type": "focus_camera", "run_id": main},
        {"type": "open_inspector", "run_id": main},
    ]


async def test_best_runs_are_marked_without_another_llm_round(client):
    exp = await make_experiment(client)
    second = await make_run(client, exp, "second", 0.8, 0.3)
    first = await make_run(client, exp, "first", 0.9, 0.2)
    await make_run(client, exp, "third", 0.7, 0.4)
    llm = use_llm(
        ScriptedLLM([LLMReply(tool_calls=[call("find_best_runs", top_k=2)]), LLMReply(text="ok")])
    )

    body = (await client.post(CHAT, json={"message": "q", "experiment_id": exp})).json()

    assert body["actions"] == chart_actions([first, second], first)
    assert len(llm.seen) == 2


async def test_comparison_focuses_the_better_run_wherever_it_is_listed(client):
    exp = await make_experiment(client)
    worse = await make_run(client, exp, "worse", 0.7, 0.4)
    better = await make_run(client, exp, "better", 0.9, 0.2)
    use_llm(
        ScriptedLLM(
            [
                LLMReply(tool_calls=[call("compare_runs", run_ids=[worse, better])]),
                LLMReply(text="k"),
            ]
        )
    )

    body = (await client.post(CHAT, json={"message": "q", "experiment_id": exp})).json()

    assert body["actions"] == chart_actions([worse, better], better)


async def test_comparison_without_finished_runs_focuses_the_first(client):
    exp = await make_experiment(client)
    a = await make_run(client, exp, "a", 0.7, 0.4, status="running")
    b = await make_run(client, exp, "b", 0.9, 0.2, status="running")
    use_llm(
        ScriptedLLM(
            [LLMReply(tool_calls=[call("compare_runs", run_ids=[a, b])]), LLMReply(text="k")]
        )
    )

    body = (await client.post(CHAT, json={"message": "q", "experiment_id": exp})).json()

    assert body["actions"] == chart_actions([a, b], a)


async def test_the_latest_answering_tool_decides_what_is_marked(client):
    exp = await make_experiment(client)
    a = await make_run(client, exp, "a", 0.7, 0.4)
    b = await make_run(client, exp, "b", 0.9, 0.2)
    use_llm(
        ScriptedLLM(
            [
                LLMReply(tool_calls=[call("find_best_runs")]),
                LLMReply(tool_calls=[call("compare_runs", run_ids=[a, b])]),
                LLMReply(text="ok"),
            ]
        )
    )

    body = (await client.post(CHAT, json={"message": "q", "experiment_id": exp})).json()

    assert body["actions"] == chart_actions([a, b], b)


async def test_actions_the_model_asked_for_replace_the_automatic_ones(client):
    exp = await make_experiment(client)
    best = await make_run(client, exp, "best", 0.9, 0.1)
    other = await make_run(client, exp, "other", 0.5, 0.5)
    use_llm(
        ScriptedLLM(
            [
                LLMReply(tool_calls=[call("find_best_runs"), call("focus_camera", run_id=other)]),
                LLMReply(text="done"),
            ]
        )
    )

    body = (await client.post(CHAT, json={"message": "q", "experiment_id": exp})).json()

    assert best not in [action.get("run_id") for action in body["actions"]]
    assert body["actions"] == [{"type": "focus_camera", "run_id": other}]


async def test_rate_limit_keeps_the_runs_already_found(client):
    exp = await make_experiment(client)
    run = await make_run(client, exp, "r", 0.9, 0.1)
    use_llm(
        ScriptedLLM([LLMReply(tool_calls=[call("find_best_runs")]), LLMRateLimitError("quota")])
    )

    body = (await client.post(CHAT, json={"message": "q", "experiment_id": exp})).json()

    assert "giới hạn" in body["message"]
    assert body["actions"] == chart_actions([run], run)


@pytest.mark.parametrize(
    "question",
    ["So sánh run-7 với cái khác", "RUN-7 có bị overfit không?", "Còn run-7?", "xem run-7."],
)
async def test_runs_named_in_the_question_reach_the_model_with_their_id(client, question):
    exp = await make_experiment(client)
    run = await make_run(client, exp, "run-7", 0.9, 0.1)
    llm = use_llm(ScriptedLLM([LLMReply(text="ok")]))

    await client.post(CHAT, json={"message": question, "experiment_id": exp})

    [asked, note] = llm.seen[0]
    assert asked.content == question
    assert f"run-7 is run_id {run} in experiment {exp}" in note.content


async def test_a_run_of_the_same_name_in_another_experiment_is_not_listed(client):
    mine = await make_experiment(client, "mine")
    other = await make_experiment(client, "other")
    await make_run(client, other, "run-7", 0.9, 0.1)
    llm = use_llm(ScriptedLLM([LLMReply(text="ok")]))

    await client.post(CHAT, json={"message": "run-7", "experiment_id": mine})

    assert len(llm.seen[0]) == 1


async def test_without_an_experiment_every_match_is_listed_for_the_model_to_ask(client):
    first = await make_experiment(client, "first")
    second = await make_experiment(client, "second")
    a = await make_run(client, first, "run-7", 0.9, 0.1)
    b = await make_run(client, second, "run-7", 0.8, 0.2)
    llm = use_llm(ScriptedLLM([LLMReply(text="ok")]))

    await client.post(CHAT, json={"message": "run-7"})

    note = llm.seen[0][1].content
    assert f"run_id {a} in experiment {first}" in note
    assert f"run_id {b} in experiment {second}" in note


async def test_no_note_when_the_question_names_no_run(client):
    exp = await make_experiment(client)
    await make_run(client, exp, "run-7", 0.9, 0.1)
    llm = use_llm(ScriptedLLM([LLMReply(text="ok")]))

    await client.post(CHAT, json={"message": "run-8 thì sao?", "experiment_id": exp})

    assert len(llm.seen[0]) == 1


async def test_request_validation(client):
    assert (await client.post(CHAT, json={"message": "   "})).status_code == 422
    assert (await client.post(CHAT, json={})).status_code == 422
    assert (await client.post(CHAT, json={"message": "q", "extra": 1})).status_code == 422


# ── Answer accuracy: numbers in the answer against the database ───────────────

ACCURACY_NOW = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)
LIVE_PAUSE_SECONDS = 20  # keeps the live set under the free tier's requests per minute

# A number: not part of a name (run-001, resnet18, 3D). Decimals may use a Vietnamese comma.
_NUMBER = re.compile(r"(?<![\w.,])(?<![^\W\d]-)(?<!\d-)\d+(?:[.,]\d+)?(?:[eE]-?\d+)?(?!\w)")
_MAX_UNCHECKED_COUNT = 10  # small integers are usually counts in the prose ("2 run")
_TOOL_TERMS = re.compile(
    r"\w+_overfitting|insufficient_data|median_value|spread_to_worst|final_\w+"
)


@dataclass(frozen=True)
class AccuracyCase:
    """A question, and what a correct answer must contain, read directly from the database."""

    question: str
    tool: str  # the query tool that holds the answer
    tool_args: dict[str, Any]
    names: tuple[str, ...]
    numbers: tuple[float, ...] = ()
    highlighted: tuple[int, ...] = ()
    verdict: str | None = None


def _final(run: Run) -> Any:
    return run.metrics[-1]


def _gap(metrics: list[Any]) -> float:
    return sum(m.accuracy - m.val_accuracy for m in metrics) / len(metrics)


def _lowest_val_loss(run: Run) -> float:
    return min(m.val_loss for m in run.metrics)


def _median_of_final(runs: list[Run], metric: str) -> float:
    return median(getattr(_final(run), metric) for run in runs)


def _best_val_accuracy_case(runs: list[Run]) -> AccuracyCase:
    best = max(runs, key=lambda run: _final(run).val_accuracy)
    return AccuracyCase(
        question="Run nào có val_accuracy cao nhất?",
        tool="find_best_runs",
        tool_args={"metric": "val_accuracy"},
        names=(best.run_name,),
        numbers=(_final(best).val_accuracy, _median_of_final(runs, "val_accuracy")),
        highlighted=(best.id,),
    )


def _lowest_val_loss_case(runs: list[Run]) -> AccuracyCase:
    best = min(runs, key=lambda run: _final(run).val_loss)
    return AccuracyCase(
        question="Run nào có val_loss thấp nhất?",
        tool="find_best_runs",
        tool_args={"metric": "val_loss"},
        names=(best.run_name,),
        numbers=(_final(best).val_loss, _median_of_final(runs, "val_loss")),
        highlighted=(best.id,),
    )


def _compare_case(runs: list[Run]) -> AccuracyCase:
    a, b = runs[0], runs[1]
    return AccuracyCase(
        question=f"So sánh {a.run_name} và {b.run_name}",
        tool="compare_runs",
        tool_args={"run_ids": [a.id, b.id]},
        names=(a.run_name, b.run_name),
        numbers=(
            _final(a).val_accuracy,
            _final(b).val_accuracy,
            _final(a).val_loss,
            _final(b).val_loss,
            abs(_final(a).val_accuracy - _final(b).val_accuracy),
        ),
        highlighted=(a.id, b.id),
    )


def _diagnose_case(run: Run, verdict: str) -> AccuracyCase:
    return AccuracyCase(
        question=f"{run.run_name} có bị overfit không?",
        tool="detect_overfitting",
        tool_args={"run_id": run.id},
        names=(run.run_name,),
        numbers=(_gap(run.metrics[-3:]), _lowest_val_loss(run)),
        highlighted=(run.id,),
        verdict=verdict,
    )


def _diagnose_overfit_case(runs: list[Run]) -> AccuracyCase:
    run = next(r for r in runs if _gap(r.metrics[-3:]) - _gap(r.metrics[:3]) >= 0.05)
    return _diagnose_case(run, "overfitting")


def _diagnose_healthy_case(runs: list[Run]) -> AccuracyCase:
    run = next(
        r
        for r in runs
        if abs(_gap(r.metrics[-3:])) < 0.01 and _final(r).val_loss < _lowest_val_loss(r) * 1.05
    )
    return _diagnose_case(run, "no_overfitting")


def _hyperparameter_case(runs: list[Run]) -> AccuracyCase:
    run = runs[2]
    return AccuracyCase(
        question=f"learning_rate của {run.run_name} là bao nhiêu?",
        tool="get_run",
        tool_args={"run_id": run.id},
        names=(),
        numbers=(run.hyperparams["learning_rate"],),
    )


def _missing_run_case(runs: list[Run]) -> AccuracyCase:
    return AccuracyCase(
        question=f"So sánh {runs[0].run_name} và run-999",
        tool="find_runs_by_name",
        tool_args={"run_names": [runs[0].run_name, "run-999"]},
        names=("run-999",),
    )


ACCURACY_CASES: dict[str, Callable[[list[Run]], AccuracyCase]] = {
    "best_val_accuracy": _best_val_accuracy_case,
    "lowest_val_loss": _lowest_val_loss_case,
    "compare": _compare_case,
    "diagnose_overfit": _diagnose_overfit_case,
    "diagnose_healthy": _diagnose_healthy_case,
    "hyperparameter": _hyperparameter_case,
    "missing_run": _missing_run_case,
}


def _numbers_in(text: str) -> list[str]:
    return _NUMBER.findall(text)


def _same_number(token: str, value: float) -> bool:
    """Whether `token` states `value`, allowing rounding and percentages but ignoring sign."""
    token = token.replace(",", ".")
    decimals = len(token.split(".")[1]) if "." in token and "e" not in token.lower() else 0
    stated = float(token)
    rounding = 0.5001 * 10**-decimals
    if abs(stated - abs(value)) <= (rounding if decimals >= 2 else 1e-9):
        return True
    return decimals >= 1 and abs(stated - abs(value) * 100) <= rounding


def _numbers_of(value: Any) -> Iterator[float]:
    if isinstance(value, bool):
        return
    if isinstance(value, int | float):
        yield value
    elif isinstance(value, dict):
        yield from _numbers_of(list(value.values()))
    elif isinstance(value, list):
        for item in value:
            yield from _numbers_of(item)


def _is_prose_count(token: str) -> bool:
    return token.isdigit() and int(token) <= _MAX_UNCHECKED_COUNT


def accuracy_problems(
    case: AccuracyCase, response: ChatResponse, messages: list[LLMMessage]
) -> list[str]:
    """Everything wrong with an answer; empty means it matches the database."""
    results = [json.loads(m.content) for m in messages if m.role == "tool"]
    known = [
        *_numbers_of(results),
        *(float(t.replace(",", ".")) for t in _numbers_in(case.question)),
    ]
    called = {tool_call.name for m in messages for tool_call in m.tool_calls}
    stated = _numbers_in(response.message)
    highlighted = {
        run_id
        for action in response.actions
        if action.type == "highlight_runs"
        for run_id in action.run_ids
    }

    problems = []
    if case.tool not in called:
        problems.append(f"never called {case.tool}")
    if case.verdict and case.verdict not in [r.get("verdict") for r in results]:
        problems.append(f"tool verdict is not {case.verdict}")
    problems += [
        f"does not name {name}"
        for name in case.names
        if name.casefold() not in response.message.casefold()
    ]
    problems += [
        f"does not state {number}"
        for number in case.numbers
        if not any(_same_number(token, number) for token in stated)
    ]
    problems += [
        f"states {token}, which no tool returned"
        for token in stated
        if not _is_prose_count(token) and not any(_same_number(token, v) for v in known)
    ]
    problems += [f"shows tool term {term}" for term in _TOOL_TERMS.findall(response.message)]
    if missing := set(case.highlighted) - highlighted:
        problems.append(f"did not highlight {sorted(missing)}")
    return problems


@dataclass
class RecordingLLM:
    """Passes calls to a real client and records the messages it was sent."""

    inner: LLMClient
    seen: list[list[LLMMessage]] = field(default_factory=list)

    async def complete(
        self, system: str, messages: list[LLMMessage], tools: list[ToolDefinition]
    ) -> LLMReply:
        self.seen.append(list(messages))
        return await self.inner.complete(system, messages, tools)


def faithful_llm(case: AccuracyCase, text: str | None = None) -> ScriptedLLM:
    """A model that calls the right tools and reports the expected numbers."""
    replies = [LLMReply(tool_calls=[call(case.tool, **case.tool_args)])]
    default = " ".join([*case.names, *(f"{abs(number):.4f}" for number in case.numbers)])
    replies.append(LLMReply(text=default if text is None else text))
    return ScriptedLLM(replies)


async def run_accuracy_case(
    session, name: str, make_llm: Callable[[AccuracyCase], Any]
) -> tuple[AccuracyCase, ChatResponse, list[LLMMessage]]:
    await seed_database(session, runs_per_experiment=30, now=ACCURACY_NOW)
    experiment_id = await session.scalar(
        select(Experiment.id).where(Experiment.name == PROFILES[0].name)
    )
    result = await session.scalars(
        select(Run)
        .options(selectinload(Run.metrics))
        .where(Run.experiment_id == experiment_id, Run.status == RunStatus.COMPLETED)
        .order_by(Run.id)
    )
    case = ACCURACY_CASES[name](list(result.all()))
    llm = make_llm(case)
    request = ChatRequest(message=case.question, experiment_id=experiment_id)
    response = await answer(session, llm, request)
    return case, response, llm.seen[-1]


@pytest.mark.parametrize("name", ACCURACY_CASES)
async def test_faithful_answer_matches_the_database(session, name):
    case, response, messages = await run_accuracy_case(session, name, faithful_llm)
    assert accuracy_problems(case, response, messages) == []


@pytest.mark.parametrize("name", ACCURACY_CASES)
async def test_invented_number_is_caught(session, name):
    def invents_a_number(case: AccuracyCase) -> ScriptedLLM:
        names_and_numbers = faithful_llm(case).replies[-1].text
        return faithful_llm(case, f"{names_and_numbers} 0.987654")

    case, response, messages = await run_accuracy_case(session, name, invents_a_number)

    assert accuracy_problems(case, response, messages) == [
        "states 0.987654, which no tool returned"
    ]


@pytest.mark.parametrize("name", ["best_val_accuracy", "compare", "diagnose_overfit"])
async def test_missing_number_is_caught(session, name):
    case, response, messages = await run_accuracy_case(
        session, name, lambda case: faithful_llm(case, " ".join(case.names))
    )
    assert any("does not state" in p for p in accuracy_problems(case, response, messages))


def test_numbers_are_found_but_names_are_skipped():
    text = "run-001 và resnet18 đạt **0,076**, 3D, gap -0.0039 (lr 1e-05) sau 13 epoch."
    assert _numbers_in(text) == ["0,076", "0.0039", "1e-05", "13"]


@pytest.mark.parametrize(
    ("token", "value", "same"),
    [
        ("0,0863", 0.0863, True),
        ("0.0039", -0.0039, True),  # the sign may be written in words
        ("0.9085", 0.90845, True),
        ("97.41", 0.9741, True),  # percentage
        ("0.12", 0.2, False),
        ("0.9", 0.9042, False),
        ("13", 14, False),
        ("1e-05", 0.00001, True),
    ],
)
def test_same_number(token, value, same):
    assert _same_number(token, value) is same


@pytest.mark.skipif(not os.getenv("COPILOT_LIVE"), reason="spends LLM quota; set COPILOT_LIVE=1")
@pytest.mark.parametrize("name", ACCURACY_CASES)
async def test_live_answer_matches_the_database(session, name):
    get_llm_client.cache_clear()  # its HTTP client is bound to one test's event loop

    case, response, messages = await run_accuracy_case(
        session, name, lambda _: RecordingLLM(get_llm_client())
    )
    await asyncio.sleep(LIVE_PAUSE_SECONDS)

    assert accuracy_problems(case, response, messages) == [], response.message
