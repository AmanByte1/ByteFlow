"""
ByteFlow Frontend CLI

Usage:
    python -m byteflow_frontend                         # frontend only (port 7860)
    python -m byteflow_frontend --with-core             # start core API too (port 7861)
    python -m byteflow_frontend --port 7860
    python -m byteflow_frontend --core-url http://localhost:7861
    python -m byteflow_frontend --open

In another terminal, start the core:
    python -m byteflow.api_server --model mistral
"""

import argparse
from byteflow_frontend.server import start_server


def main():
    p = argparse.ArgumentParser(prog="byteflow_frontend")
    p.add_argument("--host",     default="0.0.0.0")
    p.add_argument("--port",     type=int, default=7860)
    p.add_argument("--core-url", default="http://localhost:7861", dest="core_url")
    p.add_argument("--model",    default="llama2", help="Model for --with-core")
    p.add_argument("--with-core", action="store_true", dest="with_core",
                   help="Also start byteflow core API server")
    p.add_argument("--open",     action="store_true", help="Open browser")
    args = p.parse_args()

    start_server(
        host=args.host,
        port=args.port,
        core_url=args.core_url,
        open_browser=args.open,
        with_core=args.with_core,
        model=args.model,
    )


if __name__ == "__main__":
    main()
