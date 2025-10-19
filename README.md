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
- Automatically hides when no music is playing.
- Clean animated transitions between songs.
- Theme menu appears only on hover (invisible to viewers).
- Scene-specific settings saved between sessions.
- Menu bar app for easy access to server controls and scene management.
- One-click scene URL copying for easy OBS setup.
- Scrolling text marquee effect for long song/artist names.
- Automatic port selection if default port (8080) is in use.

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
- Python 3.6 or later

Steps:
1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/jam-deck.git
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
</details>

## Usage

Once installed, the overlay will automatically display your currently playing Apple Music tracks.

### Menu Bar App

Jam Deck's menu bar app provides easy access to all features directly from your Mac's menu bar:

1. **Server Control**
   - Click "Start Server" to begin displaying your music.
   - Click "Stop Server" when you're done streaming.

2. **Scene Management**
   - Under "Copy Scene URL," select any scene to copy its URL to the clipboard.
   - Each scene can have unique theme and width settings.
   - Use "Add New Scene..." to create custom scenes for different parts of your stream.
   - Use "Manage Scenes..." to rename or delete existing scenes.

3. **Browser Integration**
   - Click "Open in Browser" to preview how the default overlay looks.

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

**Note about Settings Storage**: Theme and width preferences are stored separately in each browser's local storage. This means settings selected in your regular browser (Chrome, Safari, etc.) won't automatically appear in OBS. You'll need to configure your preferred settings once in each environment where you use Jam Deck.

### Width Options

In the settings menu:

- **A**: Adaptive width (only as wide as needed for the text).
- **F**: Fixed width (expands to fill the entire browser source width, default).

## Troubleshooting

<details>
<summary>No music information appears</summary>

- Make sure the server is running.
- Make sure Apple Music is running.
- Try playing/pausing music to trigger an update.

</details>

<details>
<summary>macOS 26 Tahoe: AutoPlay shows “Music information unavailable”</summary>

- In macOS 26 Tahoe, Apple Music sometimes does not expose `current track` metadata to AppleScript during AutoPlay (infinite play) sessions. This affects many apps/scripts.
- Jam Deck v1.1.4 adds a fallback that reads the Music app’s `current stream title` when this happens and attempts to parse Song/Artist. Artwork and album may be unavailable in this mode.
- If you still see issues:
  - Toggle AutoPlay off (queue panel → ∞ button) or start playback from your Library’s Songs/Albums.
  - Ensure Jam Deck is updated and the server restarted.
  - Open the overlay with `?debug=true` to view raw responses in the browser console.
  - Report regressions with steps to reproduce.

References: discussions from developer communities indicate Apple changed behavior for AutoPlay metadata in Tahoe.

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

If you need to manually specify a different port (Manual installation only):

1. Open `music_server.py` in a text editor.
2. Find the line near the top that says `PORT = 8080`
3. Change `8080` to your desired port number.
4. Save the file and restart the server.
5. Update your browser source URL in OBS to use the new port.

## Building from Source

**Requirements:**
- Python 3.6 or later
- macOS 10.14 or later
- create-dmg (optional, for creating DMG installers)

If you want to build the Jam Deck menu bar app from source:

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/jam-deck.git
   cd jam-deck
   ```

2. Install py2app:
   ```
   pip install py2app
   ```

3. Option A - Using the build script (recommended):
   ```
   chmod +x build.sh
   ./build.sh
   ```
   
   Option B - Manual build:
   ```
   python setup.py py2app
   ```

4. The built application will be available in the `dist` directory.

### Build Scripts

- `build.sh`: Automated build script that handles closing any running instances, cleaning previous builds, building the app, and creating a DMG installer.
- `setup.py`: Main build configuration for py2app.
- `collect_zmq.py`: Helper script to ensure ZeroMQ libraries are properly included in the build.

### Script Permissions

Ensure that your build script has execute permissions. You can set this by running `chmod +x build.sh` in the terminal.

### Environment Considerations

Make sure that the necessary tools (osascript, rm, python, create-dmg) are installed and accessible in your system's PATH. The create-dmg tool is only needed if you want to create DMG installers.

## Font Attribution

- The Retro theme uses Press Start 2P font by CodeMan38 (licensed under SIL Open Font License), with Retro Gaming font by Daymarius as fallback.
- The High Contrast theme uses Atkinson Hyperlegible font designed by the Braille Institute for improved readability.
- JetBrains Mono font is used as a monospaced font for the Terminal theme.

All fonts are licensed under the [SIL Open Font License](assets/fonts/LICENSES.md).

## License

[BSD 2-Clause License](LICENSE.md)