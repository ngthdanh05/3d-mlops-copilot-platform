# CIFAR-10 và copilot local trên Windows

Nếu muốn vừa đọc code vừa quan sát API/giao diện, xem [sơ đồ và bài thực hành theo luồng dữ liệu](DATA-FLOW-AND-TEST-WALKTHROUGH.md).

Các lệnh dưới đây chạy trong PowerShell tại `backend/`, trừ khi ghi rõ khác.
Dataset, checkpoints và model LLM không được commit. Hai mô hình độc lập:
CNN phân loại ảnh CIFAR-10; Qwen trả lời qua tools truy vấn SQLite.

## Chuẩn bị online một lần

```powershell
uv sync --locked --group training
uv run --locked --group training python scripts/check_training_env.py --device cuda
uv run --locked --group training python scripts/prepare_cifar10.py --parallel-download
uv run --locked --group training python scripts/prepare_ollama.py
```

Python >=3.11. Lock dùng torch 2.7.1 / torchvision 0.22.1, CUDA 12.6 trên Windows/Linux;
macOS dùng wheel mặc định. Backend thường chỉ cần `uv sync --locked`, không cần torch.
Không cài TensorFlow. Kiểm tra GPU bằng forward/backward thực tế, không chỉ `nvidia-smi`.
Nếu CUDA thiếu, lệnh dừng; `--device cpu` là lựa chọn tường minh, không tự đổi thiết bị.

Nguồn tương thích: [PyTorch previous versions](https://pytorch.org/get-started/previous-versions/),
[Torchvision CIFAR10](https://docs.pytorch.org/vision/stable/generated/torchvision.datasets.CIFAR10.html).
Runtime portable mặc định khóa bản đã kiểm tra `v0.40.16`, tải từ GitHub chính thức và
kiểm tra SHA256 công bố trong release. Chỉ dùng `--version latest` khi chủ động nâng cấp.
Tải lại runtime là thao tác online chủ động; vận hành offline không gọi script chuẩn bị.

Chạy Ollama trong một terminal riêng:

```powershell
$env:OLLAMA_HOST='127.0.0.1:11434'
$env:OLLAMA_NO_CLOUD='1'
$env:OLLAMA_MODELS=Join-Path (Get-Location) '.cache/ollama/models'
$env:OLLAMA_CONTEXT_LENGTH='12288'
$env:OLLAMA_NUM_PARALLEL='1'
$env:OLLAMA_MAX_LOADED_MODELS='1'
.cache/ollama/ollama.exe serve
```

Terminal thứ hai, vẫn trong `backend/`:

```powershell
.cache/ollama/ollama.exe pull qwen3:4b-instruct-2507-q4_K_M
```

Model thử nghiệm: Qwen3 4B Q4_K_M, khoảng 2,5 GB, Apache-2.0.
Ghi digest thực tế bằng `/api/tags`; tag có thể thay đổi theo thời điểm tải.
[Model chính thức](https://ollama.com/library/qwen3:4b-instruct-2507-q4_K_M),
[Ollama tool calling](https://docs.ollama.com/capabilities/tool-calling),
[cấu hình local/cloud](https://docs.ollama.com/faq).

## Khởi động local và offline

Sau khi chuẩn bị, dùng trực tiếp interpreter đã cài để không cần truy cập package index.
Không dùng `uv sync` trong bài nghiệm thu offline.

```powershell
$env:DEBUG='false'
$env:LLM_PROVIDER='ollama'
$env:LLM_MODEL='qwen3:4b-instruct-2507-q4_K_M'
$env:LLM_BASE_URL='http://127.0.0.1:11434'
$env:LLM_CONTEXT='12288'
$env:OFFLINE='true'
.venv/Scripts/python.exe scripts/run_offline.py scripts/serve_local.py
```

Có thể lưu các biến này trong `backend/.env`; mẫu là `.env.example`.
`fake` là chế độ giả lập được ghi rõ trên UI. Gemini chỉ dùng khi chọn `LLM_PROVIDER=gemini`,
`OFFLINE=false` và có API key. Không tự fallback. Endpoint Ollama chỉ chấp nhận HTTP loopback,
không theo redirect, không dùng HTTP proxy từ môi trường; model tag cloud bị từ chối.
`/api/copilot/status` báo provider/model và kiểm tra model đã cache; không gửi chat để probe.

Frontend: cài sẵn dependencies khi online (`pnpm install --frozen-lockfile` tại `frontend/`).
Khi offline chạy `pnpm dev --host 127.0.0.1`, mở `http://127.0.0.1:5173`.
Assets/font phục vụ từ máy; Vite proxy `/api` tới backend loopback.
Nút **Làm mới dữ liệu** phát hiện experiment/run mới. Khi có run running, polling 4 giây;
khi tab ẩn, polling dừng. Quay lại tab cũng refresh.

## Train và resume

```powershell
.venv/Scripts/python.exe scripts/run_offline.py scripts/train_cifar10.py --device cuda --epochs 4 --batch-size 32
```

`run_offline.py` chặn socket/DNS ngoài loopback trong tiến trình Python được chạy.
Nó không áp đặt firewall cho Ollama, trình duyệt hay mọi tiến trình Windows.
Chuẩn bị dataset là lệnh riêng có `download=True`; train/evaluate luôn `download=False`.
Đường dẫn tương đối resolve theo `backend/`, kể cả khi gọi script từ thư mục khác.

Split stratified 45.000/5.000 từ train chính thức, 10.000 test giữ riêng.
`data/cifar10/split-42.json` lưu seed, indices, namespace train/test, classes, split hash và
normalization đo từ train split. Không chia lại giữa các run. Augmentation chỉ ở tập train tối ưu.
Train metrics để so với validation được đánh giá lại với `eval()` và transform xác định;
loss lấy tổng theo số mẫu, batch cuối không bị mất hay được tính trọng số ngang batch đầy.

Experiment `real-cifar10` tách khỏi mock; `--subset 128` tạo `real-cifar10-smoke`.
Metadata ghi architecture, versions, seed, split, ngân sách train. Baseline nhỏ mặc định;
`--architecture resnet18` dùng conv 3×3 stride 1, bỏ maxpool, 10 lớp, `weights=None`.
Không chạy sweep trước khi baseline full-data và reload checkpoint đã qua.

Mỗi run có `artifacts/cifar10/<local-id>/`: manifest, history, best/last checkpoint, status.
`best.pt` chọn val_accuracy cao nhất; hòa giữ epoch sớm nhất. `last.pt` dùng để resume:

```powershell
.venv/Scripts/python.exe scripts/run_offline.py scripts/train_cifar10.py --resume artifacts/cifar10/<local-id>/last.pt --epochs 8 --batch-size 32 --device cuda
```

Giữ architecture, seed, batch size, learning rate, weight decay, workers và subset giống lần đầu.
`epochs` là tổng epoch đích. Resume phục hồi model, Adam và RNG Python/NumPy/torch/CUDA/loader.
Target epochs mới cũng được cập nhật vào metadata API; không thay các cấu hình còn lại.
CUDA/driver khác nhau hoặc multiprocessing có thể không tái lập từng bit; workers=0 là cấu hình
được ưu tiên. Không có scheduler/scaler trong baseline này.

Checkpoint và journal ghi file tạm rồi replace trước khi gửi metrics. GET/PUT retry tối đa 3 lần;
POST không retry mù vì server có thể đã nhận. Resume đọc epochs từ API, bỏ qua bản ghi trùng khớp,
gửi lại epoch chưa log và từ chối dữ liệu xung đột/API đi trước checkpoint.
Nếu backend mất, xem `status.json` (`needs_reconciliation`), bật backend rồi resume `last.pt`.
Nếu không còn checkpoint, giữ run failed và tạo run mới; không gán completed cho run chưa log đủ.
Một run running bị bỏ lại có thể đánh failed bằng `PUT /api/runs/<id> {"status":"failed"}`.

## Evaluation và prediction

Chọn mô hình/hyperparameters bằng validation trước, sau đó mới đánh giá test:

```powershell
.venv/Scripts/python.exe scripts/run_offline.py scripts/evaluate_cifar10.py artifacts/cifar10/<local-id>/best.pt --device cuda --test --api-url http://127.0.0.1:8000
.venv/Scripts/python.exe scripts/run_offline.py scripts/predict_cifar10.py artifacts/cifar10/<local-id>/best.pt path/to/image.png
```

Evaluation lưu validation/test riêng, confusion matrix và precision/recall/support từng lớp.
Không tạo test như epoch validation. API `final_*` vẫn là epoch cuối, artifact là best checkpoint.
Artifact metadata có schema, tham chiếu tên file portable, lưu trong JSON hyperparams có sẵn;
không đổi bảng DB, run cũ nhận `artifacts=null`, không cần migration schema.

Prediction chuyển grayscale/RGBA thành RGB, resize/normalize theo checkpoint, trả softmax 10 lớp.
Ảnh hỏng/không tồn tại báo lỗi. Chỉ nạp checkpoint do mình tin cậy (`weights_only=True`).
Softmax chưa hiệu chuẩn; benchmark CIFAR-10 không chứng minh chất lượng ảnh thực tế ngoài domain.

## Tài nguyên, dữ liệu lưu và riêng tư

Giữ CNN và LLM chạy luân phiên trên 6 GB VRAM. Adapter giữ model qua các vòng tools của
một câu hỏi, rồi gọi unload (`keep_alive=0`) khi chat kết thúc, kể cả khi chat lỗi.
Nếu unload lỗi, runtime tự hết hạn sau 30 giây. Mỗi câu hỏi mới có chi phí load model.
Trước train có thể chạy
`.cache/ollama/ollama.exe stop qwen3:4b-instruct-2507-q4_K_M`, kiểm tra `nvidia-smi` và `ollama ps`.
Không tự đóng ứng dụng khác trên máy. Khi thiếu RAM giảm context/batch; không tăng workers trước khi đo.
Stream local được buffer để loại reasoning trước khi hiển thị, nên thời gian thấy chữ đầu có thể
gần thời gian hoàn thành một lượt. Context dùng ước lượng bảo thủ theo UTF-8 bytes, dành 1.024 token
cho output; vượt budget báo lỗi, không cắt metrics ngầm. Tool get_run mặc định lấy tối đa 20 epoch
quan sát đều cả đầu/cuối và báo số epoch bị lược; detect_overfitting vẫn tính trên toàn bộ timeline.
Có giới hạn 8 vòng tools và timeout mỗi request.

Luồng nghiệp vụ: browser → Vite loopback → FastAPI loopback → SQLite/filesystem;
FastAPI → Ollama loopback; model tools chỉ là 9 tools truy vấn/UI có sẵn, không có shell/file reader.
Online chuẩn bị cần PyPI, download.pytorch.org, GitHub, nguồn CIFAR Toronto và registry Ollama/CDN.
Không gọi các nguồn này trong vận hành offline. Không suy rộng một smoke test thành đảm bảo toàn máy
không bao giờ có kết nối ngoài; kiểm chứng runtime riêng bằng log/config, socket snapshots và firewall
nếu cần mức kiểm chứng mạnh hơn.

Chat lưu trong browser localStorage `copilot-chat` khi bật **Lưu lịch sử trên trình duyệt**.
Tắt tùy chọn xóa nội dung persisted, giữ cuộc trò chuyện đang mở trong RAM; reload sẽ mất nội dung đó.
**Xóa lịch sử** xóa cuộc trò chuyện hiện tại và persisted. Backend không lưu chat vào SQLite.
SQLite `backend/mlops.db` lưu metrics/metadata; `data/`, `artifacts/`, `.cache/ollama/models/` lưu dữ liệu
và weights; Ollama có cấu hình/key trong `%USERPROFILE%/.ollama`.
Tắt DEBUG để tránh SQL logs. Kiểm tra log runtime và bản backup trước khi chia sẻ.
Xóa dataset/artifacts/model cache khi không cần, xét cả backup; dùng quyền NTFS phù hợp và BitLocker
nếu cần bảo vệ ổ đĩa. `.gitignore` chỉ tránh commit, không phải mã hóa hay kiểm soát truy cập.

## Kiểm tra lại

```powershell
$env:DEBUG='false'
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp=.cache/pytest-review
.venv/Scripts/ruff.exe check app scripts training tests
.venv/Scripts/python.exe scripts/validate_local_copilot.py <experiment-id>
.venv/Scripts/python.exe scripts/run_offline.py scripts/benchmark_local_chat.py <experiment-id>
```

Để chạy bộ cấu hình nhỏ sau baseline: `python scripts/sweep_cifar10.py <baseline-last.pt>` với
interpreter trong `.venv`. Script chạy tuần tự LR giảm một nửa, batch gấp đôi, weight decay gấp mười
và ResNet-18; giữ seed/split/ngân sách. Không dùng test để chọn cấu hình.

Local copilot dùng LLM để chọn tools; nội dung best/compare/overfitting lấy trực tiếp từ kết quả
tools nhằm tránh đảo winner hoặc bịa số. Overfitting ghi rõ giá trị trung bình cửa sổ, khác epoch cuối.
Tên run trùng yêu cầu chọn experiment. Khung chat vẫn giới hạn trong các tools hiện có.

Frontend: `pnpm test`, `pnpm lint`, `pnpm build`. Unit tests không tải CIFAR/LLM, không gọi cloud;
tests training tự skip nếu không cài nhóm training. Báo cáo thực thi và các mục chưa nghiệm thu
được lưu trong `CIFAR10-IMPLEMENTATION-REPORT.md`, không lấy số mock làm kết quả.

Browser smoke thật (backend/runtime/frontend phải đang chạy; gọi tại `frontend/`):

```powershell
node scripts/cifar-browser-smoke.mjs http://127.0.0.1:5173 ../backend/artifacts/browser --chat
```

Script dùng browser có sẵn, chặn requests ngoài loopback, kiểm tra polling kể cả khi browser báo
offline, gửi câu hỏi local thực và kiểm tra camera/highlight/Inspector. Fixtures kiểm tra được xóa
sau khi chạy. Có thể bỏ `--chat` để chỉ smoke UI mà không load LLM.
