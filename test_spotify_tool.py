import unittest
from unittest.mock import patch, Mock, call, MagicMock, StringIO
import sys
import os

# Adjust the path to import from the parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from spotify_tool import (
    get_track_details,
    analyze_playlist_mood_genre,
    get_recommendations,
    determine_new_playlist_name,
    create_empty_playlist,
    populate_playlist_with_tracks,
    curate_playlist_command,
    parse_arguments,
    extract_playlist_id,
    get_user_top_artists_and_genres, 
    get_genre_suggestions_from_recommendations,
    get_user_top_tracks_by_time_range, 
    get_user_recently_played_tracks,  
    find_old_favorites,
    is_playlist_locked, # For testing
    lock_playlist,      # For testing
    unlock_playlist,    # For testing
    add_to_playlists,   # For testing modified version
    main,               # For testing main command handling
    load_config,        # For testing main command handling
    setup_spotify_client, # For testing main command handling
    save_config         # For testing main command handling
)
import datetime 
import spotipy 

# --- Existing Test Classes (Keep them as they are, condensed for brevity here) ---
class TestGetTrackDetails(unittest.TestCase):
    @patch('spotify_tool.spotipy.Spotify')
    def test_successful_fetch(self, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value; track_ids = ["track1", "track2"]
        mock_sp.audio_features.side_effect = [[{'id': 'track1', 'danceability': 0.7}], [{'id': 'track2', 'danceability': 0.8}]]
        mock_sp.track.side_effect = [{'id': 'track1', 'artists': [{'id': 'artist1', 'name': 'Artist One'}]}, {'id': 'track2', 'artists': [{'id': 'artist2', 'name': 'Artist Two'}]}]
        mock_sp.artist.side_effect = [{'id': 'artist1', 'genres': ['pop', 'rock']}, {'id': 'artist2', 'genres': ['electronic', 'dance']}]
        expected_details = [{'id': 'track1', 'audio_features': {'id': 'track1', 'danceability': 0.7}, 'artist_genres': ['pop', 'rock']}, {'id': 'track2', 'audio_features': {'id': 'track2', 'danceability': 0.8}, 'artist_genres': ['dance', 'electronic']}]
        result = get_track_details(mock_sp, track_ids)
        for item in expected_details: item['artist_genres'].sort()
        self.assertEqual(result, expected_details)

class TestAnalyzePlaylistMoodGenre(unittest.TestCase):
    @patch('spotify_tool.get_track_details')
    @patch('spotify_tool.spotipy.Spotify') 
    @patch('spotify_tool.extract_playlist_id')
    def test_successful_analysis(self, mock_extract_id, mock_sp_constructor, mock_get_track_details):
        mock_sp = mock_sp_constructor.return_value ; playlist_id_or_url = "some_playlist_url"; extracted_id = "playlist123"; mock_extract_id.return_value = extracted_id
        mock_sp.playlist_items.side_effect = [{'items': [{'track': {'id': 'trackA', 'uri': 'uriA'}}, {'track': {'id': 'trackB', 'uri': 'uriB'}}], 'next': 'next_page_url_fake' }]
        mock_sp.next.return_value = { 'items': [{'track': {'id': 'trackC', 'uri': 'uriC'}}], 'next': None }
        mock_get_track_details.return_value = [
            {'id': 'trackA', 'audio_features': {'danceability': 0.5, 'energy': 0.6, 'valence': 0.7, 'tempo': 120.0, 'instrumentalness': 0.1, 'acousticness': 0.2, 'speechiness': 0.05, 'liveness': 0.15}, 'artist_genres': ['rock', 'pop', 'alternative rock']},
            {'id': 'trackB', 'audio_features': {'danceability': 0.7, 'energy': 0.8, 'valence': 0.9, 'tempo': 140.0, 'instrumentalness': 0.0, 'acousticness': 0.1, 'speechiness': 0.1, 'liveness': 0.25}, 'artist_genres': ['pop', 'electronic', 'dance pop']},
            {'id': 'trackC', 'audio_features': {'danceability': 0.6, 'energy': 0.7, 'valence': 0.8, 'tempo': 130.0, 'instrumentalness': 0.2, 'acousticness': 0.3, 'speechiness': 0.08, 'liveness': 0.20}, 'artist_genres': ['rock', 'indie rock', 'pop rock']}
        ]
        expected_top_genres_set = {'pop', 'rock', 'alternative rock', 'electronic', 'dance pop'} 
        expected_analysis = {'average_audio_features': {'danceability': (0.5 + 0.7 + 0.6) / 3, 'energy': (0.6 + 0.8 + 0.7) / 3, 'valence': (0.7 + 0.9 + 0.8) / 3, 'instrumentalness': (0.1 + 0.0 + 0.2) / 3, 'acousticness': (0.2 + 0.1 + 0.3) / 3, 'speechiness': (0.05 + 0.1 + 0.08) / 3, 'liveness': (0.15 + 0.25 + 0.20) / 3, 'tempo': (120.0 + 140.0 + 130.0) / 3}, 'seed_tracks': ['trackA', 'trackB', 'trackC'] }
        result = analyze_playlist_mood_genre(mock_sp, playlist_id_or_url)
        self.assertEqual(result['seed_tracks'], expected_analysis['seed_tracks']); self.assertCountEqual(result['top_genres'], list(expected_top_genres_set)) 
        for feature, avg_val in expected_analysis['average_audio_features'].items(): self.assertAlmostEqual(result['average_audio_features'][feature], avg_val, places=5)

class TestGetRecommendations(unittest.TestCase):
    @patch('spotify_tool.spotipy.Spotify')
    def test_successful_recommendations(self, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value; analysis_results = {'seed_tracks': ['trackA', 'trackB', 'trackC', 'trackD', 'trackE'], 'top_genres': ['pop', 'rock', 'electronic', 'dance', 'hip hop'], 'average_audio_features': {'danceability': 0.7, 'energy': 0.8, 'valence': 0.6, 'tempo': 120.0}}
        mock_sp.track.side_effect = [{'artists': [{'id': 'artistA'}]}, {'artists': [{'id': 'artistB'}]}]
        mock_sp.recommendations.return_value = {'tracks': [{'id': 'recTrack1', 'name': 'Rec Song 1'}, {'id': 'recTrack2', 'name': 'Rec Song 2'}]}
        expected_seed_tracks_uris = ['spotify:track:trackA', 'spotify:track:trackB']; expected_seed_artist_ids = ['artistA', 'artistB'] ; expected_seed_genres = ['pop'] 
        expected_target_features = {'target_danceability': 0.7, 'target_energy': 0.8, 'target_valence': 0.6, 'target_tempo': 120.0}
        result = get_recommendations(mock_sp, analysis_results, limit=10)
        self.assertEqual(result, ['recTrack1', 'recTrack2'])
        mock_sp.recommendations.assert_called_once_with(seed_artists=expected_seed_artist_ids, seed_genres=expected_seed_genres, seed_tracks=expected_seed_tracks_uris, limit=10, **expected_target_features)

class TestPlaylistHelpers(unittest.TestCase):
    @patch('spotify_tool.spotipy.Spotify')
    @patch('spotify_tool.datetime.date') 
    def test_determine_new_playlist_name(self, mock_date, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value; mock_today = datetime.date(2023, 10, 26); mock_date.today.return_value = mock_today; date_str = "2023-10-26"
        name = determine_new_playlist_name(mock_sp, "source_id", "My Custom Name"); self.assertEqual(name, "My Custom Name")
        mock_sp.playlist.return_value = {'name': 'Old Playlist'}; name = determine_new_playlist_name(mock_sp, "source_id_good"); self.assertEqual(name, f"Curated - Old Playlist - {date_str}")

class TestCuratePlaylistCommand(unittest.TestCase):
    @patch('spotify_tool.populate_playlist_with_tracks')
    @patch('spotify_tool.create_empty_playlist')
    @patch('spotify_tool.determine_new_playlist_name')
    @patch('spotify_tool.get_recommendations')
    @patch('spotify_tool.analyze_playlist_mood_genre')
    @patch('spotify_tool.extract_playlist_id')
    @patch('spotify_tool.spotipy.Spotify') 
    def test_curate_playlist_successful_flow(self, mock_sp_constructor, mock_extract, mock_analyze, mock_recommend, mock_determine_name, mock_create_playlist, mock_populate):
        mock_sp = mock_sp_constructor.return_value; source_url = "http://source.playlist.url"; provided_new_name = "My New Curated Mix"
        mock_extract.return_value = "source_playlist_123"; mock_analyze.return_value = {'seed_tracks': ['s1'], 'top_genres': ['g1'], 'average_audio_features': {'energy': 0.7}}; mock_recommend.return_value = ['rec_track1', 'rec_track2']; mock_determine_name.return_value = "Final Playlist Name"; mock_create_playlist.return_value = "new_playlist_id_abc"; mock_populate.return_value = 2 
        result = curate_playlist_command(mock_sp, source_url, provided_new_name); self.assertTrue(result)

class TestSuggestGenresFunctionality(unittest.TestCase):
    @patch('spotify_tool.spotipy.Spotify')
    @patch('sys.stderr', new_callable=StringIO) 
    def test_get_user_top_artists_and_genres_success(self, mock_stderr, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value; mock_sp.current_user_top_artists.return_value = {'items': [{'id': 'artist1', 'genres': ['pop', 'rock']}, {'id': 'artist2', 'genres': ['rock', 'electronic']}, {'id': 'artist3', 'genres': ['jazz']}]}
        artist_ids, genres = get_user_top_artists_and_genres(mock_sp, time_range='short_term', limit=3)
        self.assertEqual(artist_ids, ['artist1', 'artist2', 'artist3']); self.assertEqual(genres, {'pop', 'rock', 'electronic', 'jazz'})

    @patch('spotify_tool.spotipy.Spotify')
    @patch('sys.stderr', new_callable=StringIO)
    def test_get_genre_suggestions_success(self, mock_stderr, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value; current_artist_ids = ['artistA', 'artistB']; current_genres_set = {'pop', 'rock'}
        mock_sp.recommendations.return_value = {'tracks': [{'artists': [{'id': 'artistC'}]}, {'artists': [{'id': 'artistD'}]}, {'artists': [{'id': 'artistE'}]}, {'artists': [{'id': 'artistF'}]}  ]}
        mock_sp.artists.return_value = {'artists': [{'id': 'artistC', 'name': 'Artist C', 'genres': ['new-wave']}, {'id': 'artistD', 'name': 'Artist D', 'genres': ['synth-pop']}, {'id': 'artistE', 'name': 'Artist E', 'genres': ['pop', 'funk']}, {'id': 'artistF', 'name': 'Artist F', 'genres': ['new-wave', 'post-punk']} ]}
        suggestions = get_genre_suggestions_from_recommendations(mock_sp, current_artist_ids, current_genres_set, artists_per_genre=2)
        self.assertIn('new-wave', suggestions); self.assertIn('synth-pop', suggestions); self.assertIn('funk', suggestions); self.assertIn('post-punk', suggestions); self.assertNotIn('pop', suggestions) ; self.assertNotIn('rock', suggestions)
        self.assertCountEqual(suggestions['new-wave']['artists'], ['Artist C', 'Artist F'])

class TestOldFavoritesFinderFunctionality(unittest.TestCase):
    @patch('spotify_tool.spotipy.Spotify')
    @patch('sys.stderr', new_callable=StringIO)
    def test_get_user_top_tracks_success(self, mock_stderr, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value; mock_sp.current_user_top_tracks.return_value = {'items': [{'id': 't1', 'name': 'Track 1', 'artists': [{'name': 'Artist A'}]}, {'id': 't2', 'name': 'Track 2', 'artists': [{'name': 'Artist B'}]}]}
        tracks = get_user_top_tracks_by_time_range(mock_sp, 'medium_term', limit=2)
        self.assertEqual(tracks, [{'id': 't1', 'name': 'Track 1', 'artist': 'Artist A'}, {'id': 't2', 'name': 'Track 2', 'artist': 'Artist B'}])

    @patch('spotify_tool.spotipy.Spotify')
    @patch('sys.stderr', new_callable=StringIO)
    def test_get_user_recently_played_success(self, mock_stderr, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value; mock_sp.current_user_recently_played.return_value = {'items': [{'track': {'id': 't_rec1', 'name': 'Recent Track 1', 'artists': [{'name': 'Artist X'}]}}, {'track': {'id': 't_rec2', 'name': 'Recent Track 2', 'artists': [{'name': 'Artist Y'}]}}]}
        tracks = get_user_recently_played_tracks(mock_sp, limit=2)
        self.assertEqual(tracks, [{'id': 't_rec1', 'name': 'Recent Track 1', 'artist': 'Artist X'}, {'id': 't_rec2', 'name': 'Recent Track 2', 'artist': 'Artist Y'}])

    def test_find_old_favorites_core_logic(self):
        track1 = {'id': '1', 'name': 'Track 1', 'artist': 'Artist A'}; track2 = {'id': '2', 'name': 'Track 2', 'artist': 'Artist B'}; track3 = {'id': '3', 'name': 'Track 3', 'artist': 'Artist C'}; track4 = {'id': '4', 'name': 'Track 4', 'artist': 'Artist D'}; track5 = {'id': '5', 'name': 'Track 5', 'artist': 'Artist E'}; track6 = {'id': '6', 'name': 'Track 6', 'artist': 'Artist F'}
        long_term = [track1, track2, track3, track4, track5, track6]; medium_term = [track2]; short_term = [track3]; recent = [track4]
        mock_sp_instance = MagicMock() 
        result = find_old_favorites(mock_sp_instance, long_term, medium_term, short_term, recent); self.assertCountEqual(result, [track1, track5, track6])

# --- New/Updated Test Classes for Playlist Locking ---
class TestPlaylistLockingFunctionality(unittest.TestCase):
    def test_is_playlist_locked(self):
        config_locked = {'locked_playlists': [{'id': 'id1', 'name': 'N1'}, {'id': 'id2', 'name': 'N2'}]}
        self.assertTrue(is_playlist_locked(config_locked, 'id1'))
        self.assertFalse(is_playlist_locked(config_locked, 'id3'))
        
        config_empty_lock = {'locked_playlists': []}
        self.assertFalse(is_playlist_locked(config_empty_lock, 'id1'))
        
        config_no_key = {} # load_config would add 'locked_playlists': []
        # Simulate load_config behavior for this test
        if 'locked_playlists' not in config_no_key: config_no_key['locked_playlists'] = []
        self.assertFalse(is_playlist_locked(config_no_key, 'id1'))

    @patch('builtins.print') # Mock print for this specific test
    def test_lock_playlist(self, mock_print):
        config = {'locked_playlists': []}
        
        # Lock new playlist
        self.assertTrue(lock_playlist(config, 'id1', 'Playlist 1'))
        self.assertEqual(config['locked_playlists'], [{'id': 'id1', 'name': 'Playlist 1'}])
        mock_print.assert_called_with("🔒 Playlist 'Playlist 1' (ID: id1) has been locked.")
        
        mock_print.reset_mock()
        # Try to lock already locked playlist
        self.assertFalse(lock_playlist(config, 'id1', 'Playlist 1'))
        self.assertEqual(config['locked_playlists'], [{'id': 'id1', 'name': 'Playlist 1'}]) # Should be unchanged
        mock_print.assert_called_with("ℹ️ Playlist 'Playlist 1' (ID: id1) is already locked.")

    @patch('builtins.print')
    def test_unlock_playlist(self, mock_print):
        config = {'locked_playlists': [{'id': 'id1', 'name': 'P1'}, {'id': 'id2', 'name': 'P2'}]}
        
        # Unlock existing playlist
        self.assertTrue(unlock_playlist(config, 'id1'))
        self.assertEqual(config['locked_playlists'], [{'id': 'id2', 'name': 'P2'}])
        mock_print.assert_called_with("🔓 Playlist 'P1' (ID: id1) has been unlocked.")
        
        mock_print.reset_mock()
        # Unlock non-existent playlist
        self.assertFalse(unlock_playlist(config, 'id_nonexistent'))
        self.assertEqual(config['locked_playlists'], [{'id': 'id2', 'name': 'P2'}]) # Unchanged
        mock_print.assert_called_with("ℹ️ Playlist ID 'id_nonexistent' not found in locked list or already unlocked.")

        mock_print.reset_mock()
        # Unlock from empty list
        config_empty = {'locked_playlists': []}
        self.assertFalse(unlock_playlist(config_empty, 'id1'))
        mock_print.assert_called_with("ℹ️ Playlist ID 'id1' not found in locked list or already unlocked.")

    @patch('spotify_tool.is_playlist_locked', return_value=False) # Assume not locked by default
    @patch('spotify_tool.spotipy.Spotify')
    def test_add_to_playlists_respects_lock(self, mock_sp_constructor, mock_is_locked):
        mock_sp = mock_sp_constructor.return_value
        config = {'locked_playlists': [{'id': 'locked_id', 'name': 'Locked Playlist'}]}
        
        # Setup mock_is_locked to simulate 'locked_id' being locked
        def side_effect_is_locked(cfg, pid):
            if pid == 'locked_id': return True
            return False
        mock_is_locked.side_effect = side_effect_is_locked

        playlist_ids_to_try = [('Locked Playlist', 'locked_id'), ('Unlocked Playlist', 'unlocked_id')]
        
        # Test without force
        results = add_to_playlists(mock_sp, 'track123', playlist_ids_to_try, config=config, force=False)
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], ('Locked Playlist', False, "Playlist is locked"))
        self.assertEqual(results[1], ('Unlocked Playlist', True, None)) # Assumes sp.playlist_add_items succeeds
        mock_sp.playlist_add_items.assert_called_once_with('unlocked_id', ['spotify:track:track123'])

        mock_sp.reset_mock()
        # Test with force=True
        results_forced = add_to_playlists(mock_sp, 'track123', playlist_ids_to_try, config=config, force=True)
        self.assertEqual(len(results_forced), 2)
        self.assertEqual(results_forced[0], ('Locked Playlist', True, None)) # Should attempt to add
        self.assertEqual(results_forced[1], ('Unlocked Playlist', True, None))
        self.assertEqual(mock_sp.playlist_add_items.call_count, 2)
        mock_sp.playlist_add_items.assert_any_call('locked_id', ['spotify:track:track123'])
        mock_sp.playlist_add_items.assert_any_call('unlocked_id', ['spotify:track:track123'])


class TestParseArguments(unittest.TestCase):
    # ... (keep existing tests for curate, suggest, old-favorites, etc.) ...
    @patch('sys.exit') 
    @patch('builtins.print') 
    def test_parse_curate_playlist_command(self, mock_print, mock_exit):
        with patch.object(sys, 'argv', ['spotify_tool.py', '--curate-playlist', 'source_playlist_url']): args = parse_arguments(); self.assertEqual(args['command'], 'curate_playlist'); # ... rest of assertions
        mock_exit.reset_mock()
        with patch.object(sys, 'argv', ['spotify_tool.py', '--curate-playlist']): parse_arguments(); mock_exit.assert_called_once_with(1) 
    
    @patch('sys.exit')
    @patch('builtins.print')
    def test_parse_suggest_genres_command(self, mock_print, mock_exit):
        with patch.object(sys, 'argv', ['spotify_tool.py', '--suggest-genres']): args = parse_arguments(); self.assertEqual(args, {'command': 'suggest_genres', 'time_range': 'medium_term'}); mock_exit.assert_not_called()
        mock_exit.reset_mock()
        with patch.object(sys, 'argv', ['spotify_tool.py', '--suggest-genres', '--time-range', 'invalid_range']): parse_arguments() ; mock_exit.assert_called_once_with(1) 

    @patch('sys.exit')
    @patch('builtins.print')
    def test_parse_old_favorites_command(self, mock_print, mock_exit):
        with patch.object(sys, 'argv', ['spotify_tool.py', '--old-favorites']): args = parse_arguments(); self.assertEqual(args, {'command': 'old_favorites', 'suggestions': 20}); mock_exit.assert_not_called()
        mock_exit.reset_mock()
        with patch.object(sys, 'argv', ['spotify_tool.py', '--old-favorites', '--suggestions', 'abc']): parse_arguments(); mock_exit.assert_called_once_with(1)

    @patch('sys.exit')
    @patch('builtins.print')
    def test_parse_lock_unlock_list_commands(self, mock_print, mock_exit):
        # Lock command
        with patch.object(sys, 'argv', ['spotify_tool.py', 'lock', 'playlist_id_123']):
            args = parse_arguments()
            self.assertEqual(args, {'command': 'lock_playlist', 'playlist_input': 'playlist_id_123'})
            mock_exit.assert_not_called()
        mock_exit.reset_mock()
        with patch.object(sys, 'argv', ['spotify_tool.py', 'lock']): # Missing arg
            parse_arguments()
            mock_exit.assert_called_once_with(1)
        mock_exit.reset_mock()

        # Unlock command
        with patch.object(sys, 'argv', ['spotify_tool.py', 'unlock', 'playlist_id_456']):
            args = parse_arguments()
            self.assertEqual(args, {'command': 'unlock_playlist', 'playlist_input': 'playlist_id_456'})
            mock_exit.assert_not_called()
        mock_exit.reset_mock()
        with patch.object(sys, 'argv', ['spotify_tool.py', 'unlock']): # Missing arg
            parse_arguments()
            mock_exit.assert_called_once_with(1)
        mock_exit.reset_mock()

        # List-locked command
        with patch.object(sys, 'argv', ['spotify_tool.py', 'list-locked']):
            args = parse_arguments()
            self.assertEqual(args, {'command': 'list_locked_playlists'})
            mock_exit.assert_not_called()

class TestMainLockUnlockListCommands(unittest.TestCase):
    @patch('spotify_tool.save_config')
    @patch('spotify_tool.lock_playlist')
    @patch('spotify_tool.spotipy.Spotify') # To mock sp.playlist()
    @patch('spotify_tool.extract_playlist_id')
    @patch('spotify_tool.setup_spotify_client')
    @patch('spotify_tool.load_config')
    @patch('builtins.print') # Capture print output from main
    def test_main_lock_playlist_success(self, mock_print_main, mock_load_config, mock_setup_sp, mock_extract_id, mock_sp_class, mock_lock_playlist, mock_save_config):
        mock_load_config.return_value = {"locked_playlists": []} # Sample config
        mock_sp_instance = MagicMock()
        mock_setup_sp.return_value = mock_sp_instance
        mock_extract_id.return_value = "valid_playlist_id"
        mock_sp_instance.playlist.return_value = {'name': 'Test Playlist Name'} # Mock sp.playlist() call
        mock_lock_playlist.return_value = True # Simulate successful lock

        with patch.object(sys, 'argv', ['spotify_tool.py', 'lock', 'some_playlist_url']):
            main()
        
        mock_extract_id.assert_called_once_with('some_playlist_url')
        mock_sp_instance.playlist.assert_called_once_with('valid_playlist_id')
        mock_lock_playlist.assert_called_once_with(mock_load_config.return_value, 'valid_playlist_id', 'Test Playlist Name')
        mock_save_config.assert_called_once_with(mock_load_config.return_value)

    @patch('spotify_tool.save_config')
    @patch('spotify_tool.unlock_playlist')
    @patch('spotify_tool.extract_playlist_id')
    @patch('spotify_tool.load_config')
    @patch('builtins.print')
    def test_main_unlock_playlist_success(self, mock_print_main, mock_load_config, mock_extract_id, mock_unlock_playlist, mock_save_config):
        mock_load_config.return_value = {"locked_playlists": [{'id': 'valid_id', 'name': 'Locked P'}]}
        mock_extract_id.return_value = "valid_id"
        mock_unlock_playlist.return_value = True

        with patch.object(sys, 'argv', ['spotify_tool.py', 'unlock', 'valid_id_or_url']):
            main()
        
        mock_extract_id.assert_called_once_with('valid_id_or_url')
        mock_unlock_playlist.assert_called_once_with(mock_load_config.return_value, 'valid_id')
        mock_save_config.assert_called_once_with(mock_load_config.return_value)

    @patch('spotify_tool.load_config')
    @patch('builtins.print')
    def test_main_list_locked_playlists_found(self, mock_print_main, mock_load_config):
        mock_config_data = {"locked_playlists": [{'id': 'id1', 'name': 'Playlist One'}, {'id': 'id2', 'name': 'Playlist Two'}]}
        mock_load_config.return_value = mock_config_data

        with patch.object(sys, 'argv', ['spotify_tool.py', 'list-locked']):
            main()
        
        # Check if print was called with expected output fragments
        mock_print_main.assert_any_call("🔒 Locked Playlists:")
        mock_print_main.assert_any_call(" 1. Playlist One (ID: id1)") # Note space before 1 due to :2d
        mock_print_main.assert_any_call(" 2. Playlist Two (ID: id2)") # Note space before 2

    @patch('spotify_tool.load_config')
    @patch('builtins.print')
    def test_main_list_locked_playlists_none(self, mock_print_main, mock_load_config):
        mock_load_config.return_value = {"locked_playlists": []}
        with patch.object(sys, 'argv', ['spotify_tool.py', 'list-locked']):
            main()
        mock_print_main.assert_any_call("ℹ️ No playlists are currently locked.")


if __name__ == '__main__':
    # To avoid issues with Textual's own signal handlers if tests are run via a Textual app entry point.
    # For direct `python test_spotify_tool.py` execution, this is fine.
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
