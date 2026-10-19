#!/usr/bin/env python3
"""Serve generated public files on loopback only, optionally opening a browser."""
from __future__ import annotations

import argparse
import functools
import sys
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]


def port_number(value):
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be an integer between 1 and 65535") from exc
    if not 1 <= number <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return number


def already_serving_this_build(url, index):
    """Do not send a browser to an unrelated service occupying the requested port."""
    try:
        expected = index.read_bytes()
        opener = build_opener(ProxyHandler({}))
        with opener.open(url, timeout=2) as response:
            return response.status == 200 and response.read(len(expected) + 1) == expected
    except (OSError, URLError):
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=port_number, default=8765)
    parser.add_argument("--open", action="store_true", dest="open_browser")
    args = parser.parse_args()
    directory = ROOT / "dist"
    if not (directory / "index.html").is_file():
        parser.error("dist/index.html is missing; run ./scripts/dev.sh build first")
    url = f"http://127.0.0.1:{args.port}/"
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(directory))
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    except OSError as exc:
        if already_serving_this_build(url, directory / "index.html"):
            print(f"This build is already available at {url}")
            if args.open_browser:
                webbrowser.open(url)
            return
        raise SystemExit(f"Cannot serve on {url}: {exc}. Choose another port, e.g. ./scripts/dev.sh serve 8766") from exc
    print(f"Local explorer: {url}\nServing only dist/. Press Ctrl+C to stop.", flush=True)
    if args.open_browser:
        opener = threading.Timer(.2, webbrowser.open, args=(url,))
        opener.daemon = True
        opener.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nLocal server stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
