# Epistemic Gravity Field
### Space-Field Synaptic Cognition Architecture (32³ Cube)

A PyTorch-based simulation of a 32³ voxel cognitive architecture that exhibits **"Epistemic Gravity"**—an emergent property where informational certainty naturally settles at the physical center of the system while high-entropy exploration occurs at the periphery.

## 🧠 Core Concept

The architecture models a "Space-Field" where cognitive processing is distributed across a 3D grid of 32,768 (32³) nodes ("cubes"). The system maintains stability through a dynamic equilibrium of:

*   **Radial Temperature Gradient**: High "temperature" (randomness) in the outer shells encourages exploration; low temperature in the center favors stability.
*   **Differential Update Cadence**: The center updates frequently (high temporal resolution), while the outer shells update slowly (temporal integration).
*   **Epistemic Renewal**: Nodes age and "die" (reset) based on a Time-To-Live (TTL) mechanism, preventing stagnation and ensuring continuous responsiveness.
*   **Coherence States**: Nodes track their epistemic state: *Contradictory*, *Neutral*, or *Coherent*.

This creates a "gravity well" of certainty: new information is tested in the volatile outer shell and, if consistent, propagates inward to the stable core.

## 📂 Project Structure

*   `space_field.py`: Core logic containing `SpaceFieldCognition`, `CubeTensorState`, and the physics engine.
*   `visualize.py`: Real-time visualization tool using Matplotlib to show entropy gradients and activation slices.
*   `stress_test.py`: Validates safety invariants (memory leaks, boundary conditions).
*   `perturb_test.py`: "Breaks" the gravity field by inverting physics parameters and validates that the system self-repairs (attractor dynamics).
*   `distribution_shift_test.py`: Tests the system's resilience to sudden massive shifts in input polarity.

## 🚀 Getting Started

### Requirements
*   Python 3.8+
*   `torch` (PyTorch)
*   `numpy`
*   `matplotlib`

```bash
pip install torch numpy matplotlib
```

### Running the Visualization
To see the system in action, run the visualization script. It displays the entropy gradient (Center vs. Outer) and a cross-section of the activation field.

```bash
python visualize.py
```

### Running Tests

**1. Stress Test**
Checks for memory leaks ("ink injection") and boundary violations ("vacuum boundary").
```bash
python stress_test.py
```

**2. Perturbation Test**
Deliberately inverts the physics (cool outer / hot center) to break the gravity, then restores it to verify the system naturally returns to the attractive state.
```bash
python perturb_test.py
```

**3. Distribution Shift Test**
Validates that the center remains stable even when the broadcast input signal suddenly flips polarity (positive to negative).
```bash
python distribution_shift_test.py
```

## ⚙️ Configuration

The system is configured via `SpaceFieldConfig` in `space_field.py`. Key parameters include:

*   `DIM`: Cube dimension (default 32).
*   `CENTER_radius` / `MIDDLE_radius`: Thresholds defining the varying physics shells.
*   `TEMP_MIN` / `TEMP_MAX`: Temperature gradient bounds.
*   `CENTER_TTL_MEAN`: Renewal rate for the core nodes.
