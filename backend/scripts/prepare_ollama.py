"""Online-only portable Windows runtime preparation; no system-wide installation."""

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

BACKEND = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version", default="v0.40.16", help="Verified version, or explicit latest"
    )
    args = parser.parse_args()
    root = BACKEND / ".cache/ollama"
    root.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        release_path = (
            "latest" if args.version == "latest" else "tags/" + quote(args.version, safe="")
        )
        release = client.get("https://api.github.com/repos/ollama/ollama/releases/" + release_path)
        release.raise_for_status()
        release = release.json()
        asset = next(a for a in release["assets"] if a["name"] == "ollama-windows-amd64.zip")
        archive = root / asset["name"]
        if not archive.exists() or archive.stat().st_size != asset["size"]:
            with client.stream("GET", asset["browser_download_url"]) as response:
                response.raise_for_status()
                with archive.open("wb") as output:
                    for chunk in response.iter_bytes(1024 * 1024):
                        output.write(chunk)
        with archive.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        if asset.get("digest") != f"sha256:{digest}":
            raise ValueError("Runtime archive SHA256 does not match GitHub release digest")
        with zipfile.ZipFile(archive) as package:
            for name in package.namelist():
                if not (root / name).resolve().is_relative_to(root.resolve()):
                    raise ValueError("Unsafe archive member")
            package.extractall(root)
        (root / "runtime.json").write_text(
            json.dumps(
                {
                    "version": release["tag_name"],
                    "sha256": digest,
                    "source": asset["browser_download_url"],
                }
            ),
            encoding="utf-8",
        )
        print(
            json.dumps({"version": release["tag_name"], "bytes": asset["size"], "sha256": digest})
        )


if __name__ == "__main__":
    main()
