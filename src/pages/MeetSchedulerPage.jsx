import React from "react"
import { useState } from "react"
import Card from "../components/Card"
import LoadingSpinner from "../components/LoadingSpinner"
import ErrorAlert from "../components/ErrorAlert"
import { apiCall } from "../utils/api"
import "./MeetSchedulerPage.css"

function MeetSchedulerPage() {
  // --- [FIX 1] ---
  // State should match what the API needs
  const [meetLink, setMeetLink] = useState("")
  const [joinTime, setJoinTime] = useState("") // Will hold "HH:MM"
  const [duration, setDuration] = useState("60") // Default to 60 minutes
  // --- [END FIX] ---

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  const handleSchedule = async (e) => {
    e.preventDefault()

    // --- [FIX 2] ---
    // Validate the new state variables
    if (!meetLink.trim() || !meetLink.startsWith("https://meet.google.com/")) {
      setError("Please enter a valid Google Meet link (e.g., https://meet.google.com/abc-xyz-uvw)")
      return
    }
    if (!joinTime.trim()) {
      setError("Please select a join time")
      return
    }
    if (!duration.trim() || parseInt(duration) <= 0) {
        setError("Please enter a positive duration in minutes")
        return
    }
    // --- [END FIX] ---

    try {
      setLoading(true)
      setError(null)
      setSuccess(null)

      // --- [FIX 3] ---
      // Send the correct JSON payload to the API
      const data = await apiCall("/api/schedule_meet", {
        method: "POST",
        body: JSON.stringify({
          meet_link: meetLink,
          time_str: joinTime, // Send the "HH:MM" string
          duration_minutes: duration // Send the duration
        }),
        headers: { "Content-Type": "application/json" },
        isFormData: false // This is JSON, not FormData
      })
      // --- [END FIX] ---

      setSuccess(data.status || "Meeting scheduled successfully!")
      // Clear the form
      setMeetLink("")
      setJoinTime("")
      setDuration("60")
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
              <label className="form-label">Join Time (HH:MM)</label>
              <input
                type="time" 
                className="form-input"
                value={joinTime}
                onChange={(e) => setJoinTime(e.target.value)}
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
              {/* --- [THIS LINE IS FIXED] --- */}
              <p className="step-text">Enter your Google Meet link</p>
            </div>
            <div className="info-step">
              <span className="step-number">2</span>
              <p className="step-text">Choose the time (HH:MM) to join</p>
            </div>
            <div className="info-step">
              <span className="step-number">3</span>
              <p className="step-text">Set the recording duration</p>
            </div>
            <div className="info-step">
              <span className="step-number">4</span>
              <p className="step-text">The assistant will join, record, and transcribe the meeting</p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}

export default MeetSchedulerPage