# 🎧 The Spotify Set Controller
## Created by SanitizeR

**Take absolute command over your Spotify playlists and genres.**

---

## ⚡ Overview

**The Set Controller** is a command-line utility designed for the digital maestro. It allows you to define and organize your Spotify playlists into thematic "genre groups," automatically link new music to your Liked Songs, and manage your playlists with powerful new tools. No more fragmented libraries or lost tracks – this tool ensures your audio landscape is precisely curated and under your control.

Think of it as your personal cybernetic DJ assistant, ensuring every beat falls into its designated quadrant.

## ✨ Features

* **Genre Group Creation:** Define custom genre categories (e.g., `trance`, `downtempo`, `synthwave`) to house related playlists.
* **Automated Playlist Assignment:** Easily create multiple playlists within each genre group.
* **Liked Songs Integration:** Optionally configure the tool to automatically add new songs for a specific genre to your Spotify Liked Songs, keeping your collection streamlined.
* **Simple Usage:** Integrate new tracks into your organized system with a single command.

### 🎉 New Features!

*   **Copy Playlist**: Allows copying an existing Spotify playlist (yours or someone else's that you have access to) to a new playlist under your account. Perfect for duplicating curated lists or making your own version of a friend's playlist.
*   **Get Playlist URL**: Fetches and displays the Spotify URL for one of your playlists by its name. Useful for quickly sharing a link to your favorite mixes.
*   **Generate Playlist QR Code**: Creates a QR code image for a given playlist name or URL. Share your playlists visually and easily!

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository (or download the script directly)
git clone https://github.com/crazy54/the-set-controller.git
cd the-set-controller

# Install dependencies using requirements.txt
pip install -r requirements.txt
```
Note: Ensure you have Python 3 installed. The `requirements.txt` file lists all necessary libraries, including `spotipy`, `qrcode`, and `Pillow`.

### 2. Spotify API Setup (One-Time)
The Set Controller needs access to your Spotify account to manage playlists. You'll need to set up a Spotify Developer Application:

1. Go to the Spotify Developer Dashboard.
2. Log in with your Spotify account.
3. Click "Create an app".
4. Fill in the details (App Name: The Set Controller, Description: Playlist Management Tool).
5. After creation, click "Edit Settings" for your new app.
6. Add a "Redirect URI": `http://localhost:8080` (This should match the `redirect_uri` in your `config.json`).
7. Copy your Client ID and Client Secret.
8. Create a `config.json` file in the root of the project directory (see the example in `spotify_tool.py` or below in section 5). Populate it with your `client_id`, `client_secret`, and `redirect_uri`.

### 3. Initial Authentication & Configuration
Before using most features, you need to authenticate with Spotify. The script also supports interactive setup for playlist groups (genres).

*   **Authenticate (First time only for most operations):**
    Run the setup command. This will guide you through the authentication process if you haven't authenticated before.
    ```bash
    python spotify_tool.py setup
    ```
    You'll be prompted to open a URL in your browser and paste back the authorization code.

*   **Interactively Set Up Playlist Groups (Genres):**
    ```bash
    python spotify_tool.py --playlist-setup 
    # or python spotify_tool.py -ps
    ```
    Follow the interactive prompts:
    ```
    🎸 Creating new playlist group...
    Enter genre name (e.g., trance, dubstep, rock): trance
    Enter playlist names (comma-separated): bubdub, tranceface, derpstop, glitchmatrix
    Save to Liked Songs for this genre? (y/n): y

    ✅ Configuration saved to config.json
    🎉 Created genre 'trance' with:
    📋 Playlists: bubdub, tranceface, derpstop, glitchmatrix
    ❤️  Liked Songs: Yes
    ```
    This will update your `config.json` file.

### 4. Usage
Once configured, use The Set Controller with the following commands. Remember to use `./spotify_tool.py` if you've made it executable, or `python spotify_tool.py` otherwise.

*   **Add one or more songs to genre playlists:**
    To add songs using the **default genre** configured in your `config.json`:
    ```bash
    python spotify_tool.py <song_url1> [song_url2...]
    # Example (single song):
    python spotify_tool.py https://open.spotify.com/track/YOUR_TRACK_ID_1
    # Example (multiple songs):
    python spotify_tool.py https://open.spotify.com/track/YOUR_TRACK_ID_1 https://open.spotify.com/track/YOUR_TRACK_ID_2
    ```
    To add songs using a **specific genre**:
    ```bash
    python spotify_tool.py <song_url1> [song_url2...] --genre <your_genre_name>
    # Alias for --genre: -g
    # Example (single song, specific genre):
    python spotify_tool.py https://open.spotify.com/track/YOUR_TRACK_ID --genre trance
    # Example (multiple songs, specific genre):
    python spotify_tool.py https://open.spotify.com/track/TRACK_ID_A https://open.spotify.com/track/TRACK_ID_B -g rock
    ```
    This adds the specified song(s) to all playlists in the chosen genre (or default genre if `--genre` is omitted) and to Liked Songs if configured for that genre.

*   **Copy a playlist:**
    ```bash
    python spotify_tool.py --copy-playlist <source_playlist_url_or_id> <new_playlist_name>
    # Alias: -cp
    # Example:
    python spotify_tool.py -cp spotify:playlist:37i9dQZF1DXcBWIGoYBM5M "My Copied Mix"
    ```

*   **Get a playlist's URL by its name:**
    ```bash
    python spotify_tool.py --get-playlist-url "<playlist_name>"
    # Alias: -gpu
    # Example (use quotes if the name has spaces):
    python spotify_tool.py -gpu "My Awesome Playlist"
    ```

*   **Generate a QR code for a playlist:**
    ```bash
    python spotify_tool.py --generate-qr <playlist_name_or_url> [output_filename.png]
    # Alias: -qr
    # Example (using a playlist name):
    python spotify_tool.py -qr "My Awesome Playlist" my_playlist_qr.png
    # Example (using a playlist URL, default filename 'playlist_qr.png'):
    python spotify_tool.py -qr https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
    ```

*   **List your playlists (with optional search):**
    ```bash
    python spotify_tool.py --list-playlists ["search_term"]
    # Alias: -lp
    # Example:
    python spotify_tool.py -lp "Chill"
    ```

*   **Show current genre configuration from `config.json`:**
    ```bash
    python spotify_tool.py --show-config
    # Alias: -sc
    ```

### 🎬 Command Examples

This section provides detailed examples of how to use each command, along with sample outputs.

#### 1. Setup Authentication
This command initiates the authentication process with Spotify, allowing the tool to access your account. You'll only need to do this once, or if your credentials expire.

*   **Command:**
    ```bash
    ./spotify_tool.py setup
    ```
*   **Output/Flow:**
    ```text
    🔗 Please open this URL in your browser to authorize the app:
    https://accounts.spotify.com/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http%3A%2F%2Flocalhost%3A8080&scope=playlist-modify-public+playlist-modify-private+playlist-read-private+user-library-modify+user-library-read

    📋 Paste the authorization code from the redirect URL: <user_pastes_code_here>
    ✅ Successfully authenticated as: YourSpotifyUsername
    
    📋 Your playlists:
       • Playlist A
       • Playlist B
       • ...
    
    🎵 Note: 'Liked Songs' is available but doesn't appear in playlists
    
    🎸 Available genres in config:
       • default
       • trance
       • ...
    
    💡 Update your config.json file with the playlist names and genres you want to use.
    ```

#### 2. Interactive Playlist Group (Genre) Setup
Use this to create or update genre groups and their associated playlists in your `config.json`.

*   **Command:**
    ```bash
    ./spotify_tool.py --playlist-setup
    # or ./spotify_tool.py -ps 
    ```
*   **Output/Flow:**
    ```text
    🎸 Creating new playlist group...
    Enter genre name (e.g., trance, dubstep, rock): synthwave
    Enter playlist names (comma-separated): Synthwave Classics, Retrowave Gems, Night Drive
    Save to Liked Songs for this genre? (y/n): y
    ✅ Configuration saved to config.json
    
    🎉 Created genre 'synthwave' with:
       📋 Playlists: Synthwave Classics, Retrowave Gems, Night Drive
       ❤️  Liked Songs: Yes
    
    💡 Usage: ./spotify_tool.py <song_url> --genre synthwave
    ```

#### 3. List User's Playlists
View all your playlists or search for specific ones by name.

*   **Command (List All):**
    ```bash
    ./spotify_tool.py --list-playlists
    # or ./spotify_tool.py -lp
    ```
*   **Sample Output (List All):**
    ```text
    📋 All your playlists:
        1. Chill Vibes
        2. Coding Focus
        3. My Awesome Mix
        4. Synthwave Classics
        5. Workout Hits
    📊 Total: 5 playlists
    
    🎸 Configured genres:
       • default: 2 playlists ❤️ 
       • synthwave: 3 playlists ❤️ 
    ```
*   **Command (Search):**
    ```bash
    ./spotify_tool.py --list-playlists "Mix"
    ```
*   **Sample Output (Search):**
    ```text
    🔍 Playlists matching 'Mix':
        1. My Awesome Mix
    📊 Total: 1 playlists
    ```

#### 4. Show Genre Configuration
Displays the current genre setup from your `config.json`.

*   **Command:**
    ```bash
    ./spotify_tool.py --show-config
    # or ./spotify_tool.py -sc
    ```
*   **Sample Output:**
    ```text
    🎸 Current genre configuration:

    📂 DEFAULT:
       📋 Playlists: Favorites, Daily Mix
       ❤️  Liked Songs: Yes

    📂 SYNTHWAVE:
       📋 Playlists: Synthwave Classics, Retrowave Gems, Night Drive
       ❤️  Liked Songs: Yes
    
    💡 Usage examples:
       ./spotify_tool.py <song_url> --genre default
       ./spotify_tool.py <song_url> --genre synthwave
    ```

#### 5. Add Song(s) to Genre/Default Playlists
Add one or more songs to the playlists defined under a specific genre, or to your default genre.

*   **Command (Single song, default genre):**
    ```bash
    ./spotify_tool.py https://open.spotify.com/track/4PTG3Z6ehGkBFwjybzWkR8
    ```
*   **Sample Output (Single song):**
    ```text
    Processing song 1/1: https://open.spotify.com/track/4PTG3Z6ehGkBFwjybzWkR8
    🎵 Attempting to add track: 4PTG3Z6ehGkBFwjybzWkR8
    👍 Adding 4PTG3Z6ehGkBFwjybzWkR8 to 2 playlist(s) and Liked Songs is set to: Yes
    ✅ Added to: Liked Songs
    ✅ Added to: Favorites
    ✅ Added to: Daily Mix
    
    🎉 All tasks complete! 1/1 song(s) processed with at least one successful addition.
    ```
*   **Command (Multiple songs, specific genre):**
    ```bash
    ./spotify_tool.py https://open.spotify.com/track/4PTG3Z6ehGkBFwjybzWkR8 https://open.spotify.com/track/0SfsD4X4J245UvWkS0D0xS --genre synthwave
    ```
*   **Sample Output (Multiple songs):**
    ```text
    Processing song 1/2: https://open.spotify.com/track/4PTG3Z6ehGkBFwjybzWkR8
    🎵 Attempting to add track: 4PTG3Z6ehGkBFwjybzWkR8
    👍 Adding 4PTG3Z6ehGkBFwjybzWkR8 to 3 playlist(s) and Liked Songs is set to: Yes
    ✅ Added to: Liked Songs
    ✅ Added to: Synthwave Classics
    ✅ Added to: Retrowave Gems
    ✅ Added to: Night Drive

    Processing song 2/2: https://open.spotify.com/track/0SfsD4X4J245UvWkS0D0xS
    🎵 Attempting to add track: 0SfsD4X4J245UvWkS0D0xS
    👍 Adding 0SfsD4X4J245UvWkS0D0xS to 3 playlist(s) and Liked Songs is set to: Yes
    ✅ Added to: Liked Songs
    ✅ Added to: Synthwave Classics
    ✅ Added to: Retrowave Gems
    ✅ Added to: Night Drive
    
    🎉 All tasks complete! 2/2 song(s) processed with at least one successful addition.
    ```

#### 6. Copy Playlist
Duplicates an existing playlist (yours or another user's) to your Spotify account under a new name.

*   **Command:**
    ```bash
    ./spotify_tool.py --copy-playlist spotify:playlist:37i9dQZF1DXcBWIGoYBM5M "My Copied Hits"
    # or ./spotify_tool.py -cp spotify:playlist:37i9dQZF1DXcBWIGoYBM5M "My Copied Hits"
    ```
*   **Sample Output:**
    ```text
    🔄 Starting playlist copy process...
    🔎 Fetching tracks from source playlist ID: 37i9dQZF1DXcBWIGoYBM5M...
    ✨ Creating new playlist 'My Copied Hits' for user your_user_id...
    ✅ New playlist 'My Copied Hits' created with ID: newPlaylistIdGeneratedBySpotify
    ➕ Adding X tracks to 'My Copied Hits'...
       Added batch of Y tracks... 
       (Repeats if more than 100 tracks)
    
    🎉 Playlist 'My Copied Hits' created and X/X tracks copied successfully!
    ```

#### 7. Get Playlist URL by Name
Fetches and displays the Spotify URL for one of your playlists.

*   **Command (Playlist Found):**
    ```bash
    ./spotify_tool.py --get-playlist-url "My Awesome Mix"
    # or ./spotify_tool.py -gpu "My Awesome Mix"
    ```
*   **Sample Output (Playlist Found):**
    ```text
    🔍 Searching for playlist: 'My Awesome Mix'...
    ✅ Found exact match: 'My Awesome Mix'
    🔗 Spotify URL for 'My Awesome Mix': https://open.spotify.com/playlist/yourPlaylistIdHere
    ```
*   **Command (Playlist Not Found):**
    ```bash
    ./spotify_tool.py --get-playlist-url "NonExistent Playlist"
    ```
*   **Sample Output (Playlist Not Found):**
    ```text
    🔍 Searching for playlist: 'NonExistent Playlist'...
    ❌ Playlist 'NonExistent Playlist' not found.
    ```

#### 8. Generate QR Code for Playlist
Creates a QR code image file for a playlist, allowing easy sharing.

*   **Command (By Playlist Name, default output filename):**
    ```bash
    ./spotify_tool.py --generate-qr "My Awesome Mix"
    # or ./spotify_tool.py -qr "My Awesome Mix"
    ```
*   **Sample Output (By Name):**
    ```text
    ℹ️ 'My Awesome Mix' is a name, attempting to find URL...
    🔍 Searching for playlist: 'My Awesome Mix'...
    ✅ Found exact match: 'My Awesome Mix'
    🔗 Spotify URL for 'My Awesome Mix': https://open.spotify.com/playlist/yourPlaylistIdHere
    ⚙️ Generating QR code for URL: https://open.spotify.com/playlist/yourPlaylistIdHere...
    ✅ QR code for playlist URL 'https://open.spotify.com/playlist/yourPlaylistIdHere' saved to 'playlist_qr.png'
    ```
*   **Command (By Playlist URL, custom output filename):**
    ```bash
    ./spotify_tool.py --generate-qr spotify:playlist:37i9dQZF1DXcBWIGoYBM5M custom_top_hits_qr.png
    ```
*   **Sample Output (By URL):**
    ```text
    ℹ️ Using provided URL: spotify:playlist:37i9dQZF1DXcBWIGoYBM5M
    ⚙️ Generating QR code for URL: spotify:playlist:37i9dQZF1DXcBWIGoYBM5M...
    ✅ QR code for playlist URL 'spotify:playlist:37i9dQZF1DXcBWIGoYBM5M' saved to 'custom_top_hits_qr.png'
    ```

### 5.⚙️ Configuration (`config.json`)
* The `config.json` file is automatically generated/updated by the `setup` and `--playlist-setup` commands. Here's an example structure:
```json
{
    "client_id": "your_spotify_client_id",
    "client_secret": "your_spotify_client_secret",
    "redirect_uri": "http://localhost:8080",
    "genres": {
        "default": {
            "playlists": ["Favorites", "Daily Mix"],
            "save_to_liked": true
        },
        "trance": {
            "playlists": [
                "bubdub",
                "tranceface",
                "derpstop",
                "glitchmatrix"
            ],
            "save_to_liked": true 
        },
        "downtempo": {
            "playlists": [
                "ChillOut",
                "MellowVibes"
            ],
            "save_to_liked": false
        }
    }
}
```
*Warning: Manually editing `config.json` for genre groups is possible but using `--playlist-setup` (`-ps`) is recommended to avoid formatting errors.*

### 🛠️ Development & Testing
Contributions are welcome! If you have ideas for new features, bug fixes, or improvements, please open an issue or submit a pull request.

To run tests:
```bash
python test_spotify_tool.py
```

### 📜 License
This project is licensed under the Apache 2.0 License - see the LICENSE file for details.

*The digital frontier awaits your command.*
