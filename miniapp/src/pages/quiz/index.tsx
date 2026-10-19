import { useState } from 'react'
import { Button, ScrollView, Text, View } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import type { AnswerRecord, Question, RunState } from '../../types'
import { clearRun, readRun, saveRun } from '../../utils/session'
import { isCorrectAnswer, makeAnswerRecord, xpForAnswer } from '../../utils/scoring'
import './index.scss'

function questionTypeLabel(type: Question['type']): string {
  if (type === 'single') return '单选'
  if (type === 'multiple') return '多选'
  return '判断'
}

function difficultyLabel(difficulty: Question['difficulty']): string {
  if (difficulty === 'easy') return '简单'
  if (difficulty === 'hard') return '挑战'
  return '中等'
}

function getMastery(run: RunState) {
  const questionById = new Map(
    run.quiz.questions.map((question) => [question.id, question]),
  )
  const totals = new Map<string, { total: number; correct: number }>()
  run.answer_records.forEach((record) => {
    const point = questionById.get(record.question_id)?.knowledge_point
    if (!point) return
    const current = totals.get(point) || { total: 0, correct: 0 }
    current.total += 1
    if (record.is_correct) current.correct += 1
    totals.set(point, current)
  })

  return {
    mastered: [...totals.entries()]
      .filter(([, result]) => result.correct === result.total)
      .map(([point]) => point),
    weak: [...totals.entries()]
      .filter(([, result]) => result.correct < result.total)
      .map(([point]) => point),
  }
}

export default function QuizPage() {
  const [run, setRun] = useState<RunState | null>(null)
  const [explanationOpen, setExplanationOpen] = useState(true)

  useDidShow(() => {
    const savedRun = readRun()
    setRun(savedRun)
    setExplanationOpen(true)
  })

  if (!run) {
    return (
      <View className='page-shell quiz-empty'>
        <Text className='display-font empty-title'>这一话还没开始</Text>
        <Text className='body-font empty-copy'>回到首页，说一个你想学的知识点吧。</Text>
        <Button
          className='primary-button'
          onClick={() => Taro.reLaunch({ url: '/pages/index/index' })}
        >
          回首页 <Text>→</Text>
        </Button>
      </View>
    )
  }

  if (run.current_index >= run.quiz.questions.length) {
    const { mastered, weak } = getMastery(run)
    const correctCount = run.answer_records.filter(
      (record) => record.is_correct,
    ).length
    const accuracy = Math.round(
      (correctCount * 100) / run.quiz.questions.length,
    )
    return (
      <View className='clear-page page-shell'>
        <ScrollView className='clear-scroll' scrollY>
          <View className='clear-content'>
            <View className='clear-burst display-font'>
              通关!
              <Text className='clear-episode'>第 001 话</Text>
            </View>
            <Text className='display-font clear-title'>{run.quiz.title}</Text>
            <Text className='body-font clear-subtitle'>
              你答对了 {correctCount} / {run.quiz.questions.length} 题，小墨给你盖了个章。
            </Text>

            <View className='clear-stats'>
              <View className='clear-stat'>
                <Text className='clear-stat-value'>{accuracy}%</Text>
                <Text className='clear-stat-label'>正确率</Text>
              </View>
              <View className='clear-stat'>
                <Text className='clear-stat-value'>+{run.xp_reward}</Text>
                <Text className='clear-stat-label'>XP</Text>
              </View>
              <View className='clear-stat'>
                <Text className='clear-stat-value'>+{run.coin_reward}</Text>
                <Text className='clear-stat-label'>知识币</Text>
              </View>
            </View>

            <View className='panel clear-takeaway'>
              <Text className='display-font clear-panel-title'>这一话你带走了</Text>
              {mastered.length > 0 ? (
                mastered.map((point) => (
                  <View key={point} className='takeaway-row'>
                    <Text className='takeaway-icon'>✓</Text>
                    <Text>{point}</Text>
                  </View>
                ))
              ) : (
                <Text className='body-font empty-mastery'>
                  每一次尝试都在帮你靠近答案，看看复盘报告里的下一步。
                </Text>
              )}
              {weak.map((point) => (
                <View key={point} className='takeaway-row takeaway-weak'>
                  <Text className='takeaway-icon'>⌖</Text>
                  <Text>还要再看一眼：{point}</Text>
                </View>
              ))}
            </View>

            <Button
              className='primary-button clear-report-button'
              onClick={() => Taro.navigateTo({ url: '/pages/report/index' })}
            >
              看复盘报告 <Text>→</Text>
            </Button>
            <Button
              className='primary-button button-ghost button-small clear-replay-button'
              onClick={() => {
                clearRun()
                Taro.navigateBack()
              }}
            >
              再来一话
            </Button>
            <View className='episode-next'>
              <Text className='display-font'>下一话预告</Text>
              <Text className='chip chip-yellow episode-locked'>待解锁</Text>
              <Text className='body-font episode-topic'>{run.quiz.title} · 再深入一点？</Text>
            </View>
          </View>
        </ScrollView>
      </View>
    )
  }

  const question = run.quiz.questions[run.current_index]
  const feedback: AnswerRecord | undefined = run.answer_records.find(
    (record) => record.question_id === question.id,
  )
  const selectedAnswers = feedback?.selected_answers || run.selected_answers
  const earnedThisQuestion = feedback
    ? xpForAnswer(question, feedback.selected_answers)
    : 0

  const chooseOption = (optionKey: string) => {
    if (feedback) return
    let nextAnswers: string[]
    if (question.type === 'multiple') {
      nextAnswers = selectedAnswers.includes(optionKey)
        ? selectedAnswers.filter((answer) => answer !== optionKey)
        : [...selectedAnswers, optionKey]
    } else {
      nextAnswers = [optionKey]
    }
    const updatedRun = { ...run, selected_answers: nextAnswers }
    saveRun(updatedRun)
    setRun(updatedRun)
  }

  const submitAnswer = () => {
    if (feedback || selectedAnswers.length === 0) return
    const record = makeAnswerRecord(
      question,
      selectedAnswers,
      Date.now() - run.question_started_at,
    )
    const points = xpForAnswer(question, selectedAnswers)
    const streak = record.is_correct ? run.current_streak + 1 : 0
    const updatedRun: RunState = {
      ...run,
      selected_answers: selectedAnswers,
      answer_records: [...run.answer_records, record],
      xp_reward: run.xp_reward + points,
      coin_reward: run.coin_reward + (record.is_correct ? 3 : 0),
      current_streak: streak,
      max_streak: Math.max(run.max_streak, streak),
    }
    saveRun(updatedRun)
    setRun(updatedRun)
    setExplanationOpen(true)
  }

  const nextQuestion = () => {
    const updatedRun: RunState = {
      ...run,
      current_index: run.current_index + 1,
      selected_answers: [],
      question_started_at: Date.now(),
    }
    saveRun(updatedRun)
    setRun(updatedRun)
  }

  const answerCorrect = feedback
    ? isCorrectAnswer(question, feedback.selected_answers)
    : false

  return (
    <View className='quiz-page page-shell'>
      <View className='quiz-top'>
        <View className='quiz-header'>
          <Button className='icon-button quiz-back' onClick={() => Taro.navigateBack()}>
            ←
          </Button>
          <View className='quiz-count-chip chip chip-yellow'>
            第 {run.current_index + 1} / {run.quiz.questions.length} 格
          </View>
          <Text className='xp-chip'>+{run.xp_reward} XP</Text>
        </View>
        <View className='quiz-progress'>
          {run.quiz.questions.map((item, index) => {
            const completed = run.answer_records.some(
              (record) => record.question_id === item.id,
            )
            return (
              <View
                key={item.id}
                className={`qstep ${completed ? 'qstep-done' : ''} ${
                  index === run.current_index ? 'qstep-now' : ''
                }`}
              >
                {completed ? '✓' : index + 1}
              </View>
            )
          })}
        </View>
      </View>

      <ScrollView className='quiz-scroll' scrollY>
        <View className='question-card'>
          <View className='question-meta'>
            <Text className='question-tag'>{questionTypeLabel(question.type)}</Text>
            {question.type === 'multiple' && (
              <Text className='question-tag question-tag-quiet'>
                选 {question.answer.length} 项
              </Text>
            )}
            <Text className='question-tag question-tag-quiet'>
              {question.knowledge_point} · {difficultyLabel(question.difficulty)}
            </Text>
          </View>
          <Text className='display-font question-stem'>{question.stem}</Text>

          {question.type === 'judge' ? (
            <View className='judge-grid'>
              {question.options.map((option, index) => {
                const selected = selectedAnswers.includes(option.key)
                const correct = question.answer.includes(option.key)
                const wrongSelection =
                  Boolean(feedback) && selected && !correct
                const stateClass = feedback
                  ? correct
                    ? 'option-correct'
                    : wrongSelection
                      ? 'option-wrong'
                      : 'option-dim'
                  : selected
                    ? 'option-selected'
                    : ''
                return (
                  <Button
                    key={option.key}
                    className={`judge-option judge-${index === 0 ? 'yes' : 'no'} ${stateClass}`}
                    disabled={Boolean(feedback)}
                    onClick={() => chooseOption(option.key)}
                  >
                    <Text className='judge-word'>
                      {option.text === 'True' || option.text === 'TRUE'
                        ? '对'
                        : option.text === 'False' || option.text === 'FALSE'
                          ? '错'
                          : option.text}
                    </Text>
                    <Text className='judge-translation'>
                      {index === 0 ? 'TRUE' : 'FALSE'}
                    </Text>
                    {feedback && correct && (
                      <Text className='option-state'>正确</Text>
                    )}
                    {wrongSelection && (
                      <Text className='option-state'>你选的</Text>
                    )}
                  </Button>
                )
              })}
            </View>
          ) : (
            <View className='options-list'>
              {question.options.map((option) => {
                const selected = selectedAnswers.includes(option.key)
                const correct = question.answer.includes(option.key)
                const wrongSelection =
                  Boolean(feedback) && selected && !correct
                const stateClass = feedback
                  ? correct
                    ? 'option-correct'
                    : wrongSelection
                      ? 'option-wrong'
                      : 'option-dim'
                  : selected
                    ? 'option-selected'
                    : ''
                return (
                  <Button
                    key={option.key}
                    className={`option-card ${question.type === 'multiple' ? 'option-multiple' : ''} ${stateClass}`}
                    disabled={Boolean(feedback)}
                    onClick={() => chooseOption(option.key)}
                  >
                    <Text className='option-key'>
                      {question.type === 'multiple'
                        ? selected
                          ? '✓'
                          : ''
                        : option.key}
                    </Text>
                    <Text className='option-text'>{option.text}</Text>
                    {feedback && correct && (
                      <Text className='option-state'>正确</Text>
                    )}
                    {wrongSelection && (
                      <Text className='option-state'>你选的</Text>
                    )}
                  </Button>
                )
              })}
            </View>
          )}
        </View>

        {feedback ? (
          <>
            <View className='feedback-strip'>
              <Text
                className={`feedback-stamp ${
                  answerCorrect ? 'stamp-green' : 'stamp-red'
                }`}
              >
                {answerCorrect ? '答对啦!' : '差一点!'}
              </Text>
              {answerCorrect ? (
                <Text className='xp-pop'>+{earnedThisQuestion} XP · 连击 ×{run.current_streak}</Text>
              ) : (
                <Text className='chip chip-red'>
                  答案 {question.answer.join('、')} · +{earnedThisQuestion} XP
                </Text>
              )}
            </View>
            <View className='explanation-card'>
              <View className='explanation-header'>
                <View className='mascot explanation-mascot'>
                  <View className='mascot-point' />
                  <View className='mascot-body' />
                  <View className='mascot-eye mascot-eye-left' />
                  <View className='mascot-eye mascot-eye-right' />
                  <View className='mascot-cheek mascot-cheek-left' />
                  <View className='mascot-cheek mascot-cheek-right' />
                  <View className='mascot-mouth' />
                </View>
                <Text className='display-font'>
                  {answerCorrect ? '小墨讲一句' : '小墨补一课'}
                </Text>
              </View>
              {explanationOpen && (
                <Text className='body-font explanation-copy'>
                  {question.explanation}
                </Text>
              )}
              <Button
                className='fold-button'
                onClick={() => setExplanationOpen((open) => !open)}
              >
                {explanationOpen ? '收起讲解 ⌃' : '展开讲解 ⌄'}
              </Button>
            </View>
          </>
        ) : (
          <View className='question-tip body-font'>
            {question.type === 'multiple'
              ? `已选 ${selectedAnswers.length} 项 · 少选得一半 XP，错选不得分`
              : '选一个答案，交卷后立刻看讲解'}
          </View>
        )}
      </ScrollView>

      <View className='quiz-footer safe-bottom'>
        {feedback ? (
          <Button className='primary-button button-yellow' onClick={nextQuestion}>
            {run.current_index === run.quiz.questions.length - 1
              ? '完成这一话'
              : '下一格'}
            <Text className='button-arrow'>→</Text>
          </Button>
        ) : (
          <Button
            className={`primary-button quiz-submit ${
              selectedAnswers.length > 0 ? 'quiz-submit-ready' : ''
            }`}
            disabled={selectedAnswers.length === 0}
            onClick={submitAnswer}
          >
            {question.type === 'multiple' ? '交卷，看看对不对' : '选好了，交卷'}
          </Button>
        )}
      </View>
    </View>
  )
}
