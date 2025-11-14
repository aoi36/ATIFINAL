# study_planner.py
import json
import os
import sqlite3
import re
import time
import pytz
import traceback
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import BatchHttpRequest

# Import from our other project files
from config import (
    DATABASE_FILE, GOOGLE_SERVICE_ACCOUNT_FILE, GOOGLE_CALENDAR_TIMEZONE, 
    SAVE_DIR
)
from ai_service import ai_client

# Setup Timezone
tz = pytz.timezone(GOOGLE_CALENDAR_TIMEZONE)
now_aware = lambda: datetime.now(tz)

# ================================================
# 1. GET FREE SLOTS (MODIFIED)
# ================================================
def get_free_slots(calendar_id, days=30):
    """Finds free 1, 2, or 3-hour blocks in a *specific* calendar."""
    try:
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/calendar']
        )
        service = build('calendar', 'v3', credentials=creds)
    except Exception as e:
        print(f"[Planner] ❌ Failed to build Google Service: {e}"); return []
        
    now = now_aware()
    slots = []

    for d in range(days):
        day = (now + timedelta(days=d)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # We check for free slots between 8 AM and 10 PM
        day_start = day.replace(hour=8)
        day_end = day.replace(hour=22)
        
        # Skip today if we're already past the check window
        if day_start < now:
            day_start = (now + timedelta(minutes=30)).replace(minute=0, second=0)

        if day_start >= day_end:
            continue
            
        try:
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=day_start.isoformat(),
                timeMax=day_end.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
        except Exception as e:
            print(f"[Planner] ⚠️ Failed to list events for {day.date()}: {e}")
            continue # Skip this day
            
        events = events_result.get('items', [])
        busy = []

        for e in events:
            start_dict = e['start']
            end_dict = e['end']
            if 'dateTime' in start_dict:
                s = datetime.fromisoformat(start_dict['dateTime'].replace('Z', '+00:00')).astimezone(tz)
                e_end = datetime.fromisoformat(end_dict['dateTime'].replace('Z', '+00:00')).astimezone(tz)
            elif 'date' in start_dict:
                s = tz.localize(datetime.fromisoformat(start_dict['date'] + "T00:00:00"))
                e_end = tz.localize(datetime.fromisoformat(end_dict.get('date', start_dict['date']) + "T23:59:59"))
            else:
                continue
            busy.append((s, e_end))

        # Start from 8 AM (or now if it's today)
        current = day_start
        while current < day_end:
            slot_start = current
            # Check for 3, 2, then 1-hour blocks
            for block_hours in [3, 2, 1]:
                slot_end = slot_start + timedelta(hours=block_hours)
                if slot_end > day_end:
                    continue # This block goes past 10 PM
                
                # Check if this block overlaps with any busy time
                is_free = all(
                    not (slot_start < b_end and slot_end > b_start)
                    for b_start, b_end in busy
                )
                
                if is_free:
                    slots.append((slot_start, slot_end, block_hours))
                    break # Found the biggest block for this start time
            
            # Move to the next hour to check again
            current += timedelta(hours=1)

    print(f"   [Planner] Found {len(slots)} free blocks in next {days} days.")
    return slots

# ================================================
# 2. GET ASSIGNMENT CONTENT (REWRITTEN)
# ================================================
def get_assignment_content(user_id, lms_course_id, course_name):
    """
    Reads extracted text from the local .txt files scraped by the main app.
    Does NOT use Selenium or re-scrape.
    """
    print(f"   [Planner] Reading local content for course {lms_course_id}...")
    try:
        # Build the user-specific path, just like the scraper does
        safe_course_name = re.sub(r'[\\/*?:"<>|]', "_", course_name).strip()[:150]
        course_folder = os.path.join(SAVE_DIR, f"user_{user_id}", f"{lms_course_id}_{safe_course_name}")

        if not os.path.exists(course_folder):
            print(f"   [Planner] ⚠️ Content folder not found: {course_folder}")
            return "No content folder found for this course."

        all_text = ""
        # Find all .txt files (which contain the extracted text)
        for filename in os.listdir(course_folder):
            if filename.lower().endswith(".txt"):
                txt_path = os.path.join(course_folder, filename)
                try:
                    with open(txt_path, "r", encoding="utf-8") as f:
                        all_text += f"\n\n--- Content from {filename} ---\n\n"
                        all_text += f.read()
                except Exception as e:
                    print(f"   [Planner] ⚠️ Failed to read {filename}: {e}")

        if not all_text:
            return "No text files found for this course."
            
        return all_text[:45000] # Return truncated content
        
    except Exception as e:
        print(f"   [Planner] ❌ Error in get_assignment_content: {e}")
        return f"Error reading local content: {e}"

# ================================================
# 3. AI ESTIMATE (MODIFIED)
# ================================================
def ai_estimate_difficulty(user_id, lms_course_id, course_name, title, url):
    """Reads local content and sends it to AI for estimation."""
    content = get_assignment_content(user_id, lms_course_id, course_name)
    
    prompt = f"""
    You are a university study planner. Based on the assignment title, course, and the provided
    scraped text content from the course files, estimate the difficulty and time required.

    Course: {course_name}
    Assignment: {title}
    Link: {url}
    
    SCRAPED COURSE CONTENT:
    {content}
    
    Return ONLY a valid JSON object with your estimation:
    {{
        "difficulty": 4,
        "hours": 10,
        "reason": "This assignment appears to require a significant coding component based on the lecture notes, as well as a written report.",
        "breakdown": ["Review lecture notes on TCP sockets (2h)", "Implement the client-server application (6h)", "Test and debug (1h)", "Write final report (1h)"]
    }}
    """
    try:
        response = ai_client.generate_content(prompt)
        text = response.text.strip()
        start = text.find('{')
        end = text.rfind('}') + 1
        return json.loads(text[start:end])
    except Exception as e:
        print(f"   [Planner] ⚠️ AI estimation failed: {e}")
        return {
            "difficulty": 3, "hours": 6,
            "reason": "AI estimation failed. Defaulting to 6 hours.", 
            "breakdown": ["Study related materials", "Complete assignment"]
        }

# ================================================
# 4. GENERATE STUDY PLAN (REWRITTEN)
# ================================================
def generate_study_plan(user_id: int):
    """
    Generates a full study plan for a specific user.
    1. Gets user's calendar ID and existing study events.
    2. Gets user's uncompleted deadlines from DB.
    3. Asks AI to estimate time for each deadline.
    4. Gets user's free time slots from their calendar.
    5. Schedules new study blocks in the free slots.
    """
    print(f"\n[Planner] Starting AI Study Plan for user {user_id}...")
    db = None
    
    try:
        # === 1. LOAD USER, META, & CALENDAR ===
        db = sqlite3.connect(DATABASE_FILE)
        db.row_factory = sqlite3.Row
        cursor = db.cursor()
        
        user_row = cursor.execute("SELECT google_calendar_id FROM user WHERE id = ?", (user_id,)).fetchone()
        if not user_row:
            print(f"   [Planner] ❌ User {user_id} not found."); return
        
        user_calendar_id = user_row['google_calendar_id']
        print(f"   [Planner] Found user. Syncing to calendar: {user_calendar_id}")

        META_PATH = os.path.join(SAVE_DIR, f"user_{user_id}", "study_plan_meta.json")
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
        now = now_aware()

        events_result = service.events().list(
            calendarId=user_calendar_id, timeMin=now.isoformat(),
            timeMax=(now + timedelta(days=60)).isoformat(),
            q="[STUDY]", singleEvents=True
        ).execute()
        existing_events = events_result.get('items', [])
        existing_event_ids = {e['id']: e for e in existing_events}

        # Clean meta of events deleted on GCal
        cleaned_meta = {k: v for k, v in study_meta.items() if v in existing_event_ids}
        study_meta = cleaned_meta

        # === 2. LOAD DEADLINES (FOR THIS USER) ===
        cursor.execute("""
            SELECT c.id AS course_db_id, c.lms_course_id, c.name AS course_name, d.*
            FROM deadlines d
            JOIN courses c ON d.course_db_id = c.id
            WHERE d.user_id = ? 
              AND d.parsed_iso_date IS NOT NULL
              AND d.is_completed = 0
        """, (user_id,))
        rows = cursor.fetchall()
        db.close(); db = None # Done with DB

        tasks = []
        print(f"   [Planner] Found {len(rows)} uncompleted deadlines to plan for.")
        for row in rows:
            iso = row['parsed_iso_date'].strip().split('.')[0]
            if not iso.endswith('Z') and '+' not in iso: iso += 'Z'
            try: due = datetime.fromisoformat(iso.replace('Z', '+00:00')).astimezone(tz)
            except Exception: due = now + timedelta(days=3)
            
            # Skip if already overdue
            if due < now:
                continue

            ai = ai_estimate_difficulty(
                user_id, row['lms_course_id'], row['course_name'],
                row['time_string'], row['url'] or ""
            )
            hours = max(1, ai['hours'])
            task_key = f"study_task_user{user_id}_deadline{row['id']}" # Unique key

            tasks.append({
                "key": task_key, "title": row['time_string'][:60],
                "course": row['course_name'], "due": due,
                "url": row['url'] or "", "hours": hours,
                "difficulty": ai['difficulty'], "reason": ai.get('reason', 'AI planned'),
                "breakdown": ai.get('breakdown', ['Study'])
            })

        # === 3. BUILD FREE SLOTS ===
        slots = get_free_slots(calendar_id=user_calendar_id, days=30)
        
        # === 4. FULL SYNC (Assign tasks to slots) ===
        new_meta = {}
        batch = service.new_batch_http_request()
        created_count = updated_count = deleted_count = 0

        task_day_tracker = {}
        used_time_slots = set() # (start_time_iso, end_time_iso)

        for task in sorted(tasks, key=lambda x: x['due']): # Prioritize nearest deadlines
            hours_left = task['hours']
            slot_idx = 0
            task_key = task['key']
            if task_key not in task_day_tracker:
                task_day_tracker[task_key] = {}

            while hours_left > 0 and slot_idx < len(slots):
                slot_start, slot_end, max_duration = slots[slot_idx]
                if slot_start > task['due']: # Slot is after deadline
                    slot_idx += 1
                    continue

                # Check if this slot is already used
                slot_key = (slot_start.isoformat(), slot_end.isoformat())
                if slot_key in used_time_slots:
                    slot_idx += 1
                    continue
                
                # --- One block per day per task ---
                day_str = slot_start.strftime('%Y-%m-%d')
                blocks_today = task_day_tracker[task_key].get(day_str, 0)
                if blocks_today >= 1:
                    slot_idx += 1
                    continue
                
                # Decide block size (prefer smaller blocks)
                block_h = min(1, hours_left, max_duration)
                hours_this_block = block_h
                end_time = slot_start + timedelta(hours=hours_this_block)

                # Stable Event Key
                event_key = f"{task_key}_{day_str}_{int(hours_this_block)}h"
                event_id = study_meta.get(event_key)

                # Event Body
                code_match = re.search(r'\[([^\]]+)\]', task['course'])
                course_code = code_match.group(0) if code_match else task['course'][:20]
                
                event_body = {
                    "summary": f"🎓 [STUDY] {course_code} - {task['title']}",
                    "description":
                        "✨ AI Study Plan ✨\n\n"
                        f"📊 Difficulty: {'★' * task['difficulty']}{'☆' * (5 - task['difficulty'])} ({task['difficulty']}/5)\n"
                        f"⏱ Total Time: {task['hours']}h | This Block: {hours_this_block}h\n"
                        f"📅 Due: {task['due'].strftime('%b %d, %Y at %H:%M')}\n\n"
                        "🤖 AI Reason:\n"
                        f"   {task['reason']}\n\n"
                        "📝 Breakdown:\n" +
                        "\n".join([f"   • {b}" for b in task['breakdown'][:5]]) +
                        f"\n\n🔗 Resource: {task['url'] or 'No link provided'}\n",
                    "start": {"dateTime": slot_start.isoformat(), "timeZone": GOOGLE_CALENDAR_TIMEZONE},
                    "end": {"dateTime": end_time.isoformat(), "timeZone": GOOGLE_CALENDAR_TIMEZONE},
                    "colorId": "3", # Lavender
                    "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 10}]}
                }

                # UPSERT
                if event_id and event_id in existing_event_ids:
                    batch.add(
                        service.events().update(calendarId=user_calendar_id, eventId=event_id, body=event_body),
                        callback=lambda _id, resp, exc, k=event_key: new_meta.update({k: resp['id']}) if not exc else None
                    )
                    updated_count += 1
                else:
                    batch.add(
                        service.events().insert(calendarId=user_calendar_id, body=event_body),
                        callback=lambda _id, resp, exc, k=event_key: new_meta.update({k: resp['id']}) if not exc else None
                    )
                    created_count += 1

                new_meta[event_key] = "pending"
                task_day_tracker[task_key][day_str] = blocks_today + 1
                used_time_slots.add(slot_key)
                hours_left -= hours_this_block
                slot_idx += 1

        # === 5. DELETE STALE EVENTS ===
        for key, event_id in study_meta.items():
            if key not in new_meta and event_id in existing_event_ids:
                batch.add(
                    service.events().delete(calendarId=user_calendar_id, eventId=event_id),
                    callback=lambda _id, resp, exc, k=key: print(f"   [Planner] DELETED old event: {k}") if not exc else None
                )
                deleted_count += 1

        # === 6. EXECUTE BATCH ===
        print(f"   [Planner] Executing batch: {created_count} new, {updated_count} updated, {deleted_count} deleted")
        if batch._requests:
            try:
                batch.execute()
            except Exception as e:
                print(f"   [Planner] ❌ Batch error: {e}")

        # === 7. SAVE META ===
        final_meta = {k: v for k, v in new_meta.items() if v != "pending"}
        final_meta.update({k: v for k, v in study_meta.items() if k not in final_meta and k not in new_meta})
        
        with open(META_PATH, "w", encoding="utf-8") as f:
            json.dump(final_meta, f, indent=2)

        print(f"\n[Planner] AI Study Plan for user {user_id} is COMPLETE.")
        print(f"   Created: {created_count} | Updated: {updated_count} | Deleted: {deleted_count}")
        
    except Exception as e:
        print(f"   [Planner] ❌ FAILED to generate study plan: {e}")
        traceback.print_exc()
    finally:
        if db: db.close()

# ================================================
# 5. AUTO START (No longer used as standalone script)
# ================================================
# This file is now a "service" file. 
# The scheduling (e.g., schedule.every().sunday...)
# should be handled in your main app.py's run_background_schedule function.