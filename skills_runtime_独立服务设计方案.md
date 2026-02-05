# Skills Runtime 独立服务设计方案

> 本文档用于设计一个**独立于业务系统的 Skills Runtime 服务**，对齐 Claude Agent Skills 的执行模型，支持 Python / Node(TypeScript) 等脚本能力，以 HTTP/RPC 方式对外提供执行服务。

---

## 1. 设计目标

### 1.1 核心目标

- 将 **Skills 执行能力服务化**（Skills as a Service）
- 与原有 Java 业务系统 **完全解耦**
- 支持 **Python / Node / TypeScript / Shell** 等执行环境
- 通过标准接口被 Agent / 业务系统调用
- 不强依赖具体大模型（Claude / OpenAI / 自研）

### 1.2 非目标（明确不做）

- ❌ 不承载业务逻辑
- ❌ 不直接管理数据库事务
- ❌ 不提供对话 UI
- ❌ 不与某一 Agent 框架强绑定

---

## 2. 总体架构

```
┌────────────────────────────┐
│        业务系统 / Agent     │
│  - Planner（LLM）          │
│  - API / 网关              │
└─────────────┬──────────────┘
              │ HTTP / RPC
              ▼
┌────────────────────────────────┐
│     Skills Runtime Service      │
│                                │
│  ├── Skill Registry             │
│  ├── Skill Loader               │
│  ├── Skill Executor             │
│  │    ├── Python Runner         │
│  │    └── Node Runner           │
│  ├── Sandbox & Resource Control │
│  ├── Artifact Manager           │
│  └── （可选）Planner            │
│                                │
└─────────────┬──────────────────┘
              │
              ▼
        py / ts / shell
```

> **核心原则**：
>
> - LLM 只负责“决策”
> - Runtime 只负责“执行”

---

## 3. Skill 规范设计

### 3.1 Skill 目录结构（强制约定）

```
skills/
└── get-available-resources/
    ├── skill.yaml        # 元数据（给 Planner / LLM）
    ├── skill.md          # 执行说明（可选，按需加载）
    ├── run.py            # 或 run.ts / run.sh
    └── requirements.txt  # 可选
```

---

### 3.2 skill.yaml 规范

```yaml
name: get-available-resources
description: Detect CPU, memory, disk and GPU resources
runtime:
  type: python        # python | node | shell
timeout: 10000        # ms
artifacts:
  - artifacts/resources.json
```

**说明**：

- `name / description`：用于 Planner 决策
- `runtime.type`：决定由哪个执行器运行
- `timeout`：单次执行最大时长
- `artifacts`：声明可能产生的文件产物

---

## 4. 核心模块设计

### 4.1 Skill Registry

**职责**：

- 启动时扫描 `skills/` 目录
- 解析 `skill.yaml`
- 对外提供 Skill 元数据列表

---

### 4.2 Skill Loader（渐进加载）

**职责**：

- 仅在 Skill 被选中时加载 `skill.md`
- 不将执行脚本内容暴露给 LLM

> 对齐 Claude 的「渐进式披露（Progressive Disclosure）」设计。

---

### 4.3 Skill Executor（执行引擎）

#### 执行约定（必须遵守）

- **stdin**：输入 JSON
- **stdout**：输出 JSON（唯一返回值）
- **stderr**：日志 / 错误

#### Executor 拆分

```
SkillExecutor
├── PythonExecutor
├── NodeExecutor
└── ShellExecutor（可选）
```

---

### 4.4 Artifact Manager

**职责**：

- 管理 Skill 执行产物
- 按 executionId 隔离
- 控制生命周期

**推荐结构**：

```
artifacts/
└── {executionId}/
    ├── output.json
    └── logs.txt
```

---

### 4.5 Sandbox & Resource Control

#### 第一阶段（必做）

- 超时控制（timeout kill）
- cwd 隔离
- stdout / stderr 大小限制

#### 第二阶段（进阶）

- Docker / 容器隔离
- CPU / 内存限制
- 网络访问控制

---

## 5. 对外 API 设计

### 5.1 查询可用 Skills

```
GET /api/skills
```

**Response**：

```json
[
  {
    "name": "get-available-resources",
    "description": "Detect system resources",
    "runtime": "python"
  }
]
```

---

### 5.2 执行 Skill

```
POST /api/skills/execute
```

**Request**：

```json
{
  "skillName": "get-available-resources",
  "input": {
    "project": "demo"
  },
  "options": {
    "timeoutMs": 10000
  }
}
```

**Response**：

```json
{
  "success": true,
  "executionId": "exec-123",
  "output": {
    "cpu_cores": 8,
    "memory_gb": 16
  },
  "artifacts": [
    "artifacts/exec-123/resources.json"
  ]
}
```

---

## 6. 执行链路时序

```
业务系统
  ↓
LLM Planner（决策）
  ↓
POST /api/skills/execute
  ↓
Skill Registry 校验
  ↓
Skill Executor 运行脚本
  ↓
Artifact Manager 保存产物
  ↓
JSON 返回给业务系统
  ↓
LLM 基于结果继续推理
```

---

## 7. 部署与运行建议

### 7.1 Docker 化（强烈推荐）

Runtime 镜像应包含：

- JRE 17+
- Python 3.x
- Node.js 18+
- （可选）tsx / ts-node

**示意**：

```dockerfile
FROM eclipse-temurin:17
RUN apt-get update \
 && apt-get install -y python3 nodejs npm
```

---

## 8. 与原系统的关系

| 项目            | 是否依赖          |
| ------------- | ------------- |
| 原业务系统         | ❌             |
| 数据库           | ❌             |
| Python / Node | ❌（Runtime 内置） |
| LLM Provider  | ❌             |

> Skills Runtime 是一个**通用执行平台**。

---

## 9. 分阶段落地路线

### Phase 1：最小可用

- 单实例 Runtime
- Python Skill
- 本地执行
- 无 Sandbox

### Phase 2：工程化

- Node / TS
- Artifact 管理
- 超时控制
- Docker 部署

### Phase 3：平台化

- 多租户
- 权限 / 配额
- Skill 市场
- 完整沙箱

---

## 10. 总结

> **该方案本质上是将 Claude Code 的 CLI 执行模型， 提炼为一个可复用、可治理、可扩展的 Skills 执行服务。**

适用于：

- Agent 平台
- 内部 AI 基础设施
- 企业级工具链

---

（完）

