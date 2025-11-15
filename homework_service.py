import time
import traceback
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc

def submit_homework_to_lms(
    assignment_url: str,
    file_path: str,
    username: str,
    password: str
):
    """
    Automates homework submission to LMS using Selenium.
    This function is run in a background thread.
    """
    print(f"\n🚀 Starting automated homework submission...")
    print(f"   Assignment URL: {assignment_url}")
    print(f"   File: {file_path}")

    driver = None

    try:
        if not os.path.exists(file_path):
            print(f"   ❌ ERROR: File not found: {file_path}")
            return # Just log the error and end the thread

        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
        # options.add_argument("--headless") # Headless can be detected
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "download.prompt_for_download": False
        }
        options.add_experimental_option("prefs", prefs)

        print("   Launching browser...")
        driver = uc.Chrome(options=options, use_subprocess=True)

        print("   Navigating to assignment page...")
        driver.get(assignment_url)
        time.sleep(3)

        page_source = driver.page_source.lower()
        needs_login = (
            "login" in driver.current_url.lower() or
            "guests cannot access" in page_source or
            "please log in" in page_source or
            "you are currently using guest access" in page_source
        )

        if needs_login:
            print("   Login required, attempting to log in...")
            try:
                continue_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]")
                if continue_button:
                    print("   Found 'Continue' button, clicking...")
                    driver.execute_script("arguments[0].click();", continue_button)
                    time.sleep(2)
            except:
                pass # No 'Continue' button, fine

            # --- [CALL HELPER] ---
            success = _perform_login(driver, username, password)
            if not success:
                print("   ❌ ERROR: Failed to log in to LMS")
                return # End thread

            print("   Navigating back to assignment page after login...")
            driver.get(assignment_url)
            time.sleep(3)

            page_source_after = driver.page_source.lower()
            if "guests cannot access" in page_source_after or "please log in" in page_source_after:
                print("   ❌ ERROR: Still showing guest access after login")
                return # End thread

        print("   Looking for submission button...")
        # --- [CALL HELPER] ---
        submit_button = _find_submission_button(driver)
        if submit_button:
            button_text = submit_button.text
            print(f"   ✅ Found '{button_text}' button, clicking...")
            driver.execute_script("arguments[0].click();", submit_button)
            time.sleep(3)
        else:
            print("   ⚠️ Submission button not found, checking if already on submission page...")

        print("   Looking for 'Thêm...' (Add) button...")
        # --- [CALL HELPER] ---
        add_file_button = _find_add_file_button(driver)
        if not add_file_button:
            print("   ⚠️ Could not find 'Thêm...' button. Trying direct upload (fallback)...")
            # --- [CALL HELPER] ---
            result = _try_direct_file_upload(driver, file_path, assignment_url)
            print(f"   Fallback result: {result.get('message') or result.get('error')}")
            return # End thread

        print("   ✅ Found 'Thêm...' button, clicking...")
        driver.execute_script("arguments[0].click();", add_file_button)
        time.sleep(2)

        print("   Looking for file input in file picker...")
        # --- [CALL HELPER] ---
        file_input = _find_file_picker_input(driver)
        if not file_input:
            print("   ❌ ERROR: Could not find file input in file picker dialog")
            return

        print(f"   ✅ Found file input, uploading file: {file_path}")
        file_input.send_keys(file_path)
        time.sleep(2)

        print("   Looking for 'Đăng tải tệp này' (Upload this file) button...")
        # --- [CALL HELPER] ---
        upload_button = _find_upload_file_button(driver)
        if not upload_button:
            print("   ❌ ERROR: Could not find 'Upload this file' button")
            return

        print("   ✅ Found upload button, clicking...")
        driver.execute_script("arguments[0].click();", upload_button)
        time.sleep(3)

        print("   Looking for 'Lưu những thay đổi' (Save changes) button...")
        # --- [CALL HELPER] ---
        save_button = _find_save_button(driver)
        if not save_button:
            print("   ❌ ERROR: Could not find 'Save changes' button")
            return

        print("   ✅ Found 'Save changes' button, clicking...")
        driver.execute_script("arguments[0].click();", save_button)
        time.sleep(4)

        print("   Verifying submission...")
        # --- [CALL HELPER] ---
        if _verify_submission_success(driver):
            print("   ✅ Homework submitted successfully!")
            # [TODO] Here you could email the user:
            # from scraper_service import send_email_notification
            # send_email_notification(f"Homework Submitted: {os.path.basename(file_path)}", "Your bot successfully submitted your homework.")
        else:
            print("   ❌ ERROR: Submission may have failed - please check manually")

    except Exception as e:
        print(f"   ❌ Error during homework submission: {e}")
        traceback.print_exc()
    finally:
        if driver:
            print("   Closing browser...")
            try:
                driver.quit()
            except:
                pass
        
        # Clean up the temporary file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"   🧹 Cleaned up temp file: {file_path}")
            except Exception as del_e:
                print(f"   ⚠️ Failed to delete temp file {file_path}: {del_e}")
        
        print("   ✅ Automated homework submission thread finished.")


def _perform_login(driver, username: str, password: str) -> bool:
    """
    Performs login to LMS.
    Handles both header login form and dedicated login page.
    Returns True if successful, False otherwise.
    """
    try:
        print("      Looking for username field...")

        # Look for username input (including header login form)
        username_selectors = [
            (By.ID, "inputName"),  # Header login form
            (By.ID, "username"),
            (By.NAME, "username"),
            (By.CSS_SELECTOR, "input[name='username']"),
            (By.XPATH, "//input[@placeholder='Username']"),
        ]

        username_field = None
        for by_type, selector in username_selectors:
            try:
                username_field = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((by_type, selector))
                )
                # Scroll into view and make visible
                driver.execute_script("arguments[0].scrollIntoView(true);", username_field)
                time.sleep(0.5)
                print(f"      ✅ Found username field using: {selector}")
                break
            except TimeoutException:
                continue

        if not username_field:
            print("      ❌ Could not find username field")
            return False

        # Enter username
        driver.execute_script("arguments[0].value = '';", username_field)  # Clear with JS
        username_field.send_keys(username)
        print(f"      ✅ Entered username: {username}")
        time.sleep(0.5)

        # Look for password input
        print("      Looking for password field...")
        password_selectors = [
            (By.ID, "inputPassword"),  # Header login form
            (By.ID, "password"),
            (By.NAME, "password"),
            (By.CSS_SELECTOR, "input[type='password']"),
            (By.XPATH, "//input[@placeholder='Password']"),
        ]

        password_field = None
        for by_type, selector in password_selectors:
            try:
                password_field = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((by_type, selector))
                )
                print(f"      ✅ Found password field using: {selector}")
                break
            except TimeoutException:
                continue

        if not password_field:
            print("      ❌ Could not find password field")
            return False

        # Enter password
        driver.execute_script("arguments[0].value = '';", password_field)  # Clear with JS
        password_field.send_keys(password)
        print("      ✅ Entered password")
        time.sleep(0.5)

        # Look for login button
        print("      Looking for login button...")
        login_button_selectors = [
            (By.ID, "submit"),  # Header login form
            (By.ID, "loginbtn"),
            (By.CSS_SELECTOR, "button[type='submit']#submit"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, "input[type='submit']"),
            (By.XPATH, "//button[@id='submit']"),
            (By.XPATH, "//button[contains(text(), 'Log in') or contains(text(), 'Đăng nhập')]"),
        ]

        login_button = None
        for by_type, selector in login_button_selectors:
            try:
                login_button = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((by_type, selector))
                )
                print(f"      ✅ Found login button using: {selector}")
                break
            except TimeoutException:
                continue

        if not login_button:
            print("      ❌ Could not find login button")
            # Try to submit the form directly
            try:
                print("      Trying to submit form directly...")
                password_field.submit()
                time.sleep(3)
            except:
                return False
        else:
            # Click login button
            driver.execute_script("arguments[0].click();", login_button)
            print("      ✅ Clicked login button")
            time.sleep(4)

        # Check if login was successful
        page_source = driver.page_source.lower()
        login_failed = (
            "login" in driver.current_url.lower() or
            "invalid login" in page_source or
            "incorrect username" in page_source or
            "guests cannot access" in page_source
        )

        if not login_failed:
            print("      ✅ Login successful")
            return True
        else:
            print("      ❌ Login failed - still showing login/guest page")
            return False

    except Exception as e:
        print(f"      ❌ Error during login: {e}")
        traceback.print_exc()
        return False


def _find_add_file_button(driver):
    """
    Finds the 'Thêm...' (Add) button that opens the file picker dialog.
    Returns the element if found, None otherwise.
    """
    try:
        # Multiple selectors for the add file button
        button_selectors = [
            # Vietnamese
            (By.XPATH, "//a[@role='button' and @title='Thêm...']"),
            (By.XPATH, "//a[contains(@class, 'fp-btn-add')]"),
            (By.CSS_SELECTOR, ".fp-btn-add a"),
            (By.CSS_SELECTOR, "div.fp-btn-add a[role='button']"),
            # English
            (By.XPATH, "//a[@role='button' and @title='Add...']"),
        ]

        for by_type, selector in button_selectors:
            try:
                element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((by_type, selector))
                )
                return element
            except TimeoutException:
                continue

        return None

    except Exception as e:
        print(f"      ⚠️ Error finding add file button: {e}")
        return None


def _find_file_picker_input(driver):
    """
    Finds the file input in the Moodle file picker dialog.
    Returns the element if found, None otherwise.
    """
    try:
        # Wait for file picker dialog to be visible
        time.sleep(1)

        # Multiple selectors for file input in file picker
        input_selectors = [
            # File input in upload form
            (By.CSS_SELECTOR, "form input[type='file'][name='repo_upload_file']"),
            (By.CSS_SELECTOR, ".fp-upload-form input[type='file']"),
            (By.CSS_SELECTOR, ".fp-file input[type='file']"),
            (By.CSS_SELECTOR, "input[type='file']"),
            (By.NAME, "repo_upload_file"),
        ]

        for by_type, selector in input_selectors:
            try:
                element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((by_type, selector))
                )
                # Make sure it's visible/interactable
                if element.is_displayed() or element.get_attribute('type') == 'file':
                    return element
            except TimeoutException:
                continue

        return None

    except Exception as e:
        print(f"      ⚠️ Error finding file picker input: {e}")
        return None


def _find_upload_file_button(driver):
    """
    Finds the 'Đăng tải tệp này' (Upload this file) button in file picker.
    Returns the element if found, None otherwise.
    """
    try:
        # Multiple selectors for upload button
        button_selectors = [
            # Vietnamese
            (By.XPATH, "//button[contains(text(), 'Đăng tải tệp này')]"),
            (By.XPATH, "//button[contains(@class, 'fp-upload-btn')]"),
            (By.CSS_SELECTOR, "button.fp-upload-btn"),
            # English
            (By.XPATH, "//button[contains(text(), 'Upload this file')]"),
        ]

        for by_type, selector in button_selectors:
            try:
                element = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((by_type, selector))
                )
                return element
            except TimeoutException:
                continue

        return None

    except Exception as e:
        print(f"      ⚠️ Error finding upload button: {e}")
        return None


def _try_direct_file_upload(driver, file_path, assignment_url):
    """
    Fallback method: Try direct file upload if file picker button not found.
    """
    try:
        print("   Attempting direct file upload...")

        # Look for any file input on the page
        file_input = _find_file_input(driver)
        if not file_input:
            return {
                "success": False,
                "error": "Could not find any file upload input on the page"
            }

        print(f"   ✅ Found file input, uploading: {file_path}")
        file_input.send_keys(file_path)
        time.sleep(2)

        # Try to find and click save button
        save_button = _find_save_button(driver)
        if save_button:
            print("   ✅ Found save button, clicking...")
            driver.execute_script("arguments[0].click();", save_button)
            time.sleep(3)

            # Verify submission
            if _verify_submission_success(driver):
                print("   ✅ Homework submitted successfully!")
                return {
                    "success": True,
                    "message": "Homework submitted successfully"
                }

        return {
            "success": False,
            "error": "Could not complete direct file upload"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Direct upload failed: {str(e)}"
        }


def _find_submission_button(driver):
    """
    Finds either "Add submission" (Thêm bài nộp) or "Edit submission" (Sửa bài nộp) button.
    Returns the element if found, None otherwise.
    """
    try:
        # Multiple selectors for both add and edit submission buttons
        button_selectors = [
            # Vietnamese - Add submission
            (By.XPATH, "//button[contains(text(), 'Thêm bài nộp')]"),
            (By.XPATH, "//a[contains(text(), 'Thêm bài nộp')]"),
            # Vietnamese - Edit submission
            (By.XPATH, "//button[contains(text(), 'Sửa bài nộp')]"),
            (By.XPATH, "//a[contains(text(), 'Sửa bài nộp')]"),
            (By.XPATH, "//button[contains(text(), 'Sửa bài làm')]"),
            (By.XPATH, "//a[contains(text(), 'Sửa bài làm')]"),
            # English - Add submission
            (By.XPATH, "//button[contains(text(), 'Add submission')]"),
            (By.XPATH, "//a[contains(text(), 'Add submission')]"),
            # English - Edit submission
            (By.XPATH, "//button[contains(text(), 'Edit submission')]"),
            (By.XPATH, "//a[contains(text(), 'Edit submission')]"),
            # By form action
            (By.CSS_SELECTOR, "form[action*='editsubmission'] button[type='submit']"),
            (By.CSS_SELECTOR, "a[href*='action=editsubmission']"),
        ]

        for by_type, selector in button_selectors:
            try:
                element = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((by_type, selector))
                )
                return element
            except TimeoutException:
                continue

        return None

    except Exception as e:
        print(f"      ⚠️ Error finding submission button: {e}")
        return None


def _find_file_input(driver):
    """
    Finds the file upload input element.
    Returns the element if found, None otherwise.
    """
    try:
        # Multiple selectors for file input
        file_input_selectors = [
            (By.CSS_SELECTOR, "input[type='file']"),
            (By.CSS_SELECTOR, "input[name*='file']"),
            (By.XPATH, "//input[@type='file']")
        ]

        for by_type, selector in file_input_selectors:
            try:
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((by_type, selector))
                )
                # Make sure it's visible or can accept input
                return element
            except TimeoutException:
                continue

        return None

    except Exception as e:
        print(f"      ⚠️ Error finding file input: {e}")
        return None


def _find_save_button(driver):
    """
    Finds the 'Save changes' button.
    Returns the element if found, None otherwise.
    """
    try:
        # Multiple selectors for save button
        save_button_selectors = [
            # Vietnamese text
            (By.XPATH, "//button[contains(text(), 'Lưu thay đổi')]"),
            (By.XPATH, "//input[@value='Lưu thay đổi']"),
            # English text
            (By.XPATH, "//button[contains(text(), 'Save changes')]"),
            (By.XPATH, "//input[@value='Save changes']"),
            # By ID or name
            (By.ID, "id_submitbutton"),
            (By.NAME, "submitbutton"),
            # Generic submit button in form
            (By.CSS_SELECTOR, "form button[type='submit']"),
            (By.CSS_SELECTOR, "form input[type='submit']")
        ]

        for by_type, selector in save_button_selectors:
            try:
                element = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((by_type, selector))
                )
                return element
            except TimeoutException:
                continue

        return None

    except Exception as e:
        print(f"      ⚠️ Error finding save button: {e}")
        return None


def _verify_submission_success(driver) -> bool:
    """
    Verifies that the submission was successful by checking for success indicators.
    Returns True if submission appears successful, False otherwise.
    """
    try:
        # Check for success indicators
        success_indicators = [
            # Check for "Submitted for grading" text (Vietnamese)
            (By.XPATH, "//*[contains(text(), 'Đã nộp để chấm điểm')]"),
            # Check for "Submitted for grading" text (English)
            (By.XPATH, "//*[contains(text(), 'Submitted for grading')]"),
            # Check for submission status table
            (By.CLASS_NAME, "submissionstatustable"),
            # Check if back on view page (not edit page)
            (By.XPATH, "//button[contains(text(), 'Sửa bài làm') or contains(text(), 'Edit submission')]")
        ]

        for by_type, selector in success_indicators:
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((by_type, selector))
                )
                return True
            except TimeoutException:
                continue

        # If we're not on an edit page, assume success
        if "editsubmission" not in driver.current_url:
            return True

        return False

    except Exception as e:
        print(f"      ⚠️ Error verifying submission: {e}")
        return False
