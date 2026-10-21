import Taro from '@tarojs/taro'
import type {
  Quiz,
  QuizGenerationTask,
  QuizHistoryDetail,
  QuizHistoryPage,
  ParsedSource,
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
  timeout = 65000,
) {
  return Taro.request<ApiEnvelope<T>>({
    url: `${API_BASE_URL}/api/v1${path}`,
    method,
    data,
    timeout,
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
  timeout = 65000,
): ApiRequest<T> {
  let activeTask: ReturnType<typeof createTask<T>> | null = null
  let aborted = false
  let requestAuthenticated = false

  const promise = (async () => {
    let token = useAuthentication ? await ensureWechatLogin() : null
    requestAuthenticated = token !== null
    if (aborted) throw new Error('请求已取消')

    try {
      activeTask = createTask<T>(path, 'POST', data, token, timeout)
      let response = await activeTask
      if (response.statusCode === 401) {
        clearAuthToken()
        if (token && retryAnonymouslyOnUnauthorized) {
          token = null
          requestAuthenticated = false
          activeTask = createTask<T>(path, 'POST', data, token, timeout)
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

export function generateQuiz(userInput: string): ApiRequest<QuizGenerationTask> {
  return post<QuizGenerationTask>(
    '/quiz/generate',
    { user_input: userInput },
    true,
  )
}

async function getQuizGenerationTask(
  taskId: string,
  authenticated: boolean,
): Promise<QuizGenerationTask> {
  const token = authenticated ? await ensureWechatLogin() : null
  if (authenticated && !token) {
    throw new Error('微信登录暂不可用，请重试查看生成状态')
  }
  const response = await createTask<QuizGenerationTask>(
    `/quiz/tasks/${encodeURIComponent(taskId)}`,
    'GET',
    undefined,
    token,
  )
  if (response.statusCode === 401) {
    clearAuthToken()
    throw new Error('登录状态已失效，请重新登录后查看生成结果')
  }
  return unwrap(response)
}

export async function waitForQuizGeneration(
  taskId: string,
  authenticated: boolean,
  shouldStop: () => boolean = () => false,
  onStatus?: (status: QuizGenerationTask['status']) => void,
): Promise<Quiz> {
  const deadline = Date.now() + 300_000
  while (Date.now() < deadline) {
    if (shouldStop()) throw new Error('请求已取消')
    await new Promise((resolve) => setTimeout(resolve, 1500))
    const task = await getQuizGenerationTask(taskId, authenticated)
    if (shouldStop()) throw new Error('请求已取消')
    onStatus?.(task.status)
    if (task.status === 'completed') {
      if (task.quiz) return task.quiz
      throw new Error('任务已完成，但题目结果暂时无法读取，请重新生成')
    }
    if (task.status === 'failed') {
      throw new Error(task.error_message || '题目生成失败，请稍后重试')
    }
  }
  throw new Error('生成时间较长，请稍后重试；任务仍在后台处理中')
}

export function parseSourceUrl(url: string): Promise<ParsedSource> {
  return post<ParsedSource>(
    '/source/parse/url',
    { url },
    false,
    false,
    120000,
  ).promise
}

export function generateSourceQuiz(
  source: ParsedSource,
  knowledgePoints: string[],
): ApiRequest<QuizGenerationTask> {
  return post<QuizGenerationTask>(
    '/source/generate',
    {
      source_type: source.source_type,
      title: source.title,
      content: source.content,
      headings: source.headings,
      knowledge_points: knowledgePoints,
    },
    true,
    true,
    120000,
  )
}

export async function parseSourceDocument(
  filePath: string,
  fileName: string,
): Promise<ParsedSource> {
  const upload = (token: string | null) =>
    Taro.uploadFile({
      url: `${API_BASE_URL}/api/v1/source/parse/document`,
      filePath,
      name: 'file',
      formData: { file_name: fileName },
      timeout: 120000,
      header: token ? { Authorization: `Bearer ${token}` } : {},
    })

  let token = await ensureWechatLogin()
  let response = await upload(token)
  if (response.statusCode === 401) {
    clearAuthToken()
    if (token) {
      token = null
      response = await upload(null)
    }
  }

  let envelope: ApiEnvelope<ParsedSource>
  try {
    envelope = JSON.parse(response.data) as ApiEnvelope<ParsedSource>
  } catch {
    throw new Error('文件解析服务返回了无法识别的数据')
  }
  if (
    response.statusCode < 200 ||
    response.statusCode >= 300 ||
    envelope.code !== 0 ||
    envelope.data === null
  ) {
    throw new Error(envelope.message || '文件解析失败，请检查文件后重试')
  }
  return envelope.data
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
