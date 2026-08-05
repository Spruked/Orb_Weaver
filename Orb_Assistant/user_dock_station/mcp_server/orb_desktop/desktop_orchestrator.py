"""
ORB Desktop Orchestrator
Cross-platform desktop automation layer.
Uses pyautogui as primary driver with pynput fallback.
All methods return a uniform ORBResult object.
"""

from __future__ import annotations
import time
import base64
import ctypes
import ctypes.wintypes
import io
import json
import os
import re
import shlex
import subprocess
import tempfile
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ──────────────────────────────────────────────
# Result container
# ──────────────────────────────────────────────

@dataclass
class ORBResult:
    success: bool
    content: List[Dict[str, Any]] = field(default_factory=list)
    error: str = ""

    @classmethod
    def ok(cls, text: str) -> "ORBResult":
        return cls(success=True, content=[{"type": "text", "text": text}])

    @classmethod
    def image_ok(cls, b64: str, caption: str = "Screenshot") -> "ORBResult":
        return cls(
            success=True,
            content=[
                {"type": "text", "text": caption},
                {"type": "image", "data": b64, "mimeType": "image/jpeg"},
            ]
        )

    @classmethod
    def fail(cls, message: str) -> "ORBResult":
        return cls(success=False, content=[{"type": "text", "text": message}], error=message)


# ──────────────────────────────────────────────
# Desktop Controller
# ──────────────────────────────────────────────

class ORBDesktopController:
    """
    Wraps pyautogui / pynput / PIL.
    Lazy-imports at method call time — ORB will still launch even if
    optional packages are missing; they'll surface clear errors.
    """

    def __init__(self):
        self._pyautogui   = None
        self._screenshot_mod = None
        self._clipboard_mod  = None
        self._ready = False
        self._dpi_awareness = self._set_dpi_awareness()
        self._init()

    def _set_dpi_awareness(self) -> Dict[str, Any]:
        status = {"platform": os.name, "attempted": False, "mode": None, "ok": False, "error": None}
        if os.name != "nt":
            return status
        status["attempted"] = True
        try:
            awareness_context_per_monitor_v2 = ctypes.c_void_p(-4)
            result = ctypes.windll.user32.SetProcessDpiAwarenessContext(awareness_context_per_monitor_v2)
            status.update({"mode": "PER_MONITOR_AWARE_V2", "ok": bool(result)})
            if result:
                return status
        except Exception as exc:
            status["error"] = str(exc)
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            status.update({"mode": "PROCESS_PER_MONITOR_DPI_AWARE", "ok": True, "error": None})
            return status
        except Exception as exc:
            status["error"] = str(exc)
        try:
            result = ctypes.windll.user32.SetProcessDPIAware()
            status.update({"mode": "PROCESS_SYSTEM_DPI_AWARE", "ok": bool(result)})
        except Exception as exc:
            status["error"] = str(exc)
        return status

    def _init(self):
        try:
            import pyautogui
            pyautogui.FAILSAFE      = True
            pyautogui.PAUSE         = 0.05
            self._pyautogui         = pyautogui
            self._ready             = True
        except ImportError:
            pass  # Will surface at call time

    def _require(self) -> None:
        if not self._ready or self._pyautogui is None:
            raise RuntimeError(
                "pyautogui not installed. Run: pip install pyautogui pillow pyperclip"
            )

    # ── Mouse ──────────────────────────────────────────

    def click(self, x: int, y: int, button: str = "left") -> ORBResult:
        try:
            self._require()
            self._pyautogui.click(x, y, button=button)
            return ORBResult.ok(f"Clicked {button} at ({x}, {y})")
        except Exception as e:
            return ORBResult.fail(f"click failed: {e}")

    def double_click(self, x: int, y: int) -> ORBResult:
        try:
            self._require()
            self._pyautogui.doubleClick(x, y)
            return ORBResult.ok(f"Double-clicked at ({x}, {y})")
        except Exception as e:
            return ORBResult.fail(f"double_click failed: {e}")

    def move_mouse(self, x: int, y: int) -> ORBResult:
        try:
            self._require()
            self._pyautogui.moveTo(x, y, duration=0.1)
            return ORBResult.ok(f"Moved mouse to ({x}, {y})")
        except Exception as e:
            return ORBResult.fail(f"move_mouse failed: {e}")

    def drag(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.3) -> ORBResult:
        try:
            self._require()
            self._pyautogui.dragTo(x2, y2, duration=duration, startX=x1, startY=y1)
            return ORBResult.ok(f"Dragged ({x1},{y1}) → ({x2},{y2})")
        except Exception as e:
            return ORBResult.fail(f"drag failed: {e}")

    def scroll(
        self,
        x: int, y: int,
        direction: str = "down",
        amount: int = 5
    ) -> ORBResult:
        try:
            self._require()
            self._pyautogui.moveTo(x, y)
            clicks = amount if direction in ("up", "right") else -amount
            if direction in ("up", "down"):
                self._pyautogui.scroll(clicks)
            else:
                self._pyautogui.hscroll(clicks)
            return ORBResult.ok(f"Scrolled {direction} {amount} at ({x}, {y})")
        except Exception as e:
            return ORBResult.fail(f"scroll failed: {e}")

    # ── Keyboard ───────────────────────────────────────

    def type_text(self, text: str, press_enter: bool = False, interval: float = 0.02) -> ORBResult:
        try:
            self._require()
            self._pyautogui.typewrite(text, interval=interval)
            if press_enter:
                self._pyautogui.press("enter")
            return ORBResult.ok(f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}")
        except Exception as e:
            return ORBResult.fail(f"type_text failed: {e}")

    def hotkey(self, *keys: str) -> ORBResult:
        try:
            self._require()
            self._pyautogui.hotkey(*keys)
            return ORBResult.ok(f"Hotkey: {'+'.join(keys)}")
        except Exception as e:
            return ORBResult.fail(f"hotkey failed: {e}")

    def press_key(self, key: str) -> ORBResult:
        try:
            self._require()
            self._pyautogui.press(key)
            return ORBResult.ok(f"Pressed: {key}")
        except Exception as e:
            return ORBResult.fail(f"press_key failed: {e}")

    # ── Screen ─────────────────────────────────────────

    def screenshot(self, width: int = 1024) -> ORBResult:
        try:
            self._require()
            img = self._pyautogui.screenshot()
            # Resize if needed
            if img.width > width:
                ratio  = width / img.width
                height = int(img.height * ratio)
                img    = img.resize((width, height))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85, optimize=True)
            b64 = base64.b64encode(buf.getvalue()).decode()
            return ORBResult.image_ok(b64, f"Screenshot ({img.width}x{img.height})")
        except Exception as e:
            return ORBResult.fail(f"screenshot failed: {e}")

    def _windows_path_to_wsl(self, value: str) -> str:
        raw = str(value or "")
        if len(raw) > 2 and raw[1] == ":":
            drive = raw[0].lower()
            rest = raw[2:].replace("\\", "/").lstrip("/")
            return f"/mnt/{drive}/{rest}"
        return raw.replace("\\", "/")

    def ocr_status(self) -> ORBResult:
        native_path = self._native_tesseract_path()
        native_status = {
            "available": bool(native_path),
            "path": native_path,
            "python_binding": False,
        }
        try:
            import pytesseract  # noqa: F401
            native_status["python_binding"] = True
        except Exception:
            pass
        configured = os.getenv("ORB_WSL_TESSERACT_BIN", "").strip()
        candidates = [
            configured,
            "tesseract",
            "/home/bryan/tesseract/build/bin/tesseract",
            "/home/bryan/tesseract/bin/tesseract",
            "/home/bryan/tesseract/tesseract",
        ]
        probe_script = "for c in " + " ".join(shlex.quote(c) for c in candidates if c) + "; do if command -v \"$c\" >/dev/null 2>&1; then command -v \"$c\"; \"$c\" --version | head -n 1; exit 0; fi; if [ -x \"$c\" ]; then echo \"$c\"; \"$c\" --version | head -n 1; exit 0; fi; done; if [ -d /home/bryan/tesseract ]; then echo SOURCE_ONLY:/home/bryan/tesseract; exit 2; fi; exit 1"
        wsl_status: Dict[str, Any] = {"available": False, "binary": None, "version": None, "error": None}
        try:
            probe = subprocess.run(
                ["wsl.exe", "-e", "sh", "-lc", probe_script],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception as exc:
            wsl_status["error"] = f"wsl_tesseract_unavailable:{exc}"
        else:
            if probe.returncode != 0:
                wsl_status["error"] = (probe.stdout or probe.stderr or "tesseract").strip()
            else:
                lines = probe.stdout.strip().splitlines()
                wsl_status.update({
                    "available": True,
                    "binary": lines[0] if lines else None,
                    "version": lines[1] if len(lines) > 1 else None,
                })
        payload = {"native": native_status, "wsl": wsl_status}
        if native_status["available"] and native_status["python_binding"]:
            return ORBResult.ok(json.dumps(payload, indent=2))
        if wsl_status["available"]:
            return ORBResult.ok(json.dumps(payload, indent=2))
        return ORBResult.fail(json.dumps(payload, indent=2))

    def ocr_screen(self, lang: str = "eng", psm: int = 6, width: int = 1400) -> ORBResult:
        status = self.ocr_status()
        if not status.success:
            return status
        try:
            self._require()
            img = self._pyautogui.screenshot()
            if img.width > width:
                ratio = width / img.width
                img = img.resize((width, int(img.height * ratio)))
            with tempfile.NamedTemporaryFile(prefix="orb_ocr_", suffix=".png", delete=False) as tmp:
                image_path = tmp.name
            img.save(image_path, format="PNG")
            wsl_image_path = self._windows_path_to_wsl(image_path)
            status_text = status.content[0].get("text", "") if status.content else ""
            tesseract_bin = (status_text.splitlines()[0] if status_text else os.getenv("ORB_WSL_TESSERACT_BIN", "tesseract")).strip()
            lang_safe = "".join(ch for ch in str(lang or "eng") if ch.isalnum() or ch in "_+-") or "eng"
            psm_safe = max(3, min(13, int(psm or 6)))
            command = f"{shlex.quote(tesseract_bin)} {shlex.quote(wsl_image_path)} stdout -l {shlex.quote(lang_safe)} --psm {psm_safe}"
            result = subprocess.run(["wsl.exe", "-e", "sh", "-lc", command], capture_output=True, text=True, timeout=45)
            try:
                os.unlink(image_path)
            except Exception:
                pass
            if result.returncode != 0:
                return ORBResult.fail(f"wsl_tesseract_ocr_failed:{result.stderr.strip() or result.stdout.strip()}")
            return ORBResult.ok(result.stdout.strip())
        except Exception as exc:
            return ORBResult.fail(f"ocr_screen failed: {exc}")

    def _normalize_ocr_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKC", str(text or "")).casefold()
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
        return re.sub(r"\s+", " ", normalized).strip()

    def _native_tesseract_path(self) -> Optional[str]:
        candidates = [
            os.getenv("ORB_TESSERACT_EXE", "").strip(),
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate
        return None

    def _foreground_window_info(self) -> Dict[str, Any]:
        if os.name != "nt":
            return {"hwnd": None, "title": "", "bounds": None, "client_bounds": None}
        user32 = ctypes.windll.user32
        hwnd = int(user32.GetForegroundWindow())
        return self._window_info(hwnd)

    def _window_info(self, hwnd: int) -> Dict[str, Any]:
        if os.name != "nt" or not hwnd:
            return {"hwnd": hwnd, "title": "", "bounds": None, "client_bounds": None}
        user32 = ctypes.windll.user32
        title_buffer = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, title_buffer, 512)
        rect = ctypes.wintypes.RECT()
        client_rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        user32.GetClientRect(hwnd, ctypes.byref(client_rect))
        top_left = ctypes.wintypes.POINT(client_rect.left, client_rect.top)
        bottom_right = ctypes.wintypes.POINT(client_rect.right, client_rect.bottom)
        user32.ClientToScreen(hwnd, ctypes.byref(top_left))
        user32.ClientToScreen(hwnd, ctypes.byref(bottom_right))
        return {
            "hwnd": hwnd,
            "title": title_buffer.value,
            "bounds": {
                "left": rect.left,
                "top": rect.top,
                "right": rect.right,
                "bottom": rect.bottom,
                "width": rect.right - rect.left,
                "height": rect.bottom - rect.top,
            },
            "client_bounds": {
                "left": top_left.x,
                "top": top_left.y,
                "right": bottom_right.x,
                "bottom": bottom_right.y,
                "width": bottom_right.x - top_left.x,
                "height": bottom_right.y - top_left.y,
            },
        }

    def _find_window_by_exact_title(self, title: str) -> Optional[int]:
        if os.name != "nt" or not title:
            return None
        user32 = ctypes.windll.user32
        matches: List[int] = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def callback(hwnd, _):
            if not user32.IsWindowVisible(hwnd):
                return True
            buffer = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, buffer, 512)
            if buffer.value == title:
                matches.append(int(hwnd))
            return True

        user32.EnumWindows(callback, 0)
        return matches[0] if matches else None

    def _focus_window(self, hwnd: int) -> bool:
        if os.name != "nt" or not hwnd:
            return False
        user32 = ctypes.windll.user32
        try:
            SW_SHOW = 5
            SW_RESTORE = 9
            HWND_TOP = 0
            HWND_TOPMOST = -1
            HWND_NOTOPMOST = -2
            SWP_NOSIZE = 0x0001
            SWP_NOMOVE = 0x0002
            ASFW_ANY = -1
            user32.ShowWindow(hwnd, SW_RESTORE)
            user32.ShowWindow(hwnd, SW_SHOW)
            try:
                user32.AllowSetForegroundWindow(ASFW_ANY)
            except Exception:
                pass
            foreground_hwnd = user32.GetForegroundWindow()
            foreground_thread = user32.GetWindowThreadProcessId(foreground_hwnd, None)
            target_thread = user32.GetWindowThreadProcessId(hwnd, None)
            current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
            attached_foreground = False
            attached_target = False
            if foreground_thread and foreground_thread != current_thread:
                attached_foreground = bool(user32.AttachThreadInput(current_thread, foreground_thread, True))
            if target_thread and target_thread != current_thread:
                attached_target = bool(user32.AttachThreadInput(current_thread, target_thread, True))
            try:
                user32.BringWindowToTop(hwnd)
                user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
                user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
                user32.SetWindowPos(hwnd, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
                user32.SetForegroundWindow(hwnd)
                try:
                    user32.SwitchToThisWindow(hwnd, True)
                except Exception:
                    pass
            finally:
                if attached_target:
                    user32.AttachThreadInput(current_thread, target_thread, False)
                if attached_foreground:
                    user32.AttachThreadInput(current_thread, foreground_thread, False)
            time.sleep(0.5)
            return int(user32.GetForegroundWindow()) == int(hwnd)
        except Exception:
            return False

    def _physical_coordinate_space(self, screenshot_size: Tuple[int, int]) -> Dict[str, Any]:
        pyautogui_size = self.get_display_size()
        system_metrics = None
        virtual_metrics = None
        if os.name == "nt":
            user32 = ctypes.windll.user32
            system_metrics = {
                "width": int(user32.GetSystemMetrics(0)),
                "height": int(user32.GetSystemMetrics(1)),
            }
            virtual_metrics = {
                "left": int(user32.GetSystemMetrics(76)),
                "top": int(user32.GetSystemMetrics(77)),
                "width": int(user32.GetSystemMetrics(78)),
                "height": int(user32.GetSystemMetrics(79)),
            }
        screenshot = {"width": int(screenshot_size[0]), "height": int(screenshot_size[1])}
        pyauto = {"width": int(pyautogui_size[0]), "height": int(pyautogui_size[1])}
        verified = screenshot == pyauto
        if system_metrics:
            verified = verified and screenshot == system_metrics
        return {
            "name": "physical_pixels",
            "dpi_awareness": self._dpi_awareness,
            "screenshot_size": screenshot,
            "pyautogui_size": pyauto,
            "system_metrics": system_metrics,
            "virtual_screen_metrics": virtual_metrics,
            "verified_single_space": verified,
        }

    def _ocr_from_image(self, image, lang: str, psm: int) -> Dict[str, Any]:
        native_path = self._native_tesseract_path()
        if native_path:
            try:
                import pytesseract
                from pytesseract import Output

                pytesseract.pytesseract.tesseract_cmd = native_path
                data = pytesseract.image_to_data(image, lang=lang, config=f"--psm {int(psm)}", output_type=Output.DICT)
                words = []
                confidences = []
                for text, conf in zip(data.get("text", []), data.get("conf", [])):
                    token = str(text or "").strip()
                    if not token:
                        continue
                    try:
                        confidence = float(conf)
                    except Exception:
                        confidence = -1.0
                    if confidence >= 0:
                        confidences.append(confidence)
                    words.append({"text": token, "confidence": confidence})
                extracted = " ".join(word["text"] for word in words)
                avg_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0.0
                return {
                    "ok": True,
                    "engine": "native_pytesseract",
                    "binary": native_path,
                    "text": extracted,
                    "normalized_text": self._normalize_ocr_text(extracted),
                    "confidence": avg_confidence,
                    "words": words,
                }
            except Exception as exc:
                native_error = str(exc)
        else:
            native_error = "native_tesseract_not_found"

        with tempfile.NamedTemporaryFile(prefix="orb_ocr_fallback_", suffix=".png", delete=False) as tmp:
            image_path = tmp.name
        image.save(image_path, format="PNG")
        try:
            fallback = self._run_tesseract_tsv_wsl(image_path, lang, psm)
            fallback["native_error"] = native_error
            return fallback
        finally:
            try:
                os.unlink(image_path)
            except Exception:
                pass

    def _run_tesseract_tsv_wsl(self, image_path: str, lang: str, psm: int) -> Dict[str, Any]:
        status = self.ocr_status()
        if not status.success:
            return {"ok": False, "error": status.error or (status.content[0].get("text", "") if status.content else "ocr_status_failed")}
        status_payload = json.loads(status.content[0].get("text", "{}")) if status.content else {}
        tesseract_bin = (((status_payload.get("wsl") or {}).get("binary")) or os.getenv("ORB_WSL_TESSERACT_BIN", "tesseract")).strip()
        command = (
            f"{shlex.quote(tesseract_bin)} {shlex.quote(self._windows_path_to_wsl(image_path))} "
            f"stdout -l {shlex.quote(lang)} --psm {int(psm)} tsv"
        )
        result = subprocess.run(["wsl.exe", "-e", "sh", "-lc", command], capture_output=True, text=True, timeout=45)
        if result.returncode != 0:
            return {"ok": False, "error": result.stderr.strip() or result.stdout.strip()}
        rows = []
        confidences = []
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        if not lines:
            return {"ok": True, "text": "", "normalized_text": "", "confidence": 0.0, "words": []}
        headers = lines[0].split("\t")
        for line in lines[1:]:
            values = line.split("\t")
            row = dict(zip(headers, values))
            text = (row.get("text") or "").strip()
            if not text:
                continue
            try:
                confidence = float(row.get("conf", "-1"))
            except ValueError:
                confidence = -1.0
            if confidence >= 0:
                confidences.append(confidence)
            rows.append({"text": text, "confidence": confidence})
        text = " ".join(row["text"] for row in rows)
        avg_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0.0
        return {
            "ok": True,
            "engine": "wsl_tesseract_tsv",
            "binary": tesseract_bin,
            "text": text,
            "normalized_text": self._normalize_ocr_text(text),
            "confidence": avg_confidence,
            "words": rows,
        }

    def read_desktop_region(self, left: int, top: int, width: int, height: int, lang: str = "eng", psm: int = 6) -> ORBResult:
        try:
            self._require()
            left = int(left)
            top = int(top)
            width = int(width)
            height = int(height)
            if width <= 0 or height <= 0 or width > 2400 or height > 1600:
                return ORBResult.fail("Invalid OCR region dimensions")
            full_image = self._pyautogui.screenshot()
            coordinate_space = self._physical_coordinate_space((full_image.width, full_image.height))
            if left < 0 or top < 0 or left + width > full_image.width or top + height > full_image.height:
                return ORBResult.fail("OCR region is outside the verified physical-pixel screen bounds")
            region = self._pyautogui.screenshot(region=(left, top, width, height)).convert("L")
            lang_safe = "".join(ch for ch in str(lang or "eng") if ch.isalnum() or ch in "_+-") or "eng"
            psm_safe = max(3, min(13, int(psm or 6)))
            ocr = self._ocr_from_image(region, lang_safe, psm_safe)
            payload = {
                "schema": "orb.desktop_region_ocr.v1",
                "read_only_no_click_no_type": True,
                "region": {"left": left, "top": top, "width": width, "height": height, "right": left + width, "bottom": top + height},
                "coordinate_space": coordinate_space,
                "ocr": ocr,
                "actions_performed": [],
            }
            return ORBResult.ok(json.dumps(payload, indent=2))
        except Exception as exc:
            return ORBResult.fail(f"read_desktop_region failed: {exc}")

    def macro_1_verify(
        self,
        expected_text: str = "CALIBRATION TOKEN: OW-7K2-913",
        target_title: str = "ORB MCP TEST PAD — SAFE WINDOW",
        lang: str = "eng",
        psm: int = 6,
    ) -> ORBResult:
        try:
            self._require()
            started_at = datetime.utcnow().isoformat()
            hwnd = self._find_window_by_exact_title(target_title)
            window_found = bool(hwnd)
            foreground_confirmed = self._focus_window(hwnd) if hwnd else False
            window = self._window_info(hwnd) if hwnd else {"hwnd": None, "title": "", "bounds": None, "client_bounds": None}
            full_image = self._pyautogui.screenshot()
            coordinate_space = self._physical_coordinate_space((full_image.width, full_image.height))
            bounds = window.get("bounds") or {}
            crop_box = None
            if window_found and bounds:
                # Fixed Test Pad geometry: canvas width=400, height=100, centered in 600x400 window.
                crop_left = int(bounds["left"] + 100)
                crop_top = int(bounds["top"] + 65)
                crop_width = 400
                crop_height = 100
                crop_box = {
                    "left": crop_left,
                    "top": crop_top,
                    "width": crop_width,
                    "height": crop_height,
                    "right": crop_left + crop_width,
                    "bottom": crop_top + crop_height,
                }
                image = self._pyautogui.screenshot(region=(crop_left, crop_top, crop_width, crop_height))
            else:
                image = full_image
            ocr = self._ocr_from_image(
                image.convert("L"),
                "".join(ch for ch in lang if ch.isalnum() or ch in "_+-") or "eng",
                max(3, min(13, int(psm or 6))),
            )

            normalized_expected = self._normalize_ocr_text(expected_text)
            normalized_window_expected = self._normalize_ocr_text(target_title)
            normalized_window_title = self._normalize_ocr_text(window.get("title", ""))
            normalized_ocr = ocr.get("normalized_text", "") if isinstance(ocr, dict) else ""
            checks = {
                "read_only_no_click_no_type": True,
                "target_window_exact_match": window_found,
                "foreground_confirmed": foreground_confirmed,
                "physical_coordinate_space_verified": bool(coordinate_space.get("verified_single_space")),
                "ocr_engine_ok": bool(ocr.get("ok")) if isinstance(ocr, dict) else False,
                "expected_text_found": True if not normalized_expected else normalized_expected in normalized_ocr,
                "window_title_found": normalized_window_expected == normalized_window_title,
                "hwnd_recorded": bool(window.get("hwnd")),
                "window_bounds_recorded": bool(window.get("bounds")),
                "targeted_crop_recorded": bool(crop_box),
            }
            passed = all(checks.values())
            payload = {
                "schema": "orb.macro_1.read_only_verification.v1",
                "macro": "macro_1",
                "enabled_next_macro": False,
                "target": target_title,
                "started_at": started_at,
                "completed_at": datetime.utcnow().isoformat(),
                "passed": passed,
                "checks": checks,
                "coordinate_space": coordinate_space,
                "window": window,
                "crop_box": crop_box,
                "ocr": ocr,
                "comparison": {
                    "expected_text": expected_text,
                    "normalized_expected_text": normalized_expected,
                    "normalized_ocr_text": normalized_ocr,
                    "target_title": target_title,
                    "normalized_target_title": normalized_window_expected,
                    "normalized_window_title": normalized_window_title,
                },
                "actions_performed": [],
            }
            return ORBResult.ok(json.dumps(payload, indent=2))
        except Exception as exc:
            return ORBResult.fail(f"macro_1_verify failed: {exc}")

    def get_display_size(self) -> Tuple[int, int]:
        try:
            self._require()
            return self._pyautogui.size()
        except Exception:
            return (1920, 1080)

    def snapshot(self, use_vision: bool = True) -> Dict[str, Any]:
        """Full desktop snapshot: screenshot + window list."""
        result: Dict[str, Any] = {}
        shot = self.screenshot()
        if shot.success and len(shot.content) > 1:
            result["screenshot_b64"] = shot.content[1]["data"]

        win_result = self.list_windows()
        if win_result.success and win_result.content:
            import json
            try:
                result["windows"] = json.loads(win_result.content[0]["text"])
            except Exception:
                result["windows"] = []

        size = self.get_display_size()
        result["display"] = {"width": size[0], "height": size[1]}
        return result

    # ── Applications ────────────────────────────────────

    def open_app(self, bundle_id: str) -> ORBResult:
        """Open application. Attempts cross-platform strategies."""
        import platform
        import subprocess
        system = platform.system()
        try:
            if system == "Darwin":
                ret = subprocess.run(
                    ["open", "-b", bundle_id],
                    capture_output=True, timeout=5
                )
                if ret.returncode == 0:
                    return ORBResult.ok(f"Opened app: {bundle_id}")
                return ORBResult.fail(f"macOS open failed: {ret.stderr.decode()}")

            elif system == "Windows":
                import subprocess
                # Windows: use start command or explorer
                subprocess.Popen(["explorer.exe", bundle_id])
                return ORBResult.ok(f"Launched: {bundle_id}")

            elif system == "Linux":
                subprocess.Popen(["xdg-open", bundle_id])
                return ORBResult.ok(f"Opened: {bundle_id}")

            return ORBResult.fail(f"Unsupported platform: {system}")
        except Exception as e:
            return ORBResult.fail(f"open_app failed: {e}")

    def list_windows(self) -> ORBResult:
        """List visible windows. Platform-specific."""
        import platform, json
        system = platform.system()
        try:
            if system == "Darwin":
                import subprocess
                script = """
                tell application "System Events"
                    set winList to {}
                    repeat with proc in (processes where background only is false)
                        set end of winList to name of proc
                    end repeat
                    return winList
                end tell
                """
                ret = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True, text=True, timeout=5
                )
                if ret.returncode == 0:
                    wins = [w.strip() for w in ret.stdout.strip().split(",")]
                    return ORBResult.ok(json.dumps(wins, indent=2))

            elif system == "Windows":
                import ctypes
                wins = []
                def callback(hwnd, _):
                    if ctypes.windll.user32.IsWindowVisible(hwnd):
                        buf = ctypes.create_unicode_buffer(256)
                        ctypes.windll.user32.GetWindowTextW(hwnd, buf, 256)
                        if buf.value:
                            wins.append(buf.value)
                ctypes.windll.user32.EnumWindows(
                    ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)(callback),
                    0
                )
                return ORBResult.ok(json.dumps(wins, indent=2))

        except Exception as e:
            return ORBResult.fail(f"list_windows failed: {e}")

        return ORBResult.ok("[]")

    # ── Clipboard ───────────────────────────────────────

    def read_clipboard(self) -> str:
        try:
            import pyperclip
            return pyperclip.paste()
        except ImportError:
            try:
                import subprocess
                import platform
                if platform.system() == "Darwin":
                    return subprocess.run(
                        ["pbpaste"], capture_output=True, text=True
                    ).stdout
                elif platform.system() == "Windows":
                    return subprocess.run(
                        ["clip"], capture_output=True, text=True
                    ).stdout
            except Exception:
                pass
        return ""

    def write_clipboard(self, text: str) -> None:
        try:
            import pyperclip
            pyperclip.copy(text)
        except ImportError:
            try:
                import subprocess, platform
                if platform.system() == "Darwin":
                    subprocess.run(["pbcopy"], input=text.encode(), check=True)
                elif platform.system() == "Windows":
                    subprocess.run(["clip"], input=text.encode(), check=True)
            except Exception:
                pass

    # ── Utility ─────────────────────────────────────────

    def wait(self, seconds: float) -> None:
        time.sleep(seconds)
