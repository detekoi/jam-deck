# jamdeck/server/artwork.py
import os
import re
import json
import subprocess
from urllib.parse import quote_plus

class ArtworkManager:
    def __init__(self, artwork_path="/tmp/harmony_deck_cover.jpg"):
        self.artwork_path = artwork_path
        # Key: "artist - title", Value: True (found & downloaded) or False (not found)
        self.itunes_artwork_cache = {}
        # Track which song's artwork is currently written to the temp file.
        self.last_artwork_track = None  # Will be set to "artist|||title"

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

    def _download_itunes_artwork(self, art_url, search_term):
        """Download artwork from a given URL to the temp file.
        
        Upscales from 100x100 to 600x600 and saves to self.artwork_path.
        Returns True on success, False on failure.
        """
        # Upscale from 100x100 to 600x600
        art_url = art_url.replace("100x100bb", "600x600bb")
        
        try:
            dl_result = subprocess.run(
                ['curl', '-s', '--max-time', '3', '-o', self.artwork_path, art_url],
                capture_output=True, timeout=5
            )
            
            if dl_result.returncode != 0:
                print(f"iTunes artwork: failed to download for '{search_term}'")
                return False
            
            file_size = os.path.getsize(self.artwork_path)
            print(f"iTunes artwork: downloaded for '{search_term}' ({file_size} bytes)")
            return True
        except Exception as e:
            print(f"iTunes artwork download error: {e}")
            return False

    def fetch_itunes_artwork(self, artist, title, album):
        """Fetch album artwork from iTunes Search API as a fallback.
        
        Used when AppleScript can't retrieve artwork (e.g., macOS Tahoe streaming bug,
        or non-JPEG artwork formats).
        Downloads 600x600 artwork to self.artwork_path.
        Returns True if artwork was found and saved, False otherwise.
        """
        cache_key = f"{artist} - {title}"
        track_id = f"{artist}|||{title}"
        
        # If the cache says we already found this song's art AND the file on disk
        # still belongs to this song, we can skip the download.
        if self.itunes_artwork_cache.get(cache_key) is True and self.last_artwork_track == track_id:
            return True
        
        # If cache says we previously couldn't find art for this song, don't retry.
        if self.itunes_artwork_cache.get(cache_key) is False:
            return False
        
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
                return False
            
            # Download the artwork
            if not self._download_itunes_artwork(art_url, f"{artist} - {title} [via {strategy_used}]"):
                self.itunes_artwork_cache[cache_key] = False
                return False
            
            self.itunes_artwork_cache[cache_key] = True
            self.last_artwork_track = track_id
            return True
            
        except Exception as e:
            print(f"iTunes artwork fallback error: {e}")
            self.itunes_artwork_cache[cache_key] = False
            return False
