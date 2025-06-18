# 飞书任务 Bot

一款用于远程任务分派与进度跟进的飞书机器人。

## 功能特性

- 基于 LLM 的智能人才匹配
- 一键创建任务子群
- 自动验收与评分
- CI 集成（GitHub Actions）
- 轻量级 KPI 报表

## 技术栈

- Python 3.11
- FastAPI
- 飞书多维表格（作为数据库）
- 可插拔 LLM 后端 (DeepSeek / Gemini / OpenAI)

## 快速开始

### 1. 准备环境

```bash
# 安装依赖
pip install -r requirements.txt

# 复制并修改环境变量模板
cp .env.example .env
```

### 2. 修改配置

编辑 `.env` 文件，填入你的飞书应用凭据:

```
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_VERIFY_TOKEN=xxx

# 以下至少需要一个 LLM 后端
DEEPSEEK_KEY=xxx
GEMINI_KEY=xxx 
OPENAI_KEY=xxx
```

### 3. 启动服务

```bash
# 开发环境启动
make dev
```

### 4. 设置 SSH 隧道到公网

将本地服务映射到 lyh.ai:12345：

```bash
make ssh-tunnel
```

这样飞书事件将能通过 `https://lyh.ai:12345/webhook/feishu` 传递到本地服务。

## 部署

### 创建飞书应用

1. 登录[飞书开发者后台](https://open.feishu.cn/app)
2. 创建企业自建应用
3. 添加权限:
   - `im:message` (发/收消息)
   - `chat:write`, `chat:update` (创建群、拉人)
   - `bitable:*` (读写多维表)
4. 创建并配置回调地址 `https://lyh.ai:12345/webhook/feishu`
5. 将 App ID, App Secret 和 Verification Token 填入 `.env`

### 多维表设置

1. 在飞书创建多维表，设置对应的表结构
2. 获取 app_token 和表 ID
3. 在 `app/main.py` 中的 `startup_event` 设置正确的多维表 ID

## 测试

```bash
# 运行单元测试
make test-unit

# 运行集成测试
make test-int

# 运行端到端测试
make test-e2e

# 运行所有测试
make test
```

## 主要命令

- `@bot 新任务 标题 | 技能标签 | 截止日期 | 描述` - 创建新任务
- `/done <链接>` - 提交任务结果
- `#report` - 显示当日任务统计 