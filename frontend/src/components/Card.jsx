import React from "react"
import "./Card.css"

function Card({ title, subtitle, children, onClick, className = "" }) {
  return (
    <div className={`card ${className}`} onClick={onClick}>
      {title && <h3 className="card-title">{title}</h3>}
      {subtitle && <p className="card-subtitle">{subtitle}</p>}
      {children && <div className="card-content">{children}</div>}
    </div>
  )
}

export default Card
