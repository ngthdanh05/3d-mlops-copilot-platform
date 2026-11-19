"""Render canonical local answers from validated query results, never model prose."""

import json
import re
from typing import Any

CANONICAL_TOOLS = {"find_best_runs", "compare_runs", "detect_overfitting"}


def _value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, dict | list):
        return json.dumps(value, ensure_ascii=False).replace("|", "\\|")
    return str(value).replace("|", "\\|").replace("\n", " ")


def _parameter(value: Any) -> str:
    return f"{value:.6g}" if isinstance(value, float) else _value(value)


def render_grounded(name: str, data: dict[str, Any], question: str) -> str:
    vi = bool(re.search(r"[à-ỹÀ-ỸđĐ]", question)) or any(
        word in question.lower() for word in ["tot nhat", "so sanh", "run nao", "khong"]
    )
    if name == "find_best_runs":
        runs = data["runs"]
        if not runs:
            return (
                ("Chưa có run hoàn thành có " if vi else "No completed run has ")
                + data["metric"]
                + "."
            )
        best = runs[0]
        text = (
            f"**{_value(best['run_name'])}** "
            + ("tốt nhất theo " if vi else "is best by ")
            + f"{data['metric']} = **{_value(best['value'])}** "
            + ("(chỉ số epoch cuối đã log)." if vi else "(last logged epoch).")
        )
        if data.get("median_value") is not None:
            text += " Trung vị các run hoàn thành: " if vi else " Completed-run median: "
            text += _value(data["median_value"]) + "."
        hp = best.get("hyperparams", {})
        details = [
            f"{key}={_parameter(hp[key])}" for key in ["learning_rate", "batch_size"] if key in hp
        ]
        if details:
            text += " " + ", ".join(details) + "."
        if len(runs) > 1:
            text += (
                "\n\n"
                + "; ".join(f"{_value(r['run_name'])}: {_value(r['value'])}" for r in runs[1:])
                + "."
            )
        return text + (
            " Run đã được đánh dấu trong biểu đồ." if vi else " Highlighted in the chart."
        )
    if name == "compare_runs":
        runs = data["runs"]
        lines = []
        for metric in ["val_accuracy", "val_loss"]:
            best = data["best_by_metric"].get(metric)
            if best:
                if best["spread_to_worst"] == 0:
                    lines.append(("Các run đồng hạng về " if vi else "Runs tie on ") + metric + ".")
                else:
                    lines.append(
                        f"**{_value(best['run_name'])}** "
                        + ("tốt nhất về " if vi else "is best on ")
                        + f"{metric} ({_value(best['value'])}); "
                        + ("chênh lệch tốt nhất–kém nhất: " if vi else "best-to-worst spread: ")
                        + _value(best["spread_to_worst"])
                        + "."
                    )
        lines += [
            "",
            "| "
            + ("Chỉ số" if vi else "Metric")
            + " | "
            + " | ".join(_value(r["run_name"]) for r in runs)
            + " |",
            "| --- | " + " | ".join("---" for _ in runs) + " |",
        ]
        for metric in ["accuracy", "loss", "val_accuracy", "val_loss"]:
            lines.append(
                f"| {metric} | " + " | ".join(_value(r[f"final_{metric}"]) for r in runs) + " |"
            )
        for key, values in data.get("hyperparams_differing", {}).items():
            if key != "artifacts":  # checkpoint metadata has its own Inspector section
                lines.append(
                    f"| {_value(key)} | "
                    + " | ".join(_parameter(values.get(str(r["run_id"]))) for r in runs)
                    + " |"
                )
        for run in runs:
            if run["status"] != "completed":
                lines.append(
                    f"{_value(run['run_name'])}: "
                    + (
                        "chưa hoàn thành, không được xếp hạng best."
                        if vi
                        else "not completed; excluded from best ranking."
                    )
                )
        return "\n".join(lines)
    verdicts = {
        "no_overfitting": ("chưa thấy dấu hiệu overfitting", "shows no overfitting signs"),
        "possible_overfitting": (
            "có dấu hiệu overfitting, chưa thể kết luận chắc chắn",
            "shows possible overfitting",
        ),
        "overfitting": (
            "có dấu hiệu overfitting theo heuristic",
            "shows overfitting by the heuristic",
        ),
        "insufficient_data": (
            "chưa đủ dữ liệu validation để đánh giá overfitting",
            "has insufficient validation data",
        ),
    }
    text = f"**{_value(data['run_name'])}** {verdicts[data['verdict']][0 if vi else 1]}."
    gap = data.get("accuracy_gap")
    if gap:
        text += (
            " Khoảng cách accuracy train−validation (trung bình cửa sổ): "
            if vi
            else " Train−validation accuracy gap (window means): "
        )
        text += f"{_value(gap['start'])} → {_value(gap['end'])}."
    trend = data.get("val_loss_trend")
    if trend:
        text += " val_loss thấp nhất " if vi else " Lowest val_loss "
        text += f"{_value(trend['lowest'])} (epoch {trend['lowest_epoch']}); "
        text += (
            ("trung bình cửa sổ cuối " if vi else "final window mean ")
            + _value(trend["final"])
            + "."
        )
    if data["verdict"] in {"overfitting", "possible_overfitting"}:
        text += (
            " Có thể thử early stopping hoặc điều chỉnh weight decay."
            if vi
            else " Consider early stopping or adjusting weight decay."
        )
    return text + (
        " Đây là dấu hiệu theo heuristic, không phải bằng chứng tuyệt đối."
        if vi
        else " This heuristic is a sign, not conclusive proof."
    )
