// src/pages/CalendarPage.jsx

import React, { useState, useEffect } from 'react'
import { apiCall } from '../utils/api'
import Card from '../components/Card'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorAlert from '../components/ErrorAlert'

// FullCalendar imports
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'

import './CalendarPage.css' // We'll create this file

function CalendarPage() {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)

  // State for settings
  const [calendarId, setCalendarId] = useState('')
  const [currentCalendarId, setCurrentCalendarId] = useState('primary')

  // State for button loading
  const [syncLoading, setSyncLoading] = useState(false)
  const [planLoading, setPlanLoading] = useState(false)
  const [settingsLoading, setSettingsLoading] = useState(false)

  // Fetch all data on page load
  useEffect(() => {
    fetchCalendarEvents()
    fetchUserSettings()
  }, [])

  // Fetches the user's current GCal ID to display
  const fetchUserSettings = async () => {
    try {
      const settings = await apiCall('/api/user/settings')
      if (settings.google_calendar_id) {
        setCalendarId(settings.google_calendar_id)
        setCurrentCalendarId(settings.google_calendar_id)
      }
    } catch (err) {
      setError(err.message || 'Failed to load user settings')
    }
  }

  // Fetches events from your /api/calendar/events
  const fetchCalendarEvents = async () => {
    setLoading(true)
    try {
      const data = await apiCall('/api/calendar/events')

      // Format the data for FullCalendar
      const formattedEvents = data.map((event) => ({
        title: `${event.course}: ${event.title}`,
        start: event.due_iso, // FullCalendar can read ISO strings
        end: event.due_iso, // For a single "due" event, start and end are the same
        url: event.google_link || event.lms_link, // This makes the event clickable
        color: event.status_color,
        extendedProps: {
          status: event.status,
          course: event.course,
        },
      }))

      setEvents(formattedEvents)
      setError(null)
    } catch (err) {
      setError(err.message || 'Failed to load calendar events')
    } finally {
      setLoading(false)
    }
  }

  // Handler for the "Sync Deadlines" button
  const handleSync = async () => {
    setSyncLoading(true)
    setError(null)
    setSuccess(null)
    try {
      const res = await apiCall('/api/sync_calendar', { method: 'POST' })
      setSuccess(res.status || 'Calendar sync started!')
      // Refresh events after a short delay
      setTimeout(fetchCalendarEvents, 2000)
    } catch (err) {
      setError(err.message || 'Failed to start sync')
    } finally {
      setSyncLoading(false)
    }
  }

  // Handler for the "Generate Study Plan" button
  const handleGeneratePlan = async () => {
    setPlanLoading(true)
    setError(null)
    setSuccess(null)
    try {
      const res = await apiCall('/api/generate_study_plan', { method: 'POST' })
      setSuccess(res.status || 'AI study plan generation started!')
      setTimeout(fetchCalendarEvents, 2000)
    } catch (err) {
      setError(err.message || 'Failed to start AI plan')
    } finally {
      setPlanLoading(false)
    }
  }

  // Handler for the "Save Settings" button
  const handleUpdateSettings = async (e) => {
    e.preventDefault()
    setSettingsLoading(true)
    setError(null)
    setSuccess(null)
    try {
      await apiCall('/api/user/settings', {
        method: 'POST',
        body: { google_calendar_id: calendarId },
      })
      setSuccess('Calendar ID updated successfully!')
      setCurrentCalendarId(calendarId) // Update the displayed ID
    } catch (err) {
      setError(err.message || 'Failed to update settings')
    } finally {
      setSettingsLoading(false)
    }
  }

  return (
    <div className="calendar-page">
      <h1 className="page-title">My Calendar & Study Plan</h1>

      {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}
      {success && (
        <div className="success-alert" onClick={() => setSuccess(null)}>
          {success}
        </div>
      )}

      <div className="calendar-controls">
        <Card className="control-card">
          <h2 className="card-title">Actions</h2>
          <div className="button-group">
            <button onClick={handleSync} disabled={syncLoading} className="submit-button">
              {syncLoading ? <LoadingSpinner small /> : 'Sync LMS Deadlines'}
            </button>
            <button
              onClick={handleGeneratePlan}
              disabled={planLoading}
              className="submit-button secondary"
            >
              {planLoading ? <LoadingSpinner small /> : 'Generate AI Study Plan'}
            </button>
          </div>
        </Card>

        <Card className="control-card">
          <h2 className="card-title">Calendar Settings</h2>
          <form onSubmit={handleUpdateSettings}>
            <p>
              Your current calendar ID is: <strong>{currentCalendarId}</strong>
            </p>
            <div className="form-group">
              <label className="form-label">New Google Calendar ID</label>
              <input
                type="email"
                className="form-input"
                placeholder="e.g., yourname@gmail.com"
                value={calendarId}
                onChange={(e) => setCalendarId(e.target.value)}
              />
              <p className="file-hint">
                Remember to share your calendar with the service account email.
              </p>
            </div>
            <button type="submit" disabled={settingsLoading} className="submit-button">
              {settingsLoading ? <LoadingSpinner small /> : 'Save Settings'}
            </button>
          </form>
        </Card>
      </div>

      <Card className="calendar-card">
        {loading ? (
          <LoadingSpinner />
        ) : (
          <FullCalendar
            plugins={[dayGridPlugin, timeGridPlugin]}
            initialView="dayGridMonth"
            headerToolbar={{
              left: 'prev,next today',
              center: 'title',
              right: 'dayGridMonth,timeGridWeek',
            }}
            events={events}
            eventClick={(info) => {
              // Open the Google Calendar or LMS link in a new tab
              info.jsEvent.preventDefault() // Don't let the browser follow the link
              if (info.event.url) {
                window.open(info.event.url, '_blank')
              }
            }}
          />
        )}
      </Card>
    </div>
  )
}

export default CalendarPage