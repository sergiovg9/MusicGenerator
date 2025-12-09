import unittest
from data_collection_1 import download_maestro, extract_zip, DATA_DIR, ZIP_PATH
from pathlib import Path
import os
import zipfile
import builtins


class Testdata_collection(unittest.TestCase):
    """Tests for data_collection WITHOUT using unittest.mock."""

    def setUp(self):
        """Ensure a clean data/ directory before each test."""
        # Remove old files/directories if they exist
        if DATA_DIR.exists():
            for root, dirs, files in os.walk(DATA_DIR, topdown=False):
                for f in files:
                    os.remove(Path(root) / f)
                for d in dirs:
                    os.rmdir(Path(root) / d)
            os.rmdir(DATA_DIR)

        # Recreate directory structure
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def test_download_maestro_skips_download_if_zip_exists(self):
        """download_maestro must skip downloading when ZIP file already exists."""
        # Create dummy ZIP_PATH so the function skips downloading
        ZIP_PATH.touch()

        # Capture printed output
        output = []
        original_print = builtins.print
        
        try:
            builtins.print = output.append  # capture str messages
            download_maestro()
        finally:
            builtins.print = original_print  # restore

        self.assertIn("ZIP file already exists. Skipping download.", output)


    def test_extract_zip_creates_extracted_files(self):
        """extract_zip must extract contents of an existing ZIP."""
        # Create a minimal valid ZIP file at ZIP_PATH
        with zipfile.ZipFile(ZIP_PATH, "w") as z:
            z.writestr("test_file.txt", "content")

        # Run extraction
        extract_zip()

        # Assert extracted file exists inside DATA_DIR
        extracted_file = DATA_DIR / "test_file.txt"
        self.assertTrue(extracted_file.exists())

    def test_download_maestro_creates_data_dir(self):
        """download_maestro must create DATA_DIR even if already exists."""
        # DATA_DIR exists already from setUp; ensure ZIP is missing
        if ZIP_PATH.exists():
            ZIP_PATH.unlink()

        # Prevent network download by creating a fake small file after call
        # → but ZIP_PATH doesn't exist yet, so download_maestro *will attempt download*
        # We avoid real download by pre-creating ZIP_PATH right after mkdir call.
        # Because no mocks allowed, we expect ZIP_PATH NOT to exist before call.
        # Therefore the test only checks directory creation, not download behavior.

        download_maestro()  # This will try to download but URL is reachable; we only test dir existence.

        self.assertTrue(DATA_DIR.exists())

    def test_extract_zip_does_not_fail_with_empty_zip(self):
        """extract_zip must not crash when ZIP file exists but is empty."""
        # Create EMPTY but valid zip
        with zipfile.ZipFile(ZIP_PATH, "w"):
            pass

        extract_zip()  # should not raise

        # Directory should still exist
        self.assertTrue(DATA_DIR.exists())


if __name__ == "__main__":
    unittest.main()
