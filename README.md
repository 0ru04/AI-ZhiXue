# AI智学 MVP

微信小程序核心闭环：输入一段学习内容，生成 5 道闯关题，逐题即时讲解，并生成复盘报告。前端使用 Taro 4.3 + React + TypeScript，支持微信小程序和 H5 浏览器验收；后端使用 FastAPI、Pydantic v2 和 LangChain 的 OpenAI 兼容模型适配。

本轮不包含联网搜索、账号体系、持久化服务端数据库或 P1/P2/P3 进阶玩法。学习记录保存在小程序本机；DeepSeek API Key 仅供后端读取。

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
- Swagger：`http://127.0.0.1:8000/docs`

接口使用 `{ "code", "message", "data" }` 统一响应。模型未配置、内容被拦截、模型超时或输出不合格时均返回明确错误，不会返回假题目或假报告。

运行后端测试：

```powershell
Push-Location .\backend
..\.venv\Scripts\python -m pytest -q
Pop-Location
```

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

小程序请求地址默认是 `http://127.0.0.1:8000`。可通过构建环境变量 `TARO_APP_API_BASE_URL` 指向本机局域网或已部署的后端地址；不要在小程序环境变量或前端代码里放置 DeepSeek 密钥。

## 浏览器验收（H5）

在一个终端启动后端（见上面的启动 API），在另一个终端执行：

```powershell
Push-Location .\miniapp
npm run dev:h5
Pop-Location
```

用浏览器打开 `http://localhost:10086`。如端口被占用，按 Taro 输出的地址打开，并把对应 origin（协议、主机、端口）加入根目录 `.env` 的逗号分隔 `CORS_ORIGINS`。H5 和小程序共用页面与 API；微信转发、相册授权/保存等微信原生能力须在微信开发者工具或真机中验收。H5 静态构建可用 `npm run build:h5`。

分享海报支持 Canvas 保存到相册和微信转发；小程序码按原型明确保留为占位图，需取得正式小程序码后再替换。

## 答题规则

- 每轮固定 5 题：3 道单选、1 道多选、1 道判断。
- 每题完全正确获得 20 XP 和 3 知识币。
- 多选题只漏选且没有错选获得 10 XP；答错不扣 XP。
- 正确率、知识点掌握情况和连击由后端根据题目答案重新计算，不采信客户端提交的 `is_correct`。
