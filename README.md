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

*   **Add song to genre playlists:**
    ```bash
    python spotify_tool.py <song_url> --genre <your_genre_name>
    # Example:
    python spotify_tool.py https://open.spotify.com/track/YOUR_TRACK_ID --genre trance
    ```
    This adds the song to all playlists in the "trance" genre and to Liked Songs if configured.

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
