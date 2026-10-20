# AI智学 MVP

微信小程序核心闭环：输入一段学习内容，生成 5 道闯关题，逐题即时讲解，并生成复盘报告。前端使用 Taro 4.3 + React + TypeScript，支持微信小程序和 H5 浏览器验收；后端使用 FastAPI、Pydantic v2 和 LangChain 的 OpenAI 兼容模型适配。

核心 MVP 的出题、答题与报告流程保持不变。本次用户系统扩展增加微信小程序登录用户的云端档案和闯关历史；H5 及未登录请求仍可匿名使用核心流程。学习记录也继续保存在小程序本机；DeepSeek API Key 仅供后端读取。本期不包含联网搜索或 P1/P2/P3 进阶玩法。

## 后端

在仓库根目录创建 Python 虚拟环境并安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r .\backend\requirements.txt
```

在根目录的 `.env` 中填写 `DEEPSEEK_API_KEY`。模型默认使用当前 DeepSeek 文档中的 `deepseek-flash`；如需切换，可在 `.env` 设置 `DEEPSEEK_MODEL`。可选的 `CONTENT_BLOCKLIST` 使用逗号分隔本地拦截词；服务还会检查内置的高风险短语。不要把真实密钥提交到仓库。

启动 API：

```powershell
Push-Location .\backend
..\.venv\Scripts\python -m uvicorn app.main:app --reload
Pop-Location
```

- 健康检查：`GET http://127.0.0.1:8000/api/v1/health`
- 生成题目：`POST http://127.0.0.1:8000/api/v1/quiz/generate`
- 生成报告：`POST http://127.0.0.1:8000/api/v1/report/generate`
- 解析 PDF / DOCX：`POST http://127.0.0.1:8000/api/v1/source/parse/document`
- 解析网页 / 视频链接：`POST http://127.0.0.1:8000/api/v1/source/parse/url`
- 根据确认的材料生成题目：`POST http://127.0.0.1:8000/api/v1/source/generate`
- Swagger：`http://127.0.0.1:8000/docs`

接口使用 `{ "code", "message", "data" }` 统一响应。模型未配置、内容被拦截、模型超时或输出不合格时均返回明确错误，不会返回假题目或假报告。

### 输入扩展

- 文档解析支持 PDF 和 `.docx`，单文件最大 20MB；PDF 最多 30 页，提取文本最多 30,000 字。旧版 `.doc`、加密 PDF、扫描版图片 PDF 暂不支持。
- 网页解析仅抓取无需登录的公开 HTTP/HTTPS 页面；请求和重定向均限制为公开 IP 地址，页面正文会剔除导航、脚本、页眉页脚等内容。
- 视频链接会尝试读取 B 站、抖音和微信视频号公开页面提供的字幕轨道/字幕地址；各平台页面结构及字幕可用性不同，不保证每个链接都能解析。当前不接入语音识别；没有无需登录即可读取的字幕时会明确失败，不会尝试绕过平台访问限制。
- 解析后先展示候选知识点供用户确认，再通过新增来源出题接口复用现有题目生成、登录和匿名持久化流程。原有文本出题接口及 500 字限制不变。
- 文档选择使用 Taro `chooseMessageFile`，仅在微信小程序端可用；网页与视频 URL、文本输入可在 H5 和小程序中使用。

运行后端测试：

```powershell
Push-Location .\backend
..\.venv\Scripts\python -m pytest -q
Pop-Location
```

### 用户系统（微信小程序）

用户系统后端使用 MySQL、SQLAlchemy asyncmy 和 Alembic。复制 `.env.example` 中的配置项到本机 `.env`，分别配置：

- `DATABASE_URL`：应用运行数据库，使用 `mysql+asyncmy://...`。
- `TEST_DATABASE_URL`：与运行数据库不同 schema 的测试数据库 URL。
- `WECHAT_APP_ID`、`WECHAT_APP_SECRET`：仅由后端用于调用微信 `code2session`；不要放入小程序配置或提交到仓库。
- `JWT_SECRET_KEY`：至少 32 个字符的随机密钥；不要使用示例值或提交真实密钥。

迁移命令默认只针对测试库；首次建表前确认 `TEST_DATABASE_URL` 指向专用测试 schema：

```powershell
Push-Location .\backend
..\.venv\Scripts\python -m alembic -x database=test upgrade head
Pop-Location
```

应用启动时会连接 `DATABASE_URL`。未配置数据库时，匿名核心流程仍可运行，但用户系统接口和登录用户的数据持久化不可用。当前后端接口为 `POST /api/v1/user/login`、`GET/PUT /api/v1/user/profile`、`GET /api/v1/user/quizzes?page=1&page_size=10` 及 `GET /api/v1/user/quizzes/{quiz_id}`；除登录接口外均需 Bearer JWT。微信真实登录和正式库迁移需在配置好对应环境后单独验收。

## 小程序

Taro CLI 4.3.0 的官方 React + TypeScript 脚手架生成在 `miniapp`。安装依赖并编译微信小程序：

```powershell
Push-Location .\miniapp
npm install
npm run dev:weapp
# 发布构建：npm run build:weapp
Pop-Location
```

用微信开发者工具打开 `miniapp`，或在编译后打开 `miniapp\dist`。脚手架里的 `project.config.json` 使用 `touristappid` 占位值，发布前请改成自己的 AppID。开发者工具本地调试时需按需启用本地服务器域名校验选项；真机和发布环境需要配置可访问的 HTTPS API 域名。

小程序请求地址默认是 `http://127.0.0.1:8000`。可通过构建环境变量 `TARO_APP_API_BASE_URL` 指向本机局域网或已部署的后端地址；不要在小程序环境变量或前端代码里放置 DeepSeek 密钥。微信小程序已接入静默登录、个人档案编辑、闯关历史分页和历史报告回看；登录失败时核心学习流程仍可匿名使用。H5 不启用用户系统。

## 浏览器验收（H5）

在一个终端启动后端（见上面的启动 API），在另一个终端执行：

```powershell
Push-Location .\miniapp
npm run dev:h5
Pop-Location
```

用浏览器打开 `http://localhost:10086`。如端口被占用，按 Taro 输出的地址打开，并把对应 origin（协议、主机、端口）加入根目录 `.env` 的逗号分隔 `CORS_ORIGINS`。H5 和小程序共用核心学习页面与 API；用户系统仅在微信小程序启用。微信转发、相册授权/保存及静默登录须在微信开发者工具或真机中验收。H5 静态构建可用 `npm run build:h5`。

分享海报支持 Canvas 保存到相册和微信转发；小程序码按原型明确保留为占位图，需取得正式小程序码后再替换。

## 答题规则

- 每轮固定 5 题：3 道单选、1 道多选、1 道判断。
- 每题完全正确获得 20 XP 和 3 知识币。
- 多选题只漏选且没有错选获得 10 XP；答错不扣 XP。
- 正确率、知识点掌握情况和连击由后端根据题目答案重新计算，不采信客户端提交的 `is_correct`。
