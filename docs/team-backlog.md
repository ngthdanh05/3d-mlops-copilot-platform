# Backlog dự án 3D-MLOps theo team (viết lại từ đầu)

Bản nháp để leader và mentor chỉnh trước Sprint 0. Tài liệu này dự kiến chuyển sang repo team.
- co the su dung nhieu api key model de co the chuyen sang model khac sau khi model nay het luong request
## Giả định cần xác nhận

Các con số dưới đây là giả định, chưa được team xác nhận.

- Team gồm 1 leader và 8 thành viên, mentor ở ngoài và không nhận task.
- Thời gian khoảng 12 tuần: 6 sprint, mỗi sprint 2 tuần.
- Mỗi thành viên làm tối đa 12 điểm mỗi sprint. 1 điểm tương đương khoảng nửa ngày làm việc tập trung.
- Sản phẩm cùng loại với bản PoC: theo dõi thực nghiệm, không gian 3D và trợ lý AI dùng tool calling.
- Code cũ không được chép sang. Chỉ dùng tài liệu thiết kế làm tham khảo.
- Các ngưỡng hiệu năng và tỉ lệ đúng là đề xuất, chốt lại ở FND-01.

## Tổng quan

Tổng cộng **86 task, 316 điểm**: 70 Must (255 điểm), 14 Should, 2 Could.

| Sprint | Mục tiêu | Số task | Điểm | Điểm Must |
|---|---|---|---|---|
| S0 | Chốt hợp đồng và dựng khung repo (M0, M1) | 11 | 29 | 29 |
| S1 | Luồng mỏng xuyên suốt (M2) | 7 | 21 | 21 |
| S2 | Làm sâu nền tảng (M3) | 22 | 79 | 79 |
| S3 | Hoàn thiện tính năng chính (M3) | 20 | 75 | 67 |
| S4 | Chẩn đoán, hiệu năng và tính năng mở rộng (M3) | 16 | 76 | 34 |
| S5 | Tích hợp, đo đạc và demo (M4) | 10 | 36 | 25 |

## Phân công

Tên TV1 đến TV8 là chỗ giữ tên, leader điền người thật. Người dự phòng phải đọc được code của mảng và review PR của mảng đó.

| Mã | Mảng | Phụ trách | Dự phòng |
|---|---|---|---|
| API | API và database | TV1 | TV2 |
| ML | Client và dữ liệu ML | TV2 | TV1 |
| AIC | Lõi AI | TV3 | TV4 |
| AIT | Tool của AI | TV4 | TV3 |
| VIZ | Không gian 3D | TV5 | TV6 |
| UI | Panel và sidebar | TV6 | TV5 |
| CHT | Chat và store | TV7 | TV8 |
| QA | QA và DevOps | TV8 | TV7 |

**Leader** giữ phạm vi, duyệt thay đổi API và schema, tích hợp cuối sprint. **Mentor** duyệt thiết kế ở M0 và góp ý ở mỗi buổi demo.

### Tải theo người (điểm)

| Người phụ trách | S0 | S1 | S2 | S3 | S4 | S5 | Tổng |
|---|---|---|---|---|---|---|---|
| Leader | 10 | – | – | – | – | – | 10 |
| TV1 (API) | 8 | 3 | 11 | 11 | 10 | 3 | 46 |
| TV2 (ML) | – | 2 | 10 | 8 | 8 | 3 | 31 |
| TV3 (AIC) | 3 | 5 | 8 | 11 | 8 | 5 | 40 |
| TV4 (AIT) | – | – | 9 | 8 | 10 | 3 | 30 |
| TV5 (VIZ) | – | 3 | 11 | 11 | 11 | 8 | 44 |
| TV6 (UI) | – | 2 | 9 | 8 | 11 | 3 | 33 |
| TV7 (CHT) | – | 3 | 11 | 10 | 8 | 3 | 35 |
| TV8 (QA) | 6 | 3 | 10 | 8 | 10 | 8 | 45 |
| Cả team | 2 | – | – | – | – | – | 2 |

Sprint 0 và Sprint 1 có ít việc cho nhiều người là chủ ý, vì lúc đó chưa nên làm song song. Thời gian còn lại dành cho đọc thiết kế, học công nghệ của mảng mình và viết test mẫu.

## Quy tắc

**Định nghĩa hoàn thành, áp dụng cho mọi task:**

- Đạt tiêu chí ghi trong bảng, có test cho logic mới.
- CI xanh và có ít nhất 1 approval từ người phụ trách hoặc dự phòng của mảng bị sửa.
- Đã cập nhật tài liệu nếu đổi API, cấu hình hoặc cách chạy.
- Không có API key, `.env` hay file database trong thay đổi.

**Ưu tiên:** Must là bắt buộc để demo, Should nên có, Could chỉ làm khi dư thời gian. Task Must không được phụ thuộc task thấp hơn.

**Nếu thiếu thời gian:** bỏ Could trước, rồi đến Should từ Sprint 5 ngược về. Không cắt Must và không bỏ Sprint 1.

**Phụ thuộc cùng sprint** cần hai người thống nhất giao diện ngay đầu sprint và làm task phụ thuộc sau.

## Backlog

### Sprint 0: Chốt hợp đồng và dựng khung repo (M0, M1)

| ID | Task | Phụ trách | Ưu tiên | Điểm | Phụ thuộc | Hoàn thành khi |
|---|---|---|---|---|---|---|
| FND-01 | Viết phạm vi sản phẩm và tiêu chí thành công | Leader | Must | 2 | – | Mentor duyệt danh sách trong và ngoài phạm vi |
| FND-02 | Chốt quyết định kiến trúc: database, đăng nhập, nhà cung cấp LLM | Leader | Must | 3 | FND-01 | Mỗi quyết định có một bản ghi ngắn nêu lý do |
| FND-03 | Thiết kế schema experiments, runs, metrics dạng key-value | API | Must | 3 | FND-02 | Sơ đồ bảng được leader duyệt, nhận được metric bất kỳ |
| FND-04 | Viết hợp đồng REST API | API | Must | 3 | FND-03 | Có đặc tả endpoint, dữ liệu vào ra và mã lỗi |
| FND-05 | Viết hợp đồng Copilot: actions, sự kiện SSE, giao diện tool | AIC | Must | 3 | FND-02 | Mảng AI và frontend cùng ký duyệt định dạng |
| FND-06 | Viết CONTRIBUTING: nhánh, commit, review 24 giờ, định nghĩa hoàn thành | Leader | Must | 2 | FND-01 | Cả team đã đọc và đồng ý |
| FND-07 | Dựng khung monorepo backend và frontend, healthcheck, .env.example | Leader | Must | 3 | FND-06 | Clone về chạy được hai server theo README |
| FND-08 | Thiết lập CI lint, typecheck, test, bảo vệ nhánh, CODEOWNERS | QA | Must | 3 | FND-07 | Không merge được vào main nếu CI đỏ hoặc thiếu approval |
| FND-09 | Thiết lập Alembic và migration đầu tiên | API | Must | 2 | FND-03, FND-07 | Migration chạy được trên database trống |
| FND-10 | Sinh types frontend từ OpenAPI, CI báo lỗi khi lệch | QA | Must | 3 | FND-04, FND-07 | Đổi API mà chưa sinh lại types thì CI đỏ |
| FND-11 | Onboarding: mỗi thành viên chạy local và merge một PR nhỏ | Cả team | Must | 2 | FND-07, FND-08 | Đủ 8 PR đã merge |

### Sprint 1: Luồng mỏng xuyên suốt (M2)

| ID | Task | Phụ trách | Ưu tiên | Điểm | Phụ thuộc | Hoàn thành khi |
|---|---|---|---|---|---|---|
| THN-01 | API tối thiểu: tạo và lấy experiment, run, metric; danh sách kèm metric cuối | API | Must | 3 | FND-04, FND-09 | Gọi được qua Swagger, có test |
| THN-02 | Seed tối thiểu: 1 experiment, 10 run | ML | Must | 2 | FND-09 | Một lệnh tạo xong dữ liệu |
| THN-03 | Vẽ quả cầu từ danh sách run | VIZ | Must | 3 | FND-10, THN-01 | 10 run hiện đúng vị trí theo hai tham số |
| THN-04 | Click quả cầu mở Inspector qua store | UI | Must | 2 | THN-03 | Inspector hiện đúng run được click |
| THN-05 | LLM giả lập, một tool tìm run tốt nhất, endpoint chat stream | AIC | Must | 5 | FND-05, THN-01 | Stream trả chữ và actions, không cần API key |
| THN-06 | Khung chat tối giản, nhận actions và highlight run | CHT | Must | 3 | THN-03, THN-05 | Hỏi run tốt nhất thì đúng quả cầu sáng lên |
| THN-07 | Smoke test trình duyệt cho luồng mỏng, chạy trong CI | QA | Must | 3 | THN-04, THN-06 | CI chạy trọn luồng tạo, xem, click, hỏi |

### Sprint 2: Làm sâu nền tảng (M3)

| ID | Task | Phụ trách | Ưu tiên | Điểm | Phụ thuộc | Hoàn thành khi |
|---|---|---|---|---|---|---|
| API-01 | CRUD experiment đầy đủ, xoá cascade | API | Must | 3 | THN-01 | Đúng mã 201, 204, 404, 409, 422 và có test |
| API-02 | CRUD run và chuyển trạng thái | API | Must | 3 | API-01 | Tự điền finished_at, từ chối chuyển trạng thái sai |
| API-03 | Ghi metric key-value theo epoch, chống ghi trùng | API | Must | 5 | API-02 | Nhận metric mới không cần migration, trùng epoch trả 409 |
| ML-01 | Client Python: context manager tự đánh dấu completed hoặc failed | ML | Must | 5 | THN-01 | Exception hoặc NaN làm run chuyển failed |
| ML-02 | Bộ sinh dữ liệu giả lập: run tốt, overfit, lỗi, đang chạy | ML | Must | 5 | THN-02 | Cùng seed cho cùng dữ liệu, có tiền tố mock- |
| AIC-01 | Giao diện LLMClient và LLM giả lập đầy đủ | AIC | Must | 3 | THN-05 | Test engine chạy không cần mạng |
| AIC-02 | Vòng lặp tool calling: giới hạn vòng, xử lý lỗi tool | AIC | Must | 5 | AIC-01 | Tool lỗi được trả lại cho model, không làm hỏng request |
| AIT-01 | Cơ chế đăng ký tool theo từng file | AIT | Must | 3 | THN-05 | Thêm tool mới không phải sửa file chung |
| AIT-02 | Tool liệt kê experiment và tìm run tốt nhất | AIT | Must | 3 | AIT-01 | Chỉ gọi service layer, có test |
| AIT-03 | Tool tìm run theo tên và lấy chi tiết run | AIT | Must | 3 | AIT-01 | Không phân biệt hoa thường, trùng tên trả đủ |
| VIZ-01 | Scene, điều khiển camera, ánh sáng | VIZ | Must | 3 | THN-03 | Xoay và zoom mượt, không lỗi console |
| VIZ-02 | Ánh xạ toạ độ log10, log2, tuyến tính | VIZ | Must | 5 | THN-03 | Unit test cả run thiếu tham số |
| VIZ-03 | Nhãn và vạch chia trên trục | VIZ | Must | 3 | VIZ-02 | Nhãn đọc được trên cả ba thang |
| UI-01 | Bố cục ba khung, responsive | UI | Must | 3 | THN-04 | Dùng được ở màn hình laptop và hẹp |
| UI-02 | Sidebar chọn experiment và danh sách run | UI | Must | 3 | UI-01, CHT-01 | Đổi experiment thì 3D đổi theo |
| UI-03 | Trạng thái đang tải, lỗi backend, dữ liệu trống | UI | Must | 3 | UI-01 | Mỗi trạng thái có thông báo và cách xử lý |
| CHT-01 | Tách ba store: run, camera, chat | CHT | Must | 5 | THN-06 | Không còn state chia sẻ nằm ngoài store |
| CHT-02 | Đọc luồng SSE hoàn chỉnh, xử lý đứt kết nối | CHT | Must | 3 | THN-06 | Unit test sự kiện bị chia cắt giữa các chunk |
| CHT-03 | Khung chat hiển thị markdown và trạng thái đang trả lời | CHT | Must | 3 | THN-06 | Bảng so sánh hiển thị đúng |
| QA-01 | Fixture test backend với database riêng, báo cáo coverage | QA | Must | 5 | FND-08 | Test không đụng database dev |
| QA-02 | Vitest và coverage cho frontend | QA | Must | 3 | FND-08 | Ngưỡng coverage của utils được CI kiểm tra |
| QA-03 | Quét secret trong CI | QA | Must | 2 | FND-08 | PR chứa key mẫu bị chặn |

### Sprint 3: Hoàn thiện tính năng chính (M3)

| ID | Task | Phụ trách | Ưu tiên | Điểm | Phụ thuộc | Hoàn thành khi |
|---|---|---|---|---|---|---|
| API-04 | Danh sách run kèm mọi metric cuối, không truy vấn N+1 | API | Must | 5 | API-03 | Có test đếm số câu truy vấn |
| API-05 | Lọc, sắp xếp và phân trang danh sách run | API | Should | 3 | API-04 | Có test cho từng tham số |
| API-06 | Endpoint liệt kê metric và hướng tốt của metric | API | Must | 3 | API-03 | Frontend và tool AI đọc được metric nào cao là tốt |
| ML-03 | Script huấn luyện thật trên MNIST ghi log theo epoch | ML | Must | 5 | ML-01 | Run xuất hiện trong 3D với tiền tố real- |
| ML-04 | Random search tái lập được theo seed | ML | Should | 3 | ML-03 | Hai máy cho cùng bộ cấu hình |
| AIC-03 | Client Gemini: complete, stream, timeout, giới hạn lượt gọi | AIC | Must | 5 | AIC-01 | Lỗi 429 hiện thông báo dễ hiểu |
| AIC-04 | System prompt và quy tắc chỉ dùng số từ tool | AIC | Must | 3 | AIC-02 | Câu trả lời không có số ngoài kết quả tool |
| AIC-05 | Bộ đánh giá tự động ít nhất 30 câu hỏi | AIC | Must | 3 | AIC-02 | Có báo cáo tỉ lệ đúng, mục tiêu đề xuất từ 90% |
| AIT-04 | Tool so sánh nhiều run | AIT | Must | 5 | AIT-01, API-06 | Tách tham số giống và khác, nêu run tốt nhất từng metric |
| AIT-05 | Tool điều khiển giao diện: highlight, camera, inspector | AIT | Must | 3 | AIT-01 | Run không tồn tại được báo lại cho model |
| VIZ-04 | Mã hoá màu, kích thước, trạng thái và chú giải | VIZ | Must | 5 | VIZ-02, API-06 | Run tốt phân biệt rõ khi có nhiều run xấu |
| VIZ-05 | Chọn trục từ tham số số và metric cuối | VIZ | Must | 3 | VIZ-02, API-04 | Đổi trục thì quả cầu đổi vị trí |
| VIZ-06 | Camera bay tới run, người dùng kéo thì huỷ | VIZ | Must | 3 | VIZ-01, CHT-01 | Bay được từ cả click và action của AI |
| UI-04 | Bộ lọc theo trạng thái, metric và tên | UI | Must | 5 | UI-02, CHT-01 | Lọc xong 3D ẩn run, các run còn lại không đổi vị trí |
| UI-05 | Inspector đầy đủ: metric cuối, tham số, thời gian | UI | Must | 3 | THN-04, API-04 | Hiển thị đúng với run thiếu metric |
| CHT-04 | Thực thi actions chỉ qua store, tự bỏ lọc nếu run bị ẩn | CHT | Must | 3 | CHT-01, AIT-05 | Run AI nhắc tới luôn nhìn thấy được |
| CHT-05 | Đồng bộ giữa các store và gợi ý câu hỏi | CHT | Must | 5 | CHT-01, UI-05 | Chọn run thì gợi ý đổi theo |
| CHT-06 | Lưu lịch sử chat, nút xoá lịch sử | CHT | Should | 2 | CHT-03 | Tải lại trang vẫn còn hội thoại |
| QA-04 | Mở rộng E2E: lọc, đổi trục, so sánh | QA | Must | 5 | THN-07, UI-04, VIZ-05 | Chạy ổn định, không flaky trong 10 lần liên tiếp |
| QA-05 | Kiểm tra migration lên và xuống trong CI | QA | Must | 3 | FND-09 | Migration lỗi làm CI đỏ |

### Sprint 4: Chẩn đoán, hiệu năng và tính năng mở rộng (M3)

| ID | Task | Phụ trách | Ưu tiên | Điểm | Phụ thuộc | Hoàn thành khi |
|---|---|---|---|---|---|---|
| API-07 | Lưu metadata artifact của run | API | Should | 5 | API-02 | Gắn và xem được đường dẫn file model theo run |
| API-08 | Đăng nhập bằng token | API | Could | 5 | API-01 | Endpoint ghi từ chối request không có token |
| ML-05 | Đóng gói client thành thư viện pip | ML | Should | 5 | ML-01 | Cài vào môi trường sạch và dùng được |
| ML-06 | Ví dụ bài toán hồi quy với MSE và R2 | ML | Should | 3 | ML-01, API-03 | Run hồi quy hiện đúng mà không sửa backend |
| AIC-06 | Tự sinh actions từ kết quả tool để bớt vòng gọi LLM | AIC | Must | 3 | AIC-02, AIT-05 | Số vòng gọi trung bình giảm so với trước |
| AIC-07 | Hội thoại nhiều lượt có ngữ cảnh ở backend | AIC | Should | 5 | AIC-02 | Hiểu được câu hỏi nối tiếp như 'còn run kia thì sao' |
| AIT-06 | Tool chẩn đoán overfitting tính bằng code | AIT | Must | 5 | AIT-03 | Có test cho từng mức kết luận và từng ngưỡng |
| AIT-07 | Tool chỉ ra vùng tham số chưa được thử | AIT | Should | 5 | AIT-02 | Kết quả khớp vùng trống nhìn thấy trên 3D |
| VIZ-07 | Instanced mesh khi có trên 100 run | VIZ | Must | 8 | VIZ-04 | Click, hover, highlight vẫn hoạt động |
| VIZ-08 | Câu kết luận tính từ dữ liệu | VIZ | Should | 3 | VIZ-02 | Câu đổi theo bộ lọc |
| UI-06 | Biểu đồ metric theo epoch trong Inspector | UI | Must | 8 | UI-05, API-03 | Chọn được metric, thấy rõ train và validation |
| UI-07 | Xem run của nhiều experiment cùng lúc | UI | Should | 3 | UI-02 | Phân biệt được run theo experiment |
| CHT-07 | Tự cập nhật run đang chạy bằng polling | CHT | Must | 5 | CHT-01, API-04 | Run đang huấn luyện cập nhật không cần F5 |
| CHT-08 | Gửi lại câu hỏi khi lỗi | CHT | Should | 3 | CHT-02 | Câu trả lời lỗi được thay thế, không nhân đôi |
| QA-06 | Benchmark API | QA | Should | 5 | API-04 | Có báo cáo sinh tự động |
| QA-07 | Script đo FPS trên trình duyệt | QA | Must | 5 | THN-07 | Mảng 3D dùng được cho VIZ-09 |

### Sprint 5: Tích hợp, đo đạc và demo (M4)

| ID | Task | Phụ trách | Ưu tiên | Điểm | Phụ thuộc | Hoàn thành khi |
|---|---|---|---|---|---|---|
| API-09 | Thêm index và đo tải với 500 run | API | Should | 3 | API-04 | Danh sách 500 run dưới ngưỡng đã chốt ở FND-01 |
| ML-07 | Tạo bộ dữ liệu demo chuẩn | ML | Must | 3 | ML-02, ML-03 | Một lệnh dựng lại dữ liệu demo |
| AIC-08 | Đo và tối ưu độ trễ AI | AIC | Must | 5 | AIC-03, AIC-06 | Trung vị dưới 8 giây trên bộ đánh giá |
| AIT-08 | Rà trường hợp biên: không có run, thiếu metric, run lỗi | AIT | Must | 3 | AIT-04, AIT-06 | Mọi tool trả kết quả rõ ràng, không exception |
| VIZ-09 | Đo FPS với 200 node | VIZ | Must | 3 | VIZ-07, QA-07 | Đạt 60 fps trên máy tham chiếu đã chốt |
| VIZ-10 | Chế độ giảm chiều PCA | VIZ | Could | 5 | VIZ-02 | Bật tắt được và có nhãn giải thích |
| UI-08 | Rà giao diện và khả năng truy cập | UI | Should | 3 | UI-04, UI-06 | Dùng được bằng bàn phím, đủ nhãn aria |
| CHT-09 | Rà đồng bộ ba khung theo kịch bản demo | CHT | Must | 3 | CHT-04, CHT-05, CHT-07 | Không có trạng thái lệch ở mọi bước demo |
| QA-08 | Kiểm thử hồi quy toàn bộ kịch bản demo | QA | Must | 5 | QA-04, CHT-07, UI-06 | Không còn lỗi mức cao |
| QA-09 | Hoàn thiện README, DEMO và tập demo cùng cả team | QA | Must | 3 | ML-07 | Một người mới làm theo tài liệu chạy được demo |
