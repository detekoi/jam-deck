#!/usr/bin/env python3
"""Jam Deck — standalone server entry point."""
import sys
import argparse

# Allow importing from current directory so jamdeck package is found
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jamdeck import VERSION
from jamdeck.server.runner import run_server

if __name__ == '__main__':
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(description="Jam Deck Music Server")
    parser.add_argument('--port', type=int, help='Preferred port number to start the server on.')
    args = parser.parse_args()

    # Force output buffering off for better debugging
    sys.stdout.reconfigure(line_buffering=True)
    print(f"Jam Deck v{VERSION} - Music Now Playing Server")
    run_server(preferred_port=args.port)
