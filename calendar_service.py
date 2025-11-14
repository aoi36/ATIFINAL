import os
import json
import re  # <-- Added missing import
import hashlib
import threading
import time
import pytz
import base64 # <-- Added missing import
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import BatchHttpRequest
from google.oauth2 import service_account
import sqlite3

# Import from config.py and database.py
from config import (
    DATABASE_FILE, GOOGLE_SERVICE_ACCOUNT_FILE, GOOGLE_CALENDAR_TIMEZONE, 
    GOOGLE_CLEANUP_DELETED, GOOGLE_REMINDER_MINUTES, GOOGLE_EVENT_DURATION_MIN, 
    SAVE_DIR
)
from database import get_db # We use this to connect in a thread

# ------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------

def _event_key(course_folder: str, deadline_row) -> str:
    """Generates a unique, stable ID for a deadline event."""
    # --- [THE FIX] ---
    # sqlite3.Row objects are accessed by key like a dictionary,
    # but do not have a .get() method. We'll use dict(deadline_row)
    # to safely convert it first.
    row_dict = dict(deadline_row)
    url = row_dict.get("url", "")
    time_str = row_dict.get("time_string", "")
    # --- [END FIX] ---
    
    key_str = f"{course_folder}|{url}|{time_str}"
    return hashlib.sha256(key_str.encode()).hexdigest()[:32]

def _load_meta(course_path: str) -> dict:
    """Loads the calendar_meta.json for a specific course."""
    meta_file = os.path.join(course_path, "calendar_meta.json")
    if os.path.exists(meta_file):
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def _save_meta(course_path: str, meta: dict):
    """Saves the calendar_meta.json for a specific course."""
    if not meta:
        return
    meta_file = os.path.join(course_path, "calendar_meta.json")
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

def _retry_google(callable_obj, **kwargs):
    """A retry wrapper for flaky Google API calls."""
    for attempt in range(4):
        try:
            return callable_obj(**kwargs).execute()
        except HttpError as e:
            if e.resp.status in (500, 503, 429) and attempt < 3:
                time.sleep((2 ** attempt) + 0.1)
                continue
            raise
    return None

def _is_done(deadline_row):
    """
    Checks if a deadline is marked as completed in the database.
    """
    return deadline_row["is_completed"] == 1

# ------------------------------------------------------------------
# MAIN SYNC FUNCTION (MODIFIED FOR MULTI-USER)
# ------------------------------------------------------------------

def sync_all_deadlines(user_id: int):
    """
    Syncs all uncompleted deadlines for a *specific user*
    to their personal Google Calendar.
    """
    print(f"\n[Calendar] Starting SYNC for user_id: {user_id}...")
    
    db = None
    try:
        # 1. Connect to DB (must create a new connection for this thread)
        db = sqlite3.connect(DATABASE_FILE, detect_types=sqlite3.PARSE_DECLTYPES, timeout=10)
        db.row_factory = sqlite3.Row
        cursor = db.cursor()

        # 2. Get this user's Google Calendar ID from the 'user' table
        user_row = cursor.execute("SELECT google_calendar_id FROM user WHERE id = ?", (user_id,)).fetchone()
        if not user_row:
            print(f"[Calendar] ❌ Error: User {user_id} not found.")
            return
        
        user_calendar_id = user_row['google_calendar_id']
        if not user_calendar_id:
            print(f"[Calendar] ⚠️ User {user_id} has no Google Calendar ID set. Using 'primary'.")
            user_calendar_id = 'primary'
        
        print(f"   [Calendar] Syncing to calendar: {user_calendar_id}")

        # 3. Get Google API Service
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_FILE,
            scopes=["https://www.googleapis.com/auth/calendar"]
        )
        service = build("calendar", "v3", credentials=creds)

    except Exception as e:
        print(f"[Calendar] ❌ Setup error: {e}")
        if db: db.close()
        return

    global_meta = {}
    seen_keys = set()
    batch = service.new_batch_http_request()
    course_metas = {}
    synced = 0
    tz = pytz.timezone(GOOGLE_CALENDAR_TIMEZONE)
    now = datetime.now(tz)

    # 4. [FIXED SQL] Fetch deadlines *only* for this user_id
    cursor.execute("""
        SELECT c.name AS course_name, c.lms_course_id, d.*
        FROM deadlines d
        JOIN courses c ON d.course_db_id = c.id
        WHERE d.user_id = ? 
          AND d.parsed_iso_date IS NOT NULL
          AND d.url IS NOT NULL
    """, (user_id,))
    
    rows_to_sync = cursor.fetchall()
    db.close() # We're done with the database

    for row in rows_to_sync:
        if _is_done(row): # Use the new DB-based check
            continue

        # 5. [FIXED PATH] Build the correct user-specific path
        lms_course_id = row['lms_course_id']
        safe_course_name = re.sub(r'[\\/*?:"<>|]', "_", row['course_name']).strip()[:150]
        course_folder = os.path.join(SAVE_DIR, f"user_{user_id}", f"{lms_course_id}_{safe_course_name}")
        os.makedirs(course_folder, exist_ok=True) # Ensure it exists
        # --- [END FIXED PATH] ---

        course_meta = _load_meta(course_folder)
        course_metas[course_folder] = course_meta
        global_meta.update(course_meta)

        iso = row['parsed_iso_date']
        try:
            due = datetime.fromisoformat(iso.replace('Z', '+00:00')).astimezone(tz)
        except Exception as e:
            print(f"   [Calendar] Invalid date: {iso} → {e}")
            continue

        status = "OVERDUE" if due < now else "PENDING"
        title = f"[{status}] {row['time_string']}"

        ev_key = _event_key(course_folder, row) # Pass the full row
        seen_keys.add(ev_key)

        end_dt = due + timedelta(minutes=GOOGLE_EVENT_DURATION_MIN)
        event_body = {
            "summary": title,
            "description": f"Course: {row['course_name']}\nDue: {due.strftime('%d/%m %H:%M')}\nLink: {row['url']}",
            "start": {"dateTime": due.isoformat(), "timeZone": GOOGLE_CALENDAR_TIMEZONE},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": GOOGLE_CALENDAR_TIMEZONE},
            "colorId": "11" if status == "OVERDUE" else "9",
            "reminders": {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": m} for m in GOOGLE_REMINDER_MINUTES]
            },
        }

        # 6. [FIXED] Use the user's specific calendar ID
        if ev_key in course_meta:
            batch.add(
                service.events().update(calendarId=user_calendar_id, eventId=course_meta[ev_key], body=event_body),
                callback=lambda rid, resp, exc, k=ev_key, p=course_folder:
                    print(f"   [Calendar] Updated {k[:8]}") or course_metas[p].update({k: resp["id"]}) if not exc else None
            )
        else:
            batch.add(
                service.events().insert(calendarId=user_calendar_id, body=event_body),
                callback=lambda rid, resp, exc, k=ev_key, p=course_folder:
                    print(f"   [Calendar] Created {k[:8]}") or course_metas[p].update({k: resp["id"]}) if not exc else None
            )
        synced += 1

    if batch._requests:
        print(f"   [Calendar] Syncing {synced} events to Google...")
        try:
            batch.execute()
        except Exception as e:
            print(f"   [Calendar] ❌ Batch sync failed: {e}")

    # Save all the new event IDs to their respective meta files
    for path, meta in course_metas.items():
        if meta:
            _save_meta(path, meta)

    # 7. [FIXED] Cleanup: Delete events from this user's calendar only
    if GOOGLE_CLEANUP_DELETED:
        print("   [Calendar] Cleaning up old/completed events...")
        for k in global_meta.keys() - seen_keys:
            try:
                _retry_google(service.events().delete, calendarId=user_calendar_id, eventId=global_meta[k])
                print(f"   [Calendar] Deleted {k[:8]}")
            except:
                pass

    print(f"[Calendar] SYNC DONE for user {user_id}! {synced} events in Calendar!\n")


    # AUTO-TRIGGER AI STUDY PLAN AFTER SYNC (This logic remains the same)
    try:
        from study_planner import generate_study_plan
        print("[Calendar] SYNC COMPLETE → LAUNCHING AI STUDY PLAN GENERATOR...")
        # Pass user_id to the study plan generator
        threading.Thread(target=generate_study_plan, args=(user_id,), daemon=True).start()
        print("[Calendar] AI Study Plan started in background!")
    except ImportError as e:
        print(f"[Calendar] Could not import study_planner: {e}")
    except Exception as e:
        print(f"[Calendar] Failed to start AI Study Plan: {e}")