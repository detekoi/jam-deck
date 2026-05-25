# jamdeck/menubar/updater.py
import os
import sys
import json
import threading
import subprocess
import rumps
from jamdeck import VERSION

class UpdateManager:
    def __init__(self, app):
        self.app = app
        self.notified_version = None
        self.latest_release_url = "https://github.com/detekoi/jam-deck/releases"
        self.latest_version_str = None
        self.update_checking_in_progress = False

    def _parse_version(self, version_str):
        """Parse a version string like '1.1.6' or 'v1.1.6' into a comparable tuple of ints."""
        try:
            cleaned = version_str.strip().lstrip('v')
            base_version = cleaned.split('-')[0]
            return tuple(int(x) for x in base_version.split('.'))
        except Exception:
            return (0, 0, 0)

    def check_for_updates(self, manual=False):
        """Check GitHub for updates in a background thread."""
        if self.update_checking_in_progress:
            return
        
        self.update_checking_in_progress = True
        
        if manual:
            self.app.update_menu_item.title = "Checking for Updates..."
            
        def run_check():
            try:
                # Use curl to request the latest release JSON
                url = "https://api.github.com/repos/detekoi/jam-deck/releases/latest"
                cmd = ['curl', '-s', '--max-time', '5', url]
                result = subprocess.run(cmd, capture_output=True, timeout=7)
                
                if result.returncode != 0:
                    print("Update check: curl failed")
                    if manual:
                        self.app.run_on_main_thread(lambda: rumps.alert("Update Check Failed", "Could not connect to GitHub. Please check your internet connection and try again."))
                    return
                
                stdout_str = result.stdout.decode('utf-8', errors='replace')
                data = json.loads(stdout_str)
                latest_tag = data.get("tag_name")
                release_url = data.get("html_url", "https://github.com/detekoi/jam-deck/releases")
                
                if not latest_tag:
                    print("Update check: tag_name not found in response")
                    if manual:
                        self.app.run_on_main_thread(lambda: rumps.alert("Update Check Failed", "Received invalid response from GitHub."))
                    return
                
                latest_ver = self._parse_version(latest_tag)
                current_ver = self._parse_version(VERSION)
                
                print(f"Update check: Latest is {latest_tag} ({latest_ver}), Current is {VERSION} ({current_ver})")
                
                self.latest_release_url = release_url
                self.latest_version_str = latest_tag
                
                if latest_ver > current_ver:
                    tag = latest_tag
                    self.app.run_on_main_thread(lambda: setattr(self.app.update_menu_item, 'title', f"Update Available ({tag}) \u2193"))
                    
                    if self.notified_version != latest_tag:
                        self.notified_version = latest_tag
                        self.app.run_on_main_thread(lambda: rumps.notification(
                            title="Jam Deck Update Available",
                            subtitle=f"Version {tag} is ready!",
                            message="Click 'Update Available' in the menu bar to download.",
                            sound=False
                        ))
                else:
                    def _handle_uptodate():
                        self.app.update_menu_item.title = "Check for Updates"
                        if manual:
                            rumps.alert("Jam Deck is Up to Date", f"You are running the latest version (v{VERSION}).")
                    self.app.run_on_main_thread(_handle_uptodate)
                    
            except Exception as e:
                print(f"Update check error: {e}")
                if manual:
                    err_msg = str(e)
                    self.app.run_on_main_thread(lambda: rumps.alert("Update Check Error", f"An error occurred while checking for updates:\n{err_msg}"))
            finally:
                self.update_checking_in_progress = False
                if manual and self.app.update_menu_item.title == "Checking for Updates...":
                    self.app.run_on_main_thread(lambda: setattr(self.app.update_menu_item, 'title', 'Check for Updates'))
                    
        threading.Thread(target=run_check, daemon=True).start()

    def on_check_for_updates(self, sender):
        """Callback when user clicks 'Check for Updates' / 'Update Available'."""
        current_ver = self._parse_version(VERSION)
        latest_ver = self._parse_version(self.latest_version_str) if self.latest_version_str else (0, 0, 0)
        
        if self.latest_version_str and latest_ver > current_ver:
            # Prompt the user for confirmation
            choice = rumps.alert(
                title="Update Jam Deck",
                message=f"A new version of Jam Deck is available!\n\n"
                        f"Current Version: v{VERSION}\n"
                        f"Latest Version: {self.latest_version_str}\n\n"
                        f"Would you like to download and install this update now? "
                        f"The application will restart automatically.",
                ok="Download and Install",
                cancel="Cancel"
            )
            if choice == 1:  # "Download and Install" clicked
                self.install_update()
        else:
            self.check_for_updates(manual=True)

    def install_update(self):
        """Download the DMG, mount it, and replace the running app."""
        if self.update_checking_in_progress:
            return
            
        self.update_checking_in_progress = True
        self.app.update_menu_item.title = "Downloading Update..."
        
        def run_update():
            dmg_path = "/tmp/JamDeck_latest.dmg"
            try:
                # 1. Download DMG
                print(f"Downloading update from {self.latest_release_url}...")
                
                # Fetch direct download URL from release JSON
                url = "https://api.github.com/repos/detekoi/jam-deck/releases/latest"
                cmd = ['curl', '-s', '--max-time', '5', url]
                result = subprocess.run(cmd, capture_output=True, timeout=7)
                
                if result.returncode != 0:
                    raise Exception("Failed to contact GitHub to retrieve download link.")
                    
                stdout_str = result.stdout.decode('utf-8', errors='replace')
                data = json.loads(stdout_str)
                assets = data.get("assets", [])
                download_url = None
                for asset in assets:
                    if asset.get("name", "").endswith(".dmg"):
                        download_url = asset.get("browser_download_url")
                        break
                        
                if not download_url:
                    latest_tag = data.get("tag_name", self.latest_version_str)
                    download_url = f"https://github.com/detekoi/jam-deck/releases/download/{latest_tag}/JamDeck.dmg"
                
                print(f"Downloading DMG from: {download_url}")
                dl_cmd = ['curl', '-L', '-s', '--max-time', '60', '-o', dmg_path, download_url]
                dl_result = subprocess.run(dl_cmd, capture_output=True, timeout=65)
                
                if dl_result.returncode != 0 or not os.path.exists(dmg_path) or os.path.getsize(dmg_path) < 1000000:
                    raise Exception("Failed to download the update DMG file.")
                    
                # 2. Mount DMG
                self.app.run_on_main_thread(lambda: setattr(self.app.update_menu_item, 'title', 'Installing Update...'))
                
                print("Mounting DMG...")
                mount_cmd = ["hdiutil", "attach", "-nobrowse", "-readonly", dmg_path]
                mount_result = subprocess.run(mount_cmd, capture_output=True, timeout=15)
                
                mount_stdout = mount_result.stdout.decode('utf-8', errors='replace')
                mount_stderr = mount_result.stderr.decode('utf-8', errors='replace')
                
                if mount_result.returncode != 0:
                    raise Exception(f"Failed to mount the downloaded DMG: {mount_stderr}")
                    
                idx = mount_stdout.find("/Volumes/")
                if idx == -1:
                    raise Exception("DMG mounted, but could not determine volume mount point.")
                mount_point = mount_stdout[idx:].splitlines()[0].strip()
                print(f"Mounted successfully at: {mount_point}")
                
                src_app_path = os.path.join(mount_point, "Jam Deck.app")
                if not os.path.exists(src_app_path):
                    subprocess.run(["hdiutil", "detach", mount_point])
                    raise Exception(f"Could not find Jam Deck.app inside the volume '{mount_point}'.")
                
                # Determine destination path
                if getattr(sys, 'frozen', False) or "Jam Deck.app/Contents/MacOS" in sys.executable:
                    is_bundled = True
                    dest_app_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(sys.executable))))
                else:
                    is_bundled = False
                    dest_app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "dist", "Jam Deck.app")
                    
                print(f"Source: {src_app_path}")
                print(f"Destination: {dest_app_path}")
                
                # Check write permissions
                dest_dir = os.path.dirname(dest_app_path)
                if not os.access(dest_dir, os.W_OK) or (os.path.exists(dest_app_path) and not os.access(dest_app_path, os.W_OK)):
                    subprocess.run(["hdiutil", "detach", mount_point])
                    raise PermissionError(f"Jam Deck does not have permission to overwrite the app at '{dest_app_path}'.")
                
                # 3. Spawn background script to overwrite and relaunch
                self._run_updater_script(dmg_path, mount_point, src_app_path, dest_app_path, is_bundled)
                
                # 4. Exit parent process
                if self.app.server_running:
                    self.app.stop_server()
                os._exit(0)
                
            except Exception as e:
                print(f"Installation error: {e}")
                try:
                    vol_path = "/Volumes/JamDeck"
                    if os.path.exists(vol_path):
                        subprocess.run(["hdiutil", "detach", vol_path])
                    if os.path.exists(dmg_path):
                        os.remove(dmg_path)
                except Exception:
                    pass
                    
                err_msg = str(e)
                def _handle_install_error():
                    rumps.alert("Update Installation Failed", f"An error occurred during update installation:\n{err_msg}")
                    self.app.update_menu_item.title = "Check for Updates"
                self.app.run_on_main_thread(_handle_install_error)
            finally:
                self.update_checking_in_progress = False
                
        threading.Thread(target=run_update, daemon=True).start()

    def _run_updater_script(self, dmg_path, mount_point, src_app_path, dest_app_path, is_bundled):
        """Spawn a detached shell script to replace the app and relaunch it."""
        parent_pid = os.getpid()
        
        escaped_dest = dest_app_path.replace('"', '\\"')
        escaped_src = src_app_path.replace('"', '\\"')
        escaped_mount = mount_point.replace('"', '\\"')
        escaped_dmg = dmg_path.replace('"', '\\"')
        
        if is_bundled:
            launch_cmd = f'open "{escaped_dest}"'
        else:
            launch_cmd = f'echo "Dev mode: App updated successfully!"'
            
        script = f"""
        (
            # Wait for parent process to exit
            while kill -0 {parent_pid} 2>/dev/null; do
                sleep 0.1
            done
            
            # Overwrite the app
            rm -rf "{escaped_dest}"
            cp -R "{escaped_src}" "{escaped_dest}"
            
            # Cleanup DMG and mount point
            hdiutil detach "{escaped_mount}"
            rm -f "{escaped_dmg}"
            
            # Relaunch the app
            {launch_cmd}
        ) &
        """
        print(f"Spawning background updater script:\n{script}")
        subprocess.Popen(script, shell=True, start_new_session=True)
