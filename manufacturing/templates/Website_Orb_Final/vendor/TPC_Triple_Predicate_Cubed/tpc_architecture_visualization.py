# MOVED: tpc_architecture_visualization.py
#
# Canonical location: tools/visualization/tpc_architecture_visualization.py
# This root copy is a backwards-compatible shim only.
#
# Run directly:
#   python tools/visualization/tpc_architecture_visualization.py
#   python tools/visualization/tpc_architecture_visualization.py --output my.png

from tools.visualization.tpc_architecture_visualization import generate_visualization  # noqa: F401

if __name__ == "__main__":
    import sys
    sys.exit(__import__("subprocess").call([sys.executable,
        "tools/visualization/tpc_architecture_visualization.py"] + sys.argv[1:]))
fig.patch.set_facecolor('#0a0a0a')

# Title
fig.suptitle('TRIPLE PREDICATE CUBED (TPC)\nComplete Architecture Visualization', 
             fontsize=24, fontweight='bold', color='white', y=0.98)

# Create main grid
gs = fig.add_gridspec(4, 2, height_ratios=[1, 1.2, 1, 1], hspace=0.3, wspace=0.3)

# === PANEL 1: The Three Axes ===
ax1 = fig.add_subplot(gs[0, :])
ax1.set_facecolor('#0a0a0a')
ax1.set_xlim(0, 10)
ax1.set_ylim(0, 10)
ax1.axis('off')
ax1.set_title('THE THREE AXES', fontsize=18, fontweight='bold', color='#00d4ff', pad=20)

# Axis 1: Input Trinity
ax1.add_patch(FancyBboxPatch((0.5, 6.5), 2.5, 2.5, boxstyle="round,pad=0.1", 
                             facecolor='#1a1a2e', edgecolor='#00d4ff', linewidth=2))
ax1.text(1.75, 8.5, 'AXIS 1', fontsize=14, fontweight='bold', color='#00d4ff', ha='center')
ax1.text(1.75, 7.8, 'INPUT TRINITY', fontsize=11, color='white', ha='center')
ax1.text(1.75, 7.2, '• ACP: Cochlear Synthesis', fontsize=9, color='#cccccc', ha='center')
ax1.text(1.75, 6.8, '• HLSF: 18D Space Field', fontsize=9, color='#cccccc', ha='center')
ax1.text(1.75, 6.4, '• EGF: Certainty Gravity', fontsize=9, color='#cccccc', ha='center')

# Axis 2: Reasoning Trinity
ax1.add_patch(FancyBboxPatch((3.75, 6.5), 2.5, 2.5, boxstyle="round,pad=0.1", 
                             facecolor='#1a1a2e', edgecolor='#ff6b35', linewidth=2))
ax1.text(5.0, 8.5, 'AXIS 2', fontsize=14, fontweight='bold', color='#ff6b35', ha='center')
ax1.text(5.0, 7.8, 'REASONING TRINITY', fontsize=11, color='white', ha='center')
ax1.text(5.0, 7.2, '• K⁰→K¹→K² Depth Recursion', fontsize=9, color='#cccccc', ha='center')
ax1.text(5.0, 6.8, '• 4 Philosopher ML Loops', fontsize=9, color='#cccccc', ha='center')
ax1.text(5.0, 6.4, '• Phase Coherence Signal', fontsize=9, color='#cccccc', ha='center')

# Axis 3: Resolution Trinity
ax1.add_patch(FancyBboxPatch((7.0, 6.5), 2.5, 2.5, boxstyle="round,pad=0.1", 
                             facecolor='#1a1a2e', edgecolor='#00ff88', linewidth=2))
ax1.text(8.25, 8.5, 'AXIS 3', fontsize=14, fontweight='bold', color='#00ff88', ha='center')
ax1.text(8.25, 7.8, 'RESOLUTION TRINITY', fontsize=11, color='white', ha='center')
ax1.text(8.25, 7.2, '• A Priori Vault', fontsize=9, color='#cccccc', ha='center')
ax1.text(8.25, 6.8, '• A Posteriori Vault', fontsize=9, color='#cccccc', ha='center')
ax1.text(8.25, 6.4, '• ECM Escalation Gate', fontsize=9, color='#cccccc', ha='center')

# Central Cube representation
ax1.add_patch(FancyBboxPatch((3.5, 1.0), 3.0, 4.0, boxstyle="round,pad=0.2", 
                             facecolor='#0f0f23', edgecolor='#ffd700', linewidth=3))
ax1.text(5.0, 4.5, 'TPC CUBE', fontsize=16, fontweight='bold', color='#ffd700', ha='center')
ax1.text(5.0, 3.8, 'Self-Contained Reasoning Unit', fontsize=10, color='#cccccc', ha='center')
ax1.text(5.0, 3.2, '• Input Synthesis', fontsize=9, color='#aaaaaa', ha='center')
ax1.text(5.0, 2.8, '• Philosopher Softmax Loop', fontsize=9, color='#aaaaaa', ha='center')
ax1.text(5.0, 2.4, '• Geometric Glyph Signature', fontsize=9, color='#aaaaaa', ha='center')
ax1.text(5.0, 2.0, '• Vault Retrieval State', fontsize=9, color='#aaaaaa', ha='center')

# Arrows from axes to cube
arrow_style = dict(arrowstyle='->', color='#666666', lw=2)
ax1.annotate('', xy=(4.5, 5.0), xytext=(2.0, 6.5), arrowprops=arrow_style)
ax1.annotate('', xy=(5.0, 5.0), xytext=(5.0, 6.5), arrowprops=arrow_style)
ax1.annotate('', xy=(5.5, 5.0), xytext=(8.0, 6.5), arrowprops=arrow_style)

# === PANEL 2: Philosopher Beam Architecture ===
ax2 = fig.add_subplot(gs[1, 0])
ax2.set_facecolor('#0a0a0a')
ax2.set_xlim(0, 10)
ax2.set_ylim(0, 10)
ax2.axis('off')
ax2.set_title('4-BEAM CONSTRAINT ARCHITECTURE', fontsize=16, fontweight='bold', color='#ff6b35', pad=20)

beams = [
    ("HUME", "Empirical Skepticism", "Constrained Bayesian Graph", "#3498db", 8.5),
    ("KANT", "Categorical Reasoning", "Rule-Based Transition System", "#9b59b6", 6.5),
    ("LOCKE", "Consent & Rights", "Constraint Satisfaction Graph", "#e74c3c", 4.5),
    ("SPINOZA", "Geometric Determinism", "Axiomatic Transition Graph", "#2ecc71", 2.5)
]

for name, role, encoding, color, y in beams:
    ax2.add_patch(FancyBboxPatch((0.5, y-0.8), 9, 1.5, boxstyle="round,pad=0.1", 
                                 facecolor='#1a1a2e', edgecolor=color, linewidth=2))
    ax2.text(1.0, y+0.3, name, fontsize=12, fontweight='bold', color=color, va='center')
    ax2.text(1.0, y-0.1, role, fontsize=10, color='white', va='center')
    ax2.text(1.0, y-0.4, encoding, fontsize=8, color='#888888', va='center', style='italic')
    ax2.text(8.5, y, "25%", fontsize=11, fontweight='bold', color=color, ha='right', va='center')

ax2.text(5.0, 0.5, 'ShadowPropagation: Confidence metrics only (10% influence)', 
         fontsize=9, color='#888888', ha='center', style='italic')

# === PANEL 3: Pipeline Flow ===
ax3 = fig.add_subplot(gs[1, 1])
ax3.set_facecolor('#0a0a0a')
ax3.set_xlim(0, 10)
ax3.set_ylim(0, 10)
ax3.axis('off')
ax3.set_title('FULL PIPELINE', fontsize=16, fontweight='bold', color='#00ff88', pad=20)

stages = [
    ("Input", "ACP Synthesis", 9.0),
    ("HLSF", "Traversal + Vivacity", 8.0),
    ("K⁰→K¹→K²", "Depth Recursion", 7.0),
    ("4 Philosophers", "Simultaneous ML Loops", 6.0),
    ("Phase Check", "Coherence Signal", 5.0),
    ("EGF", "Gravity Retrieval", 4.0),
    ("Vaults", "A Priori + Posteriori", 3.0),
    ("ECM", "Escalation Gate", 2.0),
    ("Output", "Drift Ping Verified", 1.0)
]

for label, desc, y in stages:
    ax3.add_patch(FancyBboxPatch((2.0, y-0.3), 6, 0.6, boxstyle="round,pad=0.05", 
                                 facecolor='#1a1a2e', edgecolor='#00ff88', linewidth=1.5))
    ax3.text(2.3, y, label, fontsize=10, fontweight='bold', color='#00ff88', va='center')
    ax3.text(5.0, y, desc, fontsize=9, color='#cccccc', va='center')
    if y > 1.0:
        ax3.annotate('', xy=(5.0, y-0.4), xytext=(5.0, y+0.4), 
                    arrowprops=dict(arrowstyle='->', color='#444444', lw=1.5))

# === PANEL 4: Geometric Signatures ===
ax4 = fig.add_subplot(gs[2, 0])
ax4.set_facecolor('#0a0a0a')
ax4.set_title('GEOMETRIC GLYPH SIGNATURES', fontsize=16, fontweight='bold', color='#ffd700', pad=20)

# Generate sample glyphs for visualization
np.random.seed(42)
n_samples = 5
glyphs_2d = []
labels = ["Exact Match", "Near Match", "Partial", "Novel", "Orthogonal"]
colors = ['#00ff88', '#88ff00', '#ffff00', '#ff8800', '#ff0000']

for i in range(n_samples):
    coords = np.random.randn(18)
    coords = coords / np.linalg.norm(coords)
    if i == 0:
        coords = coords * 0.1  # Exact - very close
    elif i == 1:
        coords = coords * 0.5  # Near
    elif i == 2:
        coords = coords * 1.2  # Partial
    elif i == 3:
        coords = coords * 2.5  # Novel
    else:
        coords = coords * 5.0  # Orthogonal
    glyphs_2d.append(coords[:2])  # Project to 2D for viz

for i, (point, label, color) in enumerate(zip(glyphs_2d, labels, colors)):
    ax4.scatter(point[0], point[1], c=color, s=200, alpha=0.8, edgecolors='white', linewidth=2)
    ax4.annotate(label, (point[0], point[1]), xytext=(10, 10), textcoords='offset points',
                color='white', fontsize=10, fontweight='bold')

# Origin reference
ax4.scatter([0], [0], c='white', s=100, marker='*', zorder=5)
ax4.annotate('Query Point', (0, 0), xytext=(-40, -30), textcoords='offset points',
            color='#ffd700', fontsize=11, fontweight='bold')

# Concentric circles for distance zones
theta = np.linspace(0, 2*np.pi, 100)
for r, color, alpha in [(0.5, '#00ff88', 0.1), (1.5, '#ffff00', 0.1), (3.0, '#ff8800', 0.1)]:
    ax4.plot(r*np.cos(theta), r*np.sin(theta), color=color, alpha=alpha, linewidth=2)

ax4.set_xlim(-6, 6)
ax4.set_ylim(-6, 6)
ax4.set_aspect('equal')
ax4.grid(True, alpha=0.2, color='#444444')
ax4.set_xlabel('Dimension 1', color='white')
ax4.set_ylabel('Dimension 2', color='white')
ax4.tick_params(colors='white')

# === PANEL 5: Drift Ping Chain ===
ax5 = fig.add_subplot(gs[2, 1])
ax5.set_facecolor('#0a0a0a')
ax5.set_xlim(0, 10)
ax5.set_ylim(0, 10)
ax5.axis('off')
ax5.set_title('DRIFT PING CHAIN', fontsize=16, fontweight='bold', color='#00d4ff', pad=20)

gates = ["ACP", "HLSF", "DEPTH", "PHIL", "PHASE", "EGF", "VAULT", "ECM", "OUT"]
x_positions = np.linspace(1, 9, len(gates))

for i, (x, gate) in enumerate(zip(x_positions, gates)):
    color = '#00ff88' if i < 7 else '#ffff00' if i == 7 else '#ff6b35'
    ax5.add_patch(Circle((x, 5), 0.4, facecolor='#1a1a2e', edgecolor=color, linewidth=2))
    ax5.text(x, 5, str(i+1), fontsize=9, color=color, ha='center', va='center', fontweight='bold')
    ax5.text(x, 4.2, gate, fontsize=8, color='white', ha='center', va='center')
    
    if i < len(gates) - 1:
        ax5.annotate('', xy=(x_positions[i+1]-0.4, 5), xytext=(x+0.4, 5),
                    arrowprops=dict(arrowstyle='->', color='#444444', lw=2))
        # Ping arrow (backward)
        ax5.annotate('', xy=(x+0.2, 5.3), xytext=(x_positions[i+1]-0.2, 5.3),
                    arrowprops=dict(arrowstyle='->', color='#00d4ff', lw=1.5, linestyle='dashed'))

ax5.text(5.0, 6.5, 'Forward Signal →', fontsize=10, color='#666666', ha='center')
ax5.text(5.0, 6.2, '← Backward Ping (Handshake)', fontsize=10, color='#00d4ff', ha='center')
ax5.text(5.0, 3.0, 'Zero Drift: Corrupted signals cannot propagate silently', 
         fontsize=9, color='#888888', ha='center', style='italic')

# === PANEL 6: Performance Comparison ===
ax6 = fig.add_subplot(gs[3, :])
ax6.set_facecolor('#0a0a0a')
ax6.set_title('TPC vs LLM: ARCHITECTURAL DIFFERENTIATION', fontsize=16, fontweight='bold', color='white', pad=20)
ax6.set_xlim(0, 10)
ax6.set_ylim(0, 10)
ax6.axis('off')

# Comparison table
aspects = [
    ("Compute per query", "Maximum every query", "Scaled to complexity (vault-first)", "#ff6b35"),
    ("Ethics grounding", "RLHF post-hoc", "Structurally encoded at root", "#00ff88"),
    ("Core mechanism", "Token prediction", "Pure ML recursion (no tokens)", "#00ff88"),
    ("Probability space", "Flat over vocabulary", "Geometric over reasoning space", "#00ff88"),
    ("Confidence", "RLHF calibration / logits", "Native: distance IS confidence", "#00ff88"),
    ("Memory", "Context window only", "Persistent vaulted priors", "#00ff88"),
    ("Reasoning paths", "Single/ensemble", "4 simultaneous beams + synthesis", "#00ff88"),
]

y_start = 8.5
for i, (aspect, llm, tpc_val, color) in enumerate(aspects):
    y = y_start - i * 1.1
    ax6.text(0.5, y, aspect, fontsize=10, fontweight='bold', color='white', va='center')
    ax6.text(3.5, y, llm, fontsize=9, color='#ff6b35', va='center')
    ax6.text(6.5, y, tpc_val, fontsize=9, color='#00ff88', va='center')
    
    # Separator
    ax6.plot([0.5, 9.5], [y-0.4, y-0.4], color='#333333', linewidth=0.5)

# Headers
ax6.text(3.5, 9.2, "LLMs", fontsize=12, fontweight='bold', color='#ff6b35', ha='center')
ax6.text(6.5, 9.2, "TPC", fontsize=12, fontweight='bold', color='#00ff88', ha='center')
ax6.plot([2.5, 4.5], [9.0, 9.0], color='#ff6b35', linewidth=2)
ax6.plot([5.5, 7.5], [9.0, 9.0], color='#00ff88', linewidth=2)

# Key stats box
ax6.add_patch(FancyBboxPatch((7.5, 0.5), 2.0, 2.0, boxstyle="round,pad=0.1", 
                             facecolor='#1a1a2e', edgecolor='#ffd700', linewidth=2))
ax6.text(8.5, 2.0, 'KEY METRICS', fontsize=11, fontweight='bold', color='#ffd700', ha='center')
ax6.text(8.5, 1.5, '~20% compute', fontsize=10, color='white', ha='center')
ax6.text(8.5, 1.1, 'vs unoptimized', fontsize=8, color='#888888', ha='center')
ax6.text(8.5, 0.7, 'transformer baseline', fontsize=8, color='#888888', ha='center')

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig('/mnt/agents/output/TPC_Architecture_Visualization.png', dpi=150, bbox_inches='tight', 
            facecolor='#0a0a0a', edgecolor='none')
plt.show()
print("Visualization saved to /mnt/agents/output/TPC_Architecture_Visualization.png")
