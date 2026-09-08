# Qoder 工具安装与操作备忘（Windows）

> 面向小白。所有快捷键以官方文档（docs.qoder.com）为准；网上博客与官方冲突的已在备注栏标注。
> 它是什么：AI 编程 IDE + 终端助手，能看懂整个项目、跨文件帮你写/改代码、还能自主跑长任务（Quest 模式）。与 WorkBuddy 互补——WorkBuddy 管对话协作，Qoder 管你在 IDE 里写码。

## 一、安装与登录（全部操作一览表）

| 分类 | 操作 / 项目 | 命令 / 快捷键 | 说明 |
|---|---|---|---|
| 形态选择 | Qoder IDE（桌面应用） | 下载 `https://qoder.com/download` | 日常写码主力，**推荐先装这个** |
| 形态选择 | Qoder CLI（终端命令） | `npm install -g @qoder-ai/qodercli` | 命令行里用 AI 干活，可选 |
| 形态选择 | JetBrains 插件 | IDEA/PyCharm 内装 Qoder 插件 | 用 JetBrains 系 IDE 的人可选 |
| IDE 安装 | 下载并安装 | 双击 `.exe` | 桌面出现 **Qoder IDE** 图标 |
| IDE 启动 | 启动并登录 | 双击图标 → 右上角用户图标 / `Ctrl+Shift+,` | 可注册新号，或用 Google/GitHub 登录 |
| IDE 打开项目 | 打开项目文件夹 | `Ctrl+O` | 选 `D:\xiongtongzhongxin\FastapiAdmin-master`，自动分析整个项目 |
| CLI 安装 | 无 Node 时安装 | `curl -fsSL https://qoder.com/install \| bash`（Git Bash 内） | 备选安装方式 |
| CLI 验证 | 查看版本 | `qodercli --version` | 看到版本号 = 安装成功 |
| CLI 登录 | 浏览器登录 | `qodercli` 进交互后输入 `/login` | 选浏览器登录 |
| 模型配置 | 接其他模型 | 设置 → Models 添加 | 个人版默认免费试用；供应商/API Key 按平台填 |

## 二、日常操作快捷键（按功能合并）

| 分类 | 操作 | 快捷键 / 命令 | 说明 |
|---|---|---|---|
| 通用面板 | 打开/关闭 AI 聊天面板 | `Ctrl+L` | ⭐ 最常用 |
| 通用面板 | 打开通用设置 | `Ctrl+,` | IDE 基础设置 |
| 通用面板 | 打开 Qoder 专属设置 | `Ctrl+Shift+,` | 模型、默认语言（设中文）等 |
| 通用面板 | 打开命令面板 | `Ctrl+Shift+P` | 搜所有命令，查真实键位 |
| 通用面板 | 打开 Quest 面板（长任务） | `Ctrl+E` | 自主编程模式 |
| 通用面板 | 打开会话面板（第三方说法） | `Ctrl+Shift+Q` | ⚠️ 与官方 `Ctrl+L` 冲突，以你 IDE 内 Keymap 为准 |
| 聊天面板 | 发送消息 | `Enter` | |
| 聊天面板 | 输入框换行 | `Shift+Enter` | |
| 聊天面板 | 接受所有建议改动 | `Ctrl+Enter` | |
| 聊天面板 | 拒绝所有建议改动 | `Ctrl+Backspace` | |
| 聊天面板 | 复制上一条回复 | `Ctrl+Shift+C` | 第三方资料，以 Keymap 为准 |
| 聊天面板 | 重新生成上一条 | `Ctrl+R` | 第三方资料，以 Keymap 为准 |
| 行间会话 | 打开光标处会话（Inline Chat） | `Ctrl+I` | ⭐ 不离开光标直接问 |
| 行间会话 | 选中代码发到主聊天 | `Ctrl+L` | |
| 行间会话 | 输入框调用快捷命令 | `/` | |
| 行间会话 | 把文件/符号加为上下文 | `#` | 例 `#UserService` |
| 代码补全 | 触发"下一步"智能编辑建议 | `Alt+P` | |
| 代码补全 | 接受当前建议 | `Tab` | |
| 代码补全 | 接受多行建议 | `Ctrl+Tab` | |
| 代码补全 | 拒绝建议 | `Esc` | |
| Diff 视图 | 接受单个更改 | `Ctrl+Shift+Enter` | |
| Diff 视图 | 拒绝单个更改 | `Ctrl+Shift+Backspace` | |
| Diff 视图 | 接受文件内全部更改 | `Ctrl+Enter` | |
| Diff 视图 | 拒绝文件内全部更改 | `Ctrl+Backspace` | |
| Diff 视图 | 跳到下一个文件 | `Ctrl+Shift+[` | |
| Diff 视图 | 跳到上一个文件 | `Ctrl+Shift+]` | |
| Diff 视图 | 跳到下一个更改 | `Alt+J` | |
| Diff 视图 | 跳到上一个更改 | `Alt+K` | |
| 文件导航 | 快速打开文件 | `Ctrl+P` | |
| 文件导航 | 符号搜索（函数/类） | `Ctrl+Shift+O` | |
| 文件导航 | 全局搜索 | `Ctrl+Shift+F` | |
| Quest 模式 | 交互模式触发任务 | `/quest` 后描述任务 | 第三方资料；生成 Spec → 确认 → 自主执行 |
| Quest 模式 | 后台并发任务 | `qodercli --worktree "任务描述"` | CLI，多任务并行 |

## 三、CLI 常用命令

| 分类 | 用途 | 命令 | 说明 |
|---|---|---|---|
| 验证 | 查版本 | `qodercli --version` | 安装成功标志 |
| 交互 | 进聊天模式 | `qodercli` | 自然语言对话，按 `Enter` 发送，`/help` 看斜杠命令 |
| 一次性 | 非交互执行 | `qodercli -p "你的指令"` | 脚本/自动化用 |
| 续会话 | 继续上次 | `qodercli -c -p "继续"` | |
| 模型 | 指定模型 | `qodercli --model=ultimate -p "重构模块"` | `auto/efficient/lite/performance/ultimate` 等 |
| 权限 | 跳过确认 | `qodercli --yolo -p "改动"` | ⚠️ 慎用 |
| MCP | 加外部工具 | `qodercli mcp add <名> -- npx -y <包>` | 例 Context7/Playwright |

## 四、三个小白提醒 / 避坑

| 点 | 说明 |
|---|---|
| 键位冲突 | 博客写的 `Ctrl+Shift+Q` 开面板与官方 `Ctrl+L` 不一致；记不准就 `Ctrl+Shift+P` 搜 "Qoder" 或去 `Ctrl+,` → Keymap 查真实绑定 |
| 首次索引 | 打开大项目后它会建索引/知识库，等几秒再问，回答更准 |
| 改动流程 | 重要改动先在 WorkBuddy 里对齐方案，Qoder 负责执行细节（你的一贯流程） |
