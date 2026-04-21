# SafeStay — YOLOv8 Model Weights

Place your custom-trained `yolov8n_safe.pt` weights file in this directory.

## Training Your Own Weights

```bash
from ultralytics import YOLO

# Start from the nano pretrained base
model = YOLO("yolov8n.pt")

# Fine-tune on your hidden camera lens dataset
model.train(
    data   = "safestay_dataset.yaml",
    epochs = 100,
    imgsz  = 640,
    batch  = 16,
    name   = "yolov8n_safe",
    device = "cpu",   # or "cuda:0" for GPU
)

# Export to TFLite INT8 for mobile edge inference
model.export(format="tflite", int8=True)
```

## Dataset Format (safestay_dataset.yaml)

```yaml
path: /data/safestay
train: images/train
val:   images/val

nc: 3
names: ["lens", "smoke_detector_cam", "clock_cam"]
```

## Fallback Behaviour

If `yolov8n_safe.pt` is not present, SafeStayEngine automatically falls back
to `yolov8n.pt` (standard pretrained weights) as a proxy. Detection accuracy
will be lower but the pipeline remains fully functional for demonstration.

## Recommended Labelling Sources

- Airbnb hidden camera case photographs (publicly documented)
- ESP32-CAM module lens close-ups
- Smoke detector + clock camera product listings
