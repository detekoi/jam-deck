#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import subprocess
import json
from urllib.parse import parse_qs, urlparse, unquote, quote_plus
from urllib.request import urlopen, Request
import os
import sys
import zmq
import signal
import atexit
import socket
import argparse # Import argparse

# Version information
VERSION = "1.1.4"

# Set starting port for the server
START_PORT = 8080
MAX_PORT_ATTEMPTS = 10 # Limit how many ports we try

# Initialize ZMQ context as None - we'll create it when needed and clean it up on exit
zmq_context = None

# Function to clean up resources on exit
def cleanup():
    global zmq_context
    if zmq_context:
        print("Closing ZMQ context...")
        zmq_context.term()
        zmq_context = None
        print("ZMQ context closed")

# Register cleanup function to run on exit
atexit.register(cleanup)

# Handle signals for clean shutdown
def signal_handler(sig, frame):
    print("\nShutting down server...")
    cleanup()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# In-memory cache for iTunes artwork lookups to avoid repeated API calls
# Key: "artist - title", Value: True (found & downloaded) or False (not found)
_itunes_artwork_cache = {}

def fetch_itunes_artwork(artist, title, album):
    """Fetch album artwork from iTunes Search API as a fallback.
    
    Used when AppleScript can't retrieve artwork (e.g., macOS Tahoe streaming bug).
    Downloads 600x600 artwork to /tmp/harmony_deck_cover.jpg.
    Returns True if artwork was found and saved, False otherwise.
    """
    cache_key = f"{artist} - {title}"
    
    # Check cache first
    if cache_key in _itunes_artwork_cache:
        return _itunes_artwork_cache[cache_key]
    
    try:
        # Search by artist + title for best match
        search_term = f"{artist} {title}"
        query = f"term={quote_plus(search_term)}&media=music&entity=song&limit=1"
        url = f"https://itunes.apple.com/search?{query}"
        
        resp = urlopen(url, timeout=3)
        data = json.loads(resp.read())
        
        if data.get("resultCount", 0) == 0:
            print(f"iTunes artwork fallback: no results for '{search_term}'")
            _itunes_artwork_cache[cache_key] = False
            return False
        
        result = data["results"][0]
        art_url = result.get("artworkUrl100", "")
        if not art_url:
            print(f"iTunes artwork fallback: no artwork URL in result for '{search_term}'")
            _itunes_artwork_cache[cache_key] = False
            return False
        
        # Upscale from 100x100 to 600x600
        art_url = art_url.replace("100x100bb", "600x600bb")
        
        # Download the artwork
        art_resp = urlopen(art_url, timeout=3)
        art_data = art_resp.read()
        
        artwork_path = "/tmp/harmony_deck_cover.jpg"
        with open(artwork_path, "wb") as f:
            f.write(art_data)
        
        print(f"iTunes artwork fallback: found artwork for '{search_term}' ({len(art_data)} bytes)")
        _itunes_artwork_cache[cache_key] = True
        return True
        
    except Exception as e:
        print(f"iTunes artwork fallback error: {e}")
        _itunes_artwork_cache[cache_key] = False
        return False

# Function to get current Apple Music track via AppleScript
def get_apple_music_track():
    # Define a unique delimiter unlikely to be in metadata
    delimiter = "|||"
    
    # Modified AppleScript to return delimited data instead of JSON
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
                
                -- Try to get album artwork
                set hasArtwork to false
                try
                    set myArtwork to artwork 1 of currentTrack
                    set artworkFile to "/tmp/harmony_deck_cover.jpg"
                    if format of myArtwork is JPEG picture then
                        set myPicture to data of myArtwork
                        set myFile to (open for access (POSIX file artworkFile) with write permission)
                        set eof of myFile to 0
                        write myPicture to myFile
                        try
                            close access (POSIX file artworkFile)
                        end try
                        set hasArtwork to true
                    end if
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

                # Build the data dictionary
                data = {
                    "playing": True,
                    "title": title,
                    "artist": artist,
                    "album": album
                }

                # Add artwork path if available (from AppleScript or iTunes fallback)
                if not has_artwork:
                    # Try iTunes Search API as fallback
                    has_artwork = fetch_itunes_artwork(artist, title, album)
                
                if has_artwork:
                    # Generate timestamp for cache busting
                    try:
                        timestamp = int(os.path.getmtime("/tmp/harmony_deck_cover.jpg"))
                        data["artworkPath"] = f"/artwork?t={timestamp}"
                    except FileNotFoundError:
                        # Handle case where artwork file might not exist when getting timestamp
                        print("Warning: Artwork file not found for timestamp, skipping artwork path.")
                        # Continue without artwork path, data dictionary is already populated

                # Convert dictionary to JSON using Python's json module for correct escaping
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
        # Attempt to return a generic error if parsing failed badly
        return json.dumps({"playing": False, "error": f"Python processing error: {str(e)}"})

# Create custom HTTP request handler
class MusicHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Print to stdout instead of stderr for better visibility
        print(f"{self.address_string()} - - [{self.log_date_time_string()}] {format % args}")
    
    def do_GET(self):
        # Parse the URL
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        print(f"Request received: {path}")
        
        # Serve static files (HTML, CSS, JS)
        if path == '/' or path.endswith('.html') or path.endswith('.css') or path.endswith('.js'):
            # If path is just '/', serve overlay.html
            if path == '/':
                file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'overlay.html')
            else:
                # Remove leading slash and get the file from current directory
                file_name = path.lstrip('/')
                file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), file_name)
            
            # Add debugging for file resolution
            print(f"Static file requested: {path}")
            print(f"Resolving to path: {file_path}")
            print(f"File exists: {os.path.exists(file_path)}")
            
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                self.send_response(200)
                # Set correct content type based on file extension
                if path.endswith('.html'):
                    content_type = 'text/html'
                elif path.endswith('.css'):
                    content_type = 'text/css'
                elif path.endswith('.js'):
                    content_type = 'text/javascript'
                else:
                    content_type = 'text/html'  # default for '/' path
                
                content_length = len(content)
                print(f"Serving {path} ({content_length} bytes) as {content_type}")
                
                self.send_header('Content-type', content_type)
                self.send_header('Content-Length', str(content_length))
                self.send_header('Cache-Control', 'no-cache, must-revalidate')
                self.end_headers()
                self.wfile.write(content)
                return
            except FileNotFoundError:
                print(f"ERROR: File not found: {file_path}")
                self.send_response(404)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'File not found')
                return
            except Exception as e:
                print(f"ERROR serving {path}: {str(e)}")
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error: {str(e)}".encode())
                return
        
        # Route requests
        if path == '/nowplaying':
            print("Handling /nowplaying request")
            music_data = get_apple_music_track()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET')
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
            self.end_headers()
            
            # Debug the output we're sending
            print(f"Sending JSON response: {music_data}")
            
            # Always ensure we send valid JSON
            self.wfile.write(music_data.encode())
            
        elif path == '/artwork' or path.startswith('/artwork?'):
            # Fixed path to the artwork file
            artwork_path = "/tmp/harmony_deck_cover.jpg"
            print(f"Serving artwork from: {artwork_path}")
            
            try:
                # Read the file
                with open(artwork_path, 'rb') as f:
                    file_data = f.read()
                
                self.send_response(200)
                self.send_header('Content-type', 'image/jpeg')
                self.send_header('Cache-Control', 'no-cache')  # Prevent caching
                self.end_headers()
                self.wfile.write(file_data)
                print("Artwork served successfully")
                
            except Exception as e:
                print(f"Error serving artwork: {e}")
                self.send_response(404)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Artwork not found')
                
        elif path.startswith('/assets/fonts/'):
            # Extract the filename from the path
            font_file = path.split('/')[-1]
            font_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'assets', 'fonts', font_file)
            
            print(f"Serving font file: {font_path}")
            
            try:
                # Open in binary mode for font files
                with open(font_path, 'rb') as f:
                    file_data = f.read()
                
                self.send_response(200)
                # Set the correct MIME type for TTF fonts
                self.send_header('Content-type', 'font/ttf')
                # Allow caching for fonts (unlike dynamic content)
                self.send_header('Cache-Control', 'max-age=86400')  # Cache for 24 hours
                self.end_headers()
                self.wfile.write(file_data)
                print(f"Font file '{font_file}' served successfully")
                
            except Exception as e:
                print(f"Error serving font file: {e}")
                self.send_response(404)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f'Font file not found: {str(e)}'.encode())
                
        elif path.startswith('/assets/images/'):
            # Extract the filename from the path
            image_file = path.split('/')[-1]
            image_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'assets', 'images', image_file)
            
            print(f"Serving image file: {image_path}")
            
            try:
                # Open in binary mode for image files
                with open(image_path, 'rb') as f:
                    file_data = f.read()
                
                self.send_response(200)
                # Set content type based on file extension
                if image_file.lower().endswith('.png'):
                    content_type = 'image/png'
                elif image_file.lower().endswith(('.jpg', '.jpeg')):
                    content_type = 'image/jpeg'
                elif image_file.lower().endswith('.gif'):
                    content_type = 'image/gif'
                elif image_file.lower().endswith('.svg'):
                    content_type = 'image/svg+xml'
                else:
                    content_type = 'application/octet-stream'
                
                self.send_header('Content-type', content_type)
                self.send_header('Cache-Control', 'max-age=86400')  # Cache for 24 hours
                self.end_headers()
                self.wfile.write(file_data)
                print(f"Image file '{image_file}' served successfully")
                
            except Exception as e:
                print(f"Error serving image file: {e}")
                self.send_response(404)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f'Image file not found: {str(e)}'.encode())
                
        else:
            print(f"404 Not Found: {path}")
            self.send_response(404)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"404 Not Found")

# Start the web server, finding an available port
def run_server(preferred_port=None): # Accept preferred_port argument
    global zmq_context # Declare zmq_context as global for this function's scope
    httpd = None
    actual_port = -1
    port_found = False

    # 1. Try the preferred port first if provided
    if preferred_port:
        print(f"Attempting to use preferred port: {preferred_port}")
        try:
            # Initialize ZMQ context if needed (now using function-scoped global)
            if zmq_context is None:
                zmq_context = zmq.Context()
                print("ZMQ context initialized")

            server_address = ('', preferred_port)
            httpd = HTTPServer(server_address, MusicHandler)
            actual_port = preferred_port
            port_found = True # Mark as found
            print(f"Successfully bound to preferred port {actual_port}")

        except socket.error as e:
            if e.errno == socket.errno.EADDRINUSE:
                print(f"Preferred port {preferred_port} already in use. Falling back to automatic detection.")
            else:
                print(f"Error trying preferred port {preferred_port}: {e}")
                # Don't immediately exit, allow fallback to automatic detection
        except Exception as e:
            print(f"Server setup error on preferred port {preferred_port}: {e}")
            # Don't immediately exit, allow fallback to automatic detection

    # 2. If preferred port failed or wasn't provided, try automatic detection
    if not port_found:
        print("Attempting automatic port detection...")
        for i in range(MAX_PORT_ATTEMPTS):
            port_to_try = START_PORT + i
            # Skip the preferred port if it was already tried and failed
            if preferred_port and port_to_try == preferred_port:
                continue

            try:
                # Initialize ZMQ context if needed (now using function-scoped global)
                if zmq_context is None:
                    zmq_context = zmq.Context()
                    print("ZMQ context initialized") # Keep this informational message

                server_address = ('', port_to_try)
                httpd = HTTPServer(server_address, MusicHandler)
                actual_port = port_to_try

                # IMPORTANT: Print the port for the parent process BEFORE other messages
                print(f"JAMDECK_PORT={actual_port}")
                sys.stdout.flush() # Ensure it's sent immediately
                
                print(f"Starting music server on port {actual_port}...")
                print(f"Open http://localhost:{actual_port}/ in your browser or OBS")
                print(f"Press Ctrl+C to stop the server")
                port_found = True # Mark as found
                break # Port found, exit loop
                
            except socket.error as e:
                if e.errno == socket.errno.EADDRINUSE:
                    print(f"Port {port_to_try} is busy, trying next...")
                    continue # Try next port (Now correctly indented)
                else: # This else correctly handles other socket errors
                    print(f"Server error on port {port_to_try}: {e}")
                    cleanup()
                    return # Exit if other socket error
            except Exception as e: # This except handles non-socket errors from the try block
                print(f"Server setup error on port {port_to_try}: {e}")
                cleanup()
            return # Exit on other setup errors

    # Check if a port was successfully found either way
    if not port_found or httpd is None:
        # Construct a more informative error message
        error_message = f"Could not bind to the preferred port ({preferred_port}) " if preferred_port else ""
        error_message += f"or find an available port in the range {START_PORT}-{START_PORT + MAX_PORT_ATTEMPTS - 1}."
        print(error_message)
        cleanup()
        return

    try:
        # Test the AppleScript before starting the server (only if server started)
        print("\nTesting AppleScript...")
        test_result = get_apple_music_track()
        print(f"Test result: {test_result}")
        print("\nServer ready!")
        print("\nTesting AppleScript...")
        test_result = get_apple_music_track()
        print(f"Test result: {test_result}")
        print("\nServer ready!")

        # Start server
        httpd.serve_forever()
        
    except KeyboardInterrupt:
        print("\nShutting down server...")
        if httpd:
            httpd.server_close()
        cleanup()
        print("Server stopped")
    except Exception as e:
        print(f"Server runtime error: {e}")
        if httpd:
            httpd.server_close()
        cleanup()

if __name__ == '__main__':
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(description="Jam Deck Music Server")
    parser.add_argument('--port', type=int, help='Preferred port number to start the server on.')
    args = parser.parse_args()
    # --- End Argument Parsing ---

    # Force output buffering off for better debugging
    sys.stdout.reconfigure(line_buffering=True)
    print(f"Jam Deck v{VERSION} - Music Now Playing Server")
    run_server(preferred_port=args.port) # Pass preferred port to run_server
