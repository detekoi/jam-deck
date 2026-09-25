#!/bin/bash
set -e

# Load environment variables (e.g. CODESIGN_IDENTITY)
[ -f .env ] && source .env

# Gracefully quit the Jam Deck application
osascript -e 'quit app "Jam Deck"'

# Kill any lingering server subprocesses that might hold the port
pkill -f "music_server\.py --port" 2>/dev/null || true
sleep 1

# Remove previous build directories
rm -rf dist/ build/

# Build the application using py2app
.venv/bin/python setup.py py2app

# Sign all binaries individually from the inside out (required for notarization).
# --deep is avoided because it does not add --timestamp to nested binaries.
CODESIGN_IDENTITY="${CODESIGN_IDENTITY:-Apple Development}"
SIGN="codesign --force --sign $CODESIGN_IDENTITY --timestamp --options runtime"

find "dist/Jam Deck.app" -type f \( -name "*.dylib" -o -name "*.so" \) | while read -r f; do
    $SIGN "$f"
done

find "dist/Jam Deck.app/Contents/MacOS" -type f | while read -r f; do
    $SIGN "$f"
done

$SIGN "dist/Jam Deck.app"

# Create the DMG installer using create-dmg
create-dmg --icon "Jam Deck.app" 100 80 --app-drop-link 300 80 "dist/JamDeck.dmg" "dist/Jam Deck.app"

# Sign the DMG
codesign --force --sign "$CODESIGN_IDENTITY" --timestamp "dist/JamDeck.dmg"

# Submit for notarization and wait for Apple's response
xcrun notarytool submit "dist/JamDeck.dmg" --keychain-profile "notary-profile" --wait

# Staple the notarization ticket to the DMG
xcrun stapler staple "dist/JamDeck.dmg"

echo "Build complete: dist/JamDeck.dmg"

# Launch the newly built Jam Deck application
"dist/Jam Deck.app/Contents/MacOS/Jam Deck"
