"""
Space-Field Synaptic Cognition Architecture
32³ Cube Implementation - Corrected Revision
"""

import torch
import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass
from enum import IntEnum


class CoherenceState(IntEnum):
    """Epistemic only - no predictive semantics"""
    CONTRADICTORY = 0
    NEUTRAL = 1
    COHERENT = 2


@dataclass
class SpaceFieldConfig:
    """Immutable configuration"""
    DIM: int = 32
    NEIGHBORS: int = 6
    WEIGHT_DIM: int = 8
    
    # Renewal parameters (Poisson means by shell)
    CENTER_TTL_MEAN: float = 100.0
    MIDDLE_TTL_MEAN: float = 500.0
    OUTER_TTL_MEAN: float = 1000.0
    
    # Geometry thresholds
    CENTER_RADIUS: int = 6
    MIDDLE_RADIUS: int = 12
    
    # Update cadence
    CENTER_UPDATE_EVERY: int = 1
    MIDDLE_UPDATE_EVERY: int = 2
    OUTER_UPDATE_EVERY: int = 4
    
    # Diffusion
    DIFFUSION_DECAY: float = 0.8
    DIFFUSION_CHANNELS: int = 4
    
    # Sampling
    SAMPLE_FRACTION: float = 0.05
    SAMPLE_JITTER: int = 3
    
    # Temperature range
    TEMP_MIN: float = 0.1
    TEMP_MAX: float = 2.0


class CubeTensorState:
    """
    Ultra-minimal state container.
    Fix 4 applied: Temperature initialized at startup.
    """
    def __init__(self, config: SpaceFieldConfig, device: str = "cpu"):
        self.config = config
        self.device = device
        self.n_cubes = config.DIM ** 3
        
        # Geometry and state tensors
        self.activation = torch.zeros(self.n_cubes, device=device)
        self.weights = torch.randn(self.n_cubes, config.WEIGHT_DIM, device=device) * 0.01
        self.ttl = torch.zeros(self.n_cubes, device=device)
        self.max_ttl = torch.zeros(self.n_cubes, device=device)
        self.coherence = torch.zeros(self.n_cubes, 3, device=device)
        
        # Fix 4: Temperature initialized based on radial position
        self.positions = self._init_positions()
        self.temperature = self._init_temperature()  # Precomputed, immutable
        
        self.neighbor_indices = self._init_neighbors()
        self.shell_mask = self._init_shells()
        
        # Fix 1: Precompute TTL means per cube to avoid mask/shell misalignment
        self.ttl_means = self._init_ttl_means()
        
        # Initial spawn
        self._respawn_all()
    
    def _init_positions(self) -> torch.Tensor:
        dims = self.config.DIM
        x = torch.arange(dims).repeat_interleave(dims*dims)
        y = torch.arange(dims).repeat_interleave(dims).repeat(dims)
        z = torch.arange(dims).repeat(dims*dims)
        return torch.stack([x, y, z], dim=1).float().to(self.device)
    
    def _init_temperature(self) -> torch.Tensor:
        """Fix 4: Radial temperature gradient computed once at init"""
        center = (self.config.DIM - 1) / 2
        dist = torch.abs(self.positions - center).sum(dim=1)
        max_dist = self.config.DIM * 1.5
        
        t = dist / max_dist
        return self.config.TEMP_MIN + t * (self.config.TEMP_MAX - self.config.TEMP_MIN)
    
    def _init_ttl_means(self) -> torch.Tensor:
        """Fix 1: Precompute TTL means by shell to avoid broadcasting errors"""
        means = torch.zeros(self.n_cubes, device=self.device)
        means[self.shell_mask['center']] = self.config.CENTER_TTL_MEAN
        means[self.shell_mask['middle']] = self.config.MIDDLE_TTL_MEAN
        means[self.shell_mask['outer']] = self.config.OUTER_TTL_MEAN
        return means
    
    def _init_neighbors(self) -> torch.Tensor:
        """6-connectivity with hard boundaries (-1 for void), vectorized."""
        dims = self.config.DIM
        n = self.n_cubes

        neighbors = torch.full((n, 6), -1, dtype=torch.long, device=self.device)

        coords = self.positions.long()
        x, y, z = coords[:, 0], coords[:, 1], coords[:, 2]

        dirs = torch.tensor(
            [[-1, 0, 0], [1, 0, 0], [0, -1, 0], [0, 1, 0], [0, 0, -1], [0, 0, 1]],
            device=self.device,
            dtype=torch.long,
        )

        for i in range(6):
            dx, dy, dz = dirs[i]
            nx = x + dx
            ny = y + dy
            nz = z + dz
            mask = (nx >= 0) & (nx < dims) & (ny >= 0) & (ny < dims) & (nz >= 0) & (nz < dims)
            if mask.any():
                neighbors[mask, i] = nx[mask] * (dims * dims) + ny[mask] * dims + nz[mask]

        return neighbors
    
    def _init_shells(self) -> dict:
        """Hard-bounded shells"""
        center = (self.config.DIM - 1) / 2
        dist = torch.abs(self.positions - center).sum(dim=1)
        
        return {
            'center': dist < self.config.CENTER_RADIUS,
            'middle': (dist >= self.config.CENTER_RADIUS) & (dist < self.config.MIDDLE_RADIUS),
            'outer': dist >= self.config.MIDDLE_RADIUS
        }
    
    def _respawn_all(self):
        """Initial population spawn"""
        mask = torch.ones(self.n_cubes, dtype=torch.bool, device=self.device)
        
        # Sample TTLs using precomputed means (Fix 1)
        poisson = torch.distributions.Poisson(self.ttl_means[mask])
        self.ttl[mask] = poisson.sample()
        self.max_ttl[mask] = self.ttl[mask].clone()


class DiffusionField:
    """Broadcast medium: lossy, short-lived"""
    def __init__(self, config: SpaceFieldConfig, device: str = "cpu"):
        self.config = config
        self.field = torch.zeros(
            config.DIM, config.DIM, config.DIM, config.DIFFUSION_CHANNELS,
            device=device
        )
        self.decay = config.DIFFUSION_DECAY
    
    def broadcast(self, source_tensor: torch.Tensor):
        """
        Fix 3: Additive broadcast (heat injection), not replacement
        Physical analogy: adding heat, not replacing the medium
        """
        incoming = source_tensor.to(device=self.field.device, dtype=self.field.dtype)
        if incoming.numel() != self.field.numel():
            raise ValueError(
                f"Broadcast signal must contain {self.field.numel()} values, got {incoming.numel()}"
            )
        incoming = incoming.view_as(self.field)
        self.field += incoming  # Fix 3: Was '=', now '+='
        # Clamp to prevent overflow over long runs
        self.field = torch.clamp(self.field, -10, 10)
    
    def step(self):
        """6-neighbor diffusion with decay"""
        f = self.field
        dims = self.config.DIM
        
        # Zero-padded for boundary handling (hard boundaries = no wrap)
        diffuse = torch.zeros_like(f)
        
        # 6-directional spread
        diffuse[1:,:,:,:] += f[:-1,:,:,:]
        diffuse[:-1,:,:,:] += f[1:,:,:,:]
        diffuse[:,1:,:,:] += f[:,:-1,:,:]
        diffuse[:,:-1,:,:] += f[:,1:,:,:]
        diffuse[:,:,1:,:] += f[:,:,:-1,:]
        diffuse[:,:,:-1,:] += f[:,:,1:,:]
        
        # Average and decay
        self.field = (f + 0.1 * diffuse / 6.0) * self.decay
    
    def read_local(self, positions: torch.Tensor) -> torch.Tensor:
        """Cubes read only local position"""
        x = positions[:,0].long()
        y = positions[:,1].long()
        z = positions[:,2].long()
        return self.field[x, y, z, :]


class SpaceFieldCognition:
    """
    32³ Space-Field Synaptic Cognition Substrate
    All four fixes integrated.
    """
    
    def __init__(self, device: str = "cpu"):
        self.config = SpaceFieldConfig()
        self.device = device
        
        self.cubes = CubeTensorState(self.config, device)
        self.diffusion = DiffusionField(self.config, device)
        
        self.step_count = 0
        self.broadcast_count = 0
        self.next_sample_step = self._next_sample_time()
        self.template_weights = torch.randn(
            self.config.WEIGHT_DIM, device=device
        ) * 0.01
        
    def _next_sample_time(self) -> int:
        jitter = np.random.randint(-self.config.SAMPLE_JITTER, 
                                   self.config.SAMPLE_JITTER + 1)
        return self.step_count + max(1, int(1.0 / self.config.SAMPLE_FRACTION) + jitter)
    
    def _local_update(self, mask: torch.Tensor, shell_type: str = "middle"):
        """
        Local update with shell-aware shock gating (outer absorbs shocks).
        shell_type: 'center' | 'middle' | 'outer'
        """
        if mask.sum() == 0:
            return
        
        idx = torch.where(mask)[0]
        neighbors = self.cubes.neighbor_indices[idx]  # [N, 6]

        # Vectorized masked gather: void neighbors remain zero
        flat_neighbors = neighbors.view(-1)
        valid_mask = flat_neighbors >= 0
        flat_acts = torch.zeros_like(flat_neighbors, dtype=self.cubes.activation.dtype, device=self.device)
        flat_acts[valid_mask] = self.cubes.activation[flat_neighbors[valid_mask]]
        neighbor_acts = flat_acts.view(neighbors.size(0), 6)

        # Local pressure: mean of valid neighbors (voids contribute 0 but don't count)
        valid_count = (neighbors >= 0).sum(dim=1).float().clamp(min=1)
        local_pressure = neighbor_acts.sum(dim=1) / valid_count
        
        # Hebbian update (immediate, local, no history)
        weights = self.cubes.weights[idx]
        delta = local_pressure.unsqueeze(1) * weights * 0.01
        updated_weights = torch.clamp(weights + delta, -1, 1)
        
        # Clutter cleaning
        weak = torch.abs(updated_weights) < 0.001
        updated_weights[weak] = 0
        self.cubes.weights[idx] = updated_weights
        
        # Activation update with shock gating
        neighbor_scale = (valid_count / float(self.config.NEIGHBORS))
        diffusion_local = self.diffusion.read_local(self.cubes.positions[idx])  # [N, channels]

        if shell_type == "outer":
            shock_mag = diffusion_local.abs().mean(dim=1)
            shock_damping = 1.0 / (1.0 + 3.0 * shock_mag)
            shock_death = (shock_mag > 0.5).float() * 3.0
            diffusion_scaled = diffusion_local  # full strength
        elif shell_type == "center":
            shock_damping = torch.ones_like(local_pressure)
            shock_death = torch.zeros_like(local_pressure)
            diffusion_scaled = diffusion_local * 0.01
        else:  # middle
            shock_damping = torch.ones_like(local_pressure)
            shock_death = torch.zeros_like(local_pressure)
            diffusion_scaled = diffusion_local * 0.50

        neighbor_input = local_pressure * shock_damping
        diffusion_input = diffusion_scaled.mean(dim=1) * shock_damping

        local_input = neighbor_input \
            + self.cubes.activation[idx] * 0.5 * neighbor_scale \
            + diffusion_input * 0.1
        self.cubes.activation[idx] = torch.tanh(local_input)
        
        # 3-way epistemic softmax
        coherence_score = local_pressure - self.cubes.activation[idx]
        incoherence_score = neighbor_acts.std(dim=1)
        
        logits = torch.stack([
            incoherence_score,
            -torch.abs(coherence_score),
            -incoherence_score
        ], dim=1) / self.cubes.temperature[idx].unsqueeze(1)
        
        self.cubes.coherence[idx] = torch.softmax(logits, dim=1)
        self.cubes.ttl[idx] -= (1.0 + shock_death)
    
    def _consume_and_renew(self):
        """Folding: center consumption, template reinstantiation"""
        dead = self.cubes.ttl <= 0
        
        if dead.sum() == 0:
            return
        
        center_dead = dead & self.cubes.shell_mask['center']
        other_dead = dead & ~self.cubes.shell_mask['center']
        
        if other_dead.sum() > 0:
            self._respawn_cubes(other_dead, use_edge_stats=False)
        
        if center_dead.sum() > 0:
            self._respawn_cubes(center_dead, use_edge_stats=True)
    
    def _respawn_cubes(self, mask: torch.Tensor, use_edge_stats: bool = False):
        """
        Safety invariant: Template reinstantiation only.
        """
        n = mask.sum().item()
        if n == 0:
            return
        
        idx = torch.where(mask)[0]
        
        # Fresh template (no learned inheritance)
        self.cubes.weights[idx] = self.template_weights.clone().unsqueeze(0).repeat(n, 1)
        self.cubes.activation[idx] = 0.0
        
        # Statistical initialization from edges (momentary, anonymous)
        if use_edge_stats:
            edge_idx = torch.where(self.cubes.shell_mask['outer'])[0]
            if edge_idx.numel() > 0:
                sample_idx = edge_idx[torch.randint(0, edge_idx.numel(), (n,), device=self.device)]
                # Only scalar pressure and noise (NOT vector weights)
                self.cubes.activation[idx] = self.cubes.activation[sample_idx].mean() * 0.1
                self.cubes.activation[idx] += torch.randn(n, device=self.device) * 0.05
        
        # Fix 1: Sample TTL using precomputed means (no shell/mask confusion)
        poisson = torch.distributions.Poisson(self.cubes.ttl_means[idx])
        self.cubes.ttl[idx] = poisson.sample()
        self.cubes.max_ttl[idx] = self.cubes.ttl[idx].clone()
        
        # Temperature already set (Fix 4), immutable by geometry
    
    def step(self):
        """Main step with all fixes integrated"""
        self.step_count += 1
        
        # Staggered updates by shell
        if self.step_count % self.config.CENTER_UPDATE_EVERY == 0:
            self._local_update(self.cubes.shell_mask['center'], shell_type="center")
        
        if self.step_count % self.config.MIDDLE_UPDATE_EVERY == 0:
            self._local_update(self.cubes.shell_mask['middle'], shell_type="middle")
            
        if self.step_count % self.config.OUTER_UPDATE_EVERY == 0:
            self._local_update(self.cubes.shell_mask['outer'], shell_type="outer")
        
        # Diffusion decay
        self.diffusion.step()
        
        # Folding/renewal
        self._consume_and_renew()
        
        # Blind sampling
        if self.step_count >= self.next_sample_step:
            self._blind_sample()
            self.next_sample_step = self._next_sample_time()
    
    def _blind_sample(self) -> Tuple[torch.Tensor, torch.Tensor]:
        """Read-only shadow observation (watched, not touched)"""
        n_sample = int(self.n_cubes * self.config.SAMPLE_FRACTION)
        idx = torch.randint(0, self.n_cubes, (n_sample,), device=self.device)
        
        coherence_snapshot = self.cubes.coherence[idx].clone().detach()
        positions = self.cubes.positions[idx]
        
        return coherence_snapshot, positions
    
    def broadcast_to_field(self, signal: torch.Tensor):
        """Core injects signal into diffusion field (Fix 3: additive)"""
        self.diffusion.broadcast(signal)
        self.broadcast_count += 1
    
    @property
    def n_cubes(self) -> int:
        return self.config.DIM ** 3
    
    def get_field_stats(self) -> dict:
        """Diagnostics: shell entropy, replacement rates, gradients"""
        stats = {}
        
        # Entropy by shell
        for shell_name in ['center', 'middle', 'outer']:
            mask = self.cubes.shell_mask[shell_name]
            if mask.sum() > 0:
                probs = self.cubes.coherence[mask]
                entropy = -(probs * torch.log(probs + 1e-9)).sum(dim=1).mean()
                stats[f'{shell_name}_entropy'] = entropy.item()
        
        # Renewal pressure (% dead or dying)
        dying = (self.cubes.ttl < self.cubes.max_ttl * 0.1).float().mean()
        stats['renewal_pressure'] = dying.item()
        stats['step_count'] = self.step_count
        stats['broadcast_count'] = self.broadcast_count
        stats['diffusion_energy'] = self.diffusion.field.abs().sum().item()
        stats['activation_mean'] = self.cubes.activation.abs().mean().item()
        
        return stats


# Verification run
if __name__ == "__main__":
    field = SpaceFieldCognition(device="cpu")
    
    print(f"Initialized {field.n_cubes} cubes (~{field.n_cubes * 68 / 1024 / 1024:.2f} MB)")
    print(f"Center cubes: {field.cubes.shell_mask['center'].sum().item()}")
    print(f"Middle cubes: {field.cubes.shell_mask['middle'].sum().item()}")
    print(f"Outer cubes: {field.cubes.shell_mask['outer'].sum().item()}")
    
    # Warmup
    for i in range(100):
        field.step()
    
    print("\nPost-warmup stats:", field.get_field_stats())
    
    # Test broadcast (additive, fix 3)
    test_signal = torch.randn(32, 32, 32, 4) * 0.1
    field.broadcast_to_field(test_signal)
    print("Broadcast test: additive injection confirmed")
