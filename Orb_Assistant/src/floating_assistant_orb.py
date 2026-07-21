#!/usr/bin/env python3
"""Electron bridge shim for CALI Orb.
Exposes CALIFloatingOrb for PythonShell usage and supports a simple stdin/stdout
message loop so the Electron bridge can coordinate readiness and queries.
"""

import json
import os
import sys
import time
import threading
import urllib.request
from pathlib import Path

# Fix Windows unicode stdout issues
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
# Add SF-ORB to path for core logic
SF_ORB_PATH = PROJECT_ROOT / "SF-ORB"
if SF_ORB_PATH.exists():
    sys.path.insert(0, str(SF_ORB_PATH))
    print(f"Added SF-ORB to path: {SF_ORB_PATH}", file=sys.stderr)

# Add ACP to path
ACP_PATH = PROJECT_ROOT / "Adaptive_Cochlear_Processor_1.0"
if ACP_PATH.exists():
    sys.path.insert(0, str(ACP_PATH))
    print(f"Added ACP to path: {ACP_PATH}", file=sys.stderr)

# --- ACP Voice Integration ---
ACP_AVAILABLE = False
CoquiBaseline = None

# Try to import speech recognition
try:
    from realtime.mic_capture import MicCapture

    SPEECH_AVAILABLE = True
    print("✓ Speech recognition available", file=sys.stderr)
except ImportError as e:
    print(f"⚠️ Speech recognition import failed: {e}", file=sys.stderr)
    SPEECH_AVAILABLE = False
    MicCapture = None

# Try to import CoquiBaseline
try:
    from coqui_baseline.synthesize import CoquiBaseline

    ACP_AVAILABLE = True
    print("✓ CoquiBaseline imported successfully", file=sys.stderr)
except ImportError as e:
    print(f"⚠️ CoquiBaseline import failed: {e}", file=sys.stderr)
    ACP_AVAILABLE = False

# Debug torch status
try:
    import torch

    print("✓ TORCH IS NOW AVAILABLE", file=sys.stderr)
    print(f"PyTorch version: {torch.__version__}", file=sys.stderr)
except ImportError:
    print("Torch still missing - gravity field disabled", file=sys.stderr)

from Orb_Assistant.src.orb_controller import SF_ORB_Controller  # noqa: E402


class CALIFloatingOrb:
    def __init__(self, project_root):
        stage_client = None
        stage_base_url = os.environ.get("ORB_WEAVER_API_URL", "").strip()
        stage_token = os.environ.get("ORB_WEAVER_CUSTOMER_TOKEN", "").strip()
        if stage_base_url and stage_token:
            from Orb_Assistant.src.orbs_integration import OrbWeaverStageClient

            stage_client = OrbWeaverStageClient.from_orb_weaver(
                stage_base_url,
                token_provider=lambda: os.environ.get("ORB_WEAVER_CUSTOMER_TOKEN", ""),
            )
        self.controller = SF_ORB_Controller(orbs_stage_client=stage_client)
        self.running = False
        self.last_cursor_pos = (0, 0)
        self.last_time = time.time()

        self.voice = None
        if ACP_AVAILABLE:
            try:
                print("Initializing Internal Voice (Coqui XTTS)...", file=sys.stderr)
                # Initialize in CPU-only mode with Cali latents (automatic in my modified CoquiBaseline)
                self.voice = CoquiBaseline()
                print("✓ Voice Online", file=sys.stderr)
            except Exception as e:
                print(f"Voice init failed: {e}", file=sys.stderr)

        self.mic = None
        if SPEECH_AVAILABLE:
            try:
                print("Initializing Speech Recognition...", file=sys.stderr)
                self.mic = MicCapture()
                print("✓ Speech Recognition Online", file=sys.stderr)
            except Exception as e:
                print(f"Speech recognition init failed: {e}", file=sys.stderr)

    def speak(self, text):
        if self.voice:
            try:
                result = self.voice.synthesize(text)
                return result.get("audio_path")
            except Exception as e:
                print(f"Speech error: {e}", file=sys.stderr)
        return None

    def start_speech_recognition(self):
        if self.mic:
            import threading

            self.speech_thread = threading.Thread(target=self._speech_loop)
            self.speech_thread.daemon = True
            self.speech_thread.start()

    def _speech_loop(self):
        import soundfile as sf
        import tempfile
        import os

        while self.running:
            try:
                # Record and process audio chunk
                audio_data = self.mic.record_chunk()

                # Save to temp file since processor expects a file path
                with tempfile.NamedTemporaryFile(
                    suffix=".wav", delete=False
                ) as temp_file:
                    temp_path = temp_file.name
                    sf.write(temp_path, audio_data.flatten(), self.mic.sample_rate)

                try:
                    transcription = self.mic.processor.hear(temp_path)

                    if transcription and transcription.strip():
                        print(f"🎤 Heard: {transcription}", file=sys.stderr)

                        # Check for verbal commands
                        self._process_verbal_command(transcription)

                        # Process the speech input like a text query
                        stimulus = {
                            "type": "speech_query",
                            "content": transcription,
                            "coordinates": [0, 0],
                            "velocity": 0.0,
                        }

                        thought = self.controller.cognitively_emerge(stimulus)
                        if thought:
                            pulse = (
                                thought.pulse()
                                if hasattr(thought, "pulse")
                                else thought
                            )

                            # Send cognitive pulse to Electron
                            response = {
                                "type": "speech_pulse",
                                "data": pulse,
                                "transcription": transcription,
                            }
                            print(json.dumps(response), flush=True)
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)

            except Exception as e:
                print(f"Speech processing error: {e}", file=sys.stderr)
                time.sleep(1)

    def _process_verbal_command(self, transcription):
        """Process verbal commands starting with 'CALI'"""
        if not transcription.lower().startswith("cali"):
            return

        command = transcription.lower()[5:].strip()

        if "slow down" in command:
            # Adjust animation speed (send to Electron)
            response = {"type": "verbal_command", "command": "slow_down"}
            print(json.dumps(response), flush=True)
            if self.voice:
                self.speak("Slowing down")

        elif "speed up" in command:
            response = {"type": "verbal_command", "command": "speed_up"}
            print(json.dumps(response), flush=True)
            if self.voice:
                self.speak("Speeding up")

        elif "change color" in command:
            # Extract color if specified
            if "blue" in command:
                color = "#00ff88"
            elif "red" in command:
                color = "#ff4444"
            elif "green" in command:
                color = "#44ff44"
            else:
                color = "#00ff88"  # default glassy blue-green

            response = {
                "type": "verbal_command",
                "command": "change_color",
                "color": color,
            }
            print(json.dumps(response), flush=True)
            if self.voice:
                self.speak("Changing color")

        elif "increase size" in command:
            response = {"type": "verbal_command", "command": "increase_size"}
            print(json.dumps(response), flush=True)
            if self.voice:
                self.speak("Increasing size")

        elif "decrease size" in command:
            response = {"type": "verbal_command", "command": "decrease_size"}
            print(json.dumps(response), flush=True)
            if self.voice:
                self.speak("Decreasing size")

    def stop(self):
        self.running = False
        if hasattr(self, "cognitive_thread"):
            self.cognitive_thread.join(timeout=1)
        if hasattr(self, "speech_thread"):
            self.speech_thread.join(timeout=1)

    def process_cursor_movement(self, x, y):
        current_time = time.time()
        dx = x - self.last_cursor_pos[0]
        dy = y - self.last_cursor_pos[1]
        dt = current_time - self.last_time
        velocity = ((dx**2 + dy**2) ** 0.5) / max(dt, 0.001) if dt > 0 else 0

        self.last_cursor_pos = (x, y)
        self.last_time = current_time

        stimulus = {
            "type": "cursor_movement",
            "coordinates": [x, y],
            "velocity": min(velocity, 50.0),
            "intent": "navigation",
        }

        thought = self.controller.cognitively_emerge(stimulus)
        if thought:
            if hasattr(thought, "pulse"):
                pulse = thought.pulse()
            else:
                # Lightning bypass returns dict directly
                pulse = thought
            # Send cognitive pulse to Electron
            response = {"type": "cognitive_pulse", "data": pulse}
            print(json.dumps(response), flush=True)
            return pulse
        return None

    def _cognitive_loop(self):
        while self.running:
            # Periodic cognitive processing if needed
            time.sleep(0.1)

    def start(self):
        self.running = True
        # Start background cognitive processing
        self.cognitive_thread = threading.Thread(target=self._cognitive_loop)
        self.cognitive_thread.daemon = True
        self.cognitive_thread.start()

        # Start speech recognition
        self.start_speech_recognition()

    def get_status(self):
        return {
            "running": self.running,
            "controller_status": "active" if self.controller else "inactive",
        }


__all__ = ["CALIFloatingOrb"]


def _main() -> None:
    """Run Orb and respond to simple IPC messages over stdin/stdout (JSON lines)."""
    orb = CALIFloatingOrb(PROJECT_ROOT)
    orb.start()

    # Check UCM status
    try:
        with urllib.request.urlopen(
            "http://localhost:5050/orb/status", timeout=5
        ) as response:
            data = json.loads(response.read().decode())
            if data.get("status") == "active":
                print("UCM status active", file=sys.stderr)
            else:
                print("UCM status not active", file=sys.stderr)
    except Exception as e:
        print(f"UCM status check failed: {e}", file=sys.stderr)

    # Signal readiness to Electron bridge
    print(json.dumps({"type": "ready"}), flush=True)

    for line in sys.stdin:
        try:
            msg = json.loads(line.strip())
        except Exception:
            continue

        msg_type = msg.get("type")

        if msg_type == "shutdown":
            orb.stop()
            print(json.dumps({"type": "shutdown_ack"}), flush=True)
            break

        elif msg_type == "cursor_move":
            x = msg.get("x", 0)
            y = msg.get("y", 0)
            orb.process_cursor_movement(x, y)

        elif msg_type == "get_status":
            status = orb.get_status()
            response = {"type": "status_response", "data": status}
            print(json.dumps(response), flush=True)

        elif msg_type == "query":
            text = msg.get("text", "")
            # Use SF-ORB cognitive processing
            stimulus = {
                "type": "text_query",
                "content": text,
                "coordinates": [0, 0],  # dummy
                "velocity": 0.0,
            }
            result = orb.controller.cognitively_emerge(stimulus)

            # Synthesize response
            response_text = f"Analyzed: {text}"
            audio_path = None
            if orb.voice:
                audio_path = orb.speak(response_text)

            response = {
                "type": "query_result",
                "data": {
                    "echo": text,
                    "response_text": response_text,
                    "audio_path": audio_path,
                    "cognitive_result": (
                        result.pulse() if hasattr(result, "pulse") else result
                    ),
                    "state": orb.get_status(),
                },
            }
            print(json.dumps(response), flush=True)


if __name__ == "__main__":
    _main()
