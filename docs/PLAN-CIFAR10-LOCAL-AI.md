# Kế hoạch chuyển sang CIFAR-10 thật và AI local

Ngày lập: **18/11/2026**  
Trạng thái: **Đã triển khai và nghiệm thu 33/33 task trên Windows mục tiêu — 18/11/2026**

Bằng chứng và giới hạn kiểm chứng: [Báo cáo triển khai](CIFAR10-IMPLEMENTATION-REPORT.md).
Hướng dẫn cài đặt, offline, resume và phục hồi: [Runbook](CIFAR10-LOCAL-RUNBOOK.md).

Tài liệu này bổ sung cho [PLAN.md](PLAN.md), tập trung vào chuyển dữ liệu thí nghiệm giả lập sang kết quả huấn luyện thật và thay kết nối AI bên ngoài bằng suy luận trên máy cá nhân.

## 1. Mục tiêu và phạm vi

Khi hoàn thành, người dùng có thể:

1. Tải CIFAR-10 chuẩn về máy một lần, sau đó huấn luyện khi không có Internet.
2. Train CNN, ghi metrics thật vào backend và theo dõi trên giao diện 3D hiện có.
3. Lưu, nạp lại checkpoint và phân loại ảnh bằng mô hình local.
4. Hỏi copilot bằng tiếng Việt về kết quả thí nghiệm thông qua LLM local và các tools hiện có.
5. Chạy toàn bộ luồng vận hành mà không gửi câu hỏi, metrics hoặc dữ liệu ảnh đến nhà cung cấp AI bên ngoài.

**Hai mô hình độc lập:** CNN được huấn luyện bằng CIFAR-10 để phân loại ảnh; LLM dùng trọng số tải sẵn để hiểu câu hỏi và gọi tools. Không dùng CIFAR-10 để huấn luyện trợ lý chat. Chưa cần fine-tune LLM.

### Cấu hình và lựa chọn đã thống nhất

| Hạng mục | Quyết định |
| --- | --- |
| Máy phát triển | Windows, RAM 16 GB |
| GPU đã kiểm tra | NVIDIA RTX 3060 Laptop, VRAM 6 GB |
| Dataset | CIFAR-10 chuẩn qua `torchvision.datasets.CIFAR10` |
| Framework | PyTorch + Torchvision; không cài thêm TensorFlow cho pipeline này |
| Thư mục dataset | `backend/data/cifar10`, tương ứng `./data/cifar10` khi đứng tại `backend/` |
| Chia tập | 45.000 train, 5.000 validation, 10.000 test |
| Phương án ban đầu | CNN nhỏ, batch size 32; tăng quy mô sau khi đo bộ nhớ |
| Copilot | Runtime local hỗ trợ tools, ưu tiên tích hợp Ollama; thử model nhỏ khoảng 4B lượng tử hóa |
| Quản lý GPU | Train và chạy LLM luân phiên trước; chạy đồng thời là tối ưu bổ sung |

Tên/tag LLM, bản PyTorch/CUDA và batch size cuối cùng phải được xác minh trong bước chuẩn bị môi trường. Chưa cam kết tốc độ hay accuracy trước khi benchmark.

### Giới hạn phiên bản đầu

- Training được khởi chạy bằng CLI; chưa cần job scheduler hay nút train trên web.
- Inference ảnh có CLI trước; API/upload ảnh trên web là phần mở rộng.
- Tiếp tục dùng FastAPI, SQLite, giao diện React/3D và client tracking hiện có.
- Chưa triển khai multi-user, public hosting, distributed training hoặc model registry đầy đủ.
- Chạy local giúp kiểm soát luồng dữ liệu; không tự bảo đảm an toàn nếu máy, tài khoản hay bản sao lưu bị truy cập trái phép.

## 2. Hiện trạng trước triển khai (đối chiếu source ban đầu)

| Vị trí | Hiện trạng | Hướng xử lý |
| --- | --- | --- |
| `backend/app/utils/seed_data.py` | Sinh metrics giả, có experiment `mock-cifar10-resnet18` | Giữ cho development/test; tạo experiment thật riêng |
| `backend/scripts/train_mnist_demo.py` | Train scikit-learn MLP trên digits/MNIST | Giữ demo; thêm trainer CIFAR-10 riêng |
| `backend/scripts/log_to_api.py` | Tạo experiment/run, ghi metrics, cập nhật trạng thái | Tái sử dụng, bổ sung độ bền khi cần |
| `backend/app/services/tracking.py` | Xếp hạng completed runs theo metric của epoch cuối | Giữ nghĩa hiện tại; bổ sung thông tin best checkpoint tách biệt |
| `backend/app/schemas/metric.py` | Hỗ trợ accuracy/loss và validation tương ứng | Dùng trực tiếp cho metrics theo epoch |
| `backend/app/services/copilot/llm_client.py` | Có interface chung, Gemini client và fake client | Thêm adapter local và chọn provider rõ ràng |
| `backend/app/services/copilot/engine.py` | Vòng lặp tools, giới hạn số vòng, hỗ trợ streaming | Tái sử dụng; điều chỉnh lỗi/timeout cho local |
| `frontend/src/hooks/useRuns.ts` | Lấy dữ liệu bằng SWR, chưa polling định kỳ | Thêm polling có điều kiện khi training |
| `frontend/src/components/panels/InspectorPanel.tsx` | Hiện metrics cuối và hyperparameters | Bổ sung đường cong học và thông tin checkpoint |
| `frontend/src/store/useChatStore.ts` | Lưu lịch sử vào localStorage | Thêm tùy chọn không lưu và xóa dữ liệu |
| `backend/pyproject.toml` | Chưa khai báo PyTorch/Torchvision; httpx nằm trong dev | Tách dependencies training và runtime local hợp lý |

Chưa có pipeline lưu/nạp checkpoint hoặc endpoint phân loại ảnh. Không suy ra chất lượng CIFAR-10 thật từ các metrics mock đang có.

## 3. Kiến trúc và quy ước dữ liệu

```text
Chuẩn bị online một lần
  ├─ Tải dependencies / gói cài đặt cần thiết
  ├─ Tải CIFAR-10 train + test → backend/data/cifar10
  └─ Tải trọng số LLM local

Vận hành offline
  CIFAR-10 local → Trainer CNN → Checkpoint + manifest local
                       ↓                    ↓
                  Tracking API        CLI dự đoán ảnh
                       ↓
                     SQLite ← Tools truy vấn ← LLM local
                       ↓                         ↑
                Giao diện 3D                 Khung chat
```

### Quy ước phải giữ

- Đường dẫn được resolve từ vị trí project/backend, không phụ thuộc thư mục gọi lệnh.
- Trainer/inference không tự tải dữ liệu hoặc trọng số; bước chuẩn bị online là lệnh riêng.
- Accuracy luôn nằm trong `[0, 1]`; loss là trung bình theo số mẫu, không lấy trung bình các batch thiếu trọng số.
- Validation/test dùng preprocessing xác định, không augmentation ngẫu nhiên.
- Metrics train dùng để chẩn đoán overfitting nên được đánh giá bằng `model.eval()` trên train subset với transform xác định, tách khỏi loss tối ưu trên batch có augmentation. Ghi rõ cách tính để tránh diễn giải sai khoảng cách train/validation.
- Giữ `final_*` là epoch cuối đã log. Best checkpoint, best epoch và test result là các thông tin riêng.
- Lưu ảnh và trọng số trên filesystem; SQLite lưu metadata/tham chiếu, không nhúng toàn bộ dữ liệu nhị phân.
- Chế độ local không tự fallback sang Gemini hay endpoint cloud khi lỗi.

### Bố trí file dự kiến

```text
backend/
  app/services/copilot/         # Thêm adapter local, giữ interface hiện có
  training/                    # Dataset, models, trainer, checkpoint dùng chung
  scripts/
    prepare_cifar10.py
    train_cifar10.py
    evaluate_cifar10.py
    predict_cifar10.py
  data/cifar10/                # Dataset, không commit
  artifacts/cifar10/<run_id>/  # Checkpoint, manifest, kết quả đánh giá, không commit
```

Tên file là thiết kế dự kiến; có thể điều chỉnh khi triển khai nếu giữ ranh giới trách nhiệm rõ ràng.

## 4. Danh sách task và tiêu chí nghiệm thu

Mỗi checkbox chỉ được đánh dấu sau khi đáp ứng tiêu chí nghiệm thu. Hoàn thành từng giai đoạn trước khi tăng số run hoặc độ lớn mô hình.

### Giai đoạn A — Chuẩn bị môi trường

**Phụ thuộc:** Không. **Đầu ra:** Môi trường train và local inference đã được xác minh.

- [x] **A01 — Kiểm kê môi trường.** Ghi Python, GPU/driver, RAM khả dụng, dung lượng đĩa và môi trường package hiện tại. **Nghiệm thu:** Có bảng cấu hình thực đo; không ghi secrets vào báo cáo.
- [x] **A02 — Tách dependencies.** Thêm nhóm training với torch/torchvision và các thư viện trực tiếp sử dụng; đưa HTTP client dùng ở runtime vào nhóm phù hợp. Chọn cặp torch/torchvision và CUDA build tương thích, cập nhật lockfile. **Nghiệm thu:** Backend thông thường không bắt buộc cài bộ training; hướng dẫn cài mới chạy được trên Windows mục tiêu.
- [x] **A03 — Xác minh CUDA.** Kiểm tra `torch.cuda.is_available()`, tên GPU và chạy forward/backward nhỏ. **Nghiệm thu:** Xác nhận tính toán thực sự chạy trên GPU; có CPU fallback rõ ràng, không im lặng đổi thiết bị.
- [x] **A04 — Chuẩn hóa thư mục và Git.** Tạo quy ước data/artifacts/cache; cập nhật `.gitignore` cho dữ liệu, checkpoint, credentials tải dữ liệu/model nếu có. **Nghiệm thu:** Dataset và trọng số không xuất hiện trong danh sách file sẽ commit; file cấu hình mẫu vẫn theo dõi được.

**Điểm kiểm tra A:** Chưa tải/train toàn bộ khi CUDA và dependencies chưa được xác nhận.

### Giai đoạn B — Dataset thật và khả năng tái lập

**Phụ thuộc:** A. **Đầu ra:** CIFAR-10 local có split cố định và manifest.

- [x] **B01 — Lệnh chuẩn bị dữ liệu.** Thêm `prepare_cifar10.py`, tải cả train/test bằng `download=True` vào thư mục chuẩn. **Nghiệm thu:** Chạy lại không tạo bản sao không cần thiết; dataset vượt qua kiểm tra integrity của loader.
- [x] **B02 — Chế độ chỉ đọc local.** Các lệnh train/evaluate dùng `download=False`. **Nghiệm thu:** Khi thiếu/hỏng dữ liệu, báo đường dẫn và cách chuẩn bị; không phát sinh yêu cầu download.
- [x] **B03 — Split cố định.** Chia stratified 45.000/5.000 từ 50.000 mẫu train, giữ 10.000 test độc lập. Lưu indices, seed, mapping lớp và định danh dataset. **Nghiệm thu:** Ba tập không giao nhau; cùng manifest cho cùng split giữa mọi run.
- [x] **B04 — Preprocessing.** Chuyển RGB/tensor; augmentation chỉ cho train; normalization dùng hằng số đã ghi nguồn hoặc thống kê từ train split. Tạo dataset evaluation riêng để không dùng nhầm transform train cho validation. **Nghiệm thu:** Tensor có shape `[3, 32, 32]`, labels 0–9; preprocessing inference khớp evaluation.
- [x] **B05 — DataLoader phù hợp Windows.** Bắt đầu `num_workers=0`, cấu hình seed cho worker khi bật multiprocessing, có main guard. **Nghiệm thu:** Đọc đủ mẫu, kiểm tra batch cuối và chạy được từ thư mục làm việc khác.

**Điểm kiểm tra B:** Đọc train/validation/test thành công khi đã ngắt Internet.

### Giai đoạn C — Training thật và tracking

**Phụ thuộc:** B. **Đầu ra:** Một run CNN thật hoàn chỉnh xuất hiện trong hệ thống.

- [x] **C01 — CNN baseline.** Tạo mạng nhỏ có đầu vào 3 kênh, đầu ra logits 10 lớp; cấu hình seed và device. **Nghiệm thu:** Forward/backward thành công; checkpoint có định danh kiến trúc và cấu hình dựng lại model.
- [x] **C02 — Training loop.** Thêm train/eval đúng chế độ, cross-entropy, optimizer, metrics tính theo mẫu; hỗ trợ batch size, learning rate, epochs và seed qua CLI. **Nghiệm thu:** Chạy thử subset nhỏ và xác minh model có thể overfit một batch nhỏ để kiểm tra pipeline; không coi đó là kết quả chất lượng dataset.
- [x] **C03 — Nối TrackingClient.** Tạo experiment thật riêng, log bốn metrics mỗi epoch, trạng thái running/completed/failed. Lưu model, dataset/split ID, seed, versions và cấu hình trong metadata. **Nghiệm thu:** Số liệu API khớp kết quả trainer, không trộn với experiment mock.
- [x] **C04 — Checkpoint và resume.** Lưu `best.pt` theo val_accuracy (quy tắc xử lý hòa được ghi rõ), `last.pt`, model state, optimizer/scheduler/scaler state nếu dùng, epoch và RNG state cần thiết. Ghi file nguyên tử và manifest. **Nghiệm thu:** Nạp lại được; resume tiếp đúng epoch, không ghi trùng metrics; ghi rõ giới hạn tái lập trên CUDA.
- [x] **C05 — Xử lý sự cố tracking.** Kiểm tra health trước train; định nghĩa retry có giới hạn cho lỗi tạm thời. Khi không thể log, lưu checkpoint và trạng thái cục bộ để đối soát; không báo hoàn thành giả. **Nghiệm thu:** Backend mất kết nối không làm mất toàn bộ tiến độ; trạng thái failed/running còn sót được xử lý theo hướng dẫn cụ thể.
- [x] **C06 — Chạy baseline đầy đủ.** Train CNN trên split thật với batch 32, đo thời gian/epoch và peak VRAM/RAM. **Nghiệm thu:** Có run completed, đường cong học hữu hạn và checkpoint tốt nhất; ghi nhận accuracy thực đo, không đặt kết quả mock làm chuẩn.

**Điểm kiểm tra C:** Một run full-data đã log đầy đủ và nạp lại được checkpoint trước khi chạy sweep.

### Giai đoạn D — Đánh giá, inference và chất lượng mô hình

**Phụ thuộc:** C. **Đầu ra:** Mô hình dùng lại được và kết quả đánh giá đáng tin cậy.

- [x] **D01 — Thông tin artifact và best epoch.** Bổ sung metadata/tham chiếu artifact có schema rõ ràng cho run; giữ nguyên nghĩa `final_*`. Nếu đổi DB, có migration và kiểm thử tương thích dữ liệu cũ. **Nghiệm thu:** Người dùng phân biệt được epoch cuối và checkpoint tốt nhất; API không trả đường dẫn nhạy cảm không cần thiết.
- [x] **D02 — Evaluation CLI.** Nạp best checkpoint, tính validation metrics; bổ sung test accuracy/loss, confusion matrix và thống kê theo lớp. Chỉ dùng test để đánh giá cuối sau khi chốt lựa chọn bằng validation. **Nghiệm thu:** Test result lưu riêng, không giả thành một epoch validation và không dùng để chọn hyperparameters.
- [x] **D03 — Prediction CLI.** Nhận ảnh local, áp dụng preprocessing đã lưu, trả nhãn và xác suất dự đoán. **Nghiệm thu:** Model nạp được trong tiến trình mới, offline; xử lý rõ ảnh hỏng, grayscale/RGBA và input không hợp lệ; xác suất không được diễn giải là độ tin cậy đã hiệu chuẩn.
- [x] **D04 — ResNet-18 cho CIFAR-10.** Sau baseline, thử stem phù hợp ảnh 32×32 (conv 3×3 stride 1, bỏ maxpool đầu), classifier 10 lớp, khởi tạo không tải trọng số ngầm. **Nghiệm thu:** Chạy được trên 6 GB VRAM với cấu hình đã đo; so sánh cùng split và ngân sách train được ghi rõ.
- [x] **D05 — Thí nghiệm có kiểm soát.** Chạy lần lượt một tập nhỏ cấu hình learning rate/batch size/weight decay; giữ split cố định, ghi seed và ngân sách. **Nghiệm thu:** Có bảng so sánh validation, thời gian và bộ nhớ; không kết luận quan hệ nhân quả từ vài run hoặc hứa mức accuracy chưa đo.

**Điểm kiểm tra D:** Có checkpoint được chọn bằng validation và báo cáo test riêng cho cấu hình đã chốt.

### Giai đoạn E — Copilot local

**Phụ thuộc:** A; dùng dữ liệu thật từ C để nghiệm thu cuối. **Đầu ra:** Chat qua tools mà không gọi AI cloud.

- [x] **E01 — Chuẩn bị runtime/model.** Cài runtime local, tải trước model hỗ trợ tools và tiếng Việt; thử model khoảng 4B lượng tử hóa, ghi tag/digest, giấy phép và dung lượng. **Nghiệm thu:** Model đã cache, chạy offline và đo được bộ nhớ; lựa chọn model dựa trên bài kiểm tra thực tế.
- [x] **E02 — Chọn provider tường minh.** Bổ sung `LLM_PROVIDER`, `LLM_BASE_URL` và cấu hình model/timeout/context. Giữ fake cho test và Gemini chỉ khi chọn rõ chế độ cloud; profile offline từ chối endpoint ngoài loopback. **Nghiệm thu:** Local không phụ thuộc việc API key cũ còn tồn tại; cấu hình sai dừng với thông báo rõ, không fallback cloud.
- [x] **E03 — Adapter local.** Triển khai `complete()` và `stream()` theo `LLMClient`, ánh xạ messages/tools/tool results; chuẩn hóa call IDs nội bộ khi provider không trả ID. **Nghiệm thu:** Tool round-trip đúng, streaming kết thúc bằng reply hoàn chỉnh, không hiển thị phần reasoning nội bộ.
- [x] **E04 — Độ bền và context.** Xử lý timeout/model thiếu/tool arguments lỗi/response rỗng; giữ giới hạn vòng gọi tools. Đo kích thước context với chín tools hiện có và kết quả nhiều epoch, thu gọn có chủ đích nếu vượt giới hạn. **Nghiệm thu:** Không treo chat, không cắt số liệu âm thầm, lỗi không còn mặc định nhắc quota Gemini khi đang local.
- [x] **E05 — Kiểm tra năng lực trên dữ liệu thật.** Bộ câu hỏi gồm best run, so sánh, overfitting, run không tồn tại, thiếu validation, tên trùng experiment và yêu cầu ngoài khả năng. **Nghiệm thu:** Đối chiếu số liệu với DB, ghi tỷ lệ trả lời đúng và lỗi tools; không chỉ đánh giá câu trả lời nghe hợp lý. Heuristic overfitting được diễn giải là dấu hiệu, không là bằng chứng tuyệt đối.

**Điểm kiểm tra E:** Ba tác vụ chính (best/compare/overfitting) chạy offline với số liệu và UI actions đúng; mọi lỗi dữ liệu trong bộ nghiệm thu được sửa hoặc công bố trước khi dùng dữ liệu nhạy cảm.

### Giai đoạn F — Giao diện theo dõi training thật

**Phụ thuộc:** C, D01; F03 cần E. **Đầu ra:** Người dùng thấy trạng thái và ý nghĩa kết quả rõ ràng.

- [x] **F01 — Polling có điều kiện.** Refresh danh sách khi có run running, bắt đầu khoảng 3–5 giây/lần; refresh khi quay lại tab hoặc theo thao tác người dùng để phát hiện run mới. Đồng bộ run detail khi cần và giảm polling khi tab ẩn. **Nghiệm thu:** Run mới/epoch mới/trạng thái hoàn thành xuất hiện; không polling dồn dập hay đổi experiment ngoài ý muốn.
- [x] **F02 — Learning curves và checkpoint.** Dùng API run detail để vẽ train/validation curves, hiện best epoch và tiêu chí chọn checkpoint. **Nghiệm thu:** Run cũ không có artifact vẫn hiển thị được; biểu đồ dùng metrics thật, không nội suy thành dữ liệu quan sát.
- [x] **F03 — Hiển thị chế độ hoạt động.** Thêm trạng thái provider/model và khả dụng của local runtime từ backend; đổi hướng dẫn trạng thái trống để chỉ tới training thật phù hợp. **Nghiệm thu:** Người dùng phân biệt local/fake/cloud; không lộ secrets hoặc đường dẫn riêng không cần thiết.

### Giai đoạn G — Riêng tư, offline và bàn giao

**Phụ thuộc:** C–F. **Đầu ra:** Demo offline có bằng chứng và hướng dẫn tái lập.

- [x] **G01 — Rà luồng dữ liệu.** Bind backend/runtime loopback, tắt cloud của runtime, kiểm tra endpoint/proxy và các kết nối ngầm của thư viện/UI; không cho model thực thi shell hay đọc file tùy ý. **Nghiệm thu:** Lập danh sách luồng mạng cần thiết và xác nhận đường dữ liệu nghiệp vụ chỉ ở local.
- [x] **G02 — Dữ liệu lưu trên máy.** Thêm lựa chọn không lưu lịch sử chat, thao tác xóa rõ ràng; kiểm tra localStorage, SQL/debug logs, file artifacts và chính sách backup. Hướng dẫn quyền truy cập và mã hóa ổ đĩa phù hợp. **Nghiệm thu:** Người dùng biết dữ liệu lưu ở đâu và cách xóa; `.gitignore` không được coi là cơ chế mã hóa.
- [x] **G03 — Kiểm thử offline thực tế.** Sau chuẩn bị online, ngắt mạng ngoài hoặc chặn egress, khởi động mới backend/frontend/runtime và chạy train ngắn → metrics → chat → reload checkpoint → predict. Kèm quan sát kết nối/attempt nếu công cụ cho phép. **Nghiệm thu:** Không cần download, DNS hay fallback cloud; ghi rõ phạm vi kiểm chứng, không tuyên bố mọi tiến trình trên máy không bao giờ kết nối Internet chỉ từ một lần thử.
- [x] **G04 — Benchmark tài nguyên.** Đo CNN và LLM riêng, sau đó mới thử đồng thời nếu còn dư bộ nhớ; ghi RAM/VRAM, thời gian/epoch, thời gian có chữ đầu và hoàn tất chat. **Nghiệm thu:** Có cấu hình ổn định trên RAM 16 GB/VRAM 6 GB, không OOM; quy trình luân phiên giải phóng model khỏi GPU được hướng dẫn rõ.
- [x] **G05 — Regression và tài liệu vận hành.** Chạy checks hiện có và tests bổ sung đúng phạm vi thay đổi; cập nhật README/hướng dẫn CLI, cài online, vận hành offline, resume, phục hồi lỗi và giới hạn mô hình. **Nghiệm thu:** Người khác có thể làm theo; báo cáo tách kết quả đã chạy khỏi giả định/chưa kiểm tra.

## 5. Thứ tự thực hiện và mốc bàn giao

| Mốc | Task | Kết quả có thể review |
| --- | --- | --- |
| M1 — Môi trường và dữ liệu | A01–A04, B01–B05 | CUDA hoạt động, dataset đọc offline, split có manifest |
| M2 — Một run thật | C01–C06 | CNN train full-data, metrics trong SQLite, checkpoint nạp được |
| M3 — Dùng lại mô hình | D01–D03 | Metadata best checkpoint, evaluation và prediction CLI |
| M4 — Copilot local | E01–E05 | Adapter provider và báo cáo độ đúng khi truy vấn dữ liệu thật |
| M5 — Theo dõi thuận tiện | F01–F03 | Run cập nhật trên UI, learning curves, trạng thái provider |
| M6 — Nghiệm thu offline | G01–G05 | Demo offline, benchmark máy mục tiêu, tài liệu vận hành |
| M7 — Cải thiện chất lượng | D04–D05 | ResNet-18 và bảng so sánh thực nghiệm có kiểm soát |

Đưa baseline CNN và copilot local vào trạng thái ổn định trước khi đầu tư nhiều thời gian vào sweep. D04–D05 có thể thực hiện sau M6 để nghiệm thu kiến trúc sớm.

## 6. Kế hoạch kiểm thử

| Nhóm | Kiểm tra cần thiết | Cách chạy |
| --- | --- | --- |
| Dataset | Split không giao nhau, đủ mẫu/lớp, transform đúng, không download trong offline mode | Unit tests với fixture nhỏ; integrity trên dữ liệu local là kiểm tra tích hợp riêng |
| Training | Gradient, loss/accuracy có trọng số theo mẫu, eval mode, checkpoint load/resume | Model/dataset nhỏ, CPU cho CI; CUDA smoke trên máy cá nhân |
| Tracking | Metrics đúng epoch, trạng thái lỗi, log không trùng khi resume, artifact metadata | Backend test DB và API hiện có |
| Local LLM adapter | Tool round-trip, stream chunks, malformed responses, timeout, không fallback cloud | Mock transport trong CI, runtime thật kiểm tra local |
| Chất lượng copilot | Số liệu/so sánh/verdict đúng DB, xử lý câu hỏi thiếu dữ liệu và tên mơ hồ | Bộ câu hỏi cố định, lưu kết quả và cấu hình model |
| Frontend | Polling, đổi experiment, run hoàn thành, lịch sử chat và provider status | Tests logic cần thiết, build và browser smoke |
| Offline | Cold start với assets đã cache, train/predict/chat không cần mạng ngoài | Chạy thủ công có ghi bằng chứng trên Windows mục tiêu |

Không bắt CI tải CIFAR-10, tải LLM hay train full-data. Không gọi Gemini trong bài nghiệm thu local. Tests live hiện có chỉ chạy khi người vận hành chọn rõ.

## 7. Rủi ro và cách xử lý

| Rủi ro | Xử lý |
| --- | --- |
| GPU hết 6 GB khi LLM/CNN/3D cùng chạy | Luân phiên workload; batch 32 trước; giảm context/model nếu cần; đo trước khi bật đồng thời |
| RAM 16 GB bị chiếm bởi cache/workers/model | Không preload toàn bộ dataset dạng float lên GPU; khởi đầu ít worker; theo dõi memory từng tiến trình |
| Cài nhầm PyTorch CPU hoặc torch/torchvision không khớp | Khóa phiên bản/build đã xác minh, chạy CUDA forward/backward trước training |
| Validation bị augmentation hoặc test bị dùng để tuning | Dataset evaluation riêng, split manifest cố định, test result tách biệt |
| Copilot trả số liệu sai dù tools đúng | Bộ kiểm tra grounding theo DB; thay model/prompt hoặc hạn chế tác vụ khi chưa đạt |
| Best checkpoint khác số trên UI | Hiển thị riêng best và final; không thay đổi nghĩa metrics cũ âm thầm |
| Backend tắt trong lúc train | Retry giới hạn, checkpoint cục bộ, quy trình resume/đối soát trạng thái |
| Dữ liệu còn trong chat/log/backup | Cấu hình lưu trữ, xóa lịch sử, giảm log nhạy cảm, kiểm soát truy cập và backup |
| Có mạng mới chạy được vì thiếu cache | Lệnh chuẩn bị riêng và bài kiểm tra offline cold start |
| CIFAR-10 tốt nhưng dữ liệu riêng kém | Đánh giá lại domain, nhãn, preprocessing và chất lượng trên dữ liệu đích; không suy rộng từ benchmark |

## 8. Điều kiện hoàn thành toàn bộ

- [x] Dataset train/test đã tải local; manifest chứng minh split đúng và không trùng mẫu.
- [x] Có ít nhất một CNN run completed trên dữ liệu thật, metrics khớp trainer và hiển thị trên UI.
- [x] Checkpoint tốt nhất nạp lại được trong tiến trình mới, có prediction CLI hoạt động offline.
- [x] Có báo cáo đánh giá cuối tách biệt validation/test và thông tin best/final rõ ràng.
- [x] Copilot dùng provider local, tools/UI actions đúng và không tự fallback ra cloud.
- [x] Có cấu hình vận hành ổn định trên RAM 16 GB/VRAM 6 GB, kèm số đo thực tế.
- [x] Luồng train → tracking → 3D → chat → prediction vượt qua nghiệm thu offline.
- [x] Có hướng dẫn cài đặt, khôi phục lỗi, giới hạn chất lượng và xử lý dữ liệu lưu trên máy.

## 9. Mở rộng sau phiên bản đầu

- API phân loại ảnh và giao diện upload: giới hạn loại/kích thước file, kiểm tra nội dung, chọn model rõ ràng, không lưu ảnh mặc định.
- Cơ chế quản lý tài nguyên tự động khi training và copilot tranh GPU.
- Model registry, quản lý nhiều phiên bản dataset/model và bảo vệ truy cập khi chia sẻ trong mạng nội bộ.
- RAG local hoặc fine-tune LLM chỉ khi có bộ đánh giá chứng minh nhu cầu.
- Thay CIFAR-10 bằng dữ liệu riêng qua interface dataset, kèm đánh giá quyền sử dụng, domain shift và chất lượng nhãn.

## 10. Tài liệu tham khảo

- [CIFAR-10 chính thức](https://www.cs.toronto.edu/~kriz/cifar.html)
- [Torchvision CIFAR10](https://docs.pytorch.org/vision/stable/generated/torchvision.datasets.CIFAR10.html)
- [Cài PyTorch local](https://pytorch.org/get-started/locally/)
- [Ollama tool calling](https://docs.ollama.com/capabilities/tool-calling)
- [Ollama local/cloud configuration](https://docs.ollama.com/faq)

Khi triển khai A02/E01, kiểm tra lại tài liệu phiên bản tại thời điểm cài đặt và ghi bản đã thử vào hướng dẫn vận hành.
