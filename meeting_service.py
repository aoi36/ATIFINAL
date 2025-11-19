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
from moviepy.editor import VideoFileClip, AudioFileClip
import whisper
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Imports for audio recording
import sounddevice as sd
import soundfile as sf


# --- [HELPER 1] Find the system audio (loopback) device ---
def find_loopback_device():
    """Finds the ID of the system's loopback/speaker device for recording."""
    print("   [Audio] Querying audio devices...")
    try:
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()
        
        wasapi_index = -1
        for i, api in enumerate(hostapis):
            if api['name'] == 'Windows WASAPI':
                wasapi_index = i
                break
        
        if wasapi_index == -1:
            print("   [Audio] ⚠️ Could not find Windows WASAPI. Falling back to default mic.")
            return None

        default_speaker = hostapis[wasapi_index]['default_output_device']
        if default_speaker == -1:
             print("   [Audio] ⚠️ No default WASAPI speaker found. Falling back to default mic.")
             return None

        speaker_info = devices[default_speaker]
        print(f"   [Audio] Found default speaker: {speaker_info['name']}")

        # Find the loopback (Stereo Mix) version of this speaker
        for i, device in enumerate(devices):
            if (device['hostapi'] == wasapi_index and
                device['max_input_channels'] > 0 and
                speaker_info['name'] in device['name'] and
                'Loopback' in device['name']):
                
                print(f"   [Audio] ✅ Found loopback device: {device['name']} (ID: {i})")
                return i # Return the device ID

        print("   [Audio] ⚠️ No loopback device found. Did you enable 'Stereo Mix' in Sound settings?")
        print("   [Audio] Falling back to default microphone (will likely fail or record silence).")
        return None 
    except Exception as e:
        print(f"   [Audio] ❌ Error querying audio devices: {e}")
        return None 


# --- [HELPER 2] Record audio in a separate thread ---
def _record_audio_task(filename: str, duration_seconds: int, samplerate: int, device_id: int | None):
    """
    A helper function (run in a thread) to record audio
    to a .wav file using sounddevice.
    """
    if device_id is None:
        print(f"   🎧 Recording default microphone... (Target file: {filename})")
    else:
        print(f"   🎧 Recording system audio (device {device_id})... (Target file: {filename})")
        
    try:
        recording = sd.rec(
            int(duration_seconds * samplerate), 
            samplerate=samplerate, 
            channels=1, 
            device=device_id, 
            dtype='float32'
        )
        sd.wait() # Wait until recording is finished
        sf.write(filename, recording, samplerate)
        print(f"   ✅ Audio recording finished: {filename}")
        
    except Exception as e:
        print(f"   ❌ Audio recording thread failed: {e}")
        traceback.print_exc()


# --- [FUNCTION 1] This is called by the thread ---
def start_screen_recording(duration_seconds: int, output_filename: str):
    """
    Records screen AND system audio simultaneously, merges them,
    and then transcribes the audio.
    """
    print(f"\n🔴 Recording screen & system audio for {duration_seconds}s...")

    base_name = os.path.splitext(output_filename)[0]
    temp_video_filename = base_name + "_temp_video.mp4"
    temp_audio_filename = base_name + "_temp_audio.wav"
    transcript_filename = base_name + "_transcript.txt"

    video_writer = None
    video_clip = None
    audio_clip = None
    final_clip = None

    try:
        # --- Find the audio device ---
        loopback_device_id = find_loopback_device()
        
        # --- Audio Setup ---
        if loopback_device_id is not None:
            device_info = sd.query_devices(loopback_device_id, 'input')
        else:
            device_info = sd.query_devices(None, 'input') # Fallback to default mic
        samplerate = int(device_info['default_samplerate'])

        # --- Start Audio Recording Thread ---
        audio_thread = threading.Thread(
            target=_record_audio_task,
            args=(temp_audio_filename, duration_seconds, samplerate, loopback_device_id),
            daemon=True
        )
        audio_thread.start()

        # --- Video Setup ---
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            width, height = monitor["width"], monitor["height"]

        fps = 15.0
        video_writer = cv2.VideoWriter(temp_video_filename, fourcc, fps, (width, height))

        # --- Start Video Recording (in main thread) ---
        print(f"   📺 Recording video...")
        start_time = time.time()
        with mss.mss() as sct:
            while (time.time() - start_time) < duration_seconds:
                frame = np.array(sct.grab(monitor))
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                video_writer.write(frame_bgr)

        video_writer.release()
        video_writer = None
        print(f"   ✅ Video recording finished: {temp_video_filename}")

        # --- Wait for audio thread to finish ---
        print("   Waiting for audio thread to complete...")
        audio_thread.join()

        # --- Merge Audio and Video ---
        print(f"\n🔀 Merging video and audio into: {output_filename}")
        if not os.path.exists(temp_audio_filename) or os.path.getsize(temp_audio_filename) == 0:
            print("   ⚠️ Audio file not found or is empty. Saving video-only.")
            os.rename(temp_video_filename, output_filename)
            return  # Can't transcribe

        video_clip = VideoFileClip(temp_video_filename)
        audio_clip = AudioFileClip(temp_audio_filename)

        final_clip = video_clip.set_audio(audio_clip)
        final_clip.write_videofile(output_filename, codec='libx264', audio_codec='aac', logger=None)
        print(f"✅ Merge complete: {output_filename}")

        # --- Transcribe ---
        print(f"\n✍️ Transcribing audio...")
        model = whisper.load_model("base")
        result = model.transcribe(temp_audio_filename, fp16=False)

        with open(transcript_filename, "w", encoding="utf-8") as f:
            f.write(result["text"])
        print(f"✅ Transcription saved: {transcript_filename}")

    except Exception as e:
        print(f"❌ Error during recording/transcription: {e}")
        traceback.print_exc()

    finally:
        # --- Cleanup ---
        print("\n🧹 Cleaning up temporary files...")
        if video_writer is not None: video_writer.release()
        if final_clip: final_clip.close()
        if video_clip: video_clip.close()
        if audio_clip: audio_clip.close()

        for temp_file in [temp_video_filename, temp_audio_filename]:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                    print(f"   Removed: {temp_file}")
                except Exception as del_err:
                    print(f"   ⚠️ Could not delete temp file: {del_err}")


# meeting_service.py

# ... (keep imports and other functions as they are) ...

def join_meet_automated_and_record(meet_link: str, record_duration_minutes: int, output_dir: str, user_name: str = "Assistant", user_id: int = 0):
    """
    Launches a dedicated Selenium browser, grants permissions,
    enters name, clicks Ask to join, and starts recording.
    """
    print(f"\n🚀 Attempting automated join for: {meet_link} as '{user_name}' (User ID: {user_id})")
    driver = None
    
    try:
        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
        # Allow microphone/camera permissions automatically
        prefs = {
            "profile.default_content_setting_values.media_stream_mic": 1,
            "profile.default_content_setting_values.media_stream_camera": 1,
            "profile.default_content_setting_values.notifications": 2
        }
        options.add_experimental_option("prefs", prefs)

        # Auto-detect version
        driver = uc.Chrome(options=options, version_main=None)

        print("   Navigating to Google Meet link...")
        driver.get(meet_link)
        time.sleep(4) # Wait a bit longer for initial load

        # --- 1. Try to clear any "Got it" / "Dismiss" popups first ---
        try:
            dismiss_selectors = [
                (By.XPATH, "//span[contains(text(), 'Got it')]"),
                (By.XPATH, "//span[contains(text(), 'Dismiss')]"),
                (By.XPATH, "//span[contains(text(), 'Không, cảm ơn')]"), # Vietnamese
            ]
            for by, sel in dismiss_selectors:
                try:
                    btn = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((by, sel)))
                    driver.execute_script("arguments[0].click();", btn)
                    print("   Clicked dismiss popup.")
                    time.sleep(1)
                    break
                except: continue
        except: pass

        # --- 2. Wait for name input field and enter name ---
        try:
            print("   Waiting for name input field...")
            name_input = None
            name_selectors = [
                (By.CSS_SELECTOR, "input[aria-label='Your name']"),
                (By.CSS_SELECTOR, "input[placeholder='Your name']"),
                (By.XPATH, "//input[@type='text' and contains(@aria-label, 'name')]"),
                (By.XPATH, "//input[@type='text']") # Fallback generic text input
            ]
            for by_type, selector in name_selectors:
                try:
                    name_input = WebDriverWait(driver, 5).until(
                        EC.visibility_of_element_located((by_type, selector))
                    )
                    print(f"   ✅ Found name input using: {selector}")
                    break
                except TimeoutException:
                    continue 

            if name_input:
                driver.execute_script("arguments[0].click();", name_input)
                time.sleep(0.5); name_input.clear(); time.sleep(0.5)
                name_input.send_keys(user_name)
                print(f"   ✅ Typed name: {user_name}")
            else:
                print("   ⚠️ Name input field not found. Trying to join anyway (might be logged in or pre-filled).")
        except Exception as e:
            print(f"   ⚠️ Error entering name: {e}")

        # --- 3. Wait and click "Ask to join" or "Join now" button ---
        # [FIX] Updated selectors to be much more robust
        try:
            print("   Waiting for join button to become clickable...")
            join_button = None
            button_selectors = [
                # Method A: Text inside a span (Most common for Google Material Design)
                (By.XPATH, "//span[contains(text(), 'Ask to join')]"),
                (By.XPATH, "//span[contains(text(), 'Join now')]"),
                
                # Method B: Text anywhere inside a button element
                (By.XPATH, "//button[contains(., 'Ask to join')]"),
                (By.XPATH, "//button[contains(., 'Join now')]"),
                
                # Method C: Vietnamese Support (Just in case)
                (By.XPATH, "//span[contains(text(), 'Yêu cầu tham gia')]"),
                (By.XPATH, "//span[contains(text(), 'Tham gia ngay')]"),
                (By.XPATH, "//button[contains(., 'Yêu cầu tham gia')]"),
                (By.XPATH, "//button[contains(., 'Tham gia ngay')]"),
            ]

            for by_type, selector in button_selectors:
                try:
                    # Check if it exists and is visible
                    join_button = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((by_type, selector))
                    )
                    print(f"   ✅ Found join button using: {selector}")
                    break
                except TimeoutException:
                    continue

            if join_button:
                # Use JavaScript click which is more reliable for overlaid elements
                driver.execute_script("arguments[0].click();", join_button)
                print(f"   ✅ Successfully clicked Join button.")
                time.sleep(5) # Wait for meeting to load
            else:
                print("   ❌ Could not find a clickable join button (tried all selectors).")
                # Take a screenshot for debugging if it fails
                driver.save_screenshot("join_fail_debug.png") 

        except Exception as click_err:
            print(f"   ❌ Error clicking join button: {click_err}")
            traceback.print_exc()

        # --- Start Recording ---
        print("   Proceeding to start recording...")
        duration_sec = record_duration_minutes * 60
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        filename = f"{user_id}_meet_recording_{timestamp}.mp4"
        output_filepath = os.path.join(output_dir, filename)

        rec_thread = threading.Thread(
            target=start_screen_recording, 
            args=(duration_sec, output_filepath),
            daemon=True
        )
        rec_thread.start()
        
        print(f"🔴 Recording thread started in background for {record_duration_minutes} min. File: {filename}")

    except Exception as e:
        print(f"❌ Failed during automated join process: {e}")
        traceback.print_exc()
    finally:
        print("   Automated join function finished (browser instance may remain open).")

    return schedule.CancelJob