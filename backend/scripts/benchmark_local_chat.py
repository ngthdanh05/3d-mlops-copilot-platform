"""Measure user-visible SSE latency and sample local runtime memory."""

import argparse
import ipaddress
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import psutil


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment_id", type=int)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    stop = threading.Event()
    samples = []
    external_connections, observation_errors = set(), set()

    def monitor():
        while not stop.is_set():
            processes = []
            for process in psutil.process_iter(["name", "memory_info"]):
                if (process.info.get("name") or "").lower() in {"ollama.exe", "llama-server.exe"}:
                    if process.info.get("memory_info"):
                        processes.append(process.info["memory_info"].rss)
                    try:
                        for connection in process.net_connections(kind="inet"):
                            if (
                                connection.raddr
                                and not ipaddress.ip_address(connection.raddr.ip).is_loopback
                            ):
                                external_connections.add(connection.raddr.ip)
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        observation_errors.add("Could not inspect every runtime connection")
            try:
                used = (
                    subprocess.check_output(
                        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                    )
                    .strip()
                    .splitlines()[0]
                )
                samples.append(
                    {
                        "gpu_used_mib_system": int(used),
                        "runtime_rss_bytes": sum(processes),
                        "available_ram_bytes": psutil.virtual_memory().available,
                    }
                )
            except (OSError, subprocess.SubprocessError):
                pass
            stop.wait(1)

    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()
    started, first, final = time.perf_counter(), None, None
    try:
        with httpx.Client(timeout=600, trust_env=False) as client:
            with client.stream(
                "POST",
                "http://127.0.0.1:8000/api/copilot/chat/stream",
                json={
                    "message": "Run nào tốt nhất theo val_accuracy?",
                    "experiment_id": args.experiment_id,
                },
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    event = json.loads(line[6:])
                    if event["type"] == "delta" and first is None:
                        first = time.perf_counter() - started
                    if event["type"] == "done":
                        final = event
    finally:
        stop.set()
        monitor_thread.join(timeout=5)
    report = {
        "user_first_text_seconds": first,
        "total_seconds": time.perf_counter() - started,
        "peak_system_gpu_used_mib": max((s["gpu_used_mib_system"] for s in samples), default=0),
        "peak_runtime_rss_bytes": max((s["runtime_rss_bytes"] for s in samples), default=0),
        "min_available_ram_bytes": min((s["available_ram_bytes"] for s in samples), default=0),
        "answer": final,
        "runtime_external_connections_observed": sorted(external_connections),
        "observation_errors": sorted(observation_errors),
        "samples": samples,
        "note": "1 second samples; GPU usage includes desktop/browser, not just LLM",
    }
    output = root / "artifacts/chat-benchmark.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"samples", "answer"}}))
    if final is None or not final.get("actions"):
        raise RuntimeError("Chat benchmark did not produce a grounded best-run answer")


if __name__ == "__main__":
    main()
