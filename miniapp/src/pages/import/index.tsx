import { useState } from 'react'
import { Button, Input, Text, Textarea, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import {
  generateQuiz,
  generateSourceQuiz,
  parseSourceDocument,
  parseSourceUrl,
  waitForQuizGeneration,
} from '../../services/api'
import type { ParsedSource } from '../../types'
import { createRun, saveRun } from '../../utils/session'
import './index.scss'

type SourceTab = 'text' | 'document' | 'web' | 'video'
type PageMode = 'idle' | 'parsing' | 'generating'

const SOURCE_TABS: Array<{ key: SourceTab; label: string; icon: string }> = [
  { key: 'text', label: '文本', icon: 'Aa' },
  { key: 'document', label: '文档', icon: '▤' },
  { key: 'web', label: '网页', icon: '◎' },
  { key: 'video', label: '视频', icon: '▷' },
]

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback
}

function formatFileSize(bytes: number) {
  if (!bytes) return ''
  if (bytes >= 1024 * 1024) {
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  }
  return `${Math.max(1, Math.round(bytes / 1024))} KB`
}

function getDocumentFormat(fileName: string) {
  return /\.pdf$/i.test(fileName) ? 'PDF' : 'DOCX'
}

export default function ImportPage() {
  const [tab, setTab] = useState<SourceTab>('text')
  const [mode, setMode] = useState<PageMode>('idle')
  const [text, setText] = useState('')
  const [url, setUrl] = useState('')
  const [fileName, setFileName] = useState('')
  const [filePath, setFilePath] = useState('')
  const [fileSize, setFileSize] = useState(0)
  const [parsed, setParsed] = useState<ParsedSource | null>(null)
  const [selectedPoints, setSelectedPoints] = useState<string[]>([])
  const [error, setError] = useState('')

  const applyParsedSource = (source: ParsedSource) => {
    setParsed(source)
    setSelectedPoints(source.knowledge_points)
    setError('')
  }

  const chooseDocument = async () => {
    if (process.env.TARO_ENV !== 'weapp') {
      setError('文档上传请在微信小程序中使用；网页和视频链接可直接解析。')
      return
    }
    try {
      const result = await Taro.chooseMessageFile({
        count: 1,
        type: 'file',
        extension: ['pdf', 'docx'],
      })
      const file = result.tempFiles[0]
      if (!file) return
      if (file.size > 20 * 1024 * 1024) {
        setError('单个文件不能超过 20MB，请更换文件后重试。')
        return
      }
      if (!/\.(pdf|docx)$/i.test(file.name)) {
        setError('仅支持 PDF 和 .docx 文件，旧版 .doc 暂不支持。')
        return
      }
      setFileName(file.name)
      setFileSize(file.size)
      setFilePath(file.path)
      setParsed(null)
      setSelectedPoints([])
      setError('')
    } catch (cause) {
      if (
        cause instanceof Error &&
        cause.message.toLowerCase().includes('cancel')
      ) {
        return
      }
      setError(errorMessage(cause, '选择文件失败，请重试。'))
    }
  }

  const removeDocument = () => {
    if (mode !== 'idle') return
    setFileName('')
    setFilePath('')
    setFileSize(0)
    setParsed(null)
    setSelectedPoints([])
    setError('')
  }

  const parseDocument = async () => {
    if (!filePath || mode !== 'idle') return
    setMode('parsing')
    setError('')
    try {
      applyParsedSource(await parseSourceDocument(filePath, fileName))
    } catch (cause) {
      setError(errorMessage(cause, '文档解析失败，请检查文件后重试。'))
    } finally {
      setMode('idle')
    }
  }

  const parseLink = async () => {
    if (!url.trim() || mode !== 'idle') return
    setMode('parsing')
    setError('')
    setParsed(null)
    try {
      const source = await parseSourceUrl(url.trim())
      if (tab === 'video' && source.source_type !== 'video') {
        throw new Error('请输入 B 站、抖音或微信视频号的公开视频链接。')
      }
      applyParsedSource(source)
    } catch (cause) {
      setError(errorMessage(cause, '链接解析失败，请检查链接后重试。'))
    } finally {
      setMode('idle')
    }
  }

  const startQuiz = async (
    request: ReturnType<typeof generateQuiz>,
  ) => {
    setMode('generating')
    setError('')
    try {
      const task = await request.promise
      const quiz = await waitForQuizGeneration(
        task.task_id,
        await request.authenticated,
      )
      saveRun(createRun(quiz, await request.authenticated))
      await Taro.navigateTo({ url: '/pages/quiz/index' })
    } catch (cause) {
      setError(errorMessage(cause, '生成题目失败，请重试。'))
      setMode('idle')
    }
  }

  const generateFromText = () => {
    if (!text.trim() || mode !== 'idle') return
    void startQuiz(generateQuiz(text.trim()))
  }

  const generateFromSource = () => {
    if (!parsed || selectedPoints.length === 0 || mode !== 'idle') {
      return
    }
    void startQuiz(generateSourceQuiz(parsed, selectedPoints))
  }

  const togglePoint = (point: string) => {
    setSelectedPoints((current) =>
      current.includes(point)
        ? current.filter((item) => item !== point)
        : [...current, point],
    )
  }

  const parseButtonLabel =
    mode === 'parsing' ? '正在解析材料…' : '解析材料'
  const isBusy = mode !== 'idle'
  const documentFormat = fileName ? getDocumentFormat(fileName) : ''
  const documentSize = formatFileSize(fileSize)
  const documentMeta = [documentFormat, documentSize].filter(Boolean).join(' · ')
  const documentStatus =
    mode === 'parsing' ? '正在解析' : parsed ? '已解析' : '等待解析'
  const documentKicker = parsed ? '解析完成' : '文件已选择'

  const knowledgePanel = parsed ? (
    <View className='knowledge-panel'>
      <View className='knowledge-heading'>
        <Text className='display-font'>确认要学习的知识点</Text>
        <Text>
          {selectedPoints.length} / {parsed.knowledge_points.length}
        </Text>
      </View>
      {parsed.knowledge_points.map((point, index) => (
        <Button
          key={`${point}-${index}`}
          className='knowledge-row'
          disabled={isBusy}
          onClick={() => togglePoint(point)}
        >
          <Text
            className={`knowledge-check ${
              selectedPoints.includes(point) ? 'knowledge-check-on' : ''
            }`}
          >
            {selectedPoints.includes(point) ? '✓' : ''}
          </Text>
          <Text className='knowledge-label'>{point}</Text>
          <Text className='knowledge-tag'>
            {parsed.headings.includes(point) ? '结构' : '要点'}
          </Text>
        </Button>
      ))}
      <View className='knowledge-actions'>
        <Button
          className='minor-button'
          disabled={isBusy}
          onClick={() => setSelectedPoints(parsed.knowledge_points.slice(0, 3))}
        >
          只留 3 个
        </Button>
        <Button
          className='minor-button'
          disabled={isBusy}
          onClick={() => setSelectedPoints(parsed.knowledge_points)}
        >
          全选
        </Button>
      </View>
      <Text className='import-note'>
        确认后只围绕所选知识点出题；原始材料不会直接出题。
      </Text>
      <Button
        className='import-primary'
        disabled={selectedPoints.length === 0 || isBusy}
        onClick={generateFromSource}
      >
        {mode === 'generating'
          ? '正在生成题目…'
          : '确认，开始出题'}{' '}
        <Text className='button-arrow'>→</Text>
      </Button>
    </View>
  ) : null

  return (
    <View
      className={`page-shell import-page ${
        tab === 'document' && !parsed ? 'import-page-with-action' : ''
      }`}
    >
      <View className='page-content import-content'>
        <View className='import-section-head'>
          <Text className='display-font import-section-title'>选择导入方式</Text>
          <View className='import-section-rule' />
        </View>

        <View className='source-tabs'>
          {SOURCE_TABS.map((item) => (
            <Button
              key={item.key}
              className={`source-tab ${
                tab === item.key ? 'source-tab-active' : ''
              }`}
              disabled={isBusy}
              onClick={() => {
                setTab(item.key)
                setParsed(null)
                setSelectedPoints([])
                setError('')
              }}
            >
              <Text
                className={`source-tab-icon source-tab-icon-${item.key}`}
              >
                {item.icon}
              </Text>
              <Text className='source-tab-label'>{item.label}</Text>
              {tab === item.key && <View className='source-tab-mark' />}
            </Button>
          ))}
        </View>

        {tab === 'text' ? (
          <>
            <View className='import-panel'>
              <Textarea
                className='import-textarea body-font'
                maxlength={500}
                value={text}
                placeholder='输入一句话或一段学习内容…'
                onInput={(event) => setText(event.detail.value)}
              />
              <View className='import-caption'>
                <Text>支持一句话 / 一段文本</Text>
                <Text>{text.length} / 500</Text>
              </View>
            </View>
            <Button
              className='import-primary'
              disabled={!text.trim() || isBusy}
              onClick={generateFromText}
            >
              {mode === 'generating'
                ? '正在生成题目…'
                : '开始印刷题目'}{' '}
              <Text className='button-arrow'>→</Text>
            </Button>
          </>
        ) : (
          <>
            {tab === 'document' ? (
              <>
                <View className='upload-card'>
                  {!fileName ? (
                    <Button
                      className='dropzone'
                      disabled={
                        isBusy || process.env.TARO_ENV !== 'weapp'
                      }
                      onClick={chooseDocument}
                    >
                      <View className='doc-illustration'>
                        <View className='doc-sheet doc-sheet-back' />
                        <View className='doc-sheet doc-sheet-front'>
                          <View className='doc-fold' />
                          <View className='doc-lines' />
                        </View>
                        <Text className='doc-badge'>PDF</Text>
                        <Text className='upload-arrow'>↑</Text>
                      </View>

                      <Text className='dropzone-title'>
                        选择 PDF 或 DOCX
                      </Text>
                      <Text className='dropzone-hint'>
                        {process.env.TARO_ENV === 'weapp'
                          ? '从微信聊天记录中选择学习文件'
                          : '文档上传请在微信小程序中使用'}
                      </Text>

                      {process.env.TARO_ENV === 'weapp' && (
                        <View className='choose-file-button'>
                          <Text className='choose-file-plus'>＋</Text>
                          <Text className='choose-file-label'>选择文件</Text>
                        </View>
                      )}

                      {process.env.TARO_ENV === 'weapp' && (
                        <View className='format-row'>
                          <Text className='format-chip format-chip-pdf'>
                            PDF
                          </Text>
                          <Text className='format-chip format-chip-docx'>
                            DOCX
                          </Text>
                          <Text className='format-size'>
                            单个文件 ≤ 20MB
                          </Text>
                        </View>
                      )}
                    </Button>
                  ) : (
                    <View className='selected-state'>
                      <Text className='selected-kicker'>
                        {documentKicker}
                      </Text>
                      <View className='selected-file-row'>
                        <View className='selected-file-icon'>
                          <Text className='selected-file-icon-label'>
                            {documentFormat}
                          </Text>
                        </View>
                        <View className='selected-file-meta'>
                          <Text className='selected-file-name'>{fileName}</Text>
                          <Text className='selected-file-info'>
                            {documentMeta}
                          </Text>
                          <Text className='selected-file-status'>
                            {documentStatus}
                          </Text>
                        </View>
                      </View>
                      <View className='selected-actions'>
                        <Button
                          className='selected-action'
                          disabled={isBusy}
                          onClick={chooseDocument}
                        >
                          更换文件
                        </Button>
                        <Button
                          className='selected-action selected-action-danger'
                          disabled={isBusy}
                          onClick={removeDocument}
                        >
                          移除文件
                        </Button>
                      </View>
                      <Text className='selected-note'>
                        {parsed
                          ? '知识点已提取，请在下方确认学习范围'
                          : '解析后可确认由 AI 提取的知识点'}
                      </Text>
                    </View>
                  )}
                </View>

                <View className='import-notice'>
                  <Text className='import-notice-mark'>!</Text>
                  <View className='import-notice-copy'>
                    <Text className='import-notice-strong'>
                      PDF 最多解析 30 页。
                    </Text>
                    <Text>旧版 .doc、扫描版和加密文件暂不支持。</Text>
                  </View>
                </View>
              </>
            ) : (
              <>
                <View className='url-field'>
                  <Input
                    value={url}
                    placeholder={
                      tab === 'video'
                        ? '粘贴 B 站 / 抖音 / 微信视频号链接'
                        : '粘贴公开网页链接 https://…'
                    }
                    onInput={(event) => setUrl(event.detail.value)}
                    disabled={isBusy}
                  />
                </View>
                {tab === 'video' && (
                  <View className='video-notice'>
                    仅读取公开可访问的字幕；无字幕、需登录或平台不可访问时会明确提示失败，暂不进行语音识别。
                  </View>
                )}
              </>
            )}

            {mode === 'parsing' && (
              <View className='parse-progress'>
                {['读取材料', '提取正文与结构', '整理候选知识点'].map(
                  (step, index) => (
                    <View
                      key={step}
                      className={`parse-step ${
                        index === 1 ? 'parse-step-current' : ''
                      }`}
                    >
                      <Text className='parse-dot'>{index + 1}</Text>
                      <Text>{step}</Text>
                      <Text className='parse-step-state'>
                        {index === 0 ? '进行中' : '等待中'}
                      </Text>
                    </View>
                  ),
                )}
              </View>
            )}

            {!parsed ? (
              tab === 'document' ? (
                <View className='import-fixed-action'>
                  <Button
                    className='import-primary import-primary-fixed'
                    disabled={!filePath || isBusy}
                    onClick={parseDocument}
                  >
                    <Text>
                      {mode === 'parsing'
                        ? '正在解析材料…'
                        : filePath
                          ? '解析材料'
                          : '选择文件后解析'}
                    </Text>
                    <Text className='button-arrow'>→</Text>
                  </Button>
                  <Text className='import-fixed-copy'>
                    文件本身不保留；解析正文随任务临时保存，至少 7 天
                  </Text>
                </View>
              ) : (
                <>
                  <Text className='import-note'>
                    上传文件本身不保留；解析正文会临时写入出题任务记录（至少保留 7 天），并提交给后端配置的
                    AI 服务提炼知识点并生成题目。
                  </Text>
                  <Button
                    className='import-primary'
                    disabled={isBusy || !url.trim()}
                    onClick={parseLink}
                  >
                    {parseButtonLabel}{' '}
                    <Text className='button-arrow'>→</Text>
                  </Button>
                </>
              )
            ) : (
              <>
                {tab !== 'document' && (
                  <View className='parsed-card'>
                    <Text className='parsed-title'>{parsed.title}</Text>
                    <Text className='parsed-meta'>
                      {parsed.source_type === 'video'
                        ? '视频字幕'
                        : '网页正文'}
                      {' · '}
                      {parsed.content.length.toLocaleString()} 字
                    </Text>
                  </View>
                )}
                {knowledgePanel}
              </>
            )}
          </>
        )}

        {error && (
          <View className='import-error'>
            <Text className='import-error-title'>操作没有完成</Text>
            <Text className='import-error-message'>{error}</Text>
            <Text className='import-error-foot'>已保留当前输入内容。</Text>
          </View>
        )}
      </View>
    </View>
  )
}
