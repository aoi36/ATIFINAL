// api.js

// -- FIX THIS LINE --
// const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:5000"
// -- TO THIS --
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:5000"

export async function apiCall(endpoint, options = {}) {
  const { method = "GET", body = null, headers = {}, isFormData = false } = options
  
  try {
    const config = {
      method,
      headers: {
        ...(!isFormData && { "Content-Type": "application/json" }),
        ...headers,
      },
    }

    if (body && method !== "GET") {
      // For FormData, let the browser set the Content-Type
      config.body = isFormData ? body : JSON.stringify(body)
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, config)

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.error || `HTTP ${response.status}`)
    }

    // Handle 204 No Content (like from a successful DELETE)
    if (response.status === 204) {
      return null;
    }

    return await response.json()
  } catch (error) {
    console.error("[v0] API call failed:", error)
    throw error
  }
}