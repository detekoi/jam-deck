# jamdeck/menubar/server_control.py
import os
import sys
import time
import subprocess
import threading
import rumps
from jamdeck import get_resources_dir
from jamdeck.menubar.config import ConfigManager

class ServerController:
    def __init__(self, app):
        self.app = app

    def start_server(self):
        """Start the music server"""
        if not self.app.server_running:
            try:
                # Find music_server.py using get_resources_dir
                resources_dir = get_resources_dir()
                server_path = os.path.join(resources_dir, "music_server.py")
                
                # Use Python from the current executable
                python_path = sys.executable
                
                # Start the server in a separate process, passing the preferred port
                cmd = [python_path, server_path, "--port", str(self.app.preferred_port)]
                print(f"Starting server with command: {' '.join(cmd)}")
                self.app.server_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, # Redirect stderr to stdout
                    text=True,
                    encoding='utf-8'
                )
                
                # Monitor the server output in a separate thread
                self.app.server_thread = threading.Thread(target=self.monitor_server)
                self.app.server_thread.daemon = True
                self.app.server_thread.start()
                
                # Give server a moment to start
                time.sleep(1)
                
                # Update state
                self.app.server_running = True
                self.app.update_menu_state()
                
                # Notify user
                rumps.notification(
                    title="Jam Deck",
                    subtitle="Server Started", 
                    message="Now playing overlay is active!",
                    sound=False
                )
            except Exception as e:
                rumps.notification(
                    title="Jam Deck",
                    subtitle="Error Starting Server", 
                    message=str(e),
                    sound=False
                )

    def stop_server(self):
        """Stop the music server"""
        if self.app.server_running and self.app.server_process:
            try:
                # Store reference to process before nulling it
                process_to_terminate = self.app.server_process
                
                # Update state first to prevent monitor_server from triggering crash notification
                self.app.server_running = False
                self.app.server_process = None
                self.app.actual_port = self.app.preferred_port 
                self.app.update_menu_state()
                
                # Terminate the server process
                if process_to_terminate:
                    try:
                        process_to_terminate.terminate()
                    except Exception:
                        # Process might have already exited
                        pass
                
                # Notify user
                rumps.notification(
                    title="Jam Deck",
                    subtitle="Server Stopped", 
                    message="Overlay is no longer available.",
                    sound=False
                )
            except Exception as e:
                rumps.notification(
                    title="Jam Deck",
                    subtitle="Error Stopping Server", 
                    message=str(e),
                    sound=False
                )

    def monitor_server(self):
        """Monitor server output and handle process exit"""
        process_ref = self.app.server_process
        while process_ref and process_ref.poll() is None:
            try:
                # Read output line by line
                output = process_ref.stdout.readline()
                if output:
                    line = output.strip()
                    print(f"Server: {line}")
                    
                    # Check for the port line
                    if line.startswith("JAMDECK_PORT="):
                        try:
                            port_str = line.split("=")[1]
                            self.app.actual_port = int(port_str)
                            print(f"Detected server port: {self.app.actual_port}")
                            # Update UI on main thread
                            self.app.run_on_main_thread(self.app.update_menu_state)
                        except (IndexError, ValueError) as e:
                            print(f"Error parsing port from server output: {e}")

                # Check if the server_process reference has changed (happens when stop_server is called)
                if self.app.server_process is None or self.app.server_process != process_ref:
                    break
                    
            except (AttributeError, ValueError):
                break
                
        # Only send notification if we didn't expect the process to end (i.e., it crashed)
        if self.app.server_running:
            self.app.server_running = False
            self.app.actual_port = self.app.preferred_port
            
            rumps.App.notification(
                title="Jam Deck",
                subtitle="Server Stopped Unexpectedly", 
                message="Check log for details.",
                sound=False
            )
            
            # Update menu state on main thread
            self.app.run_on_main_thread(self.app.update_menu_state)

    def set_server_port(self, _):
        """Show dialog to set the preferred server port."""
        current_state_msg = "The server will restart if running." if self.app.server_running else "Change applies on next start."
        
        response = rumps.Window(
            title="Set Server Port",
            message=f"Enter port (1024-65535).\n{current_state_msg}",
            default_text=str(self.app.preferred_port),
            dimensions=(120, 22)
        ).run()

        if response.clicked and response.text:
            was_running = self.app.server_running
            port_text = response.text.strip()
            try:
                port_num = int(port_text)
                
                if not (1024 <= port_num <= 65535):
                    raise ValueError("Port must be between 1024 and 65535.")

                port_changed = port_num != self.app.preferred_port
                actual_port_mismatch = self.app.server_running and self.app.actual_port != port_num

                if port_changed or actual_port_mismatch:
                    self.app.preferred_port = port_num
                    if port_changed:
                        ConfigManager.save_config(self.app.scenes, self.app.preferred_port)

                    if was_running:
                        print(f"Port {'changed' if port_changed else 'unchanged but actual port mismatched'}. Restarting server...")
                        rumps.notification(
                            title="Port Updated",
                            subtitle=f"Preferred port set to {self.app.preferred_port}",
                            message="Restarting server now...",
                            sound=False
                        )
                        self.stop_server()
                        time.sleep(0.5)
                        self.start_server()
                    else:
                        print("Port changed while server stopped.")
                        self.app.actual_port = self.app.preferred_port
                        self.app.update_menu_state()
                        rumps.notification(
                            title="Port Updated",
                            subtitle=f"Preferred port set to {self.app.preferred_port}",
                            message="Server will use this port on next start.",
                            sound=False
                        )
                    
            except ValueError as e:
                if "invalid literal for int()" in str(e):
                    rumps.alert("Invalid Input", "Please enter numbers only for the port.")
                else:
                    rumps.alert("Invalid Port Range", str(e)) 
            except Exception as e:
                 rumps.alert("Error", f"An unexpected error occurred: {e}")
