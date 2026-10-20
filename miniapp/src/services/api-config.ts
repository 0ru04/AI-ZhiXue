export interface ApiEnvelope<T> {
  code: number
  message: string
  data: T | null
}

export const API_BASE_URL =
  process.env.TARO_APP_API_BASE_URL || 'http://127.0.0.1:8000'
