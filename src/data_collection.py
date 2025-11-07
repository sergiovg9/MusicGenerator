import zipfile
from pathlib import Path
from urllib.request import urlretrieve

URL = "https://storage.googleapis.com/magentadata/datasets/maestro/v3.0.0/maestro-v3.0.0-midi.zip"
DATA_DIR = Path("data")
MIDI_DIR = DATA_DIR / "midi"
ZIP_PATH = DATA_DIR / "maestro-v3.0.0-midi.zip"

def download_maestro():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if ZIP_PATH.exists():
        print("ZIP file already exists. Skipping download.")
    else:
        print(f"Downloading file from:\n{URL}")
        urlretrieve(URL, ZIP_PATH)
        print("Download complete.")

def extract_zip():
    print("Extracting ZIP file...")
    with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
        zip_ref.extractall(DATA_DIR)
    print("Extraction complete.")


if __name__ == "__main__":
    download_maestro()
    extract_zip()