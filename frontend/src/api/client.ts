import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const rawDetail = error.response?.data?.detail
    const message = typeof rawDetail === 'string'
      ? rawDetail
      : (rawDetail?.detail ?? error.message ?? 'Unknown error')

    if (status === 409) {
      return Promise.reject(new Error('DB update already in progress'))
    }
    if (status === 400) {
      return Promise.reject(new Error(`Bad request: ${message}`))
    }
    if (status === 404) {
      return Promise.reject(new Error(`Not found: ${message}`))
    }
    return Promise.reject(new Error(message))
  }
)

export default client
