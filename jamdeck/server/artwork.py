# jamdeck/server/artwork.py
import re
import json
import time
import hashlib
import subprocess
from collections import OrderedDict, deque
from urllib.parse import quote_plus

# How many distinct artwork images to keep in memory for serving
MAX_STORED_ARTWORK = 20
# How many songs to remember iTunes lookup results for
MAX_ITUNES_CACHE_ENTRIES = 500
# How many previous tracks to compare Music app artwork against when checking for stale art
RECENT_TRACKS_CHECKED = 3
# How long to wait before retrying an iTunes lookup that failed from a network error
ITUNES_RETRY_DELAY_SECONDS = 60


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
        # (track key, album key, artwork id) for the current track and the few before it.
        # Used to catch the Music app handing back a previous track's artwork.
        self.recent_tracks = deque(maxlen=RECENT_TRACKS_CHECKED + 1)
        # Key: "artist - title", Value: artwork id (found) or False (no results)
        self.itunes_artwork_cache = OrderedDict()
        # Key: "artist - title", Value: time after which a failed lookup may be retried
        self.itunes_retry_after = {}

    @staticmethod
    def _album_key(artist, album):
        # Albums are keyed by name alone so featured-artist credits
        # ("Kelela & PinkPantheress") still match the rest of the album.
        return (album or "").strip().casefold() or (artist or "").strip().casefold()

    @staticmethod
    def _track_key(artist, title):
        return f"{artist}|||{title}"

    def _store(self, data, content_type):
        """Store image bytes in memory and return their artwork id."""
        artwork_id = hashlib.sha1(data).hexdigest()[:16]
        self.artwork_store[artwork_id] = (data, content_type)
        self.artwork_store.move_to_end(artwork_id)
        while len(self.artwork_store) > MAX_STORED_ARTWORK:
            self.artwork_store.popitem(last=False)
        return artwork_id

    def get_artwork(self, artwork_id):
        """Return (bytes, content_type) for an artwork id, or None if unknown."""
        return self.artwork_store.get(artwork_id)

    def remember_track_artwork(self, artist, title, album, artwork_id):
        """Record which artwork was chosen for the track that's playing."""
        entry = (self._track_key(artist, title), self._album_key(artist, album), artwork_id)
        if self.recent_tracks and self.recent_tracks[-1][0] == entry[0]:
            self.recent_tracks[-1] = entry  # Same track still playing
        else:
            self.recent_tracks.append(entry)

    def _stale_artwork_album(self, artwork_id, artist, title, album):
        """Return the album a recent, different track showed this artwork for, or None.
        
        Only recent tracks are checked, so a single and its album that share
        identical artwork aren't rejected when played far apart.
        """
        track_key = self._track_key(artist, title)
        album_key = self._album_key(artist, album)
        for recent_track, recent_album, recent_artwork_id in self.recent_tracks:
            if (recent_track != track_key and recent_artwork_id == artwork_id
                    and recent_album != album_key):
                return recent_album
        return None

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
        stale_album = self._stale_artwork_album(artwork_id, artist, title, album)
        if stale_album is not None:
            print(f"AppleScript artwork for '{artist} - {title}' ({album}) is identical to artwork "
                  f"just shown for album '{stale_album}'. Treating it as stale and ignoring it.")
            return None

        return self._store(data, content_type)

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
        except (subprocess.SubprocessError, OSError, ValueError) as e:
            print(f"iTunes search error for '{search_term}': {e}")
            return None

    def _download_itunes_artwork(self, art_url, search_term):
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
            return self._store(data, content_type)
        except (subprocess.SubprocessError, OSError) as e:
            print(f"iTunes artwork download error: {e}")
            return None

    def _cache_itunes_result(self, cache_key, value):
        """Remember an iTunes lookup result, dropping the oldest once the cache is full."""
        self.itunes_artwork_cache[cache_key] = value
        self.itunes_artwork_cache.move_to_end(cache_key)
        while len(self.itunes_artwork_cache) > MAX_ITUNES_CACHE_ENTRIES:
            self.itunes_artwork_cache.popitem(last=False)
        self.itunes_retry_after.pop(cache_key, None)

    def _itunes_lookup_failed(self, cache_key):
        """Back off before retrying a lookup that failed from a network error, so the
        searches don't run again on every poll (the server handles one request at a time)."""
        self.itunes_retry_after[cache_key] = time.monotonic() + ITUNES_RETRY_DELAY_SECONDS
        # Drop expired entries so this stays small
        now = time.monotonic()
        for key in [k for k, t in self.itunes_retry_after.items() if t <= now]:
            del self.itunes_retry_after[key]

    def fetch_itunes_artwork(self, artist, title, album):
        """Fetch album artwork from iTunes Search API as a fallback.
        
        Used when AppleScript can't retrieve artwork (e.g., macOS Tahoe streaming bug,
        or non-JPEG artwork formats).
        Returns the artwork id if artwork was found, None otherwise.
        """
        cache_key = f"{artist} - {title}"
        
        cached = self.itunes_artwork_cache.get(cache_key)
        # If cache says iTunes has no results for this song, don't retry.
        if cached is False:
            return None
        # Reuse the earlier download while it's still in memory.
        if cached and cached in self.artwork_store:
            return cached
        # Wait out the backoff after a recent network failure.
        if time.monotonic() < self.itunes_retry_after.get(cache_key, 0):
            return None
        
        try:
            art_url = None
            strategy_used = None
            search_failed = False
            
            def search(term):
                nonlocal search_failed
                data = self._itunes_search(term, entity="song", limit=1)
                if data is None:
                    search_failed = True
                    return None
                if data.get("resultCount", 0) > 0:
                    return data["results"][0].get("artworkUrl100", "")
                return None
            
            # Strategy 1: Search by artist + title (original behavior)
            art_url = search(f"{artist} {title}")
            strategy_used = "artist+title"
            
            # Strategy 2: Strip censoring characters (e.g. "F**k" -> "Fk") and retry
            if not art_url:
                cleaned_title = re.sub(r'[*]+', '', title)
                if cleaned_title != title:
                    search_term_clean = f"{artist} {cleaned_title}"
                    print(f"iTunes artwork: retrying with cleaned title: '{search_term_clean}'")
                    art_url = search(search_term_clean)
                    strategy_used = "artist+cleaned_title"
            
            # Strategy 3: Search by artist + album for album-level artwork
            if not art_url and album:
                search_term_album = f"{artist} {album}"
                print(f"iTunes artwork: falling back to album search: '{search_term_album}'")
                art_url = search(search_term_album)
                strategy_used = "artist+album"
            
            if not art_url:
                if search_failed:
                    # A network error isn't proof there's no artwork, so retry later
                    print(f"iTunes artwork fallback: search failed for '{artist} - {title}', "
                          f"retrying in {ITUNES_RETRY_DELAY_SECONDS}s")
                    self._itunes_lookup_failed(cache_key)
                else:
                    print(f"iTunes artwork fallback: no results for '{artist} - {title}' (album: {album}) after all strategies")
                    self._cache_itunes_result(cache_key, False)
                return None
            
            artwork_id = self._download_itunes_artwork(art_url, f"{artist} - {title} [via {strategy_used}]")
            if not artwork_id:
                self._itunes_lookup_failed(cache_key)
                return None
            
            self._cache_itunes_result(cache_key, artwork_id)
            return artwork_id
            
        except (KeyError, IndexError, TypeError, AttributeError) as e:
            # Unexpected response shape from the iTunes API
            print(f"iTunes artwork fallback error: {e}")
            self._itunes_lookup_failed(cache_key)
            return None
