# finch.py — Finch 2.0 drawing simulator (Python 3.13, notebook-friendly)
# Usage (in a Jupyter/VS Code cell):
#   from finch import Finch, Move, Turn
#   f = Finch()
#   f.setMove(Move.FORWARD, 20, 10)
#   f.setTurn(Turn.LEFT, 90, 30)
#   f  # evaluating the cell displays the drawing inline
#
# Notes:
# - Wheelbase = 10 cm; pen at chassis center; pen always down.
# - Motors accept cm/s. setMove uses cm and cm/s. setTurn uses degrees and deg/s.
# - Stubs provided for LEDs, buzzer, sensors.
# - Files saved to FINCH_SIM_OUTPUT (PNG) or "finch_sim_output.png"; SVG alongside.

from __future__ import annotations

import atexit
import dataclasses
import io
import math
import os
from typing import Literal

WHEELBASE_CM: float = 10.0


@dataclasses.dataclass(slots=True)
class Pose:
    x: float = 0.0  # cm
    y: float = 0.0  # cm
    th: float = 0.0  # radians (0 = +X)


class Finch:
    _pose: Pose
    _path: list[tuple[float, float]]
    _closed: bool
    _png_path: str
    _svg_path: str

    def __init__(self) -> None:
        self._pose = Pose()
        self._path = [(0.0, 0.0)]
        self._closed = False
        self._png_path = os.environ.get("FINCH_SIM_OUTPUT", "finch_sim_output.png")
        self._svg_path = os.path.splitext(self._png_path)[0] + ".svg"
        atexit.register(self._maybe_render)

    # --- Differential-drive integration -------------------------------------
    def _advance(self, vl_cm_s: float, vr_cm_s: float, dt: float) -> None:
        if dt <= 0.0:
            return
        v: float = 0.5 * (vl_cm_s + vr_cm_s)
        omega: float = (vr_cm_s - vl_cm_s) / WHEELBASE_CM  # rad/s
        x, y, th = self._pose.x, self._pose.y, self._pose.th

        steps: int = max(1, int(math.ceil(dt / 0.02)))
        h: float = dt / steps
        for _ in range(steps):
            if abs(omega) < 1e-9:
                x += v * h * math.cos(th)
                y += v * h * math.sin(th)
            else:
                th_new: float = th + omega * h
                R: float = v / omega if abs(v) > 1e-12 else 0.0
                x += R * (math.sin(th_new) - math.sin(th))
                y -= R * (math.cos(th_new) - math.cos(th))
                th = th_new
            self._path.append((x, y))
        self._pose = Pose(x, y, th)

    # --- Motor API -----------------------------------------------------------
    def wheels(
        self, left_cm_s: float, right_cm_s: float, duration: float | None = None
    ) -> None:
        if duration is None:
            return
        self._advance(left_cm_s, right_cm_s, float(duration))

    def setMove(
        self, direction: Literal["F", "B"], distance_cm: float, speed_cm_s: float
    ) -> None:
        distance_cm = float(distance_cm) * (1 if direction == "F" else -1)
        speed_cm_s = abs(float(speed_cm_s))
        if speed_cm_s <= 0.0:
            return
        duration: float = abs(distance_cm) / speed_cm_s
        vl = vr = speed_cm_s * (1 if distance_cm >= 0 else -1)
        self._advance(vl, vr, duration)

    def setTurn(
        self, direction: Literal["L", "R"], degrees: float, deg_per_s: float
    ) -> None:
        degrees = float(degrees) * (1 if direction == "L" else -1)
        deg_per_s = abs(float(deg_per_s))
        if deg_per_s <= 0.0:
            return
        omega_sign: float = 1.0 if degrees >= 0.0 else -1.0
        omega: float = math.radians(deg_per_s) * omega_sign
        duration: float = abs(math.radians(degrees)) / abs(omega)
        s: float = 0.5 * abs(omega) * WHEELBASE_CM
        vl: float = -s if degrees >= 0 else s
        vr: float = +s if degrees >= 0 else -s
        self._advance(vl, vr, duration)

    # --- Stubs for compatibility --------------------------------------------
    def setLED(self, r: int, g: int, b: int) -> None: ...
    def setBeak(self, r: int, g: int, b: int) -> None: ...
    def setTail(self, position: int, r: int, g: int, b: int) -> None: ...
    def playTone(self, freq_hz: int, duration_s: float) -> None: ...
    def stopAll(self) -> None: ...

    def getDistance(self) -> float:
        return 0.0

    def getLine(self) -> tuple[int, int]:
        return (0, 0)

    def getLight(self) -> tuple[float, float]:
        return (0.0, 0.0)

    def getTemperature(self) -> float:
        return 20.0

    def getOrientation(self) -> tuple[float, float, float]:
        return (0.0, 0.0, 0.0)

    def getAcceleration(self) -> tuple[float, float, float]:
        return (0.0, 0.0, 0.0)

    # --- Lifecycle -----------------------------------------------------------
    def close(self) -> None:
        self._maybe_render()

    # --- Rendering: file + notebook inline ----------------------------------
    def _maybe_render(self) -> None:
        if self._closed:
            return
        self._closed = True
        if len(self._path) < 2:
            return
        try:
            self._write_svg_png()
        except Exception:
            pass

    def _bounds(self) -> tuple[float, float, float, float]:
        xs, ys = zip(*self._path)
        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)
        dx, dy = max(1e-6, maxx - minx), max(1e-6, maxy - miny)
        margin = 0.1
        return (
            minx - dx * margin,
            miny - dy * margin,
            dx * (1 + 2 * margin),
            dy * (1 + 2 * margin),
        )

    def _to_svg_string(self) -> str:
        view_min_x, view_min_y, view_w, view_h = self._bounds()
        path_d: str = "M " + " L ".join(f"{x:.3f},{-y:.3f}" for (x, y) in self._path)

        # Fixed width of 400px, height scales proportionally (capped at 400px)
        target_width: int = 400
        aspect_ratio: float = view_h / view_w if view_w > 0 else 1.0
        target_height: int = min(400, max(2, int(target_width * aspect_ratio)))

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{target_width}" height="{target_height}"
     viewBox="{view_min_x:.3f} {-view_min_y - view_h:.3f} {view_w:.3f} {view_h:.3f}">
  <rect x="{view_min_x:.3f}" y="{-view_min_y - view_h:.3f}" width="{view_w:.3f}" height="{view_h:.3f}" fill="white" />
  <path d="{path_d}" fill="none" stroke="black" stroke-width="0.5"/>
</svg>
'''

    def _write_svg_png(self) -> None:
        svg: str = self._to_svg_string()
        with open(self._svg_path, "w", encoding="utf-8") as f:
            f.write(svg)
        try:
            png_bytes = self._png_bytes()
            if png_bytes is not None:
                with open(self._png_path, "wb") as f:
                    f.write(png_bytes)
        except Exception:
            pass

    def _png_bytes(self) -> bytes | None:
        try:
            from PIL import Image, ImageDraw  # type: ignore
        except Exception:
            return None

        view_min_x, view_min_y, view_w, view_h = self._bounds()

        # Scale to 600px width while maintaining aspect ratio
        target_width: int = 600
        aspect_ratio: float = view_h / view_w if view_w > 0 else 1.0
        W: int = target_width
        H: int = max(2, int(target_width * aspect_ratio))

        scale_x: float = W / view_w if view_w > 0 else 1.0
        scale_y: float = H / view_h if view_h > 0 else 1.0

        img = Image.new("RGB", (W, H), "white")
        draw = ImageDraw.Draw(img)

        def map_pt(x: float, y: float) -> tuple[int, int]:
            sx: int = int((x - view_min_x) * scale_x)
            sy: int = int(((-y) - (-view_min_y - view_h)) * scale_y)
            return (sx, sy)

        p0 = map_pt(*self._path[0])
        for p in self._path[1:]:
            p1 = map_pt(*p)
            draw.line([p0, p1], fill="black", width=2)
            p0 = p1

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    # --- Notebook rich display hooks ----------------------------------------
    def _repr_png_(self) -> bytes | None:
        # Called by Jupyter/VS Code to inline-render PNG when the object is the cell result.
        return self._png_bytes()

    # --- Notebook rich display hooks ----------------------------------------
    def _repr_mimebundle_(
        self, include: list[str] | None = None, exclude: list[str] | None = None
    ) -> dict[str, bytes | str] | None:
        """Return both PNG and SVG for Jupyter/VS Code inline display."""
        try:
            png = self._png_bytes()
        except Exception:
            png = None
        svg = self._to_svg_string()
        bundle: dict[str, bytes | str] = {"image/svg+xml": svg}
        if png is not None:
            bundle["image/png"] = png
        return bundle

    def show(self) -> None:
        """Display the Finch drawing inline in a Jupyter notebook, even if not the last statement."""
        try:
            from IPython.display import display

            display(self)
        except Exception:
            pass
