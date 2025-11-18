
# voice_popup_reminder.py
import queue
import threading
import time
import pytz
import numpy as np
import sounddevice as sd
import pyttsx3
import sqlite3
import schedule
from datetime import datetime, timedelta
from plyer import notification
from config import DATABASE_FILE, GOOGLE_CALENDAR_TIMEZONE

# ────────────────────── CẤU HÌNH + DEBUG ──────────────────────
tz = pytz.timezone(GOOGLE_CALENDAR_TIMEZONE)
now_aware = lambda: datetime.now(tz)
_current_user_id = None
print(f"[WAIFU DEBUG] Module loaded at {datetime.now().strftime('%H:%M:%S')}")

# ────────────────────── ALERT LEVELS ──────────────────────
ALERT_LEVELS = [
    (timedelta(minutes=5), "5 MINUTES LEFT!", "Master! {course} due in 5 minutes! Run run run!"),
    (timedelta(hours=1), "1 HOUR LEFT!", "One hour left for {course}, darling!"),
    (timedelta(hours=6), "6 HOURS LEFT!", "Six hours until {course} deadline~"),
    (timedelta(days=1), "DUE TOMORROW!", "Tomorrow is the deadline for {course}!"),
    (timedelta(days=3), "3 DAYS LEFT!", "Three days left for {course}! Don't forget!"),
    (timedelta(days=7), "1 WEEK LEFT!", "One week until {course} is due, onii-chan!"),
]

# ────────────────────── TTS + SOUND ──────────────────────
_tts_engine = None


def _init_tts():
    global _tts_engine
    if _tts_engine: return
    try:
        _tts_engine = pyttsx3.init('sapi5')
        _tts_engine.setProperty('rate', 150)
        for v in _tts_engine.getProperty('voices'):
            if 'zira' in v.name.lower():
                _tts_engine.setProperty('voice', v.id)
                print("[WAIFU DEBUG] Zira voice loaded!")
                return
        print("[WAIFU DEBUG] Using default voice")
    except Exception as e:
        print(f"[WAIFU DEBUG] TTS init failed: {e}")
        _tts_engine = None


def _speak(text: str):
    if not _tts_engine: _init_tts()
    if not _tts_engine:
        print(f"[WAIFU DEBUG] TTS not available → would say: {text}")
        return
    short = text[:197] + "..." if len(text) > 200 else text
    print(f"WAIFU SPEAKS: {short}")
    try:
        _tts_engine.say(short)
        _tts_engine.runAndWait()
    except Exception as e:
        print(f"[WAIFU DEBUG] TTS error: {e}")


def _beep():
    try:
        t = np.linspace(0, 0.25, int(44100 * 0.25), False)
        wave = 0.3 * np.sin(2 * np.pi * 880 * t)
        sd.play(wave, 44100)
        sd.wait()
    except Exception as e:
        print(f"[WAIFU DEBUG] Beep failed: {e}")


def _alert(title: str, msg: str, voice: str):
    print(f"ALERT TRIGGERED → {title}")
    try:
        notification.notify(title=title, message=msg + "\n\n(Waifu loves you~)", timeout=15, app_name="LMS Waifu")
    except Exception as e:
        print(f"[WAIFU DEBUG] Notification failed: {e}")
    _speak(voice)
    _beep()


# ────────────────────── QUEUE WORKER ──────────────────────
alert_queue = queue.Queue()

def _queue_worker():
    print("[WAIFU DEBUG] Alert queue worker started – 20 seconds gap between each reminder")
    while True:
        try:
            item = alert_queue.get(timeout=60)  # chờ tối đa 60s nếu không có alert
            if item is None:  # tín hiệu tắt worker
                print("[WAIFU DEBUG] Queue worker received shutdown signal")
                break

            title, msg, voice = item
            print(f"\nWAIFU REMINDER → {title}")
            _alert(title, msg, voice)
            print(f" → Reminder sent: {title}")

            # ĐỢI ĐÚNG 20 GIÂY TRƯỚC KHI HIỆN DEADLINE TIẾP THEO
            print(" → Waifu is waiting 20 seconds before next reminder...")
            time.sleep(20)
            print(" → 20 seconds passed! Ready for next deadline~")

        except queue.Empty:
            # Không có alert nào trong 60s → vẫn tiếp tục chạy (không in spam)
            continue
        except Exception as e:
            print(f"[WAIFU DEBUG] Queue worker error: {e}")

# Khởi động worker (chỉ chạy 1 lần duy nhất)
threading.Thread(target=_queue_worker, daemon=True).start()

# ────────────────────── CACHE RIÊNG CHO TỪNG USER (multi-user safe) ──────────────────────
_user_notified_cache = {}  # {user_id: set()}
_user_cache_time = {}  # {user_id: datetime}


def _get_user_cache(user_id):
    if user_id not in _user_notified_cache:
        _user_notified_cache[user_id] = set()
        _user_cache_time[user_id] = now_aware()
    # Reset cache mỗi 6 tiếng
    if now_aware() - _user_cache_time[user_id] > timedelta(hours=6):
        _user_notified_cache[user_id].clear()
        _user_cache_time[user_id] = now_aware()
    return _user_notified_cache[user_id]


# ────────────────────── HÀM CHECK ĐÃ NỘP CHƯA ──────────────────────
def _is_submitted(row) -> bool:
    status = (row['status'] or "").lower()
    time_str = (row['time_string'] or "").lower()
    keywords = [
        "submitted", "đã nộp", "nộp thành công", "đã nộp để chấm điểm",
        "submitted early", "để chấm điểm", "turned in", "complete"
    ]
    return any(k in status or k in time_str for k in keywords)


# ────────────────────── MAIN CHECK FUNCTION ──────────────────────
def _check_deadlines():
    global _current_user_id
    if _current_user_id is None:
        print(f"[WAIFU DEBUG] _check_deadlines() called but NO USER LOGGED IN")
        return

    now = now_aware()
    user_id = _current_user_id
    notified = _get_user_cache(user_id)

    print(f"\n[WAIFU DEBUG] CHECKING DEADLINES FOR USER {user_id} at {now.strftime('%H:%M:%S %d/%m')}")

    try:
        db = sqlite3.connect(DATABASE_FILE, timeout=10)
        db.row_factory = sqlite3.Row
        cur = db.cursor()
        cur.execute("""
            SELECT c.name AS course_name, d.id, d.parsed_iso_date, d.url, d.status, d.time_string
            FROM deadlines d
            JOIN courses c ON d.course_db_id = c.id
            WHERE d.user_id = ? AND d.parsed_iso_date IS NOT NULL
        """, (user_id,))
        rows = cur.fetchall()
        db.close()
        print(f"[WAIFU DEBUG] Found {len(rows)} deadlines in DB")
    except Exception as e:
        print(f"[WAIFU DEBUG] DB ERROR: {e}")
        return

    if not rows:
        print("[WAIFU DEBUG] No deadlines found")
        return

    alerts = 0
    for row in rows:
        try:
            # BỎ QUA DEADLINE ĐÃ NỘP
            if _is_submitted(row):
                print(f" → SKIPPED (already submitted): {row['course_name']}")
                continue

            due_str = row['parsed_iso_date']
            due = datetime.fromisoformat(due_str.replace('Z', '+00:00')).astimezone(tz)
            time_left = due - now

            print(f"[WAIFU DEBUG] Deadline: {row['course_name']} → due {due_str} → {time_left}")

            # Chỉ bỏ qua deadline quá cũ (>30 ngày trước)
            if time_left < timedelta(days=-30):
                print(f" → Skipped (very old deadline)")
                continue

            key = f"{user_id}_{row['id']}"
            if key in notified:
                print(f" → Already notified today")
                continue

            course = row['course_name'] or "Unknown Course"
            url = row['url'] or ""

            # Tìm level phù hợp
            triggered = False
            for threshold, title, voice_tpl in ALERT_LEVELS:
                if time_left <= threshold:
                    msg = f"{course}\nDue: {due.strftime('%d/%m %H:%M')}\n{url}"
                    voice = voice_tpl.format(course=course)
                    alert_queue.put((title, msg, voice))
                    notified.add(key)
                    print(f" → ALERT SENT: {title} → {course}")
                    alerts += 1
                    triggered = True
                    break

            # Nếu quá 7 ngày → vẫn nhắc nhẹ 1 lần/ngày (dù xa mấy năm cũng nhắc!)
            if not triggered and time_left > timedelta(days=7):
                title = "FUTURE DEADLINE"
                msg = f"{course}\nDue: {due.strftime('%d/%m/%Y %H:%M')}\n{url}"
                voice = f"Reminder: {course} is due on {due.strftime('%B %d, %Y')}."
                alert_queue.put((title, msg, voice))
                notified.add(key)
                print(f" → FUTURE REMINDER: {course} ({time_left.days} days away)")
                alerts += 1

        except Exception as e:
            print(f"[WAIFU DEBUG] Error processing row: {e}")

    print(f"[WAIFU DEBUG] Check complete → {alerts} alert(s) sent\n")


# ────────────────────── PUBLIC FUNCTIONS ──────────────────────
def start_waifu_for(user_id: int):
    global _current_user_id
    _current_user_id = user_id
    print(f"\n[WAIFU DEBUG] start_waifu_for({user_id}) CALLED!")
    schedule.clear(f"waifu_user_{user_id}")
    _speak("Hello Master! Your personal Waifu is now online!")
    print("[WAIFU DEBUG] Running IMMEDIATE check #1...")
    _check_deadlines()

    schedule.every(5).minutes.do(_check_deadlines).tag(f"waifu_user_{user_id}")
    print(f"[WAIFU DEBUG] Waifu scheduled for user {user_id}")


def stop_waifu():
    global _current_user_id
    if _current_user_id is not None:
        print(f"[WAIFU DEBUG] stop_waifu() called – stopping user {_current_user_id}")
        schedule.clear(f"waifu_user_{_current_user_id}")
        _speak("Good night, Master! Waifu going to sleep...")
        # Xóa cache của user này
        _user_notified_cache.pop(_current_user_id, None)
        _user_cache_time.pop(_current_user_id, None)
        _current_user_id = None