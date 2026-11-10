"""End-to-end smoke test: backend + seeded data + frontend + a real browser.

Runs on separate ports with a temporary database, so it can run beside your dev servers.
The copilot uses the stand-in LLM unless --real-llm is given.

Usage (from backend/):
    uv run python scripts/smoke_test.py
    uv run python scripts/smoke_test.py --no-browser
    uv run python scripts/smoke_test.py --real-llm --screenshots ../docs/screenshots
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import httpx
from local_stack import (
    BACKEND_DIR,
    BACKEND_URL,
    FRONTEND_URL,
    StackError,
    database_url,
    find_python,
    run_node_script,
    running_backend,
    running_frontend,
    use_utf8_output,
)

EXPECTED_EXPERIMENTS = 2
RUNS_PER_EXPERIMENT = 15


class SmokeFailure(Exception):
    pass


def report(step: str) -> None:
    print(f"[ok] {step}", flush=True)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def get_json(base_url: str, path: str) -> Any:
    response = httpx.get(f"{base_url}{path}", timeout=10)
    require(response.status_code == 200, f"GET {path} trả về {response.status_code}")
    return response.json()


def seed(db_url: str) -> None:
    command = [
        str(find_python()),
        "-m",
        "app.utils.seed_data",
        "--runs-per-experiment",
        str(RUNS_PER_EXPERIMENT),
    ]
    subprocess.run(
        command,
        cwd=BACKEND_DIR,
        env={**os.environ, "DATABASE_URL": db_url},
        check=True,
        capture_output=True,
    )


def check_api() -> int:
    """Returns the id of the first experiment."""
    experiments = get_json(BACKEND_URL, "/api/experiments")
    require(len(experiments) == EXPECTED_EXPERIMENTS, f"Có {len(experiments)} experiment")
    experiment_id = experiments[0]["id"]

    runs = get_json(BACKEND_URL, f"/api/runs?experiment_id={experiment_id}")
    require(len(runs) == RUNS_PER_EXPERIMENT, f"Có {len(runs)} run")
    require(any(run["final_val_accuracy"] is not None for run in runs), "Run không có metrics")
    report(f"GET /api/runs trả về {len(runs)} run kèm metrics")

    detail = get_json(BACKEND_URL, f"/api/runs/{runs[0]['id']}")
    require(len(detail["metrics"]) > 0, "Chi tiết run không có metrics theo epoch")
    report("GET /api/runs/{id} có metrics theo từng epoch")
    return experiment_id


def check_copilot(experiment_id: int) -> None:
    response = httpx.post(
        f"{BACKEND_URL}/api/copilot/chat",
        json={"message": "Run nào tốt nhất?", "experiment_id": experiment_id},
        timeout=30,
    )
    require(response.status_code == 200, f"Copilot trả về {response.status_code}")
    action_types = {action["type"] for action in response.json()["actions"]}
    require({"highlight_runs", "focus_camera"} <= action_types, f"Thiếu action: {action_types}")
    report("POST /api/copilot/chat trả về highlight_runs và focus_camera")


def check_frontend(experiment_id: int) -> None:
    html = httpx.get(FRONTEND_URL, timeout=10)
    require(html.status_code == 200 and 'id="root"' in html.text, "Frontend không trả về trang")
    runs = get_json(FRONTEND_URL, f"/api/runs?experiment_id={experiment_id}")
    require(len(runs) == RUNS_PER_EXPERIMENT, "Proxy của Vite không tới được backend")
    report("Frontend chạy và proxy /api tới được backend")


def run(args: argparse.Namespace) -> None:
    # Cleanup errors are ignored: Windows may still hold the SQLite file for a moment.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temp:
        temp_dir = Path(temp)
        db_url = database_url(temp_dir / "smoke.db")
        with running_backend(db_url, temp_dir, real_llm=args.real_llm):
            report("Backend khởi động, /api/health phản hồi")
            seed(db_url)
            report(f"Seed {EXPECTED_EXPERIMENTS} experiment, mỗi cái {RUNS_PER_EXPERIMENT} run")
            experiment_id = check_api()
            if not args.real_llm:
                check_copilot(experiment_id)
            with running_frontend(temp_dir):
                check_frontend(experiment_id)
                if args.no_browser:
                    return
                extra = (
                    ["--screenshots", str(args.screenshots.resolve())] if args.screenshots else []
                )
                run_node_script("browser-smoke.mjs", FRONTEND_URL, *extra)


def main() -> int:
    use_utf8_output()
    parser = argparse.ArgumentParser(description="End-to-end smoke test.")
    parser.add_argument("--no-browser", action="store_true", help="skip the browser checks")
    parser.add_argument("--real-llm", action="store_true", help="use the key in .env (uses quota)")
    parser.add_argument("--screenshots", type=Path, help="directory to save screenshots to")
    args = parser.parse_args()
    try:
        run(args)
    except (SmokeFailure, StackError, subprocess.CalledProcessError, httpx.HTTPError) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    print("Smoke test đạt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
