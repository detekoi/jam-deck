# Jam Deck for OBS: Apple Music Stream Display

A customizable Apple Music now playing display for macOS.

![Screenshot of Jam Deck showing four Apple Music now playing widgets with different color themes. Each widget displays album artwork, song title, and artist information in various styles - pink, green, dark, and white themes with different song information including Japanese characters, Wintime by CHAI, 'Dakotas' by Sofia Kourtesis, 'Learning Lessens (Shy One Remix)' by Andrew Ashong & Kaidi Tatham, and 'Hidden Memory' by AceMoMa.](assets/images/preview.png)

![Screenshot of a macOS system notification from Jam Deck. The notification features the Jam Deck icon (a pink jar) and displays 'Server Started' as the header, followed by the message 'Now playing overlay is active!' The notification uses the standard macOS rounded rectangle design with a light gray background.](/assets/images/jam-deck-macos-notification.png)

![Screenshot of Jam Deck's menu bar interface on macOS. The interface shows a dropdown menu with options including 'Stop Server', 'Copy Scene URL' (which has a submenu showing scene names like 'default', 'gaming', 'away', 'Cozy-10-9', 'minimal-16-9', 'sakura', and 'coding'), 'Open in Browser', 'Documentation', 'About', and 'Quit'. The submenu also includes options for 'Add New Scene...' and 'Manage Scenes'.](/assets/images/jam-deck-macos-menubar.png)

## Quick Links
- [Download](https://github.com/detekoi/jam-deck/releases/)
- [Installation](#installation)
- [Setting Up OBS](#setting-up-obs)
- [Theme Selection](#theme-selection)

## Features

- Shows currently playing Apple Music track on your stream with artwork.
- Ten versatile themes (5 rounded: Natural, Twitch, Dark, Pink, Light and 5 square: Transparent, Neon, Terminal, Retro, High Contrast).
- Adaptive or Fixed width display options.
- Optional edge fade for long scrolling titles, so they fade out instead of being cut off sharply.
- Automatically hides when no music is playing.
- Clean animated transitions between songs.
- Theme menu appears only on hover (invisible to viewers).
- Scene-specific settings saved between sessions.
- Menu bar app for easy access to server controls and scene management.
- One-click scene URL copying for easy OBS setup.
- Scrolling text marquee effect for long song/artist names.
- Automatic port selection if default port (8080) is in use.
- Album artwork from your Music library, with an iTunes Store fallback for streaming tracks.
- Server log for troubleshooting, one click away in the menu bar app.

## Requirements

- macOS (uses AppleScript to communicate with Apple Music).
- OBS Studio or similar streaming software with browser source support.

## Installation

### Recommended: Menu Bar App

1. Download the latest Jam Deck.app from the [Releases](https://github.com/detekoi/jam-deck/releases/) page.
2. Move to your Applications folder.
3. Launch Jam Deck from your Applications folder.
   - If you see a warning about an app from an unidentified developer, see [Apple's guide](https://support.apple.com/guide/mac-help/open-a-mac-app-from-an-unknown-developer-mh40616/mac).
4. The app will appear in your menu bar with a musical note icon.
5. The server starts automatically when you launch the app.

To continue, jump to [Menu Bar App](#menu-bar-app).

<details>
<summary><h3>Advanced: Manual Installation</h3></summary>

**Requirements:**
- Python 3.9 or later (no extra packages needed)

Steps:
1. Clone this repository:
   ```bash
   git clone https://github.com/detekoi/jam-deck.git
   cd jam-deck
   ```

2. Make sure the Python script is executable:
   ```bash
   chmod +x music_server.py
   ```

3. Start the server:
   ```bash
   ./music_server.py
   ```
   To use a specific port, add `--port`, for example `./music_server.py --port 9000`.
</details>

## Usage

Once installed, the overlay will automatically display your currently playing Apple Music tracks.

### Menu Bar App

Jam Deck's menu bar app provides easy access to all features directly from your Mac's menu bar:

1. **Server Control**
   - Click "Start Server" to begin displaying your music.
   - Click "Stop Server" when you're done streaming.
   - Use "Set Server Port..." to choose the port the server uses.

2. **Scene Management**
   - Under "Copy Scene URL," select any scene to copy its URL to the clipboard.
   - Each scene can have its own theme, width, and edge fade settings.
   - Use "Add New Scene..." to create custom scenes for different parts of your stream.
   - Use "Manage Scenes..." to rename or delete existing scenes.

3. **Browser Integration**
   - Click "Open in Browser" to preview how the default overlay looks.

4. **Troubleshooting and Updates**
   - Click "Open Server Log" to see what the server has been doing. See [Checking the server log](#troubleshooting).
   - Click "Check for Updates" to see if a newer version is available. Jam Deck also checks automatically.

## Setting Up OBS

To add Jam Deck to your OBS scene:

1. In OBS Studio, select the scene where you want to display your music.
2. In the Sources panel, click the `+` button.
3. Select `Browser` from the list of sources.
4. Choose `Create New` and give it a name (e.g., "Now Playing Music").
5. Click `OK`.
6. In the Browser Source properties:
   - URL: Use the app to copy a scene-specific URL. The default URL is `http://localhost:8080/`
   - Width: 400 (recommended minimum)
   - Height: 140
   - Check "Refresh browser when scene becomes active."
7. Click `OK` to add the browser source.

### Theme Selection

Hover over the overlay and right-click > Interact, or select the Source and press the Interact button below the preview to reveal the settings menu:

#### Rounded Themes
- **Natural** (default): Soft green theme with rounded corners.
- **Twitch**: Dark purple theme that matches Twitch aesthetics.
- **Dark**: Sleek black theme with cyan accents.
- **Pink**: Vibrant pink theme with friendly typography.
- **Light**: Clean white theme with blue accents.

#### Square Themes
- **Transparent**: Minimalist theme with no background, just text and artwork.
- **Neon**: Cyberpunk-inspired theme with glowing cyan text on black background.
- **Terminal**: Green-on-black theme reminiscent of classic computer terminals.
- **Retro**: Blue and yellow theme using pixel-style Press Start 2P font.
- **High Contrast**: Black and white theme with Atkinson Hyperlegible font optimized for maximum readability.

**Note about Settings Storage**: Theme, width, and edge fade preferences are stored separately in each browser's local storage. This means settings selected in your regular browser (Chrome, Safari, etc.) won't automatically appear in OBS. You'll need to configure your preferred settings once in each environment where you use Jam Deck.

### Width Options

In the settings menu:

- **A**: Adaptive width (only as wide as needed for the text).
- **F**: Fixed width (expands to fill the entire browser source width, default).

### Edge Fade

The button to the right of **A** and **F** turns the edge fade on or off. When it's on, long song titles and artist names fade out at the edges while they scroll, instead of being cut off with a hard edge. Text that fits is never faded. The fade is off by default and works with every theme, but it looks especially good with the **Transparent** theme.

## Troubleshooting

<details>
<summary>No music information appears</summary>

- Make sure the server is running.
- Make sure Apple Music is running.
- Try playing/pausing music to trigger an update.

</details>

<details>
<summary>Checking the server log</summary>

The menu bar app saves the server's output, with timestamps, to `~/Library/Logs/Jam Deck/server.log`. The log from the previous run is kept as `server.previous.log`. To open it, click "Open Server Log" in the menu bar app.

The log shows each song Jam Deck saw and whether its artwork came from Apple Music or an iTunes Store search. If something looks wrong on stream, note the time and check the log around then. Include the relevant lines if you [report an issue](https://github.com/detekoi/jam-deck/issues).

</details>

<details>
<summary>Wrong album art shows for a song</summary>

When a new song starts streaming, Apple Music sometimes briefly hands back the previous song's artwork. Jam Deck detects this and uses the iTunes Store artwork for that song instead. If you still see the wrong artwork:

- Check the [server log](#troubleshooting) around the time it happened. A line saying the artwork was treated as stale means the detection worked. Otherwise, the log shows whether the artwork came from Apple Music or from an iTunes Store search.
- Adding the song to your library usually makes Apple Music provide the correct artwork.

</details>

<details>
<summary>macOS 26 Tahoe: Album art missing for streaming tracks</summary>

**Partially fixed in macOS 26.3** (Bug report: FB19908171).

As of macOS 26.3, Apple has partially fixed the AppleScript `current track` regression. Track metadata (title, artist, album) now works for all content, including streaming tracks not in your library. However, **album artwork** still cannot be retrieved via AppleScript for streaming tracks.

**Automatic fallback:** Jam Deck automatically searches the iTunes Store for album artwork when AppleScript can't provide it. This works for most tracks but may not find very niche or region-restricted content.

**What works:**
- Song title, artist, and album for all tracks (library and streaming)
- Album artwork for songs in your Music library
- Album artwork via iTunes Store fallback for most streaming tracks

**What may not work:**
- Album artwork for very niche or region-restricted streaming tracks not found on the iTunes Store

**Manual workaround** (for tracks not found on the iTunes Store):

Add songs to your library for guaranteed artwork:
1. Right-click on any song/album in Apple Music
2. Select "Add to Library"
3. Now play the song - artwork should display correctly

**Background:**

The original macOS 26 Tahoe release broke `current track` entirely for streaming content (error -1728). This has been mostly fixed in 26.3 — track info works again, but artwork retrieval still fails with a "Parameter error" for non-library streaming tracks.

This issue is being tracked in Apple's developer forums: https://developer.apple.com/forums/thread/798267

</details>

<details>
<summary>Permission errors</summary>

- macOS may need permission to control Apple Music.
- Go to System Preferences → Security & Privacy → Automation.
- Ensure "Jam Deck" has permission to control Apple Music.
- If you see a permissions prompt when launching the app, click "OK" to allow access.

</details>

## Auto-Start on Boot

<details>
<summary>Using the Menu Bar App</summary>

If you're using the menu bar app (Option 1 installation):

1. Go to System Preferences → Users & Groups → Login Items.
2. Click the "+" button.
3. Browse to your Applications folder and select "Jam Deck.app"
4. The app will now start automatically at login.

</details>

<details>
<summary>Using the Manual Installation</summary>

If you're using the manual installation:

1. Create an Automator application:
   - Open Automator.
   - Create a new Application.
   - Add a "Run Shell Script" action.
   - Enter: `cd /path/to/jam-deck && ./music_server.py`
   - Save as "Start Jam Deck"

2. Add to Login Items:
   - System Preferences → Users & Groups → Login Items.
   - Add the Automator application you created.

</details>

## Customization

Advanced users can modify the CSS in `overlay.css` to create custom themes or change the layout.

### Changing the Port

The server automatically starts on port 8080. If this port is already in use, it will automatically find and use the next available port. The selected port will be displayed in the menu bar app and system notifications.

To choose a different port:

- **Menu bar app:** Click "Set Server Port..." and enter a port between 1024 and 65535. The server restarts on the new port.
- **Manual installation:** Start the server with `./music_server.py --port 9000`, replacing `9000` with your port.

Then update your browser source URL in OBS to use the new port.

## Building from Source

**Requirements:**
- Python 3.9 or later (the release builds use Python 3.12)
- macOS 10.14 or later
- An app icon at `assets/images/jamdeck.icns` (not included in the repository)
- create-dmg (optional, for creating DMG installers)

If you want to build the Jam Deck menu bar app from source:

1. Clone the repository:
   ```
   git clone https://github.com/detekoi/jam-deck.git
   cd jam-deck
   ```

2. Create a virtual environment in `.venv` and install the build dependencies:
   ```
   python3 -m venv .venv
   .venv/bin/pip install py2app rumps pyobjc-framework-Cocoa
   ```

3. Option A - Using the build script (recommended):
   ```
   chmod +x build.sh
   ./build.sh
   ```
   
   Option B - Manual build:
   ```
   .venv/bin/python setup.py py2app
   ```

4. The built application will be available in the `dist` directory.

### Build Scripts

- `build.sh`: Automated build script that closes any running instances, cleans previous builds, builds the app, code-signs it, creates a DMG installer, notarizes it with Apple, and launches the new build. Signing uses `CODESIGN_IDENTITY` from a `.env` file (defaulting to "Apple Development"), and notarization uses a `notarytool` keychain profile named `notary-profile`.
- `setup.py`: Main build configuration for py2app.

### Script Permissions

Ensure that your build script has execute permissions. You can set this by running `chmod +x build.sh` in the terminal.

### Environment Considerations

Make sure that the necessary tools (osascript, rm, python, create-dmg) are installed and accessible in your system's PATH. The create-dmg tool is only needed if you want to create DMG installers. Notarization also requires Xcode's command line tools, with the Xcode license accepted (`sudo xcodebuild -license accept`).

Build from a Python whose library py2app bundles as `libpython3.x.dylib`, such as the python.org installer or Anaconda. Homebrew's Python is bundled as a `Python.framework` that `build.sh` doesn't re-sign, and the app crashes at launch with a Team ID mismatch.

## Font Attribution

- The Retro theme uses Press Start 2P font by CodeMan38 (licensed under SIL Open Font License), with Retro Gaming font by Daymarius as fallback.
- The High Contrast theme uses Atkinson Hyperlegible font designed by the Braille Institute for improved readability.
- JetBrains Mono font is used as a monospaced font for the Terminal theme.

All fonts are licensed under the [SIL Open Font License](assets/fonts/LICENSES.md).

## License

[BSD 2-Clause License](LICENSE.md)