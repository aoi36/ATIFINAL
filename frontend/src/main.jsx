// src/main.jsx

import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx' // Import your App component
import './index.css' // Import your main stylesheet
import 'antd/dist/reset.css'

// This code finds the <div id="app"> in your index.html
// and tells React to render your <App /> component inside it.
ReactDOM.createRoot(document.getElementById('app')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)