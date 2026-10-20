import type { PropsWithChildren } from 'react'
import Taro, { useLaunch } from '@tarojs/taro'
import { ensureWechatLogin } from './services/auth'

import './app.scss'

function App({ children }: PropsWithChildren) {
  useLaunch(() => {
    Taro.setNavigationBarTitle({ title: 'AI智学' })
    if (process.env.TARO_ENV === 'weapp') {
      void ensureWechatLogin()
    }
  })

  return children
}

export default App
