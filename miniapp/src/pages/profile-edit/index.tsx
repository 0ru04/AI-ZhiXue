import { useState } from 'react'
import { Button, Input, Text, View } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { getUserProfile, updateUserProfile } from '../../services/api'
import { ensureWechatLogin } from '../../services/auth'
import './index.scss'

type PageState = 'loading' | 'ready' | 'saving' | 'login' | 'error'

export default function ProfileEditPage() {
  const [pageState, setPageState] = useState<PageState>('loading')
  const [nickname, setNickname] = useState('')
  const [avatarUrl, setAvatarUrl] = useState('')
  const [errorMessage, setErrorMessage] = useState('')

  const loadProfile = async () => {
    setPageState('loading')
    setErrorMessage('')
    try {
      const token = await ensureWechatLogin()
      if (!token) {
        setPageState('login')
        return
      }
      const profile = await getUserProfile()
      setNickname(profile.nickname)
      setAvatarUrl(profile.avatar_url || '')
      setPageState('ready')
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '个人资料暂时无法加载',
      )
      setPageState('error')
    }
  }

  useDidShow(() => {
    if (process.env.TARO_ENV === 'weapp') void loadProfile()
  })

  const saveProfile = async () => {
    const trimmedNickname = nickname.trim()
    const trimmedAvatar = avatarUrl.trim()
    if (!trimmedNickname) {
      setErrorMessage('昵称不能为空。')
      return
    }
    if (trimmedNickname.length > 100) {
      setErrorMessage('昵称最多 100 个字符。')
      return
    }

    setPageState('saving')
    setErrorMessage('')
    try {
      await updateUserProfile({
        nickname: trimmedNickname,
        avatar_url: trimmedAvatar || null,
      })
      Taro.showToast({ title: '资料已保存', icon: 'success' })
      Taro.navigateBack()
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : '资料保存失败，请重试',
      )
      setPageState('ready')
    }
  }

  if (process.env.TARO_ENV !== 'weapp') {
    return (
      <View className='page-shell profile-edit-gate'>
        <Text className='display-font profile-edit-title'>资料编辑仅在微信小程序中提供</Text>
        <Button className='primary-button' onClick={() => Taro.navigateBack()}>
          返回
        </Button>
      </View>
    )
  }

  return (
    <View className='page-shell profile-edit-page'>
      <View className='profile-edit-topbar'>
        <Button className='icon-button' aria-label='关闭' onClick={() => Taro.navigateBack()}>
          ×
        </Button>
        <Text className='display-font profile-edit-topbar-title'>编辑资料</Text>
        <View className='profile-edit-spacer' />
      </View>

      {pageState === 'loading' ? (
        <View className='profile-edit-state panel'>
          <Text className='display-font profile-edit-title'>正在读取资料…</Text>
        </View>
      ) : pageState === 'login' || pageState === 'error' ? (
        <View className='profile-edit-state panel panel-red'>
          <Text className='display-font profile-edit-title'>
            {pageState === 'login' ? '微信登录暂不可用' : '资料暂时无法打开'}
          </Text>
          <Text className='profile-edit-error'>
            {errorMessage || '请重试，或返回后继续匿名学习。'}
          </Text>
          <Button className='primary-button' onClick={() => void loadProfile()}>
            重试
          </Button>
        </View>
      ) : (
        <View className='profile-edit-content'>
          <View className='profile-edit-form panel'>
            <Text className='display-font profile-edit-title'>给档案留个名字</Text>
            <View className='profile-edit-field'>
              <Text className='profile-edit-label'>昵称</Text>
              <Input
                className='profile-edit-input'
                maxlength={100}
                value={nickname}
                placeholder='输入昵称'
                onInput={(event) => setNickname(event.detail.value)}
              />
              <Text className='profile-edit-helper'>最多 100 个字符，不能只输入空格。</Text>
            </View>
            <View className='profile-edit-field'>
              <Text className='profile-edit-label'>头像 URL</Text>
              <Input
                className='profile-edit-input'
                maxlength={500}
                value={avatarUrl}
                placeholder='https://example.com/avatar.png'
                onInput={(event) => setAvatarUrl(event.detail.value)}
              />
              <Text className='profile-edit-helper'>
                支持 HTTP / HTTPS 图片地址；留空可恢复默认头像。
              </Text>
            </View>
            {errorMessage && (
              <Text className='profile-edit-error'>{errorMessage}</Text>
            )}
            <View className='profile-edit-actions'>
              <Button
                className='secondary-button'
                disabled={pageState === 'saving'}
                onClick={() => Taro.navigateBack()}
              >
                取消
              </Button>
              <Button
                className='primary-button'
                disabled={pageState === 'saving'}
                onClick={() => void saveProfile()}
              >
                {pageState === 'saving' ? '正在保存…' : '保存资料'}
              </Button>
            </View>
          </View>
        </View>
      )}
    </View>
  )
}
