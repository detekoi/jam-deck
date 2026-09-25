# jamdeck/menubar/server_control.py
import os
import sys
import time
import signal
import subprocess
import threading
from datetime import datetime
import rumps
from jamdeck import get_resources_dir
from jamdeck.menubar.config import ConfigManager

# Server output is saved here so problems can be diagnosed after the fact
LOG_DIR = os.path.join(os.path.expanduser("~"), "Library", "Logs", "Jam Deck")
SERVER_LOG_FILE = os.path.join(LOG_DIR, "server.log")
PREVIOUS_SERVER_LOG_FILE = os.path.join(LOG_DIR, "server.previous.log")
# Start a fresh log once the current one reaches this size (the old one is kept as server.previous.log)
MAX_SERVER_LOG_BYTES = 10 * 1024 * 1024

class ServerController:
    def __init__(self, app):
        self.app = app

    @staticmethod
    def _open_server_log():
        """Start a new server log, keeping the last one as server.previous.log.
        
        Returns the open file, or None if the log can't be written.
        """
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            if os.path.exists(SERVER_LOG_FILE):
                os.replace(SERVER_LOG_FILE, PREVIOUS_SERVER_LOG_FILE)
            # Line buffered so the log is current even if the app is force quit
            return open(SERVER_LOG_FILE, "w", encoding="utf-8", buffering=1)
        except OSError as e:
            print(f"Could not open server log {SERVER_LOG_FILE}: {e}")
            return None

    @staticmethod
    def _kill_stale_servers():
        """Kill any orphaned music_server.py processes from a previous app instance.
        
        This handles the case where the old app (e.g. during an auto-update) didn't
        fully clean up its server subprocess before the new app launched.
        Called before starting a new server, so no friendly child process exists yet.
        """
        try:
            # Use a specific pattern to avoid matching editors/terminals with the file open
            result = subprocess.run(
                ["pgrep", "-f", r"music_server\.py --port"],
                capture_output=True, text=True, timeout=3
            )
        except (subprocess.SubprocessError, OSError) as e:
            print(f"Stale server cleanup check failed (non-fatal): {e}")
            return
        if result.returncode != 0 or not result.stdout.strip():
            return
        
        pids = [int(p) for p in result.stdout.split() if p.strip().isdigit()]
        
        # First pass: SIGTERM (allows graceful cleanup of sockets, etc.)
        signaled = []
        for pid in pids:
            print(f"Sending SIGTERM to stale server process (PID {pid})")
            try:
                os.kill(pid, signal.SIGTERM)
                signaled.append(pid)
            except ProcessLookupError:
                pass  # Already exited
            except PermissionError as e:
                print(f"Could not signal PID {pid}: {e}")
        
        # Wait only as long as needed, since this can run on the main (UI) thread
        remaining = ServerController._wait_for_exit(signaled, timeout=1.5)
        
        # Second pass: SIGKILL any that survived SIGTERM
        for pid in remaining:
            print(f"Process {pid} survived SIGTERM, sending SIGKILL")
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        ServerController._wait_for_exit(remaining, timeout=0.5)

    @staticmethod
    def _wait_for_exit(pids, timeout):
        """Poll until the given processes exit or the timeout passes.
        
        Returns the PIDs that are still running.
        """
        deadline = time.monotonic() + timeout
        alive = list(pids)
        while alive:
            still_alive = []
            for pid in alive:
                try:
                    # If it's our own child, reap it. An exited but unreaped (zombie)
                    # process would otherwise still pass the kill(pid, 0) check below.
                    reaped_pid, _ = os.waitpid(pid, os.WNOHANG)
                    if reaped_pid == pid:
                        continue
                except ChildProcessError:
                    pass  # Not our child; its parent (usually launchd) reaps it
                try:
                    os.kill(pid, 0)  # Signal 0 only checks whether the process exists
                    still_alive.append(pid)
                except ProcessLookupError:
                    pass
                except PermissionError:
                    still_alive.append(pid)  # Exists but owned by someone else
            alive = still_alive
            if not alive or time.monotonic() >= deadline:
                break
            time.sleep(0.05)
        return alive

    def start_server(self):
        """Start the music server"""
        if not self.app.server_running:
            try:
                # Kill any orphaned server processes from a previous app instance
                self._kill_stale_servers()
                
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
                
                # Mark as running before the monitor starts, so a server that exits
                # right away is reported as an unexpected stop
                self.app.server_running = True
                self.app.update_menu_state()
                
                # Monitor the server output in a separate thread. It sends the
                # "Server Started" notification once the server reports its port.
                self.app.server_thread = threading.Thread(target=self.monitor_server)
                self.app.server_thread.daemon = True
                self.app.server_thread.start()
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
                # Menu items can only be changed on the main thread, and the updater
                # calls this from a background thread
                if threading.current_thread() is threading.main_thread():
                    self.app.update_menu_state()
                else:
                    self.app.run_on_main_thread(self.app.update_menu_state)

                # Terminate the server process and wait for it to exit, so its port
                # is free and it isn't mistaken for a stale server on restart
                if process_to_terminate:
                    try:
                        process_to_terminate.terminate()
                        process_to_terminate.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        print("Server did not exit after SIGTERM, killing it.")
                        process_to_terminate.kill()
                        try:
                            process_to_terminate.wait(timeout=1)
                        except subprocess.TimeoutExpired:
                            print("Server process still hasn't exited after SIGKILL.")
                    except ProcessLookupError:
                        pass  # Already exited
                
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
        log_file = self._open_server_log()
        while process_ref and process_ref.poll() is None:
            try:
                # Read output line by line
                output = process_ref.stdout.readline()
                if output:
                    line = output.strip()
                    print(f"Server: {line}")
                    
                    # Save the line to the log file with a timestamp
                    if log_file:
                        try:
                            log_file.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {line}\n")
                            if log_file.tell() > MAX_SERVER_LOG_BYTES:
                                log_file.close()
                                log_file = self._open_server_log()
                        except (OSError, ValueError) as e:
                            print(f"Stopped writing server log: {e}")
                            log_file = None
                    
                    # Check for the port line
                    if line.startswith("JAMDECK_PORT="):
                        try:
                            port_str = line.split("=")[1]
                            self.app.actual_port = int(port_str)
                            print(f"Detected server port: {self.app.actual_port}")
                            # Update UI on main thread
                            self.app.run_on_main_thread(self.app.update_menu_state)
                            
                            # Announce the server now that it's actually listening,
                            # warning the user if it fell back to a different port
                            if self.app.actual_port != self.app.preferred_port:
                                fallback_port = self.app.actual_port
                                pref_port = self.app.preferred_port
                                self.app.run_on_main_thread(lambda: rumps.notification(
                                    title="Jam Deck",
                                    subtitle=f"Port {pref_port} was unavailable",
                                    message=f"Server started on port {fallback_port} instead. Another process may be using port {pref_port}.",
                                    sound=False
                                ))
                            else:
                                self.app.run_on_main_thread(lambda: rumps.notification(
                                    title="Jam Deck",
                                    subtitle="Server Started",
                                    message="Now playing overlay is active!",
                                    sound=False
                                ))
                        except (IndexError, ValueError) as e:
                            print(f"Error parsing port from server output: {e}")

                # Check if the server_process reference has changed (happens when stop_server is called)
                if self.app.server_process is None or self.app.server_process != process_ref:
                    break
                    
            except (AttributeError, ValueError):
                break
        
        if log_file:
            # If the server exited, save its last output (e.g. a crash traceback)
            try:
                if process_ref and process_ref.poll() is not None:
                    for line in process_ref.stdout.read().splitlines():
                        log_file.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {line.strip()}\n")
                    log_file.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} Server exited with code {process_ref.returncode}\n")
            except (OSError, ValueError, AttributeError) as e:
                print(f"Could not save final server output: {e}")
            log_file.close()
                
        # Only send notification if we didn't expect the process to end (i.e., it crashed).
        # Checking the process too keeps a restarted server from being reported as stopped.
        if self.app.server_running and self.app.server_process is process_ref:
            self.app.server_running = False
            self.app.actual_port = self.app.preferred_port
            
            rumps.App.notification(
                title="Jam Deck",
                subtitle="Server Stopped Unexpectedly", 
                message="Details are in ~/Library/Logs/Jam Deck/server.log",
                sound=False
            )
            
            # Update menu state on main thread
            self.app.run_on_main_thread(self.app.update_menu_state)

    def open_server_log(self):
        """Open the server log in the default viewer (Console)."""
        if not os.path.exists(SERVER_LOG_FILE):
            rumps.notification(
                title="Jam Deck",
                subtitle="No Server Log Yet",
                message="The log is created when the server starts.",
                sound=False
            )
            return
        try:
            subprocess.run(["open", SERVER_LOG_FILE])
        except Exception as e:
            rumps.notification(
                title="Jam Deck",
                subtitle="Error",
                message=f"Could not open server log: {str(e)}",
                sound=False
            )

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
