import json

from app.main import app
from app.services.copilot.grounded import render_grounded
from app.services.copilot.llm_client import LLMReply, ToolCall, get_llm_client


async def test_local_stream_cannot_show_reversed_winners_or_invented_metrics(client):
    exp = (await client.post("/api/experiments", json={"name": "real-fixture"})).json()["id"]
    ids = []
    for name, accuracy, loss in [("A", 0.691, 0.876), ("B", 0.6946, 0.8891)]:
        run = (await client.post("/api/runs", json={"experiment_id": exp, "run_name": name})).json()
        ids.append(run["id"])
        await client.post(
            f"/api/runs/{run['id']}/metrics",
            json={
                "epoch": 1,
                "accuracy": accuracy,
                "loss": loss,
                "val_accuracy": accuracy,
                "val_loss": loss,
            },
        )
        await client.put(f"/api/runs/{run['id']}", json={"status": "completed"})

    class Local:
        ground_tool_results = True

        async def stream(self, system, messages, tools):
            if any(message.role == "tool" for message in messages):
                yield "WRONG winner A accuracy 0.9999"
                yield LLMReply(text="WRONG winner A accuracy 0.9999")
            else:
                yield LLMReply(tool_calls=[ToolCall("1", "compare_runs", {"run_ids": ids})])

    app.dependency_overrides[get_llm_client] = Local
    response = await client.post(
        "/api/copilot/chat/stream", json={"message": "So sánh A và B", "experiment_id": exp}
    )
    events = [
        json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")
    ]
    assert "WRONG" not in response.text and "0.9999" not in response.text
    assert "**B** tốt nhất về val_accuracy" in events[-1]["message"]
    assert "**A** tốt nhất về val_loss" in events[-1]["message"]
    assert {"type": "focus_camera", "run_id": ids[1]} in events[-1]["actions"]


async def test_local_ambiguous_run_is_rejected_before_model_can_choose_one(client):
    for name in ["experiment-a", "experiment-b"]:
        exp = (await client.post("/api/experiments", json={"name": name})).json()["id"]
        await client.post("/api/runs", json={"experiment_id": exp, "run_name": "duplicate-run"})

    class Local:
        ground_tool_results = True

        async def complete(self, *args):
            raise AssertionError("Ambiguity must be resolved before an LLM call")

    app.dependency_overrides[get_llm_client] = Local
    response = await client.post(
        "/api/copilot/chat", json={"message": "duplicate-run có overfit không?"}
    )
    assert response.json()["actions"] == []
    assert "chọn experiment" in response.json()["message"]


def test_grounded_overfitting_labels_smoothed_values_and_preserves_real_name():
    result = render_grounded(
        "detect_overfitting",
        {
            "run_name": "small-cnn-real",
            "verdict": "no_overfitting",
            "accuracy_gap": {"start": 0.0012, "end": 0.0095},
            "val_loss_trend": {"lowest": 0.876, "lowest_epoch": 4, "final": 0.9319},
        },
        "Có dấu hiệu overfit không?",
    )
    assert "small-cnn-real" in result
    assert "0.0012 → 0.0095" in result
    assert "trung bình cửa sổ cuối 0.9319" in result
    assert "không phải bằng chứng tuyệt đối" in result


def test_grounded_best_keeps_small_learning_rate_and_final_epoch_semantics():
    result = render_grounded(
        "find_best_runs",
        {
            "metric": "val_accuracy",
            "median_value": 0.7,
            "runs": [
                {
                    "run_name": "r",
                    "value": 0.8,
                    "hyperparams": {"learning_rate": 1e-6, "batch_size": 32},
                }
            ],
        },
        "best run?",
    )
    assert "learning_rate=1e-06" in result
    assert "last logged epoch" in result


def test_grounded_missing_validation_does_not_guess():
    result = render_grounded(
        "detect_overfitting",
        {
            "run_name": "r",
            "verdict": "insufficient_data",
            "accuracy_gap": None,
            "val_loss_trend": None,
        },
        "r có bị overfit không?",
    )
    assert "chưa đủ dữ liệu validation" in result
