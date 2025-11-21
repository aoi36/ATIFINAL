"""
Learning Insights Service - COMPLETE VERSION
Provides AI-powered learning analytics and personalized recommendations
NOW: Uses Gemini AI to generate personalized recommendations based on learning data
"""

import json
import re
import time
import traceback
from datetime import datetime, timedelta, date
from database import get_db
from ai_service import ai_client  # Import Gemini client

# ===== FEATURE 1: TRACK PROGRESS & ALERT DELAYS =====

def update_learning_progress(user_id, course_db_id, completed_topics, total_topics):
    """
    Updates the learning progress for a user in a specific course.
    Calculates progress percentage and checks if user is behind schedule.
    
    Args:
        user_id: User ID
        course_db_id: Course database ID
        completed_topics: Number of topics completed
        total_topics: Total number of topics in course
    
    Returns:
        dict with progress info and alert status
    """
    try:
        db = get_db()
        
        # Validate inputs
        completed_topics = int(completed_topics)
        total_topics = int(total_topics)
        
        if total_topics <= 0:
            return {"success": False, "error": "Total topics must be greater than 0"}
        
        if completed_topics < 0:
            return {"success": False, "error": "Completed topics cannot be negative"}
        
        if completed_topics > total_topics:
            return {"success": False, "error": "Completed topics cannot exceed total topics"}
        
        progress_percentage = (completed_topics / total_topics * 100) if total_topics > 0 else 0
        
        # Calculate expected progress (assuming linear progress over course duration)
        # For now, we'll consider user behind if less than 50% at midpoint
        is_behind = 1 if progress_percentage < 50 else 0
        
        print(f"[Learning Insights] Updating progress for user {user_id}, course {course_db_id}: {completed_topics}/{total_topics} ({progress_percentage:.1f}%)")
        
        # First check if record exists
        existing = db.execute("""SELECT id FROM learning_progress WHERE user_id = ? AND course_db_id = ?""", (user_id, course_db_id)).fetchone()
        
        if existing:
            # Update existing record
            print(f"[Learning Insights] Updating existing record (id={existing['id']})")
            db.execute("""
                UPDATE learning_progress 
                SET completed_topics = ?, total_topics = ?, progress_percentage = ?, 
                    is_behind_schedule = ?, last_updated = CURRENT_TIMESTAMP
                WHERE user_id = ? AND course_db_id = ?
            """, (completed_topics, total_topics, progress_percentage, is_behind, user_id, course_db_id))
        else:
            # Insert new record
            print(f"[Learning Insights] Inserting new record")
            db.execute("""
                INSERT INTO learning_progress 
                (user_id, course_db_id, completed_topics, total_topics, progress_percentage, is_behind_schedule, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, course_db_id, completed_topics, total_topics, progress_percentage, is_behind))
        
        db.commit()
        
        print(f"[Learning Insights] Progress updated successfully. Verifying...")
        
        # Verify the update
        verify = db.execute("""SELECT * FROM learning_progress WHERE user_id = ? AND course_db_id = ?""", (user_id, course_db_id)).fetchone()
        
        if verify:
            print(f"[Learning Insights] Verification successful: {dict(verify)}")
        
        result = {
            "success": True,
            "progress_percentage": progress_percentage,
            "is_behind_schedule": bool(is_behind),
            "completed_topics": completed_topics,
            "total_topics": total_topics
        }
        
        if is_behind:
            result["alert"] = "⚠️ Bạn đang chậm so với kế hoạch. Hãy tăng tốc độ học tập!"
        
        return result
    except Exception as e:
        print(f"[Learning Insights] Error updating progress: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def get_progress_by_course(user_id, course_db_id):
    """
    Retrieves current learning progress for a course.
    
    Args:
        user_id: User ID
        course_db_id: Course database ID
    
    Returns:
        Progress data or None if not found
    """
    try:
        db = get_db()
        row = db.execute("""SELECT * FROM learning_progress WHERE user_id = ? AND course_db_id = ?""", (user_id, course_db_id)).fetchone()
        
        if row:
            return dict(row)
        return None
    except Exception as e:
        print(f"[Learning Insights] Error fetching progress: {e}")
        return None


def get_all_user_progress(user_id):
    """
    Retrieves all learning progress for a user across all courses.
    
    Args:
        user_id: User ID
    
    Returns:
        List of progress records with course names
    """
    try:
        db = get_db()
        rows = db.execute("""
            SELECT lp.*, c.name as course_name
            FROM learning_progress lp
            JOIN courses c ON lp.course_db_id = c.id
            WHERE lp.user_id = ?
            ORDER BY lp.progress_percentage DESC
        """, (user_id,)).fetchall()
        
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[Learning Insights] Error fetching all progress: {e}")
        return []


def check_behind_schedule_alerts(user_id):
    """
    Checks all courses and returns alerts for courses where user is behind.
    
    Args:
        user_id: User ID
    
    Returns:
        List of alert messages
    """
    try:
        progress_list = get_all_user_progress(user_id)
        alerts = []
        
        for progress in progress_list:
            if progress['is_behind_schedule']:
                alert = {
                    "course": progress['course_name'],
                    "progress": f"{progress['progress_percentage']:.1f}%",
                    "message": f"⚠️ Bạn đang chậm so với kế hoạch trong {progress['course_name']} ({progress['progress_percentage']:.1f}% hoàn thành)",
                    "severity": "high" if progress['progress_percentage'] < 30 else "medium"
                }
                alerts.append(alert)
        
        return alerts
    except Exception as e:
        print(f"[Learning Insights] Error checking alerts: {e}")
        return []


# ===== FEATURE 2: ANALYZE LEARNING HABITS =====

def log_study_session(user_id, course_db_id, session_date, start_time, end_time, 
                     topics_studied, content_type, difficulty_level, focus_score=0.0):
    """
    Records a study session for later analysis.
    
    Args:
        user_id: User ID
        course_db_id: Course database ID
        session_date: Date of session (YYYY-MM-DD)
        start_time: Start time (HH:MM:SS)
        end_time: End time (HH:MM:SS)
        topics_studied: Comma-separated list of topics or JSON string
        content_type: Type of content (video, reading, practice, etc.)
        difficulty_level: Difficulty (easy, medium, hard)
        focus_score: Score from 0-100 indicating user focus level
    
    Returns:
        dict with session ID or error
    """
    try:
        # Calculate duration in minutes
        from datetime import datetime as dt
        start = dt.strptime(start_time, "%H:%M:%S")
        end = dt.strptime(end_time, "%H:%M:%S")
        duration = int((end - start).total_seconds() / 60)
        
        if duration < 0:
            duration += 24 * 60  # Handle midnight crossing
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("""
            INSERT INTO study_sessions 
            (user_id, course_db_id, session_date, start_time, end_time, duration_minutes,
             topics_studied, content_type, difficulty_level, focus_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, course_db_id, session_date, start_time, end_time, duration,
              topics_studied, content_type, difficulty_level, focus_score))
        
        db.commit()
        
        print(f"[Learning Insights] Logged study session: {duration} minutes for user {user_id}")
        return {
            "success": True,
            "session_id": cursor.lastrowid,
            "duration_minutes": duration
        }
    except Exception as e:
        print(f"[Learning Insights] Error logging session: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def analyze_learning_habits(user_id):
    """
    Analyzes study patterns and suggests optimal study times.
    
    Args:
        user_id: User ID
    
    Returns:
        dict with habit analysis and recommendations
    """
    try:
        db = get_db()
        
        # Get last 30 days of study sessions
        thirty_days_ago = (date.today() - timedelta(days=30)).isoformat()
        
        sessions = db.execute("""
            SELECT * FROM study_sessions
            WHERE user_id = ? AND session_date >= ?
            ORDER BY session_date, start_time
        """, (user_id, thirty_days_ago)).fetchall()
        
        if not sessions:
            return {
                "success": False,
                "message": "Chưa đủ dữ liệu. Hãy ghi lại các session học để phân tích thói quen.",
                "recommendations": []
            }
        
        # Analyze habits
        time_slots = {}  # Hour -> count
        days_of_week = {}  # Day -> count
        content_types = {}  # Type -> count
        total_duration = 0
        focus_scores = []
        
        for session in sessions:
            # Parse start time hour
            hour = int(session['start_time'].split(':')[0])
            time_slots[hour] = time_slots.get(hour, 0) + 1
            
            # Parse day of week
            session_date = datetime.strptime(session['session_date'], "%Y-%m-%d")
            day_name = session_date.strftime("%A")
            days_of_week[day_name] = days_of_week.get(day_name, 0) + 1
            
            # Content type
            content_types[session['content_type']] = content_types.get(session['content_type'], 0) + 1
            
            total_duration += session['duration_minutes']
            if session['focus_score'] > 0:
                focus_scores.append(session['focus_score'])
        
        # Find optimal times
        peak_hour = max(time_slots, key=time_slots.get) if time_slots else 14
        most_productive_day = max(days_of_week, key=days_of_week.get) if days_of_week else "Monday"
        preferred_content = max(content_types, key=content_types.get) if content_types else "mixed"
        
        avg_session_duration = total_duration // len(sessions) if sessions else 0
        avg_focus = sum(focus_scores) / len(focus_scores) if focus_scores else 0.0
        avg_daily_hours = total_duration / 30 / 60  # Over 30 days
        
        # Save patterns
        db.execute("""INSERT OR REPLACE INTO learning_patterns
            (user_id, preferred_study_time, optimal_session_duration, most_productive_day,
             preferred_content_type, average_daily_study_hours, peak_focus_hours, last_analyzed)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (user_id, f"{peak_hour}:00", avg_session_duration, most_productive_day,
              preferred_content, avg_daily_hours, f"{peak_hour-1}-{peak_hour+2}"))
        
        db.commit()
        
        recommendations = []
        if avg_daily_hours < 1:
            recommendations.append("📚 Tăng thời gian học tập hàng ngày. Hiện tại bạn chỉ học ~{:.1f} giờ/ngày.".format(avg_daily_hours))
        if avg_focus < 60:
            recommendations.append("🎯 Tập trung tốt hơn. Điểm tập trung trung bình của bạn là {:.0f}/100.".format(avg_focus))
        
        return {
            "success": True,
            "analysis": {
                "peak_study_hour": f"{peak_hour:02d}:00",
                "most_productive_day": most_productive_day,
                "preferred_content_type": preferred_content,
                "average_session_duration_minutes": avg_session_duration,
                "average_daily_study_hours": f"{avg_daily_hours:.2f}",
                "average_focus_score": f"{avg_focus:.1f}/100",
                "total_sessions_30days": len(sessions),
                "time_distribution": time_slots,
                "day_distribution": days_of_week
            },
            "recommendations": recommendations
        }
    except Exception as e:
        print(f"[Learning Insights] Error analyzing habits: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}


# ===== FEATURE 3: COMPARE WEEKLY RESULTS =====

def log_weekly_stats(user_id, course_db_id, week_start_date, week_end_date, 
                    total_study_hours, sessions_count, topics_completed, 
                    quiz_average_score=0.0):
    """
    Records weekly statistics for trend analysis.
    
    Args:
        user_id: User ID
        course_db_id: Course database ID
        week_start_date: Start of week (YYYY-MM-DD)
        week_end_date: End of week (YYYY-MM-DD)
        total_study_hours: Total study hours this week
        sessions_count: Number of study sessions
        topics_completed: Number of topics completed
        quiz_average_score: Average quiz score
    
    Returns:
        dict with success status
    """
    try:
        db = get_db()
        
        # Calculate average focus score from study sessions in this week
        sessions = db.execute("""SELECT AVG(focus_score) as avg_focus FROM study_sessions WHERE user_id = ? AND course_db_id = ? AND session_date BETWEEN ? AND ?""", (user_id, course_db_id, week_start_date, week_end_date)).fetchone()
        
        avg_focus = sessions['avg_focus'] if sessions['avg_focus'] else 0.0
        
        db.execute("""INSERT OR REPLACE INTO weekly_stats
            (user_id, course_db_id, week_start_date, week_end_date, total_study_hours,
             sessions_count, topics_completed, average_focus_score, quiz_average_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, course_db_id, week_start_date, week_end_date, total_study_hours,
              sessions_count, topics_completed, avg_focus, quiz_average_score))
        
        db.commit()
        
        print(f"[Learning Insights] Logged weekly stats for user {user_id}, course {course_db_id}")
        return {"success": True}
    except Exception as e:
        print(f"[Learning Insights] Error logging weekly stats: {e}")
        return {"success": False, "error": str(e)}


def compare_weekly_progress(user_id, course_db_id):
    """
    Compares weekly results to identify trends and improvement areas.
    Now calculates from sessions if weekly_stats table is empty
    
    Args:
        user_id: User ID
        course_db_id: Course database ID
    
    Returns:
        dict with trend analysis and weak topics
    """
    try:
        db = get_db()
        
        # Get last 4 weeks of stats
        stats = db.execute("""SELECT * FROM weekly_stats WHERE user_id = ? AND course_db_id = ? ORDER BY week_start_date DESC LIMIT 4""", (user_id, course_db_id)).fetchall()
        
        stats_list = [dict(row) for row in stats]
        
        if not stats_list or len(stats_list) == 0:
            stats_list = calculate_weekly_stats_from_sessions(user_id, course_db_id, db)
        
        if not stats_list or len(stats_list) == 0:
            return {
                "success": False,
                "message": "Chưa có dữ liệu thống kê hàng tuần. Vui lòng ghi lại các session học."
            }
        
        # Reverse to get oldest first
        stats_list = list(reversed(stats_list))
        
        # Analyze trends
        trends = {
            "study_hours_trend": [],
            "quiz_score_trend": [],
            "topics_completed_trend": []
        }
        
        insights = []
        
        for stat in stats_list:
            trends["study_hours_trend"].append(float(stat.get('total_study_hours', 0)))
            trends["quiz_score_trend"].append(float(stat.get('quiz_average_score', 0)))
            trends["topics_completed_trend"].append(int(stat.get('topics_completed', 0)))
        
        # Check if improving or declining
        if len(trends["study_hours_trend"]) >= 2:
            if trends["study_hours_trend"][-1] > trends["study_hours_trend"][-2]:
                insights.append("📈 Thời gian học tập tăng so với tuần trước. Tuyệt vời!")
            elif trends["study_hours_trend"][-1] < trends["study_hours_trend"][-2]:
                insights.append("📉 Thời gian học tập giảm. Cố gắng tăng đặc biệt vào những ngày bận.")
        
        if len(trends["quiz_score_trend"]) >= 2:
            if trends["quiz_score_trend"][-1] > trends["quiz_score_trend"][-2]:
                insights.append("🎯 Điểm bài kiểm tra tăng! Bạn đang cải thiện.")
            elif trends["quiz_score_trend"][-1] < trends["quiz_score_trend"][-2] and trends["quiz_score_trend"][-1] > 0:
                insights.append("⚠️ Điểm bài kiểm tra giảm. Xem xét ôn tập lại những chủ đề khó.")
        
        return {
            "success": True,
            "trends": trends,
            "latest_week": stats_list[-1] if stats_list else None,
            "previous_weeks": stats_list[:-1] if len(stats_list) > 1 else [],
            "insights": insights
        }
    except Exception as e:
        print(f"[Learning Insights] Error comparing weekly progress: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def calculate_weekly_stats_from_sessions(user_id, course_db_id, db):
    """
    Calculates weekly stats from session data when weekly_stats table is empty
    
    Args:
        user_id: User ID
        course_db_id: Course database ID
        db: Database connection
    
    Returns:
        List of weekly stats calculated from sessions
    """
    try:
        # Get all sessions for this course in last 4 weeks
        four_weeks_ago = (date.today() - timedelta(days=28)).isoformat()
        
        sessions = db.execute("""SELECT * FROM study_sessions WHERE user_id = ? AND course_db_id = ? AND session_date >= ? ORDER BY session_date""", (user_id, course_db_id, four_weeks_ago)).fetchall()
        
        if not sessions:
            return []
        
        # Group sessions by week
        weekly_data = {}
        
        for session in sessions:
            session_date = datetime.strptime(session['session_date'], "%Y-%m-%d")
            # Monday of this week
            week_start = session_date - timedelta(days=session_date.weekday())
            week_key = week_start.isoformat()
            
            if week_key not in weekly_data:
                weekly_data[week_key] = {
                    'week_start': week_key,
                    'total_study_hours': 0,
                    'sessions_count': 0,
                    'topics_completed': 0,
                    'quiz_average_score': 0.0,
                    'total_focus_score': 0.0,
                    'focus_count': 0
                }
            
            weekly_data[week_key]['total_study_hours'] += session['duration_minutes'] / 60
            weekly_data[week_key]['sessions_count'] += 1
            
            if session['focus_score'] and session['focus_score'] > 0:
                weekly_data[week_key]['total_focus_score'] += session['focus_score']
                weekly_data[week_key]['focus_count'] += 1
        
        # Calculate averages and convert to list
        result = []
        for week_key in sorted(weekly_data.keys()):
            data = weekly_data[week_key]
            avg_focus = data['total_focus_score'] / data['focus_count'] if data['focus_count'] > 0 else 0.0
            
            result.append({
                'week_start_date': data['week_start'],
                'week_end_date': (datetime.fromisoformat(data['week_start']) + timedelta(days=6)).isoformat(),
                'total_study_hours': round(data['total_study_hours'], 2),
                'sessions_count': data['sessions_count'],
                'topics_completed': data['topics_completed'],
                'quiz_average_score': 0.0,
                'average_focus_score': round(avg_focus, 1)
            })
        
        return result[-4:] if len(result) > 4 else result  # Return last 4 weeks
    except Exception as e:
        print(f"[Learning Insights] Error calculating weekly stats: {e}")
        return []


# ===== FEATURE 4: PERSONALIZED RECOMMENDATIONS =====

def add_weak_topic(user_id, course_db_id, topic_name, last_quiz_score):
    """
    Records a topic that the user struggled with.
    
    Args:
        user_id: User ID
        course_db_id: Course database ID
        topic_name: Name of the topic
        last_quiz_score: Quiz score on that topic
    
    Returns:
        dict with success status
    """
    try:
        db = get_db()
        
        cursor = db.cursor()
        cursor.execute("""INSERT OR REPLACE INTO weak_topics (user_id, course_db_id, topic_name, last_quiz_score, attempts_count, last_attempted) VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)""", (user_id, course_db_id, topic_name, last_quiz_score))
        
        db.commit()
        
        print(f"[Learning Insights] Added weak topic '{topic_name}' for user {user_id}")
        return {"success": True, "topic_id": cursor.lastrowid}
    except Exception as e:
        print(f"[Learning Insights] Error adding weak topic: {e}")
        return {"success": False, "error": str(e)}

def generate_personalized_recommendations(user_id):
    """
    Generates personalized recommendations based on all learning data using Gemini AI.
    
    Args:
        user_id: User ID
    
    Returns:
        dict with list of recommendations
    """
    try:
        db = get_db()
        
        # Gather all learning data
        progress_list = get_all_user_progress(user_id)
        habits = analyze_learning_habits(user_id)
        weak_topics = db.execute("""
            SELECT * FROM weak_topics
            WHERE user_id = ? AND last_quiz_score < 70
            ORDER BY last_quiz_score ASC
            LIMIT 5
        """, (user_id,)).fetchall()
        
        weak_topics_list = [dict(t) for t in weak_topics]
        
        if not progress_list or len(progress_list) == 0:
            avg_progress = 0
        else:
            progress_values = [p.get('progress_percentage', 0) for p in progress_list]
            avg_progress = sum(progress_values) / len(progress_values)
        
        learning_data = {
            "average_progress": avg_progress,
            "num_courses": len(progress_list) if progress_list else 0,
            "courses": progress_list,
            "habits": habits.get('analysis', {}),
            "weak_topics": weak_topics_list
        }
        
        if ai_client:
            prompt = f"""Based on this student's learning data, generate 3-4 personalized, actionable recommendations in Vietnamese.
            
Learning Data:
- Average Progress: {avg_progress:.1f}%
- Number of Courses: {len(progress_list) if progress_list else 0}
- Daily Study Hours: {habits.get('analysis', {}).get('average_daily_study_hours', 'N/A')}
- Weak Topics: {', '.join([t['topic_name'] for t in weak_topics_list]) if weak_topics_list else 'None identified'}
- Most Productive Day: {habits.get('analysis', {}).get('most_productive_day', 'N/A')}

Generate recommendations as a JSON array with objects containing 'title', 'description', and 'priority' (high/medium/low).
Return ONLY the JSON array, no other text."""

            try:
                response = ai_client.generate_content(prompt)
                response_text = response.text
                
                import json
                # Try to extract JSON from response
                if "```json" in response_text:
                    json_str = response_text.split("```json")[1].split("```")[0].strip()
                elif "[" in response_text:
                    json_str = response_text[response_text.find("["):response_text.rfind("]")+1]
                else:
                    json_str = response_text
                
                recommendations = json.loads(json_str)
                
                print(f"[Learning Insights] AI generated {len(recommendations)} recommendations for user {user_id}")
                
            except Exception as e:
                print(f"[Learning Insights] AI generation failed: {e}. Using fallback recommendations.")
                recommendations = generate_fallback_recommendations(avg_progress, habits, weak_topics_list)
        else:
            recommendations = generate_fallback_recommendations(avg_progress, habits, weak_topics_list)
        
        # Save to database
        for i, rec in enumerate(recommendations):
            db.execute("""
                INSERT INTO ai_recommendations
                (user_id, recommendation_type, title, description, priority, expires_at)
                VALUES (?, ?, ?, ?, ?, datetime('now', '+30 days'))
            """, (user_id, 'general', rec.get('title', f'Khuyến nghị {i+1}'), 
                  rec.get('description', ''), rec.get('priority', 'medium')))
        
        db.commit()
        
        print(f"[Learning Insights] Generated {len(recommendations)} recommendations for user {user_id}")
        
        # Fetch the newly created recommendations
        saved_recs = get_active_recommendations(user_id)
        
        return {
            "success": True,
            "recommendations_count": len(saved_recs),
            "recommendations": saved_recs
        }
    except Exception as e:
        print(f"[Learning Insights] Error generating recommendations: {e}")
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def generate_fallback_recommendations(avg_progress, habits, weak_topics_list):
    """
    Fallback rule-based recommendations when AI is not available.
    
    Args:
        avg_progress: Average progress percentage
        habits: Habits analysis dict
        weak_topics_list: List of weak topics
    
    Returns:
        List of recommendation dicts
    """
    recommendations = []
    
    # Recommendation 1: Based on progress
    if avg_progress < 30:
        recommendations.append({
            "title": "Tăng tốc độ học tập",
            "description": "Bạn chỉ hoàn thành {:.0f}% chương trình. Hãy tăng thời gian học tập để theo kịp lịch trình.".format(avg_progress),
            "priority": "high"
        })
    elif avg_progress < 70:
        recommendations.append({
            "title": "Tiếp tục bước đều",
            "description": "Tiến độ của bạn là {:.0f}%. Hãy duy trì nhịp độ học tập hiện tại để hoàn thành kịp.".format(avg_progress),
            "priority": "medium"
        })
    
    # Recommendation 2: Based on habits
    if habits.get('success') and habits.get('analysis'):
        analysis = habits['analysis']
        daily_hours = float(analysis.get('average_daily_study_hours', 0))
        if daily_hours < 1:
            recommendations.append({
                "title": "Tăng thời lượng học tập hàng ngày",
                "description": "Bạn chỉ học {:.1f} giờ mỗi ngày. Cố gắng tăng lên ít nhất 1.5 giờ để cải thiện hiệu suất.".format(daily_hours),
                "priority": "high"
            })
    
    # Recommendation 3: Based on weak topics
    if weak_topics_list and len(weak_topics_list) > 0:
        topic_names = ", ".join([t['topic_name'] for t in weak_topics_list[:3]])
        recommendations.append({
            "title": "Ôn tập những chủ đề yếu",
            "description": "Bạn cần ôn tập: {}. Hãy dành thêm thời gian cho những chủ đề này.".format(topic_names),
            "priority": "high"
        })
    
    # Recommendation 4: General tips
    if not recommendations or len(recommendations) == 0:
        recommendations.append({
            "title": "Bắt đầu ghi lại các session học",
            "description": "Hãy bắt đầu ghi lại các session học để hệ thống phân tích thói quen học tập và đưa ra các khuyến nghị cá nhân hóa.",
            "priority": "medium"
        })
    
    return recommendations

def get_active_recommendations(user_id):
    """
    Retrieves active (non-addressed) recommendations for the user.
    
    Args:
        user_id: User ID
    
    Returns:
        List of active recommendations
    """
    try:
        db = get_db()
        
        rows = db.execute("""SELECT * FROM ai_recommendations WHERE user_id = ? AND is_addressed = 0 AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP) ORDER BY priority = 'high' DESC, created_at DESC""", (user_id,)).fetchall()
        
        recommendations = []
        for row in rows:
            rec = dict(row)
            if rec.get('created_at') and isinstance(rec['created_at'], str) == False:
                rec['created_at'] = rec['created_at'].isoformat() if hasattr(rec['created_at'], 'isoformat') else str(rec['created_at'])
            if rec.get('expires_at') and isinstance(rec['expires_at'], str) == False:
                rec['expires_at'] = rec['expires_at'].isoformat() if hasattr(rec['expires_at'], 'isoformat') else str(rec['expires_at'])
            recommendations.append(rec)
        
        return recommendations
    except Exception as e:
        print(f"[Learning Insights] Error fetching recommendations: {e}")
        traceback.print_exc()
        return []