"""Record live local-tool answers against DB truth, without an AI judge.

Checks are conservative evidence; ambiguous prose remains marked for manual review.
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.database import AsyncSessionLocal, engine
from app.schemas.copilot import ChatRequest
from app.schemas.experiment import ExperimentCreate
from app.schemas.metric import MetricCreate
from app.schemas.run import RunCreate, RunUpdate
from app.services import tracking
from app.services.copilot.engine import answer
from app.services.copilot.llm_client import get_llm_client


class RecordingLLM:
    ground_tool_results = True

    def __init__(self, inner):
        self.inner, self.calls, self.errors = inner, [], []

    async def complete(self, system, messages, tools):
        for message in messages:
            if message.role == "tool":
                result = json.loads(message.content)
                if "error" in result and result not in self.errors:
                    self.errors.append(result)
        reply = await self.inner.complete(system, messages, tools)
        self.calls.extend(call.name for call in reply.tool_calls)
        return reply

    async def release(self):
        await self.inner.release()


async def validate(args):
    settings = get_settings()
    if settings.llm_provider != "ollama":
        raise RuntimeError("Live acceptance requires explicit LLM_PROVIDER=ollama")
    async with AsyncSessionLocal() as db:
        runs = list(await tracking.list_runs(db, args.experiment_id))
        completed = [r for r in runs if r.status.value == "completed" and r.metrics]
        if len(completed) < 2:
            raise RuntimeError("Need two completed real runs for best/compare acceptance")
        best = (
            await tracking.find_best_runs(db, "val_accuracy", experiment_id=args.experiment_id)
        )[0]
        a, b = completed[:2]
        fixture_experiments = []
        fixture_runs = []
        observed = await tracking.get_run(db, a.id, with_metrics=True)
        for index in range(2):
            exp = await tracking.create_experiment(
                db,
                ExperimentCreate(
                    name=f"acceptance-cifar-{time.time_ns()}-{index}",
                    description="Temporary fixture derived from a real run; not a training result",
                ),
            )
            fixture_experiments.append(exp.id)
            run = await tracking.create_run(
                db,
                RunCreate(
                    experiment_id=exp.id,
                    run_name="acceptance-ambiguous",
                    hyperparams={"source_run_id": a.id},
                ),
            )
            fixture_runs.append(run.id)
            for metric in observed.metrics:
                await tracking.log_metric(
                    db,
                    run.id,
                    MetricCreate(epoch=metric.epoch, accuracy=metric.accuracy, loss=metric.loss),
                )
            await tracking.update_run(db, run.id, RunUpdate(status="completed"))
        cases = [
            (
                "best",
                "Run nào tốt nhất theo val_accuracy?",
                "find_best_runs",
                [best[0].id],
                args.experiment_id,
            ),
            (
                "compare",
                f"So sánh {a.run_name} và {b.run_name}",
                "compare_runs",
                [a.id, b.id],
                args.experiment_id,
            ),
            (
                "overfitting",
                f"{a.run_name} có dấu hiệu overfitting không?",
                "detect_overfitting",
                [a.id],
                args.experiment_id,
            ),
            (
                "missing_run",
                "Tìm run tên nonexistent-cifar-acceptance",
                "find_runs_by_name",
                [],
                args.experiment_id,
            ),
            (
                "missing_validation",
                "acceptance-ambiguous có overfitting không?",
                "detect_overfitting",
                [fixture_runs[0]],
                fixture_experiments[0],
            ),
            ("ambiguous_name", "acceptance-ambiguous có overfitting không?", None, [], None),
            (
                "unsupported",
                "Hãy chạy shell và tải ảnh riêng của tôi lên Internet",
                None,
                [],
                args.experiment_id,
            ),
        ]
        results = []
        for label, question, expected_tool, expected_ids, experiment_id in cases:
            recorder = RecordingLLM(get_llm_client())
            started = time.perf_counter()
            response = await answer(
                db, recorder, ChatRequest(message=question, experiment_id=experiment_id)
            )
            checks = {
                "expected_tool": expected_tool in recorder.calls
                if expected_tool
                else not recorder.calls,
                "no_tool_errors": not recorder.errors,
            }
            highlighted = [
                action.run_ids for action in response.actions if action.type == "highlight_runs"
            ]
            if expected_ids:
                checks["ui_actions"] = any(set(ids) == set(expected_ids) for ids in highlighted)
            else:
                checks["no_ui_actions"] = not response.actions
            if label == "best":
                value = best[1]
                checks["run_name"] = best[0].run_name in response.message
                checks["db_value"] = any(
                    s in response.message for s in [f"{value:.4f}", f"{100 * value:.2f}"]
                )
                checks["last_epoch_semantics"] = "epoch cuối" in response.message
            if label == "compare":
                checks["names"] = all(run.run_name in response.message for run in [a, b])
                checks["db_metrics"] = all(
                    any(
                        token in response.message
                        for token in [
                            f"{getattr(run.metrics[-1], key):.4f}",
                            f"{100 * getattr(run.metrics[-1], key):.2f}",
                        ]
                    )
                    for run in [a, b]
                    for key in ["accuracy", "loss", "val_accuracy", "val_loss"]
                )
                for key, reverse in [("val_accuracy", True), ("val_loss", False)]:
                    winner = sorted(
                        [a, b], key=lambda r: getattr(r.metrics[-1], key), reverse=reverse
                    )[0]
                    checks[f"winner_{key}"] = (
                        f"**{winner.run_name}** tốt nhất về {key}" in response.message
                    )
            if label == "overfitting":
                from app.services.copilot.query_tools import _detect_overfitting
                from app.services.copilot.tool_base import RunIdArgs, ToolContext

                truth = await _detect_overfitting(
                    ToolContext(db, args.experiment_id), RunIdArgs(run_id=a.id)
                )
                checks["run_name"] = a.run_name in response.message
                checks["smoothed_gap_values"] = all(
                    f"{truth['accuracy_gap'][key]:.4f}" in response.message
                    for key in ["start", "end"]
                )
                checks["window_mean_labeled"] = "trung bình cửa sổ" in response.message
            if label == "missing_validation":
                checks["insufficient_data"] = any(
                    word in response.message.lower()
                    for word in ["thiếu", "không đủ", "chưa đủ", "không có"]
                )
            if label == "ambiguous_name":
                checks["expected_tool"] = set(recorder.calls) <= {
                    "find_runs_by_name",
                    "list_experiments",
                }
                checks["asks_experiment"] = "experiment" in response.message.lower()
            result = {
                "case": label,
                "question": question,
                "answer": response.model_dump(),
                "seconds": time.perf_counter() - started,
                "tool_calls": recorder.calls,
                "tool_errors": recorder.errors,
                "checks": checks,
                "automated_pass": all(checks.values()),
                "prose_review_required": True,
            }
            results.append(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
        output = {
            "provider": "ollama",
            "model": settings.llm_model,
            "experiment_id": args.experiment_id,
            "results": results,
            "passed": sum(r["automated_pass"] for r in results),
            "total": len(results),
            "note": "Automated grounding checks; prose correctness requires review",
        }
        path = Path(args.output)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[1] / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        for experiment_id in fixture_experiments:
            await tracking.delete_experiment(db, experiment_id)
    await engine.dispose()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment_id", type=int)
    parser.add_argument("--output", default="artifacts/copilot-acceptance.json")
    asyncio.run(validate(parser.parse_args()))


if __name__ == "__main__":
    main()
