"""
Test script for AI Learning Insights API endpoints
"""

import requests
import json
import sys
from datetime import datetime, timedelta

# Fix encoding for Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:5000"

# Test user credentials
TEST_USERNAME = "2201040165"
TEST_PASSWORD = "123456"

def login():
    """Login and get JWT token"""
    print("[*] Logging in...")
    response = requests.post(
        f"{BASE_URL}/api/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    if response.status_code == 200:
        token = response.json().get('token')
        print(f"[OK] Login successful. Token: {token[:20]}...")
        return token
    else:
        print(f"[ERROR] Login failed: {response.text}")
        return None

def get_headers(token):
    """Get request headers with token"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def test_progress_endpoints(token):
    """Test learning progress endpoints"""
    print("\n[TEST] Testing Progress Endpoints...")
    headers = get_headers(token)
    
    # Test 1: Update progress
    print("  [1] Updating progress for course 1...")
    response = requests.post(
        f"{BASE_URL}/api/insights/progress/update",
        headers=headers,
        json={
            "course_db_id": 1,
            "completed_topics": 5,
            "total_topics": 10
        }
    )
    print(f"      Status: {response.status_code} | Response: {response.json()}")
    
    # Test 2: Get progress for course
    print("  [2] Getting progress for course 1...")
    response = requests.get(
        f"{BASE_URL}/api/insights/progress/1",
        headers=headers
    )
    print(f"      Status: {response.status_code}")
    if response.status_code == 200:
        print(f"      Data: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"      Error: {response.json()}")
    
    # Test 3: Get all progress
    print("  [3] Getting all progress...")
    response = requests.get(
        f"{BASE_URL}/api/insights/progress/all",
        headers=headers
    )
    print(f"      Status: {response.status_code} | Count: {response.json().get('total_courses', 0)}")

def test_habits_endpoints(token):
    """Test learning habits endpoints"""
    print("\n[TEST] Testing Habits Endpoints...")
    headers = get_headers(token)
    
    # Test 1: Log study session
    print("  [1] Logging study session...")
    today = datetime.now().strftime("%Y-%m-%d")
    response = requests.post(
        f"{BASE_URL}/api/insights/session/log",
        headers=headers,
        json={
            "course_db_id": 1,
            "session_date": today,
            "start_time": "14:00:00",
            "end_time": "15:30:00",
            "topics_studied": "Arrays, Linked Lists",
            "content_type": "video",
            "difficulty_level": "medium",
            "focus_score": 85.0
        }
    )
    print(f"      Status: {response.status_code} | Response: {response.json()}")
    
    # Test 2: Analyze learning habits
    print("  [2] Analyzing learning habits...")
    response = requests.get(
        f"{BASE_URL}/api/insights/habits",
        headers=headers
    )
    print(f"      Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"      Success: {data.get('success')}")
        if data.get('analysis'):
            print(f"      Peak Study Hour: {data['analysis'].get('peak_study_hour')}")
            print(f"      Most Productive Day: {data['analysis'].get('most_productive_day')}")
    else:
        print(f"      Error: {response.json()}")

def test_alerts_endpoints(token):
    """Test alert endpoints"""
    print("\n[TEST] Testing Alert Endpoints...")
    headers = get_headers(token)
    
    # Test: Get alerts
    print("  Checking for behind-schedule alerts...")
    response = requests.get(
        f"{BASE_URL}/api/insights/alerts",
        headers=headers
    )
    print(f"      Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"      Alert Count: {data.get('alert_count', 0)}")
        for alert in data.get('alerts', []):
            print(f"      - {alert['course']}: {alert['message']}")

def test_weak_topics_endpoints(token):
    """Test weak topics endpoints"""
    print("\n[TEST] Testing Weak Topics Endpoints...")
    headers = get_headers(token)
    
    # Test 1: Add weak topic
    print("  [1] Adding weak topic...")
    response = requests.post(
        f"{BASE_URL}/api/insights/weak-topics/add",
        headers=headers,
        json={
            "course_db_id": 1,
            "topic_name": "Recursion",
            "last_quiz_score": 45.5
        }
    )
    print(f"      Status: {response.status_code} | Response: {response.json()}")

def test_recommendations_endpoints(token):
    """Test recommendation endpoints"""
    print("\n[TEST] Testing Recommendation Endpoints...")
    headers = get_headers(token)
    
    # Test 1: Get active recommendations
    print("  [1] Getting active recommendations...")
    response = requests.get(
        f"{BASE_URL}/api/insights/recommendations",
        headers=headers
    )
    print(f"      Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"      Count: {data.get('recommendations_count', 0)}")
        for rec in data.get('recommendations', [])[:2]:  # Show first 2
            print(f"      - {rec.get('title', 'N/A')}")

def test_dashboard_endpoint(token):
    """Test comprehensive dashboard endpoint"""
    print("\n[TEST] Testing Dashboard Endpoint...")
    headers = get_headers(token)
    
    response = requests.get(
        f"{BASE_URL}/api/insights/dashboard",
        headers=headers
    )
    print(f"      Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        dashboard = data.get('dashboard', {})
        print(f"      Courses in progress: {len(dashboard.get('progress', []))}")
        print(f"      Active alerts: {len(dashboard.get('alerts', []))}")
        print(f"      Active recommendations: {len(dashboard.get('recommendations', []))}")

def main():
    print("=" * 60)
    print("[START] AI Learning Insights API Test Suite")
    print("=" * 60)
    
    # Login
    token = login()
    if not token:
        print("[ERROR] Cannot proceed without valid token")
        return
    
    # Run test suites
    test_progress_endpoints(token)
    test_habits_endpoints(token)
    test_alerts_endpoints(token)
    test_weak_topics_endpoints(token)
    test_recommendations_endpoints(token)
    test_dashboard_endpoint(token)
    
    print("\n" + "=" * 60)
    print("[OK] Test suite completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()