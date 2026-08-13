# 优勤智服 · AI客服利润引擎

客服工作台 + 客户端 + 利润驾驶舱 + 飞书多维表格对接的演示项目。

内置账号登录、AI 智能问答、物流轨迹追踪、数据驾驶舱、客户端咨询、营收贡献测算与飞书多维表格同步，覆盖客服全流程。

## 技术栈

- 后端：Python 3.10+ / FastAPI / SQLAlchemy / SQLite
- 前端：Node.js 18+ / Vue 3 / Vite / Element Plus / ECharts
- AI：DeepSeek API（意图识别、情绪分析、自动回答、话术推荐）
- 知识库：自建 RAG（字符级分词 + 关键词加权检索）
- 物流：模拟物流 API（轨迹查询、催件、状态推进）
- 认证：用户名/密码注册登录（pbkdf2_hmac 加密）
- 飞书：多维表格读写（用户、商品、会话、订单、客服动作、结果事件、聊天消息、KPI 共8张表）
- 营收测算：基于《客户价值视角的电商客服营收贡献测算模型》的基准差额法

## 目录结构

```
cs_dome/
├── backend/                    # 后端
│   ├── app/
│   │   ├── main.py             # 入口（启动时自动创建测试账号 admin/password）
│   │   ├── database.py         # 数据库连接
│   │   ├── models.py           # 表结构（Session/Message/Order/LogisticsTrack/Reply/User 等）
│   │   ├── routers/            # API 路由
│   │   │   ├── auth.py         # 注册/登录/用户名检查
│   │   │   ├── sessions.py     # 会话/消息管理
│   │   │   ├── ai.py           # AI 分析、模拟客户、生成话术
│   │   │   ├── logistics.py    # 物流轨迹查询、催件、状态推进
│   │   │   ├── cockpit.py      # 利润驾驶舱数据
│   │   │   ├── platforms.py    # 平台订单/商品数据
│   │   │   ├── customer.py     # 客户端接口（售前/售后咨询、下单/已解决）
│   │   │   └── feishu.py       # 飞书多维表格对接
│   │   └── services/
│   │       ├── deepseek_service.py  # DeepSeek + 提示词工程
│   │       ├── knowledge_base.py    # RAG 知识库
│   │       ├── logistics_service.py # 物流状态机与轨迹生成
│   │       └── revenue_service.py   # 营收贡献测算（基准差额法）
│   ├── .env.example            # 环境变量模板
│   ├── init_db.py              # 初始化数据库（8个示例会话）
│   ├── requirements.txt        # Python 依赖
│   └── youqin_cs.db            # SQLite 数据库（首次运行自动生成）
├── frontend/                   # 前端
│   ├── src/
│   │   ├── views/
│   │   │   ├── Login.vue       # 登录/注册页
│   │   │   ├── Workbench.vue   # 客服工作台
│   │   │   ├── Cockpit.vue     # 利润驾驶舱
│   │   │   └── Server.vue      # 客户端（免登录）
│   │   ├── stores/             # Pinia 状态管理（含会话缓存）
│   │   ├── router/             # 路由守卫（未登录跳登录页）
│   │   └── api/                # 后端接口封装
│   ├── _redirects              # Cloudflare Pages SPA 路由回退
│   ├── _headers                # Cloudflare Pages 安全头
│   └── package.json
├── railway.json                # Railway 后端部署配置
├── nixpacks.toml               # Nixpacks 构建配置
└── .github/workflows/          # GitHub Actions 自动部署
```

## 环境准备

### 1. 安装 Python

需要 Python 3.10 或以上版本：https://www.python.org/downloads/

安装时勾选「Add Python to PATH」。

验证：
```bash
python --version
```

### 2. 安装 Node.js

需要 Node.js 18 或以上版本：https://nodejs.org/

验证：
```bash
node --version
npm --version
```

## 安装依赖

### 后端依赖

```bash
cd cs_dome/backend
pip install -r requirements.txt
```

依赖清单（requirements.txt）：
- fastapi（Web 框架）
- uvicorn（ASGI 服务器）
- sqlalchemy（ORM）
- pydantic（数据校验）
- openai（调用 DeepSeek，兼容 OpenAI SDK）
- requests（调用飞书 API）
- python-dotenv（读取 .env）
- httpx、python-multipart

### 前端依赖

```bash
cd cs_dome/frontend
npm install
```

依赖清单（package.json）：
- vue / vue-router / pinia
- element-plus / @element-plus/icons-vue
- echarts
- axios
- vite / typescript

## 配置环境变量

```bash
cd cs_dome/backend
copy .env.example .env
```

用文本编辑器打开 `.env`，填入：

```
# DeepSeek API Key（必填，AI 功能依赖此项）
DEEPSEEK_API_KEY=sk-你的key

# 飞书多维表格对接（选填，不填则为 Mock 模式）
FEISHU_APP_ID=cli_xxxxxxxx
FEISHU_APP_SECRET=xxxxxxxx
FEISHU_APP_TOKEN=
```

> 说明：不配置飞书凭证也能运行项目，驾驶舱的「同步到飞书」会以 Mock 模式运行。
> 配置后会真实创建飞书多维表格并同步数据。

## 初始化数据库

首次运行需初始化 SQLite 数据库（生成 youqin_cs.db，写入 8 个示例会话）：

```bash
cd cs_dome/backend
python init_db.py
```

看到 `数据库初始化完成！` 即成功。

## 启动项目

需要**同时**启动后端和前端（开两个终端）。

### 终端1：启动后端

```bash
cd cs_dome/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

看到以下输出即成功：
```
Uvicorn running on http://0.0.0.0:8000
```

### 终端2：启动前端

```bash
cd cs_dome/frontend
npm run dev
```

看到以下输出即成功：
```
Local: http://localhost:5174/
```

### 访问应用

浏览器打开：http://localhost:5174/

首次访问会跳转到登录页，使用测试账号登录：

```
账号：admin
密码：password
```

也可在登录页点击「注册账号」创建新账号（用户名≥2字符，密码≥4字符）。登录后 token 存储在 `localStorage`，关闭浏览器后仍保持登录态；点击右上角「退出」可注销。

### 访问客户端（免登录）

客户端页面无需登录，直接访问：

```
http://localhost:5174/server
```

客户端页面包含三个入口：
- **售前咨询**：选购商品 / 参数咨询 / 推荐指南
- **售后服务**：订单问题 / 退换货 / 物流查询
- **历史会话**：查看历史咨询记录（需先输入称呼并选择平台）

客户端发送的消息会实时同步到工作台，工作台会显示 AI 思考动画并生成推荐回复。

## 功能说明

### 客服工作台

- **会话列表**：示例客户会话，支持搜索和 Tab 切换（全部/AI接待/待接手）
- **初始化按钮**：左侧搜索栏旁的红色「初始化」按钮，一键清空所有客户会话和消息数据，恢复初始状态
- **模拟客户消息**：点击「模拟客户消息」按钮，随机生成客户消息（约 50% 可 AI 自动回答，50% 需人工）
- **自动模拟**：点击「自动模拟」进入每 8 秒自动生成一条客户消息的循环，再次点击停止；切换会话时自动停止模拟
- **客户端消息同步**：客户端发来的消息会实时出现在工作台，并触发 AI 思考动画（与模拟客户消息一致）
- **AI 思考动画**：客户消息发出后，右侧面板显示 AI 思考过程（三点跳动 + RAG 检索分步激活：120ms检索知识库 → 450ms意图识别&情绪分析 → 820ms生成推荐话术 + 滑动进度条）
- **AI 自动回答**：可自动回答的场景（产品咨询、物流、优惠等）会自动生成回答并标注「AI回答」+ 置信度标签
- **AI 置信度独立化**：每条 AI 回答气泡显示**自己生成时刻**的置信度快照（后端数据库存储），互不影响；历史无快照的 AI 消息不显示置信度，避免被实时值误导。右侧面板顶部「AI 置信度」仍实时反映当前会话状态
- **催促/投诉强制人工**：含负面情绪（愤怒/激动/不满/焦虑）、高风险/中风险、或催促投诉关键词（负责人/效率/等了/等很久/等半天/不回复/没人/人呢/在吗/客服在吗/急/着急/催/怎么还不/退钱/赔偿/曝光/差评/投诉/举报/太慢/太差/失望/骗子/忽悠等）的消息，强制标记为「需人工处理」，AI 不自动回答，会话自动移到「待接手」tab
- **AI 推荐话术**：右侧面板生成 3 条推荐话术，带依次淡入动画（0.1s间隔），点击「查看更多话术」可重新生成
- **AI 智能分析**（右侧面板顶部，支持点击切换）：
  - **用户意图**：10 个意图标签可点击切换（产品咨询/物流查询/退换咨询/优惠咨询/安装指导/商品推荐/售后投诉/退款咨询/投诉升级/一般咨询）
  - **情绪状态**：7 个带 emoji 的情绪标签可点击切换（😊平稳 / 😄积极 / 😕略有不满 / 😟略有焦虑 / 😞不满 / 😡愤怒 / 😤激动）
  - **会话价值评分**：进度条 + 分数 + 等级文字（常规/中等/高/极高价值），≥70 分显示「建议转人工」
  - **AI 置信度**：基于风险/情绪/意图推算（基础分92，知识库覆盖充分的意图+5，高风险/负面情绪扣分），进度条颜色按分段变化（高/中/低/无信心），<80 分显示「建议转人工」
  - **推荐处理路径**：6 个路径标签可点击切换（AI自动回复/售后挽回/转人工客服/转售后专员/创建工单/升级主管），根据会话风险和情绪自动推荐
- **快捷操作栏**：7 个快捷按钮（查询中 / 推荐商品 / 退换说明 / 物流更新 / 商品卡片 / 发优惠券 / 快捷话术）
- **物流轨迹追踪**：右侧面板展示该会话所有订单的物流信息（承运商、物流单号、状态、时间线轨迹），支持一键催件
- **关联订单**：展示该客户最近订单及状态（含物流状态、快递单号、承运商）
- **创建工单**：底部操作栏紫色「创建工单」按钮，弹窗填写工单标题/类型/优先级/处理人/关联订单/问题描述，自动填充会话信息
- **底部操作**：创建工单 / 标记风险并升级 / 结束会话并归档（归档后自动停止消息轮询）
- **清空记录**：清空当前会话的所有消息和 AI 分析数据（同时清空 AI 回复内容和推荐话术）
- **流畅切换**：切换客户会话时采用缓存 + 预取机制，聊天记录和 AI 推荐话术持久化，秒出切换；切换时自动重置 AI 思考状态，避免动画错乱

### 利润驾驶舱

- **KPI 指标**：4 项核心指标卡片
  - 💰 客服总营收贡献：基于基准差额法汇总（售前转化 + 退款挽回）
  - 🤖 AI贡献值：AI 自助接待的会话贡献总额及占比
  - 😊 客户满意度：基于会话状态计算的满意率
  - ⚡ AI响应效率：AI 自动回答比例
- **趋势图表**：近7日会话量柱状图 + AI解决率折线图（双轴综合）
- **AI 与人工价值互补结构**：环形饼图，展示 AI 转化 / AI 挽回 / 人工转化 / 人工挽回四维价值拆解，带金额和百分比标签
- **用户意图分布**：Top 5 问题分类条形展示
- **售前转化价值**：售前会话成交转化贡献总额、贡献会话数、均会话贡献、Top 5 转化会话明细
- **会话时段分布**：基于真实会话创建时间统计 0-23 点全时段分布直方图
- **归因明细表**：客服动作归因（AI归因/人工归因），含置信度、增量价值、A/B 对照标记
- **自动刷新**：每 30 秒自动刷新数据并更新时间戳；切换时间周期（30天/7天/今天/618）立即刷新
- **同步到飞书**：一键将数据同步到飞书多维表格（8张表并行同步）

### 客户端（免登录）

访问 `http://localhost:5174/server`，无需登录即可使用：

- **售前咨询**：输入称呼、选择平台（淘宝/拼多多/京东等）、选择商品后开始咨询
- **售后服务**：输入称呼、选择平台、选择订单后开始咨询
- **历史会话**：点击进入独立的历史会话列表页，查看历史咨询记录（需先填写称呼和平台）
- **关联提问**：聊天页输入框上方提供 6 条关联提问复选框（售前/售后各6条），勾选后自动填入输入框
- **AI 思考动画**：发送消息后显示三点跳动思考动画，随后显示 AI 回复
- **AI 回复置信度**：客户端触发的 AI 自动回答同样带置信度标签（与工作台逻辑一致，后端存储快照）
- **乐观更新**：发送消息后立即本地显示气泡，后端响应后替换为真实消息，避免卡顿感
- **售前/售后高亮**：选中售前或售后选项卡时显示蓝色高亮边框
- **🛒 下单按钮**（售前）：点击「我下单了」标记成交，计算客服转化贡献 Vconv，显示系统消息
- **✅ 已解决按钮**（售后）：点击「问题已解决」标记挽回，计算退款挽回贡献 Vretain，显示系统消息

### 营收贡献测算模型

基于《客户价值视角的电商客服营收贡献测算模型》PDF 的基准差额法实现：

| 价值类型 | 公式 | 触发条件 | 说明 |
|---------|------|---------|------|
| 售前转化 Vconv | (1 - p) × GMV | 客户点击「下单」 | p=基准成交概率（意图/情绪/客群加权） |
| 退款挽回 Vretain | (q - r) × GMV | 售后客户点击「已解决」 | q=基准退款概率，r=实际退款比例 |
| 复购增量 Vrep | 0 | 预留 | 需 90 天消费跟踪 |
| VOC 信息价值 Vvoc | 0 | 预留 | 需工单确认流程 |

核心测算模块：[app/services/revenue_service.py](backend/app/services/revenue_service.py)，供客户下单接口和驾驶舱 KPI 共用。

### 飞书多维表格对接

配置好飞书凭证后，在「利润驾驶舱」点击「同步到飞书」，或直接访问浏览器接口：

#### 1. 重建表结构（首次使用或字段变更时）

```
浏览器访问：http://localhost:8000/api/feishu/bitable/rebuild-browser
```

自动执行：
- 把所有旧表改名为「待删除_xxx」（绕过飞书至少保留1张表限制）
- 按新字段定义创建 8 张数据表
- 删除改名后的旧表

8 张数据表及关键字段：

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| 用户表 | 客户信息 | 用户ID、平台、会员等级、购买偏好、风险标签、累计消费 |
| 商品表 | 商品信息 | **商品名称**、SKU、库存、规格、尺寸、材质、适用场景 |
| 会话表 | 会话记录 | **会话ID**、用户ID、问题文本（所有客户消息汇总）、会话预览、处理路径、价值评分、意图、情绪 |
| 订单表 | 订单信息 | 订单ID、用户ID、**会话ID**、**商品名称**、SKU、订单金额、状态、物流、退款状态 |
| 客服动作表 | 客服处理 | **会话ID**、用户ID、AI回复、转人工原因、人工处理结果、优惠动作 |
| 结果事件表 | 业务事件 | 用户ID、**会话ID**、事件类型、事件时间 |
| 聊天消息表 | 消息明细 | 消息ID、会话ID、用户ID、消息方向（客户/AI/客服）、消息内容、消息类型、发送时间 |
| KPI驾驶舱指标表 | KPI快照 | 指标名称、指标数值、单位、趋势说明、详细描述、进度、同步时间 |

> 各表通过「会话ID」和「用户ID」关联，可在飞书多维表格中建立关联字段。

#### 2. 同步全部数据

```
浏览器访问：http://localhost:8000/api/feishu/bitable/sync-all-browser
```

同步前自动清空各表旧数据，再写入当前工作台的最新数据。同步完成后返回各表写入条数和失败表列表。

#### 3. 单独同步某张表

| 接口 | 说明 |
|------|------|
| `POST /api/feishu/bitable/sync-users` | 同步用户表 |
| `POST /api/feishu/bitable/sync-products` | 同步商品表 |
| `POST /api/feishu/bitable/sync-sessions` | 同步会话表（问题文本=该会话所有客户消息汇总） |
| `POST /api/feishu/bitable/sync-orders` | 同步订单表 |
| `POST /api/feishu/bitable/sync-actions` | 同步客服动作表 |
| `POST /api/feishu/bitable/sync-events` | 同步结果事件表 |
| `POST /api/feishu/bitable/sync-messages` | 同步聊天消息表（每条消息一条记录） |
| `POST /api/feishu/bitable/sync-kpis` | 同步KPI驾驶舱指标表（6项指标快照） |

#### 4. 删除所有数据表

```
浏览器访问：http://localhost:8000/api/feishu/bitable/delete-tables-browser
```

删除飞书多维表格中的所有数据表（慎用）。

## 部署指南

### 后端部署到 Railway

1. 在 [Railway](https://railway.com/) 创建新项目，选择「Deploy from GitHub repo」
2. 连接此 GitHub 仓库，Railway 会自动检测 `railway.json` 构建
3. 在 Railway 项目设置中添加环境变量：
   - `DEEPSEEK_API_KEY` - DeepSeek API Key（必填）
   - `FEISHU_APP_ID` / `FEISHU_APP_SECRET` - 飞书凭证（选填）
4. Railway 自动生成域名如 `https://xxx.up.railway.app`
5. 后端 API 地址为 `https://xxx.up.railway.app/api`

### 前端部署到 Cloudflare Pages

#### 方式一：GitHub Actions 自动部署（推荐）

1. 在 [Cloudflare 控制台](https://dash.cloudflare.com/) 获取 API Token 和 Account ID
2. 在 GitHub 仓库 Settings → Secrets 添加：
   - `CLOUDFLARE_API_TOKEN` - Cloudflare API Token
   - `CLOUDFLARE_ACCOUNT_ID` - Cloudflare Account ID
3. 在 Cloudflare Pages 创建项目 `youqin-cs`
4. 推送代码到 master 分支，GitHub Actions 自动构建并部署

#### 方式二：Cloudflare Pages 直连 GitHub

1. 登录 [Cloudflare Pages](https://pages.cloudflare.com/)，点击「Create a project」
2. 连接 GitHub 仓库，选择此仓库
3. 构建设置：
   - **Build command**: `cd frontend && npm ci && npm run build`
   - **Build output directory**: `/frontend/dist`
   - **Environment variable**: `VITE_API_BASE` = Railway 后端 URL（如 `https://xxx.up.railway.app/api`）
4. 点击「Save and Deploy」

项目已内置 `frontend/_redirects`（SPA 路由回退）和 `frontend/_headers`（安全头），Cloudflare Pages 自动识别。

## 常见问题

### Q: 后端报错 `ModuleNotFoundError`

依赖没装全，重新执行：
```bash
cd cs_dome/backend
pip install -r requirements.txt
```

### Q: 前端报错 `vite: command not found`

依赖没装全，重新执行：
```bash
cd cs_dome/frontend
npm install
```

### Q: 端口被占用

```bash
# 查看占用 8000 端口的进程
# Windows
netstat -ano | findstr :8000
taskkill /PID 进程ID /F

# Mac/Linux
lsof -i:8000
kill -9 进程ID
```

前端默认端口 5174，后端默认端口 8000。

### Q: AI 功能不工作

检查 `.env` 中的 `DEEPSEEK_API_KEY` 是否正确配置。

### Q: 飞书同步失败 / 数据表删不掉 / 死数据残留

1. 先访问 `http://localhost:8000/api/feishu/bitable/rebuild-browser` 重建表结构（删除旧表+创建8张新表）
2. 再访问 `http://localhost:8000/api/feishu/bitable/sync-all-browser` 同步数据
3. 确认飞书应用已开通 `bitable:app` 和 `bitable:app:create` 权限
4. 确认应用已发布到企业
5. 查看 `.env` 中的 App ID / App Secret 是否正确

> rebuild 采用「先改名后删」策略：先把旧表改名为「待删除_xxx」，创建新表后再删除改名表，绕过飞书「至少保留1张表」限制。

### Q: 飞书同步后部分表没数据

1. 检查 `sync-all` 返回的 `failed_tables` 字段，确认哪张表同步失败
2. 常见原因：表字段不匹配。访问 `rebuild-browser` 重建表结构即可
3. 单独同步某张表排查：如 `POST /api/feishu/bitable/sync-messages`

### Q: 客户端发消息工作台没反应

1. 确认后端已启动（`http://localhost:8000`）
2. 确认客户端页面 `http://localhost:5174/server` 已填写称呼、选择平台并开始咨询
3. 工作台需选中对应客户会话才能看到消息（客户端首次发消息会自动创建会话）

### Q: 数据库丢失或想重置

删除 `backend/youqin_cs.db` 后重新运行 `init_db.py`。

### Q: 忘记登录密码

测试账号 `admin / password` 在后端启动时会自动创建（若不存在）。如需重置，删除 `youqin_cs.db` 后重启后端即可重新生成；或在登录页注册一个新账号。

### Q: 物流轨迹不显示

物流数据由模拟物流 API 生成。确认该会话关联的订单已分配物流单号（`init_db.py` 会自动生成）。若某会话无订单，右侧面板不会显示物流区块，属正常现象。

### Q: 切换会话卡顿

项目已内置会话缓存与预取机制（首次加载后 60 秒内切换免请求）。如仍卡顿，检查后端响应速度，或清理浏览器缓存后刷新。

### Q: 驾驶舱暂无数据

驾驶舱数据基于真实会话和消息实时计算。前往客服工作台或客户端发起会话后，驾驶舱会自动展示数据。营收贡献值需在客户端点击「下单」或「已解决」按钮后才会产生。

## 停止服务

在对应终端按 `Ctrl + C` 即可。

### 技术交流

qq：2964560472
