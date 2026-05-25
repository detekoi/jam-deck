# jamdeck/menubar/config.py
import os
import json
import rumps

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".jamdeck_config.json")
OLD_SCENES_FILE = os.path.join(os.path.expanduser("~"), ".jamdeck_scenes")
DEFAULT_PORT = 8080

class ConfigManager:
    @staticmethod
    def load_config():
        """Load configuration (scenes and port) from JSON file, merging old format if necessary."""
        loaded_scenes = ["default"]
        loaded_port = DEFAULT_PORT
        config_updated = False # Flag to track if we need to save merged data

        try:
            # 1. Try loading from the new JSON config file first
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    try:
                        config = json.load(f)
                        # Load scenes, ensuring 'default' is present
                        json_scenes = config.get("scenes", ["default"])
                        if isinstance(json_scenes, list) and json_scenes:
                            loaded_scenes = json_scenes
                        if "default" not in loaded_scenes:
                            loaded_scenes.insert(0, "default")

                        # Load preferred port, validate it's an integer
                        json_port = config.get("preferred_port", DEFAULT_PORT)
                        if isinstance(json_port, int):
                            loaded_port = json_port
                        
                        print(f"Loaded config from JSON: Scenes={loaded_scenes}, Port={loaded_port}")
                    except json.JSONDecodeError as json_err:
                         print(f"Warning: Error decoding JSON config file: {json_err}. Will check for old file.")

            # 2. Check if the old scenes file exists
            if os.path.exists(OLD_SCENES_FILE):
                print("Old scenes file found. Checking for scenes to migrate...")
                old_scenes_list = []
                try:
                    with open(OLD_SCENES_FILE, "r") as f:
                        old_scenes_list = [line.strip() for line in f.readlines() if line.strip()]
                except Exception as read_err:
                     print(f"Warning: Could not read old scenes file: {read_err}")

                # 3. Merge scenes (add old scenes not already present)
                existing_scenes_set = set(loaded_scenes)
                scenes_added = False
                for scene in old_scenes_list:
                    if scene not in existing_scenes_set:
                        loaded_scenes.append(scene)
                        existing_scenes_set.add(scene)
                        scenes_added = True
                        config_updated = True
                        print(f"Migrated scene: {scene}")
                
                if scenes_added:
                     print("Finished migrating scenes.")
                else:
                     print("No new scenes to migrate from old file.")

                # 4. If migration happened, save the merged config
                if config_updated:
                    print("Saving merged configuration to JSON...")
                    try:
                        ConfigManager.save_config(loaded_scenes, loaded_port)
                        print("Merged config saved successfully.")
                        # 5. Attempt to remove old file ONLY after successful save
                        try:
                            os.remove(OLD_SCENES_FILE)
                            print("Removed old scenes file.")
                        except OSError as rm_err:
                            print(f"Warning: Could not remove old scenes file after migration: {rm_err}")
                    except Exception as save_err:
                         print(f"Error saving merged config: {save_err}. Old file not removed.")
                         config_updated = False

                # If no scenes were added, but the old file still exists, try removing it
                elif not scenes_added:
                     try:
                         os.remove(OLD_SCENES_FILE)
                         print("Removed redundant old scenes file.")
                     except OSError as rm_err:
                         print(f"Warning: Could not remove redundant old scenes file: {rm_err}")

            # 6. Return the final state
            print(f"Final loaded config: Scenes={loaded_scenes}, Port={loaded_port}")
            return loaded_scenes, loaded_port

        except Exception as e:
            print(f"Unexpected error during config loading/migration: {e}. Using defaults.")
            return ["default"], DEFAULT_PORT

    @staticmethod
    def save_config(scenes, preferred_port):
        """Save current configuration (scenes and port) to JSON file."""
        config = {
            "scenes": scenes,
            "preferred_port": preferred_port
        }
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            rumps.notification("Jam Deck", "Error", f"Could not save config: {str(e)}", sound=False)
