# jamdeck/menubar/app.py
import os
import sys
import threading
import subprocess
import rumps

# Patch rumps.notification to avoid crashes when running outside a bundled app
_orig_notification = rumps.notification
def safe_notification(*args, **kwargs):
    try:
        _orig_notification(*args, **kwargs)
    except Exception as e:
        title = kwargs.get('title', args[0] if len(args) > 0 else '')
        subtitle = kwargs.get('subtitle', args[1] if len(args) > 1 else '')
        message = kwargs.get('message', args[2] if len(args) > 2 else '')
        print(f"Notification: [{title}] {subtitle} - {message} (Skipped system alert: {e})")

rumps.notification = safe_notification
rumps.App.notification = safe_notification

from jamdeck import VERSION, get_resources_dir
from jamdeck.menubar.config import ConfigManager
from jamdeck.menubar.scenes import SceneManager
from jamdeck.menubar.updater import UpdateManager
from jamdeck.menubar.server_control import ServerController

class JamDeckApp(rumps.App):
    def __init__(self):
        # Path to menu bar icon resolved using get_resources_dir
        resources_dir = get_resources_dir()
        icon_path = os.path.join(resources_dir, "assets/images/jamdeck-template.png")
        
        super(JamDeckApp, self).__init__("Jam Deck", icon=icon_path, template=True)
        
        # Server controller variables
        self.server_running = False
        self.server_process = None
        self.server_thread = None
        
        # Load configuration
        self.scenes, self.preferred_port = ConfigManager.load_config()
        self.actual_port = self.preferred_port

        # Initialize sub-managers (Composition)
        self.scene_manager = SceneManager(self)
        self.update_manager = UpdateManager(self)
        self.server_controller = ServerController(self)

        # Main-thread callback queue for dispatching UI updates from background threads.
        self._main_thread_queue = []
        self._main_thread_lock = threading.Lock()

        def _process_main_thread_queue(_):
            with self._main_thread_lock:
                pending = list(self._main_thread_queue)
                self._main_thread_queue.clear()
            for cb in pending:
                try:
                    cb()
                except Exception as e:
                    print(f"Main thread callback error: {e}")

        rumps.Timer(_process_main_thread_queue, 0.25).start()

        # --- Menu Setup ---
        set_port_item = rumps.MenuItem("Set Server Port...", callback=self.set_server_port)
        server_item = rumps.MenuItem("Start Server", callback=self.toggle_server)
        self.server_url_display = rumps.MenuItem(f"Server URL: http://localhost:{self.actual_port}", callback=None)
        self.server_url_display.set_callback(None) # Make it non-clickable initially
        open_browser_item = rumps.MenuItem("Open in Browser", callback=self.open_browser)
        docs_item = rumps.MenuItem("Documentation", callback=self.open_documentation)
        self.update_menu_item = rumps.MenuItem("Check for Updates", callback=self.on_check_for_updates)
        about_item = rumps.MenuItem("About", callback=self.show_about)

        # Create dynamic menu placeholders
        self.copy_scenes_menu = rumps.MenuItem("Copy Scene URL")
        self.manage_scenes_menu = rumps.MenuItem("Manage Scenes")

        # Populate dynamic menus
        self.scene_manager.populate_copy_menu(self.copy_scenes_menu)
        self.scene_manager.populate_manage_menu(self.manage_scenes_menu)

        # Assign the full menu structure
        self.menu = [
            server_item,
            self.server_url_display,
            set_port_item,
            None,  # Separator
            self.copy_scenes_menu,
            self.manage_scenes_menu,
            None,  # Separator
            open_browser_item,
            None,  # Separator
            docs_item,
            self.update_menu_item,
            about_item
        ]

        # Update menu text based on current state
        self.update_menu_state()

        # Start background update checks
        def initial_check(timer):
            timer.stop()
            self.update_manager.check_for_updates(manual=False)
        rumps.Timer(initial_check, 5).start()

        # Periodic check every 6 hours (21600 seconds)
        def periodic_check(_):
            self.update_manager.check_for_updates(manual=False)
        rumps.Timer(periodic_check, 21600).start()

    def run_on_main_thread(self, callback):
        """Dispatch a callback to the main thread via the polling queue."""
        with self._main_thread_lock:
            self._main_thread_queue.append(callback)

    def update_menu_state(self):
        """Update the menu items and URL display based on server state"""
        if self.server_running:
            self.menu["Start Server"].title = "Stop Server"
            self.server_url_display.title = f"Server URL: http://localhost:{self.actual_port}"
            self.server_url_display.set_callback(None)
            self.menu["Open in Browser"].set_callback(self.open_browser)
        else:
            self.menu["Start Server"].title = "Start Server"
            self.server_url_display.title = f"Server Stopped (Port: {self.preferred_port})"
            self.server_url_display.set_callback(None)
            self.menu["Open in Browser"].set_callback(self.server_not_running)

    def toggle_server(self, sender):
        """Toggle server on/off"""
        if self.server_running:
            self.server_controller.stop_server()
        else:
            self.server_controller.start_server()

    def start_server(self):
        """Delegate server start to controller"""
        self.server_controller.start_server()

    def stop_server(self):
        """Delegate server stop to controller"""
        self.server_controller.stop_server()

    def set_server_port(self, sender):
        """Delegate port setting to controller"""
        self.server_controller.set_server_port(sender)

    def on_check_for_updates(self, sender):
        """Delegate update check to manager"""
        self.update_manager.on_check_for_updates(sender)

    def open_browser(self, _):
        """Open overlay in default browser using the actual port"""
        if not self.server_running:
            self.server_not_running(None)
            return
        try:
            url = f"http://localhost:{self.actual_port}"
            subprocess.run(["open", url])
        except Exception as e:
            rumps.notification(
                title="Jam Deck",
                subtitle="Error", 
                message=f"Could not open browser: {str(e)}",
                sound=False
            )

    def server_not_running(self, _):
        """Display message when server is not running"""
        rumps.notification(
            title="Jam Deck",
            subtitle="Server Not Running", 
            message="Start the server first.",
            sound=False
        )
        
    def open_documentation(self, _):
        """Open documentation website in browser"""
        try:
            subprocess.run(["open", "https://github.com/detekoi/jam-deck/blob/main/README.md"])
        except Exception as e:
            rumps.notification(
                title="Jam Deck",
                subtitle="Error", 
                message=f"Could not open documentation: {str(e)}",
                sound=False
            )
            
    def show_about(self, _):
        """Show about dialog"""
        rumps.alert(
            title="About Jam Deck",
            message=(
                "Jam Deck for OBS\n"
                f"Version {VERSION}\n\n"
                "Display your Apple Music tracks in OBS.\n\n"
                "OBS Tip - Width: Recommended minimum 400px, Height: 140px\n\n"
                "© 2026 Henry Manes"
            )
        )
