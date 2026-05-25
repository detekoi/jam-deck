# jamdeck/server/runner.py
import os
import sys
import socket
import signal
import atexit
import zmq
from http.server import HTTPServer

from jamdeck import get_resources_dir
from jamdeck.server.artwork import ArtworkManager
from jamdeck.server.apple_music import AppleMusicProvider
from jamdeck.server.handler import MusicHandler

# Set starting port for the server
START_PORT = 8080
MAX_PORT_ATTEMPTS = 10 # Limit how many ports we try

# Initialize ZMQ context as None
zmq_context = None

def cleanup():
    global zmq_context
    if zmq_context:
        print("Closing ZMQ context...")
        try:
            zmq_context.term()
        except Exception as e:
            print(f"Error closing ZMQ context: {e}")
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

def run_server(preferred_port=None):
    global zmq_context
    httpd = None
    actual_port = -1
    port_found = False

    # Initialize artwork and apple music components
    artwork_manager = ArtworkManager()
    apple_music_provider = AppleMusicProvider(artwork_manager)
    
    # Configure the handler class with the providers
    MusicHandler.artwork_manager = artwork_manager
    MusicHandler.apple_music_provider = apple_music_provider
    MusicHandler.root_dir = get_resources_dir()

    # 1. Try the preferred port first if provided
    if preferred_port:
        print(f"Attempting to use preferred port: {preferred_port}")
        try:
            # Initialize ZMQ context if needed
            if zmq_context is None:
                zmq_context = zmq.Context()
                print("ZMQ context initialized")

            server_address = ('', preferred_port)
            httpd = HTTPServer(server_address, MusicHandler)
            actual_port = preferred_port
            port_found = True
            print(f"Successfully bound to preferred port {actual_port}")

        except socket.error as e:
            if e.errno == socket.errno.EADDRINUSE:
                print(f"Preferred port {preferred_port} already in use. Falling back to automatic detection.")
            else:
                print(f"Error trying preferred port {preferred_port}: {e}")
        except Exception as e:
            print(f"Server setup error on preferred port {preferred_port}: {e}")

    # 2. If preferred port failed or wasn't provided, try automatic detection
    if not port_found:
        print("Attempting automatic port detection...")
        for i in range(MAX_PORT_ATTEMPTS):
            port_to_try = START_PORT + i
            # Skip the preferred port if it was already tried and failed
            if preferred_port and port_to_try == preferred_port:
                continue

            try:
                # Initialize ZMQ context if needed
                if zmq_context is None:
                    zmq_context = zmq.Context()
                    print("ZMQ context initialized")

                server_address = ('', port_to_try)
                httpd = HTTPServer(server_address, MusicHandler)
                actual_port = port_to_try

                # IMPORTANT: Print the port for the parent process BEFORE other messages
                print(f"JAMDECK_PORT={actual_port}")
                sys.stdout.flush() # Ensure it's sent immediately
                
                print(f"Starting music server on port {actual_port}...")
                print(f"Open http://localhost:{actual_port}/ in your browser or OBS")
                print(f"Press Ctrl+C to stop the server")
                port_found = True
                break
                
            except socket.error as e:
                if e.errno == socket.errno.EADDRINUSE:
                    print(f"Port {port_to_try} is busy, trying next...")
                    continue
                else:
                    print(f"Server error on port {port_to_try}: {e}")
                    cleanup()
                    return
            except Exception as e:
                print(f"Server setup error on port {port_to_try}: {e}")
                cleanup()
                return

    # Check if a port was successfully found either way
    if not port_found or httpd is None:
        error_message = f"Could not bind to the preferred port ({preferred_port}) " if preferred_port else ""
        error_message += f"or find an available port in the range {START_PORT}-{START_PORT + MAX_PORT_ATTEMPTS - 1}."
        print(error_message)
        cleanup()
        return

    try:
        # Test the AppleScript once before starting the server
        print("\nTesting AppleScript...")
        test_result = apple_music_provider.get_apple_music_track()
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
