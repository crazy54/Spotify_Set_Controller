#!/usr/bin/env python3
"""
Spotify Multi-Playlist Tool
Add a song to multiple playlists with one command

Setup:
1. Install dependencies: pip install spotipy
2. Create a Spotify app at https://developer.spotify.com/dashboard
3. Set redirect URI to http://localhost:8080 in your app settings
4. Create a config.json file with your credentials (see example below)
5. Run: python spot-fav.py setup (first time only)
6. Use: python spot-fav.py {SPOTIFY_SONG_URL}

config.json example (NOTE: YOU CAN CREATE THIS BY HAND OR BY USING THE PROMPTS ON THE COMMAND LINE! I SUGGEST USING THE COMMAND LINE PROMPTS TO ENSURE YOU DO NOT HAVE ISSUES!):
{
    "client_id": "your_spotify_client_id",
    "client_secret": "your_spotify_client_secret",
    "redirect_uri": "http://localhost:8080",
    "locked_playlists": [
        "My Super Important Mix - Do Not Touch",
        "spotify:playlist:another_locked_playlist_id"
    ],
    "genres": {
        "default": {
            "playlists": ["Favorites", "Daily Mix", "Workout"],
            "save_to_liked": true
        },
        "dubstep": {
            "playlists": ["Dubstep Bangers", "Electronic Favorites", "Bass Heavy"],
            "save_to_liked": true
        },
        "trance": {
            "playlists": ["Trance Classics", "Progressive Trance", "Uplifting"],
            "save_to_liked": false
        },
        "rock": {
            "playlists": ["Rock Hits", "Classic Rock"],
            "save_to_liked": true
        }
    }
}
"""

import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
import sys
import datetime
import os
import re
import qrcode
from collections import Counter

CONFIG_FILE = "config.json"
CACHE_FILE = ".cache"

def load_config():
    """Load configuration from config.json"""
    if not os.path.exists(CONFIG_FILE):
        print(f"❌ Config file '{CONFIG_FILE}' not found!")
        print("Create a config.json file with your Spotify app credentials.")
        print("See the comments at the top of this script for the format.")
        sys.exit(1)
    
    data = {}
    try:
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error decoding {CONFIG_FILE}: {e}", file=sys.stderr)
        print(f"   Please check the file for syntax errors. Backing up and creating a default config.", file=sys.stderr)
        # Optionally, backup the corrupted file and create a default one
        # For now, we'll exit to prevent further issues.
        sys.exit(1)
    except Exception as e: # Catch other potential file reading errors
        print(f"❌ An unexpected error occurred reading {CONFIG_FILE}: {e}", file=sys.stderr)
        sys.exit(1)

    # Ensure "locked_playlists" key exists and is a list
    if 'locked_playlists' not in data:
        data['locked_playlists'] = []
        # No need to save here, load_config is for loading.
        # If a save is desired upon first load with missing key, that's a different behavior.
    elif not isinstance(data['locked_playlists'], list):
        print(f"⚠️ Warning: 'locked_playlists' in {CONFIG_FILE} is not a list. Re-initializing as empty list.", file=sys.stderr)
        data['locked_playlists'] = []
        # A save could be triggered here if desired to correct the file immediately.

    return data

def setup_spotify_client(config):
    """Initialize Spotify client with OAuth"""
    scope = "playlist-modify-public playlist-modify-private playlist-read-private user-library-modify user-library-read"
    
    auth_manager = SpotifyOAuth(
        client_id=config['client_id'],
        client_secret=config['client_secret'],
        redirect_uri=config['redirect_uri'],
        scope=scope,
        cache_path=CACHE_FILE,
        open_browser=False  # Don't auto-open browser
    )
    
    return spotipy.Spotify(auth_manager=auth_manager)

def extract_track_id(url):
    """Extract track ID from Spotify URL"""
    # Handle different Spotify URL formats
    patterns = [
        r'https://open\.spotify\.com/track/([a-zA-Z0-9]+)',
        r'spotify:track:([a-zA-Z0-9]+)',
        r'https://spotify\.link/([a-zA-Z0-9]+)'  # Short links
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def get_user_playlists(sp):
    """Get all user playlists"""
    playlists = {}
    results = sp.current_user_playlists(limit=50)
    
    while results:
        for playlist in results['items']:
            if playlist['owner']['id'] == sp.current_user()['id']:  # Only user's own playlists
                playlists[playlist['name']] = playlist['id']
        
        if results['next']:
            results = sp.next(results)
        else:
            break
    
    return playlists

def extract_playlist_id(url_or_id):
    """Extract playlist ID from Spotify URL or ID"""
    patterns = [
        r'https://open\.spotify\.com/playlist/([a-zA-Z0-9]+)',
        r'spotify:playlist:([a-zA-Z0-9]+)',
        r'([a-zA-Z0-9]{22})' # Plain ID (typically 22 chars)
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            # For plain ID, it might be captured by the URL patterns if it's a substring
            # Ensure it's the correct group and potentially re-verify if it's a standalone ID
            if pattern == r'([a-zA-Z0-9]{22})' and len(url_or_id) == 22: # Likely a plain ID
                 return match.group(1)
            elif pattern != r'([a-zA-Z0-9]{22})': # One of the URL patterns
                 return match.group(1)

    # If it's exactly 22 chars and wasn't caught by specific URL patterns, assume it's an ID
    if len(url_or_id) == 22 and re.match(r'^[a-zA-Z0-9]+$', url_or_id):
        return url_or_id
        
    return None

def copy_playlist(sp, source_playlist_id_or_url, new_playlist_name):
    """Copies a playlist to the current user's account."""
    print("🔄 Starting playlist copy process...")

    playlist_id = extract_playlist_id(source_playlist_id_or_url)
    if not playlist_id:
        print(f"❌ Could not extract playlist ID from: {source_playlist_id_or_url}")
        return

    print(f"🔎 Fetching tracks from source playlist ID: {playlist_id}...")
    source_tracks = []
    try:
        results = sp.playlist_items(playlist_id)
        source_tracks.extend([item['track']['uri'] for item in results['items'] if item['track'] and item['track']['uri']])
        while results['next']:
            results = sp.next(results)
            source_tracks.extend([item['track']['uri'] for item in results['items'] if item['track'] and item['track']['uri']])
    except Exception as e:
        print(f"❌ Error fetching tracks from source playlist: {e}")
        return

    if not source_tracks:
        print("⚠️ Source playlist is empty or tracks could not be fetched.")
        # Optionally create an empty playlist anyway, or just return
        # For now, let's proceed to create an empty playlist if that's the case

    user_id = sp.me()['id']
    print(f"✨ Creating new playlist '{new_playlist_name}' for user {user_id}...")
    try:
        new_playlist = sp.user_playlist_create(user_id, new_playlist_name)
        new_playlist_id = new_playlist['id']
        print(f"✅ New playlist '{new_playlist_name}' created with ID: {new_playlist_id}")
    except Exception as e:
        print(f"❌ Error creating new playlist: {e}")
        return

    if not source_tracks:
        print(f"✅ Playlist '{new_playlist_name}' created successfully (it's empty as the source was empty).")
        return

    print(f"➕ Adding {len(source_tracks)} tracks to '{new_playlist_name}'...")
    tracks_added_count = 0
    # Spotify API limit: 100 tracks per add request
    for i in range(0, len(source_tracks), 100):
        batch = source_tracks[i:i + 100]
        try:
            sp.playlist_add_items(new_playlist_id, batch)
            tracks_added_count += len(batch)
            print(f"   Added batch of {len(batch)} tracks...")
        except Exception as e:
            print(f"❌ Error adding batch of tracks to new playlist: {e}")
            # Decide if to continue with other batches or stop
            # For now, let's report and continue if possible, but this might leave the playlist partially copied.
    
    print(f"\n🎉 Playlist '{new_playlist_name}' created and {tracks_added_count}/{len(source_tracks)} tracks copied successfully!")


def add_to_playlists(sp, track_id, playlist_ids, save_to_liked=False):
    """Add track to multiple playlists and optionally to Liked Songs"""
    results = []
    
    # Add to Liked Songs first if requested
    if save_to_liked:
        try:
            # add_to_liked_songs now returns True/False, internal print removed too
            if add_to_liked_songs(sp, track_id):
                results.append(("Liked Songs", True, None))
            else:
                # This case implies an exception occurred in add_to_liked_songs
                results.append(("Liked Songs", False, "Failed (exception in add_to_liked_songs)"))
        except Exception as e_liked: # Catching potential exception from add_to_liked_songs if not handled within
            results.append(("Liked Songs", False, str(e_liked)))

    # Add to playlists
    for playlist_name, playlist_id in playlist_ids:
        try:
            sp.playlist_add_items(playlist_id, [f"spotify:track:{track_id}"])
            results.append((playlist_name, True, None))
        except Exception as e:
            results.append((playlist_name, False, str(e)))
    
    return results

# is_playlist_locked should be defined before add_to_playlists or imported if it were in a different file.
# Assuming is_playlist_locked is already defined above this function in spotify_tool.py.

def add_to_playlists(sp, track_id, playlist_ids, save_to_liked=False, config=None, force=False): # Added config and force
    """Add track to multiple playlists and optionally to Liked Songs"""
    results = []
    
    # Add to Liked Songs first if requested
    if save_to_liked:
        try:
            if add_to_liked_songs(sp, track_id): # add_to_liked_songs is assumed to be refactored
                results.append(("Liked Songs", True, None))
            else:
                results.append(("Liked Songs", False, "Failed (exception in add_to_liked_songs)"))
        except Exception as e_liked: 
            results.append(("Liked Songs", False, str(e_liked)))
    
    # Add to playlists
    for playlist_name, playlist_id in playlist_ids:
        if config and not force and is_playlist_locked(config, playlist_id): # Check lock status
            results.append((playlist_name, False, "Playlist is locked"))
            continue # Skip to the next playlist

        try:
            sp.playlist_add_items(playlist_id, [f"spotify:track:{track_id}"])
            results.append((playlist_name, True, None))
        except Exception as e:
            results.append((playlist_name, False, str(e)))
    
    return results

def add_to_liked_songs(sp, track_id):
    """Add track to Liked Songs (saved tracks). Returns True if successful, False otherwise."""
    try:
        sp.current_user_saved_tracks_add([track_id])
        return True
    except Exception: # Simplified: any exception means failure for this context
        # The original had a print here. We remove it.
        # The calling function (add_to_playlists) will now create the error message.
        return False

def get_genre_config(config, genre=None):
    """Get configuration for specific genre or default"""
    # Support old config format
    if 'playlists' in config and 'genres' not in config:
        return {
            'playlists': config['playlists'],
            'save_to_liked': False
        }
    
    # New genre-based format
    if 'genres' not in config:
        print("❌ No 'genres' section found in config")
        sys.exit(1)
    
    target_genre = genre or 'default'
    
    if target_genre not in config['genres']:
        print(f"❌ Genre '{target_genre}' not found in config")
        print(f"Available genres: {', '.join(config['genres'].keys())}")
        sys.exit(1)
    
    return config['genres'][target_genre]

def get_track_details(sp, track_ids):
    """
    Fetches audio features and artist genres for a list of track IDs.

    :param sp: spotipy.Spotify client instance
    :param track_ids: A list of Spotify track IDs
    :return: A list of dictionaries, each containing track_id, audio_features, and artist_genres.
    """
    track_details_list = []
    if not track_ids:
        return track_details_list

    for track_id in track_ids:
        try:
            print(f"Fetching details for track ID: {track_id}...")

            # Fetch audio features
            audio_features_response = sp.audio_features(tracks=[track_id])
            # audio_features_response is a list, get the first element
            current_audio_features = audio_features_response[0] if audio_features_response and audio_features_response[0] else None

            if not current_audio_features:
                print(f"⚠️ Warning: Could not fetch audio features for track ID: {track_id}. Skipping audio features for this track.")
                # We can decide to skip the track entirely or proceed without audio features.
                # For now, let's store None for audio_features and proceed.
            
            # Fetch full track details for artist information
            track_data = sp.track(track_id)
            if not track_data:
                print(f"❌ Error: Could not fetch track data for ID: {track_id}. Skipping this track.")
                continue

            all_artist_genres = set()
            if 'artists' in track_data:
                for artist_summary in track_data['artists']:
                    artist_id = artist_summary.get('id')
                    if artist_id:
                        try:
                            artist_details = sp.artist(artist_id)
                            if artist_details and 'genres' in artist_details:
                                all_artist_genres.update(artist_details['genres'])
                        except Exception as e_artist:
                            print(f"❌ Error fetching genres for artist ID {artist_id} (track {track_id}): {e_artist}")
                    else:
                        print(f"⚠️ Warning: Artist ID missing for an artist in track {track_id}.")
            else:
                print(f"⚠️ Warning: No artists found in track data for {track_id}.")

            track_info = {
                'id': track_id,
                'audio_features': current_audio_features,
                'artist_genres': sorted(list(all_artist_genres)) # Store as sorted list
            }
            track_details_list.append(track_info)
            print(f"✅ Successfully fetched details for track ID: {track_id}")

        except Exception as e:
            print(f"❌ An error occurred while processing track ID {track_id}: {e}")
            # Optionally, decide if you want to add partial data or skip
            # For now, we skip the track if a major error occurs in the main try block
            continue
            
    return track_details_list

def get_user_top_artists_and_genres(sp, time_range='medium_term', limit=20):
    """
    Fetches the user's top artists and aggregates their genres.

    :param sp: spotipy.Spotify client instance
    :param time_range: 'short_term', 'medium_term', or 'long_term'
    :param limit: Number of top artists to fetch (1-50)
    :return: A tuple containing (list_of_artist_ids, set_of_seed_genres)
             Returns ([], set()) on error.
    """
    # Basic validation (Spotipy might also validate, but good to have)
    valid_time_ranges = ['short_term', 'medium_term', 'long_term']
    if time_range not in valid_time_ranges:
        print(f"Error: Invalid time_range '{time_range}'. Must be one of {valid_time_ranges}", file=sys.stderr)
        return ([], set())
    if not 1 <= limit <= 50:
        print(f"Error: Invalid limit '{limit}'. Must be between 1 and 50.", file=sys.stderr)
        return ([], set())

    artist_ids = []
    seed_genres = set()

    try:
        results = sp.current_user_top_artists(time_range=time_range, limit=limit)
        if results and results.get('items'):
            for artist in results['items']:
                if artist.get('id'):
                    artist_ids.append(artist['id'])
                if artist.get('genres'):
                    seed_genres.update(artist['genres'])
        else:
            print("Warning: No top artists found or unexpected API response.", file=sys.stderr)
            
    except spotipy.SpotifyException as e: # Catching specific Spotipy exceptions
        print(f"Spotify API error fetching top artists: {e}", file=sys.stderr)
        return ([], set())
    except Exception as e: # Catching other potential errors
        print(f"An unexpected error occurred fetching top artists: {e}", file=sys.stderr)
        return ([], set())
        
    return (artist_ids, seed_genres)

def get_genre_suggestions_from_recommendations(sp, current_artist_ids, current_genres_set, rec_limit=50, artists_per_genre=3):
    """
    Suggests new genres to the user based on recommendations derived from their top artists and genres.

    :param sp: spotipy.Spotify client instance
    :param current_artist_ids: List of user's top artist IDs.
    :param current_genres_set: Set of genres from user's top artists.
    :param rec_limit: Number of recommendations to fetch.
    :param artists_per_genre: How many example artists to list per suggested new genre.
    :return: Dictionary of suggested_new_genres {'genre_name': {'artists': [names], 'artist_ids': [ids]}}, or {} on error/no suggestions.
    """
    final_seed_artist_ids = []
    final_seed_genres = []

    # Prepare seeds for sp.recommendations (max 5 total)
    if current_artist_ids:
        final_seed_artist_ids = list(current_artist_ids)[:5] # Take up to 5 artist IDs

    if len(final_seed_artist_ids) < 5 and current_genres_set:
        num_genre_seeds_to_take = 5 - len(final_seed_artist_ids)
        # Convert set to list to slice, ensure genres are strings
        potential_genre_seeds = [str(g) for g in list(current_genres_set)]
        final_seed_genres = potential_genre_seeds[:num_genre_seeds_to_take]

    if not final_seed_artist_ids and not final_seed_genres:
        print("Error: No seed artists or genres provided for recommendations.", file=sys.stderr)
        return {}

    # Fetch Recommendations
    try:
        # Use None if lists are empty, as Spotipy expects
        recommendations = sp.recommendations(
            seed_artists=final_seed_artist_ids if final_seed_artist_ids else None,
            seed_genres=final_seed_genres if final_seed_genres else None,
            limit=rec_limit
        )
    except spotipy.SpotifyException as e:
        print(f"Spotify API error fetching recommendations: {e}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"An unexpected error occurred fetching recommendations: {e}", file=sys.stderr)
        return {}

    if not recommendations or not recommendations.get('tracks'):
        print("Warning: No tracks recommended by Spotify.", file=sys.stderr)
        return {}

    # Extract Artist IDs from Recommended Tracks
    recommended_artist_ids_set = set()
    for track in recommendations['tracks']:
        if track and track.get('artists'):
            for artist in track['artists']:
                if artist and artist.get('id'):
                    recommended_artist_ids_set.add(artist['id'])
    
    if not recommended_artist_ids_set:
        print("Warning: No artist IDs found in recommended tracks.", file=sys.stderr)
        return {}

    # Fetch Genres of Recommended Artists (in batches of 50 for sp.artists)
    suggested_new_genres = {}
    all_recommended_artist_ids_list = list(recommended_artist_ids_set)
    
    for i in range(0, len(all_recommended_artist_ids_list), 50):
        batch_artist_ids = all_recommended_artist_ids_list[i:i + 50]
        try:
            artists_details_batch = sp.artists(batch_artist_ids)
            if not artists_details_batch or not artists_details_batch.get('artists'):
                continue

            for rec_artist in artists_details_batch['artists']:
                if not rec_artist or not rec_artist.get('genres'):
                    continue
                
                artist_name = rec_artist.get('name', 'Unknown Artist')
                artist_id = rec_artist.get('id')

                for genre in rec_artist['genres']:
                    if genre not in current_genres_set: # It's a new genre
                        if genre not in suggested_new_genres:
                            suggested_new_genres[genre] = {'artists': [], 'artist_ids': []}
                        
                        # Add artist to this new genre if limit not reached
                        if len(suggested_new_genres[genre]['artists']) < artists_per_genre:
                            # Avoid duplicate artists per genre suggestion
                            if artist_id not in suggested_new_genres[genre]['artist_ids']:
                                suggested_new_genres[genre]['artists'].append(artist_name)
                                suggested_new_genres[genre]['artist_ids'].append(artist_id)
        
        except spotipy.SpotifyException as e:
            print(f"Spotify API error fetching details for recommended artists (batch starting {i}): {e}", file=sys.stderr)
            # Continue to try other batches if possible
        except Exception as e:
            print(f"Unexpected error fetching details for recommended artists (batch starting {i}): {e}", file=sys.stderr)

    # Sort the results by genre name
    sorted_suggested_new_genres = dict(sorted(suggested_new_genres.items()))
    
    return sorted_suggested_new_genres

def get_user_top_tracks_by_time_range(sp, time_range, limit=50):
    """
    Fetches the user's top tracks for a given time range.

    :param sp: spotipy.Spotify client instance
    :param time_range: 'short_term', 'medium_term', or 'long_term'
    :param limit: Number of top tracks to fetch (1-50)
    :return: A list of dictionaries, each containing track 'id', 'name', and 'artist'.
             Returns an empty list on error or if no tracks are found.
    """
    valid_time_ranges = ['short_term', 'medium_term', 'long_term']
    if time_range not in valid_time_ranges:
        print(f"Error: Invalid time_range '{time_range}'. Must be one of {valid_time_ranges}", file=sys.stderr)
        return []
    if not 1 <= limit <= 50:
        print(f"Error: Invalid limit '{limit}'. Must be between 1 and 50.", file=sys.stderr)
        return []

    top_tracks_data = []
    try:
        results = sp.current_user_top_tracks(time_range=time_range, limit=limit)
        if results and results.get('items'):
            for track in results['items']:
                if not track or not track.get('id'): # Skip if track data is missing or incomplete
                    continue
                
                track_id = track['id']
                track_name = track.get('name', 'Unknown Track')
                
                artist_name = "Unknown Artist"
                if track.get('artists') and len(track['artists']) > 0:
                    # Get the first artist's name
                    first_artist = track['artists'][0]
                    if first_artist and first_artist.get('name'):
                        artist_name = first_artist['name']
                
                top_tracks_data.append({
                    'id': track_id,
                    'name': track_name,
                    'artist': artist_name
                })
        else:
            print(f"Warning: No top tracks found for time range '{time_range}' or unexpected API response.", file=sys.stderr)

    except spotipy.SpotifyException as e:
        print(f"Spotify API error fetching top tracks: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"An unexpected error occurred fetching top tracks: {e}", file=sys.stderr)
        return []
        
    return top_tracks_data

def get_user_recently_played_tracks(sp, limit=50):
    """
    Fetches the user's recently played tracks.

    :param sp: spotipy.Spotify client instance
    :param limit: Number of recently played tracks to fetch (1-50)
    :return: A list of dictionaries, each containing track 'id', 'name', and 'artist'.
             Returns an empty list on error or if no tracks are found.
    """
    if not 1 <= limit <= 50:
        print(f"Error: Invalid limit '{limit}'. Must be between 1 and 50 for recently played.", file=sys.stderr)
        return []

    recent_tracks_data = []
    try:
        results = sp.current_user_recently_played(limit=limit)
        if results and results.get('items'):
            for item in results['items']:
                track = item.get('track')
                if not track or not track.get('id'): # Skip if track data is missing or incomplete
                    continue
                
                track_id = track['id']
                track_name = track.get('name', 'Unknown Track')
                
                artist_name = "Unknown Artist"
                if track.get('artists') and len(track['artists']) > 0:
                    first_artist = track['artists'][0]
                    if first_artist and first_artist.get('name'):
                        artist_name = first_artist['name']
                
                recent_tracks_data.append({
                    'id': track_id,
                    'name': track_name,
                    'artist': artist_name
                })
        else:
            print("Warning: No recently played tracks found or unexpected API response.", file=sys.stderr)

    except spotipy.SpotifyException as e:
        print(f"Spotify API error fetching recently played tracks: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"An unexpected error occurred fetching recently played tracks: {e}", file=sys.stderr)
        return []
        
    return recent_tracks_data

def find_old_favorites(sp, long_term_tracks, medium_term_tracks, short_term_tracks, recent_tracks, num_suggestions=20):
    """
    Identifies tracks that were popular in the long term but haven't appeared
    in medium-term, short-term, or recent listening.

    :param sp: spotipy.Spotify client instance (currently unused, for future potential use).
    :param long_term_tracks: List of track dicts {'id', 'name', 'artist'} from long-term listening.
    :param medium_term_tracks: List of track dicts from medium-term listening.
    :param short_term_tracks: List of track dicts from short-term listening.
    :param recent_tracks: List of track dicts from recently played.
    :param num_suggestions: The maximum number of old favorites to return.
    :return: A list of track dictionaries that are considered "old favorites".
    """
    # Extract IDs for efficient filtering
    medium_term_ids = {track['id'] for track in medium_term_tracks if track and 'id' in track}
    short_term_ids = {track['id'] for track in short_term_tracks if track and 'id' in track}
    recent_ids = {track['id'] for track in recent_tracks if track and 'id' in track}

    old_favorites_candidates = []

    for track in long_term_tracks:
        if not track or 'id' not in track: # Ensure track and its ID are valid
            continue
            
        track_id = track['id']
        if (track_id not in medium_term_ids and
            track_id not in short_term_ids and
            track_id not in recent_ids):
            old_favorites_candidates.append(track) # Add the whole track dictionary

    # Limit the number of suggestions
    if len(old_favorites_candidates) > num_suggestions:
        # For now, simple slicing. Random sampling could be an alternative.
        # e.g., import random; return random.sample(old_favorites_candidates, num_suggestions)
        return old_favorites_candidates[:num_suggestions]
    
    return old_favorites_candidates

# --- Music Key Conversion Utilities ---

PITCH_CLASS_MAP_SHARPS = {
    0: "C",
    1: "C♯", # or D♭
    2: "D",
    3: "D♯", # or E♭
    4: "E",
    5: "F",
    6: "F♯", # or G♭
    7: "G",
    8: "G♯", # or A♭
    9: "A",
    10: "A♯", # or B♭
    11: "B"
}

MODE_MAP = {
    0: "Minor",
    1: "Major"
}

# Camelot Wheel Mapping (Standard Notation -> Camelot Code)
# Using common enharmonics for broader compatibility if input varies slightly,
# but the primary generation from spotify_key_to_standard will use sharps.
STANDARD_TO_CAMELOT_MAP = {
    # Major Keys (B series)
    "C Major":    "8B",
    "G Major":    "9B",
    "D Major":    "10B",
    "A Major":    "11B",
    "E Major":    "12B",
    "B Major":    "1B",
    "F♯ Major":   "2B", "G♭ Major": "2B",
    "C♯ Major":   "3B", "D♭ Major": "3B",
    "G♯ Major":   "4B", "A♭ Major": "4B",
    "D♯ Major":   "5B", "E♭ Major": "5B",
    "A♯ Major":   "6B", "B♭ Major": "6B",
    "F Major":    "7B",

    # Minor Keys (A series)
    "A Minor":    "8A",
    "E Minor":    "9A",
    "B Minor":    "10A",
    "F♯ Minor":   "11A", "G♭ Minor": "11A", # F-sharp minor
    "C♯ Minor":   "12A", "D♭ Minor": "12A", # C-sharp minor
    "G♯ Minor":   "1A",  "A♭ Minor": "1A",  # G-sharp minor
    "D♯ Minor":   "2A",  "E♭ Minor": "2A",  # D-sharp minor
    "A♯ Minor":   "3A",  "B♭ Minor": "3A",  # A-sharp minor (often B-flat minor)
    "F Minor":    "4A",
    "C Minor":    "5A",
    "G Minor":    "6A",
    "D Minor":    "7A",
}

def spotify_key_to_standard(key_int, mode_int) -> str:
    """
    Converts Spotify's integer key and mode to standard musical notation.
    e.g., (0, 1) -> "C Major"
    """
    if key_int not in PITCH_CLASS_MAP_SHARPS or mode_int not in MODE_MAP:
        return "Unknown Key"
    
    note_name = PITCH_CLASS_MAP_SHARPS[key_int]
    mode_name = MODE_MAP[mode_int]
    
    return f"{note_name} {mode_name}"

def standard_to_camelot(standard_key_notation: str) -> str:
    """
    Converts standard musical key notation to its Camelot wheel code.
    e.g., "C Major" -> "8B"
    """
    if standard_key_notation == "Unknown Key":
        return "-"
        
    return STANDARD_TO_CAMELOT_MAP.get(standard_key_notation, "-")

def get_audio_features_for_playlist(sp, playlist_id_or_url):
    """
    Fetches all tracks from a playlist and their audio features (tempo, key, mode).

    :param sp: spotipy.Spotify client instance
    :param playlist_id_or_url: Spotify playlist ID or URL
    :return: A list of dictionaries, each containing track 'id', 'name', 'artist', 
             'tempo', 'key', and 'mode'. Returns an empty list on error.
    """
    playlist_id = extract_playlist_id(playlist_id_or_url)
    if not playlist_id:
        print(f"Error: Could not extract playlist ID from '{playlist_id_or_url}'.", file=sys.stderr)
        return []

    playlist_tracks_info = []
    try:
        print(f"Fetching tracks for playlist ID: {playlist_id}...", file=sys.stderr) # Progress for CLI
        results = sp.playlist_items(playlist_id)
        while results:
            for item in results.get('items', []):
                track = item.get('track')
                if track and track.get('id'):
                    track_id = track['id']
                    track_name = track.get('name', 'Unknown Track')
                    artist_name = "Unknown Artist"
                    if track.get('artists') and len(track['artists']) > 0:
                        first_artist = track['artists'][0]
                        if first_artist and first_artist.get('name'):
                            artist_name = first_artist['name']
                    playlist_tracks_info.append({'id': track_id, 'name': track_name, 'artist': artist_name})
            
            if results['next']:
                results = sp.next(results) # Potentially blocking, but this function is for CLI/backend
            else:
                results = None
    except spotipy.SpotifyException as e:
        print(f"Spotify API error fetching playlist items for {playlist_id}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"An unexpected error occurred fetching playlist items for {playlist_id}: {e}", file=sys.stderr)
        return []

    if not playlist_tracks_info:
        print(f"Warning: No tracks found in playlist {playlist_id}.", file=sys.stderr)
        return []
    
    print(f"Found {len(playlist_tracks_info)} tracks. Fetching audio features...", file=sys.stderr)

    all_track_ids = [track['id'] for track in playlist_tracks_info]
    tracks_with_features = []
    missing_features_count = 0

    for i in range(0, len(all_track_ids), 100): # Spotify API limit for audio_features is 100
        batch_ids = all_track_ids[i:i + 100]
        try:
            audio_features_results = sp.audio_features(tracks=batch_ids)
            
            # The audio_features_results list is in the same order as batch_ids.
            # Some items in audio_features_results can be None if features are unavailable.
            for idx, features in enumerate(audio_features_results):
                # Find the original track info. Since we processed in batches,
                # the current batch_ids[idx] corresponds to features.
                # The original track info can be found by matching this ID or by index if we kept track of batches.
                # For simplicity, let's find the track info from playlist_tracks_info using the ID.
                # This assumes track IDs are unique within the playlist_tracks_info list.
                
                # The index in the original playlist_tracks_info for the current feature set
                original_track_info_index = i + idx 
                track_info = playlist_tracks_info[original_track_info_index]

                if features:
                    tracks_with_features.append({
                        'id': track_info['id'],
                        'name': track_info['name'],
                        'artist': track_info['artist'],
                        'tempo': features.get('tempo'),
                        'key': features.get('key'),    # Integer: 0=C, 1=C♯/D♭, ..., 11=B
                        'mode': features.get('mode')   # Integer: 0=Minor, 1=Major
                    })
                else:
                    missing_features_count += 1
                    # print(f"Warning: Audio features not available for track ID: {track_info['id']}", file=sys.stderr)

        except spotipy.SpotifyException as e:
            print(f"Spotify API error fetching audio features for batch starting at index {i}: {e}", file=sys.stderr)
            # Continue to next batch if one fails, or decide to return []
        except Exception as e:
            print(f"Unexpected error fetching audio features for batch starting at index {i}: {e}", file=sys.stderr)

    if missing_features_count > 0:
        print(f"Warning: Audio features were not available for {missing_features_count} track(s).", file=sys.stderr)
        
    return tracks_with_features

def analyze_playlist_audio_summary(tracks_with_features):
    """
    Analyzes a list of tracks (with audio features) to provide a summary including
    BPM statistics, key distribution, and adds standard/Camelot keys to each track.

    :param tracks_with_features: List of track dicts, each expected to have 'id', 'name', 
                                 'artist', 'tempo', 'key', 'mode'.
    :return: A dictionary containing the audio summary.
    """
    if not tracks_with_features:
        return {
            'average_bpm': 0.0,
            'min_bpm': 0.0,
            'max_bpm': 0.0,
            'key_distribution': {},
            'processed_tracks': []
        }

    total_bpm = 0.0
    min_bpm = float('inf')
    max_bpm = float('-inf')
    num_tracks_with_tempo = 0
    key_counts = {}  # Using a simple dict for counts
    processed_tracks_list = []

    for track in tracks_with_features:
        # Ensure track is a dictionary and has expected keys before processing
        if not isinstance(track, dict):
            # Optionally log a warning or skip
            continue

        # BPM Stats
        tempo = track.get('tempo')
        if tempo is not None:
            try:
                tempo_float = float(tempo) # Ensure tempo is a number
                total_bpm += tempo_float
                min_bpm = min(min_bpm, tempo_float)
                max_bpm = max(max_bpm, tempo_float)
                num_tracks_with_tempo += 1
            except (ValueError, TypeError):
                # Tempo was not a valid number, skip for BPM stats
                pass # Optionally log a warning

        # Key Conversion and Counting
        key_int = track.get('key')
        mode_int = track.get('mode')
        
        standard_key = "Unknown Key"
        camelot_key = "-"

        if key_int is not None and mode_int is not None:
            try:
                # Ensure key_int and mode_int are integers if they come from JSON that might have them as strings
                key_int = int(key_int)
                mode_int = int(mode_int)
                standard_key = spotify_key_to_standard(key_int, mode_int)
                camelot_key = standard_to_camelot(standard_key)
            except (ValueError, TypeError):
                # Key/mode were not valid integers, keep default "Unknown Key" / "-"
                pass # Optionally log a warning

        # Add to the current track dictionary (create a copy to avoid modifying original input list items directly if they are reused)
        processed_track = track.copy() 
        processed_track['standard_key'] = standard_key
        processed_track['camelot_key'] = camelot_key
        
        # Increment count for standard_key
        if standard_key != "Unknown Key": # Only count valid keys
            key_counts[standard_key] = key_counts.get(standard_key, 0) + 1
        
        processed_tracks_list.append(processed_track)

    # Calculate Final Stats
    average_bpm = total_bpm / num_tracks_with_tempo if num_tracks_with_tempo > 0 else 0.0
    
    # If no tracks had tempo, min_bpm and max_bpm would still be inf/-inf. Reset them.
    if num_tracks_with_tempo == 0:
        min_bpm = 0.0
        max_bpm = 0.0
        
    # Sort key_distribution by frequency (descending)
    sorted_key_distribution = dict(sorted(key_counts.items(), key=lambda item: item[1], reverse=True))

    return {
        'average_bpm': round(average_bpm, 2),
        'min_bpm': round(min_bpm, 2) if min_bpm != float('inf') else 0.0, # Ensure no inf if list was empty but passed initial check
        'max_bpm': round(max_bpm, 2) if max_bpm != float('-inf') else 0.0, # Ensure no -inf
        'key_distribution': sorted_key_distribution,
        'processed_tracks': processed_tracks_list 
    }

def analyze_playlist_mood_genre(sp, playlist_id_or_url):
    """
    Analyzes a playlist to determine its dominant genres, average audio features,
    and select a few seed tracks.

    :param sp: spotipy.Spotify client instance
    :param playlist_id_or_url: Spotify playlist ID or URL
    :return: A dictionary containing top_genres, average_audio_features, and seed_tracks,
             or a predefined structure if analysis is not possible.
    """
    print(f"🔬 Starting analysis for playlist: {playlist_id_or_url}...")
    
    playlist_id = extract_playlist_id(playlist_id_or_url)
    if not playlist_id:
        print(f"❌ Could not extract playlist ID from: {playlist_id_or_url}")
        return {'top_genres': [], 'average_audio_features': {}, 'seed_tracks': []}

    # 1. Fetch all track IDs from the playlist
    source_track_items = []
    try:
        print(f"🔎 Fetching tracks from source playlist ID: {playlist_id}...")
        results = sp.playlist_items(playlist_id)
        source_track_items.extend(results['items'])
        while results['next']:
            results = sp.next(results)
            source_track_items.extend(results['items'])
    except Exception as e:
        print(f"❌ Error fetching tracks from source playlist {playlist_id}: {e}")
        return {'top_genres': [], 'average_audio_features': {}, 'seed_tracks': []}

    track_ids = []
    for item in source_track_items:
        if item and item.get('track') and item['track'].get('id'):
            track_ids.append(item['track']['id'])
    
    if not track_ids:
        print(f"⚠️ Playlist {playlist_id} is empty or no track IDs could be fetched.")
        return {'top_genres': [], 'average_audio_features': {}, 'seed_tracks': []}
    
    print(f"📊 Found {len(track_ids)} tracks in the playlist.")

    # 2. Get track details (audio features and artist genres)
    track_details_list = get_track_details(sp, track_ids)
    if not track_details_list:
        print(f"⚠️ Could not retrieve details for any tracks in playlist {playlist_id}.")
        return {'top_genres': [], 'average_audio_features': {}, 'seed_tracks': []}

    # 3. Aggregate genres and determine top N
    genre_counts = Counter()
    for track_detail in track_details_list:
        if track_detail.get('artist_genres'):
            genre_counts.update(track_detail['artist_genres'])
    
    top_n_genres = 5 # Define how many top genres to return
    top_genres = [genre for genre, count in genre_counts.most_common(top_n_genres)]
    print(f"🎶 Top {top_n_genres} genres: {top_genres}")

    # 4. Calculate average audio features
    features_to_average = [
        'danceability', 'energy', 'valence', 'instrumentalness', 
        'acousticness', 'speechiness', 'liveness', 'tempo'
    ]
    feature_sums = {feature: 0 for feature in features_to_average}
    feature_counts = {feature: 0 for feature in features_to_average}

    for track_detail in track_details_list:
        if track_detail.get('audio_features'):
            audio_features = track_detail['audio_features']
            for feature in features_to_average:
                if audio_features.get(feature) is not None: # Check if feature exists and is not None
                    feature_sums[feature] += audio_features[feature]
                    feature_counts[feature] += 1
    
    average_audio_features = {}
    for feature in features_to_average:
        if feature_counts[feature] > 0:
            average_audio_features[feature] = feature_sums[feature] / feature_counts[feature]
        else:
            average_audio_features[feature] = None # Or omit: del average_audio_features[feature]
    
    print(f"🎧 Average audio features: {average_audio_features}")

    # 5. Select seed tracks (first up to 5 valid track IDs)
    seed_tracks = track_ids[:5]
    print(f"🌱 Seed tracks: {seed_tracks}")

    analysis_result = {
        'top_genres': top_genres,
        'average_audio_features': average_audio_features,
        'seed_tracks': seed_tracks
    }
    
    print(f"✅ Analysis complete for playlist {playlist_id}.")
    return analysis_result

def get_recommendations(sp, analysis_results, limit=20):
    """
    Gets song recommendations based on playlist analysis.

    :param sp: spotipy.Spotify client instance
    :param analysis_results: Dictionary from analyze_playlist_mood_genre
    :param limit: Number of recommendations to fetch
    :return: A list of recommended track IDs, or an empty list if errors occur.
    """
    print("🧠 Generating recommendations based on analysis...")
    if not analysis_results:
        print("❌ Cannot get recommendations: analysis_results is empty.")
        return []

    seed_tracks_ids = analysis_results.get('seed_tracks', [])
    top_genres = analysis_results.get('top_genres', [])
    average_audio_features = analysis_results.get('average_audio_features', {})

    final_seed_track_uris = []
    final_seed_artist_ids = []
    final_seed_genre_list = []
    
    # Max 2-3 seed tracks
    # Convert IDs to URIs: spotify:track:TRACK_ID
    for track_id in seed_tracks_ids[:2]: # Let's start with up to 2 seed tracks
        final_seed_track_uris.append(f"spotify:track:{track_id}")

    # Fetch artist IDs for the seed tracks
    # This is a simplified approach; more robust would be to get all artists and let Spotify pick
    if final_seed_track_uris:
        print(f"🌱 Using seed tracks: {final_seed_track_uris}")
        for track_uri in final_seed_track_uris:
            track_id_for_artist_fetch = track_uri.split(':')[-1]
            try:
                track_info = sp.track(track_id_for_artist_fetch)
                if track_info and track_info['artists']:
                    # Using only the first artist as a seed
                    main_artist_id = track_info['artists'][0]['id']
                    if main_artist_id:
                         final_seed_artist_ids.append(main_artist_id)
            except Exception as e:
                print(f"⚠️ Error fetching artist for seed track {track_id_for_artist_fetch}: {e}")
    
    # Remove duplicate artist IDs, if any
    final_seed_artist_ids = sorted(list(set(final_seed_artist_ids)))
    if final_seed_artist_ids:
        print(f"🎤 Using seed artists: {final_seed_artist_ids}")

    # Prepare seed genres
    if top_genres:
        final_seed_genre_list = top_genres
        print(f"🎶 Using seed genres: {final_seed_genre_list}")
        
    # Spotify API limits total seeds (tracks + artists + genres) to 5.
    # Prioritize tracks, then artists, then genres.
    
    current_seeds_count = len(final_seed_track_uris)
    
    # Trim artist seeds if necessary
    available_slots_for_artists = 5 - current_seeds_count
    final_seed_artist_ids = final_seed_artist_ids[:available_slots_for_artists]
    current_seeds_count += len(final_seed_artist_ids)
    
    # Trim genre seeds if necessary
    available_slots_for_genres = 5 - current_seeds_count
    final_seed_genre_list = final_seed_genre_list[:available_slots_for_genres]
    # current_seeds_count += len(final_seed_genre_list) # Not strictly needed for count after this

    print(f"ℹ️ Final seeds for API: Tracks: {len(final_seed_track_uris)}, Artists: {len(final_seed_artist_ids)}, Genres: {len(final_seed_genre_list)}")

    # Prepare target features
    target_features_for_api = {}
    if average_audio_features:
        for key, value in average_audio_features.items():
            if value is not None: # Only include features that were successfully averaged
                target_features_for_api[f"target_{key}"] = value
        if target_features_for_api:
             print(f"🎯 Using target audio features: {target_features_for_api}")


    # Ensure at least one seed type is present
    if not final_seed_track_uris and not final_seed_artist_ids and not final_seed_genre_list:
        print("❌ No seed tracks, artists, or genres available to get recommendations. Aborting.")
        return []

    try:
        print("📞 Calling Spotify recommendations API...")
        recommendations = sp.recommendations(
            seed_artists=final_seed_artist_ids if final_seed_artist_ids else None, 
            seed_genres=final_seed_genre_list if final_seed_genre_list else None,
            seed_tracks=final_seed_track_uris if final_seed_track_uris else None,
            limit=limit,
            **target_features_for_api
        )
        
        recommended_track_ids = []
        if recommendations and recommendations['tracks']:
            for track in recommendations['tracks']:
                if track and track.get('id'):
                    recommended_track_ids.append(track['id'])
            print(f"✅ Found {len(recommended_track_ids)} recommended tracks.")
            return recommended_track_ids
        else:
            print("⚠️ No tracks returned from recommendations API.")
            return []
            
    except Exception as e:
        print(f"❌ Error calling Spotify recommendations API: {e}")
        # Check for specific API errors if needed, e.g., SpotipyHTTPError
        if hasattr(e, 'http_status') and e.http_status == 400:
             print("   Detail: Bad request. This might be due to invalid seed combination or feature values.")
        elif hasattr(e, 'http_status') and e.http_status == 429:
             print("   Detail: Rate limit exceeded. Please try again later.")
        return []

def determine_new_playlist_name(sp, source_playlist_id, new_name_provided=None):
    """
    Determines the name for a new playlist.
    If new_name_provided is given, it's used.
    Otherwise, it defaults to "Curated - [Original Name] - YYYY-MM-DD"
    or "My Curated Playlist - YYYY-MM-DD" if the original can't be fetched.
    """
    if new_name_provided:
        print(f"ℹ️ Using provided name for new playlist: {new_name_provided}")
        return new_name_provided

    date_str = datetime.date.today().isoformat()
    try:
        playlist_details = sp.playlist(source_playlist_id)
        original_name = playlist_details.get('name')
        if original_name:
            determined_name = f"Curated - {original_name} - {date_str}"
            print(f"ℹ️ Determined new playlist name: {determined_name}")
            return determined_name
        else:
            print(f"⚠️ Could not retrieve original playlist name for ID {source_playlist_id}. Defaulting name.")
            return f"My Curated Playlist - {date_str}"
    except Exception as e:
        print(f"❌ Error fetching details for source playlist {source_playlist_id}: {e}. Defaulting name.")
        return f"My Curated Playlist - {date_str}"

def create_empty_playlist(sp, playlist_name):
    """
    Creates a new empty playlist for the current user.

    :param sp: spotipy.Spotify client instance
    :param playlist_name: The name for the new playlist
    :return: The ID of the new playlist, or None if creation fails.
    """
    try:
        user_id = sp.me()['id']
        print(f"✨ Creating new playlist '{playlist_name}' for user {user_id}...")
        new_playlist = sp.user_playlist_create(user=user_id, name=playlist_name, public=True) # Defaulting to public
        new_playlist_id = new_playlist['id']
        print(f"✅ New playlist '{playlist_name}' created successfully with ID: {new_playlist_id}")
        return new_playlist_id
    except Exception as e:
        print(f"❌ Error creating new playlist '{playlist_name}': {e}")
        return None

def populate_playlist_with_tracks(sp, playlist_id, track_ids):
    """
    Populates a given playlist with a list of track IDs.

    :param sp: spotipy.Spotify client instance
    :param playlist_id: The ID of the playlist to add tracks to.
    :param track_ids: A list of Spotify track IDs.
    :return: The number of tracks successfully added.
    """
    if not track_ids:
        print("ℹ️ No tracks provided to add to the playlist.")
        return 0

    track_uris = [f"spotify:track:{track_id}" for track_id in track_ids if track_id]
    if not track_uris:
        print("ℹ️ No valid track URIs to add after filtering.")
        return 0
        
    print(f"➕ Adding {len(track_uris)} tracks to playlist ID: {playlist_id}...")
    tracks_added_count = 0
    batch_size = 100 # Spotify API limit per request

    for i in range(0, len(track_uris), batch_size):
        batch = track_uris[i:i + batch_size]
        try:
            sp.playlist_add_items(playlist_id, batch)
            tracks_added_count += len(batch)
            print(f"   Added batch of {len(batch)} tracks...")
        except Exception as e:
            print(f"❌ Error adding batch of tracks to playlist {playlist_id}: {e}")
            # Decide if to continue with other batches or stop. For now, report and continue.
            
    print(f"👍 Successfully added {tracks_added_count}/{len(track_uris)} tracks to playlist {playlist_id}.")
    return tracks_added_count

def curate_playlist_command(sp, source_playlist_id_or_url, new_playlist_name_arg=None, progress_callback=None):
    """
    Orchestrates the playlist curation process.
    
    1. Analyzes a source playlist.
    2. Gets recommendations based on the analysis.
    3. Creates a new playlist.
    4. Populates the new playlist with recommended tracks.
    :param progress_callback: Optional function to call with progress messages.
    """
    def _log(message):
        if progress_callback:
            progress_callback(message)
        else:
            print(message)

    _log(f"🚀 Starting playlist curation for source: {source_playlist_id_or_url}")

    # 1. Extract Source Playlist ID
    source_playlist_id = extract_playlist_id(source_playlist_id_or_url)
    if not source_playlist_id:
        _log(f"❌ Critical: Could not extract a valid playlist ID from '{source_playlist_id_or_url}'. Aborting curation.")
        return False # Indicate failure

    # 2. Analyze Source Playlist
    _log(f"\n🔄 Step 1/5: Analyzing source playlist (ID: {source_playlist_id})...")
    # Pass the callback down if sub-functions also support it, or handle their prints here.
    # For now, assuming sub-functions print directly or their prints are acceptable for CLI.
    # If get_recommendations, etc. are also to use callback, they'd need modification.
    analysis_results = analyze_playlist_mood_genre(sp, source_playlist_id) 
    if not analysis_results or (not analysis_results.get('seed_tracks') and not analysis_results.get('top_genres') and not analysis_results.get('average_audio_features')):
        _log(f"❌ Critical: Analysis of playlist ID {source_playlist_id} failed or returned insufficient data. Aborting curation.")
        return False
    _log("✅ Analysis complete.")

    # 3. Get Recommendations
    _log(f"\n🔄 Step 2/5: Getting recommendations...")
    recommended_track_ids = get_recommendations(sp, analysis_results, limit=20) 
    if not recommended_track_ids:
        _log("❌ Critical: No recommendations returned. Aborting curation.")
        return False
    _log(f"✅ Got {len(recommended_track_ids)} recommendations.")

    # 4. Determine New Playlist Name
    _log(f"\n🔄 Step 3/5: Determining new playlist name...")
    determined_playlist_name = determine_new_playlist_name(sp, source_playlist_id, new_playlist_name_arg)
    _log(f"✅ New playlist will be named: '{determined_playlist_name}'.")

    # 5. Create New Playlist
    _log(f"\n🔄 Step 4/5: Creating new playlist '{determined_playlist_name}'...")
    new_created_playlist_id = create_empty_playlist(sp, determined_playlist_name)
    if not new_created_playlist_id:
        _log(f"❌ Critical: Failed to create the new playlist '{determined_playlist_name}'. Aborting curation.")
        return False
    _log(f"✅ New playlist created with ID: {new_created_playlist_id}.")

    # 6. Populate New Playlist
    _log(f"\n🔄 Step 5/5: Populating playlist '{determined_playlist_name}' with recommended tracks...")
    num_tracks_added = populate_playlist_with_tracks(sp, new_created_playlist_id, recommended_track_ids)
    
    # 7. Final Success Message
    new_playlist_url = f"https://open.spotify.com/playlist/{new_created_playlist_id}"
    _log("\n🎉🎉🎉 Playlist Curation Complete! 🎉🎉🎉")
    _log(f"✨ New playlist named '{determined_playlist_name}' is ready!")
    _log(f"   🆔 ID: {new_created_playlist_id}")
    _log(f"   🔗 URL: {new_playlist_url}")
    _log(f"   🎶 Contains {num_tracks_added} recommended track(s).")
    _log("\nEnjoy your new curated mix! 🎧")
    return True # Indicate success

def setup_command():
    """Setup command - authenticate and show available playlists"""
    config = load_config()
    
    scope = "playlist-modify-public playlist-modify-private playlist-read-private user-library-modify user-library-read"
    auth_manager = SpotifyOAuth(
        client_id=config['client_id'],
        client_secret=config['client_secret'],
        redirect_uri=config['redirect_uri'],
        scope=scope,
        cache_path=CACHE_FILE,
        open_browser=False
    )
    
    # Check if we already have a token
    token_info = auth_manager.get_cached_token()
    if not token_info:
        # Get the authorization URL
        auth_url = auth_manager.get_authorize_url()
        print("🔗 Please open this URL in your browser to authorize the app:")
        print(f"\n{auth_url}\n")
        
        # Get the authorization code from user
        auth_code = input("📋 Paste the authorization code from the redirect URL: ").strip()
        
        # Exchange code for token
        token_info = auth_manager.get_access_token(auth_code)
    
    sp = spotipy.Spotify(auth_manager=auth_manager)
    
    # This will trigger the OAuth flow
    user = sp.current_user()
    print(f"✅ Successfully authenticated as: {user['display_name']}")
    
    print("\n📋 Your playlists:")
    playlists = get_user_playlists(sp)
    for name in sorted(playlists.keys()):
        print(f"   • {name}")
    
    print("\n🎵 Note: 'Liked Songs' is available but doesn't appear in playlists")
    
    if 'genres' in config:
        print(f"\n🎸 Available genres in config:")
        for genre in config['genres'].keys():
            print(f"   • {genre}")
    
    print(f"\n💡 Update your {CONFIG_FILE} file with the playlist names and genres you want to use.")

def find_playlist_ids(sp, playlist_names):
    """Find playlist IDs from names"""
    user_playlists = get_user_playlists(sp)
    playlist_ids = []
    not_found = []
    
    for name in playlist_names:
        if name in user_playlists:
            playlist_ids.append((name, user_playlists[name]))
        else:
            not_found.append(name)
    
    return playlist_ids, not_found

def get_playlist_url_by_name(sp, playlist_name):
    """Gets and prints the Spotify URL for a playlist by its name."""
    print(f"🔍 Searching for playlist: '{playlist_name}'...")
    user_playlists = get_user_playlists(sp) # Returns dict of {name: id}

    exact_match_id = None
    case_insensitive_matches = {} # Store as name: id for potential multiple matches

    # First pass: Check for exact case-sensitive match
    if playlist_name in user_playlists:
        exact_match_id = user_playlists[playlist_name]
        print(f"✅ Found exact match: '{playlist_name}'")
    else:
        # Second pass: Check for case-insensitive matches
        for name, pid in user_playlists.items():
            if name.lower() == playlist_name.lower():
                case_insensitive_matches[name] = pid
        
        if len(case_insensitive_matches) == 1:
            first_match_name = list(case_insensitive_matches.keys())[0]
            exact_match_id = case_insensitive_matches[first_match_name]
            print(f"✅ Found case-insensitive match: '{first_match_name}' (searched for '{playlist_name}')")
        elif len(case_insensitive_matches) > 1:
            print(f"⚠️ Multiple case-insensitive matches found for '{playlist_name}':")
            # Get the keys (playlist names) from the dictionary
            matched_names = list(case_insensitive_matches.keys())
            # Sort these names alphabetically
            sorted_matched_names = sorted(matched_names) 
            
            for name in sorted_matched_names: # Print sorted names for clarity
                print(f"   - {name}")
            
            # Select the first name from the *sorted* list
            first_match_name = sorted_matched_names[0] 
            exact_match_id = case_insensitive_matches[first_match_name] # Get the ID using this name
            
            print(f"⚠️  Returning the first one from the alphabetically sorted list: '{first_match_name}'. Consider using a more specific name.")
            # No exact_match_id = None here, we proceed with the first one

    if exact_match_id:
        try:
            playlist_details = sp.playlist(exact_match_id)
            playlist_url = playlist_details['external_urls']['spotify']
            print(f"🔗 Spotify URL for '{playlist_details['name']}': {playlist_url}")
            return playlist_url
        except Exception as e:
            print(f"❌ Error fetching details for playlist ID {exact_match_id}: {e}")
            return None
    else:
        if not case_insensitive_matches: # Only print if no matches at all were found
            print(f"❌ Playlist '{playlist_name}' not found.")
        # If multiple matches were found but we decided not to pick one, exact_match_id would be None
        # The message for multiple matches is already printed above.
        return None

def generate_playlist_qr_code(sp, playlist_name_or_url, output_filename="playlist_qr.png"):
    """Generates a QR code for a playlist URL and saves it to a file."""
    playlist_url = None

    # Check if it's a URL or a name
    if playlist_name_or_url.startswith("http") or playlist_name_or_url.startswith("spotify:playlist:"):
        playlist_url = playlist_name_or_url
        print(f"ℹ️ Using provided URL: {playlist_url}")
    else:
        print(f"ℹ️ '{playlist_name_or_url}' is a name, attempting to find URL...")
        playlist_url = get_playlist_url_by_name(sp, playlist_name_or_url) # This function already prints messages

    if not playlist_url:
        # get_playlist_url_by_name already prints "not found" or error messages
        # Add a general message here if it was a name and resolution failed.
        if not (playlist_name_or_url.startswith("http") or playlist_name_or_url.startswith("spotify:playlist:")):
             print(f"❌ Could not generate QR code because playlist URL for '{playlist_name_or_url}' could not be determined.")
        # If it was a URL but somehow became None (e.g. future validation), that's an issue.
        # For now, get_playlist_url_by_name handles its own "not found".
        return None

    try:
        print(f"⚙️ Generating QR code for URL: {playlist_url}...")
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(playlist_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img.save(output_filename)
        print(f"✅ QR code for playlist URL '{playlist_url}' saved to '{output_filename}'")
        return output_filename
    except Exception as e:
        print(f"❌ Failed to generate or save QR code: {e}")
        return None

def save_config(config):
    """Save configuration back to config.json"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
    print(f"✅ Configuration saved to {CONFIG_FILE}")

def is_playlist_locked(config, playlist_id: str) -> bool:
    """
    Checks if a playlist ID is in the locked_playlists list in the config.
    """
    locked_playlists = config.get('locked_playlists', [])
    if not isinstance(locked_playlists, list): # Should be handled by load_config, but defensive check
        return False 
    for locked_item in locked_playlists:
        if isinstance(locked_item, dict) and locked_item.get('id') == playlist_id:
            return True
    return False

def lock_playlist(config, playlist_id_to_lock: str, playlist_name_to_lock: str) -> bool:
    """
    Adds a playlist to the 'locked_playlists' list in the config.
    Returns True if successfully locked, False if already locked or error.
    """
    if not isinstance(config.get('locked_playlists'), list):
        # This case should ideally be prevented by load_config ensuring locked_playlists is a list
        print("Error: 'locked_playlists' key is missing or not a list in config. Cannot lock playlist.", file=sys.stderr)
        # Initialize it to prevent further errors if we proceed, though this is unexpected.
        config['locked_playlists'] = [] 
        # Depending on strictness, could return False here.
        # For now, we'll allow it to proceed and add to the newly created list.

    if is_playlist_locked(config, playlist_id_to_lock):
        print(f"ℹ️ Playlist '{playlist_name_to_lock}' (ID: {playlist_id_to_lock}) is already locked.")
        return False
    
    lock_entry = {'id': playlist_id_to_lock, 'name': playlist_name_to_lock}
    config['locked_playlists'].append(lock_entry)
    print(f"🔒 Playlist '{playlist_name_to_lock}' (ID: {playlist_id_to_lock}) has been locked.")
    # Note: save_config(config) must be called separately by the caller.
    return True

def unlock_playlist(config, playlist_id_to_unlock: str) -> bool:
    """
    Removes a playlist from the 'locked_playlists' list in the config.
    Returns True if successfully unlocked, False if not found or error.
    """
    locked_playlists = config.get('locked_playlists', [])
    if not isinstance(locked_playlists, list):
        print("Error: 'locked_playlists' key is missing or not a list in config. Cannot unlock playlist.", file=sys.stderr)
        return False

    original_length = len(locked_playlists)
    playlist_name_unlocked = None

    # Rebuild the list excluding the one to unlock
    # This is safer than modifying while iterating
    new_locked_list = []
    found_and_removed = False
    for item in locked_playlists:
        if isinstance(item, dict) and item.get('id') == playlist_id_to_unlock:
            playlist_name_unlocked = item.get('name', playlist_id_to_unlock) # Use name for message if available
            found_and_removed = True
            # Don't add it to new_locked_list
        else:
            new_locked_list.append(item)
            
    if found_and_removed:
        config['locked_playlists'] = new_locked_list
        print(f"🔓 Playlist '{playlist_name_unlocked}' (ID: {playlist_id_to_unlock}) has been unlocked.")
        # Note: save_config(config) must be called separately by the caller.
        return True
    else:
        print(f"ℹ️ Playlist ID '{playlist_id_to_unlock}' not found in locked list or already unlocked.")
        return False

def playlist_setup_command():
    """Interactive playlist group setup"""
    config = load_config()
    
    # Ensure genres section exists
    if 'genres' not in config:
        config['genres'] = {}
    
    print("🎸 Creating new playlist group...")
    
    # Get genre name
    while True:
        genre = input("Enter genre name (e.g., trance, dubstep, rock): ").strip().lower()
        if not genre:
            print("Genre name cannot be empty. Please try again.")
            continue
        if genre in config['genres']:
            overwrite = input(f"Genre '{genre}' already exists. Overwrite? (y/n): ").strip().lower()
            if overwrite != 'y':
                continue
        break
    
    # Get playlist names
    while True:
        playlist_input = input("Enter playlist names (comma-separated): ").strip()
        if not playlist_input:
            print("Please enter at least one playlist name.")
            continue
        
        # Clean up playlist names
        playlists = [name.strip() for name in playlist_input.split(',') if name.strip()]
        if not playlists:
            print("Please enter valid playlist names.")
            continue
        break
    
    # Ask about Liked Songs
    while True:
        liked_input = input("Save to Liked Songs for this genre? (y/n): ").strip().lower()
        if liked_input in ['y', 'yes']:
            save_to_liked = True
            break
        elif liked_input in ['n', 'no']:
            save_to_liked = False
            break
        else:
            print("Please enter 'y' or 'n'.")
    
    # Create the new genre config
    config['genres'][genre] = {
        "playlists": playlists,
        "save_to_liked": save_to_liked
    }
    
    # Save config
    save_config(config)
    
    print(f"\n🎉 Created genre '{genre}' with:")
    print(f"   📋 Playlists: {', '.join(playlists)}")
    print(f"   ❤️  Liked Songs: {'Yes' if save_to_liked else 'No'}")
    print(f"\n💡 Usage: ./spotify_tool.py <song_url> --genre {genre}")

def list_playlists_command(search_term=None):
    """List all user playlists with optional search"""
    config = load_config()
    sp = setup_spotify_client(config)
    
    try:
        user_playlists = get_user_playlists(sp)
    except Exception as e:
        print(f"❌ Error fetching playlists: {e}")
        return
    
    if not user_playlists:
        print("📋 No playlists found.")
        return
    
    # Filter playlists if search term provided
    if search_term:
        search_lower = search_term.lower()
        filtered_playlists = {
            name: pid for name, pid in user_playlists.items() 
            if search_lower in name.lower()
        }
        print(f"🔍 Playlists matching '{search_term}':")
        playlists_to_show = filtered_playlists
    else:
        print("📋 All your playlists:")
        playlists_to_show = user_playlists
    
    if not playlists_to_show:
        print(f"   No playlists found matching '{search_term}'")
        return
    
    # Sort and display
    sorted_names = sorted(playlists_to_show.keys())
    for i, name in enumerate(sorted_names, 1):
        print(f"   {i:2d}. {name}")
    
    print(f"\n📊 Total: {len(playlists_to_show)} playlists")
    
    # Show current config genres if no search
    if not search_term and 'genres' in config:
        print(f"\n🎸 Configured genres:")
        for genre, genre_config in config['genres'].items():
            playlist_count = len(genre_config.get('playlists', []))
            liked_icon = "❤️ " if genre_config.get('save_to_liked', False) else ""
            print(f"   • {genre}: {playlist_count} playlists {liked_icon}")

def show_genre_config():
    """Show current genre configuration"""
    config = load_config()
    
    if 'genres' not in config or not config['genres']:
        print("📋 No genres configured yet.")
        print("💡 Use --playlist-setup to create your first genre group.")
        return
    
    print("🎸 Current genre configuration:")
    print()
    
    for genre, genre_config in config['genres'].items():
        print(f"📂 {genre.upper()}:")
        print(f"   📋 Playlists: {', '.join(genre_config.get('playlists', []))}")
        print(f"   ❤️  Liked Songs: {'Yes' if genre_config.get('save_to_liked', False) else 'No'}")
        print()
    
    print("💡 Usage examples:")
    for genre in config['genres'].keys():
        print(f"   ./spotify_tool.py <song_url> --genre {genre}")

def parse_arguments():
    """Parse command line arguments"""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  ./spotify_tool.py setup                                    # First time setup")
        print("  ./spotify_tool.py --playlist-setup                        # Create new genre group")
        print("  ./spotify_tool.py --list-playlists [-lp]                  # List all playlists")
        print("  ./spotify_tool.py --list-playlists 'search' [-lp]         # Search playlists")
        print("  ./spotify_tool.py --show-config [-sc]                     # Show genre config")
        print("  ./spotify_tool.py --copy-playlist <source_url_or_id> <new_name> [-cp] # Copy a playlist")
        print("  ./spotify_tool.py --curate-playlist <source_playlist_id_or_url> [--new-name <playlist_name>] [-cpL] # Curate a playlist")
        print("  ./spotify_tool.py --get-playlist-url <playlist_name> [-gpu] # Get playlist URL by name")
        print("  ./spotify_tool.py --generate-qr <playlist_name_or_url> [output.png] [-qr] # Generate QR code for playlist")
        print("  ./spotify_tool.py --suggest-genres [--time-range <short_term|medium_term|long_term>] [-sg] # Suggest new genres based on your listening habits")
        print("  ./spotify_tool.py --old-favorites [--suggestions <num>] [-of] # Find old favorite tracks you haven't listened to recently")
        print("  ./spotify_tool.py --bpm-key-analysis <playlist_url_or_id> [-bka] # Analyze BPM & Key for a playlist")
        print("  ./spotify_tool.py lock <playlist_url_or_id>                 # Lock a playlist to prevent modifications by some features")
        print("  ./spotify_tool.py unlock <playlist_url_or_id>               # Unlock a previously locked playlist")
        print("  ./spotify_tool.py list-locked                               # List all locked playlists")
        print("  ./spotify_tool.py tui                                       # Launch Textual User Interface")
        print("  ./spotify_tool.py <song_url1> [song_url2...]                # Add song(s) using default genre")
        print("  ./spotify_tool.py <song_url1> [song_url2...] --genre <name> [-g] # Add song(s) using specific genre")
        sys.exit(1)
    
    # Handle special commands
    if sys.argv[1] == "setup":
        return {"command": "setup"}

    if sys.argv[1] == "tui":
        return {"command": "tui"}

    if sys.argv[1] == "lock":
        if len(sys.argv) < 3:
            print("❌ lock command requires a <playlist_id_or_url>")
            sys.exit(1)
        return {"command": "lock_playlist", "playlist_input": sys.argv[2]}

    if sys.argv[1] == "unlock":
        if len(sys.argv) < 3:
            print("❌ unlock command requires a <playlist_id_or_url>")
            sys.exit(1)
        return {"command": "unlock_playlist", "playlist_input": sys.argv[2]}

    if sys.argv[1] == "list-locked":
        return {"command": "list_locked_playlists"}

    if sys.argv[1] in ["--bpm-key-analysis", "-bka"]:
        if len(sys.argv) < 3:
            print("❌ bpm-key-analysis command requires a <playlist_id_or_url>")
            sys.exit(1)
        # Check for unexpected additional arguments
        if len(sys.argv) > 3:
            print(f"❌ Unexpected additional arguments for {sys.argv[1]}: {' '.join(sys.argv[3:])}")
            sys.exit(1)
        return {"command": "bpm_key_analysis", "playlist_input": sys.argv[2]}

    if sys.argv[1] in ["--suggest-genres", "-sg"]:
        time_range = "medium_term" # Default
        idx = 2
        if len(sys.argv) > idx :
            if sys.argv[idx] in ["--time-range", "-tr"]:
                idx += 1
                if len(sys.argv) > idx:
                    time_range = sys.argv[idx]
                    idx += 1
                    if time_range not in ['short_term', 'medium_term', 'long_term']:
                        print(f"❌ Invalid value for --time-range: {time_range}. Must be 'short_term', 'medium_term', or 'long_term'.")
                        sys.exit(1)
                else:
                    print("❌ --time-range flag requires a value (short_term, medium_term, long_term)")
                    sys.exit(1)
            elif sys.argv[idx].startswith("-"): # Some other flag
                 print(f"❌ Unknown option for --suggest-genres: {sys.argv[idx]}")
                 sys.exit(1)
            else: # Positional argument, not allowed here if not a value for a known flag
                 print(f"❌ Unexpected argument for --suggest-genres: {sys.argv[idx]}. Did you mean --time-range?")
                 sys.exit(1)
        return {"command": "suggest_genres", "time_range": time_range}

    if sys.argv[1] in ["--old-favorites", "-of"]:
        num_suggestions = 20 # Default
        idx = 2
        if len(sys.argv) > idx:
            if sys.argv[idx] in ["--suggestions", "-n", "-N"]:
                idx += 1
                if len(sys.argv) > idx:
                    try:
                        num_suggestions = int(sys.argv[idx])
                        idx += 1
                        if num_suggestions <= 0:
                            print("❌ Number of suggestions must be a positive integer.")
                            sys.exit(1)
                    except ValueError:
                        print(f"❌ Invalid value for --suggestions: '{sys.argv[idx]}' is not a valid integer.")
                        sys.exit(1)
                else:
                    print("❌ --suggestions flag requires a number.")
                    sys.exit(1)
            elif sys.argv[idx].startswith("-"): # Some other flag
                 print(f"❌ Unknown option for --old-favorites: {sys.argv[idx]}")
                 sys.exit(1)
            else: # Positional argument
                 print(f"❌ Unexpected argument for --old-favorites: {sys.argv[idx]}. Did you mean --suggestions?")
                 sys.exit(1)
        
        # Check for any remaining unexpected arguments
        if idx < len(sys.argv):
            print(f"❌ Unexpected additional arguments for --old-favorites: {' '.join(sys.argv[idx:])}")
            sys.exit(1)

        return {"command": "old_favorites", "suggestions": num_suggestions}
    
    if sys.argv[1] in ["--playlist-setup", "-ps"]:
        return {"command": "playlist_setup"}

    if sys.argv[1] in ["--copy-playlist", "-cp"]:
        if len(sys.argv) < 4:
            print("❌ --copy-playlist requires <source_playlist_id_or_url> and <new_playlist_name>")
            sys.exit(1)
        return {"command": "copy_playlist", "source": sys.argv[2], "name": sys.argv[3]}

    if sys.argv[1] in ["--curate-playlist", "-cpL"]:
        if len(sys.argv) < 3:
            print("❌ --curate-playlist requires <source_playlist_id_or_url>")
            sys.exit(1)
        
        source_playlist_id_or_url = sys.argv[2]
        new_name = None
        
        # Check for optional --new-name argument
        if len(sys.argv) > 3:
            if sys.argv[3] == "--new-name":
                if len(sys.argv) > 4:
                    new_name = sys.argv[4]
                else:
                    print("❌ --new-name flag requires a playlist name")
                    sys.exit(1)
            # If there's a 4th argument and it's not --new-name, it's an error,
            # unless we decide to allow other optional args in the future.
            # For now, any extra arg not part of --new-name is unexpected.
            elif sys.argv[3].startswith("-"): # some other flag, not allowed here
                 print(f"❌ Unknown option after source playlist for --curate-playlist: {sys.argv[3]}")
                 sys.exit(1)
            # If it's not a flag, and not --new-name, it's an error as we expect --new-name or nothing
            else:
                 print(f"❌ Unexpected argument after source playlist for --curate-playlist: {sys.argv[3]}. Did you mean --new-name?")
                 sys.exit(1)
        
        return {
            "command": "curate_playlist",
            "source_playlist_id_or_url": source_playlist_id_or_url,
            "new_name": new_name
        }

    if sys.argv[1] in ["--get-playlist-url", "-gpu"]:
        if len(sys.argv) < 3:
            print("❌ --get-playlist-url requires <playlist_name>")
            sys.exit(1)
        return {"command": "get_playlist_url", "playlist_name": sys.argv[2]}

    if sys.argv[1] in ["--generate-qr", "-qr"]:
        if len(sys.argv) < 3:
            print("❌ --generate-qr requires <playlist_name_or_url> [output_filename.png]")
            sys.exit(1)
        playlist_name_or_url = sys.argv[2]
        output_filename = sys.argv[3] if len(sys.argv) > 3 else "playlist_qr.png"
        # Basic validation for output filename extension
        if not output_filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            print(f"⚠️ Warning: Output filename '{output_filename}' does not have a common image extension. Saving as PNG by default if not specified, or as provided.")
            if len(sys.argv) <= 3 : # if user didn't provide a name, stick to default
                 output_filename="playlist_qr.png"
        return {"command": "generate_qr", "playlist_name_or_url": playlist_name_or_url, "output_filename": output_filename}

    if sys.argv[1] in ["--list-playlists", "-lp"]:
        search_term = sys.argv[2] if len(sys.argv) > 2 else None 
        # Check if the optional search term is actually another flag
        if search_term and search_term.startswith("-"):
            search_term = None # It's a flag, not a search term
        return {"command": "list_playlists", "search": search_term}
    
    if sys.argv[1] in ["--show-config", "-sc"]:
        return {"command": "show_config"}
    
    # Handle song URL with optional genre
    # Handle song URL(s) with optional genre
    # All other commands start with a flag or are 'setup'
    
    song_urls = []
    genre = None
    idx = 1 # Start parsing from the first argument after script name
    
    # Collect song URLs
    while idx < len(sys.argv) and not sys.argv[idx].startswith("-"):
        song_urls.append(sys.argv[idx])
        idx += 1
        
    if not song_urls:
        # This case should ideally be caught by the len(sys.argv) < 2 check,
        # or if a flag is given as the first arg, it's handled by special commands.
        # If somehow it reaches here (e.g. script_name --genre rock), it's an error.
        print("❌ No song URLs provided.")
        # Re-print usage or a more specific error
        print("Usage: ./spotify_tool.py <song_url1> [song_url2...] [--genre <name>]")
        sys.exit(1)

    # Check for genre argument after song URLs
    if idx < len(sys.argv): # If there are more arguments
        if sys.argv[idx] in ['--genre', '-g']:
            if idx + 1 < len(sys.argv):
                genre = sys.argv[idx+1]
                idx += 2 # Consumed --genre and its value
            else:
                print("❌ --genre flag requires a genre name")
                sys.exit(1)
        # If there are more args after URLs but not a genre flag, it's an error
        elif idx < len(sys.argv):
             print(f"❌ Unknown argument after song URLs: {sys.argv[idx]}")
             sys.exit(1)

    return {"command": "add_song", "urls": song_urls, "genre": genre}

def main():
    args = parse_arguments()
    command = args.get("command")

    if command == "setup":
        setup_command()
    elif command == "playlist_setup":
        playlist_setup_command()
    elif command == "list_playlists":
        list_playlists_command(args.get("search"))
    elif command == "show_config":
        show_genre_config()
    elif command == "copy_playlist":
        source_playlist_id_or_url = args.get("source")
        new_playlist_name = args.get("name")
        config = load_config() # Needed for sp client
        sp = setup_spotify_client(config)
        copy_playlist(sp, source_playlist_id_or_url, new_playlist_name)
    elif command == "curate_playlist":
        source_playlist_input = args.get("source_playlist_id_or_url")
        new_name_input = args.get("new_name")
        # Initialize Spotify client here as it's needed by the command
        config = load_config()
        sp = setup_spotify_client(config)
        curate_playlist_command(sp, source_playlist_input, new_name_input)
    elif command == "suggest_genres":
        time_range_arg = args.get("time_range", "medium_term")
        config = load_config()
        sp = setup_spotify_client(config)

        print(f"🔍 Fetching your top artists and genres for time range: {time_range_arg}...")
        artist_ids, current_genres = get_user_top_artists_and_genres(sp, time_range=time_range_arg)

        if not artist_ids or not current_genres:
            print(f"Could not retrieve your top artists/genres for the selected time range: '{time_range_arg}'.")
            print("This might happen if you haven't listened to enough music recently for this time range,")
            print("or if there's an issue with your Spotify authentication (try running './spotify_tool.py setup').")
            sys.exit(1)
        
        print(f"Found {len(artist_ids)} top artists and {len(current_genres)} current genres.")
        print("🎧 Getting genre recommendations based on your listening habits...")
        
        suggested_genres_data = get_genre_suggestions_from_recommendations(sp, artist_ids, current_genres)
        
        if not suggested_genres_data:
            print("\n🤷 No new genre suggestions found at this time. Try a different time range or listen to more varied music!")
        else:
            print("\n✨ Suggested New Genres ✨")
            print("--------------------------")
            for genre_name, data in suggested_genres_data.items():
                print(f"\n🎶 Genre: {genre_name}")
                if data.get('artists'):
                    print("  🎤 Example Artists:")
                    for artist_name in data['artists']:
                        print(f"    - {artist_name}")
                else:
                    print("  (No specific example artists found for this genre suggestion)")
            print("--------------------------")
            print("\n💡 Tip: Use these suggestions to explore new music or create new genre groups with '--playlist-setup'.")

    elif command == "old_favorites":
        num_suggestions_arg = args.get("suggestions", 20)
        config = load_config()
        sp = setup_spotify_client(config)

        print(" nostalgIA: Searching for those golden oldies you might have forgotten...")
        print("--------------------------------------------------------------------")
        print("🎧 Fetching your top tracks (long term)...")
        long_term_tracks = get_user_top_tracks_by_time_range(sp, time_range='long_term', limit=50)
        if not long_term_tracks:
            print("❌ Could not retrieve your long-term top tracks. Cannot find old favorites without this data.")
            sys.exit(1)
        print(f"Found {len(long_term_tracks)} long-term top tracks.")

        print("\n🎧 Fetching your top tracks (medium term)...")
        medium_term_tracks = get_user_top_tracks_by_time_range(sp, time_range='medium_term', limit=50)
        print(f"Found {len(medium_term_tracks)} medium-term top tracks.")

        print("\n🎧 Fetching your top tracks (short term)...")
        short_term_tracks = get_user_top_tracks_by_time_range(sp, time_range='short_term', limit=50)
        print(f"Found {len(short_term_tracks)} short-term top tracks.")

        print("\n🎧 Fetching your recently played tracks...")
        recent_tracks = get_user_recently_played_tracks(sp, limit=50)
        print(f"Found {len(recent_tracks)} recently played tracks.")
        
        print("\n🔍 Analyzing your listening history to find forgotten gems...")
        old_favorites = find_old_favorites(
            sp, 
            long_term_tracks, 
            medium_term_tracks, 
            short_term_tracks, 
            recent_tracks, 
            num_suggestions=num_suggestions_arg
        )
        
        if not old_favorites:
            print("\n🤷 No forgotten old favorites found based on the current criteria.")
            print("   This could mean your long-term favorites are still in your regular rotation!")
        else:
            print("\n✨ Rediscover These Old Favorites! ✨")
            print("------------------------------------")
            for i, track in enumerate(old_favorites, 1):
                print(f"{i:2d}. {track['name']} - {track['artist']}")
            print("------------------------------------")
            print(f"\n💡 Found {len(old_favorites)} tracks you might enjoy revisiting.")

    elif command == "lock_playlist":
        playlist_input_arg = args.get("playlist_input")
        config = load_config()
        sp = setup_spotify_client(config)
        
        playlist_id = extract_playlist_id(playlist_input_arg)
        if not playlist_id:
            print(f"❌ Could not extract a valid playlist ID from '{playlist_input_arg}'.")
            sys.exit(1)
            
        try:
            playlist_details = sp.playlist(playlist_id)
            playlist_name = playlist_details.get('name', playlist_id) # Default to ID if name not found
        except spotipy.SpotifyException as e:
            print(f"❌ Error fetching playlist details for ID '{playlist_id}': {e}")
            print("   Please ensure the playlist ID or URL is correct and you have access to it.")
            sys.exit(1)
        except Exception as e:
            print(f"❌ An unexpected error occurred while fetching playlist details: {e}")
            sys.exit(1)

        if lock_playlist(config, playlist_id, playlist_name):
            save_config(config)
        # lock_playlist already prints success/failure/already locked messages.

    elif command == "unlock_playlist":
        playlist_input_arg = args.get("playlist_input")
        config = load_config()
        # sp = setup_spotify_client(config) # Not strictly needed for unlock by ID if not verifying name
        
        playlist_id = extract_playlist_id(playlist_input_arg)
        if not playlist_id:
            # Try to see if the input itself is a direct ID that was in the locked list (if it was a name)
            # This path is less likely if extract_playlist_id is robust.
            # For now, we rely on extract_playlist_id. If it fails, the input is likely not a valid ID/URL.
            print(f"❌ Could not extract a valid playlist ID from '{playlist_input_arg}'.")
            sys.exit(1)

        if unlock_playlist(config, playlist_id):
            save_config(config)
        # unlock_playlist already prints success/failure/not found messages.
            
    elif command == "list_locked_playlists":
        config = load_config()
        locked_playlists_list = config.get('locked_playlists', [])
        
        if not locked_playlists_list:
            print("ℹ️ No playlists are currently locked.")
        else:
            print("🔒 Locked Playlists:")
            print("-------------------")
            for idx, item in enumerate(locked_playlists_list, 1):
                if isinstance(item, dict):
                    name = item.get('name', 'N/A')
                    pid = item.get('id', 'N/A')
                    print(f"{idx:2d}. {name} (ID: {pid})")
                else: # Should not happen with current locking logic
                    print(f"{idx:2d}. Invalid entry: {item}") 
            print("-------------------")
            
    elif command == "bpm_key_analysis":
        playlist_input_arg = args.get("playlist_input")
        config = load_config()
        sp = setup_spotify_client(config)

        playlist_id = extract_playlist_id(playlist_input_arg)
        if not playlist_id:
            print(f"❌ Invalid playlist URL or ID: '{playlist_input_arg}'")
            sys.exit(1)
        
        try:
            playlist_details = sp.playlist(playlist_id, fields="name") # Just need name for title
            playlist_title = playlist_details.get('name', playlist_id)
        except Exception as e:
            print(f"Could not fetch playlist name for ID {playlist_id}: {e}")
            playlist_title = playlist_id # Default to ID if name fetch fails

        print(f"\n📊 Fetching audio features for playlist: '{playlist_title}' (this may take a moment)...")
        tracks_with_features = get_audio_features_for_playlist(sp, playlist_id)

        if not tracks_with_features:
            print("❌ Could not retrieve audio features or the playlist is empty.")
            sys.exit(1)
        
        analysis_summary = analyze_playlist_audio_summary(tracks_with_features)

        print("\n--- Playlist BPM & Key Analysis ---")
        print(f"Playlist: {playlist_title}")
        print(f"  Average BPM: {analysis_summary['average_bpm']:.2f}")
        print(f"  Min BPM: {analysis_summary['min_bpm']:.2f}")
        print(f"  Max BPM: {analysis_summary['max_bpm']:.2f}")
        
        print("\n  Key Distribution:")
        if analysis_summary['key_distribution']:
            for key, count in analysis_summary['key_distribution'].items():
                print(f"    - {key:<12}: {count} track(s)")
        else:
            print("    - No key information found for tracks in this playlist.")
        
        print("\n--- Track Details ---")
        header = f"{'No.':<4} | {'Track Name':<35.35} | {'Artist':<25.25} | {'BPM':<6} | {'Key':<12} | {'Camelot':<7}"
        print(header)
        print("-" * len(header))
        
        if analysis_summary['processed_tracks']:
            for idx, track in enumerate(analysis_summary['processed_tracks'], 1):
                bpm_display = f"{track.get('tempo', 0.0):.1f}" if track.get('tempo') is not None else "-"
                key_display = track.get('standard_key', '-')
                camelot_display = track.get('camelot_key', '-')
                
                # Ensure all parts are strings for formatting
                print(f"{idx:<4} | {str(track.get('name', 'N/A')):<35.35} | {str(track.get('artist', 'N/A')):<25.25} | {bpm_display:<6} | {key_display:<12} | {camelot_display:<7}")
        else:
            print("  No track details to display.")
        print("-" * len(header))

    elif command == "tui":
        try:
            from spotify_tui import SpotifyTUI
            app = SpotifyTUI()
            app.run()
            print("Exited TUI.")
        except ImportError:
            print("❌ Textual library not found or TUI could not be imported.")
            print("   Please ensure 'textual' is installed: pip install textual")
        except Exception as e:
            print(f"❌ An error occurred while running the TUI: {e}")
            
    elif command == "get_playlist_url":
        playlist_name = args.get("playlist_name")
        config = load_config() # Needed for sp client
        sp = setup_spotify_client(config)
        get_playlist_url_by_name(sp, playlist_name)
    elif command == "generate_qr":
        playlist_name_or_url = args.get("playlist_name_or_url")
        output_filename = args.get("output_filename")
        config = load_config() # Needed for sp client
        sp = setup_spotify_client(config)
        generate_playlist_qr_code(sp, playlist_name_or_url, output_filename)
    elif command == "add_song":
        song_urls = args.get("urls", []) # Default to empty list
        genre = args.get("genre")
        
        if not song_urls: # Should be caught by parse_arguments, but as a safeguard
            print("❌ No song URLs provided to add.")
            sys.exit(1)

        config = load_config()
        sp = setup_spotify_client(config) # Initialize Spotify client
        
        total_songs = len(song_urls)
        songs_processed_successfully = 0

        for i, song_url in enumerate(song_urls):
            print(f"\nProcessing song {i+1}/{total_songs}: {song_url}")
            track_id = extract_track_id(song_url)
            if not track_id:
                print(f"❌ Could not extract track ID from URL: {song_url}")
                if "spotify.link/" in song_url: # Check specifically for short links
                     print(f"ℹ️ Note: Spotify short links (spotify.link/) might need to be resolved to a full track URL first if direct extraction fails.")
                continue # Skip to the next song

            print(f"🎵 Attempting to add track: {track_id}")

            # Get genre-specific or default playlist configuration
            genre_config_details = get_genre_config(config, genre) 
            playlist_names_to_add = genre_config_details.get('playlists', [])
            save_to_liked = genre_config_details.get('save_to_liked', False)

            # Find playlist IDs for the names from the config
            target_playlist_ids, not_found_playlists = find_playlist_ids(sp, playlist_names_to_add)

            if not_found_playlists:
                print(f"⚠️ The following playlists from your config were not found on your Spotify account and will be skipped for this song: {', '.join(not_found_playlists)}")
            
            if not target_playlist_ids and not save_to_liked:
                print(f"No valid playlists found to add song {track_id} to, and not saving to Liked Songs. Skipping this song.")
                continue
            
            print(f"👍 Adding {track_id} to {len(target_playlist_ids)} playlist(s) and Liked Songs is set to: {'Yes' if save_to_liked else 'No'}")
            # add_to_playlists returns a list of tuples: (playlist_name, success_status, error_message)
            results = add_to_playlists(sp, track_id, target_playlist_ids, save_to_liked)
            
            # Check if all operations for this track were successful
            # For simplicity, we can count successful additions.
            # A more robust check might ensure all intended operations succeeded.
            # Iterate through results to print them for CLI mode
            # Pass config to add_to_playlists
            results = add_to_playlists(sp, track_id, target_playlist_ids, save_to_liked, config=config) # Pass config
            
            song_had_at_least_one_success = False
            for name, success, error_msg in results:
                if success:
                    print(f"✅ Added to: {name}")
                    song_had_at_least_one_success = True
                else:
                    print(f"❌ Failed to add to {name}: {error_msg if error_msg else 'Failed'}") # Ensure error_msg is printed
            
            if song_had_at_least_one_success:
                songs_processed_successfully += 1

        print(f"\n🎉 All tasks complete! {songs_processed_successfully}/{total_songs} song(s) processed with at least one successful addition.")
    else:
        # This case should ideally be handled by parse_arguments exiting if the command is invalid
        print(f"❌ Error: Unknown command '{command}'.")
        sys.exit(1)

# Make sure this is the VERY END of your script:
# if __name__ == "__main__":
#     main()

if __name__ == "__main__":
    main()