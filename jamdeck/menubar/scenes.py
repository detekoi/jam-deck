# jamdeck/menubar/scenes.py
import subprocess
import rumps
from jamdeck.menubar.config import ConfigManager

class SceneManager:
    def __init__(self, app):
        self.app = app

    def populate_copy_menu(self, menu_item):
        """Populate the 'Copy Scene URL' menu."""
        if len(menu_item) > 0:
            menu_item.clear()
            
        if not self.app.scenes:
            menu_item.add(rumps.MenuItem("No scenes defined", callback=None))
        else:
            for scene in self.app.scenes:
                item = rumps.MenuItem(scene, callback=self.copy_scene_url)
                menu_item.add(item)

    def populate_manage_menu(self, menu_item):
        """Populate the 'Manage Scenes' menu."""
        if len(menu_item) > 0:
            menu_item.clear()
            
        menu_item.add(rumps.MenuItem("Add New Scene...", callback=self.add_new_scene))
        menu_item.add(None) # Separator
        
        scene_management_items = self.build_manage_scenes_structure()
        if not scene_management_items:
             menu_item.add(rumps.MenuItem("No scenes to manage", callback=None))
        else:
            for item in scene_management_items:
                menu_item.add(item)

    def build_manage_scenes_structure(self):
        """Generate the list of menu items for scene management."""
        scene_items = []

        for scene in self.app.scenes:
            scene_item = rumps.MenuItem(scene)

            if scene != "default":
                # Create callbacks with scene name embedded in the callback
                rename_callback = lambda sender, scene_name=scene: self.rename_scene_with_name(sender, scene_name)
                delete_callback = lambda sender, scene_name=scene: self.delete_scene_with_name(sender, scene_name)
                
                rename_item = rumps.MenuItem("Rename...", callback=rename_callback)
                delete_item = rumps.MenuItem("Delete", callback=delete_callback)
                scene_item.add(rename_item)
                scene_item.add(delete_item)
            else:
                scene_item.set_callback(None)
            scene_items.append(scene_item)

        return scene_items

    def rebuild_dynamic_menus(self):
        """Rebuild the dynamic menus after scene changes."""
        self.populate_copy_menu(self.app.copy_scenes_menu)
        self.populate_manage_menu(self.app.manage_scenes_menu)

    def copy_scene_url(self, sender):
        """Copy the URL for the selected scene to clipboard using the actual port"""
        if not self.app.server_running:
            self.app.server_not_running(None)
            return
        try:
            base_url = f"http://localhost:{self.app.actual_port}"
            scene_name = sender.title
            if scene_name and scene_name != "default":
                url = f"{base_url}/?scene={scene_name}"
            else:
                url = base_url
            
            subprocess.run("pbcopy", text=True, input=url)
            
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
            scene_name = "".join(c if c.isalnum() else "-" for c in response.text)
            
            if scene_name in self.app.scenes:
                rumps.alert("Scene Error", f"Scene '{scene_name}' already exists.")
                return
            
            self.app.scenes.append(scene_name)
            ConfigManager.save_config(self.app.scenes, self.app.preferred_port)

            self.rebuild_dynamic_menus()

    def rename_scene_with_name(self, sender, scene_name):
        """Rename a scene using the passed scene name"""
        print(f"Renaming scene: {scene_name}")
        
        new_name = rumps.Window(
            title="Rename Scene",
            message=f"Enter new name for '{scene_name}':",
            dimensions=(300, 20)
        ).run()
        
        if new_name.clicked and new_name.text:
            sanitized_name = "".join(c if c.isalnum() else "-" for c in new_name.text)
            
            if scene_name in self.app.scenes:
                index = self.app.scenes.index(scene_name)
                self.app.scenes[index] = sanitized_name
                ConfigManager.save_config(self.app.scenes, self.app.preferred_port)

                self.rebuild_dynamic_menus()

    def delete_scene_with_name(self, sender, scene_name):
        """Delete a scene using the passed scene name"""
        print(f"Deleting scene: {scene_name}")
        
        confirm = rumps.alert(
            title="Confirm Deletion",
            message=f"Are you sure you want to delete the scene '{scene_name}'?",
            ok="No, Keep It",
            cancel="Yes, Delete It"
        )
        
        if confirm != 1:  # Not OK button (so "Yes, Delete It")
            if scene_name in self.app.scenes:
                self.app.scenes.remove(scene_name)
                ConfigManager.save_config(self.app.scenes, self.app.preferred_port)

                self.rebuild_dynamic_menus()
