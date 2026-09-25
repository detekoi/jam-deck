# Jam Deck for OBS: Apple Music Stream Display

Jam Deck is a now-playing display for Apple Music on macOS. You can change its theme and layout.

![Screenshot of Jam Deck showing four Apple Music now playing widgets with different color themes. Each widget displays album artwork, song title, and artist information in various styles - pink, green, dark, and white themes with different song information including Japanese characters, Wintime by CHAI, 'Dakotas' by Sofia Kourtesis, 'Learning Lessens (Shy One Remix)' by Andrew Ashong & Kaidi Tatham, and 'Hidden Memory' by AceMoMa.](assets/images/preview.png)

![Screenshot of a macOS system notification from Jam Deck. The notification features the Jam Deck icon (a pink jar) and displays 'Server Started' as the header, followed by the message 'Now playing overlay is active!' The notification uses the standard macOS rounded rectangle design with a light gray background.](/assets/images/jam-deck-macos-notification.png)

![Screenshot of Jam Deck's menu bar interface on macOS. The interface shows a dropdown menu with options including 'Stop Server', 'Copy Scene URL' (which has a submenu showing scene names like 'default', 'gaming', 'away', 'Cozy-10-9', 'minimal-16-9', 'sakura', and 'coding'), 'Open in Browser', 'Documentation', 'About', and 'Quit'. The submenu also includes options for 'Add New Scene...' and 'Manage Scenes'.](/assets/images/jam-deck-macos-menubar.png)

## Quick Links
- [Download](https://github.com/detekoi/jam-deck/releases/)
- [Installation](#installation)
- [Setting Up OBS](#setting-up-obs)
- [Theme Selection](#theme-selection)

## Features

- Shows the Apple Music track that plays now on your stream, with its album artwork.
- Ten themes: five rounded (Natural, Twitch, Dark, Pink, Light) and five square (Transparent, Neon, Terminal, Retro, High Contrast).
- Two width modes: adaptive and fixed.
- An optional edge fade for long titles that scroll. The text fades out at the edges and does not stop at a hard edge.
- Hides when no music plays.
- Animated transitions between songs.
- A settings menu that shows only when you move the pointer over the overlay. Viewers do not see it.
- Settings for each scene. Jam Deck keeps them between sessions.
- A menu bar app to control the server and manage scenes.
- Copy the URL of a scene for OBS with one click.
- Long song and artist names scroll across the display.
- If a different program uses the default port (8080), the server selects a different port.
- Album artwork from your Music library. For streaming tracks, Jam Deck gets the artwork from the iTunes Store.
- A server log for troubleshooting. You can open it with one click in the menu bar app.

## Requirements

- macOS. Jam Deck uses AppleScript to get data from Apple Music.
- OBS Studio, or other streaming software that supports browser sources.

## Installation

### Recommended: Menu Bar App

1. Download the latest Jam Deck.app from the [Releases](https://github.com/detekoi/jam-deck/releases/) page.
2. Move Jam Deck.app to your Applications folder.
3. Open Jam Deck from your Applications folder.
   - If macOS shows a warning about an app from an unidentified developer, read [Apple's guide to opening apps from unknown developers](https://support.apple.com/guide/mac-help/open-a-mac-app-from-an-unknown-developer-mh40616/mac).

When Jam Deck opens, it shows a musical note icon in your menu bar. The server starts automatically.

To continue, go to [Menu Bar App](#menu-bar-app).

<details>
<summary><h3>Advanced: Manual Installation</h3></summary>

**Requirements:**
- Python 3.9 or later.

Steps:
1. Clone this repository:
   ```bash
   git clone https://github.com/detekoi/jam-deck.git
   cd jam-deck
   ```

2. Make the Python script executable:
   ```bash
   chmod +x music_server.py
   ```

3. Start the server:
   ```bash
   ./music_server.py
   ```
   To use a different port, add the `--port` option. For example: `./music_server.py --port 9000`.
</details>

## Usage

When the server runs, the overlay shows the track that Apple Music plays now.

### Menu Bar App

Use the menu bar app to control all Jam Deck features from the macOS menu bar:

1. **Server Control**
   - To start showing your music, click "Start Server".
   - When you finish streaming, click "Stop Server".
   - To change the port that the server uses, click "Set Server Port...".

2. **Scene Management**
   - To copy the URL of a scene to the clipboard, select the scene under "Copy Scene URL".
   - Each scene has its own theme, width, and edge fade settings.
   - To make a custom scene for a different part of your stream, click "Add New Scene...".
   - To rename or delete scenes, click "Manage Scenes...".

3. **Browser Integration**
   - To see a preview of the default overlay, click "Open in Browser".

4. **Troubleshooting and Updates**
   - To see what the server did, click "Open Server Log". For more information, read [Checking the server log](#troubleshooting).
   - To look for a newer version, click "Check for Updates". Jam Deck also looks for updates automatically.

## Setting Up OBS

To add Jam Deck to a scene in OBS:

1. In OBS Studio, select the scene where you want to show your music.
2. In the Sources panel, click the `+` button.
3. From the list of sources, select `Browser`.
4. Select `Create New`.
5. Type a name for the source, for example "Now Playing Music".
6. Click `OK`.
7. In the Browser Source properties, set these values:
   - URL: Copy the URL of a scene from the menu bar app. The default URL is `http://localhost:8080/`.
   - Width: 400 (the recommended minimum)
   - Height: 140
   - Select "Refresh browser when scene becomes active."
8. To add the browser source, click `OK`.

### Theme Selection

To open the settings menu, do one of these steps:

- Right-click the overlay in the OBS preview, then select Interact.
- Select the source, then click the Interact button below the preview.

Then select a theme in the settings menu.

#### Rounded Themes
- **Natural** (default): Soft green theme.
- **Twitch**: Dark purple theme that matches the colors of Twitch.
- **Dark**: Black theme with cyan accents.
- **Pink**: Bright pink theme with the rounded Quicksand font.
- **Light**: White theme with blue accents.

#### Square Themes
- **Transparent**: No background. Shows only the text and the artwork.
- **Neon**: Cyberpunk style. Cyan text glows on a black background.
- **Terminal**: Green text on a black background, like an old computer terminal.
- **Retro**: Blue and yellow theme with the pixel font Press Start 2P.
- **High Contrast**: Black and white theme with the Atkinson Hyperlegible font, for maximum readability.

**Note about settings storage:** Each browser keeps its own theme, width, and edge fade settings in its local storage. Thus, settings that you select in your usual browser (for example, Chrome or Safari) do not show in OBS. You must select your settings one time in each browser where you use Jam Deck.

### Width Options

The settings menu has two width options:

- **A**: Adaptive width. The overlay is only as wide as the text.
- **F**: Fixed width (default). The overlay fills the full width of the browser source.

### Edge Fade

The button to the right of **A** and **F** turns the edge fade on and off. When the edge fade is on, long song titles and artist names fade out at the edges while they scroll. Without the fade, the text stops at a hard edge. Jam Deck does not fade text that fits in the overlay. The edge fade is off by default. It works with all themes, and it looks especially good with the **Transparent** theme.

## Troubleshooting

<details>
<summary>No music information appears</summary>

- Make sure that the server runs.
- Make sure that Apple Music is open.
- To update the overlay, pause the music, then play it again.

</details>

<details>
<summary>Checking the server log</summary>

The menu bar app saves the output of the server, with timestamps, to `~/Library/Logs/Jam Deck/server.log`. It keeps the log from the previous run as `server.previous.log`. To open the log, click "Open Server Log" in the menu bar app.

The log shows each song that Jam Deck found. For each song, the log also shows the source of the artwork: Apple Music or an iTunes Store search.

If something on your stream looks wrong, write down the time. Then read the log near that time. If you [report a problem on GitHub](https://github.com/detekoi/jam-deck/issues), include the related lines from the log.

</details>

<details>
<summary>Wrong album art shows for a song</summary>

When a new song starts to stream, Apple Music sometimes gives the artwork of the previous song for a short time. Jam Deck finds this error and uses the iTunes Store artwork for the new song. If you still see the wrong artwork:

- Add the song to your library. Apple Music then usually gives the correct artwork.
- Read the [server log](#troubleshooting) near the time of the error. If a line says that Jam Deck treated the artwork as stale, the detection worked. If not, the log shows the source of the artwork: Apple Music or an iTunes Store search.

</details>

<details>
<summary>macOS 26 Tahoe: Album art missing for streaming tracks</summary>

**Partially fixed in macOS 26.3** (Bug report: FB19908171).

In macOS 26.3, Apple partially fixed the regression in the AppleScript `current track` property. Track metadata (title, artist, album) works again for all content. This includes streaming tracks that are not in your library. But AppleScript still cannot get the **album artwork** for streaming tracks.

**Automatic fallback:** When AppleScript cannot give the artwork, Jam Deck searches the iTunes Store for it. This search finds the artwork for most tracks. It can fail for very niche content, or for content that is available only in some regions.

**What works:**
- Song title, artist, and album for all tracks (library and streaming)
- Album artwork for songs in your Music library
- Album artwork from the iTunes Store for most streaming tracks

**What can fail:**
- Album artwork for very niche or region-restricted streaming tracks that the iTunes Store does not have

**Manual workaround** (for tracks that the iTunes Store does not have):

Songs in your library always have artwork. To add a song to your library:
1. In Apple Music, right-click the song or album.
2. Select "Add to Library".
3. Play the song. The artwork now shows correctly.

**Background:**

The first release of macOS 26 Tahoe broke `current track` for all streaming content (error -1728). macOS 26.3 corrected most of this problem, and track information works again. But for streaming tracks that are not in your library, AppleScript still cannot get the artwork. It fails with a "Parameter error".

For the status of this problem, read [thread 798267 in the Apple Developer Forums](https://developer.apple.com/forums/thread/798267).

</details>

<details>
<summary>Permission errors</summary>

Jam Deck needs permission from macOS to control Apple Music.

- If macOS shows a permission prompt when Jam Deck starts, click "OK".
- To give permission later, go to System Preferences → Security & Privacy → Automation. Make sure that "Jam Deck" has permission to control Apple Music.

</details>

## Auto-Start on Boot

<details>
<summary>Using the Menu Bar App</summary>

If you use the menu bar app (the recommended installation):

1. Go to System Preferences → Users & Groups → Login Items.
2. Click the "+" button.
3. Go to your Applications folder and select "Jam Deck.app".

The app now starts automatically when you log in.

</details>

<details>
<summary>Using the Manual Installation</summary>

If you use the manual installation:

1. Make an Automator application:
   - Open Automator.
   - Create a new Application.
   - Add a "Run Shell Script" action.
   - Type this command: `cd /path/to/jam-deck && ./music_server.py`
   - Save the application as "Start Jam Deck".

2. Add the application to Login Items:
   - Go to System Preferences → Users & Groups → Login Items.
   - Add the Automator application that you made.

</details>

## Customization

To make custom themes or change the layout, edit the CSS in `overlay.css`.

### Changing the Port

By default, the server starts on port 8080. If a different program uses this port, the server finds the next available port and uses it. The menu bar app and the system notifications show the port that the server uses.

To select a different port:

- **Menu bar app:** Click "Set Server Port...". Then type a port number from 1024 to 65535. The server restarts on the new port.
- **Manual installation:** Start the server with `./music_server.py --port 9000`. Replace `9000` with your port number.

Then change the port in the URL of your browser source in OBS.

## Building from Source

**Requirements:**
- Python 3.9 or later. The release builds use Python 3.12.
- macOS 10.14 or later
- An app icon at `assets/images/jamdeck.icns`. The repository does not include this file.
- create-dmg (optional). You need it only to make DMG installers.

To build the Jam Deck menu bar app from source:

1. Clone the repository:
   ```
   git clone https://github.com/detekoi/jam-deck.git
   cd jam-deck
   ```

2. Make a virtual environment in `.venv`, then install the build dependencies:
   ```
   python3 -m venv .venv
   .venv/bin/pip install py2app rumps pyobjc-framework-Cocoa
   ```

3. Build the app with one of these options.

   Option A: The build script (recommended):
   ```
   chmod +x build.sh
   ./build.sh
   ```

   Option B: A manual build:
   ```
   .venv/bin/python setup.py py2app
   ```

The build puts the app in the `dist` directory.

### Build Scripts

- `build.sh`: The automated build script. It does these steps in sequence:
  1. Closes all running instances of Jam Deck.
  2. Removes previous builds.
  3. Builds the app.
  4. Code-signs the app.
  5. Makes a DMG installer.
  6. Sends the DMG to Apple for notarization.
  7. Opens the new build.

  Signing uses the `CODESIGN_IDENTITY` value from a `.env` file. The default value is "Apple Development". Notarization uses a `notarytool` keychain profile with the name `notary-profile`.
- `setup.py`: The main build configuration for py2app.

### Script Permissions

Make sure that the build script has execute permission. To set this permission, run `chmod +x build.sh` in Terminal.

### Environment Considerations

Make sure that these tools are installed and in your `PATH`: osascript, rm, python, create-dmg. You need create-dmg only to make DMG installers. To notarize the app, you also need the Xcode command line tools. You must also accept the Xcode license (`sudo xcodebuild -license accept`).

Build with a Python that py2app bundles as `libpython3.x.dylib`. The python.org installer and Anaconda are two examples.

Do not build with the Homebrew Python. py2app bundles it as a `Python.framework`, and `build.sh` does not re-sign that framework. As a result, the app stops at launch with a Team ID mismatch.

## Font Attribution

- The Retro theme uses the Press Start 2P font by CodeMan38. Its fallback font is Retro Gaming by Daymarius.
- The High Contrast theme uses the Atkinson Hyperlegible font. The Braille Institute designed this font for better readability.
- The Terminal theme uses the monospaced font JetBrains Mono.

All fonts use the [SIL Open Font License](assets/fonts/LICENSES.md).

## License

[BSD 2-Clause License](LICENSE.md)
