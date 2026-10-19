import type { PropsWithChildren } from 'react'
import Taro, { useLaunch } from '@tarojs/taro'

import './app.scss'

function App({ children }: PropsWithChildren) {
  useLaunch(() => {
    Taro.setNavigationBarTitle({ title: 'AI智学' })
  })

  return children
}

export default App
