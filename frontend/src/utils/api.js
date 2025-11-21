// src/utils/api.js

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:5000";

/**
 * The main API call function.
 * It automatically adds the JWT token to the header for all requests.
 */
export async function apiCall(endpoint, options = {}) {
  const { method = "GET", body = null, headers = {}, isFormData = false } = options;

  try {
    // 1. Get the token from localStorage
    const token = localStorage.getItem('authToken');
    const authHeaders = token ? { 'Authorization': `Bearer ${token}` } : {};

    const config = {
      method,
      headers: {
        ...(!isFormData && { "Content-Type": "application/json" }),
        ...headers,
        ...authHeaders, // 2. Add the token to the request headers
      },
    };

    if (body && method !== "GET") {
      // apiCall will handle stringifying, or not, based on isFormData
      config.body = isFormData ? body : JSON.stringify(body);
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, config);

    // Check if response is JSON before trying to parse
    const contentType = response.headers.get("content-type");
    const isJson = contentType && contentType.includes("application/json");

    if (!response.ok) {
      if (isJson) {
        const errorData = await response.json().catch(() => ({}));
        
        // [FIX] Only auto-logout if 401 and NOT on the login page
        if (response.status === 401 && 
            endpoint !== '/api/login' && 
            endpoint !== '/api/register'
        ) {
            handleLogout(); // Call the logout helper
        }
        throw new Error(errorData.error || `HTTP ${response.status}`);
      } else {
        const text = await response.text();
        console.error("Server returned non-JSON error:", text.substring(0, 200));
        throw new Error(`Server error: ${response.status}. Backend may not be running.`);
      }
    }

    if (response.status === 204) { // No Content
      return null;
    }

    if (isJson) {
      return await response.json();
    } else {
      return { message: "Success", data: await response.text() };
    }
  } catch (error) {
    console.error(`[API Call Failed] ${method} ${endpoint}:`, error);
    throw error;
  }
}

/**
 * Fetches a protected file as a blob and returns a temporary URL.
 */
export async function apiFetchFile(endpoint) {
  const token = localStorage.getItem('authToken');
  const authHeaders = token ? { 'Authorization': `Bearer ${token}` } : {};

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'GET',
    headers: { ...authHeaders }
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    if (response.status === 401) {
      handleLogout();
    }
    throw new Error(errorData.error || `HTTP ${response.status}`);
  }

  const blob = await response.blob(); 
  return URL.createObjectURL(blob);
}

// --- Auth Helper Functions ---

export const loginUser = async (username, password) => {
  const data = await apiCall('/api/login', {
    method: 'POST',
    body: { username, password } // Send username and password
  });
  
  if (data.token) {
    localStorage.setItem('authToken', data.token);
    localStorage.setItem('currentUser', JSON.stringify(data.user));
  }
  return data;
};

export const registerUser = async (username, password) => {
  return await apiCall('/api/register', {
    method: 'POST',
    body: { username, password }
  });
};

export const handleLogout = () => {
  const token = localStorage.getItem('authToken');
  if (token) {
    // Attempt to tell the backend to blocklist this token
    apiCall('/api/logout', { method: 'POST' }).catch(err => {
      console.error("Logout API call failed, but logging out locally anyway.", err);
    });
  }
  
  // Always clear local data immediately
  localStorage.removeItem('authToken');
  localStorage.removeItem('currentUser');
  window.location.href = '/'; // Force reload to the login page
};