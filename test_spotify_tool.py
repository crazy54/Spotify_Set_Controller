import unittest
from unittest.mock import patch, Mock, call
import sys
import os

# Adjust the path to import from the parent directory
# This allows the test script to find 'spotify_tool.py' when run from the 'tests' directory
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
    extract_playlist_id 
)
import datetime # For determine_new_playlist_name

class TestGetTrackDetails(unittest.TestCase):
    @patch('spotify_tool.spotipy.Spotify')
    def test_successful_fetch(self, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value
        
        track_ids = ["track1", "track2"]
        
        mock_sp.audio_features.side_effect = [
            [{'id': 'track1', 'danceability': 0.7}],
            [{'id': 'track2', 'danceability': 0.8}]
        ]
        mock_sp.track.side_effect = [
            {'id': 'track1', 'artists': [{'id': 'artist1', 'name': 'Artist One'}]},
            {'id': 'track2', 'artists': [{'id': 'artist2', 'name': 'Artist Two'}]}
        ]
        mock_sp.artist.side_effect = [
            {'id': 'artist1', 'genres': ['pop', 'rock']},
            {'id': 'artist2', 'genres': ['electronic', 'dance']}
        ]
        
        expected_details = [
            {
                'id': 'track1', 
                'audio_features': {'id': 'track1', 'danceability': 0.7}, 
                'artist_genres': ['pop', 'rock']
            },
            {
                'id': 'track2', 
                'audio_features': {'id': 'track2', 'danceability': 0.8}, 
                'artist_genres': ['dance', 'electronic'] # Order will be sorted by the function
            }
        ]
        
        result = get_track_details(mock_sp, track_ids)
        
        # Sort genres in expected for comparison as the function sorts them
        for item in expected_details:
            item['artist_genres'].sort()
            
        self.assertEqual(result, expected_details)
        mock_sp.audio_features.assert_has_calls([call(tracks=['track1']), call(tracks=['track2'])])
        mock_sp.track.assert_has_calls([call('track1'), call('track2')])
        mock_sp.artist.assert_has_calls([call('artist1'), call('artist2')])

    @patch('spotify_tool.spotipy.Spotify')
    def test_missing_audio_features(self, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value
        track_ids = ["track1"]
        
        mock_sp.audio_features.return_value = [None] # Simulate missing audio features
        mock_sp.track.return_value = {'id': 'track1', 'artists': [{'id': 'artist1', 'name': 'Artist One'}]}
        mock_sp.artist.return_value = {'id': 'artist1', 'genres': ['pop']}
        
        expected_details = [
            {
                'id': 'track1',
                'audio_features': None,
                'artist_genres': ['pop']
            }
        ]
        result = get_track_details(mock_sp, track_ids)
        self.assertEqual(result, expected_details)

    @patch('spotify_tool.spotipy.Spotify')
    def test_sp_track_fails(self, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value
        track_ids = ["track1", "track2"] # track1 will fail, track2 will succeed
        
        # audio_features will be called for both, as sp.track failure happens later for track1
        mock_sp.audio_features.side_effect = [
            [{'id': 'track1', 'danceability': 0.7}], 
            [{'id': 'track2', 'danceability': 0.8}]  
        ]
        # sp.track fails for track1, succeeds for track2
        mock_sp.track.side_effect = [
            None, 
            {'id': 'track2', 'artists': [{'id': 'artist2', 'name': 'Artist Two'}]}
        ]
        # sp.artist will only be called for track2's artist
        mock_sp.artist.return_value = {'id': 'artist2', 'genres': ['jazz']}
        
        expected_details = [
            { # Only track2 details should be present
                'id': 'track2',
                'audio_features': {'id': 'track2', 'danceability': 0.8},
                'artist_genres': ['jazz']
            }
        ]
        
        result = get_track_details(mock_sp, track_ids)
        self.assertEqual(result, expected_details)
        
        # Verify calls
        mock_sp.audio_features.assert_has_calls([call(tracks=['track1']), call(tracks=['track2'])])
        mock_sp.track.assert_has_calls([call('track1'), call('track2')])
        mock_sp.artist.assert_called_once_with('artist2') # Only for the successful track

    @patch('spotify_tool.spotipy.Spotify')
    def test_sp_artist_fails(self, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value
        track_ids = ["track1"]
        
        mock_sp.audio_features.return_value = [{'id': 'track1', 'danceability': 0.7}]
        mock_sp.track.return_value = {'id': 'track1', 'artists': [{'id': 'artist1', 'name': 'Artist One'}]}
        mock_sp.artist.side_effect = Exception("Simulated artist API error") # sp.artist fails
        
        expected_details = [
            {
                'id': 'track1',
                'audio_features': {'id': 'track1', 'danceability': 0.7},
                'artist_genres': [] # Empty as artist fetch failed
            }
        ]
        result = get_track_details(mock_sp, track_ids)
        self.assertEqual(result, expected_details)

    @patch('spotify_tool.spotipy.Spotify')
    def test_empty_track_ids(self, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value
        result = get_track_details(mock_sp, [])
        self.assertEqual(result, [])
        mock_sp.audio_features.assert_not_called()
        mock_sp.track.assert_not_called()
        mock_sp.artist.assert_not_called()

class TestAnalyzePlaylistMoodGenre(unittest.TestCase):
    @patch('spotify_tool.get_track_details')
    @patch('spotify_tool.spotipy.Spotify') 
    @patch('spotify_tool.extract_playlist_id')
    def test_successful_analysis(self, mock_extract_id, mock_sp_constructor, mock_get_track_details):
        mock_sp = mock_sp_constructor.return_value 
        playlist_id_or_url = "some_playlist_url"
        extracted_id = "playlist123"
        
        mock_extract_id.return_value = extracted_id
        
        mock_sp.playlist_items.side_effect = [
            {
                'items': [{'track': {'id': 'trackA', 'uri': 'uriA'}}, {'track': {'id': 'trackB', 'uri': 'uriB'}}],
                'next': 'next_page_url_fake' 
            }
        ]
        mock_sp.next.return_value = { 
            'items': [{'track': {'id': 'trackC', 'uri': 'uriC'}}],
            'next': None
        }

        mock_get_track_details.return_value = [
            {'id': 'trackA', 'audio_features': {'danceability': 0.5, 'energy': 0.6, 'valence': 0.7, 'tempo': 120.0, 'instrumentalness': 0.1, 'acousticness': 0.2, 'speechiness': 0.05, 'liveness': 0.15}, 'artist_genres': ['rock', 'pop', 'alternative rock']},
            {'id': 'trackB', 'audio_features': {'danceability': 0.7, 'energy': 0.8, 'valence': 0.9, 'tempo': 140.0, 'instrumentalness': 0.0, 'acousticness': 0.1, 'speechiness': 0.1, 'liveness': 0.25}, 'artist_genres': ['pop', 'electronic', 'dance pop']},
            {'id': 'trackC', 'audio_features': {'danceability': 0.6, 'energy': 0.7, 'valence': 0.8, 'tempo': 130.0, 'instrumentalness': 0.2, 'acousticness': 0.3, 'speechiness': 0.08, 'liveness': 0.20}, 'artist_genres': ['rock', 'indie rock', 'pop rock']}
        ]
        
        # Expected top genres are based on counts: pop:3, rock:3, alternative rock:1, electronic:1, dance pop:1, indie rock:1, pop rock:1
        # The function returns top 5, so order might vary for less frequent ones after the first few.
        expected_top_genres_set = {'pop', 'rock', 'alternative rock', 'electronic', 'dance pop'} # Using set for comparison of most_common(5)
        
        expected_analysis = {
            'average_audio_features': {
                'danceability': (0.5 + 0.7 + 0.6) / 3,
                'energy': (0.6 + 0.8 + 0.7) / 3,
                'valence': (0.7 + 0.9 + 0.8) / 3,
                'instrumentalness': (0.1 + 0.0 + 0.2) / 3,
                'acousticness': (0.2 + 0.1 + 0.3) / 3,
                'speechiness': (0.05 + 0.1 + 0.08) / 3,
                'liveness': (0.15 + 0.25 + 0.20) / 3,
                'tempo': (120.0 + 140.0 + 130.0) / 3
            },
            'seed_tracks': ['trackA', 'trackB', 'trackC'] 
        }
        
        result = analyze_playlist_mood_genre(mock_sp, playlist_id_or_url)
        
        mock_extract_id.assert_called_once_with(playlist_id_or_url)
        mock_sp.playlist_items.assert_called_once_with(extracted_id)
        mock_sp.next.assert_called_once()
        
        mock_get_track_details.assert_called_once_with(mock_sp, ['trackA', 'trackB', 'trackC'])
        
        self.assertEqual(result['seed_tracks'], expected_analysis['seed_tracks'])
        self.assertCountEqual(result['top_genres'], list(expected_top_genres_set)) # Compare as lists/sets
        for feature, avg_val in expected_analysis['average_audio_features'].items():
            self.assertAlmostEqual(result['average_audio_features'][feature], avg_val, places=5)

    @patch('spotify_tool.get_track_details')
    @patch('spotify_tool.spotipy.Spotify')
    @patch('spotify_tool.extract_playlist_id')
    def test_empty_playlist(self, mock_extract_id, mock_sp_constructor, mock_get_track_details):
        mock_sp = mock_sp_constructor.return_value
        playlist_id_or_url = "empty_playlist_url"
        extracted_id = "emptyPlaylist123"

        mock_extract_id.return_value = extracted_id
        mock_sp.playlist_items.return_value = {'items': [], 'next': None} 

        expected_return = {'top_genres': [], 'average_audio_features': {}, 'seed_tracks': []}
        result = analyze_playlist_mood_genre(mock_sp, playlist_id_or_url)

        self.assertEqual(result, expected_return)
        mock_get_track_details.assert_not_called()

    @patch('spotify_tool.get_track_details')
    @patch('spotify_tool.spotipy.Spotify')
    @patch('spotify_tool.extract_playlist_id')
    def test_get_track_details_returns_no_data(self, mock_extract_id, mock_sp_constructor, mock_get_track_details):
        mock_sp = mock_sp_constructor.return_value
        playlist_id_or_url = "some_playlist_url"
        extracted_id = "playlist123"

        mock_extract_id.return_value = extracted_id
        mock_sp.playlist_items.return_value = {
            'items': [{'track': {'id': 'trackA', 'uri': 'uriA'}}], 
            'next': None
        }
        mock_get_track_details.return_value = [] 

        expected_return = {'top_genres': [], 'average_audio_features': {}, 'seed_tracks': []}
        result = analyze_playlist_mood_genre(mock_sp, playlist_id_or_url)
        
        self.assertEqual(result, expected_return)
        mock_get_track_details.assert_called_once_with(mock_sp, ['trackA'])

    @patch('spotify_tool.spotipy.Spotify') 
    @patch('spotify_tool.extract_playlist_id')
    def test_extract_id_fails(self, mock_extract_id, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value 
        playlist_id_or_url = "invalid_playlist_url"
        mock_extract_id.return_value = None 

        expected_return = {'top_genres': [], 'average_audio_features': {}, 'seed_tracks': []}
        result = analyze_playlist_mood_genre(mock_sp, playlist_id_or_url)
        self.assertEqual(result, expected_return)
        mock_sp.playlist_items.assert_not_called() 

    @patch('spotify_tool.get_track_details')
    @patch('spotify_tool.spotipy.Spotify')
    @patch('spotify_tool.extract_playlist_id')
    def test_audio_features_missing_for_some_tracks(self, mock_extract_id, mock_sp_constructor, mock_get_track_details):
        mock_sp = mock_sp_constructor.return_value
        playlist_id_or_url = "mixed_playlist_url"
        extracted_id = "mixedPlaylist123"

        mock_extract_id.return_value = extracted_id
        mock_sp.playlist_items.return_value = {
            'items': [{'track': {'id': 'trackA', 'uri': 'uriA'}}, {'track': {'id': 'trackB', 'uri': 'uriB'}}],
            'next': None
        }
        mock_get_track_details.return_value = [
            {'id': 'trackA', 'audio_features': {'danceability': 0.5, 'energy': 0.6, 'valence': None, 'tempo': 120.0, 'instrumentalness': 0.1, 'acousticness': 0.2, 'speechiness': 0.05, 'liveness': 0.15}, 'artist_genres': ['rock']}, 
            {'id': 'trackB', 'audio_features': None, 'artist_genres': ['pop']} 
        ]
        
        result = analyze_playlist_mood_genre(mock_sp, playlist_id_or_url)
        
        self.assertAlmostEqual(result['average_audio_features']['danceability'], 0.5)
        self.assertAlmostEqual(result['average_audio_features']['energy'], 0.6)
        self.assertIsNone(result['average_audio_features'].get('valence')) 
        self.assertCountEqual(result['top_genres'], ['rock', 'pop']) 
        self.assertEqual(result['seed_tracks'], ['trackA', 'trackB'])

# Placeholder for other test classes
class TestGetRecommendations(unittest.TestCase):
    @patch('spotify_tool.spotipy.Spotify')
    def test_successful_recommendations(self, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value
        analysis_results = {
            'seed_tracks': ['trackA', 'trackB', 'trackC', 'trackD', 'trackE'],
            'top_genres': ['pop', 'rock', 'electronic', 'dance', 'hip hop'],
            'average_audio_features': {
                'danceability': 0.7, 'energy': 0.8, 'valence': 0.6, 'tempo': 120.0
            }
        }
        
        # Mock sp.track for fetching artist IDs from seed_tracks
        # Taking first 2 seed_tracks: trackA, trackB
        mock_sp.track.side_effect = [
            {'artists': [{'id': 'artistA'}]}, # For trackA
            {'artists': [{'id': 'artistB'}]}  # For trackB
        ]
        
        mock_sp.recommendations.return_value = {
            'tracks': [
                {'id': 'recTrack1', 'name': 'Rec Song 1'},
                {'id': 'recTrack2', 'name': 'Rec Song 2'}
            ]
        }
        
        expected_seed_tracks_uris = ['spotify:track:trackA', 'spotify:track:trackB']
        expected_seed_artist_ids = ['artistA', 'artistB'] # From the first 2 seed tracks
        # Seed genres will be 'pop', 'rock', 'electronic' to make total seeds = 2+2+1 = 5
        # (2 tracks, 2 artists from those tracks, 1 genre to fill up to 5)
        # Actually, the logic is: available_slots_for_artists = 5 - 2 (tracks) = 3. So 2 artists fit.
        # available_slots_for_genres = 5 - 2 (tracks) - 2 (artists) = 1. So 1 genre.
        expected_seed_genres = ['pop'] 
        
        expected_target_features = {
            'target_danceability': 0.7, 'target_energy': 0.8, 'target_valence': 0.6, 'target_tempo': 120.0
        }

        result = get_recommendations(mock_sp, analysis_results, limit=10)
        
        self.assertEqual(result, ['recTrack1', 'recTrack2'])
        mock_sp.track.assert_has_calls([call('trackA'), call('trackB')])
        mock_sp.recommendations.assert_called_once_with(
            seed_artists=expected_seed_artist_ids,
            seed_genres=expected_seed_genres,
            seed_tracks=expected_seed_tracks_uris,
            limit=10,
            **expected_target_features
        )

    @patch('spotify_tool.spotipy.Spotify')
    def test_minimal_analysis_data_only_seed_tracks(self, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value
        analysis_results = {
            'seed_tracks': ['trackX'],
            'top_genres': [], # No top genres
            'average_audio_features': {} # No audio features
        }
        
        mock_sp.track.return_value = {'artists': [{'id': 'artistX'}]} # For trackX
        
        mock_sp.recommendations.return_value = {'tracks': [{'id': 'recTrackOnlySeed'}]}
        
        expected_seed_tracks_uris = ['spotify:track:trackX']
        expected_seed_artist_ids = ['artistX']
        # No genres, total seeds = 1 track + 1 artist = 2.
        
        result = get_recommendations(mock_sp, analysis_results, limit=5)
        self.assertEqual(result, ['recTrackOnlySeed'])
        mock_sp.track.assert_called_once_with('trackX')
        mock_sp.recommendations.assert_called_once_with(
            seed_artists=expected_seed_artist_ids,
            seed_genres=None, # Explicitly None as top_genres was empty
            seed_tracks=expected_seed_tracks_uris,
            limit=5
            # No target features as average_audio_features was empty
        )

    @patch('spotify_tool.spotipy.Spotify')
    def test_recommendations_api_returns_no_tracks(self, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value
        analysis_results = {'seed_tracks': ['trackY'], 'top_genres': ['ambient'], 'average_audio_features': {}}
        
        mock_sp.track.return_value = {'artists': [{'id': 'artistY'}]}
        mock_sp.recommendations.return_value = {'tracks': []} # API returns no tracks
        
        result = get_recommendations(mock_sp, analysis_results)
        self.assertEqual(result, [])

    @patch('spotify_tool.spotipy.Spotify')
    def test_recommendations_api_raises_exception(self, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value
        analysis_results = {'seed_tracks': ['trackZ'], 'top_genres': ['blues'], 'average_audio_features': {}}
        
        mock_sp.track.return_value = {'artists': [{'id': 'artistZ'}]}
        mock_sp.recommendations.side_effect = Exception("Spotify API Error")
        
        result = get_recommendations(mock_sp, analysis_results)
        self.assertEqual(result, [])

    @patch('spotify_tool.spotipy.Spotify')
    def test_no_seeds_available(self, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value
        analysis_results = { # No seed_tracks, no top_genres
            'seed_tracks': [], 
            'top_genres': [], 
            'average_audio_features': {'danceability': 0.5}
        }
        
        result = get_recommendations(mock_sp, analysis_results)
        self.assertEqual(result, [])
        mock_sp.track.assert_not_called()
        mock_sp.recommendations.assert_not_called()

    @patch('spotify_tool.spotipy.Spotify')
    def test_seed_trimming_logic(self, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value
        # Provide more than 5 potential seeds to test trimming
        analysis_results = {
            'seed_tracks': ['t1', 't2', 't3'], # 3 tracks
            'top_genres': ['g1', 'g2', 'g3', 'g4'], # 4 genres
            'average_audio_features': {}
        }
        
        # Mock sp.track for the first 2 seed tracks (t1, t2) as per current logic in get_recommendations
        mock_sp.track.side_effect = [
            {'artists': [{'id': 'a1'}]}, # For t1
            {'artists': [{'id': 'a2'}]}  # For t2
            # sp.track for t3 won't be called if only first 2 tracks are used for artist seeds
        ]
        
        mock_sp.recommendations.return_value = {'tracks': [{'id': 'rec1'}]}

        # Expected seeds after trimming:
        # final_seed_track_uris = ['spotify:track:t1', 'spotify:track:t2'] (2)
        # final_seed_artist_ids = ['a1', 'a2'] (2 artists from these tracks)
        # current_seeds_count = 2 (tracks) + 2 (artists) = 4
        # available_slots_for_genres = 5 - 4 = 1
        # final_seed_genre_list = ['g1'] (1)
        # Total seeds = 2 + 2 + 1 = 5

        get_recommendations(mock_sp, analysis_results)
        
        mock_sp.recommendations.assert_called_once()
        args, kwargs = mock_sp.recommendations.call_args
        
        self.assertCountEqual(kwargs['seed_tracks'], ['spotify:track:t1', 'spotify:track:t2'])
        self.assertCountEqual(kwargs['seed_artists'], ['a1', 'a2'])
        self.assertCountEqual(kwargs['seed_genres'], ['g1'])


class TestPlaylistHelpers(unittest.TestCase):
    @patch('spotify_tool.spotipy.Spotify')
    @patch('spotify_tool.datetime.date') # Mock date object within datetime module
    def test_determine_new_playlist_name(self, mock_date, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value
        mock_today = datetime.date(2023, 10, 26)
        mock_date.today.return_value = mock_today
        date_str = "2023-10-26"

        # Scenario 1: new_name_provided
        name = determine_new_playlist_name(mock_sp, "source_id", "My Custom Name")
        self.assertEqual(name, "My Custom Name")

        # Scenario 2: No new_name_provided, sp.playlist succeeds
        mock_sp.playlist.return_value = {'name': 'Old Playlist'}
        name = determine_new_playlist_name(mock_sp, "source_id_good")
        self.assertEqual(name, f"Curated - Old Playlist - {date_str}")
        mock_sp.playlist.assert_called_once_with("source_id_good")

        # Scenario 3: No new_name_provided, sp.playlist fails
        mock_sp.reset_mock() # Reset call counts for sp.playlist
        mock_sp.playlist.side_effect = Exception("API error")
        name = determine_new_playlist_name(mock_sp, "source_id_bad")
        self.assertEqual(name, f"My Curated Playlist - {date_str}")
        mock_sp.playlist.assert_called_once_with("source_id_bad")
        
        # Scenario 4: No new_name_provided, sp.playlist returns no name
        mock_sp.reset_mock()
        mock_sp.playlist.return_value = {'id': 'some_id'} # No 'name' key
        mock_sp.playlist.side_effect = None # Clear side_effect
        name = determine_new_playlist_name(mock_sp, "source_id_no_name")
        self.assertEqual(name, f"My Curated Playlist - {date_str}")
        mock_sp.playlist.assert_called_once_with("source_id_no_name")


    @patch('spotify_tool.spotipy.Spotify')
    def test_create_empty_playlist_successful(self, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value
        mock_sp.me.return_value = {'id': 'user123'}
        mock_sp.user_playlist_create.return_value = {'id': 'newPlaylistId', 'name': 'Test Playlist'}
        
        playlist_id = create_empty_playlist(mock_sp, "Test Playlist")
        self.assertEqual(playlist_id, "newPlaylistId")
        mock_sp.me.assert_called_once()
        mock_sp.user_playlist_create.assert_called_once_with(user='user123', name='Test Playlist', public=True)

    @patch('spotify_tool.spotipy.Spotify')
    def test_create_empty_playlist_fails(self, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value
        mock_sp.me.return_value = {'id': 'user123'}
        mock_sp.user_playlist_create.side_effect = Exception("Creation failed")
        
        playlist_id = create_empty_playlist(mock_sp, "Failed Playlist")
        self.assertIsNone(playlist_id)

    @patch('spotify_tool.spotipy.Spotify')
    def test_populate_playlist_with_tracks(self, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value
        
        # Test < 100 tracks
        track_ids_small = [f"track{i}" for i in range(50)]
        count = populate_playlist_with_tracks(mock_sp, "playlist1", track_ids_small)
        self.assertEqual(count, 50)
        expected_uris_small = [f"spotify:track:track{i}" for i in range(50)]
        mock_sp.playlist_add_items.assert_called_once_with("playlist1", expected_uris_small)
        
        mock_sp.reset_mock()
        
        # Test > 100 tracks (e.g., 150 tracks -> 2 batches)
        track_ids_large = [f"track{i}" for i in range(150)]
        count = populate_playlist_with_tracks(mock_sp, "playlist2", track_ids_large)
        self.assertEqual(count, 150)
        expected_uris_batch1 = [f"spotify:track:track{i}" for i in range(100)]
        expected_uris_batch2 = [f"spotify:track:track{i}" for i in range(100, 150)]
        mock_sp.playlist_add_items.assert_has_calls([
            call("playlist2", expected_uris_batch1),
            call("playlist2", expected_uris_batch2)
        ])
        self.assertEqual(mock_sp.playlist_add_items.call_count, 2)

        mock_sp.reset_mock()

        # Test with 0 tracks
        count = populate_playlist_with_tracks(mock_sp, "playlist3", [])
        self.assertEqual(count, 0)
        mock_sp.playlist_add_items.assert_not_called()
        
        mock_sp.reset_mock()

        # Test with only None/empty track_ids
        count = populate_playlist_with_tracks(mock_sp, "playlist4", [None, "", None])
        self.assertEqual(count, 0)
        mock_sp.playlist_add_items.assert_not_called()


    @patch('spotify_tool.spotipy.Spotify')
    def test_populate_playlist_one_batch_fails(self, mock_sp_constructor):
        mock_sp = mock_sp_constructor.return_value
        track_ids = [f"track{i}" for i in range(150)] # 2 batches
        
        # First batch succeeds, second fails
        mock_sp.playlist_add_items.side_effect = [
            Mock(), # Simulates successful call for the first batch
            Exception("Failed to add second batch")
        ]
        
        count = populate_playlist_with_tracks(mock_sp, "playlist_err", track_ids)
        # Only tracks from the first successful batch should be counted
        self.assertEqual(count, 100) 
        self.assertEqual(mock_sp.playlist_add_items.call_count, 2)


class TestCuratePlaylistCommand(unittest.TestCase):
    @patch('spotify_tool.populate_playlist_with_tracks')
    @patch('spotify_tool.create_empty_playlist')
    @patch('spotify_tool.determine_new_playlist_name')
    @patch('spotify_tool.get_recommendations')
    @patch('spotify_tool.analyze_playlist_mood_genre')
    @patch('spotify_tool.extract_playlist_id')
    @patch('spotify_tool.spotipy.Spotify') # To mock the sp instance passed to the command
    def test_curate_playlist_successful_flow(self, mock_sp_constructor, mock_extract, mock_analyze, mock_recommend, mock_determine_name, mock_create_playlist, mock_populate):
        mock_sp = mock_sp_constructor.return_value
        source_url = "http://source.playlist.url"
        provided_new_name = "My New Curated Mix"

        mock_extract.return_value = "source_playlist_123"
        mock_analyze.return_value = {'seed_tracks': ['s1'], 'top_genres': ['g1'], 'average_audio_features': {'energy': 0.7}}
        mock_recommend.return_value = ['rec_track1', 'rec_track2']
        mock_determine_name.return_value = "Final Playlist Name"
        mock_create_playlist.return_value = "new_playlist_id_abc"
        mock_populate.return_value = 2 # Number of tracks added

        curate_playlist_command(mock_sp, source_url, provided_new_name)

        mock_extract.assert_called_once_with(source_url)
        mock_analyze.assert_called_once_with(mock_sp, "source_playlist_123")
        mock_recommend.assert_called_once_with(mock_sp, mock_analyze.return_value, limit=20)
        mock_determine_name.assert_called_once_with(mock_sp, "source_playlist_123", provided_new_name)
        mock_create_playlist.assert_called_once_with(mock_sp, "Final Playlist Name")
        mock_populate.assert_called_once_with(mock_sp, "new_playlist_id_abc", ['rec_track1', 'rec_track2'])

    @patch('spotify_tool.extract_playlist_id')
    @patch('spotify_tool.spotipy.Spotify')
    def test_curate_playlist_extract_id_fails(self, mock_sp_constructor, mock_extract):
        mock_sp = mock_sp_constructor.return_value
        mock_extract.return_value = None # Simulate extract_playlist_id failing

        # We expect the command to print an error and return early.
        # To capture print statements, we can temporarily redirect stdout, but for simplicity,
        # we'll just ensure no further functions are called.
        with patch('spotify_tool.analyze_playlist_mood_genre') as mock_analyze: # Mock to check it's not called
            curate_playlist_command(mock_sp, "invalid_url")
            mock_analyze.assert_not_called()
            
    @patch('spotify_tool.get_recommendations')
    @patch('spotify_tool.analyze_playlist_mood_genre')
    @patch('spotify_tool.extract_playlist_id')
    @patch('spotify_tool.spotipy.Spotify')
    def test_curate_playlist_analysis_fails(self, mock_sp_constructor, mock_extract, mock_analyze, mock_recommend):
        mock_sp = mock_sp_constructor.return_value
        mock_extract.return_value = "source_id"
        mock_analyze.return_value = {} # Simulate analysis returning insufficient data

        curate_playlist_command(mock_sp, "some_url")
        mock_recommend.assert_not_called() # Recommendations should not be called

    @patch('spotify_tool.determine_new_playlist_name')
    @patch('spotify_tool.get_recommendations')
    @patch('spotify_tool.analyze_playlist_mood_genre')
    @patch('spotify_tool.extract_playlist_id')
    @patch('spotify_tool.spotipy.Spotify')
    def test_curate_playlist_recommendations_fail(self, mock_sp_constructor, mock_extract, mock_analyze, mock_recommend, mock_determine_name):
        mock_sp = mock_sp_constructor.return_value
        mock_extract.return_value = "source_id"
        mock_analyze.return_value = {'seed_tracks': ['s1']}
        mock_recommend.return_value = [] # Simulate no recommendations

        curate_playlist_command(mock_sp, "some_url")
        mock_determine_name.assert_not_called() # Determining name should not be called

    @patch('spotify_tool.populate_playlist_with_tracks')
    @patch('spotify_tool.create_empty_playlist')
    @patch('spotify_tool.determine_new_playlist_name')
    @patch('spotify_tool.get_recommendations')
    @patch('spotify_tool.analyze_playlist_mood_genre')
    @patch('spotify_tool.extract_playlist_id')
    @patch('spotify_tool.spotipy.Spotify')
    def test_curate_playlist_create_playlist_fails(self, mock_sp_constructor, mock_extract, mock_analyze, mock_recommend, mock_determine_name, mock_create_playlist, mock_populate):
        mock_sp = mock_sp_constructor.return_value
        mock_extract.return_value = "source_id"
        mock_analyze.return_value = {'seed_tracks': ['s1']}
        mock_recommend.return_value = ['rec1']
        mock_determine_name.return_value = "A Good Name"
        mock_create_playlist.return_value = None # Simulate playlist creation failing

        curate_playlist_command(mock_sp, "some_url")
        mock_populate.assert_not_called() # Populating should not be called


class TestParseArguments(unittest.TestCase):
    @patch('sys.exit') # Mock sys.exit to prevent test termination
    @patch('builtins.print') # Mock print to suppress output during tests
    def test_parse_curate_playlist_command(self, mock_print, mock_exit):
        # Test case 1: --curate-playlist <source_playlist_id_or_url>
        with patch.object(sys, 'argv', ['spotify_tool.py', '--curate-playlist', 'source_playlist_url']):
            args = parse_arguments()
            self.assertEqual(args['command'], 'curate_playlist')
            self.assertEqual(args['source_playlist_id_or_url'], 'source_playlist_url')
            self.assertIsNone(args['new_name'])
            mock_exit.assert_not_called()

        mock_exit.reset_mock()
        # Test case 2: --curate-playlist <source_playlist_id_or_url> --new-name <playlist_name>
        with patch.object(sys, 'argv', ['spotify_tool.py', '--curate-playlist', 'source_playlist_url', '--new-name', 'New Playlist Name']):
            args = parse_arguments()
            self.assertEqual(args['command'], 'curate_playlist')
            self.assertEqual(args['source_playlist_id_or_url'], 'source_playlist_url')
            self.assertEqual(args['new_name'], 'New Playlist Name')
            mock_exit.assert_not_called()

        mock_exit.reset_mock()
        # Test case 3: -cpL <source_playlist_id_or_url> --new-name <playlist_name> (alias)
        with patch.object(sys, 'argv', ['spotify_tool.py', '-cpL', 'another_source_url', '--new-name', 'Another Name']):
            args = parse_arguments()
            self.assertEqual(args['command'], 'curate_playlist')
            self.assertEqual(args['source_playlist_id_or_url'], 'another_source_url')
            self.assertEqual(args['new_name'], 'Another Name')
            mock_exit.assert_not_called()
            
        mock_exit.reset_mock()
        # Test case 4: --curate-playlist (missing source_playlist_id_or_url)
        with patch.object(sys, 'argv', ['spotify_tool.py', '--curate-playlist']):
            parse_arguments()
            mock_exit.assert_called_once_with(1) # Expect sys.exit(1)
            
        mock_exit.reset_mock()
        # Test case 5: --curate-playlist <source> --new-name (missing name for --new-name)
        with patch.object(sys, 'argv', ['spotify_tool.py', '--curate-playlist', 'source_url', '--new-name']):
            parse_arguments()
            mock_exit.assert_called_once_with(1)

        mock_exit.reset_mock()
        # Test case 6: --curate-playlist <source> some_other_arg (unexpected argument)
        with patch.object(sys, 'argv', ['spotify_tool.py', '--curate-playlist', 'source_url', 'unexpected_arg']):
            parse_arguments()
            mock_exit.assert_called_once_with(1)
            
        mock_exit.reset_mock()
        # Test case 7: --curate-playlist <source> -x (unknown flag after source)
        with patch.object(sys, 'argv', ['spotify_tool.py', '--curate-playlist', 'source_url', '-x']):
            parse_arguments()
            mock_exit.assert_called_once_with(1)


    # It's good practice to also test a non-curate-playlist command to ensure it's not affected,
    # and the main usage message if no valid command is given.
    @patch('sys.exit')
    @patch('builtins.print')
    def test_parse_other_commands_and_usage(self, mock_print, mock_exit):
        # Test setup command
        with patch.object(sys, 'argv', ['spotify_tool.py', 'setup']):
            args = parse_arguments()
            self.assertEqual(args['command'], 'setup')
            mock_exit.assert_not_called()

        mock_exit.reset_mock()
        # Test no command (should print usage and exit)
        with patch.object(sys, 'argv', ['spotify_tool.py']):
            parse_arguments()
            # Check that usage was printed (first print call contains "Usage:")
            self.assertIn("Usage:", mock_print.call_args_list[0][0][0])
            mock_exit.assert_called_once_with(1)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
