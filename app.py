#!/usr/bin/env python3
import rumps
import subprocess
import sys
import os
import threading
import time
import json

# Import version from music_server.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from music_server import VERSION

class JamDeckApp(rumps.App):
    def __init__(self):
        # Path to menu bar icon (template means it adapts to light/dark mode)
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets/images/jamdeck-template.png")
        
        super(JamDeckApp, self).__init__("Jam Deck", icon=icon_path, template=True)
        
        # Set up menu items
        self.server_running = False
        self.server_process = None
        self.server_thread = None
        # self.actual_port = 8080 # Default port, will be updated # Removed old init
        
        # Load configuration
        self.scenes, self.preferred_port = self.load_config()
        self.actual_port = self.preferred_port # Initially assume preferred port, will be updated by server output

        # --- Menu Setup ---
        # Create static items
        set_port_item = rumps.MenuItem("Set Server Port...", callback=self.set_server_port)
        server_item = rumps.MenuItem("Start Server", callback=self.toggle_server)
        self.server_url_display = rumps.MenuItem(f"Server URL: http://localhost:{self.actual_port}", callback=None)
        self.server_url_display.set_callback(None) # Make it non-clickable initially
        open_browser_item = rumps.MenuItem("Open in Browser", callback=self.open_browser)
        docs_item = rumps.MenuItem("Documentation", callback=self.open_documentation)
        about_item = rumps.MenuItem("About", callback=self.show_about)

        # Create dynamic menu placeholders
        self.copy_scenes_menu = rumps.MenuItem("Copy Scene URL")
        self.manage_scenes_menu = rumps.MenuItem("Manage Scenes")

        # Populate dynamic menus
        self._populate_copy_menu(self.copy_scenes_menu)
        self._populate_manage_menu(self.manage_scenes_menu)

        # Assign the full menu structure
        self.menu = [
            server_item,
            self.server_url_display,
            set_port_item, # Add Set Port item
            None,  # Separator
            self.copy_scenes_menu, # Add Copy menu
            self.manage_scenes_menu, # Add Manage menu
            None,  # Separator
            open_browser_item,
            None,  # Separator
            docs_item,
            about_item
        ]

        # Update menu text based on current state
        self.update_menu_state()

    # --- Helper methods for populating dynamic menus ---
    def _populate_copy_menu(self, menu_item):
        """Populate the 'Copy Scene URL' menu."""
        # Only clear if the menu item has existing sub-items
        if len(menu_item) > 0:
            menu_item.clear()
            
        if not self.scenes:
            menu_item.add(rumps.MenuItem("No scenes defined", callback=None))
        else:
            for scene in self.scenes:
                item = rumps.MenuItem(scene, callback=self.copy_scene_url)
                menu_item.add(item)

    def _populate_manage_menu(self, menu_item):
        """Populate the 'Manage Scenes' menu."""
        # Only clear if the menu item has existing sub-items
        if len(menu_item) > 0:
            menu_item.clear()
            
        menu_item.add(rumps.MenuItem("Add New Scene...", callback=self.add_new_scene))
        menu_item.add(None) # Separator
        
        scene_management_items = self._build_manage_scenes_structure()
        if not scene_management_items:
             menu_item.add(rumps.MenuItem("No scenes to manage", callback=None))
        else:
            for item in scene_management_items:
                menu_item.add(item)
    # --- End Helper methods ---

    def update_menu_state(self):
        """Update the menu items and URL display based on server state"""
        server_item = self.menu["Start Server"]
        open_browser_item = self.menu["Open in Browser"]

        if self.server_running:
            server_item.title = "Stop Server"
            self.server_url_display.title = f"Server URL: http://localhost:{self.actual_port}"
            self.server_url_display.set_callback(None) # Keep it non-clickable
            open_browser_item.set_callback(self.open_browser) # Enable Open Browser
        else:
            server_item.title = "Start Server"
            self.server_url_display.title = "Server Stopped"
            self.server_url_display.set_callback(None) # Keep it non-clickable
            open_browser_item.set_callback(self.server_not_running) # Disable Open Browser

    def toggle_server(self, sender):
        """Toggle server on/off"""
        if self.server_running:
            self.stop_server()
        else:
            self.start_server()

    def update_menu_state(self):
        """Update the menu items and URL display based on server state"""
        if self.server_running:
            self.menu["Start Server"].title = "Stop Server"
            self.server_url_display.title = f"Server URL: http://localhost:{self.actual_port}"
            self.server_url_display.set_callback(None) # Keep it non-clickable
            self.menu["Open in Browser"].set_callback(self.open_browser) # Enable Open Browser
        else:
            self.menu["Start Server"].title = "Start Server"
            # Show preferred port when stopped
            self.server_url_display.title = f"Server Stopped (Port: {self.preferred_port})"
            self.server_url_display.set_callback(None) # Keep it non-clickable
            self.menu["Open in Browser"].set_callback(self.server_not_running) # Disable Open Browser

    # This toggle_server definition was duplicated and is removed by the previous block.
    # The correct definition remains above.

    def start_server(self):
        """Start the music server"""
        if not self.server_running:
            try:
                # Get the directory of the current script
                script_dir = os.path.dirname(os.path.abspath(__file__))
                server_path = os.path.join(script_dir, "music_server.py")
                
                # Use Python from the current executable
                python_path = sys.executable
                
                # Start the server in a separate process, passing the preferred port
                cmd = [python_path, server_path, "--port", str(self.preferred_port)]
                print(f"Starting server with command: {' '.join(cmd)}") # Debug output
                self.server_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, # Redirect stderr to stdout
                    text=True,
                    encoding='utf-8'
                )
                
                # Monitor the server output in a separate thread
                self.server_thread = threading.Thread(target=self.monitor_server)
                self.server_thread.daemon = True
                self.server_thread.start()
                
                # Give server a moment to start
                time.sleep(1)
                
                # Update state
                self.server_running = True
                self.update_menu_state()
                
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
        if self.server_running and self.server_process:
            try:
                # Store reference to process before nulling it
                process_to_terminate = self.server_process
                
                # Update state first to prevent monitor_server from triggering crash notification
                self.server_running = False
                self.server_process = None
                # Reset actual_port to the preferred port when stopping, not a hardcoded default
                self.actual_port = self.preferred_port 
                self.update_menu_state()
                
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
        process_ref = self.server_process  # Create a local reference
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
                            self.actual_port = int(port_str)
                            print(f"Detected server port: {self.actual_port}")
                            # Update UI on main thread
                            def update_ui_port():
                                self.update_menu_state()
                            rumps.Timer(0, update_ui_port).start()
                        except (IndexError, ValueError) as e:
                            print(f"Error parsing port from server output: {e}")

                # Check if the server_process reference has changed (happens when stop_server is called)
                if self.server_process is None or self.server_process != process_ref:
                    break
                    
            except (AttributeError, ValueError):
                # Handle possible errors if process is terminated during reading
                break
                
        # Only send notification if we didn't expect the process to end (i.e., it crashed)
        if self.server_running:
            # If we thought it was running, it crashed
            self.server_running = False
            self.actual_port = 8080 # Reset port on crash
            
            # Update UI on main thread
            rumps.App.notification(
                title="Jam Deck",
                subtitle="Server Stopped Unexpectedly", 
                message="Check log for details.",
                sound=False
            )
            
            # Update menu state on main thread
            def update():
                self.update_menu_state()
            rumps.Timer(0, update).start()

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

    def set_server_port(self, _):
        """Show dialog to set the preferred server port."""
        # Define message based on server state
        current_state_msg = "The server will restart if running." if self.server_running else "Change applies on next start."
        
        # Make window narrower and just tall enough for 5 digits
        response = rumps.Window(
            title="Set Server Port",
            message=f"Enter port (1024-65535).\n{current_state_msg}",
            default_text=str(self.preferred_port),
            dimensions=(120, 22) # Width just enough for 5 digits, minimal height
        ).run()

        if response.clicked and response.text:
            was_running = self.server_running # Check server state BEFORE changing port
            port_text = response.text.strip() # Get the entered text
            try:
                # Attempt conversion first
                port_num = int(port_text) 
                
                # Then check the range
                if not (1024 <= port_num <= 65535):
                    raise ValueError("Port must be between 1024 and 65535.") # Raise specific error for range

                # If conversion and range check pass, proceed
                if port_num != self.preferred_port:
                    self.preferred_port = port_num
                    self.save_config() # Save the new port

                    # Decide on action based on whether server was running
                    if was_running:
                            print("Port changed while server running. Restarting server...")
                            rumps.notification(
                                title="Port Updated",
                                subtitle=f"Preferred port set to {self.preferred_port}",
                                message="Restarting server now...",
                                sound=False
                            )
                            self.stop_server()
                            # Short delay before restarting might be needed
                            time.sleep(0.5)
                            self.start_server()
                    else: # Corrected indentation
                        print("Port changed while server stopped.")
                        # Update display placeholder and notify
                        self.actual_port = self.preferred_port
                        self.update_menu_state() # Corrected indentation
                        rumps.notification(
                            title="Port Updated",
                            subtitle=f"Preferred port set to {self.preferred_port}",
                                message="Server will use this port on next start.",
                                sound=False
                            )
                    # No need for an 'else' alert if port is unchanged
                    
            except ValueError as e:
                # Check if the error is due to invalid integer conversion or the range check
                if "invalid literal for int()" in str(e):
                    rumps.alert("Invalid Input", "Please enter numbers only for the port.")
                else:
                    # Handles the ValueError raised for the range check
                    rumps.alert("Invalid Port Range", str(e)) 
            except Exception as e: # Catch any other unexpected errors
                 rumps.alert("Error", f"An unexpected error occurred: {e}")

    # --- Configuration Loading/Saving ---
    CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".jamdeck_config.json")
    DEFAULT_PORT = 8080 # Define default port constant

    OLD_SCENES_FILE = os.path.join(os.path.expanduser("~"), ".jamdeck_scenes")

    def load_config(self):
        """Load configuration (scenes and port) from JSON file, merging old format if necessary."""
        loaded_scenes = ["default"]
        loaded_port = self.DEFAULT_PORT
        config_updated = False # Flag to track if we need to save merged data

        try:
            # 1. Try loading from the new JSON config file first
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, "r") as f:
                    try:
                        config = json.load(f)
                        # Load scenes, ensuring 'default' is present
                        json_scenes = config.get("scenes", ["default"])
                        if isinstance(json_scenes, list) and json_scenes:
                            loaded_scenes = json_scenes
                        if "default" not in loaded_scenes:
                            loaded_scenes.insert(0, "default")

                        # Load preferred port, validate it's an integer
                        json_port = config.get("preferred_port", self.DEFAULT_PORT)
                        if isinstance(json_port, int):
                            loaded_port = json_port
                        
                        print(f"Loaded config from JSON: Scenes={loaded_scenes}, Port={loaded_port}")
                    except json.JSONDecodeError as json_err:
                         print(f"Warning: Error decoding JSON config file: {json_err}. Will check for old file.")
                         # Proceed to check for old file even if JSON is corrupt

            # 2. Check if the old scenes file exists
            if os.path.exists(self.OLD_SCENES_FILE):
                print("Old scenes file found. Checking for scenes to migrate...")
                old_scenes_list = []
                try:
                    with open(self.OLD_SCENES_FILE, "r") as f:
                        old_scenes_list = [line.strip() for line in f.readlines() if line.strip()]
                except Exception as read_err:
                     print(f"Warning: Could not read old scenes file: {read_err}")

                # 3. Merge scenes (add old scenes not already present)
                # Use a set for efficient checking, but maintain order from loaded_scenes
                existing_scenes_set = set(loaded_scenes)
                scenes_added = False
                for scene in old_scenes_list:
                    if scene not in existing_scenes_set:
                        loaded_scenes.append(scene)
                        existing_scenes_set.add(scene)
                        scenes_added = True
                        config_updated = True # Mark that we need to save
                        print(f"Migrated scene: {scene}")
                
                if scenes_added:
                     print("Finished migrating scenes.")
                else:
                     print("No new scenes to migrate from old file.")

                # 4. If migration happened, save the merged config
                if config_updated:
                    print("Saving merged configuration to JSON...")
                    # Use the potentially updated loaded_scenes and the port loaded from JSON (or default)
                    self.scenes = loaded_scenes 
                    self.preferred_port = loaded_port
                    try:
                        self.save_config() # Call save_config directly
                        print("Merged config saved successfully.")
                        # 5. Attempt to remove old file ONLY after successful save
                        try:
                            os.remove(self.OLD_SCENES_FILE)
                            print("Removed old scenes file.")
                        except OSError as rm_err:
                            print(f"Warning: Could not remove old scenes file after migration: {rm_err}")
                    except Exception as save_err:
                         print(f"Error saving merged config: {save_err}. Old file not removed.")
                         # Keep config_updated = True? Maybe not, if save failed. Let's reset.
                         config_updated = False # Revert flag as save failed
                         # Revert self.scenes/port to what was loaded initially? Or just return defaults?
                         # Let's return what we managed to load initially before the failed save.
                         # The initial load logic already handled defaults if JSON load failed.

                # If no scenes were added, but the old file still exists, try removing it
                elif not scenes_added:
                     try:
                         os.remove(self.OLD_SCENES_FILE)
                         print("Removed redundant old scenes file.")
                     except OSError as rm_err:
                         print(f"Warning: Could not remove redundant old scenes file: {rm_err}")


            # 6. Return the final state
            print(f"Final loaded config: Scenes={loaded_scenes}, Port={loaded_port}")
            return loaded_scenes, loaded_port

        except Exception as e:
            print(f"Unexpected error during config loading/migration: {e}. Using defaults.")
            # Return defaults in case of any unexpected error
            return ["default"], self.DEFAULT_PORT

    def save_config(self):
        """Save current configuration (scenes and port) to JSON file."""
        config = {
            "scenes": self.scenes,
            "preferred_port": self.preferred_port
        }
        try:
            with open(self.CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            rumps.notification("Jam Deck", "Error", f"Could not save scenes: {str(e)}", sound=False)

    # Method removed: create_copy_scenes_menu (functionality moved to _populate_copy_menu and _populate_manage_menu)

    def _rebuild_dynamic_menus(self):
        """Rebuild the dynamic menus after scene changes."""
        self._populate_copy_menu(self.copy_scenes_menu)
        self._populate_manage_menu(self.manage_scenes_menu)

    def copy_scene_url(self, sender):
        """Copy the URL for the selected scene to clipboard using the actual port"""
        if not self.server_running:
            self.server_not_running(None)
            return
        try:
            # Base URL using the actual port
            base_url = f"http://localhost:{self.actual_port}"
            
            # Add scene parameter if not default
            scene_name = sender.title
            if scene_name and scene_name != "default":
                url = f"{base_url}/?scene={scene_name}"
            else:
                url = base_url
            
            # Copy URL to clipboard using pbcopy
            subprocess.run("pbcopy", text=True, input=url)
            
            # Notification
            rumps.notification(
                title="Jam Deck",
                subtitle="URL Copied",
                message=f"OBS source URL for scene '{scene_name}' copied to clipboard",
                sound=False
            )
        except Exception as e:
            rumps.notification(
                title="Jam Deck",
                subtitle="Error",
                message=f"Could not copy URL: {str(e)}",
                sound=False
            )

    def add_new_scene(self, _):
        """Show dialog to add a new scene"""
        response = rumps.Window(
            title="Add New Scene",
            message="Enter a name for the new scene:",
            dimensions=(300, 20)
        ).run()
        
        if response.clicked and response.text:
            # Sanitize name for URL (replace spaces with hyphens, remove special chars)
            scene_name = "".join(c if c.isalnum() else "-" for c in response.text)
            
            # Check if name exists
            if scene_name in self.scenes:
                rumps.alert("Scene Error", f"Scene '{scene_name}' already exists.")
                return
            
            # Add the new scene
            self.scenes.append(scene_name)
            self.save_config() # Use new save method

            # Rebuild dynamic menus
            self._rebuild_dynamic_menus()

    def manage_scenes(self, _):
        """Placeholder callback for the 'Manage Scenes' menu item itself."""
        # This function is just a placeholder for menu item callback
        # The actual menu structure is built in _build_manage_scenes_structure and added in _populate_manage_menu
        pass

    def _build_manage_scenes_structure(self):
        """Generate the list of menu items for scene management."""
        scene_items = []

        # Add each scene as a menu item with its own submenu
        for scene in self.scenes:
            # Use the scene name directly for the item title in this context
            scene_item = rumps.MenuItem(scene)

            # Only add operation submenus for non-default scenes
            if scene != "default":
                # Create callbacks with scene name embedded in the callback
                rename_callback = lambda sender, scene_name=scene: self.rename_scene_with_name(sender, scene_name)
                delete_callback = lambda sender, scene_name=scene: self.delete_scene_with_name(sender, scene_name)
                
                rename_item = rumps.MenuItem("Rename...", callback=rename_callback)
                delete_item = rumps.MenuItem("Delete", callback=delete_callback)
                scene_item.add(rename_item)
                scene_item.add(delete_item)
            else:
                # Make default scene item appear disabled
                scene_item.set_callback(None)
            scene_items.append(scene_item)

        return scene_items

    def rename_scene_with_name(self, sender, scene_name):
        """Rename a scene using the passed scene name"""
        print(f"Renaming scene: {scene_name}")
        
        # Show rename dialog
        new_name = rumps.Window(
            title="Rename Scene",
            message=f"Enter new name for '{scene_name}':",
            dimensions=(300, 20)
        ).run()
        
        if new_name.clicked and new_name.text:
            # Sanitize name
            sanitized_name = "".join(c if c.isalnum() else "-" for c in new_name.text)
            
            # Find and update scene name
            if scene_name in self.scenes:
                index = self.scenes.index(scene_name)
                self.scenes[index] = sanitized_name
                self.save_config() # Use new save method

                # Rebuild dynamic menus
                self._rebuild_dynamic_menus()

    def delete_scene_with_name(self, sender, scene_name):
        """Delete a scene using the passed scene name"""
        print(f"Deleting scene: {scene_name}")
        
        # Confirm deletion
        confirm = rumps.alert(
            title="Confirm Deletion",
            message=f"Are you sure you want to delete the scene '{scene_name}'?",
            ok="No, Keep It",
            cancel="Yes, Delete It"
        )
        
        if confirm != 1:  # Not OK button (so "Yes, Delete It")
            # Remove the scene
            if scene_name in self.scenes:
                self.scenes.remove(scene_name)
                self.save_config() # Use new save method

                # Rebuild dynamic menus
                self._rebuild_dynamic_menus()


if __name__ == "__main__":
    app = JamDeckApp()
    # Auto-start server when app launches
    app.start_server()
    app.run()
