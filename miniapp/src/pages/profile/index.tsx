import { useState } from 'react'
import { Button, Image, ScrollView, Text, View } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { getQuizHistory, getUserProfile } from '../../services/api'
import {
  ensureWechatLogin,
  hasExplicitlyLoggedOut,
  loginWithWechat,
  logoutWechat,
} from '../../services/auth'
import type { QuizHistoryItem, QuizHistoryPage, UserProfile } from '../../types'
import './index.scss'

const PAGE_SIZE = 10

type PageState = 'loading' | 'ready' | 'login' | 'loggedOut' | 'error'

function formatDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.getMonth() + 1}月${date.getDate()}日 ${String(
    date.getHours(),
  ).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function HistoryRow({ item }: { item: QuizHistoryItem }) {
  return (
    <Button
      className='history-row'
      onClick={() =>
        Taro.navigateTo({
          url: `/pages/history-detail/index?quiz_id=${encodeURIComponent(item.quiz_id)}`,
        })
      }
    >
      <View className='history-row-main'>
        <Text className='display-font history-row-title'>{item.title}</Text>
        <Text className='history-row-date'>{formatDate(item.created_at)}</Text>
      </View>
      <View className='history-row-result'>
        <Text className='history-row-score'>{item.accuracy}%</Text>
        <Text className='history-row-count'>{item.question_count} 题</Text>
      </View>
    </Button>
  )
}

export default function ProfilePage() {
  const [pageState, setPageState] = useState<PageState>('loading')
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [history, setHistory] = useState<QuizHistoryPage | null>(null)
  const [page, setPage] = useState(1)
  const [loadingMore, setLoadingMore] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  const loadProfile = async () => {
    setPageState('loading')
    setErrorMessage('')
    try {
      const token = await ensureWechatLogin()
      if (!token) {
        setProfile(null)
        setHistory(null)
        setPage(1)
        setPageState(hasExplicitlyLoggedOut() ? 'loggedOut' : 'login')
        return
      }
      const [nextProfile, firstPage] = await Promise.all([
        getUserProfile(),
        getQuizHistory(1, PAGE_SIZE),
      ])
      setProfile(nextProfile)
      setHistory(firstPage)
      setPage(1)
      setPageState('ready')
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '学习档案暂时无法加载',
      )
      setPageState('error')
    }
  }

  useDidShow(() => {
    if (process.env.TARO_ENV === 'weapp') void loadProfile()
  })

  const loadMore = async () => {
    if (!history || loadingMore || history.items.length >= history.total) return
    setLoadingMore(true)
    setErrorMessage('')
    try {
      const nextPage = page + 1
      const result = await getQuizHistory(nextPage, PAGE_SIZE)
      setHistory({
        ...result,
        items: [...history.items, ...result.items],
      })
      setPage(nextPage)
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '更多历史暂时无法加载',
      )
    } finally {
      setLoadingMore(false)
    }
  }

  const handleLogout = async () => {
    const result = await Taro.showModal({
      title: '退出登录？',
      content: '退出后将进入匿名学习模式，账号中的闯关历史不会被删除。',
      confirmText: '退出登录',
      confirmColor: '#b9341d',
    })
    if (!result.confirm) return

    logoutWechat()
    setProfile(null)
    setHistory(null)
    setPage(1)
    setLoadingMore(false)
    setErrorMessage('')
    setPageState('loggedOut')
  }

  const handleWechatLogin = async () => {
    setPageState('loading')
    setErrorMessage('')
    const token = await loginWithWechat()
    if (!token) {
      setProfile(null)
      setHistory(null)
      setPageState('login')
      return
    }
    await loadProfile()
  }

  const goHome = () => Taro.reLaunch({ url: '/pages/index/index' })

  if (process.env.TARO_ENV !== 'weapp') {
    return (
      <View className='page-shell profile-gate'>
        <Text className='display-font profile-gate-title'>用户档案仅在微信小程序中提供</Text>
        <Button className='primary-button' onClick={goHome}>回到学习首页</Button>
      </View>
    )
  }

  return (
    <View className='page-shell profile-page'>
      <View className='profile-topbar'>
        <Button className='icon-button' aria-label='返回' onClick={() => Taro.navigateBack()}>
          ←
        </Button>
        <Text className='display-font profile-topbar-title'>我的学习档案</Text>
        <View className='profile-topbar-spacer' />
      </View>

      {pageState === 'loading' ? (
        <View className='profile-state panel'>
          <View className='profile-loading-mark'>…</View>
          <Text className='display-font profile-state-title'>正在整理你的档案</Text>
          <Text className='muted profile-state-copy'>小墨正在把已经完成的闯关收进书架。</Text>
        </View>
      ) : pageState === 'loggedOut' ? (
        <View className='profile-state panel panel-yellow'>
          <View className='profile-loading-mark'>匿</View>
          <Text className='display-font profile-state-title'>已进入匿名学习模式</Text>
          <Text className='muted profile-state-copy'>
            账号和学习历史仍然保留，再次使用微信身份登录即可继续同步。
          </Text>
          <Button className='primary-button' onClick={() => void handleWechatLogin()}>
            使用微信身份登录
          </Button>
          <Button className='secondary-button profile-secondary-action' onClick={goHome}>
            继续匿名学习
          </Button>
        </View>
      ) : pageState === 'login' ? (
        <View className='profile-state panel panel-yellow'>
          <View className='profile-loading-mark'>墨</View>
          <Text className='display-font profile-state-title'>微信登录暂时不可用</Text>
          <Text className='muted profile-state-copy'>
            你的学习仍可匿名继续；重试后即可同步档案与闯关历史。
          </Text>
          <Button className='primary-button' onClick={() => void loadProfile()}>
            重试微信登录
          </Button>
          <Button className='secondary-button profile-secondary-action' onClick={goHome}>
            继续匿名学习
          </Button>
        </View>
      ) : pageState === 'error' || !profile || !history ? (
        <View className='profile-state panel panel-red'>
          <View className='profile-loading-mark'>!</View>
          <Text className='display-font profile-state-title'>档案暂时没有打开</Text>
          <Text className='muted profile-state-copy'>
            {errorMessage || '请检查网络后重试。'}
          </Text>
          <Button className='primary-button' onClick={() => void loadProfile()}>
            重新加载
          </Button>
          <Button className='secondary-button profile-secondary-action' onClick={goHome}>
            回到学习首页
          </Button>
        </View>
      ) : (
        <ScrollView className='profile-scroll' scrollY>
          <View className='profile-content'>
            <View className='profile-identity panel panel-yellow'>
              {profile.avatar_url ? (
                <Image className='profile-avatar' src={profile.avatar_url} mode='aspectFill' />
              ) : (
                <View className='profile-avatar profile-avatar-fallback'>
                  {profile.nickname.slice(0, 1)}
                </View>
              )}
              <View className='profile-identity-copy'>
                <Text className='display-font profile-nickname'>{profile.nickname}</Text>
                <Text className='profile-tagline'>每一话，都算数。</Text>
              </View>
              <Button
                className='profile-edit-button'
                onClick={() => Taro.navigateTo({ url: '/pages/profile-edit/index' })}
              >
                编辑
              </Button>
            </View>

            <View className='profile-xp-strip'>
              <Text>累计经验 XP</Text>
              <Text className='profile-xp-value'>{profile.total_xp} XP</Text>
            </View>

            <View className='profile-stats'>
              <View className='profile-stat panel'>
                <Text className='profile-stat-value'>{profile.quiz_count}</Text>
                <Text className='profile-stat-label'>完成闯关</Text>
              </View>
              <View className='profile-stat panel'>
                <Text className='profile-stat-value'>{profile.correct_count}</Text>
                <Text className='profile-stat-label'>答对题目</Text>
              </View>
              <View className='profile-stat panel'>
                <Text className='profile-stat-value'>
                  {profile.quiz_count > 0 ? `${profile.average_accuracy}%` : '—'}
                </Text>
                <Text className='profile-stat-label'>平均正确率</Text>
              </View>
            </View>

            <View className='profile-history-heading'>
              <Text className='display-font profile-section-title'>闯关历史</Text>
              <Text className='muted profile-history-total'>{history.total} 条记录</Text>
            </View>

            {history.items.length > 0 ? (
              <View className='profile-history-list'>
                {history.items.map((item) => (
                  <HistoryRow key={item.quiz_id} item={item} />
                ))}
              </View>
            ) : (
              <View className='profile-empty panel'>
                <Text className='display-font profile-empty-mascot'>小墨</Text>
                <Text className='display-font profile-empty-title'>书架还空着</Text>
                <Text className='muted profile-empty-copy'>
                  去印下第一话，学过的知识就会留在这里。
                </Text>
                <Button className='primary-button' onClick={goHome}>
                  回首页，开始学习
                </Button>
              </View>
            )}

            {errorMessage && (
              <Text className='profile-inline-error'>{errorMessage}</Text>
            )}
            {history.items.length < history.total && (
              <Button
                className='secondary-button profile-load-more'
                disabled={loadingMore}
                onClick={() => void loadMore()}
              >
                {loadingMore ? '正在加载…' : '加载更早的闯关'}
              </Button>
            )}
            <Button
              className='secondary-button profile-logout-button'
              onClick={() => void handleLogout()}
            >
              退出登录
            </Button>
          </View>
        </ScrollView>
      )}
    </View>
  )
}
