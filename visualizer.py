"""
SafeStay — visualizer.py
3D Digital Twin renderer using PyVista.
Maps YOLOv8 detections to 3D room coordinates and renders:
  • A wireframe hotel room box
  • Furniture mesh stand-ins (bed, desk, smoke-detector zone)
  • Red Warning Spheres at threat detection coordinates
  • Green Safe markers for verified clean zones
Falls back to a Matplotlib 3D scatter if PyVista is unavailable.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger("safestay.visualizer")

# Room dimensions in metres (matches CoordMapper3D in detector.py)
ROOM_W, ROOM_D, ROOM_H = 6.0, 4.0, 3.0

# ── Colour palette ────────────────────────────────────────────────────────────
BG_NAVY   = (10/255,  14/255,  26/255)   # #0A0E1A  Midnight Navy
GREEN_RGB = (46/255, 204/255, 113/255)   # #2ECC71  Safety Green
RED_RGB   = (231/255, 76/255,  60/255)   # #E74C3C  Threat Red
AMBER_RGB = (243/255, 156/255, 18/255)   # #F39C12  Warning Amber
WALL_RGB  = (20/255,  26/255,  50/255)   # Dark blue-grey walls
WIRE_RGB  = (46/255,  60/255, 100/255)   # Wire-frame edges


@dataclass
class ThreatMarker:
    x: float
    y: float
    z: float
    level: str         # CRITICAL / HIGH / MEDIUM / LOW
    label: str
    score: float

    @property
    def colour(self) -> tuple[float, float, float]:
        return {
            "CRITICAL": RED_RGB,
            "HIGH":     RED_RGB,
            "MEDIUM":   AMBER_RGB,
            "LOW":      GREEN_RGB,
        }.get(self.level, AMBER_RGB)

    @property
    def radius(self) -> float:
        return 0.10 + self.score * 0.18


# ── PyVista Renderer ──────────────────────────────────────────────────────────

class RoomVisualizer3D:
    """
    PyVista-based 3D Digital Twin of a hotel room.
    Call `render_to_bytes()` to get a PNG suitable for st.image().
    """

    def __init__(self):
        self._pyvista_ok = self._check_pyvista()

    @staticmethod
    def _check_pyvista() -> bool:
        try:
            import pyvista  # type: ignore  # noqa: F401
            return True
        except ImportError:
            logger.warning("PyVista not installed — using Matplotlib fallback")
            return False

    # ── Scene Construction ────────────────────────────────────────────────────

    def _build_scene(self, markers: list[ThreatMarker]):
        """Build and return a PyVista Plotter with the hotel room scene."""
        import pyvista as pv  # type: ignore

        pl = pv.Plotter(off_screen=True, window_size=[900, 600])
        pl.set_background(BG_NAVY)

        # ── Room walls (transparent boxes) ────────────────────────────────────
        room = pv.Box(bounds=(0, ROOM_W, 0, ROOM_D, 0, ROOM_H))
        pl.add_mesh(room, style="wireframe", color=WIRE_RGB, line_width=1.5, opacity=0.4)

        # ── Floor ─────────────────────────────────────────────────────────────
        floor = pv.Plane(
            center=(ROOM_W/2, ROOM_D/2, 0),
            direction=(0, 0, 1),
            i_size=ROOM_W, j_size=ROOM_D,
        )
        pl.add_mesh(floor, color=WALL_RGB, opacity=0.6)

        # ── Furniture stand-ins ───────────────────────────────────────────────
        # Bed
        bed = pv.Box(bounds=(0.3, 2.2, 0.4, 3.6, 0, 0.5))
        pl.add_mesh(bed, color=(0.15, 0.18, 0.32), opacity=0.7)

        # Desk
        desk = pv.Box(bounds=(4.0, 5.8, 0.3, 1.2, 0, 0.75))
        pl.add_mesh(desk, color=(0.12, 0.15, 0.28), opacity=0.7)

        # Ceiling fixture (smoke detector zone)
        fixture = pv.Cylinder(
            center=(ROOM_W/2, ROOM_D/2, ROOM_H - 0.05),
            direction=(0, 0, 1),
            radius=0.08, height=0.06,
        )
        pl.add_mesh(fixture, color=(0.6, 0.6, 0.6), opacity=0.8)

        # ── Room label ────────────────────────────────────────────────────────
        pl.add_text(
            "SafeStay Digital Twin — Hotel Room",
            position="upper_left",
            font_size=10,
            color=GREEN_RGB,
            font="courier",
        )

        # ── Threat Markers ────────────────────────────────────────────────────
        for m in markers:
            sphere = pv.Sphere(radius=m.radius, center=(m.x, m.y, m.z))
            pl.add_mesh(sphere, color=m.colour, opacity=0.85,
                        smooth_shading=True, specular=0.5)

            # Pulsing ring around CRITICAL threats
            if m.level in ("CRITICAL", "HIGH"):
                ring = pv.Disc(
                    center=(m.x, m.y, m.z),
                    normal=(0, 0, 1),
                    inner=m.radius * 1.3,
                    outer=m.radius * 2.0,
                )
                pl.add_mesh(ring, color=m.colour, opacity=0.35, style="wireframe",
                            line_width=2.0)

            # Vertical drop line to floor
            line = pv.Line((m.x, m.y, 0.0), (m.x, m.y, m.z))
            pl.add_mesh(line, color=m.colour, opacity=0.5, line_width=1.0)

            pl.add_point_labels(
                [m.x, m.y, m.z + m.radius + 0.1],
                [f"{m.label} {m.score*100:.0f}%"],
                font_size=8,
                text_color=m.colour,
                always_visible=True,
                show_points=False,
            )

        # ── Camera ────────────────────────────────────────────────────────────
        pl.camera_position = [
            (ROOM_W * 1.8, -ROOM_D * 0.9, ROOM_H * 1.6),   # eye
            (ROOM_W / 2,   ROOM_D / 2,    ROOM_H / 2),      # focal
            (0, 0, 1),                                        # up
        ]
        pl.add_axes(line_width=2, color="white", xlabel="X (m)", ylabel="Y (m)", zlabel="Z (m)")

        return pl

    # ── Public API ────────────────────────────────────────────────────────────

    def render_to_bytes(self, markers: list[ThreatMarker]) -> bytes:
        """Render scene to PNG bytes (for Streamlit st.image)."""
        if self._pyvista_ok:
            return self._render_pyvista(markers)
        return self._render_matplotlib(markers)

    def _render_pyvista(self, markers: list[ThreatMarker]) -> bytes:
        pl = self._build_scene(markers)
        img_arr = pl.screenshot(return_img=True)
        pl.close()
        # Convert numpy array → PNG bytes
        from PIL import Image  # type: ignore
        buf = io.BytesIO()
        Image.fromarray(img_arr).save(buf, format="PNG")
        return buf.getvalue()

    def _render_matplotlib(self, markers: list[ThreatMarker]) -> bytes:
        """Fallback 3D scatter plot using Matplotlib."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

        fig = plt.figure(figsize=(9, 6), facecolor=BG_NAVY)
        ax  = fig.add_subplot(111, projection="3d", facecolor=BG_NAVY)

        # Room wireframe
        for x in (0, ROOM_W):
            for y in (0, ROOM_D):
                ax.plot([x, x], [y, y], [0, ROOM_H], color=WIRE_RGB, lw=0.8, alpha=0.5)
        for x in (0, ROOM_W):
            for z in (0, ROOM_H):
                ax.plot([x, x], [0, ROOM_D], [z, z], color=WIRE_RGB, lw=0.8, alpha=0.5)
        for y in (0, ROOM_D):
            for z in (0, ROOM_H):
                ax.plot([0, ROOM_W], [y, y], [z, z], color=WIRE_RGB, lw=0.8, alpha=0.5)

        # Threat markers
        for m in markers:
            size = 120 + m.score * 400
            c    = [m.colour]
            ax.scatter(m.x, m.y, m.z, s=size, c=c, alpha=0.85, zorder=5)
            ax.text(m.x, m.y, m.z + 0.15,
                    f"{m.label[:12]}\n{m.score*100:.0f}%",
                    color=m.colour, fontsize=6.5, ha="center",
                    fontfamily="monospace")
            ax.plot([m.x, m.x], [m.y, m.y], [0, m.z], color=m.colour, lw=0.8, alpha=0.4)

        ax.set_xlim(0, ROOM_W); ax.set_ylim(0, ROOM_D); ax.set_zlim(0, ROOM_H)
        ax.set_xlabel("X (m)", color="white", fontsize=8)
        ax.set_ylabel("Y (m)", color="white", fontsize=8)
        ax.set_zlabel("Z (m)", color="white", fontsize=8)
        ax.tick_params(colors="gray", labelsize=6)
        for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
            pane.fill      = False
            pane.set_edgecolor(WIRE_RGB)
        ax.set_title("SafeStay 3D Digital Twin", color=GREEN_RGB, fontsize=11,
                     fontfamily="monospace")

        buf = io.BytesIO()
        plt.savefig(buf, format="PNG", bbox_inches="tight",
                    facecolor=BG_NAVY, dpi=130)
        plt.close(fig)
        return buf.getvalue()


# ── Marker Builder ────────────────────────────────────────────────────────────

def build_markers_from_scan(scan_data: dict) -> list[ThreatMarker]:
    """Convert API scan result detections into ThreatMarker objects."""
    markers = []
    for d in scan_data.get("detections", []):
        c = d.get("coord_3d", {})
        if not all(k in c for k in ("x", "y", "z")):
            continue
        host = d.get("host_object") or "Unknown"
        markers.append(ThreatMarker(
            x     = float(c["x"]),
            y     = float(c["y"]),
            z     = float(c["z"]),
            level = d.get("threat_level", "LOW"),
            label = host[:18],
            score = float(d.get("threat_score", 0)),
        ))
    return markers


# ── Singleton ─────────────────────────────────────────────────────────────────
_visualizer = RoomVisualizer3D()


def render_room(scan_data: dict) -> bytes:
    """
    Public one-call API.
    Pass in a scan result dict, get back PNG bytes ready for st.image().
    """
    markers = build_markers_from_scan(scan_data)
    return _visualizer.render_to_bytes(markers)


def render_empty_room() -> bytes:
    """Render the room with no threat markers (idle state)."""
    return _visualizer.render_to_bytes([])
