# Jam Deck for OBS: Dev Reference Guide

## Project Structure
- `app.py` - Entry point for the macOS menu bar app
- `music_server.py` - Standalone entry point for the HTTP server
- `jamdeck/` - Main package directory for Jam Deck application logic
  - `menubar/` - Menu bar UI, configuration, scene management, updater
  - `server/` - HTTP server routing, static asset serving, Apple Music tracking, artwork fetching
- `overlay.html` / `overlay.js` / `overlay.css` - HTML/CSS/JS for the OBS browser source overlay
- `setup.py` - Build configuration for py2app
- `collect_zmq.py` - Helper for ZeroMQ libraries bundling
- Browser source URL: http://localhost:8080/

## Commands
- Start server: `./music_server.py` or `python3 music_server.py`
- Start app: `python3 app.py`
- Build app: `python setup.py py2app` (creates .app in dist/)
- Version updates: Update VERSION in `jamdeck/__init__.py`, `setup.py` CFBundleVersion/CFBundleShortVersionString
- No linting commands (simple Python/HTML project)

## Code Style Guidelines
- **Python**: 
  - Use descriptive variable/function names
  - Comment complex logic sections
  - Handle errors with try/except blocks with specific error types
  - Follow PEP 8 spacing and indentation
  - Print debug statements for troubleshooting
- **HTML/CSS/JS**:
  - Use camelCase for JS variables and functions
  - CSS classes use kebab-case
  - Organize CSS logically by component/theme
  - Transitions and animations for UI elements
  - Use localStorage for persistent settings with scene-specific context

## Architecture Notes
- Server uses AppleScript to get music data from Apple Music
- Overlay connects to server API endpoint: `/nowplaying`
- Album artwork served via `/artwork` endpoint
- Static assets served via `/assets/fonts/` and `/assets/images/`
- Ten themes available: 5 rounded (Natural, Twitch, Dark, Pink, Light) and 5 square (Transparent, Neon, Terminal, Retro, High Contrast)

## Troubleshooting
- Check `debugMode` in overlay.html (set to true for visible errors)
- Look for error logs in Terminal
- System Preferences → Security & Privacy → Automation permissions