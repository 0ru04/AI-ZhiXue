export type QuestionType = 'single' | 'multiple' | 'judge'
export type Difficulty = 'easy' | 'medium' | 'hard'

export interface Option {
  key: string
  text: string
}

export interface Question {
  id: string
  type: QuestionType
  stem: string
  options: Option[]
  answer: string[]
  explanation: string
  knowledge_point: string
  difficulty: Difficulty
}

export interface Quiz {
  quiz_id: string
  title: string
  summary: string
  source_type: 'text' | 'document' | 'web' | 'video'
  user_input: string
  questions: Question[]
}

export interface QuizGenerationTask {
  task_id: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  created_at: string
  updated_at: string
  quiz: Quiz | null
  error_message: string | null
}

export interface ParsedSource {
  source_type: 'document' | 'web' | 'video'
  title: string
  content: string
  headings: string[]
  knowledge_points: string[]
  source_url: string | null
}

export interface AnswerRecord {
  question_id: string
  selected_answers: string[]
  is_correct: boolean
  duration_ms: number
}

export interface Report {
  accuracy: number
  correct_count: number
  total_questions: number
  xp_reward: number
  coin_reward: number
  max_streak: number
  total_duration_ms: number
  mastered_points: string[]
  weak_points: string[]
  three_line_summary: string[]
  advice: string[]
  share_quote: string
}

export interface UserSummary {
  id: number
  nickname: string
  avatar_url: string | null
  total_xp: number
}

export interface UserProfile extends UserSummary {
  quiz_count: number
  correct_count: number
  average_accuracy: number
}

export interface LoginResponse {
  token: string
  user: UserSummary
}

export interface QuizHistoryItem {
  quiz_id: string
  title: string
  accuracy: number
  question_count: number
  created_at: string
}

export interface QuizHistoryPage {
  items: QuizHistoryItem[]
  total: number
  page: number
  page_size: number
}

export interface QuizHistoryDetail {
  quiz_id: string
  title: string
  summary: string | null
  user_input: string
  questions: Question[]
  answer_records: AnswerRecord[]
  report: Report
  created_at: string
}

export type ReportStatus = 'idle' | 'loading' | 'error' | 'ready'

export interface RunState {
  quiz: Quiz
  user_persisted?: boolean
  current_index: number
  selected_answers: string[]
  answer_records: AnswerRecord[]
  xp_reward: number
  coin_reward: number
  current_streak: number
  max_streak: number
  question_started_at: number
  report_status: ReportStatus
  report?: Report
}
