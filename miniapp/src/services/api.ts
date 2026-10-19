import Taro from '@tarojs/taro'
import type { Quiz, Report, RunState } from '../types'

interface ApiEnvelope<T> {
  code: number
  message: string
  data: T | null
}

export interface ApiRequest<T> {
  promise: Promise<T>
  abort: () => void
}

const API_BASE_URL =
  process.env.TARO_APP_API_BASE_URL || 'http://127.0.0.1:8000'

function post<T>(path: string, data: object): ApiRequest<T> {
  const task = Taro.request<ApiEnvelope<T>>({
    url: `${API_BASE_URL}/api/v1${path}`,
    method: 'POST',
    data,
    timeout: 65000,
    header: { 'content-type': 'application/json' },
  })

  const promise = task.then(({ data: envelope, statusCode }) => {
    if (
      statusCode < 200 ||
      statusCode >= 300 ||
      envelope.code !== 0 ||
      envelope.data === null
    ) {
      throw new Error(envelope.message || '服务暂时无法连接，请稍后重试')
    }
    return envelope.data
  })

  return { promise, abort: () => task.abort() }
}

export function generateQuiz(userInput: string): ApiRequest<Quiz> {
  return post<Quiz>('/quiz/generate', { user_input: userInput })
}

export function generateReport(run: RunState): ApiRequest<Report> {
  return post<Report>('/report/generate', {
    quiz_id: run.quiz.quiz_id,
    topic: run.quiz.user_input,
    questions: run.quiz.questions,
    answer_records: run.answer_records,
  })
}
