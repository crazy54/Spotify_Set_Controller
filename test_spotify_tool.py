import unittest
from unittest.mock import patch, MagicMock, call
import sys
import os

# Add the directory containing spotify_tool to sys.path
# This is to ensure that the spotify_tool module can be imported
# Assumes test_spotify_tool.py is in the same directory as spotify_tool.py
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Now import from spotify_tool
# We need to be careful if spotify_tool.py itself tries to load config on import
# For now, let's assume it's safe or mock things globally if needed.
from spotify_tool import (
    extract_playlist_id,
    copy_playlist,
    get_playlist_url_by_name,
    generate_playlist_qr_code,
    parse_arguments,
    # We might need spotipy.Spotify if we are not mocking all sp instances
)

# Basic Test for extract_playlist_id (can be a standalone function or in a class)
class TestExtractPlaylistId(unittest.TestCase):
    def test_full_url(self):
        self.assertEqual(extract_playlist_id('https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M'), '37i9dQZF1DXcBWIGoYBM5M')
        self.assertEqual(extract_playlist_id('https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M?si=something'), '37i9dQZF1DXcBWIGoYBM5M')

    def test_spotify_uri(self):
        self.assertEqual(extract_playlist_id('spotify:playlist:37i9dQZF1DXcBWIGoYBM5M'), '37i9dQZF1DXcBWIGoYBM5M')

    def test_plain_id(self):
        self.assertEqual(extract_playlist_id('37i9dQZF1DXcBWIGoYBM5M'), '37i9dQZF1DXcBWIGoYBM5M')
        # Test a slightly different valid ID
        self.assertEqual(extract_playlist_id('1z2x3c4v5b6n7m8l9k0j2p'), '1z2x3c4v5b6n7m8l9k0j2p')


    def test_invalid_inputs(self):
        self.assertIsNone(extract_playlist_id(''))
        self.assertIsNone(extract_playlist_id('http://google.com'))
        self.assertIsNone(extract_playlist_id('spotify:track:37i9dQZF1DXcBWIGoYBM5M')) # Track ID
        self.assertIsNone(extract_playlist_id('InvalidPlaylistID'))
        self.assertIsNone(extract_playlist_id('https://open.spotify.com/artist/4r6sFBIZ7WHrlgAbK01Dr0')) # Artist URL

    def test_id_like_string_but_not_id(self):
        # A string that is 22 chars but contains invalid chars for base62 or is otherwise not a valid ID format
        # The current regex r'([a-zA-Z0-9]{22})' is quite permissive.
        # This tests if it correctly identifies it as an ID if it matches the 22 char alphanumeric pattern.
        self.assertEqual(extract_playlist_id('abcdefghijklmnopqrstuv'), 'abcdefghijklmnopqrstuv')
        # And if it's not 22 chars, it should be None unless it matches a URL pattern (which it won't here)
        self.assertIsNone(extract_playlist_id('abcdefghijklmnopqrstu')) # 21 chars
        self.assertIsNone(extract_playlist_id('abcdefghijklmnopqrstuvw')) # 23 chars
        self.assertIsNone(extract_playlist_id('abcdefghijklmnopqrstu!')) # 22 chars with invalid char


class TestCopyPlaylist(unittest.TestCase):
    @patch('spotify_tool.extract_playlist_id')
    @patch('spotify_tool.spotipy.Spotify') # Patching the class
    def test_successful_copy_less_than_100_tracks(self, MockSpotify, mock_extract_id):
        mock_sp_instance = MockSpotify.return_value
        mock_extract_id.return_value = 'source_playlist_id'

        mock_sp_instance.me.return_value = {'id': 'test_user'}
        mock_sp_instance.user_playlist_create.return_value = {'id': 'new_playlist_id', 'name': 'New Playlist Name'}
        
        # Mock playlist_items to return a list of tracks
        track_uris = [f'spotify:track:track{i}' for i in range(5)] # 5 tracks
        mock_items = [{'track': {'uri': uri}} for uri in track_uris]
        mock_sp_instance.playlist_items.return_value = {
            'items': mock_items,
            'next': None # No pagination
        }

        copy_playlist(mock_sp_instance, 'source_url_or_id', 'New Playlist Name')

        mock_extract_id.assert_called_once_with('source_url_or_id')
        mock_sp_instance.me.assert_called_once()
        mock_sp_instance.user_playlist_create.assert_called_once_with('test_user', 'New Playlist Name')
        mock_sp_instance.playlist_add_items.assert_called_once_with('new_playlist_id', track_uris)

    @patch('spotify_tool.extract_playlist_id')
    @patch('spotify_tool.spotipy.Spotify')
    def test_successful_copy_more_than_100_tracks_pagination(self, MockSpotify, mock_extract_id):
        mock_sp_instance = MockSpotify.return_value
        mock_extract_id.return_value = 'source_playlist_id'
        mock_sp_instance.me.return_value = {'id': 'test_user'}
        mock_sp_instance.user_playlist_create.return_value = {'id': 'new_playlist_id', 'name': 'New Playlist Name'}

        # Simulate 150 tracks, requiring two batches for adding, and two pages for fetching
        tracks_page1 = [{'track': {'uri': f'spotify:track:track{i}'}} for i in range(100)]
        tracks_page2 = [{'track': {'uri': f'spotify:track:track{i+100}'}} for i in range(50)]
        
        all_track_uris = [t['track']['uri'] for t in tracks_page1] + [t['track']['uri'] for t in tracks_page2]

        # Mock sp.playlist_items for the first call
        mock_sp_instance.playlist_items.return_value = {
            'items': tracks_page1,
            'next': 'next_page_url' # Indicates more tracks
        }
        # Mock sp.next for the second call (pagination)
        mock_sp_instance.next.return_value = {
            'items': tracks_page2,
            'next': None
        }

        copy_playlist(mock_sp_instance, 'source_url_or_id', 'New Playlist Name')

        mock_extract_id.assert_called_once_with('source_url_or_id')
        mock_sp_instance.playlist_items.assert_called_once_with('source_playlist_id')
        mock_sp_instance.next.assert_called_once() # Ensure pagination was triggered for fetching
        mock_sp_instance.me.assert_called_once()
        mock_sp_instance.user_playlist_create.assert_called_once_with('test_user', 'New Playlist Name')
        
        # Check that playlist_add_items was called twice (batching)
        self.assertEqual(mock_sp_instance.playlist_add_items.call_count, 2)
        mock_sp_instance.playlist_add_items.assert_any_call('new_playlist_id', all_track_uris[:100])
        mock_sp_instance.playlist_add_items.assert_any_call('new_playlist_id', all_track_uris[100:])

    @patch('spotify_tool.extract_playlist_id')
    @patch('spotify_tool.spotipy.Spotify')
    def test_source_playlist_not_found(self, MockSpotify, mock_extract_id):
        mock_sp_instance = MockSpotify.return_value
        mock_extract_id.return_value = None # Simulate playlist ID not extracted

        copy_playlist(mock_sp_instance, 'invalid_source', 'New Playlist Name')

        mock_extract_id.assert_called_once_with('invalid_source')
        mock_sp_instance.playlist_items.assert_not_called()
        mock_sp_instance.user_playlist_create.assert_not_called()

    @patch('spotify_tool.extract_playlist_id')
    @patch('spotify_tool.spotipy.Spotify')
    def test_source_playlist_empty(self, MockSpotify, mock_extract_id):
        mock_sp_instance = MockSpotify.return_value
        mock_extract_id.return_value = 'source_playlist_id'
        mock_sp_instance.me.return_value = {'id': 'test_user'}
        mock_sp_instance.user_playlist_create.return_value = {'id': 'new_playlist_id', 'name': 'New Playlist Name'}
        
        mock_sp_instance.playlist_items.return_value = {'items': [], 'next': None}

        copy_playlist(mock_sp_instance, 'empty_source', 'New Playlist Name')

        mock_extract_id.assert_called_once_with('empty_source')
        mock_sp_instance.playlist_items.assert_called_once_with('source_playlist_id')
        mock_sp_instance.user_playlist_create.assert_called_once_with('test_user', 'New Playlist Name')
        mock_sp_instance.playlist_add_items.assert_not_called() # No tracks to add


class TestGetPlaylistUrlByName(unittest.TestCase):
    @patch('spotify_tool.get_user_playlists') # Mock the helper function directly
    @patch('spotify_tool.spotipy.Spotify') 
    def test_playlist_found_exact_match(self, MockSpotify, mock_get_user_playlists):
        mock_sp_instance = MockSpotify.return_value
        mock_get_user_playlists.return_value = {'Test Playlist': 'id123', 'Another Playlist': 'id456'}
        mock_sp_instance.playlist.return_value = {
            'name': 'Test Playlist', 
            'external_urls': {'spotify': 'http://spotify.com/playlist/id123'}
        }

        url = get_playlist_url_by_name(mock_sp_instance, 'Test Playlist')
        
        self.assertEqual(url, 'http://spotify.com/playlist/id123')
        mock_get_user_playlists.assert_called_once_with(mock_sp_instance)
        mock_sp_instance.playlist.assert_called_once_with('id123')

    @patch('spotify_tool.get_user_playlists')
    @patch('spotify_tool.spotipy.Spotify')
    def test_playlist_found_case_insensitive_match(self, MockSpotify, mock_get_user_playlists):
        mock_sp_instance = MockSpotify.return_value
        mock_get_user_playlists.return_value = {'Test Playlist': 'id123'}
        mock_sp_instance.playlist.return_value = {
            'name': 'Test Playlist', 
            'external_urls': {'spotify': 'http://spotify.com/playlist/id123'}
        }

        url = get_playlist_url_by_name(mock_sp_instance, 'test playlist')
        
        self.assertEqual(url, 'http://spotify.com/playlist/id123')
        mock_get_user_playlists.assert_called_once_with(mock_sp_instance)
        mock_sp_instance.playlist.assert_called_once_with('id123')

    @patch('spotify_tool.get_user_playlists')
    @patch('spotify_tool.spotipy.Spotify')
    def test_playlist_not_found(self, MockSpotify, mock_get_user_playlists):
        mock_sp_instance = MockSpotify.return_value
        mock_get_user_playlists.return_value = {'Another Playlist': 'id456'}

        url = get_playlist_url_by_name(mock_sp_instance, 'NonExistent Playlist')
        
        self.assertIsNone(url)
        mock_get_user_playlists.assert_called_once_with(mock_sp_instance)
        mock_sp_instance.playlist.assert_not_called()

    @patch('spotify_tool.get_user_playlists')
    @patch('spotify_tool.spotipy.Spotify')
    def test_multiple_case_insensitive_matches(self, MockSpotify, mock_get_user_playlists):
        mock_sp_instance = MockSpotify.return_value
        # Order might matter if the implementation picks the "first" based on dict iteration
        # For reliable testing, ensure the mock returns a consistent order if possible,
        # or check if any of the expected IDs is used.
        # Python 3.7+ dicts preserve insertion order.
        mock_get_user_playlists.return_value = {'My Playlist': 'id1', 'my playlist': 'id2'}
        
        # Let's assume 'My Playlist' (id1) would be "first" if iteration order is preserved
        # or if the logic specifically sorts/selects. The current code iterates and picks first.
        mock_sp_instance.playlist.side_effect = lambda pid: {
            'name': 'My Playlist' if pid == 'id1' else 'my playlist',
            'external_urls': {'spotify': f'http://spotify.com/playlist/{pid}'}
        }

        url = get_playlist_url_by_name(mock_sp_instance, 'my playlist') # Search term
        
        # The current implementation will find 'My Playlist' then 'my playlist' if dict order is as defined.
        # It will then pick the first one from the case_insensitive_matches dict.
        # Let's ensure the mock is set up so 'My Playlist' is found first by lowercasing.
        # The code as written will iterate through user_playlists.items().
        # If 'My Playlist' comes before 'my playlist' in this iteration, and both .lower() match,
        # the first one added to case_insensitive_matches will be 'My Playlist'.
        # Then, list(case_insensitive_matches.keys())[0] will be 'My Playlist'.
        
        # To make it deterministic, let's assume 'My Playlist' is the one whose URL is returned.
        # This means it expects 'id1' to be used for the sp.playlist call.
        expected_url = 'http://spotify.com/playlist/id1' # Corresponds to 'My Playlist'
        self.assertEqual(url, expected_url)
        mock_sp_instance.playlist.assert_called_once_with('id1')


class TestGeneratePlaylistQrCode(unittest.TestCase):
    @patch('spotify_tool.os.path.exists', return_value=True) # Mock os.path.exists if needed by underlying functions
    @patch('spotify_tool.qrcode.QRCode') # Mock the QRCode class
    @patch('spotify_tool.get_playlist_url_by_name')
    @patch('spotify_tool.spotipy.Spotify') # To provide a mock_sp_instance
    def test_input_name_url_found(self, MockSpotify, mock_get_url, MockQRCode, mock_os_exists):
        mock_sp_instance = MockSpotify.return_value
        mock_get_url.return_value = 'http://spotify.com/playlist/id123'
        
        mock_qr_instance = MockQRCode.return_value
        mock_img_instance = MagicMock()
        mock_qr_instance.make_image.return_value = mock_img_instance

        result_filename = generate_playlist_qr_code(mock_sp_instance, 'Test Playlist', output_filename='test_qr.png')

        mock_get_url.assert_called_once_with(mock_sp_instance, 'Test Playlist')
        MockQRCode.assert_called_once_with(version=1, error_correction='L', box_size=10, border=4)
        mock_qr_instance.add_data.assert_called_once_with('http://spotify.com/playlist/id123')
        mock_qr_instance.make.assert_called_once_with(fit=True)
        mock_qr_instance.make_image.assert_called_once_with(fill_color="black", back_color="white")
        mock_img_instance.save.assert_called_once_with('test_qr.png')
        self.assertEqual(result_filename, 'test_qr.png')

    @patch('spotify_tool.os.path.exists', return_value=True)
    @patch('spotify_tool.qrcode.QRCode')
    @patch('spotify_tool.get_playlist_url_by_name') # Still need to patch it, though not called
    @patch('spotify_tool.spotipy.Spotify')
    def test_input_is_url(self, MockSpotify, mock_get_url, MockQRCode, mock_os_exists):
        mock_sp_instance = MockSpotify.return_value
        
        mock_qr_instance = MockQRCode.return_value
        mock_img_instance = MagicMock()
        mock_qr_instance.make_image.return_value = mock_img_instance

        direct_url = 'http://direct.url/playlist'
        result_filename = generate_playlist_qr_code(mock_sp_instance, direct_url, output_filename='direct_qr.png')

        mock_get_url.assert_not_called()
        mock_qr_instance.add_data.assert_called_once_with(direct_url)
        mock_img_instance.save.assert_called_once_with('direct_qr.png')
        self.assertEqual(result_filename, 'direct_qr.png')

    @patch('spotify_tool.os.path.exists', return_value=True)
    @patch('spotify_tool.qrcode.QRCode')
    @patch('spotify_tool.get_playlist_url_by_name')
    @patch('spotify_tool.spotipy.Spotify')
    def test_name_input_url_not_found(self, MockSpotify, mock_get_url, MockQRCode, mock_os_exists):
        mock_sp_instance = MockSpotify.return_value
        mock_get_url.return_value = None # Simulate URL not found

        mock_qr_instance = MockQRCode.return_value

        result = generate_playlist_qr_code(mock_sp_instance, 'Unknown Playlist')

        mock_get_url.assert_called_once_with(mock_sp_instance, 'Unknown Playlist')
        MockQRCode.assert_not_called() # qrcode.QRCode() should not be instantiated
        mock_qr_instance.make_image.assert_not_called() # No image saving
        self.assertIsNone(result)


class TestParseArguments(unittest.TestCase):
    # Test --copy-playlist
    def test_parse_copy_playlist_long_form(self):
        with patch.object(sys, 'argv', ['spotify_tool.py', '--copy-playlist', 'source_id', 'New Name']):
            args = parse_arguments()
            self.assertEqual(args, {'command': 'copy_playlist', 'source': 'source_id', 'name': 'New Name'})

    def test_parse_copy_playlist_short_form(self):
        with patch.object(sys, 'argv', ['spotify_tool.py', '-cp', 'source_id', 'New Name']):
            args = parse_arguments()
            self.assertEqual(args, {'command': 'copy_playlist', 'source': 'source_id', 'name': 'New Name'})
            
    def test_parse_copy_playlist_missing_args(self):
        with patch.object(sys, 'argv', ['spotify_tool.py', '--copy-playlist', 'source_id']):
            with self.assertRaises(SystemExit): # Expect sys.exit(1)
                parse_arguments()

    # Test --get-playlist-url
    def test_parse_get_playlist_url_long_form(self):
        with patch.object(sys, 'argv', ['spotify_tool.py', '--get-playlist-url', 'My Favs']):
            args = parse_arguments()
            self.assertEqual(args, {'command': 'get_playlist_url', 'playlist_name': 'My Favs'})
            
    def test_parse_get_playlist_url_short_form(self):
        with patch.object(sys, 'argv', ['spotify_tool.py', '-gpu', 'My Favs']):
            args = parse_arguments()
            self.assertEqual(args, {'command': 'get_playlist_url', 'playlist_name': 'My Favs'})

    def test_parse_get_playlist_url_missing_args(self):
        with patch.object(sys, 'argv', ['spotify_tool.py', '--get-playlist-url']):
            with self.assertRaises(SystemExit):
                parse_arguments()

    # Test --generate-qr
    def test_parse_generate_qr_long_form_no_filename(self):
        with patch.object(sys, 'argv', ['spotify_tool.py', '--generate-qr', 'My Playlist Name']):
            args = parse_arguments()
            self.assertEqual(args, {'command': 'generate_qr', 
                                     'playlist_name_or_url': 'My Playlist Name', 
                                     'output_filename': 'playlist_qr.png'}) # Default filename

    def test_parse_generate_qr_short_form_with_filename(self):
        with patch.object(sys, 'argv', ['spotify_tool.py', '-qr', 'http://my.url/playlist', 'custom_name.png']):
            args = parse_arguments()
            self.assertEqual(args, {'command': 'generate_qr', 
                                     'playlist_name_or_url': 'http://my.url/playlist', 
                                     'output_filename': 'custom_name.png'})
            
    def test_parse_generate_qr_bad_extension_default_used_if_not_provided(self):
        with patch.object(sys, 'argv', ['spotify_tool.py', '-qr', 'My Playlist']):
             args = parse_arguments()
             self.assertEqual(args['output_filename'], 'playlist_qr.png')


    def test_parse_generate_qr_bad_extension_user_provided_is_kept(self):
        # The code has a slight logic issue in the test description vs implementation.
        # If user provides 'file.txt', it warns but uses 'file.txt'.
        # If user provides NO filename, it defaults to 'playlist_qr.png'.
        # The test name was a bit misleading from the original prompt.
        with patch.object(sys, 'argv', ['spotify_tool.py', '-qr', 'My Playlist', 'file.txt']):
             args = parse_arguments()
             self.assertEqual(args['output_filename'], 'file.txt')


    def test_parse_generate_qr_missing_playlist_arg(self):
        with patch.object(sys, 'argv', ['spotify_tool.py', '--generate-qr']):
            with self.assertRaises(SystemExit):
                parse_arguments()
    
    # Test other commands to ensure no regressions
    def test_parse_setup(self):
        with patch.object(sys, 'argv', ['spotify_tool.py', 'setup']):
            args = parse_arguments()
            self.assertEqual(args, {"command": "setup"})

    def test_parse_add_song_default_genre(self):
        with patch.object(sys, 'argv', ['spotify_tool.py', 'http://song.url']):
            args = parse_arguments()
            self.assertEqual(args, {"command": "add_song", "url": "http://song.url", "genre": None})

    def test_parse_add_song_with_genre(self):
        with patch.object(sys, 'argv', ['spotify_tool.py', 'http://song.url', '--genre', 'rock']):
            args = parse_arguments()
            self.assertEqual(args, {"command": "add_song", "url": "http://song.url", "genre": 'rock'})
            
    def test_parse_list_playlists_no_search(self):
        with patch.object(sys, 'argv', ['spotify_tool.py', '--list-playlists']):
            args = parse_arguments()
            self.assertEqual(args, {"command": "list_playlists", "search": None})

    def test_parse_list_playlists_with_search(self):
        with patch.object(sys, 'argv', ['spotify_tool.py', '-lp', 'My Search']):
            args = parse_arguments()
            self.assertEqual(args, {"command": "list_playlists", "search": "My Search"})
            
    def test_parse_list_playlists_search_term_is_not_another_flag(self):
        # Test that if a flag follows -lp, search term is None
        with patch.object(sys, 'argv', ['spotify_tool.py', '-lp', '-cp']): # -cp is another flag
            args = parse_arguments()
            # The implementation was updated to handle this:
            # if search_term and search_term.startswith("-"): search_term = None
            self.assertEqual(args, {"command": "list_playlists", "search": None})


if __name__ == '__main__':
    unittest.main()
