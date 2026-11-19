# Báo cáo triển khai CIFAR-10 / AI local

Ngày thực hiện: **18/11/2026**, Windows mục tiêu, múi giờ Asia/Bangkok.
Trạng thái: **Hoàn tất 33/33 task trong kế hoạch**, với phạm vi kiểm chứng offline nêu bên dưới.
Mã nguồn được sửa trực tiếp; không commit dataset, model, database hoặc secrets.
Hướng dẫn thao tác: [CIFAR10-LOCAL-RUNBOOK.md](CIFAR10-LOCAL-RUNBOOK.md).

## Môi trường đã đo

| Thành phần | Kết quả |
| --- | --- |
| OS / Python | Windows 11 build 26300 / Python 3.12.6 |
| CPU | Intel Core i7-12700H |
| RAM vật lý | 16.85 GB thập phân, khoảng 15.69 GiB |
| GPU / driver | RTX 3060 Laptop, 6144 MiB VRAM / 596.08 |
| PyTorch / Torchvision | 2.7.1+cu126 / 0.22.1+cu126 |
| CUDA | Build 12.6; forward/backward thực chạy CUDA, output [2,10] |
| Dung lượng đĩa trống sau chuẩn bị | Khoảng 202 GB, thay đổi theo hoạt động trên máy |
| Ollama portable | v0.40.16, SHA256 archive `50fcf5ad54277f2fa5d173ebfc93bcb017adbc0c9ef2314daabc96ca9e6aa64e` |
| Model chọn | `qwen3:4b-instruct-2507-q4_K_M`, 2.497 GB, Q4_K_M, Apache-2.0 |
| Model digest | `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0` |

RAM trống biến động mạnh do các ứng dụng khác: có lúc dưới 1 GB. Không đóng ứng dụng của
người dùng. Chạy CNN và LLM luân phiên; không nghiệm thu training đồng thời với LLM.
Danh sách package và số đo thô nằm ở `backend/artifacts/environment.json`,
`backend/artifacts/ollama-model.json`. Dependency graph backend mặc định đã kiểm tra không có torch.

Nguồn phiên bản: [PyTorch](https://pytorch.org/get-started/previous-versions/),
[model Ollama](https://ollama.com/library/qwen3:4b-instruct-2507-q4_K_M),
[Ollama API](https://docs.ollama.com/api/chat).

## Dataset và kết quả training thật

CIFAR-10 chính thức đã tải và vượt integrity checks của Torchvision. Chuẩn bị lại tái sử dụng
archive/dataset, không tạo bản sao. Train/evaluate/predict không tự download.
Split seed 42: **45.000 train / 5.000 validation / 10.000 test**. Train/validation indices không
giao nhau; test thuộc namespace official-test riêng. Mỗi lớp validation có 500 ảnh.

Split ID: `9547836cf14a8ab336ad597af4006b8764935e9dc0d8c636d879f1c3df48071f`.
Normalization đo chỉ từ train split: mean ≈ [0.491351, 0.482068, 0.446550],
std ≈ [0.247132, 0.243621, 0.261721]. Validation/inference dùng transform xác định giống nhau.
Các indices đầy đủ và thống kê lưu tại `backend/data/cifar10/split-42.json`.

Tất cả run bên dưới dùng seed 42, Adam, cùng split và **4 epoch full-data**,
không dùng test để chọn cấu hình. Bốn run CNN thay từng yếu tố riêng so với baseline.

| Run ID | Model | LR | Batch | Weight decay | Best val accuracy | Final val accuracy | Best epoch | Tổng giây các epoch | Peak RSS GiB | Peak torch allocated MiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 75 | CNN baseline | 0.001 | 32 | 0.0001 | 0.6910 | 0.6910 | 4 | 288.1 | 1.53 | 36.3 |
| 76 | CNN | 0.0005 | 32 | 0.0001 | 0.6946 | 0.6946 | 4 | 275.7 | 1.53 | 36.3 |
| 77 | CNN | 0.001 | 64 | 0.0001 | 0.6982 | 0.6982 | 4 | 204.4 | 1.54 | 50.3 |
| 78 | CNN | 0.001 | 32 | 0.001 | 0.6802 | 0.6802 | 4 | 92.3 | 1.54 | 36.3 |
| 79 | ResNet-18 CIFAR | 0.001 | 32 | 0.0001 | **0.7574** | **0.7488** | **3** | 349.6 | 1.66 | 329.6 |

Experiment thật: `real-cifar10` (ID 5). Cả năm run completed và metrics API khớp journal trainer.
Đối soát cuối cả năm run được lưu tại `backend/artifacts/tracking-consistency.json`.
Thời gian ở bảng là tổng train + train-eval + validation từng epoch, không gồm startup,
checkpoint IO hoặc API logging. Máy còn chạy ứng dụng khác và checks trong một phần thời gian,
nên không dùng chênh lệch thời gian này để kết luận nhân quả về hyperparameters.
RSS là peak working set tiến trình trên Windows. VRAM ở bảng là peak allocated của PyTorch,
không phải tổng VRAM driver, desktop và các tiến trình khác.

Baseline epoch 1–4 có val_accuracy: **0.5228, 0.5820, 0.6568, 0.6910**.
Model đã overfit được batch fixture nhỏ trong unit test; đây chỉ là chẩn đoán pipeline.
ResNet dùng conv 3×3 stride 1, bỏ maxpool đầu, classifier 10 lớp, `weights=None`.

## Checkpoint, test và prediction

Mô hình chốt bằng validation: run **79**, `best.pt` **epoch 3**.

| Tập | Số ảnh | Accuracy | Loss |
| --- | --- | --- | --- |
| Validation | 5.000 | 0.7574 | 0.715747 |
| Test cuối | 10.000 | **0.7489** | **0.744081** |

Run 79 epoch cuối là 4, val_accuracy 0.7488. API `final_*` và xếp hạng run tiếp tục dùng epoch cuối;
artifact metadata và Inspector hiển thị best epoch 3 riêng. Không sửa nghĩa dữ liệu cũ.
Metadata artifact có schema và lưu trong JSON hyperparams có sẵn; không thay cấu trúc bảng DB.
Run cũ không có artifact vẫn đọc được. Không trả absolute checkpoint paths qua API.

Artifact đã dùng:

- CNN baseline: `backend/artifacts/cifar10/1a413c0cba694c5386c56c04c3e727f3/`.
- Model chọn: `backend/artifacts/cifar10/9979d2c952de4169896f89625e3bc3d0/`.
- So sánh: `backend/artifacts/cifar10/sweep.json`.
- Test/confusion matrix/precision/recall/support: `evaluation-test.json` trong thư mục model chọn.

Checkpoint đã nạp trong tiến trình mới khi chặn Python egress. Prediction CLI chạy được trên
ảnh local, grayscale/RGBA được kiểm thử; ảnh hỏng/thiếu có lỗi rõ. Ảnh minh họa là ảnh train CIFAR
đầu tiên, không phải ảnh riêng. Model dự đoán dog trong khi nhãn thật là frog: pipeline chạy được
không có nghĩa mọi ảnh đều đúng. Softmax chưa hiệu chuẩn và chỉ có 10 lớp CIFAR-10.

Resume phục hồi model/optimizer/RNG và đối soát epochs trước khi log lại. Test mô phỏng server
đã commit metric rồi ngắt response chứng minh không gửi trùng epoch khi resume; checkpoint và
trạng thái needs_reconciliation vẫn được giữ. Target epochs cập nhật vào metadata khi resume.
Tái lập từng bit trên CUDA/driver khác không được bảo đảm.

## Copilot và dữ liệu được kiểm chứng

Provider chọn tường minh; `.env` local đã chọn Ollama, `OFFLINE=true`, context 12288.
Key cloud cũ được giữ riêng, không tự kích hoạt Gemini. Ollama bind 127.0.0.1, cloud disabled;
API không tự tải model hoặc fallback. `/api/copilot/status` báo model/provider và cache availability.

Thử nghiệm đầu với tag `qwen3:4b` xác định đây là bản Thinking. Cấu hình đầu có context 16384
và unload mỗi request mất khoảng 162 giây cho câu hỏi best. Cấu hình Instruct + context 12288,
giữ model qua các vòng tools và unload sau chat đo khoảng 66 giây. Nhiều biến được thay đổi cùng
lúc nên không quy mức cải thiện cho riêng model. Số đo lần Instruct:

- Chữ đầu người dùng thấy: khoảng 64,1 giây; hoàn tất khoảng 66,2 giây, gồm cold load.
- Peak GPU toàn hệ thống quan sát: **4225 MiB**; peak RSS runtime quan sát: khoảng **1,20 GiB**.
- RAM trống thấp nhất quan sát: khoảng 0,89 GiB; không OOM trong lượt này.
- Không thấy kết nối runtime ra ngoài loopback trong các socket snapshots; không có lỗi quan sát.
- Sampling khoảng 1 giây, GPU bao gồm desktop/ứng dụng khác; không phải profiler mọi network attempt.

SSE local buffer trước hiển thị để không lộ reasoning. Thời gian chữ đầu không tương đương
thời gian token đầu nội bộ. Native stream kết thúc bằng reply đầy đủ; malformed/truncated/timeout
được xử lý và model được giải phóng sau chat. Không chạy benchmark CNN/LLM đồng thời vì RAM trống hạn chế.

Đối chiếu thủ công phát hiện model từng đảo kết luận winner dù chép đúng bảng, lẫn giá trị cửa sổ
overfitting với epoch cuối và tự chọn một run trùng tên. Đã sửa bằng:

- LLM tiếp tục chọn tools và arguments; best/compare/overfitting được render từ dữ liệu tool đã xác thực.
- Chặn cả text delta sai trước khi hiển thị; không chỉ thay câu trả lời cuối.
- Nhận xét overfitting ghi rõ trung bình cửa sổ và tính heuristic.
- Tên trùng giữa experiment được yêu cầu chọn experiment trước khi gọi LLM.
- Bộ nghiệm thu kiểm tra winner, số liệu, semantics và UI actions; không chỉ kiểm tra văn phong.

Lượt nghiệm thu cuối: **7/7 tình huống đạt**, **0 lỗi tools**, đã đối chiếu nội dung và UI actions:

| Tình huống | Kết quả |
| --- | --- |
| Best run | Đúng run 79, final val_accuracy 0.7488 và trung vị 0.6946; đủ highlight/focus/Inspector |
| Compare | Đúng run 76 thắng val_accuracy, run 75 thắng val_loss; bảng và chênh lệch khớp DB |
| Overfitting | Đúng tên run; gap cửa sổ 0.0012 → 0.0095; không bịa số hay kết luận tuyệt đối |
| Run không tồn tại | Báo không tìm thấy, không có UI actions |
| Thiếu validation | Báo chưa đủ dữ liệu, không đoán verdict |
| Tên trùng experiment | Yêu cầu chọn experiment, không tự chọn run hoặc gọi LLM |
| Ngoài khả năng | Từ chối chạy shell/upload, không có tools/UI actions |

Chín tool schemas cùng prompt có payload fixture khoảng 7.266 bytes; fixture 20 epoch khoảng
9.983 bytes được guard context chấp nhận, fixture 50 epoch bị từ chối có lỗi context rõ.
Các fixture chỉ đo budget, không gửi tới LLM. Prompt native dài
nhất quan sát trong log là 2.727 tokens trên context 12.288. Fixtures đo context không phải run
huấn luyện thật. Bằng chứng: `backend/artifacts/context-budget.json`.
Raw evidence: `backend/artifacts/copilot-acceptance.json`; lượt trước sửa được giữ riêng tại
`copilot-acceptance-before-grounding.json`. Bộ câu hỏi nhỏ không chứng minh mọi câu hỏi tự do đều đúng.

## Regression, UI và phạm vi offline

- Backend: **305 passed, 7 skipped**, coverage khoảng **95%**. Bảy live tests bị skip theo cấu hình;
  nghiệm thu Ollama thật chạy bằng script riêng, không gọi Gemini.
- Frontend: **115 passed**, coverage lines khoảng **98,09%** trong các vùng cấu hình đo coverage.
- Ruff format/lint, TypeScript, ESLint, production build đều đạt. Build còn cảnh báo bundle >500 kB
  do ứng dụng 3D; không phải lỗi build.
- CI bổ sung CPU training regression với fixtures, không tải CIFAR/LLM; GitHub Actions chưa chạy từ
  thay đổi local vì chưa commit/push.
- Browser smoke đã kiểm tra curves thật, best checkpoint, chat privacy, polling epoch/status và đổi
  experiment, kể cả khi `navigator.onLine=false`. Không có page errors hoặc request ngoài loopback.
  Lượt cuối chờ đúng state/stream hoàn tất, xác nhận chat chọn run 79, camera/Inspector/highlight
  đều trỏ run 79. Bài smoke ban đầu có lỗi chờ quá sớm và đã sửa, không dùng kết quả đó làm nghiệm thu.

Luồng offline cuối: resume smoke run 80 từ epoch 1 lên 2 → API khớp journal và không trùng epoch →
chat thực trên browser → reload best checkpoint trong tiến trình mới → predict. Smoke dùng 128 ảnh,
lưu riêng ở real-cifar10-smoke, không đưa vào bảng chất lượng full-data. Tie val_accuracy giữ epoch
sớm nhất. `/api/ps` xác nhận model LLM đã unload khi kết thúc chat.
Bằng chứng: `backend/artifacts/offline-resume.json`, `predict-offline.json`,
`browser/result.json`, `browser/local-chat.json`, `browser/real-cifar10.png`.
Evaluation CLI cũng chạy thành công từ thư mục repo root thay vì backend, đọc đủ 5.000 validation
samples và tái tạo accuracy 0.7574, xác nhận đường dẫn dataset/artifacts độc lập thư mục gọi lệnh.

Offline được kiểm tra theo tiến trình: Python socket/DNS guard chặn ngoài loopback; browser route
chặn request ngoài loopback; runtime chạy từ cache trong môi trường thực thi hạn chế mạng và tắt cloud.
Backend/runtime/frontend đã khởi động lại từ dependencies/assets có sẵn. Không thay firewall toàn
Windows hoặc ngắt mạng của ứng dụng khác. Không tuyên bố mọi tiến trình trên máy không kết nối Internet.

Chat persistent có thể tắt hoặc xóa từ UI. SQLite lưu metrics/metadata; images/weights ở filesystem,
không nhúng binaries vào DB. Quyền truy cập, BitLocker, backup và cách xóa được hướng dẫn trong runbook;
`.gitignore` không được coi là mã hóa. Dataset/model/checkpoints/cache đã xác minh được Git ignore.
