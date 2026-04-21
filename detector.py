"""
SafeStay — detector.py
YOLOv8 + OpenCV optical lens detection engine with 3D coordinate mapping.
Combines Hough Circle Transform, host-object classification, and threat scoring.
"""

from __future__ import annotations

import math
import time
import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger("safestay.detector")

# ── Constants ────────────────────────────────────────────────────────────────

MODEL_PATH   = Path(__file__).parent.parent / "models" / "yolov8n_safe.pt"

# High-risk host objects that commonly conceal cameras
HIGH_RISK_CLASSES = {
    "smoke detector", "clock", "alarm clock", "usb charger",
    "power bank", "air purifier", "router", "speaker", "mirror",
    "picture frame", "smoke_detector", "clock_radio",
}

# Threat level thresholds
THRESHOLDS = {"CRITICAL": 0.75, "HIGH": 0.55, "MEDIUM": 0.35, "LOW": 0.0}

# 3D room bounding box (metres) — maps pixel coords → room coordinates
ROOM_3D = {"x_range": (0.0, 6.0), "y_range": (0.0, 4.0), "z_range": (0.0, 3.0)}


# ── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class Detection:
    """Single lens/camera detection result."""
    frame_id:       int
    bbox:           tuple[int, int, int, int]   # x1, y1, x2, y2 (pixels)
    ai_confidence:  float
    host_object:    Optional[str]
    is_high_risk:   bool
    hough_radius:   Optional[float]
    coord_3d:       tuple[float, float, float]  # (x, y, z) metres
    threat_score:   float
    threat_level:   str
    frame_hash:     str
    timestamp:      float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "frame_id":      self.frame_id,
            "bbox":          list(self.bbox),
            "ai_confidence": round(self.ai_confidence, 4),
            "host_object":   self.host_object,
            "is_high_risk":  self.is_high_risk,
            "hough_radius":  self.hough_radius,
            "coord_3d":      {"x": round(self.coord_3d[0], 3),
                              "y": round(self.coord_3d[1], 3),
                              "z": round(self.coord_3d[2], 3)},
            "threat_score":  round(self.threat_score, 4),
            "threat_level":  self.threat_level,
            "frame_hash":    self.frame_hash,
            "timestamp":     self.timestamp,
        }


@dataclass
class ScanResult:
    """Aggregated result of a full camera scan session."""
    session_id:      str
    frames_analysed: int
    detections:      list[Detection]
    peak_score:      float
    overall_level:   str
    network_match:   bool = False
    ir_detected:     bool = False
    fusion_critical: bool = False

    @property
    def camera_count(self) -> int:
        return len([d for d in self.detections if d.threat_level in ("CRITICAL", "HIGH")])

    def to_dict(self) -> dict:
        return {
            "session_id":      self.session_id,
            "frames_analysed": self.frames_analysed,
            "detections":      [d.to_dict() for d in self.detections],
            "peak_score":      round(self.peak_score, 4),
            "overall_level":   self.overall_level,
            "network_match":   self.network_match,
            "ir_detected":     self.ir_detected,
            "fusion_critical": self.fusion_critical,
            "camera_count":    self.camera_count,
        }


# ── Threat Scorer ────────────────────────────────────────────────────────────

class ThreatScorer:
    """
    Combines four independent signals into a single threat score [0.0 – 1.0].

    Weights (must sum to 1.0):
        AI lens confidence     → 40%
        High-risk host object  → 25%
        IR LED detected        → 20%
        Network MAC match      → 15%

    CRITICAL override: if AI confidence > 0.60 AND network_match → floor = 0.90
    """

    WEIGHTS = {
        "ai":      0.40,
        "host":    0.25,
        "ir":      0.20,
        "network": 0.15,
    }

    @classmethod
    def compute(
        cls,
        ai_confidence: float,
        host_is_risky: bool,
        ir_detected:   bool,
        network_match: bool,
    ) -> tuple[float, str]:
        raw = (
            cls.WEIGHTS["ai"]      * ai_confidence +
            cls.WEIGHTS["host"]    * (1.0 if host_is_risky else 0.0) +
            cls.WEIGHTS["ir"]      * (1.0 if ir_detected    else 0.0) +
            cls.WEIGHTS["network"] * (1.0 if network_match  else 0.0)
        )

        # Fusion CRITICAL override rule
        if ai_confidence > 0.60 and network_match:
            raw = max(raw, 0.90)

        score = min(raw, 1.0)

        level = "LOW"
        for lvl, threshold in THRESHOLDS.items():
            if score >= threshold:
                level = lvl
                break

        return score, level


# ── 3D Coordinate Mapper ─────────────────────────────────────────────────────

class CoordMapper3D:
    """
    Maps a 2D bounding box centre (pixels) to a 3D room coordinate (metres).

    The frame is treated as a projection of one wall of the room.
    x → horizontal room axis, z → vertical (height), y → estimated depth
    based on bbox area (larger bbox = closer to camera = closer to front wall).
    """

    def __init__(self, frame_w: int, frame_h: int):
        self.fw = frame_w
        self.fh = frame_h

    def map(self, bbox: tuple[int, int, int, int]) -> tuple[float, float, float]:
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        bbox_area = (x2 - x1) * (y2 - y1)
        frame_area = self.fw * self.fh

        rx, ry, rz = ROOM_3D["x_range"], ROOM_3D["y_range"], ROOM_3D["z_range"]

        room_x = rx[0] + (cx / self.fw)  * (rx[1] - rx[0])
        room_z = rz[0] + (1 - cy / self.fh) * (rz[1] - rz[0])   # flip y→z

        # Depth estimate: small objects are farther away
        depth_norm = 1.0 - min(bbox_area / (frame_area * 0.25), 1.0)
        room_y = ry[0] + depth_norm * (ry[1] - ry[0])

        return round(room_x, 3), round(room_y, 3), round(room_z, 3)


# ── SafeStay Engine ──────────────────────────────────────────────────────────

class SafeStayEngine:
    """
    Main detection engine.  Loads YOLOv8 (or falls back to OpenCV-only mode
    if the model file is absent) and runs per-frame inference + Hough Circles.
    """

    def __init__(self, model_path: Path = MODEL_PATH, confidence: float = 0.40):
        self.confidence   = confidence
        self.model        = None
        self.model_path   = model_path
        self._frame_count = 0
        self._try_load_model()

    # ── Model Loading ──────────────────────────────────────────────────────

    def _try_load_model(self):
        try:
            from ultralytics import YOLO          # type: ignore
            if self.model_path.exists():
                self.model = YOLO(str(self.model_path))
                logger.info("YOLOv8 model loaded: %s", self.model_path)
            else:
                # Fall back to YOLOv8n pretrained as proxy
                self.model = YOLO("yolov8n.pt")
                logger.warning("Custom weights not found — using yolov8n.pt proxy")
        except ImportError:
            logger.warning("ultralytics not installed — running OpenCV-only mode")

    # ── Frame Analysis ──────────────────────────────────────────────────────

    def analyse_frame(
        self,
        frame:         np.ndarray,
        network_match: bool = False,
        ir_detected:   bool = False,
    ) -> list[Detection]:
        """
        Full per-frame pipeline:
          1. YOLOv8 inference (or mock detections)
          2. Hough Circle Transform for lens verification
          3. Host object classification
          4. Threat scoring + 3D mapping
        """
        self._frame_count += 1
        h, w = frame.shape[:2]
        mapper = CoordMapper3D(w, h)

        raw_boxes = self._yolo_detect(frame)
        circles   = self._hough_detect(frame)
        results: list[Detection] = []

        for box in raw_boxes:
            x1, y1, x2, y2, conf, cls_name = box
            host_risky  = cls_name.lower() in HIGH_RISK_CLASSES
            hough_r     = self._nearest_circle(circles, (x1, y1, x2, y2))
            ai_conf     = min(conf + (0.08 if hough_r else 0.0), 1.0)

            score, level = ThreatScorer.compute(
                ai_confidence = ai_conf,
                host_is_risky = host_risky,
                ir_detected   = ir_detected,
                network_match = network_match,
            )

            frame_hash = self._hash_region(frame, (x1, y1, x2, y2))
            coord_3d   = mapper.map((x1, y1, x2, y2))

            det = Detection(
                frame_id      = self._frame_count,
                bbox          = (x1, y1, x2, y2),
                ai_confidence = ai_conf,
                host_object   = cls_name,
                is_high_risk  = host_risky,
                hough_radius  = hough_r,
                coord_3d      = coord_3d,
                threat_score  = score,
                threat_level  = level,
                frame_hash    = frame_hash,
            )
            results.append(det)
            logger.debug("Detection: level=%s score=%.3f coord=%s", level, score, coord_3d)

        return results

    # ── YOLOv8 Inference ────────────────────────────────────────────────────

    def _yolo_detect(self, frame: np.ndarray) -> list[tuple]:
        """Returns list of (x1, y1, x2, y2, confidence, class_name)."""
        if self.model is None:
            return self._mock_detect(frame)
        try:
            results = self.model(frame, conf=self.confidence, verbose=False)
            boxes = []
            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf      = float(box.conf[0])
                    cls_id    = int(box.cls[0])
                    cls_name  = r.names.get(cls_id, "unknown")
                    boxes.append((x1, y1, x2, y2, conf, cls_name))
            return boxes
        except Exception as exc:
            logger.error("YOLO inference failed: %s", exc)
            return self._mock_detect(frame)

    def _mock_detect(self, frame: np.ndarray) -> list[tuple]:
        """
        Deterministic mock detections for demo / offline mode.
        Simulates a lens inside a smoke detector.
        """
        h, w = frame.shape[:2]
        return [
            (int(w*0.30), int(h*0.25), int(w*0.52), int(h*0.48), 0.82, "smoke detector"),
            (int(w*0.60), int(h*0.55), int(w*0.72), int(h*0.68), 0.61, "clock"),
        ]

    # ── Hough Circle Transform ───────────────────────────────────────────────

    def _hough_detect(self, frame: np.ndarray) -> list[tuple[int, int, int]]:
        """Detect circular lens reflections using Hough Circles."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (9, 9), 2)
        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=30,
            param1=60,
            param2=35,
            minRadius=4,
            maxRadius=60,
        )
        if circles is None:
            return []
        return [(int(x), int(y), int(r)) for x, y, r in circles[0]]

    def _nearest_circle(
        self,
        circles: list[tuple[int, int, int]],
        bbox:    tuple[int, int, int, int],
        max_dist: float = 40.0,
    ) -> Optional[float]:
        """Return the radius of the Hough circle closest to bbox centre, if within max_dist."""
        if not circles:
            return None
        x1, y1, x2, y2 = bbox
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        best_r, best_d = None, float("inf")
        for hx, hy, hr in circles:
            d = math.hypot(hx - cx, hy - cy)
            if d < best_d:
                best_d, best_r = d, float(hr)
        return best_r if best_d <= max_dist else None

    # ── Frame Integrity Hash ─────────────────────────────────────────────────

    @staticmethod
    def _hash_region(frame: np.ndarray, bbox: tuple[int, int, int, int]) -> str:
        """SHA-256 of the raw pixel bytes within the bounding box."""
        x1, y1, x2, y2 = bbox
        region = frame[y1:y2, x1:x2]
        return hashlib.sha256(region.tobytes()).hexdigest()

    # ── Session Scan ─────────────────────────────────────────────────────────

    def run_session(
        self,
        source:        int | str = 0,
        num_frames:    int        = 12,
        network_match: bool       = False,
        ir_detected:   bool       = False,
    ) -> ScanResult:
        """
        Capture `num_frames` from `source` (webcam index or video path),
        analyse each frame, and return a ScanResult.
        Falls back to synthetic frames if camera not available.
        """
        import uuid
        session_id = uuid.uuid4().hex[:12]
        all_detections: list[Detection] = []

        cap = cv2.VideoCapture(source)
        use_synth = not cap.isOpened()
        if use_synth:
            logger.warning("Camera source %s unavailable — using synthetic frames", source)

        for _ in range(num_frames):
            if use_synth:
                frame = self._synthetic_frame()
            else:
                ok, frame = cap.read()
                if not ok:
                    frame = self._synthetic_frame()

            dets = self.analyse_frame(frame, network_match=network_match, ir_detected=ir_detected)
            all_detections.extend(dets)

        if not use_synth:
            cap.release()

        peak   = max((d.threat_score for d in all_detections), default=0.0)
        level  = "CLEAN"
        for lvl, thr in THRESHOLDS.items():
            if peak >= thr:
                level = lvl
                break

        fusion = any(
            d.ai_confidence > 0.60 and network_match
            for d in all_detections
        )

        return ScanResult(
            session_id      = session_id,
            frames_analysed = num_frames,
            detections      = all_detections,
            peak_score      = peak,
            overall_level   = level,
            network_match   = network_match,
            ir_detected     = ir_detected,
            fusion_critical = fusion,
        )

    @staticmethod
    def _synthetic_frame() -> np.ndarray:
        """Generate a realistic-looking synthetic frame for demo mode."""
        frame = np.random.randint(20, 60, (480, 640, 3), dtype=np.uint8)
        # Add a circular lens-like feature
        cx, cy = np.random.randint(160, 480), np.random.randint(120, 360)
        cv2.circle(frame, (cx, cy), np.random.randint(8, 22), (180, 200, 210), -1)
        cv2.circle(frame, (cx, cy), np.random.randint(3, 7),  (240, 255, 255), -1)
        return frame
