"""Measure 3D FPS, API latency and copilot latency, and write docs/performance.md.

Uses a temporary database of synthetic runs on separate ports, so it can run beside your
dev servers. The copilot section calls the real LLM with that synthetic data and spends
quota (about 40 calls); without --real-llm it measures the stand-in instead.

Usage (from backend/):
    uv run python scripts/benchmark.py --real-llm
    uv run python scripts/benchmark.py --skip-fps --output -
"""

import argparse
import asyncio
import json
import platform
import random
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import median

import httpx
from local_stack import (
    BACKEND_DIR,
    BACKEND_URL,
    FRONTEND_DIR,
    FRONTEND_URL,
    database_url,
    find_tool,
    running_backend,
    running_frontend,
    use_utf8_output,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.database import Base
from app.models import Experiment
from app.utils.seed_data import PROFILES, generate_experiment_runs

NODE_COUNTS = (50, 100, 200, 500)
API_SAMPLES = 200
FPS_TARGET = 58.0  # a 60 Hz display reports just under 60
FPS_TARGET_NODES = 200
API_P95_TARGET_MS = 200
AI_TARGET_S = 8
AI_ROUNDS = 3  # one reading is mostly provider noise
AI_PAUSE_S = 13  # stays inside the Gemini free tier's requests per minute
AI_EXPERIMENT_RUNS = 50
AI_QUESTIONS = (
    "Run nào có val_accuracy cao nhất?",
    "So sánh run-001 với run-002",
    "run-003 có bị overfitting không?",
    "Tóm tắt kết quả của experiment này",
    "Run nào có val_loss thấp nhất?",
)
_FAILED_ANSWER_PREFIXES = ("Trợ lý AI đang gặp sự cố", "Đã chạm giới hạn", "Trợ lý AI không đưa ra")
_DEFAULT_OUTPUT = BACKEND_DIR.parent / "docs" / "performance.md"


@dataclass(frozen=True)
class Latency:
    name: str
    p50_ms: float
    p95_ms: float


@dataclass(frozen=True)
class AiSample:
    question: str
    first_text_s: float | None
    total_s: float
    is_ok: bool


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * fraction))]


async def seed(db_url: str) -> dict[int, int]:
    """Creates one `bench-<n>` experiment per node count. Returns {node count: experiment id}."""
    engine = create_async_engine(db_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    now = datetime.now(UTC).replace(microsecond=0)
    rng = random.Random(42)
    experiment_ids: dict[int, int] = {}
    async with AsyncSession(engine, expire_on_commit=False) as session:
        for count in NODE_COUNTS:
            generated = generate_experiment_runs(rng, PROFILES[0], count, now)
            for index, run in enumerate(generated):  # the free-form names must stay unique
                run.run_name = f"run-{index + 1:03d}"
            experiment = Experiment(name=f"bench-{count}", created_at=now)
            experiment.runs = [run.to_orm() for run in generated]
            session.add(experiment)
            await session.flush()
            experiment_ids[count] = experiment.id
        await session.commit()
    await engine.dispose()
    return experiment_ids


def timed(name: str, request: Callable[[int], httpx.Response]) -> Latency:
    samples: list[float] = []
    for index in range(API_SAMPLES):
        started = time.perf_counter()
        response = request(index)
        samples.append((time.perf_counter() - started) * 1000)
        response.raise_for_status()
    print(f"[ok] {name}: p95 {percentile(samples, 0.95):.1f} ms", file=sys.stderr, flush=True)
    return Latency(name, median(samples), percentile(samples, 0.95))


def measure_api(experiment_ids: dict[int, int]) -> list[Latency]:
    with httpx.Client(base_url=BACKEND_URL, timeout=30) as client:
        runs = client.get("/api/runs", params={"experiment_id": experiment_ids[200]}).json()
        full_run_id = max(runs, key=lambda run: run["final_epoch"] or 0)["id"]
        logging_run_id = client.post(
            "/api/runs", json={"experiment_id": experiment_ids[50], "run_name": "bench-writes"}
        ).json()["id"]
        metric = {"accuracy": 0.9, "loss": 0.1, "val_accuracy": 0.8, "val_loss": 0.2}
        latencies = [
            timed("GET /api/health", lambda _: client.get("/api/health")),
            timed("GET /api/experiments", lambda _: client.get("/api/experiments")),
        ]
        for count in NODE_COUNTS:
            latencies.append(
                timed(
                    f"GET /api/runs ({count} run)",
                    lambda _, count=count: client.get(
                        "/api/runs", params={"experiment_id": experiment_ids[count]}
                    ),
                )
            )
        latencies.extend(
            [
                timed("GET /api/runs/{id}", lambda _: client.get(f"/api/runs/{full_run_id}")),
                timed(
                    "POST /api/runs/{id}/metrics",
                    lambda index: client.post(
                        f"/api/runs/{logging_run_id}/metrics", json={"epoch": index + 1, **metric}
                    ),
                ),
                timed(
                    "POST /api/copilot/chat (LLM giả lập, 200 run)",
                    lambda _: client.post(
                        "/api/copilot/chat",
                        json={
                            "message": "Run nào tốt nhất?",
                            "experiment_id": experiment_ids[200],
                        },
                    ),
                ),
            ]
        )
    return latencies


def ask(client: httpx.Client, question: str, experiment_id: int) -> AiSample:
    """Time until the first streamed text, and until the final answer arrives."""
    started = time.perf_counter()
    first_text: float | None = None
    message = ""
    with client.stream(
        "POST",
        "/api/copilot/chat/stream",
        json={"message": question, "experiment_id": experiment_id},
    ) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line.startswith("data: "):
                continue
            event = json.loads(line[6:])
            if event["type"] == "delta" and first_text is None:
                first_text = time.perf_counter() - started
            elif event["type"] == "done":
                message = event["message"]
    total = time.perf_counter() - started
    is_ok = bool(message) and not message.startswith(_FAILED_ANSWER_PREFIXES)
    return AiSample(question, first_text, total, is_ok)


def measure_ai(experiment_id: int, pause_s: float) -> list[AiSample]:
    samples: list[AiSample] = []
    with httpx.Client(base_url=BACKEND_URL, timeout=90) as client:
        for index, question in enumerate(AI_QUESTIONS * AI_ROUNDS):
            if index:
                time.sleep(pause_s)
            sample = ask(client, question, experiment_id)
            state = "ok" if sample.is_ok else "LỖI"
            print(f"[{state}] {question}: {sample.total_s:.1f} s", file=sys.stderr, flush=True)
            samples.append(sample)
    return samples


def measure_fps() -> dict:
    node = find_tool("node")
    script = FRONTEND_DIR / "scripts" / "benchmark-fps.mjs"
    counts = [str(count) for count in NODE_COUNTS]
    finished = subprocess.run(
        [node, str(script), FRONTEND_URL, *counts],
        cwd=FRONTEND_DIR,
        check=True,
        stdout=subprocess.PIPE,
        encoding="utf-8",
    )
    return json.loads(finished.stdout.strip().splitlines()[-1])


def mark(passed: bool) -> str:
    return "✅ Đạt" if passed else "❌ Không đạt"


def fps_section(fps: dict | None) -> list[str]:
    if fps is None:
        return ["## 3D FPS", "", "Không đo trong lần chạy này.", ""]
    rows = [
        f"| {r['nodes']} | {r['idle']['fps']:.1f} | {r['orbit']['fps']:.1f} "
        f"| {r['orbit']['p95FrameMs']:.1f} |"
        for r in fps["results"]
    ]
    at_target = next(r for r in fps["results"] if r["nodes"] == FPS_TARGET_NODES)
    worst = min(at_target["idle"]["fps"], at_target["orbit"]["fps"])
    return [
        "## 3D FPS",
        "",
        f"GPU: `{fps['renderer']}`. Bản build production, khung nhìn 1600×900. Mỗi mức đo "
        "6 giây khi đứng yên và 6 giây khi kéo xoay camera liên tục.",
        "",
        "| Số node | FPS đứng yên | FPS khi xoay | p95 thời gian khung hình khi xoay (ms) |",
        "| ---: | ---: | ---: | ---: |",
        *rows,
        "",
        f"**Mục tiêu {FPS_TARGET_NODES} node @ 60 fps:** {mark(worst >= FPS_TARGET)} "
        f"(thấp nhất {worst:.1f} fps).",
        "",
    ]


def api_section(latencies: list[Latency]) -> list[str]:
    rows = [f"| `{item.name}` | {item.p50_ms:.1f} | {item.p95_ms:.1f} |" for item in latencies]
    in_scope = [item for item in latencies if "copilot" not in item.name]
    worst = max(in_scope, key=lambda item: item.p95_ms)
    return [
        "## Thời gian phản hồi API",
        "",
        f"{API_SAMPLES} request tuần tự mỗi endpoint, đo từ client trên cùng máy, "
        "database SQLite có 850 run.",
        "",
        "| Endpoint | p50 (ms) | p95 (ms) |",
        "| --- | ---: | ---: |",
        *rows,
        "",
        f"**Mục tiêu p95 < {API_P95_TARGET_MS} ms:** {mark(worst.p95_ms < API_P95_TARGET_MS)} "
        f"(chậm nhất: `{worst.name}`, {worst.p95_ms:.1f} ms).",
        "",
    ]


def ai_section(samples: list[AiSample], real_llm: bool) -> list[str]:
    provider = "Gemini thật" if real_llm else "LLM giả lập (chưa phản ánh độ trễ thật)"
    rows = []
    for question in AI_QUESTIONS:
        asked = [s for s in samples if s.question == question]
        times = [s.total_s for s in asked]
        first = [s.first_text_s for s in asked if s.first_text_s is not None]
        first_text = f"{median(first):.2f}" if first else "—"
        ok_count = sum(s.is_ok for s in asked)
        rows.append(
            f"| {question} | {first_text} | {median(times):.2f} | {max(times):.2f} "
            f"| {ok_count}/{len(asked)} |"
        )
    answered = [s.total_s for s in samples if s.is_ok]
    lines = [
        "## Thời gian trả lời của AI (end-to-end)",
        "",
        f"Nhà cung cấp: {provider}. Đo qua `POST /api/copilot/chat/stream`, gồm toàn bộ các "
        f"vòng gọi tool. Experiment có {AI_EXPERIMENT_RUNS} run, mỗi câu hỏi {AI_ROUNDS} lần.",
        "",
        "| Câu hỏi | Chữ đầu tiên, trung vị (s) | Hoàn tất, trung vị (s) "
        "| Chậm nhất (s) | Trả lời được |",
        "| --- | ---: | ---: | ---: | --- |",
        *rows,
        "",
    ]
    if answered:
        slowest = max(answered)
        lines.append(
            f"**Mục tiêu < {AI_TARGET_S} s:** {mark(slowest < AI_TARGET_S)} "
            f"(trung vị {median(answered):.2f} s, chậm nhất {slowest:.2f} s, "
            f"{len(answered)}/{len(samples)} câu trả lời được)."
        )
    else:
        lines.append(f"**Mục tiêu < {AI_TARGET_S} s:** ❌ Không đo được, không câu nào thành công.")
    return [*lines, ""]


def render(fps: dict | None, latencies: list[Latency], ai: list[AiSample], real_llm: bool) -> str:
    today = datetime.now(UTC).date().isoformat()
    lines = [
        "# Hiệu năng",
        "",
        "> Tệp này do `backend/scripts/benchmark.py` sinh ra. Đừng sửa tay, hãy chạy lại script.",
        "",
        f"Đo ngày {today} trên `{platform.system()} {platform.release()}`, "
        "backend và frontend chạy cùng máy, dữ liệu giả lập.",
        "",
        *fps_section(fps),
        *api_section(latencies),
        *ai_section(ai, real_llm),
        "## Chạy lại",
        "",
        "```bash",
        "cd backend",
        "uv run python scripts/benchmark.py --real-llm",
        "```",
        "",
    ]
    return "\n".join(lines)


def run(args: argparse.Namespace) -> str:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        temp_dir = Path(temp)
        db_url = database_url(temp_dir / "benchmark.db")
        experiment_ids = asyncio.run(seed(db_url))
        with running_backend(db_url, temp_dir):
            latencies = measure_api(experiment_ids)
            fps = None
            if not args.skip_fps:
                with running_frontend(temp_dir, production=True):
                    fps = measure_fps()
        with running_backend(db_url, temp_dir, real_llm=args.real_llm):
            pause_s = AI_PAUSE_S if args.real_llm else 0
            ai = measure_ai(experiment_ids[AI_EXPERIMENT_RUNS], pause_s)
    return render(fps, latencies, ai, args.real_llm)


def main() -> int:
    use_utf8_output()
    parser = argparse.ArgumentParser(description="Measure performance; write docs/performance.md.")
    parser.add_argument("--real-llm", action="store_true", help="use the key in .env (uses quota)")
    parser.add_argument("--skip-fps", action="store_true", help="skip the browser measurement")
    parser.add_argument(
        "--output", default=str(_DEFAULT_OUTPUT), help="file to write, - for stdout"
    )
    args = parser.parse_args()
    report = run(args)
    if args.output == "-":
        print(report)
    else:
        Path(args.output).write_text(report, encoding="utf-8", newline="\n")
        print(f"Đã ghi {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
