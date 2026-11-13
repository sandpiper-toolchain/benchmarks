import numpy as np
import csv
import os
from typing import Tuple, Union

import matplotlib.pyplot as plt

def sample_normal(mean: float, std_dev: float) -> float:
    """Sample from a normal distribution using NumPy."""
    return np.random.normal(mean, std_dev)

def simulate_compensational_stacking(
    num_steps: int = 500,
    num_cols: int = 400,
    channel_width: float = 20.0,
    element_height: float = 2.0,
    avulsion_mean: float = 12.0,
    avulsion_std_dev: float = 1.0,
    avulsion_strategy: str = 'low',  # Options: 'low', 'random', 'high'
    clip_edges: int = 50,
    clip_bottom: int = 100,
    clip_top: int = 100,
    return_cycle_ids: bool = False,
) -> Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]:
    """
    Simulates 2D compensational stacking of triangular channel elements.

    Parameters:
        num_steps (int): Total number of time steps/elements to deposit.
        num_cols (int): Number of grid points across the basin width.
        channel_width (float): Base width of the triangular channel deposit.
        element_height (float): Apex thickness of each channel deposit.
        avulsion_mean (float): Mean time steps (n) before an avulsion occurs.
        avulsion_std_dev (float): Standard deviation of the avulsion timescale.
        avulsion_strategy (str): 'low' (compensational), 'random', or 'high'.
        clip_edges (int): Number of columns to remove from each edge of the
            domain before returning, to discard boundary reflection artifacts.
        clip_bottom (int): Number of early timestep rows to remove from the
            bottom of the stack before returning, to discard the initial
            spin-up period before the channel has explored the full domain.
        clip_top (int): Number of late timestep rows to remove from the top
            of the stack before returning, symmetric with clip_bottom.
        return_cycle_ids (bool): If True, also return the avulsion cycle ID
            associated with each timestep row.

    Returns:
        If return_cycle_ids is False, returns a 2D elevation array of shape
        (num_steps - clip_bottom - clip_top, num_cols - 2*clip_edges).
        Otherwise, returns the elevation array and a 1D array of cycle IDs.
    """
    # Array to track basin surface elevation over time: shape (num_steps, num_cols)
    elevation_history = np.zeros((num_steps, num_cols), dtype=np.float64)
    cycle_history = np.zeros(num_steps, dtype=np.int64)
    current_elevation = np.zeros(num_cols, dtype=np.float64)
    
    # Grid coordinates along X-axis
    x_coords = np.arange(num_cols, dtype=np.float64)
    half_width = channel_width / 2.0
    
    # Model tracking state
    step_count = 0
    current_cycle = 0
    steps_until_avulsion = max(1, int(round(sample_normal(avulsion_mean, avulsion_std_dev))))
    # center_position = np.random.uniform(0, num_cols)
    center_position = np.random.randint(num_cols)


    direction = 1.0
    
    for t in range(num_steps):
        step_count += 1
        
        # --- Check for Avulsion ---
        if step_count >= steps_until_avulsion:
            step_count = 0
            steps_until_avulsion = max(1, int(round(sample_normal(avulsion_mean, avulsion_std_dev))))
            if t > 0:
                current_cycle += 1
            
            if avulsion_strategy == 'low':
                # Relocate to topographic low
                min_val = np.min(current_elevation)
                min_indices = np.where(np.isclose(current_elevation, min_val, atol=1e-5))[0]
                center_position = int(np.random.choice(min_indices))

                # fig, ax = plt.subplots()
                # ax.plot(elevation_history.T, color="k")
                # ax.plot(current_elevation, color="r")
                # ax.plot(center_position, current_elevation[center_position], 'b*')
                # plt.show()
                
            elif avulsion_strategy == 'high':
                # Relocate to topographic high
                max_val = np.max(current_elevation)
                max_indices = np.where(np.isclose(current_elevation, max_val, atol=1e-5))[0]
                center_position = int(np.random.choice(max_indices))
                
            elif avulsion_strategy == 'random':
                # Relocate anywhere in the domain randomly
                # center_position = np.random.uniform(0, num_cols)
                center_position = np.random.randint(num_cols)
            else:
                raise ValueError("avulsion_strategy must be 'low', 'high', or 'random'")

        else:
            # --- Random Walk Movement ---
            direction = -1 if np.random.rand() < 0.5 else 1
            step_size = 1 # channel_width * np.abs(np.random.normal(0.0, 0.5)) #np.random.uniform(0.05, 0.4)
            center_position += (direction * step_size)

            # Periodic boundary: wrap position around the domain
            center_position = int(center_position % num_cols)

        # --- Deposit Triangular Element ---
        # Compute distances with periodic wrapping
        distances = np.abs(x_coords - center_position)
        distances = np.minimum(distances, num_cols - distances)
        mask = distances <= half_width
        
        # Triangular thickness profile: H * (1 - dist / (W/2))
        thickness = np.zeros(num_cols)
        thickness[mask] = (element_height + np.random.normal(0, 0.1)) * (1.0 - distances[mask] / half_width)

        current_elevation += thickness
        elevation_history[t, :] = current_elevation.copy()
        cycle_history[t] = current_cycle

    # Clip boundary columns to remove edge-reflection artifacts
    if clip_edges > 0:
        elevation_history = elevation_history[:, clip_edges:-clip_edges]

    # Clip early timestep rows to remove spin-up period
    if clip_bottom > 0:
        elevation_history = elevation_history[clip_bottom:, :]
        cycle_history = cycle_history[clip_bottom:]

    # Clip late timestep rows symmetrically
    if clip_top > 0:
        elevation_history = elevation_history[:-clip_top, :]
        cycle_history = cycle_history[:-clip_top]

    if return_cycle_ids:
        return elevation_history, cycle_history
    return elevation_history


# =====================================================================
# Runs & Plotting
# =====================================================================

# mean = 1
RUN_KWARGS = dict(
    num_steps=2000,
    num_cols=40,
    channel_width=2.0,
    element_height=2,
    avulsion_mean=1.0,
    avulsion_std_dev=0.0,
    clip_edges=0,
    clip_bottom=0,
    clip_top=0,
)

np.random.seed(42)
history_comp, cycles_comp = simulate_compensational_stacking(
    **RUN_KWARGS, avulsion_strategy='low', return_cycle_ids=True
)

np.random.seed(42)
history_rand, cycles_rand = simulate_compensational_stacking(
    **RUN_KWARGS, avulsion_strategy='random', return_cycle_ids=True
)

# mean = ?
RUN_KWARGS['avulsion_mean'] = 15

np.random.seed(42)
history_comp_meanX, cycles_comp_meanX = simulate_compensational_stacking(
    **RUN_KWARGS, avulsion_strategy='low', return_cycle_ids=True
)

RUN_KWARGS['avulsion_mean'] = 30

np.random.seed(42)
history_comp_mean2X, cycles_comp_mean2X = simulate_compensational_stacking(
    **RUN_KWARGS, avulsion_strategy='low', return_cycle_ids=True
)

fig, axes = plt.subplots(2, 2, figsize=(5, 7), dpi=120, sharey=True)

plot_data = [
    (history_comp, cycles_comp, 'Compensational  ($T_A=1$)'),
    (history_rand, cycles_rand, 'Random  ($T_A=1$)'),
    (history_comp_meanX, cycles_comp_meanX, 'Compensational  ($T_A=X$)'),
    (history_comp_mean2X, cycles_comp_mean2X, 'Compensational  ($T_A=2X$)'),
]
cycle_cmap = plt.get_cmap('tab10')

for ax, (history, cycle_ids, title) in zip(
    axes.ravel(),
    plot_data,
):
    for step in range(0, history.shape[0], 3):
        ax.plot(
            history[step, :],
            color=cycle_cmap(int(cycle_ids[step]) % cycle_cmap.N),
            linewidth=0.5,
            alpha=0.7,
        )
    ax.set_title(title, fontsize=10)
    ax.set_xlabel('horizontal distance (m)', fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(True, linestyle=':', alpha=0.5)

axes[0,0].set_ylabel('elevation (m)', fontsize=8)
axes[1,0].set_ylabel('elevation (m)', fontsize=8)
plt.tight_layout()
plt.savefig('stacking_comparison.png', dpi=150)
plt.show()

# =====================================================================
# Save CSVs
# =====================================================================
def save_history_csv(history: np.ndarray, path: str) -> None:
    """Save an elevation history array to CSV.

    Rows are timesteps; columns are spatial grid positions.
    The first column is a 'timestep' index; remaining columns are
    named col_0, col_1, ... matching the clipped array width.
    """
    n_cols = history.shape[1]
    header = ['timestep'] + [f'col_{i}' for i in range(n_cols)]
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for t in range(history.shape[0]):
            writer.writerow([t] + list(history[t, :]))
    print(f'Saved {history.shape[0]} rows x {n_cols} cols -> {os.path.basename(path)}')

script_dir = os.path.dirname(os.path.abspath(__file__))
save_history_csv(history_comp, os.path.join(script_dir, 'compensational_stacking.csv'))
save_history_csv(history_rand, os.path.join(script_dir, 'random_stacking.csv'))
save_history_csv(history_comp_meanX, os.path.join(script_dir, 'compensational_stacking_meanX.csv'))
save_history_csv(history_comp_mean2X, os.path.join(script_dir, 'compensational_stacking_mean2X.csv'))
