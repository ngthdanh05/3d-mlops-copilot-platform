# 🚀 PLAN.md — 3D-MLOps Copilot Platform

> **Nền tảng quản lý thực nghiệm học máy trong không gian 3D tích hợp trợ lý AI**
>
> Version: `1.0.0-draft` · Created: 2026-11-06 · Author: Principal System Architect

---

## Mục lục

1. [Project Overview & Architecture](#1-project-overview--architecture)
2. [Core Features Scope (MVP Phase)](#2-core-features-scope-mvp-phase)
3. [Tech Stack & Project Setup](#3-tech-stack--project-setup)
4. [Implementation Roadmap & Detailed Task Breakdown](#4-implementation-roadmap--detailed-task-breakdown)
5. [Risk Assessment & Technical Constraints](#5-risk-assessment--technical-constraints)

---

## 1. Project Overview & Architecture

### 1.1 Tóm tắt mục tiêu (PoC / MVP Scope)

Xây dựng một **Proof of Concept** hoạt động end-to-end, cho phép:

| #   | Mục tiêu                                  | Tiêu chí thành công (PoC)                                               |
| --- | ----------------------------------------- | ----------------------------------------------------------------------- |
| 1   | **Track** các đợt huấn luyện ML           | Ghi hyperparams + metrics vào SQLite qua REST API; ≥ 5 runs mẫu         |
| 2   | **Visualize** kết quả trong không gian 3D | Render ≥ 50 nodes ở 60 fps; click node hiển thị Inspector Panel         |
| 3   | **Converse** với AI Copilot               | Trả lời ≥ 3 loại truy vấn (best run, compare, diagnose) trong < 5 giây  |
| 4   | **Synchronize** trạng thái xuyên suốt     | Click node → panel update; AI trả lời → camera focus tới node tương ứng |

> [!IMPORTANT]
> Phạm vi PoC **không** bao gồm: xác thực người dùng, multi-tenant, CI/CD pipeline tích hợp, model registry, hoặc deployment pipeline. Các tính năng này thuộc roadmap post-MVP.

### 1.2 Kiến trúc hệ thống tổng quan

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CLIENT (Browser)                                   │
│                                                                             │
│  ┌───────────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │   3D Spatial Canvas   │  │  Inspector Panel  │  │   AI Chat Panel     │  │
│  │  (React Three Fiber)  │  │  (React + TW CSS) │  │  (React + Markdown) │  │
│  │                       │  │                   │  │                     │  │
│  │  • OrbitControls      │  │  • Hyperparams    │  │  • Message history  │  │
│  │  • Node Spheres       │◄─┤  • Metrics table  │  │  • Streaming resp.  │  │
│  │  • Raycasting click   │  │  • Run metadata   │  │  • Action buttons   │  │
│  │  • Camera animation   │  │                   │  │                     │  │
│  └──────────┬────────────┘  └────────┬─────────┘  └──────────┬───────────┘  │
│             │                        │                       │              │
│             └────────────────────────┼───────────────────────┘              │
│                                      │                                      │
│                        Zustand Global State Store                           │
│                    (selectedRun, runs[], chatMessages[])                    │
└──────────────────────────────────────┼──────────────────────────────────────┘
                                       │  HTTP / REST
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI – Python)                            │
│                                                                              │
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────────┐  │
│  │  /api/runs          │  │  /api/runs/{id}     │  │  /api/copilot/chat     │  │
│  │  GET  → list runs   │  │  GET  → run detail  │  │  POST → AI query       │  │
│  │  POST → create run  │  │  PUT  → update run  │  │                        │  │
│  └────────┬───────────┘  └────────┬───────────┘  └──────────┬─────────────┘  │
│           │                       │                         │                │
│           ▼                       ▼                         ▼                │
│  ┌─────────────────────────────────────┐    ┌──────────────────────────────┐  │
│  │         SQLite Database             │    │      AI Copilot Engine       │  │
│  │  • experiments table                │    │                              │  │
│  │  • runs table                       │◄───┤  • Context Builder           │  │
│  │  • metrics table                    │    │  • Prompt Template Engine    │  │
│  │  • hyperparams table               │    │  • LLM API Client            │  │
│  └─────────────────────────────────────┘    │  • Response Parser           │  │
│                                             │    (action extraction)       │  │
│                                             └──────────────┬───────────────┘  │
│                                                            │                 │
└────────────────────────────────────────────────────────────┼─────────────────┘
                                                             │  HTTPS
                                                             ▼
                                                  ┌─────────────────────┐
                                                  │   LLM Provider API  │
                                                  │  (Gemini / OpenAI)  │
                                                  └─────────────────────┘
```

### 1.3 Data Flow chính

```
sequenceDiagram (mô tả text)

[Train Script] ──POST /api/runs──► [FastAPI] ──INSERT──► [SQLite]
[Frontend]     ──GET /api/runs───► [FastAPI] ──SELECT──► [SQLite]
[Frontend]     ──renders──────────► [3D Canvas: Node spheres]
[User]         ──click node───────► [Zustand] ──update──► [Inspector Panel]
[User]         ──chat message─────► [Frontend] ──POST /api/copilot/chat──► [FastAPI]
[FastAPI]      ──build context────► [LLM API] ──response──► [FastAPI]
[FastAPI]      ──parsed response──► [Frontend] ──camera focus + chat bubble──► [UI]
```

---

## 2. Core Features Scope (MVP Phase)

### 2.1 ML Tracking Core

#### Mô hình dữ liệu (Data Model)

```
┌─────────────────────────────────────────────────────────┐
│                      experiments                         │
├──────────────┬──────────┬────────────────────────────────┤
│ id (PK)      │ INTEGER  │ Auto-increment                 │
│ name         │ TEXT     │ "MNIST-CNN-v1"                 │
│ description  │ TEXT     │ Mô tả thí nghiệm              │
│ created_at   │ DATETIME │ ISO 8601                       │
└──────┬───────┴──────────┴────────────────────────────────┘
       │ 1:N
       ▼
┌─────────────────────────────────────────────────────────┐
│                         runs                             │
├──────────────┬──────────┬────────────────────────────────┤
│ id (PK)      │ INTEGER  │ Auto-increment                 │
│ experiment_id│ INTEGER  │ FK → experiments.id             │
│ run_name     │ TEXT     │ "run-001"                      │
│ status       │ TEXT     │ "running" | "completed" | "failed" │
│ hyperparams  │ JSON     │ {"lr": 0.001, "batch_size": 32}│
│ created_at   │ DATETIME │                                │
│ finished_at  │ DATETIME │ nullable                       │
└──────┬───────┴──────────┴────────────────────────────────┘
       │ 1:N
       ▼
┌─────────────────────────────────────────────────────────┐
│                       metrics                            │
├──────────────┬──────────┬────────────────────────────────┤
│ id (PK)      │ INTEGER  │ Auto-increment                 │
│ run_id       │ INTEGER  │ FK → runs.id                   │
│ epoch        │ INTEGER  │ 1, 2, 3, ...                   │
│ accuracy     │ REAL     │ 0.0 – 1.0                     │
│ loss         │ REAL     │ ≥ 0                            │
│ val_accuracy │ REAL     │ nullable                       │
│ val_loss     │ REAL     │ nullable                       │
│ logged_at    │ DATETIME │                                │
└──────────────┴──────────┴────────────────────────────────┘
```

#### Chức năng MVP

| ID    | Chức năng               | Mô tả                                                                  |
| ----- | ----------------------- | ---------------------------------------------------------------------- |
| TR-01 | Tạo Experiment          | `POST /api/experiments` — tạo nhóm thực nghiệm                         |
| TR-02 | Tạo Run                 | `POST /api/runs` — log hyperparams, gắn experiment_id                  |
| TR-03 | Log Metrics theo Epoch  | `POST /api/runs/{id}/metrics` — ghi accuracy, loss, val_loss per epoch |
| TR-04 | Lấy danh sách Runs      | `GET /api/runs?experiment_id=X` — trả về list runs + final metrics     |
| TR-05 | Lấy chi tiết Run        | `GET /api/runs/{id}` — hyperparams + full metrics timeline             |
| TR-06 | Cập nhật trạng thái Run | `PUT /api/runs/{id}` — đánh dấu "completed" / "failed"                 |

### 2.2 3D Spatial Workspace

#### Hệ tọa độ 3D (Coordinate Mapping)

```
        Y (Accuracy: 0→1)
        ▲
        │       ● run-003 (best)
        │      ╱
        │     ╱
        │    ● run-001
        │   ╱
        │  ● run-002
        │ ╱
        ├──────────────────────► X (Epoch: 1→N)
       ╱
      ╱  ● run-004 (high loss)
     ╱
    ▼
    Z (Loss: 0→max)
```

| Trục | Ý nghĩa          | Ánh xạ                                               |
| ---- | ---------------- | ---------------------------------------------------- |
| X    | Epoch (final)    | `normalize(epoch, 0, max_epoch) * SCALE_X`           |
| Y    | Accuracy (final) | `accuracy * SCALE_Y`                                 |
| Z    | Loss (final)     | `normalize(loss, 0, max_loss) * SCALE_Z` (đảo chiều) |

#### Visual Encoding của Node

| Thuộc tính         | Encoding                                                                        |
| ------------------ | ------------------------------------------------------------------------------- |
| **Vị trí (x,y,z)** | Epoch × Accuracy × Loss (cuối cùng của run)                                     |
| **Màu sắc**        | Trạng thái: 🟢 `#22c55e` completed · 🟡 `#eab308` running · 🔴 `#ef4444` failed |
| **Kích thước**     | Tỉ lệ thuận với `val_accuracy` (or `accuracy` nếu không có val)                 |
| **Phát sáng**      | Emissive glow khi node đang được selected hoặc AI highlight                     |
| **Label**          | Billboard text hiển thị `run_name` khi hover                                    |

#### Tương tác 3D

| ID    | Tương tác          | Chi tiết kỹ thuật                                                    |
| ----- | ------------------ | -------------------------------------------------------------------- |
| 3D-01 | Orbit Controls     | Zoom (scroll), Pan (right-click drag), Rotate (left-click drag)      |
| 3D-02 | Raycasting Click   | `onClick` trên mesh → dispatch `selectRun(runId)` vào Zustand        |
| 3D-03 | Hover Tooltip      | `onPointerOver` → hiện billboard label với run_name + accuracy       |
| 3D-04 | Camera Fly-to      | Animate camera position smooth tới node khi selected (GSAP / spring) |
| 3D-05 | Grid & Axes Helper | Lưới tham chiếu + labels trục X, Y, Z                                |
| 3D-06 | Node Filtering     | Filter nodes theo status, accuracy range (UI controls bên ngoài)     |

### 2.3 AI Copilot Agent

#### Kiểu truy vấn hỗ trợ (MVP)

| ID    | Intent                    | Ví dụ câu hỏi                              | Hành vi                                             |
| ----- | ------------------------- | ------------------------------------------ | --------------------------------------------------- |
| AI-01 | **Tìm best run**          | "Run nào có accuracy cao nhất?"            | Trả lời + highlight node + camera fly-to            |
| AI-02 | **So sánh 2 runs**        | "So sánh run-001 và run-003"               | Bảng so sánh hyperparams + metrics + nhận xét       |
| AI-03 | **Chẩn đoán overfitting** | "Run-002 có bị overfit không?"             | Phân tích gap train/val → kết luận + đề xuất        |
| AI-04 | **Tóm tắt experiment**    | "Tóm tắt tình trạng thí nghiệm hiện tại"   | Thống kê tổng quan: best/worst, trung bình, phân bố |
| AI-05 | **Đề xuất hyperparams**   | "Tôi nên thử learning_rate nào tiếp theo?" | Dựa trên pattern các runs trước → đề xuất           |

#### Kiến trúc AI Engine

```
┌─────────────────────────────────────────────────────────────────┐
│                     AI Copilot Engine                            │
│                                                                 │
│  ┌──────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │ Context      │    │ Prompt Template  │    │ Response       │  │
│  │ Builder      │───►│ Engine           │───►│ Parser         │  │
│  │              │    │                  │    │                │  │
│  │ • Fetch runs │    │ • System prompt  │    │ • Extract text │  │
│  │ • Rank top-K │    │ • Few-shot       │    │ • Extract      │  │
│  │ • Build      │    │   examples       │    │   actions:     │  │
│  │   summary    │    │ • User query     │    │   highlight,   │  │
│  │   stats      │    │ • Context inject │    │   focus,       │  │
│  └──────────────┘    └────────┬─────────┘    │   compare      │  │
│                               │              └───────┬───────┘  │
│                               ▼                      │          │
│                      ┌────────────────┐              │          │
│                      │  LLM API Call  │──────────────┘          │
│                      │  (Gemini/GPT)  │                         │
│                      └────────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

#### Structured Response Format

AI Engine trả về JSON có cấu trúc để Frontend xử lý hành vi:

```json
{
  "message": "Run tốt nhất là **run-003** với accuracy 0.9845...",
  "actions": [
    {
      "type": "highlight",
      "run_ids": ["run-003"]
    },
    {
      "type": "camera_focus",
      "target_run_id": "run-003"
    }
  ],
  "metadata": {
    "intent": "best_run",
    "confidence": 0.95,
    "referenced_runs": ["run-003"]
  }
}
```

---

## 3. Tech Stack & Project Setup

### 3.1 Technology Matrix

#### Frontend

| Lớp                | Công nghệ               | Phiên bản | Vai trò                                  |
| ------------------ | ----------------------- | --------- | ---------------------------------------- |
| Build Tool / App   | Vite (React SPA)        | ≥ 5       | Bundler siêu nhanh, HMR tức thì, tối ưu render 3D client-side |
| UI Library         | React                   | ≥ 18      | Component rendering                      |
| 3D Engine          | Three.js                | ≥ 0.160   | WebGL rendering engine                   |
| 3D React Binding   | React Three Fiber (R3F) | ≥ 8       | Declarative Three.js trong React         |
| 3D Helpers         | @react-three/drei       | ≥ 9       | OrbitControls, Billboard, Html, Text     |
| State Management   | Zustand                 | ≥ 4       | Global state đơn giản, không boilerplate |
| Styling            | Tailwind CSS            | ≥ 3       | Utility-first CSS                        |
| HTTP Client        | fetch / SWR             | native    | Data fetching with caching               |
| Markdown Rendering | react-markdown          | ≥ 9       | Render câu trả lời AI dạng Markdown      |
| Animation          | @react-spring/three     | ≥ 9       | Spring-based camera & node animation     |

#### Backend

| Lớp                | Công nghệ              | Phiên bản | Vai trò                                    |
| ------------------ | ---------------------- | --------- | ------------------------------------------ |
| Framework          | FastAPI                | ≥ 0.104   | Async REST API framework                   |
| Runtime            | Python                 | ≥ 3.11    | Backend runtime                            |
| ORM                | SQLAlchemy             | ≥ 2.0     | Database abstraction + async support       |
| Database           | SQLite                 | built-in  | Lightweight persistent storage (PoC scope) |
| Migration          | Alembic                | ≥ 1.12    | Schema migration (optional for PoC)        |
| Validation         | Pydantic               | ≥ 2.0     | Request/Response schema validation         |
| CORS               | fastapi.middleware     | built-in  | Cross-origin cho frontend dev server       |
| AI SDK             | google-genai / openai  | latest    | LLM API client                             |
| ML Training (demo) | scikit-learn / PyTorch | latest    | Script huấn luyện mẫu để tạo data          |

#### DevOps & Tooling

| Công cụ  | Vai trò                       |
| -------- | ----------------------------- |
| pnpm     | Frontend package manager      |
| uv / pip | Python package manager        |
| ESLint   | JavaScript/TypeScript linting |
| Ruff     | Python linting + formatting   |
| Prettier | Code formatting (JS/TS/CSS)   |
| pytest   | Python unit/integration tests |
| Vitest   | Frontend unit tests           |

### 3.2 Cấu trúc thư mục dự án (Directory Tree)

```
3d-mlops-copilot/
│
├── README.md                          # Hướng dẫn tổng quan
├── PLAN.md                            # File kế hoạch này
├── .gitignore
├── .env.example                       # Template biến môi trường
│
├── backend/                           # ═══ Python FastAPI Backend ═══
│   ├── pyproject.toml                 # Python dependencies (uv/pip)
│   ├── alembic.ini                    # DB migration config
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app entry point
│   │   ├── config.py                  # Settings (DB path, LLM key, CORS)
│   │   ├── database.py                # SQLAlchemy engine + session
│   │   │
│   │   ├── models/                    # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── experiment.py          # Experiment model
│   │   │   ├── run.py                 # Run model (+ hyperparams JSON)
│   │   │   └── metric.py             # Metric model (per-epoch)
│   │   │
│   │   ├── schemas/                   # Pydantic request/response schemas
│   │   │   ├── __init__.py
│   │   │   ├── experiment.py
│   │   │   ├── run.py
│   │   │   ├── metric.py
│   │   │   └── copilot.py            # ChatRequest, ChatResponse, Action
│   │   │
│   │   ├── routers/                   # API route handlers
│   │   │   ├── __init__.py
│   │   │   ├── experiments.py         # /api/experiments
│   │   │   ├── runs.py                # /api/runs
│   │   │   ├── metrics.py            # /api/runs/{id}/metrics
│   │   │   └── copilot.py            # /api/copilot/chat
│   │   │
│   │   ├── services/                  # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── tracking.py           # ML tracking CRUD operations
│   │   │   └── copilot/
│   │   │       ├── __init__.py
│   │   │       ├── engine.py          # AI Copilot orchestrator
│   │   │       ├── context_builder.py # Build context from runs data
│   │   │       ├── prompt_templates.py# System prompt + few-shot examples
│   │   │       └── response_parser.py # Parse LLM output → structured JSON
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── seed_data.py           # Seed sample runs for development
│   │
│   ├── scripts/
│   │   ├── train_mnist_demo.py        # Demo training script (sklearn/torch)
│   │   └── log_to_api.py             # Logger client: gửi metrics → API
│   │
│   └── tests/
│       ├── __init__.py
│       ├── test_tracking_api.py
│       ├── test_copilot_engine.py
│       └── conftest.py
│
├── frontend/                          # ═══ Vite + React Frontend ═══
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── vite.config.ts                 # Cấu hình Vite & API proxy
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── index.html                     # Entry HTML cho SPA
│   │
│   ├── public/
│   │   └── textures/                  # Texture maps cho 3D nodes (optional)
│   │
│   ├── src/
│   │   ├── main.tsx                   # Entry point React
│   │   ├── App.tsx                    # Root component → renders Workspace
│   │   ├── index.css                  # Tailwind imports & global styles
│   │   │
│   │   │
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Workspace.tsx      # Main 3-panel layout container
│   │   │   │   ├── Sidebar.tsx        # Left sidebar (experiment list)
│   │   │   │   └── TopBar.tsx         # Header bar
│   │   │   │
│   │   │   ├── three/                 # ═══ 3D Components (R3F) ═══
│   │   │   │   ├── Scene.tsx          # Canvas + Scene setup
│   │   │   │   ├── RunNode.tsx        # Single run sphere mesh
│   │   │   │   ├── RunNodes.tsx       # Collection: maps runs[] → RunNode
│   │   │   │   ├── AxesLabels.tsx     # X/Y/Z axis labels + grid
│   │   │   │   ├── CameraController.tsx # Animated camera fly-to
│   │   │   │   └── SceneLighting.tsx  # Ambient + directional lights
│   │   │   │
│   │   │   ├── panels/
│   │   │   │   ├── InspectorPanel.tsx # Run detail panel (right side)
│   │   │   │   ├── MetricsChart.tsx   # Epoch-over-epoch line chart
│   │   │   │   └── HyperparamsTable.tsx
│   │   │   │
│   │   │   └── copilot/
│   │   │       ├── ChatPanel.tsx      # AI chat container
│   │   │       ├── ChatMessage.tsx    # Single message bubble
│   │   │       ├── ChatInput.tsx      # Input + send button
│   │   │       └── ActionHandler.tsx  # Process AI response actions
│   │   │
│   │   ├── store/
│   │   │   ├── useRunStore.ts         # Zustand: runs[], selectedRunId
│   │   │   ├── useChatStore.ts        # Zustand: messages[], isLoading
│   │   │   └── useCameraStore.ts      # Zustand: cameraTarget, shouldAnimate
│   │   │
│   │   ├── hooks/
│   │   │   ├── useRuns.ts             # SWR hook: fetch /api/runs
│   │   │   ├── useCopilot.ts          # Hook: send chat, parse response
│   │   │   └── useNodePosition.ts     # Hook: calculate 3D coords from run
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts                 # API client (base URL, helpers)
│   │   │   ├── constants.ts           # 3D scale factors, colors, etc.
│   │   │   └── types.ts              # TypeScript interfaces (Run, Metric...)
│   │   │
│   │   └── utils/
│   │       ├── coordinate-mapper.ts   # Map run data → 3D position
│   │       └── color-utils.ts         # Status → color mapping
│   │
│   └── tests/
│       ├── components/
│       │   └── RunNode.test.tsx
│       └── utils/
│           └── coordinate-mapper.test.ts
│
└── docs/
    ├── api-spec.md                    # API endpoint documentation
    ├── architecture-decisions.md      # ADR log
    └── screenshots/                   # Demo screenshots
```

---

## 4. Implementation Roadmap & Detailed Task Breakdown

### Tổng quan Timeline

```
Phase 1          Phase 2          Phase 3          Phase 4         Phase 5
Foundation       3D Scene         AI Copilot       Sync & Polish   Testing
━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━  ━━━━━━━━━━
  ~2-3 days       ~3-4 days        ~3-4 days        ~2-3 days      ~1-2 days
```

> [!NOTE]
> Ước lượng thời gian dành cho **1 developer full-time**. Có thể parallelise Phase 2 và Phase 3 nếu có 2 developers (frontend + backend).

---

### Phase 1: Foundation & MLOps Engine Setup

> **Mục tiêu:** Backend hoạt động, có thể ghi/đọc experiment data qua REST API. Có ≥ 5 runs mẫu trong database.

#### Tasks

- [ ] **P1-T01: Khởi tạo Backend Project**
  - Tạo `backend/` directory, `pyproject.toml` với dependencies
  - Setup FastAPI app skeleton (`main.py`, `config.py`)
  - Cấu hình CORS middleware cho `localhost:5173` (Vite dev server) / `localhost:3000`
  - **DoD:** `uvicorn app.main:app --reload` khởi chạy, `/docs` (Swagger) accessible

- [ ] **P1-T02: Database Models & Setup**
  - Định nghĩa SQLAlchemy models: `Experiment`, `Run`, `Metric`
  - Tạo `database.py` với async SQLite engine
  - Auto-create tables on startup (`metadata.create_all`)
  - **DoD:** Database file `mlops.db` được tạo; tables verify qua `sqlite3` CLI

- [ ] **P1-T03: Pydantic Schemas**
  - Tạo request/response schemas cho Experiment, Run, Metric
  - Validation rules: `learning_rate > 0`, `0 ≤ accuracy ≤ 1`, `epochs ≥ 1`
  - **DoD:** Schemas importable, JSON serialization/deserialization hoạt động

- [ ] **P1-T04: CRUD API Endpoints**
  - `POST /api/experiments` — Tạo experiment
  - `GET /api/experiments` — List experiments
  - `POST /api/runs` — Tạo run (với hyperparams JSON)
  - `GET /api/runs` — List runs (filter by experiment_id, include final metrics)
  - `GET /api/runs/{id}` — Chi tiết run + full metrics timeline
  - `PUT /api/runs/{id}` — Update status
  - `POST /api/runs/{id}/metrics` — Log metrics cho 1 epoch
  - **DoD:** Tất cả endpoints test thành công qua Swagger UI; HTTP status codes đúng

- [ ] **P1-T05: Demo Training Script**
  - Viết `scripts/train_mnist_demo.py`:
    - Train sklearn `MLPClassifier` hoặc PyTorch CNN trên MNIST (subset nhỏ)
    - Mỗi epoch: call `POST /api/runs/{id}/metrics` với accuracy, loss, val_loss
    - Kết thúc: `PUT /api/runs/{id}` → status = "completed"
  - Chạy 5-10 lần với hyperparams khác nhau (vary `lr`, `batch_size`, `epochs`)
  - **DoD:** Database có ≥ 5 runs, mỗi run có ≥ 5 epochs metrics; `GET /api/runs` trả về đúng data

- [ ] **P1-T06: Seed Data Utility**
  - Viết `utils/seed_data.py`: tạo synthetic runs (không cần train thật) cho dev nhanh
  - Generate 20-50 runs với realistic-looking metrics curves
  - **DoD:** Chạy seed script → DB populated; frontend dev có thể dùng ngay

- [ ] **P1-T07: Unit Tests cho Tracking API**
  - Test CRUD operations với in-memory SQLite
  - Test validation (invalid hyperparams, missing fields)
  - **DoD:** `pytest tests/test_tracking_api.py` — all green, ≥ 80% coverage cho routers

---

### Phase 2: 3D Scene & Canvas Development

> **Mục tiêu:** Frontend hiển thị không gian 3D với các Run Nodes, tương tác được (orbit, click, hover). Inspector Panel hiển thị chi tiết khi click node.

#### Tasks

- [ ] **P2-T01: Khởi tạo Frontend Project**
  - `pnpm create vite frontend --template react-ts` (Vite + React SPA, TypeScript)
  - Install: `three`, `@react-three/fiber`, `@react-three/drei`, `zustand`, `swr`
  - Setup Tailwind CSS: `tailwind.config.js`, `postcss.config.js`, `src/index.css`
  - Cấu hình API reverse proxy trong `vite.config.ts` (`/api` -> `http://localhost:8000`)
  - **DoD:** `pnpm dev` → Vite dev server chạy tại `localhost:5173`; khởi động tức thì, blank page renders

- [ ] **P2-T02: TypeScript Types & API Client**
  - Định nghĩa `types.ts`: `Run`, `Metric`, `Experiment`, `ChatMessage`, `CopilotResponse`
  - Tạo `lib/api.ts`: base URL config, `fetchRuns()`, `fetchRunDetail(id)`
  - **DoD:** `useRuns()` hook trả về data từ backend (proxy qua `vite.config.ts` server.proxy)

- [ ] **P2-T03: Layout Workspace (3-Panel)**
  - Tạo `Workspace.tsx`: CSS Grid / Flexbox layout
    ```
    ┌──────────┬────────────────────────┬──────────────┐
    │ Sidebar  │     3D Canvas          │  Inspector   │
    │ (250px)  │     (flex-1)           │  Panel       │
    │          │                        │  (350px)     │
    │          │                        │              │
    │          │                        ├──────────────┤
    │          │                        │  Chat Panel  │
    │          │                        │  (350px)     │
    └──────────┴────────────────────────┴──────────────┘
    ```
  - Responsive: collapse sidebar on mobile
  - **DoD:** Layout hiển thị đúng 3 panels; resize browser không break layout

- [ ] **P2-T04: 3D Scene Foundation**
  - Tạo `Scene.tsx` với R3F `<Canvas>`:
    - Camera: PerspectiveCamera, position `[15, 10, 15]`, fov 60
    - `<OrbitControls>` enabled (zoom, pan, rotate)
    - `<SceneLighting>`: AmbientLight (0.4) + DirectionalLight (0.8)
    - `<gridHelper>` trên mặt XZ
    - `<axesHelper>` scale 10
  - **DoD:** 3D canvas renders; orbit controls functional; grid visible

- [ ] **P2-T05: Axes Labels & Reference Grid**
  - `<AxesLabels>`: Billboard text cho "Epoch →", "Accuracy ↑", "Loss →"
  - Tick marks + giá trị trên mỗi trục (0, 0.2, 0.4, ..., 1.0 cho Accuracy)
  - Semi-transparent planes cho mặt XY, XZ (optional)
  - **DoD:** Labels đọc được từ mọi góc camera; không bị clip khi zoom

- [ ] **P2-T06: Run Node Component**
  - `<RunNode>`: nhận prop `run: Run`
  - Render `<Sphere>` tại vị trí `(x, y, z)` từ `useNodePosition(run)`
  - Màu sắc: `getStatusColor(run.status)`
  - Kích thước: `getNodeSize(run.final_accuracy)` (range 0.15 – 0.5)
  - Material: `MeshStandardMaterial` + emissive khi selected
  - **DoD:** Single sphere renders đúng vị trí; màu thay đổi theo status

- [ ] **P2-T07: Run Nodes Collection & Data Binding**
  - `<RunNodes>`: fetch runs từ API → map thành `<RunNode>` components
  - Coordinate mapper: `coordinate-mapper.ts`
    - X = `(run.final_epoch / max_epoch_across_runs) * SCALE_X`
    - Y = `run.final_accuracy * SCALE_Y`
    - Z = `(run.final_loss / max_loss_across_runs) * SCALE_Z`
  - Handle empty state (no runs)
  - **DoD:** Tất cả runs từ API hiển thị đúng vị trí trong 3D; ≥ 20 nodes render mượt

- [ ] **P2-T08: Node Interaction — Click & Hover**
  - Raycasting: `onClick` trên `<RunNode>` → `useRunStore.selectRun(id)`
  - Hover: `onPointerOver` → change cursor, show tooltip (Billboard HTML)
  - Visual feedback: selected node → emissive glow (pulsing animation)
  - **DoD:** Click node → `selectedRunId` updates trong Zustand; hover → tooltip visible

- [ ] **P2-T09: Inspector Panel**
  - `<InspectorPanel>`: subscribe `useRunStore.selectedRunId`
  - Hiển thị:
    - Run name, status badge, created_at
    - Hyperparams table (key-value pairs)
    - Final metrics (accuracy, loss, val_loss)
    - Mini line chart: accuracy & loss over epochs (simple SVG or recharts)
  - Empty state khi chưa select run
  - **DoD:** Click node → panel hiển thị đúng data; chart renders epoch timeline

- [ ] **P2-T10: Camera Fly-to Animation**
  - `<CameraController>`: subscribe `useCameraStore.cameraTarget`
  - Khi target thay đổi: animate camera position → offset từ node position
  - Sử dụng `@react-spring/three` hoặc manual lerp trong `useFrame`
  - Giữ camera nhìn vào node (lookAt target)
  - **DoD:** Select node → camera smooth transition tới node; không jump

---

### Phase 3: AI Copilot & Context Integration

> **Mục tiêu:** Chat interface hoạt động; AI trả lời dựa trên context thực nghiệm; response có structured actions (highlight, focus).

#### Tasks

- [ ] **P3-T01: LLM Client Setup**
  - Install `google-generativeai` (Gemini) hoặc `openai` SDK
  - Tạo `config.py`: load API key từ `.env` (`LLM_API_KEY`, `LLM_MODEL`)
  - Tạo thin wrapper: `async def call_llm(messages: list[dict]) -> str`
  - **DoD:** Call LLM với test prompt → nhận response thành công

- [ ] **P3-T02: Context Builder**
  - `context_builder.py`:
    - `build_runs_summary(runs)`: tạo text tóm tắt tất cả runs

      ```
      Experiment: MNIST-CNN-v1 (10 runs)
      Best accuracy: run-003 (0.9845), Worst: run-007 (0.7123)
      Average accuracy: 0.8932 ± 0.067
      Hyperparams range: lr=[0.0001, 0.1], batch_size=[16, 128]

      Run details:
      - run-001: lr=0.001, bs=32, epochs=10 → acc=0.9567, loss=0.145
      - run-002: lr=0.01, bs=64, epochs=15 → acc=0.9234, loss=0.267
      ...
      ```

    - `build_run_detail(run)`: chi tiết 1 run (all epochs metrics)
    - `build_comparison(run_a, run_b)`: side-by-side
  - **DoD:** Functions output clean, structured text; unit tested

- [ ] **P3-T03: Prompt Template Engine**
  - `prompt_templates.py`:
    - **System prompt**: Vai trò AI, output format yêu cầu, cách xử lý actions
    - **Few-shot examples**: 2-3 ví dụ Q&A với structured JSON response
    - Template:

      ```
      You are an ML Experiment Copilot. You have access to experiment data.

      IMPORTANT: Your response MUST be valid JSON with this structure:
      {
        "message": "Your answer in Markdown...",
        "actions": [
          {"type": "highlight", "run_ids": ["run-003"]},
          {"type": "camera_focus", "target_run_id": "run-003"}
        ]
      }

      EXPERIMENT CONTEXT:
      {context}

      USER QUESTION: {question}
      ```
  - **DoD:** Templates generate valid prompts; context injection works

- [ ] **P3-T04: Response Parser**
  - `response_parser.py`:
    - Parse LLM output → extract JSON
    - Handle cases: pure JSON, JSON trong markdown code block, fallback text-only
    - Validate `actions` array: known types (`highlight`, `camera_focus`, `compare`)
    - Validate `run_ids` tồn tại trong database
  - **DoD:** Parser handles all 3 format cases; invalid run_ids filtered out

- [ ] **P3-T05: Copilot API Endpoint**
  - `POST /api/copilot/chat`:
    - Request: `{ "message": str, "experiment_id": int (optional) }`
    - Flow: fetch runs → build context → inject prompt → call LLM → parse → respond
    - Response: `CopilotResponse` schema (message + actions + metadata)
  - Error handling: LLM timeout → fallback message; invalid response → retry once
  - **DoD:** Endpoint returns structured JSON; 3 test queries return meaningful answers

- [ ] **P3-T06: Chat Panel UI**
  - `<ChatPanel>`: message list + input
  - `<ChatMessage>`: render Markdown (react-markdown), differentiate user/AI bubbles
  - `<ChatInput>`: text input + send button + loading indicator
  - `useChatStore`: `messages[]`, `isLoading`, `sendMessage()`
  - **DoD:** Type message → send → loading spinner → AI response rendered

- [ ] **P3-T07: Action Handler (Frontend)**
  - `<ActionHandler>`: subscribe `useChatStore` → khi AI response có actions:
    - `highlight`: dispatch `useRunStore.highlightRuns(run_ids)`
    - `camera_focus`: dispatch `useCameraStore.setTarget(run_id)`
  - RunNode listens: nếu highlighted → add orange emissive ring
  - **DoD:** AI says "best run is run-003" → node run-003 glows + camera flies to it

- [ ] **P3-T08: Copilot Engine Tests**
  - Unit tests cho context builder, prompt templates, response parser
  - Integration test: mock LLM response → verify full pipeline
  - **DoD:** `pytest tests/test_copilot_engine.py` — all green

---

### Phase 4: Dynamic Synchronization & UI Polish

> **Mục tiêu:** Trạng thái đồng bộ hoàn hảo giữa 3 panels. UX mượt mà, professional.

#### Tasks

- [ ] **P4-T01: Cross-Panel State Sync**
  - Kịch bản 1: Click node → Inspector cập nhật + Chat suggest question
  - Kịch bản 2: AI response → Node highlight + Camera focus + Inspector update
  - Kịch bản 3: Sidebar filter → 3D nodes filtered + reset selection
  - Implement via Zustand subscriptions (không prop drilling)
  - **DoD:** Tất cả 3 kịch bản hoạt động; state consistency verified

- [ ] **P4-T02: Sidebar — Experiment & Run List**
  - Experiment dropdown / tabs
  - Run list: name, status badge, final accuracy
  - Click run in sidebar → same effect as click node (select + focus)
  - Search/filter by run name
  - **DoD:** Sidebar interactive; select run from list → node highlighted in 3D

- [ ] **P4-T03: Node Visual Enhancements**
  - Connecting lines giữa các nodes cùng experiment (optional)
  - Particle effect / glow shader cho selected node
  - Smooth appear animation khi data loads (scale from 0 → 1)
  - **DoD:** Nodes có appear animation; selected state visually distinct

- [ ] **P4-T04: 3D Performance Optimization**
  - Implement `<Instances>` (InstancedMesh) cho khi nodes > 100
  - LOD: giảm geometry detail khi camera xa
  - Frustum culling (mặc định trong Three.js, verify enabled)
  - **DoD:** 200 nodes render ≥ 60fps; memory footprint stable

- [ ] **P4-T05: Chat UX Improvements**
  - Streaming response (nếu LLM API hỗ trợ SSE)
  - Suggested questions (quick action buttons):
    - "🏆 Tìm run tốt nhất"
    - "🔍 So sánh run đang chọn"
    - "⚠️ Kiểm tra overfitting"
  - Chat history persistence (localStorage)
  - **DoD:** Quick actions work; streaming visible; history survives page refresh

- [ ] **P4-T06: Error Handling & Loading States**
  - Backend down → friendly error message + retry button
  - LLM API error → fallback message trong chat
  - Loading skeletons cho panels
  - 3D canvas loading → progress indicator
  - **DoD:** Disconnect backend → UI shows error gracefully; no console errors

- [ ] **P4-T07: Responsive Design & Dark Theme**
  - Dark mode (mặc định cho 3D workspace aesthetic)
  - Panels collapsible trên mobile
  - 3D canvas full-screen toggle
  - **DoD:** App looks professional ở 1920x1080 và 768x1024

---

### Phase 5: Testing & Verification

> **Mục tiêu:** End-to-end flow hoạt động hoàn chỉnh. Demo-ready.

#### Tasks

- [ ] **P5-T01: End-to-End Smoke Test**
  - Script tự động:
    1. Start backend (`uvicorn`)
    2. Seed database (hoặc run `train_mnist_demo.py`)
    3. Start frontend (`pnpm dev`)
    4. Verify: `GET /api/runs` returns data
    5. Manual: mở browser → 3D loads → click node → Inspector shows data
    6. Manual: chat "run nào tốt nhất?" → AI responds + node highlights
  - **DoD:** Full flow passes without errors; documented with screenshots

- [ ] **P5-T02: API Integration Tests**
  - Test full CRUD cycle: create experiment → create run → log metrics → query
  - Test copilot endpoint with various intents
  - Test edge cases: empty DB, 100+ runs, malformed requests
  - **DoD:** `pytest` suite passes; covers all endpoints

- [ ] **P5-T03: Frontend Component Tests**
  - Test `coordinate-mapper.ts`: edge cases (0 accuracy, max loss)
  - Test Zustand stores: state transitions
  - Test action handler: mock AI response → verify store updates
  - **DoD:** `pnpm test` passes; ≥ 70% util coverage

- [ ] **P5-T04: Performance Benchmark**
  - Measure: 3D FPS with 50, 100, 200, 500 nodes
  - Measure: API response time (p50, p95)
  - Measure: AI response time (end-to-end)
  - Document results in `docs/performance.md`
  - **DoD:** 200 nodes @ 60fps; API p95 < 200ms; AI e2e < 8s

- [ ] **P5-T05: Demo Script & Documentation**
  - Viết `README.md`: setup instructions, prerequisites, run commands
  - Tạo demo script / walkthrough cho stakeholders
  - Screenshots / screen recording of key flows
  - **DoD:** New developer có thể setup và run trong < 15 phút theo README

---

## 5. Risk Assessment & Technical Constraints

### Risk Matrix

| #   | Rủi ro                                            | Xác suất   | Tác động   | Giải pháp giảm thiểu                                                                                                                     |
| --- | ------------------------------------------------- | ---------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| R1  | **3D Performance Degradation** khi > 200 nodes    | Trung bình | Cao        | Sử dụng `InstancedMesh` thay vì individual meshes; LOD (Level of Detail); Frustum culling; Virtual pagination (chỉ render visible nodes) |
| R2  | **LLM Latency cao** (> 10s per response)          | Cao        | Trung bình | Streaming response (SSE); Cache frequent queries; Giảm context window (top-K runs thay vì all); Show loading skeleton                    |
| R3  | **LLM Output không đúng JSON format**             | Trung bình | Trung bình | Robust parser với multiple fallback strategies; JSON mode (nếu API hỗ trợ); Retry với explicit format reminder; Schema validation        |
| R4  | **CORS / Proxy issues** giữa Vite và FastAPI      | Thấp       | Thấp       | Cấu hình `vite.config.ts` proxy; FastAPI CORS middleware rõ ràng; Document networking setup                                              |
| R5  | **State Desync** giữa 3 panels                    | Trung bình | Cao        | Single source of truth (Zustand); Derived state thay vì duplicated; Unit test state transitions; DevTools middleware                     |
| R6  | **SQLite Concurrency** khi nhiều writes đồng thời | Thấp       | Thấp       | Acceptable cho PoC; Migration path to PostgreSQL documented; WAL mode enabled                                                            |
| R7  | **LLM API Key bị expose** ở frontend              | Thấp       | Cao        | LLM calls ONLY từ backend; API key trong `.env` server-side; Never expose to client bundle                                               |
| R8  | **Three.js Memory Leak** từ undisposed resources  | Trung bình | Trung bình | R3F auto-disposal; `useEffect` cleanup; Monitor với Chrome DevTools Memory tab; Dispose textures/geometries explicitly                   |

### Technical Constraints

| Constraint                | Chi tiết                                                                        |
| ------------------------- | ------------------------------------------------------------------------------- |
| **Database**              | SQLite — single file, phù hợp PoC. Không dùng cho production multi-user.        |
| **LLM Provider**          | Cần API key (Gemini hoặc OpenAI). Free tier có rate limits.                     |
| **Browser Compatibility** | WebGL 2.0 required. Chrome/Edge/Firefox modern. Safari có thể gặp issues.       |
| **Concurrent Users**      | PoC scope: single user. Không thiết kế cho multi-user real-time collaboration.  |
| **Data Scale**            | Thiết kế cho ≤ 500 runs / ≤ 50 epochs per run. Vượt quá cần optimization riêng. |
| **Network**               | Frontend và Backend chạy cùng máy (localhost). Không deploy cloud cho PoC.      |

### Tiêu chí thành công tổng thể (Overall Success Criteria)

```
✅ Backend API hoạt động — CRUD experiments, runs, metrics
✅ Demo training script tạo ≥ 5 runs realistic
✅ 3D Canvas render ≥ 50 nodes @ 60fps
✅ Click node → Inspector Panel hiện đúng data
✅ AI Copilot trả lời ≥ 3 loại truy vấn có context
✅ AI response trigger camera fly-to + node highlight
✅ Full flow E2E: train → log → visualize → query AI — dưới 1 phút demo
```

---

> **Next Step:** Bắt đầu Phase 1 — Foundation & MLOps Engine Setup.
>
> Ước tính tổng thời gian: **11–16 ngày** (1 developer) hoặc **7–10 ngày** (2 developers parallel).
