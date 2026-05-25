# jamdeck/server/handler.py
import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse

class MusicHandler(BaseHTTPRequestHandler):
    # Class variables to be configured before starting the server
    apple_music_provider = None
    artwork_manager = None
    root_dir = None

    def log_message(self, format, *args):
        # Print to stdout instead of stderr for better visibility
        print(f"{self.address_string()} - - [{self.log_date_time_string()}] {format % args}")
    
    def do_GET(self):
        # Parse the URL
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        print(f"Request received: {path}")
        
        # Use configured root_dir or calculate from this file
        base_dir = self.root_dir
        if not base_dir:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
        
        # Serve static files (HTML, CSS, JS)
        if path == '/' or path.endswith('.html') or path.endswith('.css') or path.endswith('.js'):
            # Use os.path.basename to strip directory components, preventing path traversal
            if path == '/':
                safe_name = 'overlay.html'
            else:
                safe_name = os.path.basename(path)
            file_path = os.path.join(base_dir, safe_name)
            
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
            
        elif path == '/artwork' or path.startswith('/artwork?'):
            # Fixed path to the artwork file
            artwork_path = self.artwork_manager.artwork_path if self.artwork_manager else "/tmp/harmony_deck_cover.jpg"
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
            font_path = os.path.join(base_dir, 'assets', 'fonts', font_file)
            
            # Prevent path traversal attacks
            base_fonts_dir = os.path.realpath(os.path.join(base_dir, 'assets', 'fonts'))
            real_font_path = os.path.realpath(font_path)
            if not real_font_path.startswith(base_fonts_dir + os.sep):
                self.send_response(403)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Forbidden')
                return
            
            print(f"Serving font file: {real_font_path}")
            
            try:
                # Open in binary mode for font files
                with open(real_font_path, 'rb') as f:
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
            image_path = os.path.join(base_dir, 'assets', 'images', image_file)
            
            # Prevent path traversal attacks
            base_images_dir = os.path.realpath(os.path.join(base_dir, 'assets', 'images'))
            real_image_path = os.path.realpath(image_path)
            if not real_image_path.startswith(base_images_dir + os.sep):
                self.send_response(403)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Forbidden')
                return
            
            print(f"Serving image file: {real_image_path}")
            
            try:
                # Open in binary mode for image files
                with open(real_image_path, 'rb') as f:
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
