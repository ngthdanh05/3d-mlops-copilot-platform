# 🚀 PLAN.md — 3D-MLOps Copilot Platform

> **Nền tảng quản lý thực nghiệm học máy trong không gian 3D tích hợp trợ lý AI**
>
> Version: `1.1.0-draft` · Created: 2026-11-06 · Updated: 2026-11-10 · Author: Principal System Architect
>
> Bản 1.1 thống nhất với README: không gian 3D theo siêu tham số và trợ lý AI dùng tool calling.
> Quy ước phát triển nằm ở `CONTRIBUTING.md`.

---

## Tiến độ hiện tại

Cập nhật 2026-11-10, đối chiếu với code. ✅ là đã xong, 🚧 là làm một phần, ô trống là chưa làm.

| Phase | ✅ Xong | 🚧 Một phần | Chưa làm |
| --- | --- | --- | --- |
| 1. Backend & MLOps | 7 | 0 | 0 |
| 2. Không gian 3D | 11 | 1 | 0 |
| 3. AI Copilot | 8 | 0 | 0 |
| 4. Đồng bộ & hoàn thiện | 7 | 0 | 0 |
| 5. Kiểm thử & demo | 4 | 1 | 0 |
| **Tổng (39 task)** | **37** | **2** | **0** |

Việc còn lại, xếp theo thứ tự nên làm:

| # | Task | Trạng thái | Còn thiếu |
| --- | --- | --- | --- |
| 1 | Thang màu (phát sinh) | Chưa làm | Các run tốt khó phân biệt khi có nhiều run xấu, thấy rõ ở `real-mnist-mlp` |
| 2 | P2-T09 Inspector Panel | 🚧 | Biểu đồ accuracy/loss theo epoch |
| 3 | P5-T04 Benchmark | 🚧 | AI e2e phải < 8 s. Đã bớt vòng gọi LLM; lần đo chính thức trung vị 7,63 s, chậm nhất 11,31 s do Gemini chậm |

---

## Mục lục

- [Tiến độ hiện tại](#tiến-độ-hiện-tại)

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
> Phạm vi PoC **không** bao gồm: xác thực người dùng, multi-tenant, model registry, hoặc deployment pipeline. Các tính năng này thuộc roadmap post-MVP. CI (lint và test cho mỗi PR) đã nằm trong phạm vi.

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
│  │  • runs table                       │◄───┤  • Query tools (service)     │  │
│  │  • metrics table                    │    │  • System prompt             │  │
│  │  (hyperparams: cột JSON của runs)   │    │  • LLM client (tool calling) │  │
│  └─────────────────────────────────────┘    │  • UI action collector       │  │
│                                             │    (actions cho frontend)    │  │
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
[FastAPI]      ──câu hỏi + tools──► [LLM API] ──tool calls──► [Service layer] ──kết quả──► [LLM API]
[FastAPI]      ──message + actions──► [Frontend] ──Zustand store──► [highlight + camera + chat bubble]
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
│ hyperparams  │ JSON     │ {"learning_rate": 0.001, ...}  │
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
| TR-04 | Lấy danh sách Runs      | `GET /api/runs` (lọc bằng `?experiment_id=X`) — trả về list runs + final metrics |
| TR-05 | Lấy chi tiết Run        | `GET /api/runs/{id}` — hyperparams + full metrics timeline             |
| TR-06 | Cập nhật trạng thái Run | `PUT /api/runs/{id}` — đánh dấu "completed" / "failed"                 |

### 2.2 3D Spatial Workspace

#### Hệ tọa độ 3D (Coordinate Mapping)

**Vị trí thể hiện đầu vào (siêu tham số), hình thức thể hiện kết quả.** Nhờ vậy người dùng thấy được vùng cấu hình nào cho kết quả tốt và vùng nào chưa được thử.

```
        Y (batch_size, log2)
        ▲
        │       ● run tốt (màu sáng, cầu to)
        │
        │              ○ vùng chưa thử
        │
        │  ● run overfit
        ├──────────────────────► X (learning_rate, log10)
       ╱
      ╱
     ▼
     Z (dropout / epochs / key số khác)
```

| Trục | Mặc định        | Ánh xạ                                                                       |
| ---- | --------------- | ---------------------------------------------------------------------------- |
| X    | `learning_rate` | `normalize(log10(value), min, max) * SCALE_X`                                |
| Y    | `batch_size`    | `normalize(log2(value), min, max) * SCALE_Y`                                 |
| Z    | Key số còn lại  | Ưu tiên `dropout`, rồi `epochs`, rồi key khác; lấy key đầu có ≥ 2 giá trị khác nhau. Không có thì Z phẳng |

Quy tắc:

- Người dùng chọn được trục từ mọi key dạng số trong `hyperparams` và mọi metric cuối.
- Key không phải số (`optimizer`, `hidden_layers`) chưa làm trục được ở PoC, nhưng vẫn hiện trong Inspector Panel.
- Run thiếu key đang dùng làm trục được đặt ở mặt phẳng "không xác định" và vẽ mờ.
- Không dùng epoch, accuracy và loss làm 3 trục cùng lúc: accuracy và loss gần như tỉ lệ nghịch nên các điểm dồn trên một đường.

#### Visual Encoding của Node

| Thuộc tính     | Encoding                                                              |
| -------------- | --------------------------------------------------------------------- |
| **Vị trí**     | Siêu tham số theo 3 trục đang chọn                                    |
| **Màu sắc**    | `final_val_accuracy` (hoặc `final_accuracy`), thang màu liên tục có chú giải |
| **Kích thước** | `final_val_loss`: loss cao → cầu nhỏ                                  |
| **Viền / icon**| Trạng thái: ● completed · ◐ running · ✕ failed                        |
| **Phát sáng**  | Emissive glow khi node được selected hoặc AI highlight                |
| **Label**      | Billboard text hiển thị `run_name` khi hover                          |

#### Tương tác 3D

| ID    | Tương tác          | Chi tiết kỹ thuật                                                    |
| ----- | ------------------ | -------------------------------------------------------------------- |
| 3D-01 | Orbit Controls     | Zoom (scroll), Pan (right-click drag), Rotate (left-click drag)      |
| 3D-02 | Raycasting Click   | `onClick` trên mesh → dispatch `selectRun(runId)` vào Zustand        |
| 3D-03 | Hover Tooltip      | `onPointerOver` → hiện billboard label với run_name + accuracy       |
| 3D-04 | Camera Fly-to      | Animate camera position smooth tới node khi selected (GSAP / spring) |
| 3D-05 | Grid & Axes Helper | Lưới tham chiếu + labels trục X, Y, Z                                |
| 3D-06 | Node Filtering     | Filter nodes theo status, accuracy range (UI controls bên ngoài)     |
| 3D-07 | Axis Selector      | Chọn key cho từng trục X, Y, Z; node di chuyển theo lựa chọn mới     |

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

Trợ lý dùng **tool calling**. LLM không nhận toàn bộ dữ liệu trong prompt và không tự đưa ra số liệu: mọi con số đều lấy qua tool, và tool gọi service layer. Tên và tham số của từng tool xem ở mục "Thiết kế trợ lý AI" trong README.

```
Câu hỏi ──► Engine ──► LLM (kèm danh sách tool)
              ▲              │
              │              ▼ tool call
              │        ┌───────────────┐      ┌───────────────┐
              ├────────┤  Query tools  ├─────►│ Service layer │
              │ kết quả└───────────────┘      └───────────────┘
              │        ┌───────────────┐
              ├────────┤   UI tools    │  (không chạm DB, chỉ ghi nhận action)
              │        └───────────────┘
              ▼
   { message, actions } ──► Frontend ──► Zustand store
```

| Intent | Tool truy vấn                                                    | Action trên giao diện            |
| ------ | ---------------------------------------------------------------- | -------------------------------- |
| AI-01  | `find_best_runs`                                                 | `highlight_runs`, `focus_camera` |
| AI-02  | `find_runs_by_name`, `compare_runs`                              | `highlight_runs`                 |
| AI-03  | `find_runs_by_name`, `detect_overfitting`, `get_run`             | `focus_camera`, `open_inspector` |
| AI-04  | `list_experiments`, `find_best_runs`, thêm `summarize_experiment` khi làm task này | Không bắt buộc |
| AI-05  | `find_best_runs`, `compare_runs`                                 | `highlight_runs`                 |

Quy tắc:

- Phép tính số liệu (so sánh, phát hiện overfitting) làm bằng code, không để LLM tự tính.
- Action sinh ra từ UI tool, không tách từ văn bản của LLM. `run_id` phải tồn tại trong database trước khi trả về frontend.
- Giới hạn số vòng gọi tool trong một câu hỏi để tránh lặp vô hạn.
- Nhà cung cấp LLM: Gemini (`gemini-3.5-flash-lite`, gói miễn phí), mọi chi tiết nằm trong `llm_client.py`.

#### Structured Response Format

`POST /api/copilot/chat` trả về JSON. ID của run là số nguyên:

```json
{
  "message": "Run-007 có val_accuracy cao nhất (0.9644)...",
  "actions": [
    { "type": "highlight_runs", "run_ids": [7] },
    { "type": "focus_camera", "run_id": 7 },
    { "type": "open_inspector", "run_id": 7 }
  ]
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
├── CONTRIBUTING.md                    # Quy ước phát triển     
├── CLAUDE.md                          # Quy ước code cho dự án
├── .github/                           # CI, mẫu PR
│
├── backend/                           # ═══ Python FastAPI Backend ═══
│   ├── pyproject.toml                 # Python dependencies (uv/pip)
│   ├── .env.example                   # Template biến môi trường
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
│   │   │       ├── engine.py          # Vòng lặp tool calling
│   │   │       ├── llm_client.py      # Wrapper LLM, đổi nhà cung cấp tại đây
│   │   │       ├── query_tools.py     # Tool truy vấn, gọi service layer
│   │   │       ├── ui_tools.py        # Tool điều khiển giao diện (actions)
│   │   │       ├── tool_base.py       # Kiểu dùng chung cho các tool
│   │   │       └── prompts.py         # System prompt
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
│   │   │       └── ChatInput.tsx      # Input + send button
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
│   │       └── color-utils.ts         # Metric → thang màu, status → viền
│   │
│   └── tests/
│       ├── components/
│       │   └── RunNode.test.tsx
│       └── utils/
│           └── coordinate-mapper.test.ts
│
└── docs/
    ├── PLAN.md                        # File kế hoạch này
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

- [x] ✅ **P1-T01: Khởi tạo Backend Project**
  - Tạo `backend/` directory, `pyproject.toml` với dependencies
  - Setup FastAPI app skeleton (`main.py`, `config.py`)
  - Cấu hình CORS middleware cho `localhost:5173` (Vite dev server) / `localhost:3000`
  - **DoD:** `uvicorn app.main:app --reload` khởi chạy, `/docs` (Swagger) accessible

- [x] ✅ **P1-T02: Database Models & Setup**
  - Định nghĩa SQLAlchemy models: `Experiment`, `Run`, `Metric`
  - Tạo `database.py` với async SQLite engine
  - Auto-create tables on startup (`metadata.create_all`)
  - **DoD:** Database file `mlops.db` được tạo; tables verify qua `sqlite3` CLI

- [x] ✅ **P1-T03: Pydantic Schemas**
  - Tạo request/response schemas cho Experiment, Run, Metric
  - Validation rules: `learning_rate > 0`, `0 ≤ accuracy ≤ 1`, `epochs ≥ 1`
  - **DoD:** Schemas importable, JSON serialization/deserialization hoạt động

- [x] ✅ **P1-T04: CRUD API Endpoints**
  - `POST /api/experiments` — Tạo experiment
  - `GET /api/experiments` — List experiments
  - `POST /api/runs` — Tạo run (với hyperparams JSON)
  - `GET /api/runs` — List runs (filter by experiment_id, include final metrics)
  - `GET /api/runs/{id}` — Chi tiết run + full metrics timeline
  - `PUT /api/runs/{id}` — Update status
  - `POST /api/runs/{id}/metrics` — Log metrics cho 1 epoch
  - **DoD:** Tất cả endpoints test thành công qua Swagger UI; HTTP status codes đúng

- [x] ✅ **P1-T05: Demo Training Script**
  - Viết `scripts/train_mnist_demo.py`:
    - Train sklearn `MLPClassifier` hoặc PyTorch CNN trên MNIST (subset nhỏ)
    - Mỗi epoch: call `POST /api/runs/{id}/metrics` với accuracy, loss, val_loss
    - Kết thúc: `PUT /api/runs/{id}` → status = "completed"
  - Chạy 5-10 lần với hyperparams khác nhau (vary `lr`, `batch_size`, `epochs`)
  - **DoD:** Database có ≥ 5 runs, mỗi run có ≥ 5 epochs metrics; `GET /api/runs` trả về đúng data

- [x] ✅ **P1-T06: Seed Data Utility**
  - Viết `utils/seed_data.py`: tạo synthetic runs (không cần train thật) cho dev nhanh
  - Generate 20-50 runs với realistic-looking metrics curves
  - **DoD:** Chạy seed script → DB populated; frontend dev có thể dùng ngay

- [x] ✅ **P1-T07: Unit Tests cho Tracking API**
  - Test CRUD operations với in-memory SQLite
  - Test validation (invalid hyperparams, missing fields)
  - **DoD:** `pytest tests/test_tracking_api.py` — all green, ≥ 80% coverage cho routers

---

### Phase 2: 3D Scene & Canvas Development

> **Mục tiêu:** Frontend hiển thị không gian 3D với các Run Nodes, tương tác được (orbit, click, hover). Inspector Panel hiển thị chi tiết khi click node.

#### Tasks

- [x] ✅ **P2-T01: Khởi tạo Frontend Project**
  - `pnpm create vite frontend --template react-ts` (Vite + React SPA, TypeScript)
  - Install: `three`, `@react-three/fiber`, `@react-three/drei`, `zustand`, `swr`
  - Setup Tailwind CSS: `tailwind.config.js`, `postcss.config.js`, `src/index.css`
  - Cấu hình API reverse proxy trong `vite.config.ts` (`/api` -> `http://localhost:8000`)
  - **DoD:** `pnpm dev` → Vite dev server chạy tại `localhost:5173`; khởi động tức thì, blank page renders

- [x] ✅ **P2-T02: TypeScript Types & API Client**
  - Định nghĩa `types.ts`: `Run`, `Metric`, `Experiment`, `ChatMessage`, `CopilotResponse`
  - Tạo `lib/api.ts`: base URL config, `fetchRuns()`, `fetchRunDetail(id)`
  - **DoD:** `useRuns()` hook trả về data từ backend (proxy qua `vite.config.ts` server.proxy)

- [x] ✅ **P2-T03: Layout Workspace (3-Panel)**
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

- [x] ✅ **P2-T04: 3D Scene Foundation**
  - Tạo `Scene.tsx` với R3F `<Canvas>`:
    - Camera: PerspectiveCamera, position `[15, 10, 15]`, fov 60
    - `<OrbitControls>` enabled (zoom, pan, rotate)
    - `<SceneLighting>`: AmbientLight (0.4) + DirectionalLight (0.8)
    - `<gridHelper>` trên mặt XZ
    - `<axesHelper>` scale 10
  - **DoD:** 3D canvas renders; orbit controls functional; grid visible

- [x] ✅ **P2-T05: Axes Labels & Reference Grid**
  - `<AxesLabels>`: Billboard text theo tên key của trục đang chọn (mặc định `learning_rate`, `batch_size`, `dropout`)
  - Tick marks + giá trị trên mỗi trục, đúng thang đang dùng (log hoặc tuyến tính)
  - Semi-transparent planes cho mặt XY, XZ (optional)
  - **DoD:** Labels đọc được từ mọi góc camera; không bị clip khi zoom

- [x] ✅ **P2-T06: Run Node Component**
  - `<RunNode>`: nhận prop `run: Run`
  - Render `<Sphere>` tại vị trí `(x, y, z)` từ `useNodePosition(run)`
  - Màu sắc: thang màu theo `final_val_accuracy` (fallback `final_accuracy`)
  - Kích thước: theo `final_val_loss`, loss cao → cầu nhỏ (range 0.15 – 0.5)
  - Viền / icon theo `run.status`
  - Material: `MeshStandardMaterial` + emissive khi selected
  - **DoD:** Single sphere renders đúng vị trí; màu theo metric, viền theo status

- [x] ✅ **P2-T07: Run Nodes Collection & Data Binding**
  - `<RunNodes>`: fetch runs từ API → map thành `<RunNode>` components
  - Coordinate mapper: `coordinate-mapper.ts`
    - X = `normalize(log10(learning_rate)) * SCALE_X`
    - Y = `normalize(log2(batch_size)) * SCALE_Y`
    - Z = `normalize(key số còn lại) * SCALE_Z`, theo quy tắc ở mục 2.2
    - Run thiếu key đang dùng làm trục → mặt phẳng "không xác định", vẽ mờ
  - Handle empty state (no runs)
  - **DoD:** Tất cả runs từ API hiển thị đúng vị trí trong 3D; ≥ 20 nodes render mượt

- [x] ✅ **P2-T08: Node Interaction — Click & Hover**
  - Raycasting: `onClick` trên `<RunNode>` → `useRunStore.selectRun(id)`
  - Hover: `onPointerOver` → change cursor, show tooltip (Billboard HTML)
  - Visual feedback: selected node → emissive glow (pulsing animation)
  - **DoD:** Click node → `selectedRunId` updates trong Zustand; hover → tooltip visible

- [ ] 🚧 **P2-T09: Inspector Panel** (đã có thông tin run; còn biểu đồ accuracy/loss theo epoch)
  - `<InspectorPanel>`: subscribe `useRunStore.selectedRunId`
  - Hiển thị:
    - Run name, status badge, created_at
    - Hyperparams table (key-value pairs)
    - Final metrics (accuracy, loss, val_loss)
    - Mini line chart: accuracy & loss over epochs (simple SVG or recharts)
  - Empty state khi chưa select run
  - **DoD:** Click node → panel hiển thị đúng data; chart renders epoch timeline

- [x] ✅ **P2-T10: Camera Fly-to Animation**
  - `<CameraController>`: subscribe `useCameraStore.cameraTarget`
  - Khi target thay đổi: animate camera position → offset từ node position
  - Sử dụng `@react-spring/three` hoặc manual lerp trong `useFrame`
  - Giữ camera nhìn vào node (lookAt target)
  - **DoD:** Select node → camera smooth transition tới node; không jump

- [x] ✅ **P2-T11: Chọn trục 3D**
  - Dropdown cho X, Y, Z, liệt kê key dạng số trong `hyperparams` và các metric cuối
  - Đổi trục → node di chuyển, label và tick cập nhật
  - **DoD:** Đổi trục → mọi node về đúng vị trí mới; key không phải số không xuất hiện trong danh sách

- [x] ✅ **P2-T12: Endpoint xoá (Should)**
  - `DELETE /api/experiments/{id}` và `DELETE /api/runs/{id}`, tận dụng cascade đã có ở tầng database
  - **DoD:** Xoá xong trả 204; id không tồn tại trả 404; có test

---

### Phase 3: AI Copilot & Context Integration

> **Mục tiêu:** Chat interface hoạt động; AI trả lời dựa trên context thực nghiệm; response có structured actions (highlight, focus).

#### Tasks

- [x] ✅ **P3-T01: LLM Client Setup**
  - Chốt nhà cung cấp, cài SDK tương ứng
  - Tạo `config.py`: load API key từ `.env` (`LLM_API_KEY`, `LLM_MODEL`)
  - Tạo `llm_client.py`: một interface hỗ trợ tool calling, kèm bản giả (fake) để test không tốn API
  - **DoD:** Gọi LLM với một tool mẫu → nhận được tool call đúng tên và tham số

- [x] ✅ **P3-T02: Query Tools**
  - `query_tools.py`: `list_experiments`, `find_best_runs`, `find_runs_by_name`, `get_run`, `compare_runs`, `detect_overfitting`
  - Tool gọi service layer, không truy vấn database trực tiếp
  - `detect_overfitting`: tính khoảng cách train/val qua các epoch bằng code
  - **DoD:** Mỗi tool có unit test với dữ liệu seed; run không tồn tại trả lỗi rõ ràng cho LLM

- [x] ✅ **P3-T03: UI Action Tools**
  - `ui_tools.py`: `highlight_runs`, `focus_camera`, `open_inspector`
  - Tool chỉ ghi nhận action, không chạm database ngoài việc kiểm tra `run_id` tồn tại
  - **DoD:** `run_id` không tồn tại bị loại khỏi `actions`; có unit test

- [x] ✅ **P3-T04: System Prompt & Schemas**
  - `prompts.py`: vai trò của trợ lý, yêu cầu mọi con số phải lấy từ tool, ngôn ngữ trả lời
  - `schemas/copilot.py`: `ChatRequest`, `ChatResponse`, các kiểu `Action`
  - **DoD:** Schema khớp ví dụ ở mục 2.3; OpenAPI hiển thị đúng

- [x] ✅ **P3-T05: Copilot API Endpoint**
  - `POST /api/copilot/chat`:
    - Request: `{ "message": str, "experiment_id": int (optional) }`
    - Flow: gửi câu hỏi + danh sách tool → chạy tool call → lặp đến khi LLM trả lời (có giới hạn số vòng) → gom actions
    - Response: `{ message, actions }`
  - Error handling: LLM timeout hoặc lỗi → thông báo thân thiện, không trả 500 thô
  - **DoD:** 3 loại câu hỏi (best run, compare, diagnose) trả lời đúng số liệu trong database

- [x] ✅ **P3-T06: Chat Panel UI**
  - `<ChatPanel>`: message list + input
  - `<ChatMessage>`: render Markdown (react-markdown), differentiate user/AI bubbles
  - `<ChatInput>`: text input + send button + loading indicator
  - `useChatStore`: `messages[]`, `isLoading`, `sendMessage()`
  - **DoD:** Type message → send → loading spinner → AI response rendered

- [x] ✅ **P3-T07: Action Handler (Frontend)**
  - `applyActions` trong `hooks/useCopilot.ts`: khi AI response có actions:
    - `highlight_runs`: dispatch `useRunStore.highlightRuns(run_ids)`
    - `focus_camera`: dispatch `useCameraStore.setTarget(run_id)`
    - `open_inspector`: dispatch `useRunStore.selectRun(run_id)`
  - RunNode listens: nếu highlighted → add orange emissive ring
  - **DoD:** AI says "best run is run-003" → node run-003 glows + camera flies to it

- [x] ✅ **P3-T08: Copilot Engine Tests**
  - Unit tests cho query tools, UI tools và vòng lặp engine
  - Integration test: fake LLM trả tool call → kiểm tra toàn bộ pipeline
  - Bộ câu hỏi kiểm tra độ chính xác của AI: đối chiếu số trong câu trả lời với database
  - **DoD:** `pytest tests/test_copilot_engine.py` — all green

---

### Phase 4: Dynamic Synchronization & UI Polish

> **Mục tiêu:** Trạng thái đồng bộ hoàn hảo giữa 3 panels. UX mượt mà, professional.

#### Tasks

- [x] ✅ **P4-T01: Cross-Panel State Sync**
  - Kịch bản 1: Click node → Inspector cập nhật + Chat suggest question
  - Kịch bản 2: AI response → Node highlight + Camera focus + Inspector update
  - Kịch bản 3: Sidebar filter → 3D nodes filtered + reset selection
  - Implement via Zustand subscriptions (không prop drilling)
  - **DoD:** Tất cả 3 kịch bản hoạt động; state consistency verified

- [x] ✅ **P4-T02: Sidebar — Experiment & Run List**
  - Experiment dropdown / tabs
  - Run list: name, status badge, final accuracy
  - Click run in sidebar → same effect as click node (select + focus)
  - Search/filter by run name
  - **DoD:** Sidebar interactive; select run from list → node highlighted in 3D

- [x] ✅ **P4-T03: Node Visual Enhancements**
  - Connecting lines giữa các nodes cùng experiment (optional)
  - Glow cho selected node (sprite phát sáng, nhịp nhẹ)
  - Smooth appear animation khi data loads (scale from 0 → 1)
  - **DoD:** Nodes có appear animation; selected state visually distinct

- [x] ✅ **P4-T04: 3D Performance Optimization**
  - Implement `<Instances>` (InstancedMesh) cho khi nodes > 100
  - LOD: giảm geometry detail khi camera xa
  - Frustum culling (mặc định trong Three.js, verify enabled)
  - **DoD:** 200 nodes render ≥ 60fps; memory footprint stable

- [x] ✅ **P4-T05: Chat UX Improvements**
  - Streaming response (nếu LLM API hỗ trợ SSE)
  - Suggested questions (quick action buttons):
    - "🏆 Tìm run tốt nhất"
    - "🔍 So sánh run đang chọn"
    - "⚠️ Kiểm tra overfitting"
  - Chat history persistence (localStorage)
  - **DoD:** Quick actions work; streaming visible; history survives page refresh

- [x] ✅ **P4-T06: Error Handling & Loading States**
  - Backend down → friendly error message + retry button
  - LLM API error → fallback message trong chat
  - Loading skeletons cho panels
  - 3D canvas loading → progress indicator
  - **DoD:** Disconnect backend → UI shows error gracefully; no console errors

- [x] ✅ **P4-T07: Responsive Design & Dark Theme**
  - Dark mode (mặc định cho 3D workspace aesthetic)
  - Panels collapsible trên mobile
  - 3D canvas full-screen toggle
  - **DoD:** App looks professional ở 1920x1080 và 768x1024

---

### Phase 5: Testing & Verification

> **Mục tiêu:** End-to-end flow hoạt động hoàn chỉnh. Demo-ready.

#### Tasks

- [x] ✅ **P5-T01: End-to-End Smoke Test** (`backend/scripts/smoke_test.py`, ảnh ở `docs/screenshots/`)
  - Script tự động:
    1. Start backend (`uvicorn`)
    2. Seed database (hoặc run `train_mnist_demo.py`)
    3. Start frontend (`pnpm dev`)
    4. Verify: `GET /api/runs` returns data
    5. Manual: mở browser → 3D loads → click node → Inspector shows data
    6. Manual: chat "run nào tốt nhất?" → AI responds + node highlights
  - **DoD:** Full flow passes without errors; documented with screenshots

- [x] ✅ **P5-T02: API Integration Tests** (`backend/tests/test_edge_cases.py`)
  - Test full CRUD cycle: create experiment → create run → log metrics → query
  - Test copilot endpoint with various intents
  - Test edge cases: empty DB, 100+ runs, malformed requests
  - **DoD:** `pytest` suite passes; covers all endpoints

- [x] ✅ **P5-T03: Frontend Component Tests**
  - Test `coordinate-mapper.ts`: edge cases (0 accuracy, max loss)
  - Test Zustand stores: state transitions
  - Test action handler: mock AI response → verify store updates
  - **DoD:** `pnpm test` passes; ≥ 70% util coverage

- [ ] 🚧 **P5-T04: Performance Benchmark** (đã đo, FPS và API đạt. AI đã giảm còn 2 vòng gọi LLM mỗi câu: 1,9–3,6 s khi Gemini tải thấp, nhưng 6–11 s khi Gemini chậm, nên chưa đảm bảo < 8 s. Xem `docs/performance.md`)
  - Measure: 3D FPS with 50, 100, 200, 500 nodes
  - Measure: API response time (p50, p95)
  - Measure: AI response time (end-to-end)
  - Document results in `docs/performance.md`
  - **DoD:** 200 nodes @ 60fps; API p95 < 200ms; AI e2e < 8s

- [x] ✅ **P5-T05: Demo Script & Documentation** (`docs/DEMO.md`)
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
| R2  | **LLM Latency cao** (> 10s per response)          | Cao        | Trung bình | Streaming response (SSE); Cache frequent queries; Giới hạn số vòng tool và kích thước kết quả tool (top-K); Show loading skeleton                    |
| R3  | **Tool call sai** (sai tên, sai tham số, lặp vô hạn) | Trung bình | Trung bình | Validate tham số bằng schema; trả lỗi rõ ràng để LLM tự sửa; giới hạn số vòng gọi tool; `run_id` được kiểm tra trước khi trả về frontend |
| R4  | **CORS / Proxy issues** giữa Vite và FastAPI      | Thấp       | Thấp       | Cấu hình `vite.config.ts` proxy; FastAPI CORS middleware rõ ràng; Document networking setup                                              |
| R5  | **State Desync** giữa 3 panels                    | Trung bình | Cao        | Single source of truth (Zustand); Derived state thay vì duplicated; Unit test state transitions; DevTools middleware                     |
| R6  | **SQLite Concurrency** khi nhiều writes đồng thời | Thấp       | Thấp       | Acceptable cho PoC; Migration path to PostgreSQL documented; WAL mode enabled                                                            |
| R7  | **LLM API Key bị expose** ở frontend              | Thấp       | Cao        | LLM calls ONLY từ backend; API key trong `.env` server-side; Never expose to client bundle                                               |
| R8  | **Three.js Memory Leak** từ undisposed resources  | Trung bình | Trung bình | R3F auto-disposal; `useEffect` cleanup; Monitor với Chrome DevTools Memory tab; Dispose textures/geometries explicitly                   |

### Technical Constraints

| Constraint                | Chi tiết                                                                        |
| ------------------------- | ------------------------------------------------------------------------------- |
| **Database**              | SQLite — single file, phù hợp PoC. Không dùng cho production multi-user.        |
| **LLM Provider**          | Cần API key Gemini. Free tier có rate limits, quota tính theo project.                     |
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
✅ AI Copilot trả lời ≥ 3 loại truy vấn bằng số liệu lấy qua tool
✅ AI response trigger camera fly-to + node highlight
✅ Full flow E2E: train → log → visualize → query AI — dưới 1 phút demo
```

---

> **Next Step:** Xem bảng việc còn lại ở mục Tiến độ hiện tại.
>
> Ước tính tổng thời gian: **11–16 ngày** (1 developer) hoặc **7–10 ngày** (2 developers parallel).
