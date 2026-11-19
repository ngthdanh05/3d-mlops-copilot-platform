"""Write a secret-free inventory and exercise real forward/backward on chosen device."""

import argparse
import importlib.metadata
import platform
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psutil
import torch
import torchvision

from training.data import atomic_json, resolve
from training.models import build_model, device_for


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    args = parser.parse_args()
    memory = psutil.virtual_memory()
    report = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": str(torch.__version__),
        "torchvision": str(torchvision.__version__),
        "cuda_build": torch.version.cuda,
        "cuda_available": torch.cuda.is_available(),
        "ram_total_bytes": memory.total,
        "ram_available_bytes": memory.available,
        "disk_free_bytes": shutil.disk_usage(resolve(".")).free,
        "packages": {
            dist.metadata["Name"]: dist.version
            for dist in importlib.metadata.distributions()
            if dist.metadata["Name"]
        },
    }
    if shutil.which("nvidia-smi"):
        report["gpu_driver"] = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total,memory.free",
                "--format=csv,noheader",
            ],
            text=True,
        ).strip()
    device = device_for(args.device)
    model = build_model().to(device)
    output = model(torch.randn(2, 3, 32, 32, device=device))
    output.sum().backward()
    if device.type == "cuda":
        torch.cuda.synchronize()
    report.update(device=str(device), forward_backward_passed=True, output_shape=list(output.shape))
    atomic_json(resolve("artifacts/environment.json"), report)
    print(report)


if __name__ == "__main__":
    main()
