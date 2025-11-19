#!/usr/bin/env python3
"""
Quick API endpoint tester for Learning Insights
Tests all endpoints to ensure they return correct data structures
"""

import requests
import json
from datetime import datetime, date, timedelta
import sys

# Configuration
API_BASE = "http://127.0.0.1:5000"
TEST_USERNAME = "2201040165"
TEST_PASSWORD = "Evsthai234@"

def print_header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def print_result(test_name, success, data=None, error=None):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {test_name}")
    if data:
        print(f"  Data: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}...")
    if error:
        print(f"  Error: {error}")
    print()

def test_login():
    """Test user login"""
    print_header("TEST 1: USER LOGIN")
    try:
        response = requests.post(
            f"{API_BASE}/api/login",
            json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get('token')
            print_result("Login", True, {"token": token[:20] + "..."})
            return token
        else:
            print_result("Login", False, error=response.text[:100])
            return None
    except Exception as e:
        print_result("Login", False, error=str(e))
        return None

def test_endpoints(token):
    """Test all insights endpoints"""
    if not token:
        print("❌ Cannot test endpoints without token")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print_header("TEST 2: GET COURSES")
    try:
        response = requests.get(f"{API_BASE}/api/courses", headers=headers)
        if response.status_code == 200:
            courses = response.json()
            if courses:
                course_id = courses[0]['id']
                print_result("Get Courses", True, {"count": len(courses), "first": courses[0]})
            else:
                print_result("Get Courses", True, {"count": 0, "note": "No courses yet"})
                return
        else:
            print_result("Get Courses", False, error=response.text[:100])
            return
    except Exception as e:
        print_result("Get Courses", False, error=str(e))
        return
    
    print_header("TEST 3: GET DASHBOARD")
    try:
        response = requests.get(f"{API_BASE}/api/insights/dashboard", headers=headers)
        if response.status_code == 200:
            dashboard = response.json()
            print_result("Get Dashboard", True, {
                "success": dashboard.get('success'),
                "has_dashboard": bool(dashboard.get('dashboard')),
                "dashboard_keys": list(dashboard.get('dashboard', {}).keys()) if dashboard.get('dashboard') else []
            })
        else:
            print_result("Get Dashboard", False, error=response.text[:100])
    except Exception as e:
        print_result("Get Dashboard", False, error=str(e))
    
    print_header("TEST 4: GET ALL PROGRESS")
    try:
        response = requests.get(f"{API_BASE}/api/insights/progress/all", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print_result("Get All Progress", True, {
                "success": data.get('success'),
                "total_courses": data.get('total_courses'),
                "data_count": len(data.get('data', []))
            })
        else:
            print_result("Get All Progress", False, error=response.text[:100])
    except Exception as e:
        print_result("Get All Progress", False, error=str(e))
    
    print_header("TEST 5: GET ALERTS")
    try:
        response = requests.get(f"{API_BASE}/api/insights/alerts", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print_result("Get Alerts", True, {
                "success": data.get('success'),
                "alert_count": data.get('alert_count'),
                "alerts": data.get('alerts', [])[:2]
            })
        else:
            print_result("Get Alerts", False, error=response.text[:100])
    except Exception as e:
        print_result("Get Alerts", False, error=str(e))
    
    print_header("TEST 6: UPDATE PROGRESS")
    try:
        payload = {
            "course_db_id": course_id,
            "completed_topics": 5,
            "total_topics": 10
        }
        response = requests.post(
            f"{API_BASE}/api/insights/progress/update",
            json=payload,
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            print_result("Update Progress", True, {
                "success": data.get('success'),
                "progress_percentage": data.get('progress_percentage'),
                "is_behind_schedule": data.get('is_behind_schedule')
            })
        else:
            print_result("Update Progress", False, error=response.text[:100])
    except Exception as e:
        print_result("Update Progress", False, error=str(e))
    
    print_header("TEST 7: GET HABITS")
    try:
        response = requests.get(f"{API_BASE}/api/insights/habits", headers=headers)
        if response.status_code == 200:
            data = response.json()
            has_analysis = bool(data.get('analysis') or data.get('success') == False)
            print_result("Get Habits", True, {
                "success": data.get('success'),
                "has_analysis": has_analysis,
                "message": data.get('message', 'N/A')
            })
        else:
            print_result("Get Habits", False, error=response.text[:100])
    except Exception as e:
        print_result("Get Habits", False, error=str(e))
    
    print_header("TEST 8: LOG STUDY SESSION")
    try:
        today = date.today().isoformat()
        payload = {
            "course_db_id": course_id,
            "session_date": today,
            "start_time": "14:00:00",
            "end_time": "15:30:00",
            "topics_studied": "Arrays, Linked Lists",
            "content_type": "video",
            "difficulty_level": "medium",
            "focus_score": 85.0
        }
        response = requests.post(
            f"{API_BASE}/api/insights/session/log",
            json=payload,
            headers=headers
        )
        if response.status_code == 201:
            data = response.json()
            print_result("Log Study Session", True, {
                "success": data.get('success'),
                "session_id": data.get('session_id'),
                "duration": data.get('duration_minutes')
            })
        else:
            print_result("Log Study Session", False, error=response.text[:100])
    except Exception as e:
        print_result("Log Study Session", False, error=str(e))
    
    print_header("TEST 9: GET WEEKLY COMPARISON")
    try:
        response = requests.get(
            f"{API_BASE}/api/insights/weekly/compare/{course_id}",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            print_result("Get Weekly Comparison", True, {
                "success": data.get('success'),
                "has_trends": bool(data.get('trends')),
                "has_insights": bool(data.get('insights')),
                "message": data.get('message', 'N/A')
            })
        else:
            print_result("Get Weekly Comparison", False, error=response.text[:100])
    except Exception as e:
        print_result("Get Weekly Comparison", False, error=str(e))
    
    print_header("TEST 10: GET RECOMMENDATIONS")
    try:
        response = requests.get(f"{API_BASE}/api/insights/recommendations", headers=headers)
        if response.status_code == 200:
            data = response.json()
            print_result("Get Recommendations", True, {
                "success": data.get('success'),
                "recommendations_count": data.get('recommendations_count'),
                "recommendations_sample": data.get('recommendations', [])[:1]
            })
        else:
            print_result("Get Recommendations", False, error=response.text[:100])
    except Exception as e:
        print_result("Get Recommendations", False, error=str(e))
    
    print_header("TEST 11: GENERATE RECOMMENDATIONS")
    try:
        response = requests.post(
            f"{API_BASE}/api/insights/recommendations/generate",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            print_result("Generate Recommendations", True, {
                "success": data.get('success'),
                "recommendations_count": data.get('recommendations_count')
            })
        else:
            print_result("Generate Recommendations", False, error=response.text[:100])
    except Exception as e:
        print_result("Generate Recommendations", False, error=str(e))

def main():
    print("\n🧪 LEARNING INSIGHTS API TEST SUITE")
    print(f"Testing: {API_BASE}\n")
    
    # Test login
    token = test_login()
    if token:
        # Test endpoints
        test_endpoints(token)
    
    print("\n" + "="*60)
    print("✅ TEST SUITE COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()