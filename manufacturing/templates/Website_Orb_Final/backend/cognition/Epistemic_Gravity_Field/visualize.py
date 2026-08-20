"""
Optional real-time visualization for the 32³ Space-Field.
Shows entropy gradients and a mid-plane activation slice.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import torch

try:
    from .space_field import SpaceFieldCognition
except ImportError:
    from space_field import SpaceFieldCognition


def visualize_entropy_gradients(steps: int = 2000, device: str | None = None, slice_z: int = 16):
    """Run a live matplotlib view of entropy gradients and a 32x32 activation slice."""
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    field = SpaceFieldCognition(device=device)

    # 1. Inject Stimulus (Center Pulse)
    print("Injecting initial stimulus...")
    mid = 32 // 2
    with torch.no_grad():
        # Inject strong pulse into the center to kickstart entropy
        field.cubes.activation.view(32, 32, 32)[mid, mid, mid] = 10.0

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))

    # Entropy over time
    ax_ent = axes[0]
    ax_ent.set_title("Epistemic Entropy by Shell")
    ax_ent.set_xlabel("Step")
    ax_ent.set_ylabel("Entropy")
    center_line, = ax_ent.plot([], [], "r-", label="Center")
    middle_line, = ax_ent.plot([], [], "y-", label="Middle")
    outer_line, = ax_ent.plot([], [], "b-", label="Outer")
    ax_ent.legend()
    ax_ent.grid(True, alpha=0.3)

    # Activation slice
    ax_slice = axes[1]
    ax_slice.set_title(f"Activation Slice z={slice_z}")
    # 3. Fix activation slice visibility (adaptive scaling setup)
    im = ax_slice.imshow(np.zeros((32, 32)), cmap="viridis", interpolation="nearest")
    plt.colorbar(im, ax=ax_slice, fraction=0.046, pad=0.04)

    # Renewal pressure
    ax_pressure = axes[2]
    ax_pressure.set_title("Renewal Pressure")
    ax_pressure.set_xlabel("Step")
    ax_pressure.set_ylabel("Fraction near death")
    pressure_line, = ax_pressure.plot([], [], "g-")
    ax_pressure.set_ylim(0, 1)
    ax_pressure.grid(True, alpha=0.3)

    history = {"steps": [], "center": [], "middle": [], "outer": [], "pressure": []}

    print("Starting visualization...")
    
    def init():
        return [center_line, middle_line, outer_line, im, pressure_line]

    def update(_frame):
        # Advance simulation in small bursts for smoother animation
        for _ in range(5):  # Throttled from 10 to 5 for better dynamics visibility
            field.step()

        stats = field.get_field_stats()
        
        # 2. Make stats failure visible
        if _frame == 0:
            print("[EGF] Raw stats:", stats)
        if not stats:
            print("[EGF] WARNING: get_field_stats() returned empty dict")
        
        # Debug output every 10 frames
        if _frame % 10 == 0:
            print(f"Step {field.step_count}: C={stats.get('center_entropy', 0):.3f} O={stats.get('outer_entropy', 0):.3f}")

        history["steps"].append(field.step_count)
        history["center"].append(stats.get("center_entropy", 0.0))
        history["middle"].append(stats.get("middle_entropy", 0.0))
        history["outer"].append(stats.get("outer_entropy", 0.0))
        history["pressure"].append(stats.get("renewal_pressure", 0.0))

        # Update data with error handling
        try:
            center_line.set_data(history["steps"], history["center"])
            middle_line.set_data(history["steps"], history["middle"])
            outer_line.set_data(history["steps"], history["outer"])
            pressure_line.set_data(history["steps"], history["pressure"])

            if history["steps"]:
                xmax = max(history["steps"])
                ax_ent.set_xlim(0, max(100, xmax))
                ax_pressure.set_xlim(0, max(100, xmax))
                
                # Dynamic Y-limits with padding
                vals = history["center"] + history["outer"]
                if vals:
                    ymin = min(vals) * 0.9
                    ymax = max(vals) * 1.1
                    if ymax > ymin:
                        ax_ent.set_ylim(ymin, ymax)

            activations = field.cubes.activation.view(32, 32, 32)[:, :, slice_z].cpu().numpy()
            im.set_array(activations)

            # 3. Adaptive Scaling for Activation Slice
            vmax = np.max(np.abs(activations))
            if vmax > 0:
                im.set_clim(-vmax, vmax)
        except Exception as e:
            print(f"Plot update error: {e}")

        return [center_line, middle_line, outer_line, im, pressure_line]

    frames = max(1, steps // 10)
    anim = FuncAnimation(fig, update, init_func=init, frames=frames, interval=50, blit=False)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    visualize_entropy_gradients()
