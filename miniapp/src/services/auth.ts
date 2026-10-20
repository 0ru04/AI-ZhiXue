import Taro from '@tarojs/taro'
import type { LoginResponse } from '../types'
import { API_BASE_URL, type ApiEnvelope } from './api-config'
const AUTH_TOKEN_KEY = 'ai-zhi-xue-auth-token'
const AUTH_LOGOUT_KEY = 'ai-zhi-xue-auth-logged-out'

let loginPromise: Promise<string | null> | null = null
let authGeneration = 0

export function getAuthToken(): string | null {
  const token: unknown = Taro.getStorageSync(AUTH_TOKEN_KEY)
  return typeof token === 'string' && token.length > 0 ? token : null
}

export function clearAuthToken(): void {
  Taro.removeStorageSync(AUTH_TOKEN_KEY)
}

export function hasExplicitlyLoggedOut(): boolean {
  const value: unknown = Taro.getStorageSync(AUTH_LOGOUT_KEY)
  return value === true || value === 'true'
}

function performWechatLogin(): Promise<string | null> {
  const cachedToken = getAuthToken()
  if (cachedToken) return Promise.resolve(cachedToken)
  if (loginPromise) return loginPromise

  const generation = authGeneration
  loginPromise = (async () => {
    try {
      const loginResult = await Taro.login()
      if (!loginResult.code) {
        throw new Error('微信未返回登录凭证')
      }

      const response = await Taro.request<ApiEnvelope<LoginResponse>>({
        url: `${API_BASE_URL}/api/v1/user/login`,
        method: 'POST',
        data: { code: loginResult.code },
        timeout: 10000,
        header: { 'content-type': 'application/json' },
      })
      const envelope = response.data
      if (
        response.statusCode < 200 ||
        response.statusCode >= 300 ||
        envelope.code !== 0 ||
        envelope.data === null ||
        !envelope.data.token
      ) {
        throw new Error(envelope.message || '微信登录暂时不可用')
      }
      if (generation !== authGeneration || hasExplicitlyLoggedOut()) {
        return null
      }
      Taro.setStorageSync(AUTH_TOKEN_KEY, envelope.data.token)
      return envelope.data.token
    } catch (error) {
      console.warn('微信静默登录失败，将继续使用匿名学习模式。', error)
      return null
    } finally {
      if (generation === authGeneration) loginPromise = null
    }
  })()

  return loginPromise
}

export function ensureWechatLogin(): Promise<string | null> {
  if (process.env.TARO_ENV !== 'weapp') return Promise.resolve(null)
  if (hasExplicitlyLoggedOut()) return Promise.resolve(null)
  return performWechatLogin()
}

export function loginWithWechat(): Promise<string | null> {
  if (process.env.TARO_ENV !== 'weapp') return Promise.resolve(null)

  authGeneration += 1
  loginPromise = null
  clearAuthToken()
  Taro.removeStorageSync(AUTH_LOGOUT_KEY)
  return performWechatLogin()
}

export function logoutWechat(): void {
  authGeneration += 1
  loginPromise = null
  clearAuthToken()
  Taro.setStorageSync(AUTH_LOGOUT_KEY, true)
}
