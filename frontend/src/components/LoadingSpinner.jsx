import React from "react"
import "./LoadingSpinner.css"

function LoadingSpinner() {
  return (
    <div className="spinner-container">
      <div className="spinner"></div>
      <p className="spinner-text">Loading...</p>
    </div>
  )
}

export default LoadingSpinner
