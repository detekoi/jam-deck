# jamdeck/server/artwork.py
import os
import re
import json
import hashlib
import subprocess
from collections import OrderedDict
from urllib.parse import quote_plus

# How many distinct artwork images to keep in memory for serving
MAX_STORED_ARTWORK = 20


def detect_image_type(data):
    """Return the MIME type for image bytes, or None if they aren't a recognized image."""
    if not data:
        return None
    if data.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if data.startswith((b'GIF87a', b'GIF89a')):
        return 'image/gif'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'image/webp'
    return None


class ArtworkManager:
    """Keeps album artwork in memory, keyed by a hash of the image bytes.

    Each /nowplaying response points at /artwork?id=<hash>, so the overlay always
    receives exactly the image that was chosen for that track. Nothing can be
    swapped out underneath it by a later AppleScript poll or iTunes download.
    """

    def __init__(self, applescript_artwork_path="/tmp/harmony_deck_cover.jpg"):
        # Temp file AppleScript writes the Music app's artwork into.
        # Only AppleScript writes here; iTunes downloads go straight to memory.
        self.applescript_artwork_path = applescript_artwork_path
        # Key: artwork id (hash), Value: (bytes, content_type)
        self.artwork_store = OrderedDict()
        # Key: artwork id, Value: album key of the first track seen with that art.
        # Used to catch the Music app handing back the previous track's artwork.
        self.artwork_owner = {}
        # Key: "artist - title", Value: artwork id (found) or False (not found)
        self.itunes_artwork_cache = {}

    @staticmethod
    def _album_key(artist, album):
        # Albums are keyed by name alone so featured-artist credits
        # ("Kelela & PinkPantheress") still match the rest of the album.
        return (album or "").strip().casefold() or (artist or "").strip().casefold()

    def _store(self, data, content_type, album_key):
        """Store image bytes in memory and return their artwork id."""
        artwork_id = hashlib.sha1(data).hexdigest()[:16]
        self.artwork_owner.setdefault(artwork_id, album_key)
        self.artwork_store[artwork_id] = (data, content_type)
        self.artwork_store.move_to_end(artwork_id)
        while len(self.artwork_store) > MAX_STORED_ARTWORK:
            self.artwork_store.popitem(last=False)
        return artwork_id

    def get_artwork(self, artwork_id):
        """Return (bytes, content_type) for an artwork id, or None if unknown."""
        return self.artwork_store.get(artwork_id)

    def accept_applescript_artwork(self, artist, title, album):
        """Validate the artwork AppleScript just wrote and store it.

        Returns the artwork id, or None if the file is missing, not an image,
        or looks like another album's artwork (a known issue with streamed
        tracks where Music keeps returning the previous track's art).
        """
        try:
            with open(self.applescript_artwork_path, 'rb') as f:
                data = f.read()
        except OSError as e:
            print(f"AppleScript artwork: could not read temp file: {e}")
            return None

        content_type = detect_image_type(data)
        if not content_type:
            print(f"AppleScript artwork for '{artist} - {title}' is not a valid image ({len(data)} bytes). Ignoring it.")
            return None

        artwork_id = hashlib.sha1(data).hexdigest()[:16]
        album_key = self._album_key(artist, album)
        owner = self.artwork_owner.get(artwork_id, album_key)
        if owner != album_key:
            print(f"AppleScript artwork for '{artist} - {title}' ({album}) is identical to artwork "
                  f"already seen for album '{owner}'. Treating it as stale and ignoring it.")
            return None

        return self._store(data, content_type, album_key)

    def _itunes_search(self, search_term, entity="song", limit=1):
        """Perform an iTunes Search API query and return the parsed JSON data.

        Returns the parsed dict on success, or None on failure.
        Uses subprocess curl to avoid SSL issues in py2app bundles.
        """
        query = f"term={quote_plus(search_term)}&media=music&entity={entity}&limit={limit}"
        url = f"https://itunes.apple.com/search?{query}"

        try:
            result = subprocess.run(
                ['curl', '-s', '--max-time', '3', url],
                capture_output=True, text=True, timeout=5
            )

            if result.returncode != 0:
                print(f"iTunes search: curl failed for '{search_term}'")
                return None

            return json.loads(result.stdout)
        except Exception as e:
            print(f"iTunes search error for '{search_term}': {e}")
            return None

    def _download_itunes_artwork(self, art_url, search_term, album_key):
        """Download artwork from a given URL into memory.

        Upscales from 100x100 to 600x600.
        Returns the artwork id on success, None on failure.
        """
        # Upscale from 100x100 to 600x600
        art_url = art_url.replace("100x100bb", "600x600bb")

        try:
            # -f makes curl fail on HTTP errors instead of returning the error page as the body
            dl_result = subprocess.run(
                ['curl', '-s', '-f', '--max-time', '3', art_url],
                capture_output=True, timeout=5
            )

            if dl_result.returncode != 0:
                print(f"iTunes artwork: failed to download for '{search_term}'")
                return None

            data = dl_result.stdout
            content_type = detect_image_type(data)
            if not content_type:
                print(f"iTunes artwork: download for '{search_term}' is not a valid image ({len(data)} bytes)")
                return None

            print(f"iTunes artwork: downloaded for '{search_term}' ({len(data)} bytes)")
            return self._store(data, content_type, album_key)
        except Exception as e:
            print(f"iTunes artwork download error: {e}")
            return None

    def fetch_itunes_artwork(self, artist, title, album):
        """Fetch album artwork from iTunes Search API as a fallback.

        Used when AppleScript can't retrieve artwork (e.g., macOS Tahoe streaming bug,
        or non-JPEG artwork formats).
        Returns the artwork id if artwork was found, None otherwise.
        """
        cache_key = f"{artist} - {title}"

        cached = self.itunes_artwork_cache.get(cache_key)
        # If cache says we previously couldn't find art for this song, don't retry.
        if cached is False:
            return None
        # Reuse the earlier download while it's still in memory.
        if cached and cached in self.artwork_store:
            return cached

        try:
            art_url = None
            strategy_used = None

            # Strategy 1: Search by artist + title (original behavior)
            search_term = f"{artist} {title}"
            data = self._itunes_search(search_term, entity="song", limit=1)
            if data and data.get("resultCount", 0) > 0:
                art_url = data["results"][0].get("artworkUrl100", "")
                strategy_used = "artist+title"

            # Strategy 2: Strip censoring characters (e.g. "F**k" -> "Fk") and retry
            if not art_url:
                cleaned_title = re.sub(r'[*]+', '', title)
                if cleaned_title != title:
                    search_term_clean = f"{artist} {cleaned_title}"
                    print(f"iTunes artwork: retrying with cleaned title: '{search_term_clean}'")
                    data = self._itunes_search(search_term_clean, entity="song", limit=1)
                    if data and data.get("resultCount", 0) > 0:
                        art_url = data["results"][0].get("artworkUrl100", "")
                        strategy_used = "artist+cleaned_title"

            # Strategy 3: Search by artist + album for album-level artwork
            if not art_url and album:
                search_term_album = f"{artist} {album}"
                print(f"iTunes artwork: falling back to album search: '{search_term_album}'")
                data = self._itunes_search(search_term_album, entity="song", limit=1)
                if data and data.get("resultCount", 0) > 0:
                    art_url = data["results"][0].get("artworkUrl100", "")
                    strategy_used = "artist+album"

            # If no artwork URL found from any strategy, cache the miss
            if not art_url:
                print(f"iTunes artwork fallback: no results for '{artist} - {title}' (album: {album}) after all strategies")
                self.itunes_artwork_cache[cache_key] = False
                return None

            # Download the artwork. A failed download isn't cached as a miss,
            # since it's usually a transient network problem.
            artwork_id = self._download_itunes_artwork(art_url, f"{artist} - {title} [via {strategy_used}]",
                                                       self._album_key(artist, album))
            if not artwork_id:
                return None

            self.itunes_artwork_cache[cache_key] = artwork_id
            return artwork_id

        except Exception as e:
            print(f"iTunes artwork fallback error: {e}")
            return None
