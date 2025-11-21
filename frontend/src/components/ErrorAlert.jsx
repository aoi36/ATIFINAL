import React from "react"
import "./ErrorAlert.css"

function ErrorAlert({ message, onDismiss }) {
  return (
    <div className="error-alert">
      <div className="error-content">
        <span className="error-icon">⚠️</span>
        <p className="error-message">{message}</p>
      </div>
      {onDismiss && (
        <button className="error-close" onClick={onDismiss}>
          ✕
        </button>
      )}
    </div>
  )
}

export default ErrorAlert
