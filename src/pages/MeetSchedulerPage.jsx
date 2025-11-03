
import React from "react"
import { useState } from "react"
import Card from "../components/Card"
import ErrorAlert from "../components/ErrorAlert"
import { apiCall } from "../utils/api"
import "./MeetSchedulerPage.css"

function MeetSchedulerPage() {
  const [courseId, setCourseId] = useState("")
  const [startTime, setStartTime] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  const handleSchedule = async (e) => {
    e.preventDefault()

    if (!courseId.trim()) {
      setError("Please enter a course ID")
      return
    }
    if (!startTime.trim()) {
      setError("Please select a start time")
      return
    }

    try {
      setLoading(true)
      setError(null)
      setSuccess(null)

      const data = await apiCall("/api/schedule_meet", {
        method: "POST",
        body: JSON.stringify({
          course_id: courseId,
          start_time: startTime,
        }),
        headers: { "Content-Type": "application/json" },
      })

      setSuccess(`Meeting scheduled! Meeting link: ${data.meet_link || "Meeting scheduled successfully"}`)
      setCourseId("")
      setStartTime("")
    } catch (err) {
      setError(err.message || "Failed to schedule meeting")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="meet-scheduler-page">
      <h1 className="page-title">Schedule Google Meet</h1>

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
              <label className="form-label">Course ID</label>
              <input
                type="text"
                className="form-input"
                placeholder="Enter course ID"
                value={courseId}
                onChange={(e) => setCourseId(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Start Time</label>
              <input
                type="datetime-local"
                className="form-input"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
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
              <p className="step-text">Enter your course ID</p>
            </div>
            <div className="info-step">
              <span className="step-number">2</span>
              <p className="step-text">Choose when you want to schedule the meeting</p>
            </div>
            <div className="info-step">
              <span className="step-number">3</span>
              <p className="step-text">We'll create a Google Meet and send you the link</p>
            </div>
            <div className="info-step">
              <span className="step-number">4</span>
              <p className="step-text">The meeting will be automatically recorded</p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}

export default MeetSchedulerPage
