import { useState } from 'react'
import { Button, ScrollView, Text, View } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { getQuizHistoryDetail } from '../../services/api'
import type { QuizHistoryDetail } from '../../types'
import './index.scss'

type PageState = 'loading' | 'ready' | 'error'

function formatDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 ${String(
    date.getHours(),
  ).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function formatDuration(durationMs: number): string {
  const seconds = Math.floor(durationMs / 1000)
  return `${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒`
}

export default function HistoryDetailPage() {
  const [pageState, setPageState] = useState<PageState>('loading')
  const [detail, setDetail] = useState<QuizHistoryDetail | null>(null)
  const [errorMessage, setErrorMessage] = useState('')

  const loadDetail = async () => {
    const quizId = Taro.getCurrentInstance().router?.params?.quiz_id
    if (typeof quizId !== 'string' || !quizId) {
      setErrorMessage('没有找到这次闯关的编号。')
      setPageState('error')
      return
    }

    setPageState('loading')
    setErrorMessage('')
    try {
      setDetail(await getQuizHistoryDetail(quizId))
      setPageState('ready')
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '历史报告暂时无法加载',
      )
      setPageState('error')
    }
  }

  useDidShow(() => {
    if (process.env.TARO_ENV === 'weapp') void loadDetail()
  })

  if (process.env.TARO_ENV !== 'weapp') {
    return (
      <View className='page-shell history-detail-state'>
        <Text className='display-font history-state-title'>历史回看仅在微信小程序中提供</Text>
        <Button className='primary-button' onClick={() => Taro.navigateBack()}>
          返回
        </Button>
      </View>
    )
  }

  if (pageState === 'loading') {
    return (
      <View className='page-shell history-detail-state'>
        <View className='panel history-state-panel'>
          <View className='history-state-mark'>…</View>
          <Text className='display-font history-state-title'>正在翻开这一话</Text>
          <Text className='muted history-state-copy'>正在读取这次闯关保存的报告和作答记录。</Text>
        </View>
      </View>
    )
  }

  if (pageState === 'error' || !detail) {
    return (
      <View className='page-shell history-detail-state'>
        <View className='panel panel-red history-state-panel'>
          <View className='history-state-mark'>!</View>
          <Text className='display-font history-state-title'>这份报告暂时打不开</Text>
          <Text className='muted history-state-copy'>{errorMessage}</Text>
          <Button className='primary-button' onClick={() => void loadDetail()}>
            重试
          </Button>
          <Button className='secondary-button history-state-back' onClick={() => Taro.navigateBack()}>
            返回闯关历史
          </Button>
        </View>
      </View>
    )
  }

  const { report } = detail
  const questionById = new Map(detail.questions.map((question) => [question.id, question]))

  return (
    <View className='page-shell history-detail-page'>
      <View className='history-detail-topbar'>
        <Button className='icon-button' aria-label='返回' onClick={() => Taro.navigateBack()}>
          ←
        </Button>
        <Text className='display-font history-detail-topbar-title'>历史复盘</Text>
        <View className='history-detail-spacer' />
      </View>

      <ScrollView className='history-detail-scroll' scrollY>
        <View className='history-detail-content'>
          <View className='history-accuracy-ring'>
            <View className='history-accuracy-inner'>
              <Text className='history-accuracy-value'>{report.accuracy}%</Text>
              <Text className='history-accuracy-label'>正确率</Text>
            </View>
          </View>
          <Text className='display-font history-detail-title'>{detail.title}</Text>
          <Text className='history-detail-subtitle'>
            {report.correct_count} / {report.total_questions} 题答对 · {formatDate(detail.created_at)}
          </Text>
          <Text className='history-detail-time'>用时 {formatDuration(report.total_duration_ms)} · 最高连击 ×{report.max_streak}</Text>

          <View className='panel history-report-section history-summary'>
            <Text className='display-font history-section-title'>这一话的总结</Text>
            {report.three_line_summary.map((line, index) => (
              <View key={`${index}-${line}`} className='history-summary-line'>
                <Text className='history-summary-number'>{index + 1}</Text>
                <Text className='body-font'>{line}</Text>
              </View>
            ))}
          </View>

          <View className='panel history-report-section'>
            <Text className='display-font history-section-title'>掌握点与薄弱点</Text>
            <Text className='history-point-label history-point-mastered'>✓ 掌握得不错</Text>
            {report.mastered_points.length > 0 ? (
              <View className='history-tags'>
                {report.mastered_points.map((point) => (
                  <Text key={point} className='history-tag'>{point}</Text>
                ))}
              </View>
            ) : (
              <Text className='muted history-empty-points'>这一话还没有记录已掌握的知识点。</Text>
            )}
            <Text className='history-point-label history-point-weak'>⌖ 还要再看一眼</Text>
            {report.weak_points.length > 0 ? (
              <View className='history-tags'>
                {report.weak_points.map((point) => (
                  <Text key={point} className='history-tag history-tag-weak'>{point}</Text>
                ))}
              </View>
            ) : (
              <Text className='muted history-empty-points'>这一话没有明显薄弱点，继续保持。</Text>
            )}
          </View>

          <View className='panel history-report-section'>
            <Text className='display-font history-section-title'>答题记录</Text>
            {detail.answer_records.map((record, index) => {
              const question = questionById.get(record.question_id)
              if (!question) return null
              const selected = record.selected_answers
                .map((key) => question.options.find((option) => option.key === key)?.text ?? key)
                .join('、')
              const correct = question.answer
                .map((key) => question.options.find((option) => option.key === key)?.text ?? key)
                .join('、')
              return (
                <View
                  key={record.question_id}
                  className={`history-answer ${record.is_correct ? '' : 'history-answer-wrong'}`}
                >
                  <Text className='history-answer-number'>{String(index + 1).padStart(2, '0')}</Text>
                  <View className='history-answer-copy'>
                    <Text className='history-question-title'>{question.stem}</Text>
                    <Text className='history-answer-selected'>
                      你的回答：{selected || '未作答'}
                    </Text>
                    {!record.is_correct && (
                      <Text className='history-answer-correct'>正确答案：{correct}</Text>
                    )}
                  </View>
                  <Text className={`history-answer-tag ${record.is_correct ? '' : 'history-answer-tag-wrong'}`}>
                    {record.is_correct ? '答对' : '答错'}
                  </Text>
                </View>
              )
            })}
          </View>

          <View className='panel history-report-section'>
            <Text className='display-font history-section-title'>下一步建议</Text>
            {report.advice.map((advice, index) => (
              <View key={`${index}-${advice}`} className='history-advice-row'>
                <Text className='history-advice-dot'>·</Text>
                <Text>{advice}</Text>
              </View>
            ))}
          </View>

          <Button className='primary-button history-detail-back' onClick={() => Taro.navigateBack()}>
            返回闯关历史
          </Button>
        </View>
      </ScrollView>
    </View>
  )
}
