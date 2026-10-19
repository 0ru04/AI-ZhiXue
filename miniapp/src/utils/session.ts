import Taro from '@tarojs/taro'
import type { Quiz, RunState } from '../types'

const RUN_STORAGE_KEY = 'ai-zhi-xue-active-run'

export function createRun(quiz: Quiz): RunState {
  return {
    quiz,
    current_index: 0,
    selected_answers: [],
    answer_records: [],
    xp_reward: 0,
    coin_reward: 0,
    current_streak: 0,
    max_streak: 0,
    question_started_at: Date.now(),
    report_status: 'idle',
  }
}

export function readRun(): RunState | null {
  return Taro.getStorageSync(RUN_STORAGE_KEY) || null
}

export function saveRun(run: RunState): void {
  Taro.setStorageSync(RUN_STORAGE_KEY, run)
}

export function clearRun(): void {
  Taro.removeStorageSync(RUN_STORAGE_KEY)
}
