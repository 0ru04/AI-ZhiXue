const userPages =
  process.env.TARO_ENV === 'weapp'
    ? [
        'pages/profile/index',
        'pages/profile-edit/index',
        'pages/history-detail/index',
      ]
    : []

export default defineAppConfig({
  pages: [
    'pages/index/index',
    'pages/import/index',
    'pages/quiz/index',
    'pages/report/index',
    ...userPages,
  ],
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#F4EBD3',
    navigationBarTitleText: 'AI智学',
    navigationBarTextStyle: 'black',
  }
})
