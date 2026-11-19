"""Predict a local RGB/grayscale/RGBA image without any network access."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch
from PIL import Image, UnidentifiedImageError

from training.data import resolve, transform
from training.engine import load_checkpoint
from training.models import device_for


def predict(checkpoint, image, device="cpu"):
    device = device_for(device)
    model, state = load_checkpoint(resolve(checkpoint), device)
    try:
        with Image.open(resolve(image)) as picture:
            tensor = transform(preprocessing=state["config"]["preprocessing"])(
                picture.convert("RGB")
            )
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise ValueError("Image missing, corrupt, unsupported, or too large") from exc
    model.eval()
    with torch.inference_mode():
        probabilities = model(tensor.unsqueeze(0).to(device)).softmax(1)[0].cpu().tolist()
    classes = state["config"]["classes"]
    return {
        "label": classes[max(range(10), key=probabilities.__getitem__)],
        "probabilities": dict(zip(classes, probabilities, strict=True)),
        "note": "Softmax scores are not calibrated confidence; CIFAR-10 classes only.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint")
    parser.add_argument("image", help="Relative paths resolve against backend/")
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    args = parser.parse_args()
    try:
        print(json.dumps(predict(args.checkpoint, args.image, args.device)))
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Prediction failed: {exc}\n")


if __name__ == "__main__":
    main()
