# jamdeck/server/handler.py
import os
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

class MusicHandler(BaseHTTPRequestHandler):
    # Class variables to be configured before starting the server
    apple_music_provider = None
    artwork_manager = None
    root_dir = None

    def log_message(self, format, *args):
        # Print to stdout instead of stderr for better visibility
        print(f"{self.address_string()} - - [{self.log_date_time_string()}] {format % args}")
    
    def _send_forbidden(self):
        """Send a 403 Forbidden response."""
        self.send_response(403)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Forbidden')

    def do_GET(self):
        # Parse the URL
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        print(f"Request received: {path}")
        
        # Use configured root_dir or calculate using get_resources_dir
        base_dir = self.root_dir
        if not base_dir:
            from jamdeck import get_resources_dir
            base_dir = get_resources_dir()
        
        # Resolve the base directory once as an absolute Path
        resolved_base = Path(base_dir).resolve()
        
        # Serve static files (HTML, CSS, JS)
        if path == '/' or path.endswith('.html') or path.endswith('.css') or path.endswith('.js'):
            # Use only the basename to strip any directory traversal components
            safe_name = 'overlay.html' if path == '/' else os.path.basename(path)
            resolved_path = (resolved_base / safe_name).resolve()
            
            # Inline path traversal guard — CodeQL recognizes is_relative_to
            if not resolved_path.is_relative_to(resolved_base):
                self._send_forbidden()
                return
            
            # Debug logging uses the validated resolved_path
            print(f"Static file requested: {safe_name}")
            print(f"Resolving to path: {resolved_path}")
            print(f"File exists: {resolved_path.exists()}")
            
            try:
                content = resolved_path.read_bytes()
                
                self.send_response(200)
                # Set correct content type based on file extension
                if safe_name.endswith('.html'):
                    content_type = 'text/html'
                elif safe_name.endswith('.css'):
                    content_type = 'text/css'
                elif safe_name.endswith('.js'):
                    content_type = 'text/javascript'
                else:
                    content_type = 'text/html'  # default for '/' path
                
                content_length = len(content)
                print(f"Serving {safe_name} ({content_length} bytes) as {content_type}")
                
                self.send_header('Content-type', content_type)
                self.send_header('Content-Length', str(content_length))
                self.send_header('Cache-Control', 'no-cache, must-revalidate')
                self.end_headers()
                self.wfile.write(content)
                return
            except FileNotFoundError:
                print(f"ERROR: File not found: {safe_name}")
                self.send_response(404)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'File not found')
                return
            except Exception as e:
                print(f"ERROR serving {safe_name}: {str(e)}")
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(f"Error: {str(e)}".encode())
                return
        
        # Route requests
        if path == '/nowplaying':
            print("Handling /nowplaying request")
            if self.apple_music_provider:
                music_data = self.apple_music_provider.get_apple_music_track()
            else:
                music_data = '{"playing": false, "error": "Apple Music provider not configured"}'
            
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
            
        elif path == '/artwork':
            # Artwork is served from memory by id (a hash of the image bytes),
            # so each URL always returns the same image
            artwork_id = parse_qs(parsed_path.query).get('id', [None])[0]
            artwork = self.artwork_manager.get_artwork(artwork_id) if self.artwork_manager and artwork_id else None
            
            if artwork:
                file_data, content_type = artwork
                self.send_response(200)
                self.send_header('Content-type', content_type)
                self.send_header('Content-Length', str(len(file_data)))
                # Safe to cache: a given id never changes content
                self.send_header('Cache-Control', 'max-age=86400')
                self.end_headers()
                self.wfile.write(file_data)
                print(f"Artwork {artwork_id} served successfully")
            else:
                print(f"Artwork not found: {artwork_id}")
                self.send_response(404)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Artwork not found')
                
        elif path.startswith('/assets/fonts/'):
            font_file = os.path.basename(path)
            resolved_font_path = (resolved_base / 'assets' / 'fonts' / font_file).resolve()
            resolved_fonts_dir = (resolved_base / 'assets' / 'fonts').resolve()
            
            # Inline path traversal guard — CodeQL recognizes is_relative_to
            if not resolved_font_path.is_relative_to(resolved_fonts_dir):
                self._send_forbidden()
                return
            
            print(f"Serving font file: {resolved_font_path}")
            
            try:
                file_data = resolved_font_path.read_bytes()
                
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
            image_file = os.path.basename(path)
            resolved_image_path = (resolved_base / 'assets' / 'images' / image_file).resolve()
            resolved_images_dir = (resolved_base / 'assets' / 'images').resolve()
            
            # Inline path traversal guard — CodeQL recognizes is_relative_to
            if not resolved_image_path.is_relative_to(resolved_images_dir):
                self._send_forbidden()
                return
            
            print(f"Serving image file: {resolved_image_path}")
            
            try:
                file_data = resolved_image_path.read_bytes()
                
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
