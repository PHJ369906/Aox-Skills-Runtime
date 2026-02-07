# Skills Runtime Service (Django)

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2+-0C4B33.svg)](https://www.djangoproject.com/)

独立的 Skills Runtime 服务，面向 Agent/业务系统提供标准化的 Skills 执行能力。

## 项目简介

- 解耦业务系统：Runtime 只负责执行
- 支持多语言技能：Python / Node / Shell
- 标准化 I/O：stdin JSON 输入、stdout JSON 输出
- 产物归档：每次执行隔离 `artifacts/<executionId>/`

## 功能概览（MVP）

- 扫描并注册 `skills/` 目录下的技能
- 执行技能并返回 JSON 输出
- 超时控制、stdout/stderr 限制、错误返回
- 产物归档与执行日志保存

## 目录结构

```
.
├── manage.py
├── requirements.txt
├── skills_runtime_service/   # Django project
├── runtime_api/              # API app
├── runtime/                  # 执行引擎（Registry/Executor）
├── skills/                   # Skills 目录
│   └── get-available-resources/
└── artifacts/                # 执行产物（运行时生成）
```

## 安装与运行

前置要求：
- Python 3.10+

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8080
```

可通过环境变量覆盖默认路径：

```bash
export SKILLS_DIR=./skills
export ARTIFACTS_DIR=./artifacts
export DEFAULT_TIMEOUT_MS=10000
export DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
export SQLITE_PATH=./db.sqlite3
```

生产环境建议设置：

```bash
export DJANGO_DEBUG=0
export DJANGO_SECRET_KEY='replace-with-a-strong-secret'
export DJANGO_ALLOWED_HOSTS='your.domain.com'
```

## Docker 运行

### 使用 Docker Compose

```bash
docker compose up --build -d
curl http://localhost:8080/api/health
docker compose logs -f
```

停止服务：

```bash
docker compose down
```

默认 compose 配置会：
- 启动时自动执行 `python manage.py migrate`
- 使用 `gunicorn` 监听 `0.0.0.0:8080`
- 挂载 `./artifacts` 与 `./data`（持久化产物与 SQLite）

## API

### Health

```bash
curl http://localhost:8080/api/health
```

### List Skills

```bash
curl http://localhost:8080/api/skills
```

### Execute Skill

```bash
curl -X POST http://localhost:8080/api/skills/execute \
  -H 'Content-Type: application/json' \
  -d '{"skillName":"get-available-resources","input":{},"options":{"timeoutMs":10000}}'
```

## Skill 规范

每个技能放在 `skills/<skill-name>/` 下，必须包含 `skill.yaml` 与入口脚本。

`skill.yaml` 使用 **JSON 兼容 YAML**：

```json
{
  "name": "get-available-resources",
  "description": "Detect CPU, memory, disk and platform info",
  "runtime": {"type": "python"},
  "timeout": 10000,
  "artifacts": ["artifacts/resources.json"]
}
```

支持运行时：
- `python`（入口 `run.py`）
- `node`（入口 `run.js` / `run.ts`）
- `shell`（入口 `run.sh`）

## 执行约定

- stdin：JSON 输入
- stdout：JSON 输出（必须）
- stderr：日志/错误信息

## Roadmap（建议）

- API Key 鉴权
- 技能热更新/重载
- OpenAPI 文档
- 更强沙箱隔离
- 指标与监控

---

如需扩展或接入企业级能力，请直接在 issues 或 PR 中讨论。
