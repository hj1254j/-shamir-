# 基于 Shamir 门限的可追踪秘密共享系统

这是一个面向初学者的教学演示项目，核心路线是：

`Shamir 门限秘密共享 + Hash(x) + 完美黑盒追踪`

项目目标不是逐行复刻 CRYPTO 2024 的 NITS 原方案，而是把最值得学习的主线先讲清楚、跑通并看见日志。

## 一、项目定位与论文关系

这个项目保留了论文思路里最适合教学演示的部分：

- 用 Shamir 门限秘密共享生成份额。
- 对每个参与者的横坐标 `x` 计算 `Hash(x)` 作为追踪标签。
- 当黑盒泄露某个 `y` 时，先用参考份额恢复多项式 `q(x)`。
- 再对 `q(x) = y` 求根，找回真正的 `x`。
- 最后用 `Hash(x)` 与追踪密钥、验证密钥比对，判断是谁泄露了份额。

为了让项目更适合课堂展示和上手调试，这里做了几处刻意简化：

- 不实现论文中的完整安全性细节和复杂机制。
- 默认黑盒是“完美黑盒”，只泄露真实的 `y`，不作恶，不返回错误值。
- 不接数据库、不做登录、不做权限系统、不做持久化存储。
- 后端为了更友好地提示“份额数量不足”，会在内存中暂存当前进程生成过的分发记录；服务重启后这些记录会清空。

这份教学版里最重要的一句数学话是：

```text
分发时给每个人一个 (x, y = q(x))；
追踪时拿到泄露的 y，先恢复 q，再解 q(x) = y，找回 x；
最后检查 Hash(x) 是否命中追踪密钥和验证密钥。
```

## 二、目录讲解

项目固定放在：

```text
D:\project\Solution1\可追踪秘密共享
```

目录结构固定为：

```text
可追踪秘密共享/
├─ README.md
├─ backend/
│  ├─ main.py
│  └─ requirements.txt
└─ frontend/
   ├─ package.json
   ├─ vite.config.js
   ├─ index.html
   └─ src/
      ├─ main.js
      ├─ App.vue
      ├─ router/
      │  └─ index.js
      ├─ api/
      │  └─ http.js
      ├─ styles/
      │  └─ global.css
      └─ views/
         ├─ ShareView.vue
         ├─ ReconstructView.vue
         ├─ TraceView.vue
         └─ VerifyView.vue
```

每个位置负责什么：

- `README.md`
  这是整份项目的教学讲义，先讲目录，再讲运行环境，再讲后端和前端。

- `backend/`
  这是 Python 后端，负责有限域计算、Shamir 多项式、插值、追踪、验证和日志输出。

- `backend/main.py`
  这是后端核心文件。FastAPI 应用、请求响应模型、有限域辅助函数、4 个接口都在这里。

- `backend/requirements.txt`
  这是后端依赖列表，告诉 Python 需要安装哪些库。

- `frontend/`
  这是 Vue 前端，负责中文界面、路由导航、表单输入、结果展示和浏览器日志。

- `frontend/package.json`
  这是前端依赖和脚本入口。

- `frontend/vite.config.js`
  这是 Vite 配置，负责开发服务器端口和 `/api` 代理。

- `frontend/index.html`
  这是页面最外层的 HTML 外壳。

- `frontend/src/main.js`
  这是 Vue 应用启动入口。

- `frontend/src/App.vue`
  这是前端整体布局，包含左侧导航和右侧内容区。

- `frontend/src/router/index.js`
  这是前端路由，负责四个页面之间的切换。

- `frontend/src/api/http.js`
  这是 Axios 请求层，负责统一发请求并打印中文日志。

- `frontend/src/styles/global.css`
  这是全局样式文件，负责整体视觉风格和响应式布局。

- `frontend/src/views/*.vue`
  这是四个功能页面：
  - `ShareView.vue`：秘密分发
  - `ReconstructView.vue`：秘密重构
  - `TraceView.vue`：叛徒追踪
  - `VerifyView.vue`：防诬陷验证

## 三、Windows 环境安装与运行指南

这份项目默认采用下面这套开发环境：

- Python：官方标准版 `Python 3.11 x64`
- Node.js：官方 `Node.js v24 LTS Windows x64`
- 编辑器：VS Code
- 推荐扩展：`Python`、`Pylance`、`Vue - Official`、`ESLint`

### 1. 验证本机命令

先在 PowerShell 里验证以下命令都可用：

```powershell
python --version
python -m pip --version
node --version
npm --version
```

这四条命令都能输出版本号，说明基础命令环境已经准备好。

### 2. 安装 VS Code 常用扩展

如果已经安装了 VS Code，并且命令行里能使用 `code.cmd`，可以执行：

```powershell
code.cmd --install-extension ms-python.python --force
code.cmd --install-extension ms-python.vscode-pylance --force
code.cmd --install-extension Vue.volar --force
code.cmd --install-extension dbaeumer.vscode-eslint --force
```

### 3. 创建后端虚拟环境并启动后端

进入后端目录：

```powershell
cd D:\project\Solution1\可追踪秘密共享\backend
```

创建虚拟环境：

```powershell
python -m venv .venv
```

安装依赖：

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

启动后端：

```powershell
.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

看到类似下面的提示，就说明后端已经启动成功：

```text
Uvicorn running on http://127.0.0.1:8000
```

### 4. 安装前端依赖并启动前端

打开新的 PowerShell，进入前端目录：

```powershell
cd D:\project\Solution1\可追踪秘密共享\frontend
```

安装依赖：

```powershell
npm install
```

启动前端：

```powershell
npm run dev
```

看到类似下面的提示，就说明前端已经启动成功：

```text
Local: http://127.0.0.1:5173/
```

然后用浏览器打开 `http://127.0.0.1:5173/` 即可。

### 5. 一键启动脚本

如果你不想每次都手动开两个终端，可以直接在项目根目录执行：

```powershell
cd D:\project\Solution1\可追踪秘密共享
powershell -ExecutionPolicy Bypass -File .\start-project.ps1
```

这个脚本会自动完成下面几件事：

- 检查 `python`、`node`、`npm` 是否可用
- 如果后端 `.venv` 不存在，就自动创建
- 如果后端依赖缺失，就自动安装 `requirements.txt`
- 如果前端 `node_modules` 不存在，就自动执行 `npm install`
- 自动拉起后端窗口和前端窗口
- 等待 `8000` 和 `5173` 端口就绪后打印访问地址

如果你怀疑本地已经有旧进程占着 `8000` 或 `5173`，可以改用：

```powershell
powershell -ExecutionPolicy Bypass -File .\start-project.ps1 -ForceRestart
```

这个参数会先清理占用 `8000` 和 `5173` 的旧进程，再重新启动前后端。

## 四、后端文件与接口讲解

### 1. `backend/requirements.txt`

后端依赖非常少，只有教学演示必须用到的几项：

- `fastapi`
  提供 Web API 框架。

- `uvicorn`
  用来启动 FastAPI 应用。

- `galois`
  用来做素数域 `GF(p)` 里的有限域运算。

- `pydantic`
  用来定义请求和响应模型。

### 2. `backend/main.py`

这个文件遵循“单文件、易读、重日志”的教学风格，大体分成下面几块：

- 常量和有限域初始化
  固定素数域 `GF(2305843009213693951)`。

- 请求与响应模型
  用 Pydantic 明确每个接口收什么、回什么。

- 有限域辅助函数
  包括字符串转整数、整数转域元素、`Hash(x)` 计算、随机多项式生成、求值和插值。

- 追踪辅助函数
  包括把 `q(x) - y` 转成多项式、在有限域里求根、用哈希匹配候选横坐标。

- 四个正式接口
  - `POST /api/share`
  - `POST /api/rec`
  - `POST /api/trace`
  - `POST /api/verify`

### 3. 有限域与哈希规则

- 有限域固定为：

```text
GF(2305843009213693951)
```

- 秘密输入固定为十进制整数，必须满足：

```text
0 <= secret < p
```

- 哈希规则固定为：

```python
SHA-256(str(x).encode("utf-8")).hexdigest()
```

### 4. 为什么接口里的大整数用字符串

后端内部仍然会把 `galois` 域元素显式转成普通 `int`，但进入 JSON 响应前又会转成十进制字符串。

这样做有两个原因：

- 避免 `galois` 域对象无法直接序列化成 JSON。
- 避免浏览器把大整数当成 `Number` 后发生精度丢失。

换句话说：

- `participant_id`、`share_count`、`threshold` 这些小整数仍然用 JSON 数字。
- `secret`、`x`、`y`、`proof_x`、`leaked_y` 这些有限域大整数统一用十进制字符串。

### 5. 四个 API 的固定形状

#### `POST /api/share`

请求：

```json
{
  "secret": "1234",
  "share_count": 5,
  "threshold": 3
}
```

响应：

```json
{
  "field_prime": "2305843009213693951",
  "secret": "1234",
  "share_count": 5,
  "threshold": 3,
  "shares": [
    {
      "participant_id": 1,
      "x": "123456",
      "y": "789012",
      "trace_hash": "..."
    }
  ],
  "trace_key": [
    {
      "participant_id": 1,
      "trace_hash": "..."
    }
  ],
  "verify_key": {
    "hash_algorithm": "sha256",
    "participants": [
      {
        "participant_id": 1,
        "trace_hash": "..."
      }
    ]
  }
}
```

#### `POST /api/rec`

请求：

```json
{
  "shares": [
    {
      "participant_id": 1,
      "x": "123456",
      "y": "789012"
    }
  ]
}
```

响应：

```json
{
  "recovered_secret": "1234"
}
```

#### `POST /api/trace`

请求：

```json
{
  "reference_shares": [
    {
      "participant_id": 1,
      "x": "123456",
      "y": "789012"
    }
  ],
  "leaked_outputs": [
    {
      "leaked_y": "789012"
    }
  ],
  "trace_key": [
    {
      "participant_id": 1,
      "trace_hash": "..."
    }
  ]
}
```

处理步骤固定为：

1. 用 `reference_shares` 插值恢复 `q(x)`。
2. 对每个 `leaked_y` 构造 `q(x) - leaked_y`。
3. 在有限域里求 `q(x) = leaked_y` 的候选根。
4. 把候选 `x` 逐个做哈希，与 `trace_key` 比对。

响应：

```json
{
  "trace_result": "success",
  "traitor_id": 1,
  "evidence": [
    {
      "leaked_y": "789012",
      "candidate_x_values": ["123456"],
      "matched_participant_ids": [1],
      "proof_x": "123456"
    }
  ]
}
```

如果某个 `leaked_y` 对应多个候选参与者，就返回 `ambiguous`，不做最终指控。

#### `POST /api/verify`

请求：

```json
{
  "verify_key": {
    "hash_algorithm": "sha256",
    "participants": [
      {
        "participant_id": 1,
        "trace_hash": "..."
      }
    ]
  },
  "suspect_participant_id": 1,
  "proof_x": "123456"
}
```

响应：

```json
{
  "verified": true,
  "expected_hash": "...",
  "provided_hash": "...",
  "message": "验证通过：这份证据和嫌疑人的验证密钥一致。"
}
```

### 6. 后端阅读顺序建议

第一次阅读 `backend/main.py` 时，建议按这个顺序：

1. `FIELD_PRIME` 和 `FIELD`
2. `parse_big_integer()`、`to_field_element()`、`hash_x_value()`
3. `build_random_polynomial()` 和 `evaluate_polynomial()`
4. `interpolate_polynomial()`
5. `find_candidate_x_values()` 和 `match_roots_with_trace_key()`
6. 四个正式 API

## 五、前端文件与页面讲解

前端固定采用：

- Vue 3
- Vite
- Element Plus
- Axios
- Vue Router

### 1. `frontend/package.json`

这个文件负责管理前端依赖，并提供：

- `npm run dev`
- `npm run build`
- `npm run preview`

### 2. `frontend/vite.config.js`

这个文件负责：

- 挂载 Vue 插件
- 固定开发端口为 `5173`
- 把 `/api` 请求代理到 `http://127.0.0.1:8000`

### 3. `frontend/index.html`

这个文件是最外层 HTML 壳子，真正的 Vue 应用会挂载到这里面的 `#app` 节点。

### 4. `frontend/src/main.js`

这个文件负责：

- 创建 Vue 应用
- 挂载 Vue Router
- 挂载 Element Plus
- 引入 Element Plus 默认样式和全局自定义样式

### 5. `frontend/src/App.vue`

这个文件负责整体布局：

- 左侧导航栏
- 顶部说明卡片
- 右侧页面内容区域

整个前端只有一个壳子，四个功能页都在这个壳子里切换。

### 6. `frontend/src/router/index.js`

这个文件定义四个页面的路由：

- `/share`
- `/reconstruct`
- `/trace`
- `/verify`

### 7. `frontend/src/api/http.js`

这个文件封装 Axios 请求层：

- 请求发出前打印中文日志
- 响应成功后打印中文日志
- 响应失败后提取中文错误信息

### 8. 四个页面各做什么

- `ShareView.vue`
  输入秘密、份额数量、门限；调用 `/api/share`；用表格展示份额、追踪密钥、验证密钥。

- `ReconstructView.vue`
  支持动态增删份额输入行；调用 `/api/rec`；显示恢复出的秘密。

- `TraceView.vue`
  把界面拆成“参考份额输入区”和“泄露输出输入区”；调用 `/api/trace`；醒目显示叛徒 ID 与 `proof_x`。

- `VerifyView.vue`
  输入验证密钥、嫌疑人 ID 和 `proof_x`；调用 `/api/verify`；用绿色和红色状态块显示结论。

## 六、建议的学习和验收顺序

第一次跑通项目时，建议按下面的节奏观察：

1. 先看浏览器控制台。
   看按钮点击、表单提交、请求发送和响应返回的中文日志。

2. 再看后端终端。
   看随机系数生成、评估点选择、份额计算、插值、求根、哈希匹配、验证通过或拒绝的日志。

3. 先试 `/api/share`。
   看秘密怎样变成份额。

4. 再试 `/api/rec`。
   看若干份额怎样恢复 `q(0)`。

5. 再试 `/api/trace`。
   看 `q(x) = leaked_y` 怎样找回真正的 `x`。

6. 最后试 `/api/verify`。
   看 `Hash(proof_x)` 怎样和验证密钥做最终比对。

推荐的验收样例是：

- `secret = "1234"`
- `share_count = 5`
- `threshold = 3`

预期结果：

- 分发成功并返回 5 个份额。
- 任取 3 个份额可以恢复出 `1234`。
- 任取 3 个合法参考份额，并输入某一参与者的 `leaked_y`，可以追踪出唯一 `traitor_id` 与 `proof_x`。
- `proof_x` 正确时验证通过，错误时验证拒绝。
