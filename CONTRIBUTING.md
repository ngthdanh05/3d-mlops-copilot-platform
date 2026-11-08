# Hướng dẫn đóng góp

Tài liệu này mô tả cách cả nhóm làm việc với **ClickUp** và **GitHub**. Mọi thành viên cần đọc hết trước khi nhận việc đầu tiên.

## Mục lục

1. [Nhóm và vai trò](#1-nhóm-và-vai-trò)
2. [Thiết lập môi trường lần đầu](#2-thiết-lập-môi-trường-lần-đầu)
3. [Quy trình một việc từ đầu đến cuối](#3-quy-trình-một-việc-từ-đầu-đến-cuối)
4. [Thẻ việc trên ClickUp](#4-thẻ-việc-trên-clickup)
5. [Đặt tên branch](#5-đặt-tên-branch)
6. [Viết commit](#6-viết-commit)
7. [Pull Request và review](#7-pull-request-và-review)
8. [Định nghĩa "Xong"](#8-định-nghĩa-xong)
9. [Quy ước code](#9-quy-ước-code)
10. [Bảo mật](#10-bảo-mật)
11. [Giao tiếp và báo cáo](#11-giao-tiếp-và-báo-cáo)
12. [Xử lý tình huống thường gặp](#12-xử-lý-tình-huống-thường-gặp)

---

## 1. Nhóm và vai trò

| Vai trò          | Số người | Phụ trách thư mục                                     | Nhiệm vụ chính                                                                |
| ---------------- | -------- | ----------------------------------------------------- | ----------------------------------------------------------------------------- |
| Leader           | 1        | Toàn repo, `docs/`                                    | Điều phối, kiến trúc, tích hợp, review chỗ ghép giữa các nhóm, báo cáo mentor |
| Web3D / Frontend | 3        | `frontend/`                                           | Không gian 3D, Inspector Panel, khung chat UI, Zustand store                  |
| Backend          | 2        | `backend/app/` (trừ phần copilot), `backend/scripts/` | API, database, client ghi log, CI                                             |
| AI integration   | 2        | `backend/app/**/copilot*`                             | Kết nối LLM, tool truy vấn, tool điều khiển giao diện, prompt                 |
| Data / Test      | 1        | `backend/tests/`, `backend/app/utils/seed_data.py`    | Dữ liệu mẫu, kiểm thử end-to-end, bộ câu hỏi kiểm tra AI                      |

Mỗi nhóm có **1 sub-lead**, chịu trách nhiệm review PR của nhóm và gửi báo cáo tuần cho leader. Người review được gán tự động theo file [`.github/CODEOWNERS`](.github/CODEOWNERS).

---

## 2. Thiết lập môi trường lần đầu

**Công cụ cần cài:** Git, Python 3.11+, [uv](https://docs.astral.sh/uv/), và Node.js 20+ cùng pnpm nếu bạn làm frontend.

```bash
# 1. Clone repo
git clone https://github.com/ngthdanh05/3d-mlops-copilot-platform.git
cd 3d-mlops-copilot-platform

# 2. Cấu hình Git (một lần)
git config user.name  "Tên của bạn"
git config user.email "email-dang-ky-github@example.com"

# 3. Backend
cd backend
uv sync
cp .env.example .env
uv run pytest            # phải pass hết trước khi bắt đầu làm
```

**Tài khoản:**

- [ ] Đã được mời vào ClickUp Workspace và GitHub Organization.
- [ ] Đã **kết nối tài khoản GitHub cá nhân với ClickUp** (ClickUp → App Center → GitHub). Có bước này thì mới tạo được branch/PR từ trong thẻ.

---

## 3. Quy trình một việc từ đầu đến cuối

```
ClickUp: nhận thẻ  →  IN PROGRESS
   │
GitHub:  git switch main && git pull
         git switch -c ML3D-42-panel-chi-tiet-run
         ... code, commit (có ML3D-42) ...
         git push -u origin ML3D-42-panel-chi-tiet-run
         Mở PR "ML3D-42 feat(frontend): panel chi tiết run"
   │
ClickUp: thẻ  →  IN REVIEW   (link PR tự hiện trong thẻ)
   │
GitHub:  CI xanh + 1 người duyệt  →  Squash and merge
   │
ClickUp: thẻ  →  DONE
```

Nếu bị vướng ở bất kỳ bước nào quá **2–3 tiếng**: chuyển thẻ sang `BLOCKED`, ghi lý do vào comment thẻ, rồi nhắn sub-lead.

---

## 4. Thẻ việc trên ClickUp

**Nguyên tắc: không có thẻ thì không làm.** Mọi việc, kể cả sửa lỗi nhỏ hay viết tài liệu, đều phải có thẻ. Thẻ chỉ quản lý trên ClickUp. **Không dùng GitHub Issues** để giao việc.

### Trạng thái

| Trạng thái    | Khi nào chuyển                                      |
| ------------- | --------------------------------------------------- |
| `TO DO`       | Thẻ đã vào sprint, chưa ai bắt đầu                  |
| `IN PROGRESS` | Bạn bắt đầu làm (nhớ tự gán tên mình)               |
| `BLOCKED`     | Bị vướng, cần người khác hỗ trợ. Bắt buộc ghi lý do |
| `IN REVIEW`   | Đã mở PR                                            |
| `DONE`        | PR đã merge vào `main`                              |

### Các trường bắt buộc

| Trường         | Giá trị                                            |
| -------------- | -------------------------------------------------- |
| Nhóm           | Web3D / Backend / AI / Data-Test / Leader          |
| Ưu tiên        | Must / Should / Could                              |
| Giai đoạn      | Phase 1–5                                          |
| Sprint Points  | 1 (S, vài giờ) · 3 (M, 1–2 ngày) · 5 (L, 3–5 ngày) |
| Người làm, Hạn | Bắt buộc                                           |

Việc lớn hơn 5 điểm phải **chia nhỏ** thành nhiều thẻ.

### Viết thẻ tốt

```
Tên: [Động từ] + [kết quả cụ thể]
     ✅ "Click vào quả cầu hiện Inspector Panel"
     ❌ "Làm phần 3D"

Mô tả:
- Mục tiêu: ...
- Tiêu chí hoàn thành:
  [ ] ...
  [ ] ...
- Liên quan: endpoint / thẻ khác / tài liệu
```

---

## 5. Đặt tên branch

```
ML3D-<số>-<mô-tả-ngắn-không-dấu>
```

| ✅ Đúng                      | ❌ Sai                                              |
| ---------------------------- | --------------------------------------------------- |
| `ML3D-42-panel-chi-tiet-run` | `panel` (không có ID)                               |
| `ML3D-57-api-xoa-experiment` | `ML3D-57-API Xoá Experiment` (dấu cách, chữ có dấu) |
| `ML3D-63-tool-compare-runs`  | `an-dev` (branch cá nhân dùng chung nhiều việc)     |

- Mỗi thẻ là **một branch**, luôn tạo từ `main` mới nhất.
- Branch tự xoá sau khi merge.
- Mẹo: mở thẻ trên ClickUp, bấm biểu tượng GitHub để copy tên branch gợi ý.

---

## 6. Viết commit

Dùng [Conventional Commits](https://www.conventionalcommits.org/) **kèm ID thẻ ClickUp**:

```
<loại>(<phạm vi>): ML3D-<số> <mô tả ngắn, thể mệnh lệnh>
```

| Loại       | Dùng khi                             |
| ---------- | ------------------------------------ |
| `feat`     | Thêm tính năng                       |
| `fix`      | Sửa lỗi                              |
| `refactor` | Sửa cấu trúc code, không đổi hành vi |
| `test`     | Thêm/sửa test                        |
| `docs`     | Tài liệu                             |
| `chore`    | Cấu hình, dependency, CI             |
| `perf`     | Tối ưu hiệu năng                     |

**Phạm vi:** `backend`, `frontend`, `copilot`, `scripts`, `ci`, `docs`.

**Ví dụ:**

```
feat(frontend): ML3D-42 thêm raycasting chọn quả cầu
fix(backend): ML3D-51 trả 404 khi run_id không tồn tại
test(copilot): ML3D-66 thêm test cho tool detect_overfitting
chore(ci): ML3D-3 thêm job kiểm tra tiêu đề PR
```

Commit nhỏ, mỗi commit làm một việc. Vì PR được **squash** khi merge, commit trong branch không cần hoàn hảo, nhưng **tiêu đề PR thì phải chuẩn** (nó sẽ thành commit trên `main`).

---

## 7. Pull Request và review

### Tiêu đề PR

```
ML3D-<số> <loại>(<phạm vi>): <mô tả>
```

Ví dụ: `ML3D-42 feat(frontend): Inspector Panel khi click quả cầu`

> CI có job `pr-title` kiểm tra tiêu đề có `ML3D-<số>`. Thiếu ID thì CI đỏ và không merge được.

### Trước khi mở PR

```bash
git switch main && git pull
git switch ML3D-42-panel-chi-tiet-run
git merge main                      # hoặc: git rebase main

# Backend
cd backend
uv run ruff format . && uv run ruff check . && uv run pytest

# Frontend (Phase 2)
cd frontend
pnpm lint && pnpm build
```

### Khi mở PR

- Điền đủ [mẫu PR](.github/pull_request_template.md). **Thay đổi giao diện bắt buộc có ảnh hoặc GIF.**
- PR nên nhỏ, **dưới khoảng 400 dòng thay đổi**. PR lớn hãy chia nhỏ.
- Có đổi API hoặc database → tick vào mẫu PR và **báo trên kênh chung**, vì các nhóm khác bị ảnh hưởng.
- Chưa xong nhưng muốn xin góp ý sớm → mở **Draft PR**.

### Điều kiện merge

- [ ] CI xanh (`pr-title`, `backend`, `frontend`)
- [ ] Ít nhất **1 người duyệt**, là code owner của thư mục bị sửa
- [ ] Không còn comment chưa giải quyết
- [ ] Merge bằng **Squash and merge**

### Người review

- Review trong vòng **24 giờ** (ngày làm việc).
- Góp ý cụ thể, kèm lý do. Phân biệt rõ:
  - **Bắt buộc sửa:** lỗi, bảo mật, sai thiết kế.
  - **`nit:`** góp ý nhỏ, người viết tự quyết.
- Kéo branch về chạy thử nếu là thay đổi giao diện.

---

## 8. Định nghĩa "Xong"

Một thẻ chỉ được chuyển `DONE` khi **đủ tất cả**:

- [ ] Đạt mọi tiêu chí hoàn thành ghi trong thẻ
- [ ] PR đã merge vào `main`, CI xanh
- [ ] Có test cho logic mới (backend, copilot)
- [ ] Cập nhật tài liệu nếu thay đổi API, cấu hình hoặc cách chạy (README, `/docs`)
- [ ] Chạy được trên máy người review, không chỉ trên máy người viết

---

## 9. Quy ước code

### Python (backend, copilot)

- PEP 8, kiểm tra bằng **Ruff** (`line-length = 100`).
- Có type hint cho hàm public.
- Logic nghiệp vụ đặt trong `services/`, router chỉ nhận request và gọi service.
- **Tool của AI phải gọi service layer**, không truy vấn database trực tiếp.
- Mọi phép tính số liệu (so sánh, phát hiện overfitting) làm bằng code, **không để LLM tự tính**.

### TypeScript (frontend)

- Dùng các Zustand store (`useRunStore`, `useCameraStore`, `useChatStore`) làm **nguồn trạng thái duy nhất** giữa 3 khung.
- Hành động từ AI (`actions` trong phản hồi `/api/copilot/chat`) chỉ được thực thi qua store, không thao tác trực tiếp lên scene.
- Không gọi LLM từ frontend.

### Đặt tên key siêu tham số

Cả nhóm thống nhất: `learning_rate`, `batch_size`, `epochs`, `hidden_layers`, `dropout`, `optimizer`. Không dùng tên viết tắt như `lr` hay `bs` trong dữ liệu mới, để không gian 3D đặt run đúng trục.

---

## 10. Bảo mật

- **Không bao giờ** commit file `.env`, API key, mật khẩu hay token.
- API key của LLM chỉ nằm trong `backend/.env` trên máy mỗi người. Leader gửi key riêng cho người cần, **không dán vào chat nhóm, ClickUp hay GitHub**.
- Lỡ commit key: báo leader **ngay lập tức** để thu hồi key. Xoá commit thôi là không đủ, vì key đã nằm trong lịch sử Git.
- Không commit file database (`*.db`), dữ liệu lớn hay file model.

---

## 11. Giao tiếp và báo cáo

| Khi nào              | Ai           | Làm gì                                        | Ở đâu          |
| -------------------- | ------------ | --------------------------------------------- | -------------- |
| Hằng ngày, trước 22h | Mọi người    | Cập nhật 3 dòng: đã làm / sẽ làm / đang vướng | Kênh chat nhóm |
| Liên tục             | Mọi người    | Cập nhật trạng thái thẻ                       | ClickUp        |
| Kẹt quá 2–3 tiếng    | Người bị kẹt | Chuyển `BLOCKED` + nhắn sub-lead              | ClickUp + chat |
| Cuối tuần            | Sub-lead     | Báo cáo tuần theo mẫu                         | ClickUp Docs   |
| Cuối sprint (2 tuần) | Mỗi nhóm     | Demo 3–5 phút + rút kinh nghiệm               | Họp nhóm       |
| Đổi API / database   | Người đổi    | Báo trước khi merge                           | Kênh chung     |

**Mẫu cập nhật hằng ngày:**

```
[Tên] – [Ngày]
✅ Đã làm: ML3D-42 xong raycasting
🔜 Sẽ làm: ML3D-42 panel hiển thị hyperparams
⛔ Đang vướng: Không
```

Liên hệ trực tiếp với mentor do **leader** đảm nhận. Có câu hỏi cho mentor, hãy gửi leader để gom lại.

---

## 12. Xử lý tình huống thường gặp

**Branch bị conflict với `main`:**

```bash
git switch main && git pull
git switch ML3D-42-...
git merge main
# sửa các file conflict, rồi:
git add . && git commit
```

Không chắc cách sửa conflict ở code của nhóm khác → hỏi người viết đoạn code đó.

**Lỡ code trên `main` ở máy mình:**

```bash
git switch -c ML3D-42-ten-viec   # mang toàn bộ thay đổi sang branch mới
```

**Thẻ ClickUp không hiện branch/PR:** kiểm tra lại ID trong tên branch hoặc tiêu đề PR có đúng dạng `ML3D-<số>` không, viết hoa đúng.

**CI đỏ:** bấm vào job đỏ trên trang PR để xem log. Phần lớn lỗi là do chưa chạy `ruff format`. Chạy lại lệnh ở mục 7 trên máy rồi push.
