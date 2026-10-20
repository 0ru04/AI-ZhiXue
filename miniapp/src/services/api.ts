import Taro from '@tarojs/taro'
import type {
  Quiz,
  QuizHistoryDetail,
  QuizHistoryPage,
  Report,
  RunState,
  UserProfile,
  UserSummary,
} from '../types'
import {
  clearAuthToken,
  ensureWechatLogin,
} from './auth'
import { API_BASE_URL, type ApiEnvelope } from './api-config'

export interface ApiRequest<T> {
  promise: Promise<T>
  authenticated: Promise<boolean>
  abort: () => void
}

type RequestMethod = 'GET' | 'POST' | 'PUT'

function createTask<T>(
  path: string,
  method: RequestMethod,
  data: object | undefined,
  token: string | null,
) {
  return Taro.request<ApiEnvelope<T>>({
    url: `${API_BASE_URL}/api/v1${path}`,
    method,
    data,
    timeout: 65000,
    header: {
      'content-type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
}

function unwrap<T>(
  response: Awaited<ReturnType<typeof createTask<T>>>,
): T {
  const { data: envelope, statusCode } = response
  if (
    statusCode < 200 ||
    statusCode >= 300 ||
    envelope.code !== 0 ||
    envelope.data === null
  ) {
    throw new Error(envelope.message || '服务暂时无法连接，请稍后重试')
  }
  return envelope.data
}

function post<T>(
  path: string,
  data: object,
  retryAnonymouslyOnUnauthorized = false,
  useAuthentication = true,
): ApiRequest<T> {
  let activeTask: ReturnType<typeof createTask<T>> | null = null
  let aborted = false
  let requestAuthenticated = false

  const promise = (async () => {
    let token = useAuthentication ? await ensureWechatLogin() : null
    requestAuthenticated = token !== null
    if (aborted) throw new Error('请求已取消')

    try {
      activeTask = createTask<T>(path, 'POST', data, token)
      let response = await activeTask
      if (response.statusCode === 401) {
        clearAuthToken()
        if (token && retryAnonymouslyOnUnauthorized) {
          token = null
          requestAuthenticated = false
          activeTask = createTask<T>(path, 'POST', data, token)
          response = await activeTask
        }
      }
      return unwrap(response)
    } finally {
      requestAuthenticated = requestAuthenticated && token !== null
    }
  })()

  return {
    promise,
    authenticated: promise.then(
      () => requestAuthenticated,
      () => requestAuthenticated,
    ),
    abort: () => {
      aborted = true
      activeTask?.abort()
    },
  }
}

async function authenticatedRequest<T>(
  path: string,
  method: RequestMethod,
  data?: object,
): Promise<T> {
  const token = await ensureWechatLogin()
  if (!token) throw new Error('微信登录暂不可用，请重试或继续匿名学习')

  const response = await createTask<T>(path, method, data, token)
  if (response.statusCode === 401) {
    clearAuthToken()
    throw new Error('微信登录已失效，请重新登录后查看学习记录')
  }
  return unwrap(response)
}

export function generateQuiz(userInput: string): ApiRequest<Quiz> {
  return post<Quiz>('/quiz/generate', { user_input: userInput }, true)
}

export function generateReport(run: RunState): ApiRequest<Report> {
  return post<Report>(
    '/report/generate',
    {
      quiz_id: run.quiz.quiz_id,
      topic: run.quiz.user_input,
      questions: run.quiz.questions,
      answer_records: run.answer_records,
    },
    true,
    run.user_persisted === true,
  )
}

export function getUserProfile(): Promise<UserProfile> {
  return authenticatedRequest('/user/profile', 'GET')
}

export function updateUserProfile(
  data: { nickname?: string; avatar_url?: string | null },
): Promise<UserSummary> {
  return authenticatedRequest('/user/profile', 'PUT', data)
}

export function getQuizHistory(
  page = 1,
  pageSize = 10,
): Promise<QuizHistoryPage> {
  return authenticatedRequest(
    `/user/quizzes?page=${page}&page_size=${pageSize}`,
    'GET',
  )
}

export function getQuizHistoryDetail(
  quizId: string,
): Promise<QuizHistoryDetail> {
  return authenticatedRequest(
    `/user/quizzes/${encodeURIComponent(quizId)}`,
    'GET',
  )
}
