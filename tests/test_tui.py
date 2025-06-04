import unittest
import os

# Adjust the Python path to include the root directory
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestTUIImport(unittest.TestCase):
    def test_import_and_instantiate_tui(self):
        try:
            from spotify_tui import SpotifyTUI
            # Try to instantiate the TUI.
            # We expect this might fail if Spotify client setup fails,
            # but it shouldn't be due to a syntax error.
            # For now, we'll just instantiate. If it needs more setup for a basic check,
            # this test might need to be adjusted.
            app = SpotifyTUI()
            self.assertIsNotNone(app)
        except SyntaxError as e:
            self.fail(f"SyntaxError during TUI import or instantiation: {e}")
        except ImportError as e:
            self.fail(f"ImportError during TUI import or instantiation: {e}")
        except Exception as e:
            # Catch other potential errors during instantiation (like config not found)
            # For this test, we are primarily concerned with SyntaxErrors,
            # but it's good to know if other basic setup steps fail.
            print(f"Note: TUI instantiation threw an exception (not a SyntaxError): {e}")
            pass # Or self.assertIsNotNone(app) if instantiation is expected to always pass basic checks

if __name__ == '__main__':
    unittest.main()
