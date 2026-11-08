<!--
Tiêu đề PR phải có dạng:  ML3D-<số> <loại>(<phạm vi>): <mô tả>
Ví dụ:                    ML3D-42 feat(frontend): Inspector Panel khi click quả cầu
-->

## Thẻ ClickUp

ML3D-

## Mô tả

<!-- Làm gì, vì sao. Tóm tắt 2–4 dòng. -->

## Cách kiểm tra

1.
2.
3.

## Ảnh / GIF

<!-- Bắt buộc nếu có thay đổi giao diện. Kéo thả ảnh vào đây. -->

## Ảnh hưởng

- [ ] Có thay đổi API (đã cập nhật README / bảng API và báo kênh chung)
- [ ] Có thay đổi database / mô hình dữ liệu
- [ ] Có thay đổi biến môi trường (đã cập nhật `.env.example`)
- [ ] Không có thay đổi nào ở trên

## Tự kiểm tra

- [ ] Đã merge `main` mới nhất vào branch
- [ ] Backend: `ruff format`, `ruff check`, `pytest` đều pass trên máy
- [ ] Frontend: `pnpm lint`, `pnpm build` pass trên máy
- [ ] Có test cho logic mới (nếu là backend / copilot)
- [ ] Không có API key, `.env` hay file `*.db` trong thay đổi
