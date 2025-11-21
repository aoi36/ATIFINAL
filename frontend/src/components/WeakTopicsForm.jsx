import { useState } from 'react'
import { apiCall } from '../utils/api.js'
import Card from './Card'
import '../pages/LearningInsightsPage.css'

export default function WeakTopicsForm({ selectedCourse, onSubmitSuccess }) {
  const [formData, setFormData] = useState({
    topic_name: '',
    last_quiz_score: '',
  })
  const [submitting, setSubmitting] = useState(false)

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'last_quiz_score' ? (value ? parseInt(value) : '') : value,
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
        topic_name: formData.topic_name,
        last_quiz_score: formData.last_quiz_score ? formData.last_quiz_score : null,
      }

      await apiCall('/api/insights/weak-topics/add', {
        method: 'POST',
        body: payload,
      })

      alert('✅ Weak topic recorded! AI will generate recommendations.')
      setFormData({
        topic_name: '',
        last_quiz_score: '',
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
      <Card title="🎯 Record Struggling Topic">
        <p className="no-data">Select a course to record weak topics</p>
      </Card>
    )
  }

  return (
    <Card title="🎯 Record Struggling Topic" className="card-form">
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label htmlFor="topic_name">📌 Topic Name:</label>
          <input
            type="text"
            id="topic_name"
            name="topic_name"
            value={formData.topic_name}
            onChange={handleChange}
            placeholder="e.g., Quadratic Equations, Photosynthesis"
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="last_quiz_score">📊 Last Quiz Score (optional):</label>
          <input
            type="number"
            id="last_quiz_score"
            name="last_quiz_score"
            value={formData.last_quiz_score}
            onChange={handleChange}
            placeholder="e.g., 65"
            min="0"
            max="100"
          />
          <small style={{ color: '#999', marginTop: '4px', display: 'block' }}>
            Leave blank if you don't have a score yet
          </small>
        </div>

        <button
          type="submit"
          className="btn-primary"
          disabled={submitting}
          style={{ width: '100%' }}
        >
          {submitting ? '⏳ Recording...' : '✅ Record Topic'}
        </button>
      </form>
    </Card>
  )
}