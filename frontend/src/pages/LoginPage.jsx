// src/pages/LoginPage.jsx

import React, { useState } from 'react';
import { loginUser } from '../utils/api';
import Card from '../components/Card';
import ErrorAlert from '../components/ErrorAlert';
import "./LoginPage.css"; // Make sure your CSS is imported

// 1. This function receives 'onLoginSuccess' and 'onSwitchToRegister'
function LoginPage({ onLoginSuccess, onSwitchToRegister }) { 
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  // 2. The handleSubmit function *must* accept 'e' (the event)
  const handleSubmit = async (e) => {
    
    // 3. This line is CRITICAL. It stops the page from refreshing.
    e.preventDefault(); 
    
    setLoading(true);
    setError(null);
    
    try {
      await loginUser(username, password);
      onLoginSuccess(); // This updates App.jsx and logs you in
      
    } catch (err) {
      setError(err.message || 'An error occurred.');
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <Card className="login-card">
        <h1 className="page-title">LMS Agent</h1>
        <p>Please log in with your LMS credentials.</p>
        
        {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}
        
        {/* 1. The <form> tag *must* have the onSubmit prop */}
        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label className="form-label">LMS Username</label>
            <input
              type="text"
              className="form-input"
              placeholder="Your LMS Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">LMS Password</label>
            <input
              type="password"
              className="form-input"
              placeholder="Your LMS Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <div className="button-group">
            {/* 2. The button *must* be type="submit" */}
            <button
              type="submit"
              className="submit-button"
              disabled={loading}
            >
              {loading ? 'Logging in...' : 'Login'}
            </button>
          </div>
        </form>

        {/* This "Register" button is OUTSIDE the form, so it won't submit it */}
        <div className="switch-auth">
          <span>Don't have an account? </span>
          <button onClick={onSwitchToRegister} className="switch-auth-button">
            Register here
          </button>
        </div>
      </Card>
    </div>
  );
}

export default LoginPage;