"""Run a Python script with socket/DNS egress blocked except literal loopback.

This guards this Python process only, not Go runtimes or other applications.
"""

import ipaddress
import runpy
import socket
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/run_offline.py scripts/train_cifar10.py [args]")
    backend = Path(__file__).resolve().parents[1]
    script = Path(sys.argv[1])
    if not script.is_absolute():
        script = backend / script
    sys.path.insert(0, str(backend))
    original_connect, original_dns = socket.socket.connect, socket.getaddrinfo

    def allow(host):
        if host == "localhost":
            return
        try:
            if ipaddress.ip_address(host).is_loopback:
                return
        except ValueError:
            pass
        raise RuntimeError(f"Offline guard blocked external network/DNS: {host}")

    def connect(sock, address):
        if isinstance(address, tuple):
            allow(address[0])
        return original_connect(sock, address)

    def dns(host, *args, **kwargs):
        allow(host)
        return original_dns(host, *args, **kwargs)

    socket.socket.connect = connect
    socket.getaddrinfo = dns
    sys.argv = [str(script), *sys.argv[2:]]
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    main()
