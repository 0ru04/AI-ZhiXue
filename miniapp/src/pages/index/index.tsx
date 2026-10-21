import { useRef, useState } from 'react'
import { Button, Image, Text, Textarea, View } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import {
  generateQuiz,
  getUserProfile,
  waitForQuizGeneration,
  type ApiRequest,
} from '../../services/api'
import { ensureWechatLogin, hasExplicitlyLoggedOut } from '../../services/auth'
import type { QuizGenerationTask, UserProfile } from '../../types'
import { createRun, saveRun } from '../../utils/session'
import './index.scss'

const EXAMPLE_TOPICS = ['RAG 是什么', '光合作用', '黑洞会吞掉地球吗']
const MORE_EXAMPLES = ['为什么天空是蓝色的？', '什么是区块链？', '蝴蝶如何变成蝴蝶？']
const PRINT_STEPS = [
  ['创建并保存任务', '等待后台领取'],
  ['生成闯关题目', '后台处理中'],
]

function Mascot({ className = '' }: { className?: string }) {
  return (
    <View className={`mascot ${className}`}>
      <View className='mascot-point' />
      <View className='mascot-body' />
      <View className='mascot-eye mascot-eye-left' />
      <View className='mascot-eye mascot-eye-right' />
      <View className='mascot-cheek mascot-cheek-left' />
      <View className='mascot-cheek mascot-cheek-right' />
      <View className='mascot-mouth' />
    </View>
  )
}

export default function Index() {
  const [input, setInput] = useState('')
  const [mode, setMode] = useState<'idle' | 'loading' | 'error'>('idle')
  const [loadingStep, setLoadingStep] = useState(0)
  const [errorMessage, setErrorMessage] = useState('')
  const [showMoreExamples, setShowMoreExamples] = useState(false)
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null)
  const [userCardState, setUserCardState] = useState<
    'loading' | 'ready' | 'anonymous' | 'error'
  >('loading')
  const [wechatLoggedOut, setWechatLoggedOut] = useState(false)
  const activeRequest = useRef<ApiRequest<QuizGenerationTask> | null>(null)
  const requestSequence = useRef(0)
  const homeRequestSequence = useRef(0)

  useDidShow(() => {
    if (process.env.TARO_ENV !== 'weapp') return

    const sequence = homeRequestSequence.current + 1
    homeRequestSequence.current = sequence
    setUserCardState('loading')

    void (async () => {
      const token = await ensureWechatLogin()
      if (homeRequestSequence.current !== sequence) return
      if (!token) {
        setUserProfile(null)
        setWechatLoggedOut(hasExplicitlyLoggedOut())
        setUserCardState('anonymous')
        return
      }

      setWechatLoggedOut(false)
      try {
        const profile = await getUserProfile()
        if (homeRequestSequence.current !== sequence) return
        setUserProfile(profile)
        setUserCardState('ready')
      } catch (error) {
        if (homeRequestSequence.current !== sequence) return
        console.error('首页学习档案加载失败。', error)
        setUserProfile(null)
        setUserCardState('error')
      }
    })()
  })

  const startGeneration = async () => {
    const userInput = input.trim()
    if (!userInput || mode === 'loading') return

    const sequence = requestSequence.current + 1
    requestSequence.current = sequence
    setErrorMessage('')
    setLoadingStep(0)
    setMode('loading')

    const request = generateQuiz(userInput)
    activeRequest.current = request
    let requestFailed = false
    try {
      const task = await request.promise
      const authenticated = await request.authenticated
      const quiz = await waitForQuizGeneration(
        task.task_id,
        authenticated,
        () => requestSequence.current !== sequence,
        (status) => setLoadingStep(status === 'running' ? 1 : 0),
      )
      if (requestSequence.current !== sequence) return
      saveRun(createRun(quiz, await request.authenticated))
      await Taro.navigateTo({ url: '/pages/quiz/index' })
    } catch (error) {
      if (requestSequence.current !== sequence) return
      requestFailed = true
      setErrorMessage(
        error instanceof Error ? error.message : '网络抖了一下，请稍后重试',
      )
      setMode('error')
    } finally {
      if (requestSequence.current === sequence) {
        activeRequest.current = null
        if (!requestFailed) setMode('idle')
      }
    }
  }

  const cancelGeneration = () => {
    requestSequence.current += 1
    activeRequest.current?.abort()
    activeRequest.current = null
    setMode('idle')
    setLoadingStep(0)
  }

  const chooseExample = (example: string) => {
    setInput(example)
    if (mode === 'error') setMode('idle')
  }

  const editAfterError = () => {
    setMode('idle')
    setErrorMessage('')
  }

  const examples = showMoreExamples
    ? [...EXAMPLE_TOPICS, ...MORE_EXAMPLES]
    : EXAMPLE_TOPICS

  return (
    <View className='home-page page-shell'>
      <View className='page-content home-content'>
        <View className='topbar'>
          {mode === 'idle' ? (
            <>
              <View className='brand'>
                <View className='brand-mark'>AI</View>
                <Text>智学</Text>
              </View>
              <Text className='chip chip-yellow'>今日一话</Text>
              {process.env.TARO_ENV === 'weapp' ? (
                <Button
                  className='icon-button home-settings'
                  aria-label='我的'
                  onClick={() => Taro.navigateTo({ url: '/pages/profile/index' })}
                >
                  我
                </Button>
              ) : (
                <Button
                  className='icon-button home-settings'
                  aria-label='设置'
                  onClick={() =>
                    Taro.showToast({ title: '先专心闯过这一话吧', icon: 'none' })
                  }
                >
                  ···
                </Button>
              )}
            </>
          ) : (
            <>
              <Button
                className='icon-button'
                onClick={mode === 'loading' ? cancelGeneration : editAfterError}
              >
                ←
              </Button>
              <Text className='display-font home-state-title'>
                {mode === 'loading' ? '正在印刷' : '印刷中断'}
              </Text>
              <View className='home-header-spacer' />
            </>
          )}
        </View>

        {mode === 'loading' ? (
          <View className='print-state panel'>
            <View className='print-stage'>
              <View className='print-sheet print-sheet-back' />
              <View className='print-sheet print-sheet-middle' />
              <View className='print-sheet print-sheet-front' />
              <Mascot className='print-mascot' />
              <Text className='print-caption display-font'>
                正在把知识压成 5 道题…
              </Text>
            </View>
            <View className='steps-list'>
              {PRINT_STEPS.map(([label, activeStatus], index) => (
                <View
                  key={label}
                  className={`step-row ${
                    index < loadingStep
                      ? 'step-done'
                      : index === loadingStep
                        ? 'step-now'
                        : ''
                  }`}
                >
                  <View className='step-dot'>
                    {index < loadingStep ? '✓' : index + 1}
                  </View>
                  <Text className='step-label'>{label}</Text>
                  <Text className='step-status'>
                    {index < loadingStep
                      ? '已完成'
                      : index === loadingStep
                        ? activeStatus
                        : '等待中'}
                  </Text>
                </View>
              ))}
            </View>
            <View className='skeleton-card'>
              <View className='skeleton-line' />
              <View className='skeleton-line' />
              <View className='skeleton-line' />
              <View className='skeleton-line' />
            </View>
            <View className='bubble bubble-yellow'>
              小墨正在逐题校对，确保答案和讲解都对得上。
            </View>
            <Text className='tiny loading-time'>
              任务已保存，正在后台整理资料并生成题目；完成后会自动进入闯关。
            </Text>
            <Button className='primary-button button-ghost cancel-button' onClick={cancelGeneration}>
              停止等待
            </Button>
          </View>
        ) : mode === 'error' ? (
          <View className='error-state'>
            <Mascot className='error-mascot' />
            <Text className='error-badge'>任务失败</Text>
            <Text className='display-font error-title'>这次没有印出来</Text>
            <Text className='body-font error-subtitle'>
              出题任务没有完成。查看下方提示后可以重试，原输入会保留。
            </Text>
            <View className='error-input'>
              <Text className='error-input-label'>你刚才输入的是</Text>
              <Text className='body-font'>{input}</Text>
            </View>
            <Text className='error-code'>
              {errorMessage || 'NETWORK TIMEOUT'} · 输入已保留
            </Text>
            <View className='error-actions'>
              <Button className='primary-button' onClick={startGeneration}>
                再印一次 <Text>→</Text>
              </Button>
              <Button
                className='primary-button button-ghost button-small'
                onClick={editAfterError}
              >
                改一下主题
              </Button>
            </View>
            <Text className='tiny error-note'>
              不会把半成品题目交给你；重新提交会创建一个新的任务。
            </Text>
          </View>
        ) : (
          <>
            {process.env.TARO_ENV === 'weapp' && (
              <>
                <Button
                  className='home-user-card panel panel-yellow'
                  onClick={() => Taro.navigateTo({ url: '/pages/profile/index' })}
                >
                  {userCardState === 'ready' && userProfile ? (
                    <>
                      {userProfile.avatar_url ? (
                        <Image
                          className='home-user-avatar'
                          src={userProfile.avatar_url}
                          mode='aspectFill'
                        />
                      ) : (
                        <View className='home-user-avatar home-user-avatar-fallback'>
                          {userProfile.nickname.slice(0, 1)}
                        </View>
                      )}
                      <View className='home-user-copy'>
                        <Text className='display-font home-user-name'>
                          {userProfile.nickname}
                        </Text>
                        <Text className='home-user-xp'>
                          累计经验 · {userProfile.total_xp} XP
                        </Text>
                      </View>
                      <Text className='home-user-link'>我的 ›</Text>
                    </>
                  ) : (
                    <>
                      <View className='home-user-avatar home-user-avatar-fallback'>
                        {userCardState === 'loading' ? '…' : '墨'}
                      </View>
                      <View className='home-user-copy'>
                        <Text className='display-font home-user-name'>
                          {userCardState === 'loading'
                            ? '正在同步学习档案'
                            : userCardState === 'error'
                              ? '学习数据暂时没有同步'
                              : wechatLoggedOut
                                ? '已退出微信身份'
                                : '微信登录暂不可用'}
                        </Text>
                        <Text className='home-user-xp'>
                          {userCardState === 'anonymous'
                            ? '仍可匿名继续学习'
                            : '点击查看或重试'}
                        </Text>
                      </View>
                      <Text className='home-user-link'>我的 ›</Text>
                    </>
                  )}
                </Button>
              </>
            )}

            <View className='home-hero'>
              <Text className='hero-episode'>第 001 话</Text>
              <View className='hero-row'>
                <View className='hero-copy'>
                  <Text className='display-font hero-title'>
                    今天想搞懂
                    <Text className='hero-highlight'>点什么？</Text>
                  </Text>
                  <Text className='body-font hero-subtitle'>
                    说一句话，我把它印成一话闯关漫画。
                  </Text>
                </View>
                <Mascot className='hero-mascot' />
              </View>
            </View>

            <View className='input-card'>
              <Textarea
                className='topic-input body-font'
                maxlength={500}
                value={input}
                placeholder='例如：为什么天空是蓝色的？'
                placeholderClass='topic-placeholder'
                onInput={(event) => setInput(event.detail.value)}
              />
              <View className='input-foot dashed-divider'>
                <Text>支持一句话 / 一段文本</Text>
                <Text>{input.length} / 500</Text>
              </View>
            </View>

            <View className='examples-row'>
              {examples.map((example) => (
                <Button
                  key={example}
                  className={`example-chip ${input === example ? 'example-active' : ''}`}
                  onClick={() => chooseExample(example)}
                >
                  {example}
                </Button>
              ))}
              <Button
                className='example-chip example-refresh'
                onClick={() => setShowMoreExamples((shown) => !shown)}
              >
                + {showMoreExamples ? '收起' : '换一批'}
              </Button>
            </View>

            <View className='settings-row'>
              <View className='setting-chip'><Text className='setting-key'>题量</Text>5 题</View>
              <View className='setting-chip'><Text className='setting-key'>难度</Text>混合</View>
              <View className='setting-chip setting-types'>
                <Text className='setting-key'>题型</Text>单选 / 多选 / 判断
              </View>
            </View>

            <Button
              className={`primary-button home-cta home-submit ${
                input.trim() ? 'home-submit-ready' : ''
              }`}
              disabled={!input.trim()}
              onClick={startGeneration}
            >
              开始印刷题目 <Text className='button-arrow'>→</Text>
            </Button>

            <Button
              className='primary-button button-ghost import-entry'
              onClick={() => Taro.navigateTo({ url: '/pages/import/index' })}
            >
              ＋ 导入学习材料
            </Button>

            <View className='home-footnote'>
              <Text className='footnote-check'>✓</Text>
              <Text>
                {process.env.TARO_ENV === 'weapp'
                  ? '登录后同步闯关记录；未登录也能继续学习。'
                  : 'MVP 无需登录；生成记录只保存在本机。'}
              </Text>
            </View>

            <View className='daily-card'>
              <View className='daily-head'>
                <Mascot className='daily-mascot' />
                <Text className='display-font'>小墨的今日一句</Text>
              </View>
              <Text className='body-font daily-quote'>
                “蓝光不是被天空染上的，是被空气弹出来的。”
              </Text>
              <Text className='daily-topic'>今日知识 · 瑞利散射</Text>
            </View>
          </>
        )}
      </View>
    </View>
  )
}
