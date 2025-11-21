import { useState } from 'react'
import { apiCall } from '../utils/api.js'
import Card from './Card'
import '../pages/LearningInsightsPage.css'

export default function StudySessionForm({ selectedCourse, onSubmitSuccess }) {
  const [formData, setFormData] = useState({
    session_date: new Date().toISOString().split('T')[0],
    start_time: '09:00',
    end_time: '10:00',
    topics_studied: '',
    content_type: 'video',
    difficulty_level: 'medium',
    focus_score: 75,
  })
  const [submitting, setSubmitting] = useState(false)

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'focus_score' ? parseInt(value) : value,
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!selectedCourse) {
      alert('Please select a course first')
      return
    }

    setSubmitting(true)

    try {
      const payload = {
        course_db_id: selectedCourse.id,
        ...formData,
      }

      await apiCall('/api/insights/session/log', {
        method: 'POST',
        body: payload,
      })

      alert('✅ Study session logged successfully!')
      setFormData({
        session_date: new Date().toISOString().split('T')[0],
        start_time: '09:00',
        end_time: '10:00',
        topics_studied: '',
        content_type: 'video',
        difficulty_level: 'medium',
        focus_score: 75,
      })
      onSubmitSuccess()
    } catch (err) {
      alert(`Error: ${err.message}`)
    } finally {
      setSubmitting(false)
    }
  }

  if (!selectedCourse) {
    return (
      <Card title="📝 Log Study Session">
        <p className="no-data">Select a course to log study sessions</p>
      </Card>
    )
  }

  return (
    <Card title="📝 Log Study Session" className="card-form">
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="session_date">📅 Date:</label>
          <input
            type="date"
            id="session_date"
            name="session_date"
            value={formData.session_date}
            onChange={handleChange}
            required
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div className="form-group">
            <label htmlFor="start_time">⏰ Start Time:</label>
            <input
              type="time"
              id="start_time"
              name="start_time"
              value={formData.start_time}
              onChange={handleChange}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="end_time">⏰ End Time:</label>
            <input
              type="time"
              id="end_time"
              name="end_time"
              value={formData.end_time}
              onChange={handleChange}
              required
            />
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="topics_studied">📚 Topics Studied:</label>
          <textarea
            id="topics_studied"
            name="topics_studied"
            value={formData.topics_studied}
            onChange={handleChange}
            placeholder="e.g., Chapter 3: Functions, Practice Problems 1-10"
            required
            style={{ minHeight: '70px', resize: 'vertical' }}
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div className="form-group">
            <label htmlFor="content_type">📖 Content Type:</label>
            <select
              id="content_type"
              name="content_type"
              value={formData.content_type}
              onChange={handleChange}
            >
              <option value="video">Video Lecture</option>
              <option value="reading">Reading</option>
              <option value="practice">Practice Problems</option>
              <option value="review">Review Session</option>
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="difficulty_level">📊 Difficulty Level:</label>
            <select
              id="difficulty_level"
              name="difficulty_level"
              value={formData.difficulty_level}
              onChange={handleChange}
            >
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="focus_score">🎯 Focus Score: {formData.focus_score}%</label>
          <input
            type="range"
            id="focus_score"
            name="focus_score"
            min="0"
            max="100"
            step="5"
            value={formData.focus_score}
            onChange={handleChange}
          />
          <small style={{ color: '#999', marginTop: '4px', display: 'block' }}>
            0% = distracted, 100% = fully focused
          </small>
        </div>

        <button
          type="submit"
          className="btn-primary"
          disabled={submitting}
          style={{ width: '100%' }}
        >
          {submitting ? '⏳ Logging Session...' : '✅ Log Session'}
        </button>
      </form>
    </Card>
  )
}