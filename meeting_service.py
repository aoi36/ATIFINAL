# meeting_service.py
import os
import getpass
import time
import threading
import schedule
import webbrowser
import cv2
import mss
import traceback
import numpy as np
from datetime import datetime
from moviepy import VideoFileClip
import whisper
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import sounddevice as sd
import soundfile as sf

# (Paste your functions: start_screen_recording 
#  and join_meet_automated_and_record here)
#
# Example (paste your full function):

def _record_audio_task(filename: str, duration_seconds: int, samplerate: int):
    """
    A helper function (run in a thread) to record microphone audio
    to a .wav file using sounddevice.
    """
    print(f"   🎧 Recording microphone... (Target file: {filename})")
    try:
        # q = queue.Queue()
        # This will record from the default input device
        recording = sd.rec(int(duration_seconds * samplerate), samplerate=samplerate, channels=1, dtype='float32')
        sd.wait() # Wait until recording is finished
        
        # Save the recording to a file
        sf.write(filename, recording, samplerate)
        print(f"   ✅ Audio recording finished: {filename}")
        
    except Exception as e:
        print(f"   ❌ Audio recording thread failed: {e}")
        traceback.print_exc()

# --- [REPLACE with THIS] Screen Recording & Transcription Function ---
def start_screen_recording(duration_seconds: int, output_filename: str):
    """
    Records the primary screen AND SYSTEM AUDIO, saves video,
    extracts audio, and transcribes.
    This version does NOT use 'sounddevice' or 'soundfile'.
    """
    print(f"\n🔴 Recording screen & system audio for {duration_seconds} seconds...")
    print(f"   Saving video to: {output_filename}")

    video_writer = None
    audio_filename = None
    video_clip = None
    audio_clip = None

    try:
        # --- 1. Video Recording Part (using mss and cv2) ---
        fourcc = cv2.VideoWriter_fourcc(*'mp4v') # Codec for .mp4
        
        with mss.mss() as sct:
            monitor = sct.monitors[1] # Monitor 1 is the primary screen
            width = monitor["width"]
            height = monitor["height"]
            
        fps = 15.0 # Frame rate (lower = smaller file)
        video_writer = cv2.VideoWriter(output_filename, fourcc, fps, (width, height))

        start_time = time.time()
        print(f"   Recording... (Will stop in {duration_seconds}s)")
        with mss.mss() as sct:
            while (time.time() - start_time) < duration_seconds:
                # Grab the screen frame
                img_np = np.array(sct.grab(monitor))
                # Convert from BGRA (mss format) to BGR (OpenCV format)
                frame = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)
                video_writer.write(frame)
        
        # Release the video file
        video_writer.release()
        video_writer = None # Mark as released
        print(f"✅ Screen recording finished: {output_filename}")

        # --- 2. Audio Extraction Part (using moviepy) ---
        print(f"\n🔊 Extracting audio from {output_filename}...")
        audio_filename = os.path.splitext(output_filename)[0] + ".mp3"
        
        video_clip = VideoFileClip(output_filename)
        audio_clip = video_clip.audio
        if audio_clip is None:
             print("   ⚠️ No audio track found in the video recording. This can happen if the system audio was silent or not captured.")
             return # Exit if no audio
        
        audio_clip.write_audiofile(audio_filename, codec='mp3', logger=None)
        print(f"✅ Audio extracted successfully: {audio_filename}")
        
        # Close the clips to free up the file
        audio_clip.close(); audio_clip = None
        video_clip.close(); video_clip = None

        # --- 3. Transcription Part (using whisper) ---
        print(f"\n✍️ Transcribing audio using Whisper (this may take time)...")
        
        model = whisper.load_model("base") # Or "tiny.en", "base.en"
        result = model.transcribe(audio_filename, fp16=False) 

        transcript_text = result["text"]
        transcript_filename = os.path.splitext(output_filename)[0] + "_transcript.txt"
        
        with open(transcript_filename, "w", encoding="utf-8") as f:
            f.write(transcript_text)
        
        print(f"✅ Transcription complete: {transcript_filename}")

    except Exception as e:
        print(f"❌ Error during recording/transcription: {e}")
        traceback.print_exc() # Print full error
    finally:
        # Ensure all resources are released
        if video_writer is not None and video_writer.isOpened():
            video_writer.release()
        if audio_clip:
            audio_clip.close()
        if video_clip:
            video_clip.close()
            
        # Clean up the temporary audio file
        if audio_filename and os.path.exists(audio_filename):
             try:
                 os.remove(audio_filename)
                 print(f"🧹 Cleaned up temporary audio file: {audio_filename}")
             except Exception as del_err:
                 print(f"   ⚠️ Could not delete temporary audio file {audio_filename}: {del_err}")
# --- END CORRECT FUNCTION ---


# --- [MODIFIED] Google Meet Automated Join and Record Function ---
def join_meet_automated_and_record(meet_link: str, record_duration_minutes: int, output_dir: str, user_name: str = "Assistant"):
    """
    Launches a dedicated Selenium browser, grants permissions,
    enters name, clicks Ask to join, and starts recording.
    This version uses a fresh profile to avoid browser conflicts.
    """
    print(f"\n🚀 Attempting automated join for: {meet_link} as '{user_name}'")
    driver = None
    
    try:
        # Use undetected_chromedriver
        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")

        # Set preferences for permissions
        prefs = {
            "profile.default_content_setting_values.media_stream_mic": 1,
            "profile.default_content_setting_values.media_stream_camera": 1,
            "profile.default_content_setting_values.notifications": 2
        }
        options.add_experimental_option("prefs", prefs)

        # --- [FIX 1] ---
        # Explicitly set the Chrome version to match your browser
        driver = uc.Chrome(options=options, version_main=140)
        # --- [END FIX] ---

        print("   Navigating to Google Meet link...")
        driver.get(meet_link)
        time.sleep(3) # Give page a moment to load

        # --- Wait for name input field and enter name ---
        # (This is from your working code, it's good)
        try:
            print("   Waiting for name input field...")
            name_input = None
            # Look for the input field to type a name
            name_selectors = [
                (By.CSS_SELECTOR, "input[aria-label='Your name']"),
                (By.CSS_SELECTOR, "input[placeholder='Your name']"),
                (By.XPATH, "//input[@type='text' and contains(@aria-label, 'name')]")
            ]

            for by_type, selector in name_selectors:
                try:
                    name_input = WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located((by_type, selector))
                    )
                    print(f"   ✅ Found name input using: {selector}")
                    break
                except TimeoutException:
                    continue # Try next selector

            if name_input:
                driver.execute_script("arguments[0].click();", name_input)
                time.sleep(0.5)
                name_input.clear()
                time.sleep(0.5)
                name_input.send_keys(user_name)
                print(f"   ✅ Typed name: {user_name}")
            else:
                print("   ⚠️ Name input field not found. Trying to join anyway (might be pre-filled).")
        except Exception as e:
            print(f"   ⚠️ Error entering name: {e}")
            traceback.print_exc()

        # --- Wait and click "Ask to join" or "Join now" button ---
        # (This is also from your working code)
        try:
            print("   Waiting for join button to become clickable...")
            join_button = None
            button_selectors = [
                (By.XPATH, "//button[.//span[contains(text(), 'Ask to join')]]"),
                (By.XPATH, "//button[.//span[contains(text(), 'Join now')]]")
            ]

            for by_type, selector in button_selectors:
                try:
                    join_button = WebDriverWait(driver, 15).until(
                        EC.element_to_be_clickable((by_type, selector))
                    )
                    print(f"   ✅ Found join button using: {selector}")
                    break
                except TimeoutException:
                    continue

            if join_button:
                button_text = join_button.text or "Join"
                print(f"   ✅ Clicking '{button_text}' button...")
                driver.execute_script("arguments[0].click();", join_button) # JS click
                print(f"   ✅ Successfully clicked button.")
                time.sleep(5) # Wait for meeting to load
            else:
                print("   ❌ Could not find a clickable join button.")
        except Exception as click_err:
            print(f"   ❌ Error clicking join button: {click_err}")
            traceback.print_exc()

        # --- Start Recording ---
        print("   Proceeding to start recording...")
        duration_sec = record_duration_minutes * 60
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filepath = os.path.join(output_dir, f"meet_recording_{timestamp}.mp4")

        rec_thread = threading.Thread(
            target=start_screen_recording,
            args=(duration_sec, output_filepath),
            daemon=True
        )
        rec_thread.start()
        
        # --- [FIX 2] ---
        # REMOVED rec_thread.join()
        # This was a bug. Removing it lets the recording run in the background
        # and allows this function to return immediately.
        # --- [END FIX] ---
        
        print(f"🔴 Recording thread started in background for {record_duration_minutes} min.")

    except Exception as e:
        print(f"❌ Failed during automated join process: {e}")
        traceback.print_exc()
    finally:
        print("   Automated join function finished (browser instance may remain open).")
        # We don't quit the driver here, as it would close the meeting.
        # The browser will close when the main app.py script is stopped.

    return schedule.CancelJob
# --- END Automated Meet Function ---