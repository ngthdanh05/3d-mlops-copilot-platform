# Quy ước phát triển

Dự án do một người phát triển. Tài liệu này ghi lại cách làm để giữ code ổn định.

## Thiết lập lần đầu

Cần có Git, Python 3.11+, [uv](https://docs.astral.sh/uv/), Node.js 20.19+ và pnpm.

```bash
cd backend
uv sync
cp .env.example .env
uv run pytest
```

```bash
cd frontend
pnpm install
```

## Quy trình một thay đổi

1. Tạo nhánh mới từ `main`, ví dụ `feat/bieu-do-epoch` hoặc `fix/thang-mau`.
2. Code và commit theo [Conventional Commits](https://www.conventionalcommits.org/): `<loại>(<phạm vi>): <mô tả>`.
3. Chạy các kiểm tra bên dưới.
4. Mở Pull Request vào `main` để CI chạy, rồi merge khi CI xanh.

Loại commit: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`. Phạm vi: `backend`, `frontend`, `copilot`, `scripts`, `ci`, `docs`.

## Kiểm tra trước khi mở PR

```bash
cd backend
uv run ruff format . && uv run ruff check . && uv run pytest
```

```bash
cd frontend
pnpm lint && pnpm build
```

## Quy ước code

**Python**

- PEP 8, kiểm tra bằng Ruff (`line-length = 100`), có type hint cho hàm public.
- Logic nghiệp vụ đặt trong `services/`, router chỉ nhận request và gọi service.
- Tool của AI phải gọi service layer, không truy vấn database trực tiếp.
- Mọi phép tính số liệu làm bằng code, không để LLM tự tính.

**TypeScript**

- Dùng các Zustand store (`useRunStore`, `useCameraStore`, `useChatStore`) làm nguồn trạng thái duy nhất giữa các khung.
- `actions` trong phản hồi `/api/copilot/chat` chỉ được thực thi qua store.
- Không gọi LLM từ frontend.

**Tên key siêu tham số:** `learning_rate`, `batch_size`, `epochs`, `hidden_layers`, `dropout`, `optimizer`. Không dùng tên viết tắt như `lr` hay `bs`, để không gian 3D đặt run đúng trục.

## Bảo mật

- Không commit `.env`, API key, mật khẩu hay token. Key của LLM chỉ nằm trong `backend/.env`.
- Lỡ commit key thì phải thu hồi key ngay. Xoá commit là không đủ, vì key đã nằm trong lịch sử Git.
- Không commit file database (`*.db`), dữ liệu lớn hay file model.
