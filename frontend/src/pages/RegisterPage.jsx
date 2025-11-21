// src/pages/RegisterPage.jsx

import React, { useState } from 'react';
import { registerUser } from '../utils/api'; // <--- Use registerUser
import Card from '../components/Card';
import ErrorAlert from '../components/ErrorAlert';
import "./LoginPage.css"; // We can reuse the same CSS

function RegisterPage({ onRegisterSuccess, onSwitchToLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault(); // Prevent default form submission
    setLoading(true);
    setError(null);
    setSuccess(null);
    
    try {
      await registerUser(username, password);
      // Show success message and prompt user to log in
      setSuccess("Registration successful! Please log in.");
      // After 2 seconds, switch to the login page
      setTimeout(() => {
        onRegisterSuccess(); 
      }, 2000);
      
    } catch (err) {
      setError(err.message || 'An error occurred during registration.');
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <Card className="login-card">
        <h1 className="page-title">Register</h1>
        <p>Create a new account for the LMS Agent.</p>
        
        {error && <ErrorAlert message={error} onDismiss={() => setError(null)} />}
        {success && <div className="success-alert">{success}</div>}
        
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
            <button
              type="submit"
              className="submit-button"
              disabled={loading}
            >
              {loading ? 'Registering...' : 'Register'}
            </button>
          </div>
        </form>

        <div className="switch-auth">
          <span>Already have an account? </span>
          <button onClick={onSwitchToLogin} className="switch-auth-button">
            Login here
          </button>
        </div>
      </Card>
    </div>
  );
}

export default RegisterPage;