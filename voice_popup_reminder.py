# waifu_reminder.py
import os
import json
import hashlib
import queue
import threading
import time
import pytz
import numpy as np
import sounddevice as sd
import pyttsx3
import sqlite3
import schedule
import re # <-- Added for path sanitizing
from datetime import datetime, timedelta
from plyer import notification
import pdfplumber # <--- [FIX] Using pdfplumber
from io import BytesIO

# --- [MODIFIED] Import only what's needed ---
from config import (
    DATABASE_FILE,
    GOOGLE_SERVICE_ACCOUNT_FILE,
    GOOGLE_CALENDAR_TIMEZONE,
    LMS_USERNAME, # This script will run FOR this user
    SAVE_DIR      # Need this for the new file-reading
)
from ai_service import ai_client

tz = pytz.timezone(GOOGLE_CALENDAR_TIMEZONE)

# ... (ALERT_LEVELS, _beep, _init_tts, _speak, _process_alert, 
#      _worker, _ensure_worker, _reset_cache, _reset_cache_if_needed 
#      functions are all OK. Paste them here unchanged.) ...
#
# (The functions _beep to _reset_cache_if_needed are unchanged)
#
# ---------- BEEP (non-blocking) ----------
def _beep():
    try:
        freq = 880; duration = 0.25; samplerate = 44100
        t = np.linspace(0, duration, int(samplerate * duration), endpoint=False)
        wave = 0.3 * np.sin(2 * np.pi * freq * t)
        sd.play(wave, samplerate)
    except Exception as e:
        print(f"BEEP FAILED: {e}")

# ---------- TTS (BLOCKING) ----------
_tts_engine = None
def _init_tts():
    global _tts_engine
    if _tts_engine is not None: return
    try:
        _tts_engine = pyttsx3.init('sapi5')
        _tts_engine.setProperty('rate', 145); _tts_engine.setProperty('volume', 1.0)
        voices = _tts_engine.getProperty('voices')
        for v in voices:
            if 'zira' in v.name.lower():
                _tts_engine.setProperty('voice', v.id)
                print(f"TTS voice: {v.name} (Zira)"); return
        _tts_engine.setProperty('voice', voices[0].id)
        print(f"TTS voice: {voices[0].name} (default)")
    except Exception as e:
        print(f"TTS INIT FAILED: {e}"); _tts_engine = None

def _speak(text: str):
    global _tts_engine
    if not _tts_engine:
        _init_tts()
        if not _tts_engine:
            print("TTS NOT AVAILABLE – skipping voice"); return
    if len(text) > 200: text = text[:197] + "..."
    try:
        print(f"  → TTS SPEAKING: {text[:60]}...")
        _tts_engine.say(text); _tts_engine.runAndWait()
        print(f"  → TTS FINISHED")
    except Exception as e:
        print(f"TTS ERROR: {e}"); _tts_engine = None; _init_tts()

# ---------- ALERT PROCESSOR ----------
def _process_alert(title: str, msg: str, voice_line: str):
    try:
        notification.notify(
            title=title, message=msg + "\n\n(✿♡‿♡) Waifu loves you~",
            timeout=15, app_name="LMS Waifu"
        )
        print(f"  → POPUP: {title}")
    except Exception as e:
        print(f"POPUP FAILED: {e}")
    _speak(voice_line)
    try:
        _beep(); print("  → BEEP")
    except Exception as e:
        print(f"BEEP FAILED: {e}")

# ---------- NOTIFICATION QUEUE & WORKER ----------
_notification_queue = queue.Queue()
_worker_thread = None
def _worker():
    print("WAIFU NOTIFICATION WORKER STARTED")
    while True:
        try:
            item = _notification_queue.get(timeout=30)
            if item is None:
                print("WAIFU NOTIFICATION WORKER: Shutdown"); break
            title, msg, voice_line = item
            print(f"\nWAIFU ALERT: {title}")
            _process_alert(title, msg, voice_line)
            print(f"  → ALERT FINISHED: {title}")
            print("  → Waiting 30 s before next alert...")
            time.sleep(30)
            print("  → 30 s DONE! Ready for next!")
        except queue.Empty:
            print("WAIFU: No alerts in 30 s – still alive")
        except Exception as e:
            print(f"NOTIFICATION WORKER ERROR: {e}")
        finally:
            try: _notification_queue.task_done()
            except Exception: pass
    print("WAIFU NOTIFICATION WORKER STOPPED")

def _ensure_worker():
    global _worker_thread
    if _worker_thread is None or not _worker_thread.is_alive():
        print("WAIFU NOTIFICATION: Starting worker thread...")
        _worker_thread = threading.Thread(target=_worker, daemon=True)
        _worker_thread.start()
        time.sleep(1.0)

# ---------- CACHE ----------
_notified_cache = set()
_cache_valid_until = None
now_aware = lambda: datetime.now(tz) # Define now_aware here
def _reset_cache():
    global _notified_cache, _cache_valid_until
    _notified_cache.clear()
    _cache_valid_until = now_aware() + timedelta(hours=6)
    print("WAIFU: Cache reset (every 6 h)")

def _reset_cache_if_needed():
    now = now_aware()
    if _cache_valid_until is None or now > _cache_valid_until:
        _reset_cache()

# ---------- HELPER (MODIFIED) ----------
def _is_submitted(row):
    """Checks the database 'is_completed' flag."""
    return row['is_completed'] == 1

# ---------- [REMOVED] login_and_get_session() ----------
# This is redundant. We will read from the database and local files.

# ---------- [REWRITTEN] GET ASSIGNMENT CONTENT ----------
def get_assignment_content(user_id, lms_course_id, course_name):
    """
    Reads extracted text from the local .txt file scraped by the main app.
    Does NOT use Selenium.
    """
    print(f"   [Planner] Reading local content for course {lms_course_id}...")
    try:
        # Build the user-specific path, just like the scraper does
        safe_course_name = re.sub(r'[\\/*?:"<>|]', "_", course_name).strip()[:150]
        course_folder = os.path.join(SAVE_DIR, f"user_{user_id}", f"{lms_course_id}_{safe_course_name}")

        if not os.path.exists(course_folder):
            print(f"   [Planner] ⚠️ Content folder not found: {course_folder}")
            return "No content folder found."

        all_text = ""
        # Find all .txt files (which contain the extracted text)
        for filename in os.listdir(course_folder):
            if filename.lower().endswith(".txt"):
                txt_path = os.path.join(course_folder, filename)
                try:
                    with open(txt_path, "r", encoding="utf-8") as f:
                        all_text += f.read() + "\n\n"
                except Exception as e:
                    print(f"   [Planner] ⚠️ Failed to read {filename}: {e}")

        if not all_text:
            return "No text files found for this course."
            
        return all_text[:45000] # Return truncated content
        
    except Exception as e:
        print(f"   [Planner] ❌ Error in get_assignment_content: {e}")
        return f"Error reading local content: {e}"

# ---------- [REWRITTEN] AI ESTIMATE ----------
def ai_estimate_difficulty(user_id, lms_course_id, course_name, title, url):
    """Reads local content and sends it to AI for estimation."""
    content = get_assignment_content(user_id, lms_course_id, course_name)
    
    prompt = f"""
    Course: {course_name}
    Assignment: {title}
    Link: {url}
    CONTENT (from scraped files): {content}
    
    Based on the content, estimate the difficulty and time.
    Return ONLY JSON:
    {{
        "difficulty": 4,
        "hours": 10,
        "reason": "Requires coding and report",
        "breakdown": ["Read: 2h", "Code: 5h", "Write: 3h"]
    }}
    """
    try:
        response = ai_client.generate_content(prompt)
        text = response.text.strip()
        start = text.find('{')
        end = text.rfind('}') + 1
        return json.loads(text[start:end])
    except:
        return {
            "difficulty": 3, "hours": 6,
            "reason": "AI failed", "breakdown": ["Study: 6h"]
        }

# ---------- [REWRITTEN] GENERATE STUDY PLAN ----------
def generate_study_plan(user_id: int):
    """Generates a study plan for the *specific user*."""
    print(f"\nWAIFU v22 — FULL SYNC MODE ACTIVATED for user {user_id}")

    db = None
    try:
        # === 1. LOAD META + CALENDAR EVENTS ===
        db = sqlite3.connect(DATABASE_FILE)
        db.row_factory = sqlite3.Row
        cursor = db.cursor()
        
        # Get this user's Google Calendar ID
        user_row = cursor.execute("SELECT google_calendar_id FROM user WHERE id = ?", (user_id,)).fetchone()
        if not user_row:
            print(f"   [Planner] ❌ User {user_id} not found."); return
        
        user_calendar_id = user_row['google_calendar_id']
        print(f"   [Planner] Found user. Syncing to calendar: {user_calendar_id}")

        # Load user-specific meta file
        META_PATH = f"study_plan_meta_{user_id}.json"
        study_meta = {}
        if os.path.exists(META_PATH):
            try:
                with open(META_PATH, "r", encoding="utf-8") as f:
                    study_meta = json.load(f)
                print(f"   [Planner] Loaded {len(study_meta)} existing study events from meta.")
            except Exception as e:
                print(f"   [Planner] ⚠️ Failed to load meta: {e}")
                study_meta = {}

        service = build(
            'calendar', 'v3',
            credentials=service_account.Credentials.from_service_account_file(
                GOOGLE_SERVICE_ACCOUNT_FILE,
                scopes=['https://www.googleapis.com/auth/calendar']
            )
        )
        now = datetime.now(tz)

        # Get existing [STUDY] events
        events_result = service.events().list(
            calendarId=user_calendar_id, # <--- Use user's calendar
            timeMin=now.isoformat(),
            timeMax=(now + timedelta(days=60)).isoformat(),
            q="[STUDY]",
            singleEvents=True
        ).execute()
        existing_events = events_result.get('items', [])
        existing_event_ids = {e['id']: e for e in existing_events}

        # ... (Clean stale meta logic is OK) ...

        # === 2. LOAD DEADLINES (FOR THIS USER) ===
        cursor.execute("""
            SELECT c.id AS course_db_id, c.lms_course_id, c.name AS course_name, d.*
            FROM deadlines d
            JOIN courses c ON d.course_db_id = c.id
            WHERE d.user_id = ? AND d.parsed_iso_date IS NOT NULL
        """, (user_id,)) # <--- [FIX] Use correct join and filter
        
        rows = cursor.fetchall()
        db.close() # Done with DB

        tasks = []
        for row in rows:
            if _is_submitted(row): continue # Use the DB flag
            
            iso = row['parsed_iso_date'].strip().split('.')[0]
            if not iso.endswith('Z') and '+' not in iso: iso += 'Z'
            try: due = datetime.fromisoformat(iso.replace('Z', '+00:00')).astimezone(tz)
            except Exception: due = now + timedelta(days=3)

            ai = ai_estimate_difficulty(
                user_id, row['lms_course_id'], row['course_name'],
                row['time_string'], row['url'] or ""
            )
            hours = max(2, ai['hours'])
            task_key = f"waifu_task_user{user_id}_deadline{row['id']}" # Make key user-specific

            tasks.append({
                "key": task_key, "title": row['time_string'][:60],
                "course": row['course_name'], "due": due,
                "url": row['url'] or "", "hours": hours,
                "difficulty": ai['difficulty'], "reason": ai.get('reason', 'AI planned'),
                "breakdown": ai.get('breakdown', ['Study'])
            })

        # === 3. BUILD FREE SLOTS ===
        # Note: This is still using the GLOBAL calendar.
        # For a true multi-user app, get_free_slots would also need the user's calendar ID.
        # For now, we'll assume it's syncing to the main config calendar.
        slots = []
        free_slots = get_free_slots(days=30, calendar_id=user_calendar_id) # Pass user's calendar
        for start, end, duration in free_slots:
            slots.append((start, duration))
        print(f"   [Planner] Generated {len(slots)} study slots from user's calendar.")
        
        # ... (Rest of logic: 4. FULL SYNC, 5. DELETE STALE, 6. EXECUTE, 7. SAVE) ...
        # ... (This logic is complex but should work, just ensure it uses user_calendar_id) ...

    except Exception as e:
        print(f"   [Planner] ❌ FAILED to generate study plan: {e}")
        traceback.print_exc()
    finally:
        if db: db.close()

# ---------- [REWRITTEN] NOTIFY DEADLINES ----------
def notify_deadlines(user_id: int):
    """Checks deadlines for a *specific user*."""
    _ensure_worker()
    _reset_cache_if_needed()

    now = now_aware()
    print(f"\nWAIFU REMINDER v9 at {now.strftime('%H:%M')} for user {user_id}")

    db = None
    try:
        db = sqlite3.connect(DATABASE_FILE, timeout=10)
        db.row_factory = sqlite3.Row
        cur = db.cursor()
        
        # [FIX] Use correct join AND filter by user_id
        cur.execute("""
            SELECT c.name AS course_name, d.*
            FROM deadlines d
            JOIN courses c ON d.course_db_id = c.id
            WHERE d.user_id = ? AND d.parsed_iso_date IS NOT NULL
        """, (user_id,))
    except Exception as e:
        print(f"DB ERROR: {e}"); return 0

    alerts = []
    for row in cur.fetchall():
        if _is_submitted(row): # Use the DB flag
            continue
        
        iso = row['parsed_iso_date']
        try: due = datetime.fromisoformat(iso.replace('Z', '+00:00')).astimezone(tz)
        except Exception: continue

        time_left = due - now
        if time_left < timedelta(days=-90): continue # Ignore very old

        url = row['url']
        course = row['course_name']
        key = f"user{user_id}_deadline{row['id']}" # User-specific cache key
        
        if key in _notified_cache:
            continue

        due_str = due.strftime("%b %d, %Y")
        triggered = False

        for threshold, title, voice_tmpl in ALERT_LEVELS:
            if time_left <= threshold and (due >= now or threshold == timedelta(0)):
                days_left = max(0, time_left.days)
                msg = f"{course}\nDue in {days_left} day(s)!\n{url}"
                voice = voice_tmpl.format(course=course, days=days_left, due_date=due_str)
                alerts.append((title, msg, voice))
                print(f"ALERT [{title}]: {course} ({days_left}d)")
                triggered = True
                break
        
        if not triggered and time_left > timedelta(days=14):
             # This logic seems to be for future, but ALERT_LEVELS already has a 365-day catchall
             # This part might be redundant, but we'll leave it
             pass 

        _notified_cache.add(key)
    
    db.close()

    # ... (Queue processing logic is OK) ...

    return len(alerts)

# ---------- [REWRITTEN] SCHEDULER & MAIN ----------
stop_scheduler = threading.Event()

def start_reminder_scheduler(user_id: int):
    """Starts the scheduler for the given user_id."""
    print(f"ANIME WAIFU REMINDER v9 ACTIVE for user {user_id}!")

    _init_tts()
    _speak("Waifu system online. Ready to remind you!")
    time.sleep(3)

    notify_deadlines(user_id) # Run once on start
    schedule.every(5).minutes.do(notify_deadlines, user_id=user_id)
    # You can add the study plan schedule here too if you want
    # schedule.every().sunday.at("20:00").do(generate_study_plan, user_id=user_id)

    while not stop_scheduler.is_set():
        schedule.run_pending()
        time.sleep(1)

    # Graceful shutdown
    _notification_queue.put(None)
    if _worker_thread and _worker_thread.is_alive():
        _worker_thread.join(timeout=5)
    print(f"Waifu signed off for user {user_id}!")

def get_user_id_from_username(lms_username):
    """Finds the user_id from the DB based on the config username."""
    db = None
    try:
        db = sqlite3.connect(DATABASE_FILE)
        cursor = db.cursor()
        cursor.execute("SELECT id FROM user WHERE lms_username = ?", (lms_username,))
        user = cursor.fetchone()
        if user:
            return user[0]
        else:
            return None
    except Exception as e:
        print(f"WAIFU ❌: Could not find user {lms_username} in database: {e}")
        return None
    finally:
        if db: db.close()

# ---------- START ----------
if __name__ == "__main__":
    print("WAIFU: Starting up...")
    
    # 1. Find out which user this script is for
    target_username = LMS_USERNAME
    if not target_username:
        print("WAIFU ❌: LMS_USERNAME is not set in your .env/config.py file. Cannot start.")
        exit()
        
    print(f"WAIFU: This instance will run for user: {target_username}")
    user_id = get_user_id_from_username(target_username)
    
    if not user_id:
        print(f"WAIFU ❌: Could not find user '{target_username}' in the database.")
        print("WAIFU: Please register this user through the app first.")
        exit()
        
    # 2. Start the reminder scheduler for that user
    try:
        start_reminder_scheduler(user_id)
    except KeyboardInterrupt:
        print("\nWaifu: See you later! *poof*")
        stop_scheduler.set()