"""
ByteFlow Frontend
=================
Phone/web interface for ByteFlow. Runs on your laptop,
controllable from any phone or device on the same WiFi.

Usage:
    python -m byteflow_frontend
    python -m byteflow_frontend --port 7860 --model mistral
"""

from .server import app, start_server

__all__ = ["app", "start_server"]
__version__ = "1.0.0"
