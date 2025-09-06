import axios from 'axios'
import { toast } from '@/components/ui/toast'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000, // 10 second timeout
})

// Add response interceptor for error handling
api.interceptors.response.use(
  response => response,
  error => {
    // Don't show toast for cancelled requests
    if (axios.isCancel(error)) {
      return Promise.reject(error)
    }

    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      console.error('API Error:', error.response.data)
      
      const status = error.response.status
      const data = error.response.data
      
      // Handle specific status codes
      if (status === 401) {
        toast.error('Authentication required', {
          description: 'Please log in to continue',
        })
      } else if (status === 403) {
        toast.error('Access denied', {
          description: 'You do not have permission to perform this action',
        })
      } else if (status === 404) {
        toast.error('Not found', {
          description: data?.detail || 'The requested resource was not found',
        })
      } else if (status === 422) {
        toast.error('Validation error', {
          description: data?.detail || 'Please check your input and try again',
        })
      } else if (status >= 500) {
        toast.error('Server error', {
          description: 'Something went wrong on our end. Please try again later.',
        })
      } else if (data?.detail) {
        toast.error('Request failed', {
          description: data.detail,
        })
      }
    } else if (error.request) {
      // The request was made but no response was received
      console.error('Network Error:', error.request)
      
      if (error.code === 'ECONNABORTED') {
        toast.error('Request timeout', {
          description: 'The request took too long. Please try again.',
        })
      } else {
        toast.error('Network error', {
          description: 'Unable to connect to the server. Please check your connection.',
        })
      }
    } else {
      // Something happened in setting up the request that triggered an Error
      console.error('Error:', error.message)
      toast.error('Request failed', {
        description: error.message || 'An unexpected error occurred',
      })
    }
    return Promise.reject(error)
  }
)