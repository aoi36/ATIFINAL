# config.py
import os
from dotenv import load_dotenv

load_dotenv()
print("Loading configuration...")

# --- Absolute Paths ---
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(APP_ROOT, 'lms_data.db')
SAVE_DIR = os.path.join(APP_ROOT, "courses_data")
INDEX_DIR = os.path.join(APP_ROOT, "search_index")
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'uploads')
MEET_RECORDING_DIR = os.path.join(APP_ROOT, "meet_recordings") # Renamed from ZOOM
STATE_FILE = os.path.join(APP_ROOT, 'scrape_state.json')

# --- Credentials ---
LMS_USERNAME = os.environ.get("LMS_USERNAME")
LMS_PASSWORD = os.environ.get("LMS_PASSWORD")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GMAIL_SENDER = os.environ.get("GMAIL_SENDER")
SECRET_KEY = "63f4945d921d599f27ae4fdf5bada3f1"
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
GMAIL_RECEIVER = os.environ.get("GMAIL_RECEIVER")

# --- Scraper Config ---
REQUESTS_TIMEOUT = 30
MAX_SUBPAGES = None
MAX_TEXT_LENGTH_FOR_SUMMARY = 75000
ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.docx', '.pptx'}

# --- Create Folders ---
for folder in [SAVE_DIR, INDEX_DIR, UPLOAD_FOLDER, MEET_RECORDING_DIR]:
    os.makedirs(folder, exist_ok=True)

if not LMS_USERNAME or not LMS_PASSWORD:
    print("❌ ERROR: LMS_USERNAME and LMS_PASSWORD must be set in the .env file.")
    exit()