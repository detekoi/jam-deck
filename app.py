#!/usr/bin/env python3
"""Jam Deck — macOS menu bar app entry point."""
from jamdeck.menubar.app import JamDeckApp

if __name__ == "__main__":
    app = JamDeckApp()
    app.start_server()
    app.run()
