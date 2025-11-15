// src/components/Navigation.jsx

import React from 'react';
// import './Navigation.css'; // Make sure to import your CSS

// 1. Receive the 'onLogout' prop
function Navigation({ currentPage, setCurrentPage, onLogout }) {
  
  // (Your existing navigation items)
  const navItems = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'courses', label: 'Courses' },
    { id: 'search', label: 'Search' },
    { id: 'tools', label: 'AI Tools' },
    { id: 'meet', label: 'Meet Scheduler' },
    { id: 'scraper', label: 'Scraper' },
    { id: 'calendar', label: 'Calendar' },
    { id: 'study-plan', label: 'Study Plan' },
    { id: "homework-submit", label: "Submit Homework", icon: "📝" },


  ];

  return (
    <nav className="navigation">
      <div className="nav-logo">
        LMS Agent
      </div>
      <ul className="nav-links">
        {navItems.map(item => (
          <li key={item.id}>
            <button
              className={`nav-button ${currentPage === item.id ? 'active' : ''}`}
              onClick={() => setCurrentPage(item.id)}
            >
              {item.label}
            </button>
          </li>
        ))}
      </ul>
      
      {/* 2. Add the Logout button */}
      <div className="nav-logout">
        <button className="logout-button" onClick={onLogout}>
          Logout
        </button>
      </div>
    </nav>
  );
}

export default Navigation;