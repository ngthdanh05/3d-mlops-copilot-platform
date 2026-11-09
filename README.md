# 3D-MLOps Copilot Platform

> Nền tảng quản lý thực nghiệm học máy (ML experiment tracking) trong **không gian 3D**, tích hợp **trợ lý AI** giúp bạn tìm, so sánh và chẩn đoán các lần huấn luyện mô hình.

[![CI](https://github.com/ngthdanh05/3d-mlops-copilot-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/ngthdanh05/3d-mlops-copilot-platform/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-async-003B57?logo=sqlite&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![Three.js](https://img.shields.io/badge/React_Three_Fiber-3D-000000?logo=three.js&logoColor=white)
![Status](https://img.shields.io/badge/trạng_thái-PoC-orange)

---

## Mục lục

- [Dự án này làm gì?](#dự-án-này-làm-gì)
- [Tính năng](#tính-năng)
- [Kiến trúc](#kiến-trúc)
- [Thiết kế không gian 3D](#thiết-kế-không-gian-3d)
- [Thiết kế trợ lý AI](#thiết-kế-trợ-lý-ai)
- [Công nghệ sử dụng](#công-nghệ-sử-dụng)
- [Cấu trúc thư mục](#cấu-trúc-thư-mục)
- [Bắt đầu nhanh](#bắt-đầu-nhanh)
- [Tạo dữ liệu mẫu](#tạo-dữ-liệu-mẫu)
- [Tài liệu API](#tài-liệu-api)
- [Ghi log từ script huấn luyện của bạn](#ghi-log-từ-script-huấn-luyện-của-bạn)
- [Cấu hình](#cấu-hình)
- [Kiểm thử](#kiểm-thử)
- [Lộ trình phát triển](#lộ-trình-phát-triển)
- [Giới hạn của bản PoC](#giới-hạn-của-bản-poc)
- [Quy ước phát triển](#quy-ước-phát-triển)

---

## Dự án này làm gì?

Khi huấn luyện mô hình học máy, ta thường chạy **rất nhiều lần** (gọi là các *run*) với các bộ siêu tham số khác nhau: learning rate, batch size, số epoch... Theo dõi xem run nào tốt nhất, run nào bị overfit, run nào bị lỗi trong một bảng số liệu dài là việc mệt mỏi. Bảng số liệu cũng khó cho thấy **vì sao** một run tốt hơn, hay **vùng siêu tham số nào chưa được thử**.

**3D-MLOps Copilot** giải quyết việc đó bằng ba thành phần:

| | Thành phần | Ý nghĩa |
|---|---|---|
| 📊 | **Theo dõi (Track)** | Mỗi run gửi siêu tham số và chỉ số từng epoch (accuracy, loss, val_accuracy, val_loss) về một REST API, lưu vào SQLite. |
| 🌐 | **Trực quan hoá 3D (Visualize)** | Mỗi run là một quả cầu trong **không gian siêu tham số 3D**: vị trí cho biết run được cấu hình thế nào, màu và kích thước cho biết kết quả. Người dùng thấy ngay vùng nào cho kết quả tốt và vùng nào còn trống. Xem [Thiết kế không gian 3D](#thiết-kế-không-gian-3d). |
| 🤖 | **Trợ lý AI (Converse)** | Hỏi bằng ngôn ngữ tự nhiên: *"Run nào có accuracy cao nhất?"*, *"Run-002 có bị overfit không?"*. AI lấy số liệu qua các công cụ (tool) của backend rồi trả lời, đồng thời **làm nổi bật và bay camera tới** các run liên quan. |

Ba khung giao diện (không gian 3D, bảng chi tiết, khung chat) luôn **đồng bộ trạng thái** với nhau.

> [!NOTE]
> Đây là bản **Proof of Concept (PoC)**, chạy trên máy cá nhân (localhost), một người dùng. Hiện backend tracking, không gian 3D và luồng AI tìm run tốt nhất đã chạy được; các công cụ phân tích còn lại của AI đang được phát triển. Xem [Lộ trình](#lộ-trình-phát-triển).

---

## Tính năng

### ✅ Đã có

- Không gian 3D tương tác: xoay, zoom, click, hover, camera bay tới run, câu kết luận tính từ dữ liệu, Inspector Panel.
- Trợ lý AI dùng Gemini: tìm run tốt nhất, giải thích so với trung vị, làm nổi bật và bay camera tới run đó.

- REST API để tạo **experiment**, **run** và ghi **metrics theo từng epoch**.
- Kiểm tra dữ liệu chặt chẽ: `learning_rate > 0`, `0 ≤ accuracy ≤ 1`, `loss ≥ 0`, `epoch ≥ 1`, không nhận NaN/vô cực, không nhận field lạ.
- Danh sách run kèm **chỉ số của epoch cuối** (`final_accuracy`, `final_loss`, ...), sẵn sàng để vẽ lên không gian 3D.
- Mã lỗi HTTP rõ ràng: `201` tạo mới · `404` không tìm thấy · `409` trùng lặp · `422` dữ liệu sai.
- **Script huấn luyện demo** (scikit-learn) tự ghi log lên API.
- **Công cụ sinh dữ liệu giả lập** với đường cong học tập thực tế (có run tốt, run overfit, run lỗi, run đang chạy).
- Swagger UI tự động tại `/docs`.
- 113 bài kiểm thử backend. CI tự chạy test và lint cho mỗi Pull Request.

### 🚧 Sắp có

| Tính năng | Phase | Ưu tiên |
|---|---|---|
| Chọn trục 3D từ danh sách siêu tham số / metrics | 2 | Must |
| Inspector Panel: biểu đồ accuracy/loss theo epoch | 2 | Must |
| AI Copilot: so sánh 2 run, chẩn đoán overfitting | 3 | Must |
| AI tóm tắt experiment, gợi ý siêu tham số | 3 | Should |
| Endpoint xoá experiment / run | 2 | Should |
| Giao diện xem run của nhiều experiment cùng lúc (API đã hỗ trợ) | 2 | Should |
| Tự cập nhật run đang chạy (polling) | 4 | Should |
| Chế độ giảm chiều (PCA) khi có nhiều hơn 3 siêu tham số | 4 | Could |
| Đóng gói client ghi log thành thư viện `pip install` | 4 | Could |

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
│      Service layer (tracking)  ◄──── tool calls ────  AI Copilot Engine (P3)       │
│              │                                              │                      │
│      SQLite (experiments · runs · metrics)                  └──► LLM API           │
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

Ở tầng database, xoá một experiment sẽ xoá luôn các run và metrics của nó (cascade). API xoá dùng đúng cơ chế này.

---

## Thiết kế không gian 3D

> [!NOTE]
> Trục mặc định, màu, kích thước và trạng thái **đã được cài đặt**. Instanced mesh chưa có.

Mục tiêu của không gian 3D là trả lời hai câu hỏi mà bảng số liệu khó trả lời: *run tốt nằm ở vùng cấu hình nào?* và *vùng nào chưa được thử?* Vì vậy **vị trí thể hiện đầu vào (siêu tham số), còn hình thức thể hiện kết quả**.

| Kênh hiển thị | Mặc định | Ghi chú |
|---|---|---|
| Trục X | `learning_rate` | **Thang log** (giá trị thường trải từ 1e-5 đến 1e-1) |
| Trục Y | `batch_size` | Thang log cơ số 2 |
| Trục Z | Siêu tham số dạng số còn lại: ưu tiên `dropout`, rồi `epochs`, rồi các key khác | Lấy key đầu tiên có ≥ 2 giá trị khác nhau. Không có key nào thì Z phẳng |
| Màu | `final_val_accuracy` (hoặc `final_accuracy` nếu không có) | Thang màu liên tục, có chú giải. Miền giá trị lấy từ các run hoàn thành và bỏ giá trị ngoại lai ở phía thấp, để một run phân kỳ không làm các run còn lại cùng màu |
| Kích thước | `final_val_loss` | Loss cao → cầu nhỏ |
| Viền / icon | Trạng thái | ● hoàn thành · ◐ đang chạy · ✕ lỗi |

- Đầu đồ thị luôn có một câu kết luận tính từ dữ liệu. Run đang chọn hoặc được AI làm nổi bật có nhãn, đường gióng xuống trục, và các run còn lại mờ đi.
- Người dùng **chọn được trục** từ mọi key **dạng số** trong `hyperparams` và mọi metric cuối.
- Key không phải số (`optimizer` là chuỗi, `hidden_layers` là danh sách) chưa làm trục được ở PoC, nhưng vẫn hiện trong Inspector Panel.
- Run thiếu một siêu tham số đang dùng làm trục được đặt ở mặt phẳng "không xác định" và vẽ mờ.
- Không dùng epoch, accuracy và loss làm 3 trục cùng lúc: accuracy và loss gần như tỉ lệ nghịch nên các điểm sẽ dồn trên một đường, còn số epoch thường giống nhau giữa các run.
- Mục tiêu hiệu năng: ≥ 200 node ở 60 fps (dùng instanced mesh).

---

## Thiết kế trợ lý AI

> [!NOTE]
> Đã có vòng lặp tool calling, kết nối Gemini, 6 tool truy vấn, 3 tool điều khiển giao diện và khung chat. Khi chưa đặt `LLM_API_KEY`, backend dùng **LLM giả lập**: câu trả lời có tiền tố `[LLM giả lập]` và chỉ hiểu câu hỏi tìm run tốt nhất.

Trợ lý dùng **tool calling (function calling)**: LLM **không** được nhận toàn bộ dữ liệu trong prompt và **không** tự đưa ra số liệu. Mọi con số phải lấy qua công cụ. Cách này tránh việc AI bịa số và vẫn chạy được khi có hàng trăm run.

**Công cụ truy vấn** (chạy ở backend, gọi service layer):

| Tool | Chức năng |
|---|---|
| `list_experiments()` | Danh sách experiment |
| `find_best_runs(experiment_id, metric, top_k)` | Các run tốt nhất theo một metric |
| `find_runs_by_name(run_names, experiment_id)` | Tìm `run_id` từ tên run người dùng nhắc tới, không phân biệt hoa thường |
| `get_run(run_id)` | Siêu tham số + metrics từng epoch của một run |
| `compare_runs(run_ids)` | So sánh siêu tham số và metrics cuối |
| `detect_overfitting(run_id)` | Phân tích khoảng cách train/val qua các epoch (tính bằng code, không do LLM tự đoán) |

**Công cụ điều khiển giao diện** (backend trả về dưới dạng `actions`, frontend thực thi qua Zustand store):

| Tool | Chức năng |
|---|---|
| `highlight_runs(run_ids)` | Làm nổi bật các run |
| `focus_camera(run_id)` | Bay camera tới một run |
| `open_inspector(run_id)` | Mở bảng chi tiết |

Ví dụ phản hồi của `/api/copilot/chat`:

```json
{
  "message": "Run-007 có val_accuracy cao nhất (0.9644)...",
  "actions": [
    { "type": "highlight_runs", "run_ids": [7] },
    { "type": "focus_camera", "run_id": 7 }
  ]
}
```

Nhà cung cấp LLM: **Gemini**, mặc định model `gemini-3.5-flash-lite` trên gói miễn phí. Mọi chi tiết của nhà cung cấp nằm trong `backend/app/services/copilot/llm_client.py`.

> [!WARNING]
> Google dùng nội dung gửi qua gói miễn phí để cải thiện sản phẩm. Không đưa dữ liệu nhạy cảm vào hyperparams, tên run hay câu hỏi khi dùng gói này.

---

## Công nghệ sử dụng

| Phần | Công nghệ |
|---|---|
| **Backend** | Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2 (async) + aiosqlite, SQLite (chế độ WAL) |
| **Frontend** *(Phase 2)* | React 18, Vite, TypeScript, Tailwind CSS, React Three Fiber + drei, Zustand |
| **AI** | Gemini qua SDK `google-genai`, dùng tool calling, gọi qua backend |
| **Công cụ** | uv (quản lý gói Python), pnpm, Ruff, pytest + pytest-cov, GitHub Actions |

---

## Cấu trúc thư mục

```
3d-mlops-copilot-platform/
├── README.md
├── CONTRIBUTING.md               # Quy ước branch, commit, kiểm tra và code
├── CLAUDE.md                     # Quy ước code cho dự án
├── .github/
│   ├── workflows/ci.yml          # CI: lint + test cho mỗi PR
│   └── pull_request_template.md  # Mẫu PR
├── docs/
│   └── PLAN.md                   # Kế hoạch chi tiết & lộ trình
├── frontend/                     # React + R3F (khung 3 panel, store, API client)
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
- **[uv](https://docs.astral.sh/uv/)**: trình quản lý gói Python. Cài bằng `pip install uv` hoặc xem [hướng dẫn chính thức](https://docs.astral.sh/uv/getting-started/installation/).
- **Node.js 20.19+** (hoặc 22.12+) và **pnpm** (`npm install -g pnpm@10`), nếu làm frontend.

> [!TIP]
> Trên Windows, nếu cài bằng `pip install --user uv` mà gõ `uv` báo "not found", hãy thêm thư mục `%APPDATA%\Python\Python3xx\Scripts` vào biến môi trường `PATH`.

### Backend

```bash
cd backend
uv sync                                  # tạo .venv và cài thư viện (kể cả công cụ dev)
cp .env.example .env                     # tuỳ chọn, không có .env thì dùng mặc định
uv run uvicorn app.main:app --reload     # chạy server
```

Khi khởi động, server tự tạo file `backend/mlops.db` cùng các bảng.

| Địa chỉ | Nội dung |
|---|---|
| http://localhost:8000/docs | Swagger UI, thử trực tiếp mọi API trên trình duyệt |
| http://localhost:8000/redoc | Tài liệu API dạng ReDoc |
| http://localhost:8000/api/health | Kiểm tra server sống: `{"status": "ok"}` |

### Frontend

```bash
cd frontend
pnpm install
pnpm dev          # mở http://localhost:5173
```

Frontend chuyển các request `/api` tới `http://localhost:8000` qua proxy của Vite. Hãy chạy backend trước.

> [!TIP]
> Trên Windows, nếu gõ `pnpm` báo "not recognized", hãy thêm thư mục `%APPDATA%\npm` vào biến môi trường `PATH`.

> [!WARNING]
> Dự án dùng React 18 nên phải giữ `@react-three/fiber` ở v8 và `@react-three/drei` ở v9. Bản mới hơn của hai thư viện này yêu cầu React 19.

---

## Tạo dữ liệu mẫu

### Cách 1: dữ liệu giả lập (nhanh, không cần server)

```bash
cd backend
uv run python -m app.utils.seed_data
```

Tạo 2 experiment là `mock-mnist-cnn` và `mock-cifar10-resnet18`, mỗi cái 15 run với đường cong học tập trông như thật: có run tốt, run overfit, run bị phân kỳ rồi lỗi, run đang chạy dở.

> [!NOTE]
> Đây là dữ liệu **giả lập**, dùng để phát triển giao diện và test. Tiền tố `mock-` nghĩa là không có mô hình nào được huấn luyện thật. Dữ liệu huấn luyện thật có tiền tố `real-`.

| Tham số | Ý nghĩa |
|---|---|
| `--runs-per-experiment N` | Số run mỗi experiment (mặc định 15) |
| `--seed N` | Hạt giống ngẫu nhiên, cùng seed cho cùng dữ liệu (mặc định 42) |
| `--reset` | Xoá và tạo lại 2 experiment mẫu. Dữ liệu khác không bị ảnh hưởng. |

Chạy lại nhiều lần không bị trùng: experiment mẫu đã có sẽ được bỏ qua.

### Cách 2: huấn luyện thật (cần server đang chạy)

Bộ thử chuẩn cho demo là 35 run trên MNIST, gồm 30 cấu hình ngẫu nhiên và 5 cấu hình cố ý xấu. Cùng `--seed` sẽ cho cùng bộ cấu hình, nên tái tạo được dữ liệu trên máy khác mà không cần chép file database. Lệnh này tự bỏ qua nếu experiment đã có run.

```bash
uv run python scripts/train_mnist_demo.py --dataset mnist --random-search 30
```

Một bộ thử nhỏ hơn, chạy nhanh:

```bash
cd backend
uv run python scripts/train_mnist_demo.py --sweep
```

Huấn luyện mạng nơ-ron nhiều lớp (`MLPClassifier` của scikit-learn) với 9 bộ siêu tham số khác nhau, mỗi epoch gửi kết quả lên API. Mặc định dùng **tập ảnh chữ số 8×8 có sẵn trong scikit-learn** (không cần tải), không phải MNIST gốc 28×28.

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
| `DELETE` | `/api/experiments/{id}` | Xoá experiment cùng các run và metrics của nó | 204 · 404 |
| `POST` | `/api/runs` | Tạo run (trạng thái ban đầu `running`) | 201 · 404 · 409 trùng tên run |
| `GET` | `/api/runs` | Danh sách run kèm chỉ số epoch cuối. Thêm `?experiment_id=X` để lọc, bỏ trống để lấy mọi experiment | 200 · 404 |
| `GET` | `/api/runs/{id}` | Chi tiết run kèm toàn bộ metrics theo epoch | 200 · 404 |
| `PUT` | `/api/runs/{id}` | Cập nhật trạng thái: `completed` / `failed` / `running` | 200 · 404 · 409 |
| `DELETE` | `/api/runs/{id}` | Xoá run cùng metrics của nó | 204 · 404 |
| `POST` | `/api/runs/{id}/metrics` | Ghi metrics cho 1 epoch | 201 · 404 · 409 epoch đã ghi |
| `POST` | `/api/copilot/chat` | Hỏi trợ lý AI, trả về `message` + `actions` | 200 · 422 |

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

> [!TIP]
> Để các run hiển thị đúng chỗ trong không gian 3D, hãy dùng **tên key thống nhất**: `learning_rate` (không dùng `lr`), `batch_size`, `epochs`, `hidden_layers`.

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
| `LLM_API_KEY` | — | API key Gemini, lấy tại [AI Studio](https://aistudio.google.com/apikey). Chỉ dùng ở backend. Để trống thì dùng LLM giả lập |
| `LLM_MODEL` | `gemini-3.5-flash-lite` | Tên model Gemini |

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

**CI (GitHub Actions)** chạy tự động cho mỗi Pull Request vào `main`:

| Job | Kiểm tra |
|---|---|
| `backend` | `ruff format --check`, `ruff check`, `pytest --cov` |
| `frontend` | `lint`, `typecheck`, `build` (tự bỏ qua khi chưa có `frontend/package.json`) |

---

## Lộ trình phát triển

Chi tiết từng task: [`docs/PLAN.md`](docs/PLAN.md).

| Phase | Nội dung | Trạng thái |
|---|---|---|
| 1 | **Nền tảng Backend & MLOps:** API tracking, database, validation, script demo, dữ liệu mẫu, kiểm thử | ✅ Xong |
| 2 | **Không gian 3D:** khởi tạo frontend, layout 3 khung, node 3D theo [thiết kế](#thiết-kế-không-gian-3d), chọn trục, click/hover, Inspector Panel, camera bay tới node. Backend bổ sung `DELETE` | 🚧 Phần lớn đã có |
| 3 | **AI Copilot:** kết nối LLM, các tool truy vấn và tool điều khiển giao diện theo [thiết kế](#thiết-kế-trợ-lý-ai), bộ câu hỏi kiểm thử độ chính xác | 🚧 Mới có tìm run tốt nhất |
| 4 | **Đồng bộ & hoàn thiện:** đồng bộ 3 khung, sidebar, polling run đang chạy, tối ưu hiệu năng (≥ 200 node @ 60 fps), dark mode | ⏳ |
| 5 | **Kiểm thử & demo:** smoke test end-to-end, benchmark, tài liệu demo, báo cáo | ⏳ |

---

## Giới hạn của bản PoC

- Chưa có đăng nhập, chỉ một người dùng, chạy trên localhost.
- SQLite phù hợp cho thử nghiệm. Thiết kế cho tối đa khoảng 500 run và 50 epoch mỗi run.
- **Metrics cố định 4 loại** (`accuracy`, `loss`, `val_accuracy`, `val_loss`), phù hợp bài toán **phân loại**. Chưa hỗ trợ metric khác như F1, MSE, R².
- Chưa lưu file model (artifact).
- Cần trình duyệt hỗ trợ WebGL 2.0 (Chrome, Edge, Firefox).

---

## Quy ước phát triển

Xem [CONTRIBUTING.md](CONTRIBUTING.md) cho quy ước branch, commit và code, và [`CLAUDE.md`](CLAUDE.md) cho các lệnh build/test.
