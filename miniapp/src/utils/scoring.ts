import type { AnswerRecord, Question } from '../types'

export function isCorrectAnswer(
  question: Question,
  selectedAnswers: string[],
): boolean {
  return (
    question.answer.length === selectedAnswers.length &&
    question.answer.every((answer) => selectedAnswers.includes(answer))
  )
}

export function xpForAnswer(
  question: Question,
  selectedAnswers: string[],
): number {
  if (isCorrectAnswer(question, selectedAnswers)) return 20
  if (
    question.type === 'multiple' &&
    selectedAnswers.length > 0 &&
    selectedAnswers.every((answer) => question.answer.includes(answer)) &&
    selectedAnswers.length < question.answer.length
  ) {
    return 10
  }
  return 0
}

export function makeAnswerRecord(
  question: Question,
  selectedAnswers: string[],
  durationMs: number,
): AnswerRecord {
  return {
    question_id: question.id,
    selected_answers: selectedAnswers,
    is_correct: isCorrectAnswer(question, selectedAnswers),
    duration_ms: Math.max(0, durationMs),
  }
}
