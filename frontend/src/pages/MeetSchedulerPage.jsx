// src/pages/MeetSchedulerPage.jsx

import React, { useState, useEffect } from "react"
import Card from "../components/Card"
import LoadingSpinner from "../components/LoadingSpinner"
import ErrorAlert from "../components/ErrorAlert"
import { apiCall, apiFetchFile } from "../utils/api"
import "./MeetSchedulerPage.css"

function MeetSchedulerPage() {
  // --- State Variables ---
  const [meetLink, setMeetLink] = useState("")
  const [joinDateTime, setJoinDateTime] = useState("")
  const [duration, setDuration] = useState("60")
  const [userName, setUserName] = useState("Assistant")
  
  // --- [THIS WAS MISSING] ---
  const [recordings, setRecordings] = useState([]) 
  // --------------------------

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  // --- Fetch recordings on load ---
  useEffect(() => {
    fetchRecordings()
  }, [])

  const fetchRecordings = async () => {
    try {
      const data = await apiCall("/api/recordings")
      setRecordings(data || [])
    } catch (err) {
      console.error("Failed to load recordings", err)
    }
  }

  const handleDownload = async (filename) => {
    try {
      const blobUrl = await apiFetchFile(`/api/recordings/${filename}`)
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = filename.substring(filename.indexOf('_') + 1) 
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    } catch (err) {
      alert("Failed to download file")
    }
  }

  const getLocalNow = () => {
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    return now.toISOString().slice(0, 16);
  };

  const handleSchedule = async (e) => {
    e.preventDefault()

    if (!meetLink.trim() || !meetLink.startsWith("https://meet.google.com/")) {
      setError("Please enter a valid Google Meet link")
      return
    }
    if (!joinDateTime.trim()) {
      setError("Please select a date and time to join")
      return
    }
    if (new Date(joinDateTime) < new Date()) {
      setError("Cannot schedule a meeting in the past.");
      return;
    }
    if (!duration.trim() || parseInt(duration) <= 0) {
        setError("Please enter a positive duration in minutes")
        return
    }

    try {
      setLoading(true)
      setError(null)
      setSuccess(null)

      const data = await apiCall("/api/schedule_meet", {
        method: "POST",
        body: {
          meet_link: meetLink,
          join_datetime_str: joinDateTime, 
          duration_minutes: duration,
          user_name: userName
        },
        headers: { "Content-Type": "application/json" },
        isFormData: false 
      })

      setSuccess(data.status || "Meeting scheduled successfully!")
      setMeetLink("")
      setJoinDateTime("")
      setDuration("60")
      setUserName("Assistant")
      
      // Refresh list after scheduling
      fetchRecordings() 
    } catch (err) {
      setError(err.message || "Failed to schedule meeting")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="meet-scheduler-page">
      <h1 className="page-title">Schedule Google Meet Recording</h1>

      <div className="scheduler-container">
        <Card className="form-card">
          <h2 className="card-title">Schedule a New Meeting</h2>

          {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}
          {success && (
            <div className="success-alert">
              <span className="success-icon">✓</span>
              <p className="success-message">{success}</p>
            </div>
          )}

          <form onSubmit={handleSchedule} className="schedule-form">
            
            <div className="form-group">
              <label className="form-label">Google Meet Link</label>
              <input
                type="url"
                className="form-input"
                placeholder="https://meet.google.com/abc-xyz-uvw"
                value={meetLink}
                onChange={(e) => setMeetLink(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Join Date and Time</label>
              <input
                type="datetime-local"
                className="form-input"
                value={joinDateTime}
                onChange={(e) => setJoinDateTime(e.target.value)}
                min={getLocalNow()}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Bot Display Name</label>
              <input
                type="text"
                className="form-input"
                placeholder="Name the bot will use to join"
                value={userName}
                onChange={(e) => setUserName(e.target.value)}
                required
              />
            </div>
            
            <div className="form-group">
              <label className="form-label">Recording Duration (in minutes)</label>
              <input
                type="number"
                className="form-input"
                placeholder="e.g., 60"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                required
                min="1"
              />
            </div>

            <button type="submit" className="submit-button" disabled={loading}>
              {loading ? "Scheduling..." : "Schedule Meeting"}
            </button>
          </form>
        </Card>

        <Card className="info-card">
          <h2 className="card-title">How it works</h2>
          <div className="info-content">
            <div className="info-step">
              <span className="step-number">1</span>
              <p className="step-text">Enter the Google Meet link.</p>
            </div>
            <div className="info-step">
              <span className="step-number">2</span>
              <p className="step-text">Choose the exact date and time for the bot to join.</p>
            </div>
            <div className="info-step">
              <span className="step-number">3</span>
              <p className="step-text">Set a display name for the bot (e.g., "Note Taker").</p>
            </div>
            <div className="info-step">
              <span className="step-number">4</span>
              <p className="step-text">The assistant will join and record system audio (what you hear).</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Recordings List */}
      <div className="recordings-section" style={{ marginTop: '2rem' }}>
        <Card title="My Recordings & Transcripts">
          {recordings.length === 0 ? (
            <p>No recordings found yet.</p>
          ) : (
            <ul className="recording-list">
              {recordings.map((rec, idx) => (
                <li key={idx} className="recording-item" style={{
                    display: 'flex', 
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '15px',
                    borderBottom: '1px solid #eee'
                }}>
                  <div className="rec-info">
                    <div style={{ fontWeight: 'bold', fontSize: '1.1rem', marginBottom: '5px' }}>
                        {rec.type === "Video" ? "🎥" : "📄"} {rec.display_name}
                    </div>
                    <small style={{ color: '#666' }}>Created: {rec.created_at}</small>
                  </div>
                  <button 
                    className="submit-button" 
                    style={{ width: 'auto', padding: '8px 16px', fontSize: '0.9rem' }}
                    onClick={() => handleDownload(rec.filename)}
                  >
                    Download
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

    </div>
  )
}

export default MeetSchedulerPage