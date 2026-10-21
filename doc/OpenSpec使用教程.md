# OpenSpec 使用教程

本文按 OpenSpec `1.14.3` 编写，只讲一条最短路径：

```text
安装一次 -> 写方案 -> 你确认 -> AI 写代码 -> 测试 -> 归档
```

你不需要先学一套复杂理论。只要记住下面三句话：

1. 先让 OpenSpec 写清楚“要做什么”，暂时不要写代码。
2. 你看懂方案并确认后，再让 AI 按任务清单写代码。
3. 功能做完并测试通过后，把这次变更归档。

---

## 一、安装 OpenSpec

### 1. 检查 Node.js

在项目根目录打开 PowerShell，执行：

```powershell
node -v
```

OpenSpec 要求 Node.js `20.19.0` 或更高版本。

本文编写时，本机检测到的版本是 `v20.18.0`，比要求低一点，所以第一步需要先升级。

最简单的方法：

1. 打开 <https://nodejs.org/>。
2. 下载并安装最新的 LTS 版本。
3. 安装完成后，关闭所有终端。
4. 重新打开 PowerShell，再次执行 `node -v`。

只要版本不低于 `20.19.0` 就可以继续。

### 2. 全局安装 OpenSpec

```powershell
npm install -g @fission-ai/openspec@latest
```

检查是否安装成功：

```powershell
openspec --version
```

如果提示找不到 `openspec`，先关闭终端再重新打开。

如果出现权限错误，用管理员身份打开 PowerShell 后重新执行安装命令。

---

## 二、给项目初始化一次

进入项目根目录：

```powershell
cd D:\code\hua-ai-learn
```

执行初始化：

```powershell
openspec init --tools codex --language Chinese
```

这条命令会创建：

```text
openspec/
  specs/      当前项目已经确定的正式需求
  changes/    正在做的功能方案
  config.yaml 项目级配置

.agents/
  skills/     Codex 使用的 OpenSpec 技能
```

初始化成功后，不需要手工创建 Markdown 文件，后续交给 OpenSpec 生成。

这里使用 `Chinese` 而不是直接传中文参数，是为了避免部分 Windows 终端把中文参数写成乱码。OpenSpec 会把“所有文档使用中文”写入项目配置。

注意：

- 一个项目只初始化一次。
- 如果项目里已经有 `openspec` 目录，不要重复执行 `openspec init`。
- OpenSpec 升级后，再执行 `openspec update` 更新项目里的技能文件。

---

## 三、开始一个新功能

下面以一个小功能为例：

> 在答题报告页显示本次答错的题目。

第一次使用不要选太大、太模糊的功能。一次只做一个明确结果，例如“显示本次错题”，而不是“完善整个错题本系统”。

### 1. 在 Codex 里选择 `openspec-propose`

在 Codex 桌面端：

1. 在当前项目中新建一个对话。
2. 在侧边栏的 Skills 中选择 `openspec-propose`。
3. 粘贴下面的任务描述。

如果你使用的是 Codex CLI 或 IDE，也可以直接输入：

```text
$openspec-propose
```

然后接上你的需求。

### 2. 直接复制这段需求

```text
使用 openspec-propose，为当前项目新增“报告页显示本次错题”功能。

需求：
1. 用户答完题进入报告页后，可以看到本次答错的题目列表。
2. 每题显示题干、用户答案、正确答案和解析。
3. 没有错题时显示明确的空状态。
4. 只修改微信小程序和现有后端接口，不改 H5 的用户系统。
5. 复用现有答题记录和报告数据结构；如果确实需要新增字段，先在方案中说明原因。

这次只生成 OpenSpec 方案，不要修改任何业务代码。
完成后列出需要我确认的关键点。
```

你只需要把第一行的功能名称和后面的需求替换成自己真正想做的内容。

一个好需求至少要说清楚：

1. 给谁用。
2. 用户会看到什么、能做什么。
3. 哪些端、哪些模块要做。
4. 哪些内容明确不做。
5. 怎样算完成。

### 3. 等它生成方案

正常情况下，会生成类似下面的目录：

```text
openspec/changes/add-report-wrong-questions/
  proposal.md
  design.md
  tasks.md
  specs/
    report-review/spec.md
```

每个文件的作用：

| 文件 | 你要看什么 |
| --- | --- |
| `proposal.md` | 为什么做、具体改什么、影响哪里 |
| `spec.md` | 系统必须满足什么行为，尤其是 `WHEN / THEN` 场景 |
| `design.md` | 技术上准备怎么做 |
| `tasks.md` | AI 接下来要执行的步骤清单 |

你只需要重点检查三件事：

1. 它理解的功能是不是你想要的。
2. 有没有偷偷扩大范围。
3. `tasks.md` 是否具体，不能只写“优化代码”“完善功能”这种空话。

如果方案不对，直接在同一个对话里说：

```text
先不要写代码。请只修改 OpenSpec 方案：
1. 去掉 XXX。
2. 增加 XXX。
3. tasks.md 要写成可以直接执行的步骤。
```

等方案改对后，再进入下一步。

---

## 四、让 AI 按方案写代码

方案确认后，新建一条消息，明确进入实施阶段。

在 Codex 桌面端选择 `openspec-apply-change` 技能，或者输入：

```text
$openspec-apply-change add-report-wrong-questions
```

然后发送：

```text
请按 openspec/changes/add-report-wrong-questions/tasks.md 开始实现。

要求：
1. 每完成一项就勾选对应任务。
2. 保持修改范围最小，不做方案以外的重构。
3. 后端修改后运行相关 pytest。
4. 前端修改后运行相关构建或类型检查。
5. 如果发现方案和现有代码冲突，先停下来告诉我，不要自行改需求。
6. 全部完成后汇总修改文件和测试结果。
```

这一步才是真正修改业务代码。

实施过程中，你可能会看到它依次做这些事：

1. 阅读 `proposal.md`、`spec.md`、`design.md`、`tasks.md`。
2. 检查现有前后端代码。
3. 修改代码。
4. 运行测试。
5. 把 `tasks.md` 里的 `[ ]` 改成 `[x]`。

不要让 AI 跳过测试。测试失败时，把完整报错贴回对话，让它继续修复。

---

## 五、检查并验证

代码写完后，先自己看一遍修改内容，再执行验证。

查看当前有哪些变更：

```powershell
openspec list
```

查看某个变更：

```powershell
openspec show add-report-wrong-questions
```

校验方案是否完整：

```powershell
openspec validate add-report-wrong-questions --strict
```

如果校验报错，把报错原样发给 Codex：

```text
请修复下面的 OpenSpec 校验错误，不要改变已经确认的功能范围：
<粘贴报错>
```

项目自己的测试也要通过。当前项目常用的后端测试命令是：

```powershell
Push-Location .\backend
..\.venv\Scripts\python -m pytest -q
Pop-Location
```

前端至少执行本次改动相关的构建或检查。测试没通过，不要归档。

---

## 六、归档本次变更

功能已经完成、测试通过、你确认没有问题后，才能归档。

在 Codex 桌面端选择 `openspec-archive-change` 技能，或者输入：

```text
$openspec-archive-change add-report-wrong-questions
```

也可以直接使用 CLI：

```powershell
openspec archive add-report-wrong-questions
```

归档会做两件事：

1. 把本次变更移到 `openspec/changes/archive/`。
2. 把本次新增或修改的正式需求同步到 `openspec/specs/`。

归档完成后，这个功能就从“正在做”变成“项目当前行为”的一部分。

---

## 七、只用记住这些命令

| 你想做什么 | 命令 |
| --- | --- |
| 查看正在做的变更 | `openspec list` |
| 查看已经确定的正式需求 | `openspec list --specs` |
| 查看某个变更 | `openspec show <变更名>` |
| 校验全部内容 | `openspec validate --all` |
| 归档已完成变更 | `openspec archive <变更名>` |
| OpenSpec 升级后更新项目 | `openspec update` |

Codex 中最常用的四个技能：

| 技能 | 用途 |
| --- | --- |
| `openspec-explore` | 想法还不清楚时，先和 AI 一起梳理 |
| `openspec-propose` | 把清楚的需求写成方案和任务 |
| `openspec-apply-change` | 按任务清单写代码 |
| `openspec-archive-change` | 完成后归档并更新正式需求 |

---

## 八、最容易犯的五个错误

1. 需求一句话太模糊，例如“优化一下用户体验”。应该说清楚页面、行为和验收标准。
2. 一个变更塞进很多功能。一次只做一个可验收的结果。
3. 方案还没看就让 AI 写代码。先检查 `proposal.md`、`spec.md` 和 `tasks.md`。
4. 中途改需求却不改方案。先更新 OpenSpec，再继续写代码。
5. 没测试就归档。归档代表这次变更已经完成，不是“先记下来以后再说”。

---

## 九、第一次使用的推荐流程

第一次只用照下面做：

1. 升级 Node.js 到 `20.19.0` 以上。
2. 执行 `npm install -g @fission-ai/openspec@latest`。
3. 执行 `openspec init --tools codex --language Chinese`。
4. 选一个很小、很明确的功能。
5. 用 `openspec-propose` 生成方案。
6. 看懂并修改方案。
7. 用 `openspec-apply-change` 写代码和跑测试。
8. 用 `openspec-archive-change` 归档。

官方资料：

- 仓库：<https://github.com/Fission-AI/OpenSpec/>
- 快速开始：<https://openspec.dev/docs/quickstart>
