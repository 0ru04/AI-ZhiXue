import { useState } from 'react'
import {
  Button,
  Canvas,
  ScrollView,
  Text,
  View,
} from '@tarojs/components'
import Taro, { useDidShow, useShareAppMessage } from '@tarojs/taro'
import { generateReport } from '../../services/api'
import type { Report, RunState } from '../../types'
import { readRun, saveRun } from '../../utils/session'
import './index.scss'

function formatDuration(durationMs: number): string {
  const seconds = Math.floor(durationMs / 1000)
  const minutes = Math.floor(seconds / 60)
  return `${minutes} 分 ${seconds % 60} 秒`
}

function splitForPoster(value: string, maxCharacters: number): string[] {
  const lines: string[] = []
  for (let index = 0; index < value.length; index += maxCharacters) {
    lines.push(value.slice(index, index + maxCharacters))
  }
  return lines
}

function drawPlaceholderCode(
  context: ReturnType<typeof Taro.createCanvasContext>,
  left: number,
  top: number,
) {
  const cells = 21
  const cellSize = 3
  context.setFillStyle('#fff')
  context.fillRect(left - 4, top - 4, cells * cellSize + 8, cells * cellSize + 8)
  context.setFillStyle('#191510')
  for (let row = 0; row < cells; row += 1) {
    for (let column = 0; column < cells; column += 1) {
      const inFinder =
        (row < 7 && column < 7) ||
        (row < 7 && column >= cells - 7) ||
        (row >= cells - 7 && column < 7)
      const finderEdge =
        row % 14 === 0 ||
        column % 14 === 0 ||
        row % 14 === 6 ||
        column % 14 === 6
      const finderCenter =
        (row % 14 >= 2 && row % 14 <= 4) &&
        (column % 14 >= 2 && column % 14 <= 4)
      const filled = inFinder
        ? finderEdge || finderCenter
        : (row * 7 + column * 11 + row * column) % 5 < 2
      if (filled) {
        context.fillRect(
          left + column * cellSize,
          top + row * cellSize,
          cellSize,
          cellSize,
        )
      }
    }
  }
}

function savePoster(run: RunState, report: Report) {
  const context = Taro.createCanvasContext('share-poster')
  const width = 390
  const height = 489
  const exportWidth = 750
  const exportHeight = 940
  const cardLeft = 20
  const cardTop = 18
  const cardWidth = 350
  const cardHeight = 438

  context.setFillStyle('#F4EBD3')
  context.fillRect(0, 0, width, height)
  context.setFillStyle('rgba(25, 21, 16, 0.09)')
  for (let x = 5; x < width; x += 9) {
    for (let y = 5; y < height; y += 9) {
      context.fillRect(x, y, 1.5, 1.5)
    }
  }

  context.setFillStyle('#191510')
  context.fillRect(cardLeft + 8, cardTop + 8, cardWidth, cardHeight)
  context.setFillStyle('#EE4B2B')
  context.fillRect(cardLeft + 4, cardTop + 4, cardWidth, cardHeight)
  context.setFillStyle('#FFFDF5')
  context.fillRect(cardLeft, cardTop, cardWidth, cardHeight)
  context.setStrokeStyle('#191510')
  context.setLineWidth(4)
  context.strokeRect(cardLeft, cardTop, cardWidth, cardHeight)

  context.setFillStyle('#191510')
  context.setFontSize(12)
  context.fillText('AI智学 · VOL.001', 36, 47)
  context.setFillStyle('#EE4B2B')
  context.fillRect(298, 34, 58, 20)
  context.setStrokeStyle('#191510')
  context.setLineWidth(2)
  context.strokeRect(298, 34, 58, 20)
  context.setFillStyle('#FFFFFF')
  context.setFontSize(10)
  context.fillText('通关', 315, 48)

  const titleLines = splitForPoster(run.quiz.title, 12).slice(0, 2)
  let currentY = 77
  context.setFillStyle('#191510')
  context.font = '900 20px "Microsoft YaHei", "PingFang SC", sans-serif'
  context.fillText('我把', 36, currentY)

  currentY += 27
  context.setFillStyle('#EE4B2B')
  context.font = '900 22px "Microsoft YaHei", "PingFang SC", sans-serif'
  titleLines.forEach((line) => {
    context.fillText(line, 36, currentY)
    currentY += 26
  })

  context.setFillStyle('#191510')
  context.font = '900 20px "Microsoft YaHei", "PingFang SC", sans-serif'
  context.fillText('学明白了。', 36, currentY)

  const quoteLines = splitForPoster(`“${report.share_quote}”`, 18).slice(0, 2)
  const quoteTop = 164 + Math.max(0, titleLines.length - 1) * 26
  const quoteHeight = 25 + quoteLines.length * 18
  context.setFillStyle('#191510')
  context.fillRect(38, quoteTop + 4, 320, quoteHeight)
  context.setFillStyle('#FBE08A')
  context.fillRect(34, quoteTop, 320, quoteHeight)
  context.setStrokeStyle('#191510')
  context.setLineWidth(2)
  context.strokeRect(34, quoteTop, 320, quoteHeight)
  context.setFillStyle('#191510')
  context.setFontSize(12)
  quoteLines.forEach((line, index) => {
    context.fillText(line, 45, quoteTop + 20 + index * 18)
  })

  const statsY = quoteTop + quoteHeight + 38
  context.setFillStyle('#EE4B2B')
  context.setFontSize(25)
  context.fillText(`${report.accuracy}%`, 47, statsY)
  context.fillText(
    `${report.correct_count}/${report.total_questions}`,
    169,
    statsY,
  )
  context.fillText(`×${report.max_streak}`, 292, statsY)
  context.setFillStyle('#776C5A')
  context.setFontSize(10)
  context.fillText('正确率', 52, statsY + 16)
  context.fillText('答对', 180, statsY + 16)
  context.fillText('最高连击', 297, statsY + 16)

  context.setStrokeStyle('#191510')
  context.setLineWidth(2)
  for (let x = 38; x < 356; x += 8) {
    context.beginPath()
    context.moveTo(x, 346)
    context.lineTo(x + 4, 346)
    context.stroke()
  }

  context.setFillStyle('#191510')
  context.setFontSize(12)
  context.fillText('扫码也来闯一话', 36, 378)
  context.setFillStyle('#776C5A')
  context.setFontSize(9)
  context.fillText('输入任意知识，AI 给你印题', 36, 397)
  drawPlaceholderCode(context, 294, 371)

  context.draw(false, () => {
    Taro.canvasToTempFilePath({
      canvasId: 'share-poster',
      destWidth: exportWidth,
      destHeight: exportHeight,
      success: ({ tempFilePath }) => {
        Taro.saveImageToPhotosAlbum({
          filePath: tempFilePath,
          success: () =>
            Taro.showToast({ title: '海报已保存', icon: 'success' }),
          fail: (error) => {
            const denied =
              error.errMsg.toLowerCase().includes('auth deny') ||
              error.errMsg.toLowerCase().includes('authorize')
            Taro.showModal({
              title: '保存失败',
              content: denied
                ? '请在微信设置中允许保存图片到相册，再试一次。'
                : '海报暂时没有保存成功，请稍后重试。',
              showCancel: false,
            })
          },
        })
      },
      fail: () => {
        Taro.showToast({ title: '海报生成失败，请重试', icon: 'none' })
      },
    })
  })
}

export default function ReportPage() {
  const [run, setRun] = useState<RunState | null>(null)
  const [report, setReport] = useState<Report | null>(null)
  const [pageState, setPageState] = useState<
    'loading' | 'error' | 'success' | 'empty'
  >('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [showPoster, setShowPoster] = useState(false)

  useShareAppMessage(() => ({
    title: report?.share_quote || '把知识印成一话漫画，来和我一起闯关吧！',
    path: '/pages/index/index',
  }))

  const loadReport = async (currentRun: RunState) => {
    const loadingRun: RunState = {
      ...currentRun,
      report_status: 'loading',
    }
    saveRun(loadingRun)
    setRun(loadingRun)
    setPageState('loading')
    setErrorMessage('')

    try {
      const result = await generateReport(loadingRun).promise
      const completedRun: RunState = {
        ...loadingRun,
        report_status: 'ready',
        report: result,
      }
      saveRun(completedRun)
      setRun(completedRun)
      setReport(result)
      setPageState('success')
    } catch (error) {
      const failedRun: RunState = {
        ...loadingRun,
        report_status: 'error',
      }
      saveRun(failedRun)
      setRun(failedRun)
      setErrorMessage(
        error instanceof Error ? error.message : '请稍后再试一次',
      )
      setPageState('error')
    }
  }

  useDidShow(() => {
    const savedRun = readRun()
    if (!savedRun) {
      setRun(null)
      setReport(null)
      setPageState('empty')
      return
    }

    setRun(savedRun)
    if (savedRun.report_status === 'ready' && savedRun.report) {
      setReport(savedRun.report)
      setPageState('success')
      return
    }
    if (savedRun.report_status === 'error') {
      setPageState('error')
      return
    }
    void loadReport(savedRun)
  })

  const closePoster = () => setShowPoster(false)

  if (pageState === 'empty' || !run) {
    return (
      <View className='page-shell report-empty'>
        <Text className='display-font report-empty-title'>还没有这一话的复盘</Text>
        <Button
          className='primary-button'
          onClick={() => Taro.reLaunch({ url: '/pages/index/index' })}
        >
          回首页 <Text>→</Text>
        </Button>
      </View>
    )
  }

  if (pageState === 'loading') {
    return (
      <View className='page-shell report-loading'>
        <View className='report-loading-content panel'>
          <View className='report-loading-ring'>…</View>
          <Text className='display-font report-loading-title'>正在整理这一话</Text>
          <Text className='body-font report-loading-copy'>
            小墨正在对照你的答案，准备一份真实的复盘。
          </Text>
          <View className='skeleton-card'>
            <View className='skeleton-line' />
            <View className='skeleton-line' />
            <View className='skeleton-line' />
            <View className='skeleton-line' />
          </View>
        </View>
      </View>
    )
  }

  if (pageState === 'error') {
    return (
      <View className='page-shell report-error-page'>
        <View className='report-error-content'>
          <View className='mascot report-error-mascot'>
            <View className='mascot-point' />
            <View className='mascot-body' />
            <View className='mascot-eye mascot-eye-left' />
            <View className='mascot-eye mascot-eye-right' />
            <View className='mascot-cheek mascot-cheek-left' />
            <View className='mascot-cheek mascot-cheek-right' />
            <View className='mascot-mouth' />
          </View>
          <Text className='error-badge'>RPT-500</Text>
          <Text className='display-font report-error-title'>报告没印出来</Text>
          <Text className='body-font report-error-copy'>
            你的 {run.answer_records.length} 道答案已经保留，重试不会丢。小墨不会给你一份编出来的报告。
          </Text>
          <View className='report-fail-card'>
            <View className='report-fail-ring'>…</View>
            <View className='report-fail-line' />
            <View className='report-fail-line' />
            <View className='report-fail-line' />
          </View>
          <Text className='error-code'>
            {errorMessage || 'REPORT TIMEOUT'} · 答案已本地保存
          </Text>
          <View className='report-error-actions'>
            <Button
              className='primary-button'
              onClick={() => void loadReport(run)}
            >
              重新生成报告 <Text>→</Text>
            </Button>
            <Button
              className='primary-button button-ghost button-small'
              onClick={() => Taro.reLaunch({ url: '/pages/index/index' })}
            >
              先返回首页
            </Button>
          </View>
          <Text className='tiny report-error-note'>
            失败时不展示虚构报告；重试成功后再进入分享。
          </Text>
        </View>
      </View>
    )
  }

  if (!report) return null

  return (
    <View className='page-shell report-page'>
      <View className='report-topbar'>
        <Button className='icon-button' onClick={() => Taro.navigateBack()}>
          ←
        </Button>
        <Text className='display-font report-topbar-title'>学习复盘</Text>
        <Button className='icon-button' onClick={() => setShowPoster(true)}>
          ↗
        </Button>
      </View>
      <ScrollView className='report-scroll' scrollY>
        <View className='report-content'>
          <View className='accuracy-ring'>
            <View className='accuracy-ring-inner'>
              <Text className='accuracy-value'>{report.accuracy}</Text>
              <Text className='accuracy-label'>正确率 %</Text>
            </View>
          </View>

          <Text className='display-font report-title'>
            第 001 话 · {run.quiz.title}
          </Text>
          <Text className='report-subtitle'>
            {report.correct_count} 题答对 · 用时{' '}
            {formatDuration(report.total_duration_ms)} · 最高连击 ×
            {report.max_streak}
          </Text>

          <View className='summary-bubble body-font'>
            {report.three_line_summary.map((line, index) => (
              <View key={`${index}-${line}`} className='summary-line'>
                <Text className='summary-number'>{index + 1}</Text>
                <Text className='summary-text'>{line}</Text>
              </View>
            ))}
          </View>

          <View className='panel report-section'>
            <Text className='display-font report-section-title'>
              <Text className='section-check'>✓</Text> 掌握得不错
            </Text>
            {report.mastered_points.length > 0 ? (
              <View className='report-tags'>
                {report.mastered_points.map((point) => (
                  <Text key={point} className='report-tag'>{point}</Text>
                ))}
              </View>
            ) : (
              <Text className='body-font report-empty-points'>
                每个知识点都值得再练一次，我们已经为你记下。
              </Text>
            )}
          </View>

          <View className='panel report-section report-section-weak'>
            <Text className='display-font report-section-title'>
              <Text className='section-pin'>⌖</Text> 还要再看一眼
            </Text>
            {report.weak_points.length > 0 ? (
              <View className='report-tags'>
                {report.weak_points.map((point) => (
                  <Text key={point} className='report-tag report-tag-weak'>
                    {point}
                  </Text>
                ))}
              </View>
            ) : (
              <Text className='body-font report-empty-points'>
                这一话没有明显薄弱点，继续保持！
              </Text>
            )}
          </View>

          <View className='panel report-section'>
            <Text className='display-font report-section-title'>
              <Text className='next-label'>NEXT</Text> 下一步
            </Text>
            <View className='advice-list'>
              {report.advice.map((advice, index) => (
                <View key={`${index}-${advice}`} className='advice-row'>
                  <Text className='advice-dot'>·</Text>
                  <Text>{advice}</Text>
                </View>
              ))}
            </View>
          </View>

          <View className='share-quote-card'>
            <Text className='share-quote-mark'>“</Text>
            <Text className='body-font share-quote'>{report.share_quote}</Text>
          </View>

          <Button
            className='primary-button report-poster-button'
            onClick={() => setShowPoster(true)}
          >
            生成分享海报 <Text>↗</Text>
          </Button>
        </View>
      </ScrollView>

      {showPoster && (
        <View className='poster-modal'>
          <View className='poster-modal-head'>
            <Text className='display-font'>分享这一话</Text>
            <Button className='icon-button poster-close' onClick={closePoster}>
              ×
            </Button>
          </View>
          <View className='poster-preview'>
            <View className='poster-top'>
              <Text className='poster-number'>AI智学 · VOL.001</Text>
              <Text className='chip chip-red poster-clear-chip'>通关</Text>
            </View>
            <Text className='poster-title'>
              我把
              <Text className='poster-topic'>{run.quiz.title}</Text>
              学明白了。
            </Text>
            <Text className='body-font poster-quote'>
              “{report.share_quote}”
            </Text>
            <View className='poster-stats'>
              <View className='poster-stat'>
                <Text className='poster-stat-value'>{report.accuracy}%</Text>
                <Text className='poster-stat-label'>正确率</Text>
              </View>
              <View className='poster-stat'>
                <Text className='poster-stat-value'>
                  {report.correct_count}/{report.total_questions}
                </Text>
                <Text className='poster-stat-label'>答对</Text>
              </View>
              <View className='poster-stat'>
                <Text className='poster-stat-value'>×{report.max_streak}</Text>
                <Text className='poster-stat-label'>最高连击</Text>
              </View>
            </View>
            <View className='poster-bottom'>
              <View>
                <Text className='poster-bottom-title'>扫码也来闯一话</Text>
                <Text className='poster-bottom-copy'>
                  小程序码占位 · 输入知识，AI 给你印题
                </Text>
              </View>
              <View className='qr-placeholder'>
                <View className='qr-finder qr-finder-one' />
                <View className='qr-finder qr-finder-two' />
                <View className='qr-finder qr-finder-three' />
                <View className='qr-dots' />
              </View>
            </View>
          </View>
          <View className='poster-actions'>
            <Button
              className='primary-button'
              onClick={() => savePoster(run, report)}
            >
              保存到相册
            </Button>
            <Button
              className='primary-button button-ghost button-small'
              openType='share'
              onClick={closePoster}
            >
              分享给好友
            </Button>
          </View>
          <Text className='poster-hint'>海报不含排名，避免学习攀比。</Text>
          <Canvas
            canvasId='share-poster'
            className='poster-canvas'
            style={{ width: '750rpx', height: '940rpx' }}
          />
        </View>
      )}
    </View>
  )
}
