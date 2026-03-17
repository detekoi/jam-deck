#!/bin/bash

# Gracefully quit the Jam Deck application
osascript -e 'quit app "Jam Deck"'

# Remove previous build directories
rm -rf dist/ build/

# Build the application using py2app
.venv/bin/python setup.py py2app

# Create the DMG installer using create-dmg
create-dmg --icon "Jam Deck.app" 100 80 --app-drop-link 300 80 dist/JamDeck.dmg "dist/Jam Deck.app"

# Launch the newly built Jam Deck application
"dist/Jam Deck.app/Contents/MacOS/Jam Deck"
