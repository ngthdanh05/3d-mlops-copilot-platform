# Hiệu năng

> Tệp này do `backend/scripts/benchmark.py` sinh ra. Đừng sửa tay, hãy chạy lại script.

Đo ngày 2026-11-10 trên `Windows 11`, backend và frontend chạy cùng máy, dữ liệu giả lập.

## 3D FPS

GPU: `ANGLE (Intel, Intel(R) Iris(R) Xe Graphics (0x000046A6) Direct3D11 vs_5_0 ps_5_0, D3D11)`. Bản build production, khung nhìn 1600×900. Mỗi mức đo 6 giây khi đứng yên và 6 giây khi kéo xoay camera liên tục.

| Số node | FPS đứng yên | FPS khi xoay | p95 thời gian khung hình khi xoay (ms) |
| ---: | ---: | ---: | ---: |
| 50 | 164.7 | 162.9 | 6.2 |
| 100 | 164.5 | 157.4 | 6.9 |
| 200 | 165.0 | 160.0 | 6.4 |
| 500 | 165.0 | 151.2 | 12.1 |

**Mục tiêu 200 node @ 60 fps:** ✅ Đạt (thấp nhất 160.0 fps).

## Thời gian phản hồi API

200 request tuần tự mỗi endpoint, đo từ client trên cùng máy, database SQLite có 850 run.

| Endpoint | p50 (ms) | p95 (ms) |
| --- | ---: | ---: |
| `GET /api/health` | 1.2 | 2.1 |
| `GET /api/experiments` | 1.7 | 2.9 |
| `GET /api/runs (50 run)` | 9.2 | 33.2 |
| `GET /api/runs (100 run)` | 15.0 | 36.9 |
| `GET /api/runs (200 run)` | 22.7 | 63.9 |
| `GET /api/runs (500 run)` | 51.7 | 118.6 |
| `GET /api/runs/{id}` | 5.0 | 13.6 |
| `POST /api/runs/{id}/metrics` | 6.1 | 12.6 |
| `POST /api/copilot/chat (LLM giả lập, 200 run)` | 21.1 | 60.0 |

**Mục tiêu p95 < 200 ms:** ✅ Đạt (chậm nhất: `GET /api/runs (500 run)`, 118.6 ms).

## Thời gian trả lời của AI (end-to-end)

Nhà cung cấp: Gemini thật. Đo qua `POST /api/copilot/chat/stream`, gồm toàn bộ các vòng gọi tool. Experiment có 50 run, mỗi câu hỏi 3 lần.

| Câu hỏi | Chữ đầu tiên, trung vị (s) | Hoàn tất, trung vị (s) | Chậm nhất (s) | Trả lời được |
| --- | ---: | ---: | ---: | --- |
| Run nào có val_accuracy cao nhất? | 9.29 | 9.64 | 11.13 | 3/3 |
| So sánh run-001 với run-002 | 6.73 | 7.77 | 11.31 | 3/3 |
| run-003 có bị overfitting không? | 7.35 | 7.63 | 8.54 | 3/3 |
| Tóm tắt kết quả của experiment này | 6.75 | 6.96 | 6.99 | 3/3 |
| Run nào có val_loss thấp nhất? | 7.39 | 7.62 | 8.34 | 3/3 |

**Mục tiêu < 8 s:** ❌ Không đạt (trung vị 7.63 s, chậm nhất 11.31 s, 15/15 câu trả lời được).

## Chạy lại

```bash
cd backend
uv run python scripts/benchmark.py --real-llm
```
