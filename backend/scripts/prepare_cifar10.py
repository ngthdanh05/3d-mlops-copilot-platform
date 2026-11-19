"""The only CIFAR CLI allowed to download data."""

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from torchvision.datasets import CIFAR10
from torchvision.datasets.utils import check_integrity

from training.data import atomic_json, resolve, split_manifest


def parallel_download(root):
    """Optional range download from the official origin; loader still checks MD5."""
    root.mkdir(parents=True, exist_ok=True)
    archive = root / CIFAR10.filename
    if check_integrity(str(archive), CIFAR10.tgz_md5):
        return
    url = "https://www.cs.toronto.edu/~kriz/cifar-10-python.tar.gz"
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        response = client.head(url)
        response.raise_for_status()
        size = int(response.headers["content-length"])
    count = 8
    chunk_size = (size + count - 1) // count

    def download_part(index):
        start, end = index * chunk_size, min(size, (index + 1) * chunk_size) - 1
        part = root / f"cifar-download-{index}.part"
        with httpx.Client(timeout=120, follow_redirects=True) as client:
            with client.stream("GET", url, headers={"Range": f"bytes={start}-{end}"}) as reply:
                if reply.status_code != 206:
                    raise RuntimeError("Official server did not honor range request")
                with part.open("wb") as output:
                    for chunk in reply.iter_bytes(1024 * 1024):
                        output.write(chunk)
        if part.stat().st_size != end - start + 1:
            raise RuntimeError("Incomplete dataset download")
        print(f"Downloaded official CIFAR part {index + 1}/{count}", flush=True)
        return part

    with ThreadPoolExecutor(max_workers=count) as pool:
        parts = list(pool.map(download_part, range(count)))
    temporary = root / "cifar-10-python.tar.gz.tmp"
    with temporary.open("wb") as output:
        for part in parts:
            with part.open("rb") as source:
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)
    if not check_integrity(str(temporary), CIFAR10.tgz_md5):
        raise RuntimeError("Downloaded archive failed official MD5 integrity check")
    temporary.replace(archive)
    for part in parts:
        part.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/cifar10")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--parallel-download", action="store_true")
    args = parser.parse_args()
    root = resolve(args.data)
    if args.parallel_download:
        parallel_download(root)
    train = CIFAR10(str(root), train=True, download=True)
    test = CIFAR10(str(root), train=False, download=True)
    if len(train) != 50_000 or len(test) != 10_000:
        raise ValueError("Unexpected official CIFAR-10 size")
    manifest = split_manifest(train.targets, args.seed, data=train.data)
    atomic_json(root / f"split-{args.seed}.json", manifest)
    print(f"Prepared {root}; split={manifest['split_id']} (45000/5000/10000)")


if __name__ == "__main__":
    main()
