/**
 * API client for Store Provisioning Platform
 */

import axios from 'axios'

// API base URL - defaults to localhost for development
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://api.local.store'

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds
})

/**
 * Get all stores
 */
export const getStores = async () => {
  try {
    const response = await apiClient.get('/stores')
    return response.data
  } catch (error) {
    throw extractError(error)
  }
}

/**
 * Get a single store by ID
 */
export const getStore = async (storeId) => {
  try {
    const response = await apiClient.get(`/stores/${storeId}`)
    return response.data
  } catch (error) {
    throw extractError(error)
  }
}

/**
 * Create a new store
 */
export const createStore = async (storeData) => {
  try {
    const response = await apiClient.post('/stores', storeData)
    return response.data
  } catch (error) {
    throw extractError(error)
  }
}

/**
 * Delete a store
 */
export const deleteStore = async (storeId) => {
  try {
    const response = await apiClient.delete(`/stores/${storeId}`)
    return response.data
  } catch (error) {
    throw extractError(error)
  }
}

/**
 * Extract user-friendly error message from axios error
 */
const extractError = (error) => {
  if (error.response) {
    // Server responded with error status
    const message = error.response.data?.message || error.response.data?.error || error.message
    return new Error(message)
  } else if (error.request) {
    // Request made but no response
    return new Error('No response from server. Please check your connection.')
  } else {
    // Something else went wrong
    return new Error(error.message || 'An unexpected error occurred')
  }
}

export default apiClient
