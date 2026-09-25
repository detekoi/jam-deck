# jamdeck/server/apple_music.py
import json
import subprocess

class AppleMusicProvider:
    def __init__(self, artwork_manager):
        self.artwork_manager = artwork_manager

    def get_apple_music_track(self):
        # Define a unique delimiter unlikely to be in metadata
        delimiter = "|||"
        
        # AppleScript to return delimited data instead of JSON
        script = f'''
        set output_delimiter to "{delimiter}"
        set artworkFile to "{self.artwork_manager.applescript_artwork_path}"

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
                        set myPicture to data of myArtwork
                        set myFile to (open for access (POSIX file artworkFile) with write permission)
                        try
                            set eof of myFile to 0
                            write myPicture to myFile
                            close access myFile
                        on error writeErr
                            -- Always release the file, or later polls can't open it
                            close access myFile
                            error writeErr
                        end try
                        set hasArtwork to true
                    on error errMsg
                        -- Log error but continue. quoted form of keeps apostrophes in the
                        -- message from breaking the shell command, and the inner try keeps
                        -- a logging failure from hiding the track info.
                        try
                            do shell script "echo " & quoted form of ("Artwork error: " & errMsg) & " >> /tmp/harmony-deck-log.txt"
                        end try
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

                    # Build the data dictionary
                    data = {
                        "playing": True,
                        "title": title,
                        "artist": artist,
                        "album": album
                    }

                    # Use the Music app's artwork if it's a valid image that belongs to this
                    # track. Otherwise fall back to the iTunes Search API.
                    artwork_id = None
                    if has_artwork:
                        artwork_id = self.artwork_manager.accept_applescript_artwork(artist, title, album)
                    if not artwork_id:
                        artwork_id = self.artwork_manager.fetch_itunes_artwork(artist, title, album)
                    self.artwork_manager.remember_track_artwork(artist, title, album, artwork_id)

                    # The id is a hash of the image bytes, so the URL only ever serves
                    # this exact image and changes whenever the artwork changes.
                    if artwork_id:
                        data["artworkPath"] = f"/artwork?id={artwork_id}"

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
            print(f"Error processing AppleScript output or artwork: {e}")
            return json.dumps({"playing": False, "error": f"Python processing error: {str(e)}"})
