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
    
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

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
        if add_to_liked_songs(sp, track_id):
            print(f"✅ Added to: Liked Songs")
            results.append(("Liked Songs", True, None))
        else:
            results.append(("Liked Songs", False, "Failed to save"))
    
    # Add to playlists
    for playlist_name, playlist_id in playlist_ids:
        try:
            sp.playlist_add_items(playlist_id, [f"spotify:track:{track_id}"])
            results.append((playlist_name, True, None))
            print(f"✅ Added to: {playlist_name}")
        except Exception as e:
            results.append((playlist_name, False, str(e)))
            print(f"❌ Failed to add to {playlist_name}: {e}")
    
    return results

def add_to_liked_songs(sp, track_id):
    """Add track to Liked Songs (saved tracks)"""
    try:
        sp.current_user_saved_tracks_add([track_id])
        return True
    except Exception as e:
        print(f"❌ Failed to add to Liked Songs: {e}")
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

def curate_playlist_command(sp, source_playlist_id_or_url, new_playlist_name_arg=None):
    """
    Orchestrates the playlist curation process.
    
    1. Analyzes a source playlist.
    2. Gets recommendations based on the analysis.
    3. Creates a new playlist.
    4. Populates the new playlist with recommended tracks.
    """
    print(f"🚀 Starting playlist curation for source: {source_playlist_id_or_url}")

    # 1. Extract Source Playlist ID
    source_playlist_id = extract_playlist_id(source_playlist_id_or_url)
    if not source_playlist_id:
        print(f"❌ Critical: Could not extract a valid playlist ID from '{source_playlist_id_or_url}'. Aborting curation.")
        return

    # 2. Analyze Source Playlist
    print(f"\n tahap 1/5: Analyzing source playlist (ID: {source_playlist_id})...")
    analysis_results = analyze_playlist_mood_genre(sp, source_playlist_id)
    if not analysis_results or (not analysis_results.get('seed_tracks') and not analysis_results.get('top_genres') and not analysis_results.get('average_audio_features')):
        print(f"❌ Critical: Analysis of playlist ID {source_playlist_id} failed or returned insufficient data (no seeds/genres/features). Aborting curation.")
        return
    print("✅ Analysis complete.")

    # 3. Get Recommendations
    print(f"\n tahap 2/5: Getting recommendations...")
    # Using a default limit of 20 for now, can be made configurable
    recommended_track_ids = get_recommendations(sp, analysis_results, limit=20) 
    if not recommended_track_ids:
        print("❌ Critical: No recommendations returned. Aborting curation.")
        return
    print(f"✅ Got {len(recommended_track_ids)} recommendations.")

    # 4. Determine New Playlist Name
    print(f"\n tahap 3/5: Determining new playlist name...")
    determined_playlist_name = determine_new_playlist_name(sp, source_playlist_id, new_playlist_name_arg)
    print(f"✅ New playlist will be named: '{determined_playlist_name}'.")

    # 5. Create New Playlist
    print(f"\n tahap 4/5: Creating new playlist '{determined_playlist_name}'...")
    new_created_playlist_id = create_empty_playlist(sp, determined_playlist_name)
    if not new_created_playlist_id:
        print(f"❌ Critical: Failed to create the new playlist '{determined_playlist_name}'. Aborting curation.")
        return
    print(f"✅ New playlist created with ID: {new_created_playlist_id}.")

    # 6. Populate New Playlist
    print(f"\n tahap 5/5: Populating playlist '{determined_playlist_name}' with recommended tracks...")
    num_tracks_added = populate_playlist_with_tracks(sp, new_created_playlist_id, recommended_track_ids)
    
    # 7. Print Final Success Message
    new_playlist_url = f"https://open.spotify.com/playlist/{new_created_playlist_id}"
    print("\n🎉🎉🎉 Playlist Curation Complete! 🎉🎉🎉")
    print(f"✨ New playlist named '{determined_playlist_name}' is ready!")
    print(f"   🆔 ID: {new_created_playlist_id}")
    print(f"   🔗 URL: {new_playlist_url}")
    print(f"   🎶 Contains {num_tracks_added} recommended track(s).")
    print("\nEnjoy your new curated mix! 🎧")

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
        print("  ./spotify_tool.py <song_url1> [song_url2...]                # Add song(s) using default genre")
        print("  ./spotify_tool.py <song_url1> [song_url2...] --genre <name> [-g] # Add song(s) using specific genre")
        sys.exit(1)
    
    # Handle special commands
    if sys.argv[1] == "setup":
        return {"command": "setup"}
    
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
            if any(res[1] for res in results): # If at least one add operation was successful
                songs_processed_successfully +=1

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
