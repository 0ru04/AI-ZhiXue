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
  source_type: 'text'
  user_input: string
  questions: Question[]
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

export type ReportStatus = 'idle' | 'loading' | 'error' | 'ready'

export interface RunState {
  quiz: Quiz
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
