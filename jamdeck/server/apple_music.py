# jamdeck/server/apple_music.py
import os
import json
import subprocess

class AppleMusicProvider:
    def __init__(self, artwork_manager, artwork_path="/tmp/harmony_deck_cover.jpg"):
        self.artwork_manager = artwork_manager
        self.artwork_path = artwork_path

    def get_apple_music_track(self):
        # Define a unique delimiter unlikely to be in metadata
        delimiter = "|||"
        
        # AppleScript to return delimited data instead of JSON
        script = f'''
        set output_delimiter to "{delimiter}"

        if application "Music" is running then
            tell application "Music"
                if player state is playing then
                    try
                        set currentTrack to current track
                    set songName to name of currentTrack
                    set artistName to artist of currentTrack
                    set albumName to album of currentTrack
                    
                    -- Try to get album artwork (handles JPEG, PNG, and other formats)
                    set hasArtwork to false
                    try
                        set myArtwork to artwork 1 of currentTrack
                        set artworkFile to "/tmp/harmony_deck_cover.jpg"
                        set myPicture to data of myArtwork
                        set myFile to (open for access (POSIX file artworkFile) with write permission)
                        set eof of myFile to 0
                        write myPicture to myFile
                        try
                            close access (POSIX file artworkFile)
                        end try
                        set hasArtwork to true
                    on error errMsg
                        -- Log error but continue
                        do shell script "echo 'Artwork error: " & errMsg & "' >> /tmp/harmony-deck-log.txt"
                    end try
                    
                    -- Return delimited string: playing_state|||title|||artist|||album|||has_artwork
                    return "true" & output_delimiter & songName & output_delimiter & artistName & output_delimiter & albumName & output_delimiter & hasArtwork

                on error readErr
                    return "false" & output_delimiter & readErr
                    end try
                else
                    -- Not playing but app is running
                    return "false" & output_delimiter & "Not playing"
                end if
            end tell
        else
            -- Music app is not running
            return "not_running" & output_delimiter & "Music app not running"
        end if
        '''
        
        try:
            print("Executing AppleScript...")
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=5)
            
            print(f"AppleScript raw output: {result.stdout}")
            if result.stderr:
                print(f"AppleScript error output: {result.stderr}")
            
            output = result.stdout.strip()
            if not output:
                print("Warning: Empty response from AppleScript")
                return json.dumps({"playing": False, "error": "Empty response from AppleScript"})
                
            # Parse the delimited string
            parts = output.split(delimiter)
            
            # Check the status from the first part
            status = parts[0].lower()
            
            if status == 'true':
                # Playing: Expect 5 parts: playing, title, artist, album, has_artwork
                if len(parts) == 5:
                    title, artist, album, has_artwork_str = parts[1], parts[2], parts[3], parts[4]
                    has_artwork = has_artwork_str.lower() == 'true'
                    track_id = f"{artist}|||{title}"

                    # Build the data dictionary
                    data = {
                        "playing": True,
                        "title": title,
                        "artist": artist,
                        "album": album
                    }

                    # If AppleScript successfully wrote artwork, update the on-disk track record.
                    # This ensures we know whose art is currently in the temp file.
                    if has_artwork:
                        self.artwork_manager.last_artwork_track = track_id

                    # Add artwork path if available (from AppleScript or iTunes fallback)
                    if not has_artwork:
                        # Try iTunes Search API as fallback
                        has_artwork = self.artwork_manager.fetch_itunes_artwork(artist, title, album)
                    
                    if has_artwork:
                        # Only serve the artwork file if it belongs to the current track.
                        # If a different song's art is on disk (e.g. from a queued track),
                        # we skip the artwork rather than show the wrong album art.
                        if self.artwork_manager.last_artwork_track == track_id:
                            # Generate timestamp for cache busting
                            try:
                                timestamp = int(os.path.getmtime(self.artwork_path))
                                data["artworkPath"] = f"/artwork?t={timestamp}"
                            except FileNotFoundError:
                                print("Warning: Artwork file not found for timestamp, skipping artwork path.")
                        else:
                            print(f"Artwork on disk belongs to '{self.artwork_manager.last_artwork_track}', not current track '{track_id}'. Skipping stale art.")

                    return json.dumps(data)
                else:
                    print(f"Error: Unexpected number of parts from AppleScript when playing. Parts: {parts}")
                    return json.dumps({"playing": False, "error": "Malformed response from AppleScript (playing)"})
            elif status == 'false':
                # Not playing or error reading track
                error_message = parts[1] if len(parts) > 1 else "Unknown state"

                if error_message != "Not playing":
                    print(f"Music app state: {error_message}")

                if error_message == "Not playing":
                    return json.dumps({"playing": False, "error": None})
                else:
                    return json.dumps({"playing": False, "error": error_message})
            elif status == 'not_running':
                # Music app not running
                error_message = parts[1] if len(parts) > 1 else "Music app not running"
                print(error_message)
                return json.dumps({"playing": False, "error": error_message})
            else:
                # Unexpected status from AppleScript
                print(f"Error: Unexpected status from AppleScript: {status}. Parts: {parts}")
                return json.dumps({"playing": False, "error": "Unknown response from AppleScript"})

        except subprocess.TimeoutExpired:
            print("Error: AppleScript timed out after 5 seconds")
            return json.dumps({"playing": False, "error": "AppleScript timed out"})
        except Exception as e:
            print(f"Error processing AppleScript output or getting artwork timestamp: {e}")
            return json.dumps({"playing": False, "error": f"Python processing error: {str(e)}"})
