from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container, VerticalScroll
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import (
    Header, Footer, Label, ListView, ListItem, DataTable, Static, 
    Input, Button, RadioSet, RadioButton, Log, Markdown, LoadingIndicator
)
from textual.worker import Worker, get_current_worker 
from textual.reactive import reactive

import spotipy 

# Attempt to import from spotify_tool.py
try:
    from spotify_tool import (
        load_config, setup_spotify_client, get_user_playlists,
        extract_track_id, get_genre_config, find_playlist_ids, add_to_playlists,
        curate_playlist_command,
        get_user_top_artists_and_genres, 
        get_genre_suggestions_from_recommendations,
        get_user_top_tracks_by_time_range, 
        get_user_recently_played_tracks,  
        find_old_favorites,
        is_playlist_locked, lock_playlist, unlock_playlist, save_config,
        get_audio_features_for_playlist, # For BPM/Key Analysis
        analyze_playlist_audio_summary   # For BPM/Key Analysis
    )
except ImportError:
    print("Could not import from spotify_tool.py. Ensure it's in the PYTHONPATH.")
    # Define dummy functions if needed for basic TUI layout to work without full functionality
    def load_config(): raise FileNotFoundError("config.json not found (dummy function)")
    def setup_spotify_client(config): raise ConnectionError("Spotify client setup failed (dummy function)")
    def get_user_playlists(sp): return {"Dummy Playlist 1": "id1", "Dummy Playlist 2": "id2"}
    def extract_track_id(url): return "dummyTrackId" if url else None
    def get_genre_config(config, genre): return {'playlists': ["Dummy Playlist 1"], 'save_to_liked': True} if genre == "dummy" else {}
    def find_playlist_ids(sp, names): return ([("Dummy Playlist 1", "id1")], []) if "Dummy Playlist 1" in names else ([], names)
    def add_to_playlists(sp, track_id, playlists, save_to_liked, config=None, force=False): return [("Dummy Playlist 1", True, None)] 
    def curate_playlist_command(sp, source_id, new_name, progress_callback):
        if progress_callback:
            progress_callback("Dummy curation started.")
            progress_callback("Dummy step 1...")
            progress_callback("Dummy curation complete.")
        return True 
    def get_user_top_artists_and_genres(sp, time_range, limit): return (["artist1"], {"pop", "rock"}) 
    def get_genre_suggestions_from_recommendations(sp, artists, genres): 
        return {"new wave": {"artists": ["Artist X"], "artist_ids": ["idX"]}}
    def get_user_top_tracks_by_time_range(sp, time_range, limit=50): return [{'id': 't1', 'name': 'Track 1', 'artist': 'Artist A'}]
    def get_user_recently_played_tracks(sp, limit=50): return [{'id': 't2', 'name': 'Track 2', 'artist': 'Artist B'}]
    def find_old_favorites(sp, lt, mt, st, rec, num=20): return lt[:num] 
    def is_playlist_locked(config, playlist_id): return False 
    def lock_playlist(config, playlist_id, name): return True 
    def unlock_playlist(config, playlist_id): return True 
    def save_config(config): pass 
    def get_audio_features_for_playlist(sp, playlist_id): return [{'id': 't1', 'name': 'Track 1', 'artist': 'Artist A', 'tempo': 120.0, 'key': 0, 'mode': 1}] # Dummy
    def analyze_playlist_audio_summary(tracks): return {'average_bpm': 120.0, 'min_bpm': 120.0, 'max_bpm': 120.0, 'key_distribution': {'C Major': 1}, 'processed_tracks': [{'id': 't1', 'name': 'Track 1', 'artist': 'Artist A', 'tempo': 120.0, 'standard_key': 'C Major', 'camelot_key': '8B'}]} # Dummy


DEFAULT_CSS = """
Screen {
    overflow: hidden;
}
#main_content_area {
    layout: horizontal;
    height: 1fr; 
}
#playlist_pane {
    width: 30%;
    height: 100%;
    border: solid $primary-background-lighten-2;
    padding: 1;
    overflow-y: auto; 
}
#track_pane {
    width: 70%;
    height: 100%;
    border: solid $primary-background-lighten-2;
    padding: 1;
    overflow-y: auto; 
}
#playlist_list {
    height: 1fr; 
}
#track_table {
    height: 1fr; 
}
#status_bar {
    dock: bottom;
    height: 1; 
    padding: 0 1;
    background: $primary-background-lighten-1;
    overflow: hidden; 
    text-overflow: ellipsis;
    white-space: nowrap;
}
Static > .static--title { 
    padding: 1 0 1 1;
    background: $primary-background-lighten-3;
    width: 100%;
    text-style: bold;
}

/* AddSongScreen specific styles */
AddSongScreen {
    align: center middle;
}
#add_song_dialog {
    width: 80%;
    max-width: 70; 
    height: auto;
    max-height: 22; 
    border: thick $primary-background-lighten-2;
    background: $surface;
    padding: 1 2;
}
#add_song_dialog Input, #add_song_dialog RadioSet {
    margin-bottom: 1;
}
#playlist_selection_container {
    height: 6; 
    border: round $primary-background-lighten-2;
    padding: 1;
    margin-bottom: 1;
    overflow-y: auto;
}
#add_song_playlist_list {
     overflow-y: auto; 
}
#add_song_buttons {
    width: 100%;
    align-horizontal: right;
    padding-top: 1;
}
#add_song_buttons Button {
    margin-left: 2;
}
#add_song_status {
    margin-top: 1;
    height: 1; 
    color: $text-muted;
}

/* CuratePlaylistScreen specific styles */
CuratePlaylistScreen {
    align: center middle;
}
#curate_playlist_dialog {
    width: 80%;
    max-width: 80; 
    height: auto;
    max-height: 25; 
    border: thick $primary-background-lighten-2;
    background: $surface;
    padding: 1 2;
}
#curation_log_container { 
    height: 10; 
    border: round $primary-background-lighten-2;
    padding: 1;
    margin-top: 1;
    margin-bottom: 1;
    overflow-y: auto; 
}
#curation_log { 
    width: 100%;
    height: 100%; 
}
#curate_playlist_buttons {
    width: 100%;
    align-horizontal: right;
    padding-top: 1;
}
#curate_playlist_buttons Button {
    margin-left: 2;
}

/* HelpScreen specific styles */
HelpScreen {
    align: center middle;
}
#help_dialog {
    width: 80%;
    max-width: 60; 
    height: auto;
    max-height: 20; 
    border: thick $primary-background-lighten-2;
    background: $surface;
    padding: 1 2;
}
#help_content {
    height: 1fr; 
    overflow-y: auto;
    margin-top: 1;
    margin-bottom: 1;
}
#help_close_button_container {
    width: 100%;
    align-horizontal: center; 
    padding-top: 1;
}

/* SuggestGenresScreen specific styles */
SuggestGenresScreen {
    align: center middle;
}
#suggest_genres_dialog {
    width: 80%;
    max-width: 70;
    height: auto;
    max-height: 25; 
    border: thick $primary-background-lighten-2;
    background: $surface;
    padding: 1 2;
}
#time_range_selector {
    margin-bottom: 1;
    width: 100%;
}
#suggested_genres_display_container { 
    height: 10;
    border: round $primary-background-lighten-2;
    padding: 1;
    margin-top: 1;
    margin-bottom: 1;
    overflow-y: auto;
}
#suggested_genres_display { 
    width: 100%;
    height: 100%;
}
#suggest_genres_buttons {
    width: 100%;
    align-horizontal: right;
    padding-top: 1;
}
#suggest_genres_buttons Button {
    margin-left: 2;
}
#suggest_genres_status {
    margin-top: 1;
    height: 1;
    color: $text-muted;
}

/* OldFavoritesScreen specific styles */
OldFavoritesScreen {
    align: center middle;
}
#old_favorites_dialog {
    width: 90%;
    max-width: 80; 
    height: auto;
    max-height: 28; 
    border: thick $primary-background-lighten-2;
    background: $surface;
    padding: 1 2;
}
#old_favorites_input_container {
    layout: horizontal;
    height: auto;
    margin-bottom: 1;
}
#num_suggestions_input {
    width: 1fr; 
    margin-right: 1;
}
#find_old_favorites_button {
    width: auto; 
}
#old_favorites_table_container {
    height: 12; 
    border: round $primary-background-lighten-2;
    padding: 0; 
    margin-top: 1;
    margin-bottom: 1;
    overflow: hidden; 
}
#old_favorites_table {
    width: 100%;
    height: 100%; 
}
#old_favorites_status {
    margin-top: 1;
    height: 1;
    color: $text-muted;
}
#old_favorites_close_button_container {
    width: 100%;
    align-horizontal: center;
    padding-top: 1;
}

/* BPMKeyAnalysisScreen specific styles */
BPMKeyAnalysisScreen {
    align: center middle;
}
#bpm_key_dialog {
    width: 90%;
    max-width: 90; /* Allow wider for table */
    height: 90%; /* Take more vertical space */
    max-height: 30; /* Max height */
    border: thick $primary-background-lighten-2;
    background: $surface;
    padding: 1 2;
}
#analysis_results_container {
    height: 1fr; /* Fill available space */
    overflow-y: auto; /* Scroll if content overflows */
    padding: 1;
    border: round $primary-background-lighten-2;
    margin-top: 1;
    margin-bottom: 1;
}
#overall_stats_display {
    margin-bottom: 1;
    padding: 1;
    border: round $primary-background-lighten-3;
    background: $primary-background-lighten-1;
    height: auto; /* Adjust to content */
}
#bpm_key_track_table {
    height: 1fr; /* Allow table to take remaining space */
}
#bpm_key_close_button_container {
    width: 100%;
    align-horizontal: center;
    padding-top: 1;
}
"""

HELP_TEXT_MARKDOWN = """
## Keybindings

### Global
- **q**: Quit the application.
- **a**: Open "Add Song to Playlists" screen.
- **c**: Open "Curate Playlist" screen (requires a playlist to be selected from the main list).
- **g**: Open "Suggest New Genres" screen.
- **o**: Open "Old Favorites Finder" screen.
- **l**: Lock/Unlock selected playlist (from main playlist view).
- **b**: Open "BPM & Key Analysis" for selected playlist.
- **F1**: Show / Hide this Help screen.

### Navigation
- **Up/Down Arrows**: Navigate lists (Playlists, Tracks, options in dialogs).
- **Enter**: Select an item in a list or table, or activate a button.
- **Tab / Shift+Tab**: Move focus between UI elements.

### Dialogs / Screens
- **Escape**: Close the current dialog/screen (e.g., Help, Add Song, Curate Playlist).
- Buttons are usually activated with **Enter** when focused.
"""

class PlaylistItem(ListItem):
    def __init__(self, name: str, playlist_id: str, is_locked: bool = False) -> None:
        super().__init__() 
        self.playlist_name = name 
        self.playlist_id = playlist_id
        self.is_locked = is_locked
        self.is_selected_for_add = False 
        self.update_display() 

    def update_display(self) -> None:
        lock_icon = "🔒 " if self.is_locked else ""
        display_name = f"{lock_icon}{self.playlist_name}"
        try:
            label_widget = self.query_one(Label)
            label_widget.update(display_name)
        except NoMatches:
            self._nodes = [Label(display_name)] 

    def toggle_selection(self): 
        self.is_selected_for_add = not self.is_selected_for_add
        current_label_text = self.playlist_name 
        if self.is_locked:
            current_label_text = f"🔒 {current_label_text}"
        select_prefix = "[X] " if self.is_selected_for_add else "[ ] "
        label_widget = self.query_one(Label)
        label_widget.update(f"{select_prefix}{current_label_text}")

    def update_lock_status(self, is_locked: bool) -> None:
        self.is_locked = is_locked
        self.update_display()
        self.refresh() 


class AddSongScreen(Screen):
    # ... (content remains the same) ...
    def compose(self) -> ComposeResult:
        with Vertical(id="add_song_dialog"):
            yield Static("Add Song to Playlists", classes="static--title")
            yield Input(placeholder="Spotify Song URL or ID", id="song_url_input")
            with RadioSet(id="selection_mode"):
                yield RadioButton("Select Playlists", id="select_playlists_mode", value=True)
                yield RadioButton("Use Genre", id="use_genre_mode")
            
            with Container(id="playlist_selection_container"):
                yield ListView(id="add_song_playlist_list") 
                yield Input(placeholder="Genre Name", id="genre_input", classes="hidden") 

            yield Static("", id="add_song_status") 
            with Horizontal(id="add_song_buttons"):
                yield Button("Add Song", variant="primary", id="add_song_confirm_button")
                yield Button("Cancel", id="add_song_cancel_button")
    
    def on_mount(self) -> None:
        self.query_one("#add_song_status").update("Load your playlists or enter a genre.")
        self.run_worker(self.populate_playlist_list_for_add_song, thread=True)

    async def populate_playlist_list_for_add_song(self) -> None:
        playlist_list_widget = self.query_one("#add_song_playlist_list", ListView)
        status_widget = self.query_one("#add_song_status", Static)
        try:
            if self.app.sp: 
                playlists_data = get_user_playlists(self.app.sp)
                await playlist_list_widget.clear()
                if playlists_data:
                    for name in sorted(playlists_data.keys()):
                        is_locked = self.app.is_playlist_locked(self.app.config, playlists_data[name]) 
                        item = PlaylistItem(name, playlists_data[name], is_locked)
                        lock_icon = "🔒 " if item.is_locked else ""
                        item.query_one(Label).update(f"[ ] {lock_icon}{name}")
                        await playlist_list_widget.append(item)
                    status_widget.update("Select playlists or switch to genre mode.")
                else:
                    status_widget.update("No playlists found to select. Try genre mode.")
            else:
                status_widget.update("Spotify client not available.")
        except Exception as e:
            status_widget.update(f"Error loading playlists: {e}")

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        playlist_list = self.query_one("#add_song_playlist_list", ListView)
        genre_input = self.query_one("#genre_input", Input)
        if event.radio_set.id == "selection_mode":
            if event.pressed_button.id == "select_playlists_mode":
                playlist_list.remove_class("hidden")
                genre_input.add_class("hidden")
            elif event.pressed_button.id == "use_genre_mode":
                playlist_list.add_class("hidden")
                genre_input.remove_class("hidden")
    
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "add_song_playlist_list": 
            if isinstance(event.item, PlaylistItem):
                event.item.toggle_selection() 
                event.list_view.refresh_item(event.item)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        status_widget = self.query_one("#add_song_status", Static)
        if event.button.id == "add_song_cancel_button":
            self.app.pop_screen()
        elif event.button.id == "add_song_confirm_button":
            status_widget.update("Processing...")
            song_url = self.query_one("#song_url_input", Input).value
            if not song_url: status_widget.update("Error: Song URL cannot be empty."); return
            track_id = extract_track_id(song_url) 
            if not track_id: status_widget.update("Error: Invalid Song URL or ID."); return
            target_playlist_tuples = []; save_to_liked = False 
            selection_mode_radioset = self.query_one(RadioSet); selected_mode_button_id = None
            for button in selection_mode_radioset.query(RadioButton):
                if button.value: selected_mode_button_id = button.id; break
            if selected_mode_button_id == "select_playlists_mode":
                playlist_list_widget = self.query_one("#add_song_playlist_list", ListView)
                for item_widget in playlist_list_widget.children: 
                    if isinstance(item_widget, PlaylistItem) and item_widget.is_selected_for_add:
                        target_playlist_tuples.append((item_widget.playlist_name, item_widget.playlist_id))
                if not target_playlist_tuples: status_widget.update("Error: No playlists selected."); return
            elif selected_mode_button_id == "use_genre_mode":
                genre_name = self.query_one("#genre_input", Input).value.strip()
                if not genre_name: status_widget.update("Error: Genre name cannot be empty."); return
                genre_conf = get_genre_config(self.app.config, genre_name) 
                if not genre_conf or not genre_conf.get('playlists'): status_widget.update(f"Error: Genre '{genre_name}' not found or has no playlists."); return
                playlist_names_from_genre = genre_conf['playlists']; save_to_liked = genre_conf.get('save_to_liked', False)
                target_playlist_tuples_found, not_found = find_playlist_ids(self.app.sp, playlist_names_from_genre)
                target_playlist_tuples = target_playlist_tuples_found 
                if not_found: status_widget.update(f"Warning: Some genre playlists not found: {', '.join(not_found)}")
                if not target_playlist_tuples: status_widget.update(f"Error: No valid playlists found for genre '{genre_name}'."); return
            else: status_widget.update("Error: Unknown selection mode."); return
            self.run_worker(lambda: self.execute_add_to_playlists(track_id, target_playlist_tuples, save_to_liked), thread=True, name=f"add_song_{track_id}")

    async def execute_add_to_playlists(self, track_id, target_playlist_tuples, save_to_liked):
        status_widget = self.query_one("#add_song_status", Static)
        try:
            results = add_to_playlists(self.app.sp, track_id, target_playlist_tuples, save_to_liked, config=self.app.config )
            succeeded_playlists = [name for name, success, _ in results if success]; failed_playlists = [(name, err) for name, success, err in results if not success]
            summary_parts = []
            if succeeded_playlists: summary_parts.append(f"Added to: {', '.join(succeeded_playlists)}.")
            if failed_playlists: failed_summary = ", ".join([f"{name} (Error: {err})" for name, err in failed_playlists]); summary_parts.append(f"Failed for: {failed_summary}.")
            final_status = " ".join(summary_parts) if summary_parts else "No action taken or no playlists specified."
            status_widget.update(final_status)
        except Exception as e: status_widget.update(f"Error during add operation: {e}"); self.app.log(f"Full error in execute_add_to_playlists: {e}")

class CuratePlaylistScreen(Screen):
    # ... (content remains the same) ...
    def __init__(self, source_playlist_id: str, source_playlist_name: str, **kwargs) -> None:
        super().__init__(**kwargs); self.source_playlist_id = source_playlist_id; self.source_playlist_name = source_playlist_name
    def compose(self) -> ComposeResult:
        with Vertical(id="curate_playlist_dialog"):
            yield Static(f"Curate from: {self.source_playlist_name}", classes="static--title")
            yield Input(placeholder="New playlist name (optional)", id="new_curated_name_input")
            with Container(id="curation_log_container"): yield Log(id="curation_log", auto_scroll=True)
            with Horizontal(id="curate_playlist_buttons"): yield Button("Start Curation", variant="primary", id="start_curation_button"); yield Button("Cancel", id="curate_cancel_button")
    def on_mount(self) -> None: log_widget = self.query_one(Log); log_widget.write_line("Enter an optional name for the new curated playlist."); log_widget.write_line("Press 'Start Curation' to begin.")
    def tui_progress_callback(self, message: str) -> None: self.query_one(Log).write_line(message)
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "curate_cancel_button": self.app.pop_screen()
        elif event.button.id == "start_curation_button":
            event.button.disabled = True ; log_widget = self.query_one(Log); log_widget.clear(); log_widget.write_line("Starting curation process...")
            new_name = self.query_one("#new_curated_name_input", Input).value.strip() or None
            self.run_worker(lambda: self.execute_curation(new_name), thread=True, name=f"curate_{self.source_playlist_id}")
    async def execute_curation(self, new_name: str | None) -> None:
        success = False
        try:
            if not self.app.sp: self.tui_progress_callback("❌ Error: Spotify client not available."); return
            success = curate_playlist_command(self.app.sp, self.source_playlist_id, new_playlist_name_arg=new_name, progress_callback=self.tui_progress_callback)
        except Exception as e: self.tui_progress_callback(f"❌ An unexpected error occurred: {e}"); self.app.log(f"Full error in execute_curation: {e}") 
        finally:
            self.call_from_thread(self._enable_start_button)
            if success: self.tui_progress_callback("✅ Curation process finished successfully. Refreshing playlists."); self.app.call_later(self.app.refresh_playlists)
            else: self.tui_progress_callback("⚠️ Curation process finished with errors or was aborted.")
    def _enable_start_button(self) -> None:
        try: self.query_one("#start_curation_button", Button).disabled = False
        except NoMatches: pass 

class HelpScreen(Screen):
    # ... (content remains the same) ...
    BINDINGS = [("escape", "close_help", "Close Help"), ("f1", "close_help", "Close Help (Toggle)")]
    def compose(self) -> ComposeResult:
        with Vertical(id="help_dialog"): yield Static("Help - Keybindings", classes="static--title"); yield Markdown(HELP_TEXT_MARKDOWN, id="help_content"); with Container(id="help_close_button_container"): yield Button("Close (Esc or F1)", id="help_close_button")
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "help_close_button": self.action_close_help()
    def action_close_help(self) -> None: self.app.pop_screen()

class SuggestGenresScreen(Screen):
    # ... (content remains the same) ...
    TIME_RANGE_MAP = {"Short Term (Last 4 weeks)": "short_term", "Medium Term (Last 6 months)": "medium_term", "Long Term (Several years)": "long_term"}
    def compose(self) -> ComposeResult:
        with Vertical(id="suggest_genres_dialog"):
            yield Static("Suggest New Genres", classes="static--title")
            with RadioSet(id="time_range_selector"): yield RadioButton("Short Term (Last 4 weeks)", id="time_range_short"); yield RadioButton("Medium Term (Last 6 months)", id="time_range_medium", value=True); yield RadioButton("Long Term (Several years)", id="time_range_long")
            with Container(id="suggested_genres_display_container"): yield Log(id="suggested_genres_display", auto_scroll=True)
            yield Static("", id="suggest_genres_status")
            with Horizontal(id="suggest_genres_buttons"): yield Button("Get Suggestions", variant="primary", id="get_suggestions_button"); yield Button("Close", id="close_suggest_screen_button")
    def on_mount(self) -> None: self.query_one("#suggest_genres_status").update("Select a time range and get suggestions."); self.query_one("#suggested_genres_display", Log).write_line("Results will appear here.")
    def _update_status(self, message: str) -> None: self.query_one("#suggest_genres_status", Static).update(message)
    def _clear_results_and_status(self) -> None: self.query_one("#suggested_genres_display", Log).clear(); self._update_status("")
    def _enable_suggestion_button(self, enable: bool) -> None:
        try: self.query_one("#get_suggestions_button", Button).disabled = not enable
        except NoMatches: pass 
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close_suggest_screen_button": self.app.pop_screen()
        elif event.button.id == "get_suggestions_button":
            self._clear_results_and_status(); self._update_status("Fetching suggestions..."); self._enable_suggestion_button(False)
            selected_time_range_label = ""; time_range_selector = self.query_one(RadioSet)
            for rb in time_range_selector.query(RadioButton):
                if rb.value: selected_time_range_label = str(rb.label); break
            api_time_range = self.TIME_RANGE_MAP.get(selected_time_range_label, "medium_term")
            self.run_worker(lambda: self.execute_genre_suggestion(api_time_range), thread=True, name="suggest_genres_worker")
    async def execute_genre_suggestion(self, time_range: str) -> None:
        log_widget = self.query_one("#suggested_genres_display", Log)
        def _log_to_widget(message: str): self.call_from_thread(log_widget.write_line, message)
        try:
            if not self.app.sp: self.call_from_thread(self._update_status, "❌ Error: Spotify client not available."); return
            _log_to_widget(f"Fetching your top artists and genres for: {time_range}..."); artist_ids, current_genres = get_user_top_artists_and_genres(self.app.sp, time_range=time_range)
            if not artist_ids or not current_genres: msg = f"Could not retrieve top artists/genres for '{time_range}'."; _log_to_widget(f"⚠️ {msg}"); self.call_from_thread(self._update_status, msg); return
            _log_to_widget(f"Found {len(artist_ids)} top artists and {len(current_genres)} current genres."); _log_to_widget("Getting genre recommendations...")
            suggested_genres_data = get_genre_suggestions_from_recommendations(self.app.sp, artist_ids, current_genres)
            if not suggested_genres_data: _log_to_widget("\n🤷 No new genre suggestions found at this time."); self.call_from_thread(self._update_status, "No new genres found.")
            else:
                _log_to_widget("\n✨ Suggested New Genres ✨"); _log_to_widget("--------------------------")
                for genre_name, data in suggested_genres_data.items():
                    _log_to_widget(f"\n🎶 Genre: {genre_name}")
                    if data.get('artists'): _log_to_widget("  🎤 Example Artists:"); [ _log_to_widget(f"    - {artist_name}") for artist_name in data['artists'] ]
                _log_to_widget("--------------------------"); self.call_from_thread(self._update_status, "Suggestions loaded.")
        except Exception as e: error_msg = f"❌ An unexpected error occurred: {e}"; _log_to_widget(error_msg); self.call_from_thread(self._update_status, "Error fetching suggestions."); self.app.log(f"Full error in execute_genre_suggestion: {e}")
        finally: self.call_from_thread(self._enable_suggestion_button, True)

class OldFavoritesScreen(Screen):
    # ... (content remains the same) ...
    def compose(self) -> ComposeResult:
        with Vertical(id="old_favorites_dialog"):
            yield Static("Old Favorites Finder", classes="static--title")
            with Horizontal(id="old_favorites_input_container"): yield Input(placeholder="Number of suggestions (default 20)", id="num_suggestions_input", value="20"); yield Button("Find Old Favorites", variant="primary", id="find_old_favorites_button")
            with Container(id="old_favorites_table_container"): yield DataTable(id="old_favorites_table")
            yield Static("Enter number of suggestions and click 'Find'.", id="old_favorites_status")
            with Container(id="old_favorites_close_button_container"): yield Button("Close", id="close_old_favorites_screen_button")
    def on_mount(self) -> None: table = self.query_one("#old_favorites_table", DataTable); table.add_columns("Track", "Artist"); self.query_one("#num_suggestions_input", Input).focus()
    def _update_status(self, message: str) -> None: self.query_one("#old_favorites_status", Static).update(message)
    def _enable_find_button(self, enable: bool) -> None:
        try: self.query_one("#find_old_favorites_button", Button).disabled = not enable
        except NoMatches: pass
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close_old_favorites_screen_button": self.app.pop_screen()
        elif event.button.id == "find_old_favorites_button":
            self.query_one("#old_favorites_table", DataTable).clear(); self._update_status("Finding old favorites... (this may take a moment)"); self._enable_find_button(False)
            num_input_widget = self.query_one("#num_suggestions_input", Input); num_suggestions_str = num_input_widget.value
            try:
                num_suggestions = int(num_suggestions_str) if num_suggestions_str else 20
                if num_suggestions <= 0: self._update_status("Error: Number of suggestions must be positive."); self._enable_find_button(True); return
            except ValueError: self._update_status("Error: Invalid number for suggestions."); self._enable_find_button(True); return
            self.run_worker(lambda: self.execute_find_old_favorites(num_suggestions), thread=True, name="find_old_favorites_worker")
    async def execute_find_old_favorites(self, num_suggestions: int) -> None:
        table = self.query_one("#old_favorites_table", DataTable)
        def _add_row_to_table(track_name, artist_name, track_id): self.call_from_thread(table.add_row, track_name, artist_name, key=track_id)
        try:
            if not self.app.sp: self.call_from_thread(self._update_status, "❌ Error: Spotify client not available."); return
            self.call_from_thread(self._update_status, "Fetching long-term tracks..."); long_term = get_user_top_tracks_by_time_range(self.app.sp, 'long_term')
            if not long_term: self.call_from_thread(self._update_status, "❌ Error: Could not fetch long-term tracks."); return
            self.call_from_thread(self._update_status, "Fetching medium-term tracks..."); medium_term = get_user_top_tracks_by_time_range(self.app.sp, 'medium_term')
            self.call_from_thread(self._update_status, "Fetching short-term tracks..."); short_term = get_user_top_tracks_by_time_range(self.app.sp, 'short_term')
            self.call_from_thread(self._update_status, "Fetching recent tracks..."); recent = get_user_recently_played_tracks(self.app.sp)
            self.call_from_thread(self._update_status, "Analyzing tracks..."); favorites = find_old_favorites(self.app.sp, long_term, medium_term, short_term, recent, num_suggestions)
            if not favorites: self.call_from_thread(self._update_status, "🤷 No old favorites found matching criteria.")
            else:
                for track in favorites:
                    if get_current_worker().is_cancelled: break
                    _add_row_to_table(track['name'], track['artist'], track['id'])
                self.call_from_thread(self._update_status, f"Found {len(favorites)} old favorites.")
        except Exception as e: error_msg = f"❌ An unexpected error occurred: {e}"; self.call_from_thread(self._update_status, error_msg); self.app.log(f"Full error in execute_find_old_favorites: {e}")
        finally: self.call_from_thread(self._enable_find_button, True)


class BPMKeyAnalysisScreen(Screen):
    def __init__(self, playlist_id: str, playlist_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.playlist_id = playlist_id
        self.playlist_name = playlist_name

    def compose(self) -> ComposeResult:
        with Vertical(id="bpm_key_dialog"):
            yield Static(f"BPM & Key Analysis for: {self.playlist_name}", classes="static--title")
            yield LoadingIndicator(id="bpm_key_loading_indicator") # Initially visible
            with VerticalScroll(id="analysis_results_container", classes="hidden"): # Initially hidden
                yield Markdown(id="overall_stats_display") # Use Markdown for better formatting
                yield DataTable(id="bpm_key_track_table")
            with Container(id="bpm_key_close_button_container"):
                 yield Button("Close", id="close_analysis_screen_button")

    def on_mount(self) -> None:
        table = self.query_one("#bpm_key_track_table", DataTable)
        table.add_columns("Track", "Artist", "BPM", "Key", "Camelot")
        self.run_worker(self.load_analysis_data, thread=True, name=f"bpm_key_analysis_{self.playlist_id}")

    async def load_analysis_data(self) -> None:
        loading_indicator = self.query_one("#bpm_key_loading_indicator", LoadingIndicator)
        results_container = self.query_one("#analysis_results_container", VerticalScroll)
        overall_stats_widget = self.query_one("#overall_stats_display", Markdown)
        track_table_widget = self.query_one("#bpm_key_track_table", DataTable)
        
        # Show loading indicator, hide results
        loading_indicator.remove_class("hidden")
        results_container.add_class("hidden")
        track_table_widget.clear() # Clear previous results

        try:
            if not self.app.sp:
                overall_stats_widget.update("❌ Error: Spotify client not available.")
                return

            tracks_with_features = self.app.get_audio_features_for_playlist(self.app.sp, self.playlist_id)
            
            if not tracks_with_features:
                overall_stats_widget.update("ℹ️ No tracks found or features could not be retrieved for this playlist.")
                return

            analysis_summary = self.app.analyze_playlist_audio_summary(tracks_with_features)

            # Format overall stats using Markdown
            stats_md = f"### Overall Statistics\n\n"
            stats_md += f"- **Average BPM**: {analysis_summary['average_bpm']:.2f}\n"
            stats_md += f"- **Min BPM**: {analysis_summary['min_bpm']:.2f}\n"
            stats_md += f"- **Max BPM**: {analysis_summary['max_bpm']:.2f}\n\n"
            stats_md += "### Key Distribution\n\n"
            if analysis_summary['key_distribution']:
                for key, count in analysis_summary['key_distribution'].items():
                    stats_md += f"- **{key}**: {count} track(s)\n"
            else:
                stats_md += "- No key information found.\n"
            
            overall_stats_widget.update(stats_md)

            # Populate track table
            if analysis_summary['processed_tracks']:
                for track in analysis_summary['processed_tracks']:
                    if get_current_worker().is_cancelled: break
                    bpm_display = f"{track.get('tempo', 0.0):.1f}" if track.get('tempo') is not None else "-"
                    key_display = track.get('standard_key', '-')
                    camelot_display = track.get('camelot_key', '-')
                    track_table_widget.add_row(
                        str(track.get('name', 'N/A')),
                        str(track.get('artist', 'N/A')),
                        bpm_display,
                        key_display,
                        camelot_display,
                        key=track.get('id')
                    )
        except Exception as e:
            overall_stats_widget.update(f"❌ An unexpected error occurred: {e}")
            self.app.log(f"Full error in load_analysis_data: {e}")
        finally:
            # Hide loading indicator, show results
            loading_indicator.add_class("hidden")
            results_container.remove_class("hidden")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close_analysis_screen_button":
            self.app.pop_screen()


class SpotifyTUI(App):
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("a", "add_song_screen", "Add Song"),
        ("c", "curate_playlist_screen", "Curate Playlist"),
        ("g", "suggest_genres_screen", "Suggest Genres"),
        ("o", "old_favorites_screen", "Old Favorites"),
        ("l", "toggle_lock_playlist", "Lock/Unlock Playlist"),
        ("b", "bpm_key_analysis_screen", "BPM/Key Analysis"),
        ("f1", "toggle_help", "Help")
    ]
    TITLE = "Spotify TUI"
    CSS = DEFAULT_CSS

    sp = None 
    config = None 
    current_playlist_id = reactive(None) 
    selected_playlist_for_curation: PlaylistItem | None = None 

    is_playlist_locked = is_playlist_locked
    lock_playlist = lock_playlist
    unlock_playlist = unlock_playlist
    save_config = save_config
    get_audio_features_for_playlist = get_audio_features_for_playlist # Make accessible
    analyze_playlist_audio_summary = analyze_playlist_audio_summary   # Make accessible


    def compose(self) -> ComposeResult:
        # ... (compose remains the same) ...
        yield Header()
        with Horizontal(id="main_content_area"):
            with Vertical(id="playlist_pane"):
                yield Static("Playlists", classes="static--title")
                yield ListView(id="playlist_list") 
            with Vertical(id="track_pane"):
                yield Static("Tracks", classes="static--title")
                yield DataTable(id="track_table")
        yield Static("Initializing...", id="status_bar") 
        yield Footer() 

    async def on_mount(self) -> None:
        # ... (on_mount remains mostly the same) ...
        status_bar = self.query_one("#status_bar", Static)
        status_bar.update("Loading config...")
        try: self.config = load_config() 
        except FileNotFoundError: status_bar.update("Error: config.json not found. Please run './spotify_tool.py setup'."); return
        except Exception as e: status_bar.update(f"Error loading config: {e}"); return
        status_bar.update("Initializing Spotify client...")
        try: self.sp = setup_spotify_client(self.config) ; status_bar.update("Spotify client initialized.")
        except spotipy.SpotifyException as e: status_bar.update(f"Spotify Error: {e}. Check credentials or run './spotify_tool.py setup'."); return
        except Exception as e: status_bar.update(f"Error initializing Spotify: {e}"); return
        table = self.query_one(DataTable); table.add_columns("Track", "Artist", "Album") 
        if self.sp: await self.refresh_playlists() 
        else: status_bar.update("Spotify client not available. Cannot load playlists.")

    async def refresh_playlists(self) -> None:
        # ... (refresh_playlists remains the same) ...
        status_bar = self.query_one("#status_bar", Static); status_bar.update("Refreshing playlists...")
        self.run_worker(self.fetch_and_display_playlists, thread=True, name="refresh_playlists_worker")

    async def fetch_and_display_playlists(self) -> None:
        # ... (fetch_and_display_playlists remains the same, using self.is_playlist_locked) ...
        status_bar = self.query_one("#status_bar", Static); playlist_list_widget = self.query_one("#playlist_list", ListView)
        try:
            playlists_data = get_user_playlists(self.sp) 
            current_highlighted_id = playlist_list_widget.highlighted_child.playlist_id if playlist_list_widget.highlighted_child else None
            await playlist_list_widget.clear() 
            if not playlists_data:
                if not get_current_worker().is_cancelled: status_bar.update("No playlists found."); return
            count = 0; new_highlight_index = None; sorted_names = sorted(playlists_data.keys())
            for idx, name in enumerate(sorted_names):
                if get_current_worker().is_cancelled: break
                playlist_id = playlists_data[name]; is_locked = self.is_playlist_locked(self.config, playlist_id) 
                item = PlaylistItem(name, playlist_id, is_locked) ; await playlist_list_widget.append(item)
                if playlist_id == current_highlighted_id: new_highlight_index = idx
                count +=1
            if new_highlight_index is not None: playlist_list_widget.index = new_highlight_index
            if not get_current_worker().is_cancelled: status_bar.update(f"Loaded {count} playlists. Select a playlist to view tracks.")
        except spotipy.SpotifyException as e:
            if not get_current_worker().is_cancelled: status_bar.update(f"Spotify API Error loading playlists: {e}")
        except Exception as e:
            if not get_current_worker().is_cancelled: status_bar.update(f"Error loading playlists: {e}"); self.log(f"Error in fetch_and_display_playlists: {e}")

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        # ... (on_list_view_selected remains the same) ...
        if event.list_view.id == "playlist_list": 
            status_bar = self.query_one("#status_bar", Static); track_table = self.query_one("#track_table", DataTable)
            if isinstance(event.item, PlaylistItem):
                self.selected_playlist_for_curation = event.item ; self.current_playlist_id = event.item.playlist_id
                playlist_name = event.item.playlist_name ; status_bar.update(f"Loading tracks for '{playlist_name}'...")
                track_table.clear() 
                self.run_worker(lambda: self.fetch_and_display_tracks(self.current_playlist_id, playlist_name), thread=True, name=f"fetch_tracks_{self.current_playlist_id}")

    async def fetch_and_display_tracks(self, playlist_id: str, playlist_name: str) -> None:
        # ... (fetch_and_display_tracks remains the same) ...
        status_bar = self.query_one("#status_bar", Static); track_table = self.query_one("#track_table", DataTable)
        if not self.sp or not playlist_id:
            if not get_current_worker().is_cancelled: status_bar.update("Spotify client or playlist ID not available."); return
        all_tracks_details = []
        try:
            fields = "items(track(id,name,artists(name),album(name))),next"; results = self.sp.playlist_items(playlist_id, fields=fields, limit=50)
            while results:
                if get_current_worker().is_cancelled: return
                for item in results.get('items', []):
                    track = item.get('track')
                    if track and track.get('id'): 
                        track_name = track.get('name', 'N/A'); album_name = track.get('album', {}).get('name', 'N/A')
                        artist_names = [artist.get('name') for artist in track.get('artists', []) if artist.get('name')]; main_artist = ", ".join(artist_names) if artist_names else 'N/A'
                        all_tracks_details.append({'id': track.get('id'), 'name': track_name, 'artist': main_artist, 'album': album_name})
                if results.get('next') and not get_current_worker().is_cancelled: results = self.sp.next(results) 
                else: results = None 
            if get_current_worker().is_cancelled: return
            if not all_tracks_details:
                if not get_current_worker().is_cancelled: status_bar.update(f"No tracks found in '{playlist_name}'."); return
            for track_detail in all_tracks_details:
                 if get_current_worker().is_cancelled: break
                 track_table.add_row(track_detail['name'], track_detail['artist'], track_detail['album'], key=track_detail['id'])
            if not get_current_worker().is_cancelled: status_bar.update(f"Showing {len(all_tracks_details)} tracks for '{playlist_name}'.")
        except spotipy.SpotifyException as e:
            if not get_current_worker().is_cancelled: status_bar.update(f"Spotify API Error loading tracks: {e}")
        except Exception as e:
            if not get_current_worker().is_cancelled: status_bar.update(f"Error loading tracks: {e}"); self.log(f"Full error loading tracks for {playlist_id}: {e}") 

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        # ... (on_data_table_row_selected remains the same) ...
        status_bar = self.query_one("#status_bar", Static); track_name = event.data[0] if event.data and len(event.data) > 0 else "Unknown Track"; status_bar.update(f"Track selected: '{track_name}' (RowKey: {event.row_key})")

    def action_add_song_screen(self) -> None:
        # ... (remains the same) ...
        if self.sp and self.config: self.push_screen(AddSongScreen())
        else: self.query_one("#status_bar", Static).update("Error: Spotify client or config not ready.")

    def action_curate_playlist_screen(self) -> None:
        # ... (remains the same) ...
        status_bar = self.query_one("#status_bar", Static)
        if self.selected_playlist_for_curation: self.push_screen(CuratePlaylistScreen(source_playlist_id=self.selected_playlist_for_curation.playlist_id, source_playlist_name=self.selected_playlist_for_curation.playlist_name))
        else: status_bar.update("Select a source playlist from the list first to enable curation.")

    def action_toggle_help(self) -> None:
        # ... (remains the same) ...
        if isinstance(self.screen, HelpScreen): self.pop_screen()
        else: self.push_screen(HelpScreen())

    def action_suggest_genres_screen(self) -> None:
        # ... (remains the same) ...
        if self.sp: self.push_screen(SuggestGenresScreen())
        else: self.query_one("#status_bar", Static).update("Error: Spotify client not ready.")

    def action_old_favorites_screen(self) -> None:
        # ... (remains the same) ...
        if self.sp: self.push_screen(OldFavoritesScreen())
        else: self.query_one("#status_bar", Static).update("Error: Spotify client not ready.")

    async def action_toggle_lock_playlist(self) -> None:
        # ... (remains the same) ...
        status_bar = self.query_one("#status_bar", Static); playlist_list_widget = self.query_one("#playlist_list", ListView); selected_item = playlist_list_widget.highlighted_child
        if not isinstance(selected_item, PlaylistItem): status_bar.update("No playlist selected to lock/unlock."); return
        playlist_id = selected_item.playlist_id; playlist_name = selected_item.playlist_name; current_lock_status = selected_item.is_locked
        if current_lock_status:
            status_bar.update(f"Unlocking '{playlist_name}'...")
            if self.unlock_playlist(self.config, playlist_id): self.save_config(self.config); selected_item.update_lock_status(False); status_bar.update(f"🔓 Playlist '{playlist_name}' unlocked.")
            else: status_bar.update(f"Failed to unlock '{playlist_name}'. (Already unlocked or error)")
        else:
            status_bar.update(f"Locking '{playlist_name}'...")
            if self.lock_playlist(self.config, playlist_id, playlist_name): self.save_config(self.config); selected_item.update_lock_status(True); status_bar.update(f"🔒 Playlist '{playlist_name}' locked.")
            else: status_bar.update(f"Failed to lock '{playlist_name}'. (Already locked or error)")
            
    def action_bpm_key_analysis_screen(self) -> None:
        """Pushes the BPMKeyAnalysisScreen if a playlist is selected."""
        status_bar = self.query_one("#status_bar", Static)
        # Use self.selected_playlist_for_curation as it holds the last selected PlaylistItem
        if self.selected_playlist_for_curation:
            self.push_screen(BPMKeyAnalysisScreen(
                playlist_id=self.selected_playlist_for_curation.playlist_id,
                playlist_name=self.selected_playlist_for_curation.playlist_name
            ))
        else:
            status_bar.update("Select a playlist from the list first for BPM/Key analysis.")


if __name__ == "__main__":
    app = SpotifyTUI()
    app.run()
