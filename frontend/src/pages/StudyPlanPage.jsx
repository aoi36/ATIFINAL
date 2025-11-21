// src/pages/StudyPlanPage.jsx

import React, { useState, useEffect } from 'react';
import { apiCall } from '../utils/api';
import Card from '../components/Card';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorAlert from '../components/ErrorAlert';
import './StudyPlanPage.css'; // We'll create this CSS file

function StudyPlanPage() {
  const [stats, setStats] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchStudyPlan();
  }, []);

  const fetchStudyPlan = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiCall('/api/study_plan/events');
      setEvents(data.events || []);
      setStats({
        total: data.total_sessions,
        next_7_days: data.next_7_days,
        message: data.waifu_message,
      });
    } catch (err) {
      setError(err.message || 'Failed to load study plan');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorAlert message={error} onDismiss={() => setError(null)} />;

  return (
    <div className="study-plan-page">
      <h1 className="page-title">My AI Study Plan</h1>

      {stats && (
        <>
          <Card className="waifu-message-card">
            <p><strong>Waifu says:</strong> "{stats.message}"</p>
          </Card>
          <div className="stats-grid">
            <Card className="stat-card">
              <span className="stat-value">{stats.total}</span>
              <span className="stat-label">Total Study Sessions</span>
            </Card>
            <Card className="stat-card">
              <span className="stat-value">{stats.next_7_days}</span>
              <span className="stat-label">Sessions in Next 7 Days</span>
            </Card>
          </div>
        </>
      )}

      <div className="plan-list">
        {events.length > 0 ? (
          events.map((event) => (
            <Card key={event.id} className="plan-card">
              <div className="plan-card-header">
                <div className="plan-card-title">
                  <h2>{event.course.replace('🎓', '').trim()}</h2>
                  <span className="plan-card-date">{event.date}</span>
                </div>
                <div className="plan-card-time">
                  {event.start_time} - {event.end_time} ({event.duration_hours}h)
                </div>
              </div>
              
              <div className="plan-card-body">
                <div className="plan-card-details">
                  <div className="plan-detail-item">
                    <strong>Difficulty:</strong>
                    <span className="difficulty-stars" style={{ color: event.color }}>
                      {event.difficulty_stars}
                    </span>
                  </div>
                  <div className="plan-detail-item">
                    <strong>Assignment Due:</strong>
                    <span>{event.due_date}</span>
                  </div>
                  <div className="plan-detail-item">
                    <strong>AI Reason:</strong>
                    <p>{event.ai_reason}</p>
                  </div>
                </div>
                
                <div className="plan-card-breakdown">
                  <strong>Study Breakdown:</strong>
                  <ul>
                    {event.breakdown.map((step, idx) => (
                      <li key={idx}>{step}</li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="plan-card-footer">
                <a href={event.lms_link} target="_blank" rel="noopener noreferrer" className="plan-link">
                  LMS Page
                </a>
                <a href={event.google_link} target="_blank" rel="noopener noreferrer" className="plan-link">
                  Google Calendar
                </a>
              </div>
            </Card>
          ))
        ) : (
          <Card>
            <p>No study sessions found. Try running the "Generate AI Study Plan" in the Calendar tab!</p>
          </Card>
        )}
      </div>
    </div>
  );
}

export default StudyPlanPage;