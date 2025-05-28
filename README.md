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
*   **Automated Playlist Curation**: Analyzes an existing playlist's genres and audio features (mood) to generate a list of recommended songs, then creates a new playlist populated with these recommendations. Ideal for discovering new tracks similar to a playlist you love or for creating a fresh mix with a similar vibe.
*   **Playlist Locking**: Protect important playlists from accidental modifications by the "Add Song" feature. Locked playlists will be skipped unless a force option is used (future enhancement).

---

## 💻 Textual User Interface (TUI) Mode

In addition to its command-line interface, The Set Controller offers an interactive Textual User Interface (TUI) for a more visual and dynamic experience.

### Launching the TUI
To launch the TUI, ensure you have installed all dependencies, including `textual` (which is listed in `requirements.txt`):
```bash
pip install -r requirements.txt
```
Then, run:
```bash
python spotify_tool.py tui
```

### TUI Features
The TUI provides the following functionalities:
*   **Browse Playlists and Tracks**: View your Spotify playlists in a dedicated pane and see the tracks within the selected playlist in another pane.
*   **Add Song to Playlists**: Press 'a' to open a dialog where you can input a song URL. You can then choose to:
    *   Select multiple specific playlists from a list to add the song to.
    *   Use a pre-configured genre from your `config.json` to add the song to all playlists in that genre.
    *   The "Add Song" feature respects playlist locks; it will not add songs to locked playlists and will indicate this.
*   **Automated Playlist Curation**: Select a source playlist from the list, then press 'c' to open the curation screen. You can:
    *   Optionally provide a name for the new curated playlist.
    *   Start the curation process and see real-time progress messages in a log view as the tool analyzes the source, gets recommendations, and creates/populates the new playlist.
*   **Suggest New Genres**: Press 'g' to open a screen where you can select a time range (short, medium, or long term). The TUI then displays a list of new genre suggestions based on your listening habits for that period, along with example artists for each suggested genre.
*   **Old Favorites Finder**: Press 'o' to open a screen where you can specify the number of suggestions. The TUI then displays a list of tracks you might have enjoyed frequently in the past but haven't listened to recently.
*   **Playlist Locking**:
    *   **Visual Indicator**: Locked playlists are visually marked with a "🔒" icon in the main playlist list.
    *   **Toggling Lock**: Press 'l' when a playlist is selected in the main list to lock or unlock it. The visual indicator updates immediately.
*   **Status Updates**: A status bar at the bottom provides feedback on current operations, errors, or successful actions.
*   **Help Screen**: Press `F1` to toggle an in-app help screen that lists keybindings and provides guidance.

### Keybindings & Navigation
*   Global keybindings are displayed in the **Footer** of the TUI.
*   Press **F1** at any time to access the **Help Screen** for a more detailed list of keybindings.
*   Essential global keys include:
    *   `q`: Quit the application.
    *   `a`: Open the "Add Song to Playlists" screen.
    *   `c`: Open the "Curate Playlist" screen (requires a playlist to be selected first).
    *   `g`: Open the "Suggest New Genres" screen.
    *   `o`: Open the "Old Favorites Finder" screen.
    *   `l`: Lock/Unlock the currently selected playlist in the main playlist view.
*   Standard Textual navigation (Arrow keys, Tab, Enter, Escape) is used for moving around and interacting with UI elements.

---

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository (or download the script directly)
git clone https://github.com/crazy54/the-set-controller.git
cd the-set-controller

# Install dependencies using requirements.txt
pip install -r requirements.txt
```
Note: Ensure you have Python 3 installed. The `requirements.txt` file lists all necessary libraries, including `spotipy`, `qrcode`, `Pillow`, and `textual`.

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
    This adds the specified song(s) to all playlists in the chosen genre (or default genre if `--genre` is omitted) and to Liked Songs if configured for that genre. Adding songs respects playlist locks (see "Playlist Locking" below).

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

*   **Automated Playlist Curation:**
    Analyzes a source playlist and generates a new playlist with recommended tracks based on the source's mood and genres.
    ```bash
    python spotify_tool.py --curate-playlist <source_playlist_id_or_url> [--new-name <desired_playlist_name>]
    # Alias: -cpL
    # Example (with a custom name):
    python spotify_tool.py --curate-playlist spotify:playlist:37i9dQZF1DXcBWIGoYBM5M --new-name "My Curated Chill Mix"
    # Example (system-generated name):
    python spotify_tool.py -cpL https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M 
    ```
    If `--new-name` is not provided, a name will be generated based on the source playlist's name and the current date (e.g., "Curated - \[Original Name] - YYYY-MM-DD").

*   **Suggest New Genres:**
    Suggests new genres to explore based on your top artists and their genres for a given period.
    ```bash
    python spotify_tool.py suggest-genres [--time-range <short_term|medium_term|long_term>]
    # Alias: -sg
    # --time-range or -tr: Defaults to 'medium_term'. Other options: 'short_term', 'long_term'.
    # Example:
    python spotify_tool.py suggest-genres -tr short_term
    ```

*   **Old Favorites Finder:**
    Suggests tracks you might have listened to frequently in the past but not recently.
    ```bash
    python spotify_tool.py old-favorites [--suggestions <number>]
    # Alias: -of
    # --suggestions or -n <number>: Specifies the maximum number of old favorites to suggest (defaults to 20).
    # Example:
    python spotify_tool.py old-favorites -n 15
    ```

*   **Playlist Locking:**
    Manage playlist locks to prevent accidental modifications by some features (like song additions).
    ```bash
    # Lock a playlist
    python spotify_tool.py lock <playlist_url_or_id>
    # Unlock a playlist
    python spotify_tool.py unlock <playlist_url_or_id>
    # List all locked playlists
    python spotify_tool.py list-locked
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
... (content remains the same) ...

#### 2. Interactive Playlist Group (Genre) Setup
... (content remains the same) ...

#### 3. List User's Playlists
... (content remains the same) ...

#### 4. Show Genre Configuration
... (content remains the same) ...

#### 5. Add Song(s) to Genre/Default Playlists
... (content remains the same, but note that song additions respect locks) ...

#### 6. Copy Playlist
... (content remains the same) ...

#### 7. Get Playlist URL by Name
... (content remains the same) ...

#### 8. Generate QR Code for Playlist
... (content remains the same) ...

#### 9. Automated Playlist Curation
... (content remains the same) ...

#### 10. Suggest New Genres
... (content remains the same) ...

#### 11. Old Favorites Finder
... (content remains the same) ...

#### 12. Playlist Locking Management
These commands allow you to protect specific playlists from being modified by features like "Add Song".

*   **Lock a Playlist:**
    ```bash
    python spotify_tool.py lock spotify:playlist:yourPlaylistIDHere
    # or by URL:
    python spotify_tool.py lock https://open.spotify.com/playlist/yourPlaylistIDHere
    ```
*   **Sample Output (Lock):**
    ```text
    🔒 Playlist 'Your Playlist Name' (ID: yourPlaylistIDHere) has been locked.
    ✅ Configuration saved to config.json
    ```
    If already locked:
    ```text
    ℹ️ Playlist 'Your Playlist Name' (ID: yourPlaylistIDHere) is already locked.
    ```

*   **Unlock a Playlist:**
    ```bash
    python spotify_tool.py unlock spotify:playlist:yourPlaylistIDHere
    ```
*   **Sample Output (Unlock):**
    ```text
    🔓 Playlist 'Your Playlist Name' (ID: yourPlaylistIDHere) has been unlocked.
    ✅ Configuration saved to config.json
    ```
    If not found in locked list:
    ```text
    ℹ️ Playlist ID 'yourPlaylistIDHere' not found in locked list or already unlocked.
    ```

*   **List Locked Playlists:**
    ```bash
    python spotify_tool.py list-locked
    ```
*   **Sample Output (List Locked):**
    ```text
    🔒 Locked Playlists:
    -------------------
     1. My Precious Mix (ID: playlistId1)
     2. Do Not Disturb (ID: playlistId2)
    -------------------
    ```
    If no playlists are locked:
    ```text
    ℹ️ No playlists are currently locked.
    ```
*   **Effect of Locking**: When a playlist is locked, the `add-song` command (and the corresponding TUI feature) will skip it by default, printing a message like "❌ Failed to add to My Precious Mix: Playlist is locked".

### 5.⚙️ Configuration (`config.json`)
* The `config.json` file is automatically generated/updated by the `setup` and `--playlist-setup` commands. Here's an example structure:
```json
{
    "client_id": "your_spotify_client_id",
    "client_secret": "your_spotify_client_secret",
    "redirect_uri": "http://localhost:8080",
    "locked_playlists": [
        {
            "id": "playlistId1",
            "name": "My Precious Mix"
        },
        {
            "id": "playlistId2",
            "name": "Do Not Disturb"
        }
    ],
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
*Warning: Manually editing `config.json` for genre groups is possible but using `--playlist-setup` (`-ps`) is recommended to avoid formatting errors. The `locked_playlists` section is managed by the `lock` and `unlock` commands.*

### 🛠️ Development & Testing
Contributions are welcome! If you have ideas for new features, bug fixes, or improvements, please open an issue or submit a pull request.

To run tests:
```bash
python test_spotify_tool.py
```

### 📜 License
This project is licensed under the Apache 2.0 License - see the LICENSE file for details.

*The digital frontier awaits your command.*