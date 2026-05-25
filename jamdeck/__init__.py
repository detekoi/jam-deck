# jamdeck/__init__.py
VERSION = "1.1.6"

def get_resources_dir():
    """Locate the project root / Resources directory.

    Works in three scenarios:
    1. Frozen app (sys.frozen) — use RESOURCEPATH or derive from executable.
    2. py2app server subprocess — sys.frozen is NOT set, but __file__ lives
       inside a .app/Contents/Resources/lib/ tree.  Walk up from __file__
       until we find the Contents/Resources directory.
    3. Development mode — parent of the jamdeck package directory.
    """
    import sys
    import os

    # 1. Frozen main process (py2app sets sys.frozen)
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

    # 2. py2app subprocess — __file__ is inside
    #    .app/Contents/Resources/lib/python3.XX/jamdeck/__init__.py
    #    Walk upward to find the Contents/Resources boundary.
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    cur = pkg_dir
    for _ in range(8):  # safety limit
        parent = os.path.dirname(cur)
        if parent == cur:
            break  # hit filesystem root
        if (os.path.basename(cur) == 'Resources'
                and os.path.basename(parent) == 'Contents'):
            return cur
        cur = parent

    # 3. Dev mode: parent of the jamdeck package directory
    return os.path.dirname(pkg_dir)

