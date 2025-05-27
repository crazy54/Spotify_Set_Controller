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

config.json example:
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
import os
import re
import qrcode

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
        print("  ./spotify_tool.py --get-playlist-url <playlist_name> [-gpu] # Get playlist URL by name")
        print("  ./spotify_tool.py --generate-qr <playlist_name_or_url> [output.png] [-qr] # Generate QR code for playlist")
        print("  ./spotify_tool.py <song_url>                              # Add using default")
        print("  ./spotify_tool.py <song_url> --genre <name> [-g]          # Add using genre")
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
    # Ensure this is not a special command before treating as song_url
    if sys.argv[1].startswith("-"):
        print(f"❌ Unknown command or missing song URL: {sys.argv[1]}")
        # Consider re-printing usage here or part of it
        sys.exit(1)
        
    song_url = sys.argv[1]
    genre = None
    
    # Check for genre argument
    if len(sys.argv) > 2:
        if sys.argv[2] in ['--genre', '-g']:
            if len(sys.argv) > 3:
                genre = sys.argv[3]
            else:
                print("❌ --genre flag requires a genre name")
                sys.exit(1)
    
    return {"command": "add_song", "url": song_url, "genre": genre}

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
        song_url = args.get("url")
        genre = args.get("genre")
        
        config = load_config()
        sp = setup_spotify_client(config) # Initialize Spotify client
        
        track_id = extract_track_id(song_url)
        if not track_id:
            print(f"❌ Could not extract track ID from URL: {song_url}")
            if "spotify.link/" in song_url: # Check specifically for short links
                 print(f"ℹ️ Note: Spotify short links (spotify.link/) might need to be resolved to a full track URL first if direct extraction fails.")
            sys.exit(1)

        print(f"🎵 Attempting to add track: {track_id}")

        # Get genre-specific or default playlist configuration
        genre_config_details = get_genre_config(config, genre) # Renamed to avoid conflict
        playlist_names_to_add = genre_config_details.get('playlists', [])
        save_to_liked = genre_config_details.get('save_to_liked', False)

        # Find playlist IDs for the names from the config
        target_playlist_ids, not_found_playlists = find_playlist_ids(sp, playlist_names_to_add)

        if not_found_playlists:
            print(f"⚠️ The following playlists from your config were not found on your Spotify account and will be skipped: {', '.join(not_found_playlists)}")
        
        if not target_playlist_ids and not save_to_liked:
            print("No valid playlists found to add the song to, and not saving to Liked Songs. Exiting.")
            sys.exit(0)
        
        print(f"👍 Adding to {len(target_playlist_ids)} playlist(s) and Liked Songs is set to: {'Yes' if save_to_liked else 'No'}")
        add_to_playlists(sp, track_id, target_playlist_ids, save_to_liked)
        print("\n🎉 All tasks complete!")
    else:
        # This case should ideally be handled by parse_arguments exiting if the command is invalid
        print(f"❌ Error: Unknown command '{command}'.")
        sys.exit(1)

# Make sure this is the VERY END of your script:
# if __name__ == "__main__":
#     main()

if __name__ == "__main__":
    main()