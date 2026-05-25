# jamdeck/__init__.py
VERSION = "1.1.6"

def get_resources_dir():
    import sys
    import os
    if getattr(sys, 'frozen', False):
        resource_path = os.environ.get('RESOURCEPATH')
        if resource_path and os.path.exists(resource_path):
            return resource_path
        # Contents/MacOS/Jam Deck -> Contents/Resources
        mac_os_dir = os.path.dirname(os.path.abspath(sys.executable))
        contents_dir = os.path.dirname(mac_os_dir)
        resources_dir = os.path.join(contents_dir, 'Resources')
        if os.path.exists(resources_dir):
            return resources_dir
            
    # Dev mode: parent of the jamdeck package directory
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

