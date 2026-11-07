# 3D-MLOps Copilot Platform

> Nền tảng quản lý thực nghiệm học máy (ML experiment tracking) trong **không gian 3D**, tích hợp **trợ lý AI** giúp bạn tìm, so sánh và chẩn đoán các lần huấn luyện mô hình.

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-async-003B57?logo=sqlite&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![Three.js](https://img.shields.io/badge/React_Three_Fiber-3D-000000?logo=three.js&logoColor=white)
![Status](https://img.shields.io/badge/trạng_thái-PoC_·_Phase_1_xong-orange)

---

## Mục lục

- [Dự án này làm gì?](#dự-án-này-làm-gì)
- [Tính năng](#tính-năng)
- [Kiến trúc](#kiến-trúc)
- [Công nghệ sử dụng](#công-nghệ-sử-dụng)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Bắt đầu nhanh](#bắt-đầu-nhanh)
- [Tạo dữ liệu mẫu](#tạo-dữ-liệu-mẫu)
- [Tài liệu API](#tài-liệu-api)
- [Ghi log từ script huấn luyện của bạn](#ghi-log-từ-script-huấn-luyện-của-bạn)
- [Cấu hình](#cấu-hình)
- [Kiểm thử](#kiểm-thử)
- [Lộ trình phát triển](#lộ-trình-phát-triển)
- [Quy ước đóng góp](#quy-ước-đóng-góp)

---

## Dự án này làm gì?

Khi huấn luyện mô hình học máy, ta thường chạy **rất nhiều lần** (gọi là các *run*) với các bộ siêu tham số khác nhau: learning rate, batch size, số epoch... Theo dõi xem run nào tốt nhất, run nào bị overfit, run nào bị lỗi trong một bảng số liệu dài là việc mệt mỏi.

**3D-MLOps Copilot** giải quyết việc đó bằng ba thành phần:

| | Thành phần | Ý nghĩa |
|---|---|---|
| 📊 | **Theo dõi (Track)** | Mỗi run gửi siêu tham số và chỉ số từng epoch (accuracy, loss, val_accuracy, val_loss) về một REST API, lưu vào SQLite. |
| 🌐 | **Trực quan hoá 3D (Visualize)** | Mỗi run là một quả cầu trong không gian 3D: trục X = số epoch, Y = accuracy, Z = loss. Màu thể hiện trạng thái (🟢 hoàn thành · 🟡 đang chạy · 🔴 lỗi). Click vào quả cầu để xem chi tiết. |
| 🤖 | **Trợ lý AI (Converse)** | Hỏi bằng ngôn ngữ tự nhiên: *"Run nào có accuracy cao nhất?"*, *"Run-002 có bị overfit không?"*. AI trả lời và **tự động bay camera tới** run tương ứng trong không gian 3D. |

Ba khung giao diện (không gian 3D, bảng chi tiết, khung chat) luôn **đồng bộ trạng thái** với nhau.

> [!NOTE]
> Đây là bản **Proof of Concept (PoC)**, chạy trên máy cá nhân (localhost), một người dùng. Hiện **Phase 1 (Backend tracking)** đã hoàn thành; giao diện 3D và trợ lý AI đang được phát triển. Xem [Lộ trình](#lộ-trình-phát-triển).

---

## Tính năng

### ✅ Đã có (Phase 1 – Backend)

- REST API đầy đủ để tạo **experiment**, **run** và ghi **metrics theo từng epoch**.
- Kiểm tra dữ liệu chặt chẽ: `learning_rate > 0`, `0 ≤ accuracy ≤ 1`, `loss ≥ 0`, `epoch ≥ 1`, không nhận NaN/vô cực, không nhận field lạ.
- Danh sách run kèm **chỉ số của epoch cuối** (`final_accuracy`, `final_loss`, ...) — sẵn sàng để vẽ lên không gian 3D.
- Mã lỗi HTTP rõ ràng: `201` tạo mới · `404` không tìm thấy · `409` trùng lặp · `422` dữ liệu sai.
- **Script huấn luyện demo** (scikit-learn) tự ghi log lên API.
- **Công cụ sinh dữ liệu giả lập** với đường cong học tập thực tế (có run tốt, run overfit, run lỗi, run đang chạy).
- Swagger UI tự động tại `/docs`.
- 78 bài kiểm thử, độ phủ code 99%.

### 🚧 Sắp có

- Không gian 3D tương tác (xoay, zoom, click, hover, camera bay tới node).
- Inspector Panel: bảng siêu tham số + biểu đồ accuracy/loss theo epoch.
- AI Copilot: tìm run tốt nhất, so sánh 2 run, chẩn đoán overfitting, tóm tắt experiment, gợi ý siêu tham số.

---

## Kiến trúc

```
┌──────────────────────────── Trình duyệt (React + Vite) ────────────────────────────┐
│   Không gian 3D (R3F)  │   Inspector Panel   │   Khung chat AI                     │
│                Zustand store — nguồn trạng thái duy nhất, đồng bộ 3 khung          │
└───────────────────────────────────────┬────────────────────────────────────────────┘
                                        │ HTTP / REST (/api/...)
┌───────────────────────────────────────▼────────────────────────────────────────────┐
│                               Backend (FastAPI)                                    │
│  /api/experiments   /api/runs   /api/runs/{id}/metrics   /api/copilot/chat (P3)    │
│              │                                              │                      │
│      Service layer (tracking)                        AI Copilot Engine (P3)        │
│              │                                              │                      │
│      SQLite (experiments · runs · metrics)  ◄───────────────┘ ──► LLM API          │
└────────────────────────────────────────────────────────────────────────────────────┘
        ▲
        │ POST /api/runs, /metrics
  Script huấn luyện của bạn
```

**Luồng dữ liệu chính:** script huấn luyện → gửi metrics lên API → lưu SQLite → frontend lấy danh sách run → vẽ thành các node 3D → người dùng click node hoặc hỏi AI → giao diện cập nhật.

> [!IMPORTANT]
> **API key của LLM không bao giờ nằm ở frontend.** Mọi lời gọi AI đều đi qua backend (`/api/copilot/chat`).

### Mô hình dữ liệu

```
experiments 1 ──── N runs 1 ──── N metrics
─────────────        ─────────────────        ──────────────────
id                   id                       id
name (duy nhất)      experiment_id  (FK)      run_id (FK)
description          run_name                 epoch          (≥ 1, duy nhất trong run)
created_at           status: running |        accuracy       (0–1)
                       completed | failed     loss           (≥ 0)
                     hyperparams (JSON)       val_accuracy   (0–1, tuỳ chọn)
                     created_at               val_loss       (≥ 0, tuỳ chọn)
                     finished_at              logged_at
```

Xoá một experiment sẽ xoá luôn các run và metrics của nó.

---

## Công nghệ sử dụng

| Phần | Công nghệ |
|---|---|
| **Backend** | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2 (async) + aiosqlite, SQLite (chế độ WAL) |
| **Frontend** *(Phase 2)* | React 18, Vite, TypeScript, Tailwind CSS, React Three Fiber + drei, Zustand |
| **AI** *(Phase 3)* | Gemini hoặc OpenAI, gọi qua backend |
| **Công cụ** | uv (quản lý gói Python), pnpm, Ruff, pytest + pytest-cov |

---

## Cấu trúc thư mục

```
3d-mlops-copilot-platform/
├── README.md
├── CLAUDE.md                     # Quy ước code cho dự án
├── docs/
│   └── PLAN.md                   # Kế hoạch chi tiết & lộ trình
├── frontend/                     # (Phase 2 – chưa khởi tạo)
└── backend/
    ├── pyproject.toml            # Dependencies & cấu hình pytest/ruff/coverage
    ├── .env.example              # Mẫu biến môi trường
    ├── app/
    │   ├── main.py               # Điểm khởi chạy FastAPI, CORS, đăng ký router
    │   ├── config.py             # Cấu hình (đọc từ .env)
    │   ├── database.py           # Engine async, session, tạo bảng
    │   ├── models/               # ORM: Experiment, Run, Metric
    │   ├── schemas/              # Pydantic: dữ liệu vào/ra + validation
    │   ├── routers/              # Các endpoint /api/...
    │   ├── services/             # Logic nghiệp vụ (tracking.py)
    │   └── utils/seed_data.py    # Sinh dữ liệu giả lập
    ├── scripts/
    │   ├── train_mnist_demo.py   # Script huấn luyện demo
    │   └── log_to_api.py         # Client Python để ghi log lên API
    └── tests/                    # Bộ kiểm thử pytest
```

---

## Bắt đầu nhanh

### Yêu cầu

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/)** — trình quản lý gói Python. Cài bằng một trong hai cách:

  ```bash
  pip install uv
  ```

  hoặc xem hướng dẫn chính thức tại [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/).

> [!TIP]
> Trên Windows, nếu cài bằng `pip install --user uv` mà gõ `uv` báo "not found", hãy thêm thư mục `%APPDATA%\Python\Python3xx\Scripts` vào biến môi trường `PATH`.

### 1. Cài đặt dependencies

```bash
cd backend
uv sync
```

Lệnh này tạo môi trường ảo `backend/.venv` và cài toàn bộ thư viện (kể cả công cụ dev như pytest, ruff, scikit-learn).

### 2. (Tuỳ chọn) Tạo file cấu hình

```bash
cp .env.example .env
```

Không có `.env` thì dùng giá trị mặc định — đủ để chạy ngay.

### 3. Chạy server

```bash
uv run uvicorn app.main:app --reload
```

Khi khởi động, server tự tạo file `backend/mlops.db` cùng các bảng.

| Địa chỉ | Nội dung |
|---|---|
| http://localhost:8000/docs | Swagger UI — thử trực tiếp mọi API trên trình duyệt |
| http://localhost:8000/redoc | Tài liệu API dạng ReDoc |
| http://localhost:8000/api/health | Kiểm tra server sống: `{"status": "ok"}` |

---

## Tạo dữ liệu mẫu

Có hai cách để có dữ liệu thử nghiệm.

### Cách 1 — Dữ liệu giả lập (nhanh, không cần server)

```bash
cd backend
uv run python -m app.utils.seed_data
```

Tạo 2 experiment là `MNIST-CNN-v1` và `CIFAR10-ResNet18`, mỗi cái 15 run với đường cong học tập trông như thật: có run tốt, run overfit, run bị phân kỳ rồi lỗi, run đang chạy dở.

| Tham số | Ý nghĩa |
|---|---|
| `--runs-per-experiment N` | Số run mỗi experiment (mặc định 15) |
| `--seed N` | Hạt giống ngẫu nhiên, cùng seed cho cùng dữ liệu (mặc định 42) |
| `--reset` | Xoá và tạo lại 2 experiment mẫu. Dữ liệu khác không bị ảnh hưởng. |

Chạy lại nhiều lần không bị trùng: experiment mẫu đã có sẽ được bỏ qua.

### Cách 2 — Huấn luyện thật (cần server đang chạy)

```bash
cd backend
uv run python scripts/train_mnist_demo.py --sweep
```

Huấn luyện mạng nơ-ron (`MLPClassifier` của scikit-learn) với 9 bộ siêu tham số khác nhau, mỗi epoch gửi kết quả lên API. Mặc định dùng tập ảnh chữ số 8×8 có sẵn trong scikit-learn (không cần tải).

```bash
# Một run với siêu tham số tự chọn
uv run python scripts/train_mnist_demo.py --lr 0.001 --batch-size 32 --epochs 15 --hidden-layers 128,64

# Dùng MNIST thật (tải ~15 MB từ OpenML ở lần đầu)
uv run python scripts/train_mnist_demo.py --dataset mnist --mnist-samples 10000 --sweep

# Xem toàn bộ tham số
uv run python scripts/train_mnist_demo.py --help
```

---

## Tài liệu API

Tất cả endpoint có tiền tố `/api`. Tài liệu đầy đủ, có thể bấm thử, nằm ở **`/docs`**.

| Method | Endpoint | Chức năng | Mã trả về |
|---|---|---|---|
| `GET` | `/api/health` | Kiểm tra server | 200 |
| `POST` | `/api/experiments` | Tạo experiment | 201 · 409 trùng tên |
| `GET` | `/api/experiments` | Danh sách experiment | 200 |
| `GET` | `/api/experiments/{id}` | Chi tiết experiment | 200 · 404 |
| `POST` | `/api/runs` | Tạo run (trạng thái ban đầu `running`) | 201 · 404 · 409 trùng tên run |
| `GET` | `/api/runs?experiment_id=X` | Danh sách run kèm chỉ số epoch cuối | 200 · 404 |
| `GET` | `/api/runs/{id}` | Chi tiết run kèm toàn bộ metrics theo epoch | 200 · 404 |
| `PUT` | `/api/runs/{id}` | Cập nhật trạng thái: `completed` / `failed` / `running` | 200 · 404 · 409 |
| `POST` | `/api/runs/{id}/metrics` | Ghi metrics cho 1 epoch | 201 · 404 · 409 epoch đã ghi |

Dữ liệu gửi lên sai định dạng luôn trả về **422**, kèm thông báo chỉ rõ field nào sai.

### Ví dụ với `curl`

```bash
# 1. Tạo experiment
curl -X POST localhost:8000/api/experiments \
  -H "Content-Type: application/json" \
  -d '{"name": "MNIST-CNN-v1", "description": "CNN baseline on MNIST"}'

# 2. Tạo run với siêu tham số
curl -X POST localhost:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{"experiment_id": 1, "run_name": "run-001", "hyperparams": {"learning_rate": 0.001, "batch_size": 32, "epochs": 10}}'

# 3. Ghi metrics của epoch 1
curl -X POST localhost:8000/api/runs/1/metrics \
  -H "Content-Type: application/json" \
  -d '{"epoch": 1, "accuracy": 0.91, "loss": 0.31, "val_accuracy": 0.89, "val_loss": 0.35}'

# 4. Đánh dấu hoàn thành (finished_at tự điền thời điểm hiện tại, UTC)
curl -X PUT localhost:8000/api/runs/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "completed"}'

# 5. Xem danh sách run
curl "localhost:8000/api/runs?experiment_id=1"
```

> [!TIP]
> Các lệnh trên dùng cú pháp bash (Linux, macOS, Git Bash, WSL). Trên Windows, nếu chuỗi JSON có chữ tiếng Việt có dấu thì terminal có thể gửi sai bảng mã và API trả lỗi 400. Khi đó hãy thử trực tiếp trên Swagger UI (`/docs`) hoặc dùng client Python ở phần dưới.

<details>
<summary>Ví dụ kết quả của <code>GET /api/runs</code></summary>

```json
[
  {
    "id": 1,
    "experiment_id": 1,
    "run_name": "run-001",
    "status": "completed",
    "hyperparams": { "learning_rate": 0.001, "batch_size": 32, "epochs": 10 },
    "created_at": "2026-11-07T08:27:00Z",
    "finished_at": "2026-11-07T08:29:41Z",
    "final_epoch": 10,
    "final_accuracy": 0.9812,
    "final_loss": 0.106,
    "final_val_accuracy": 0.9644,
    "final_val_loss": 0.139
  }
]
```

</details>

### Quy tắc kiểm tra siêu tham số

`hyperparams` là một object JSON tự do: bạn đặt key gì cũng được. Riêng các key quen thuộc sau bị kiểm tra:

| Key | Điều kiện |
|---|---|
| `learning_rate` hoặc `lr` | số > 0 |
| `epochs`, `batch_size` | số nguyên ≥ 1 |

---

## Ghi log từ script huấn luyện của bạn

Dùng client có sẵn trong `backend/scripts/log_to_api.py`. Client chỉ cần thư viện `httpx`: đặt script của bạn trong `backend/scripts/`, hoặc chép file `log_to_api.py` sang project của bạn.

```python
from log_to_api import TrackingClient

with TrackingClient("http://localhost:8000") as client:
    exp = client.ensure_experiment("My-Experiment", "Mô tả")

    hyperparams = {"learning_rate": 1e-3, "batch_size": 64, "epochs": 20}
    with client.start_run(exp["id"], hyperparams) as run:  # tự đặt tên run-001, run-002, ...
        for epoch in range(1, 21):
            acc, loss, val_acc, val_loss = train_one_epoch()  # code huấn luyện của bạn
            run.log(epoch, accuracy=acc, loss=loss, val_accuracy=val_acc, val_loss=val_loss)
    # Ra khỏi khối `with`: run tự chuyển sang "completed".
    # Nếu có lỗi (exception) hoặc loss = NaN: run tự chuyển sang "failed".
```

---

## Cấu hình

Đặt trong `backend/.env`. Xem mẫu ở `backend/.env.example`.

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `DEBUG` | `false` | In câu lệnh SQL ra console |
| `DATABASE_URL` | file `backend/mlops.db` | Chuỗi kết nối, ví dụ `sqlite+aiosqlite:///./mlops.db` |
| `CORS_ORIGINS` | `localhost:5173`, `localhost:3000` | Các địa chỉ frontend được phép gọi API (dạng JSON list) |
| `LLM_API_KEY` | — | API key của LLM *(Phase 3, chỉ dùng ở backend)* |
| `LLM_MODEL` | — | Tên model LLM *(Phase 3)* |

> [!CAUTION]
> Không commit file `.env` (đã có trong `.gitignore`).

---

## Kiểm thử

```bash
cd backend

uv run pytest                 # chạy toàn bộ test
uv run pytest --cov           # kèm báo cáo độ phủ code
uv run ruff check .           # kiểm tra lỗi code
uv run ruff format .          # định dạng code
```

Mỗi bài test dùng một database SQLite **trong bộ nhớ** riêng, nên không ảnh hưởng tới `mlops.db` của bạn.

---

## Lộ trình phát triển

Chi tiết từng task xem tại [`docs/PLAN.md`](docs/PLAN.md).

- [x] **Phase 1 — Nền tảng Backend & MLOps:** API tracking, database, validation, script demo, dữ liệu mẫu, kiểm thử
- [ ] **Phase 2 — Không gian 3D:** khởi tạo frontend, layout 3 khung, node 3D, click/hover, Inspector Panel, camera bay tới node
- [ ] **Phase 3 — AI Copilot:** kết nối LLM, xây dựng ngữ cảnh từ dữ liệu run, prompt template, phân tích phản hồi thành hành động (highlight, focus camera)
- [ ] **Phase 4 — Đồng bộ & hoàn thiện giao diện:** đồng bộ 3 khung, sidebar, hiệu ứng, tối ưu hiệu năng (≥ 200 node @ 60 fps), dark mode
- [ ] **Phase 5 — Kiểm thử & demo:** smoke test end-to-end, benchmark, tài liệu demo

### Giới hạn của bản PoC

- Chưa có đăng nhập, chỉ một người dùng, chạy trên localhost.
- SQLite phù hợp cho thử nghiệm. Thiết kế cho tối đa khoảng 500 run và 50 epoch mỗi run.
- Cần trình duyệt hỗ trợ WebGL 2.0 (Chrome, Edge, Firefox).

---

## Quy ước đóng góp

- **Python:** PEP 8, kiểm tra bằng Ruff (`line-length = 100`). Chạy `uv run ruff format . && uv run ruff check .` trước khi commit.
- **Frontend:** dùng các Zustand store (`useRunStore`, `useCameraStore`, `useChatStore`) làm nguồn trạng thái duy nhất giữa các khung.
- **Bảo mật:** không bao giờ đưa API key của LLM vào code frontend.
- **Commit:** theo [Conventional Commits](https://www.conventionalcommits.org/), ví dụ `feat(backend): ...`, `fix(frontend): ...`, `docs: ...`.
- Mở Pull Request vào `main`. Toàn bộ test phải pass.

Xem thêm [`CLAUDE.md`](CLAUDE.md) để biết các lệnh build/test và quy ước kiến trúc.
