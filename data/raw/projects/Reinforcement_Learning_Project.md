# Reinforcement Learning Project

## 1. Purpose and scope
This repository is a compact reinforcement learning (RL) sandbox centered on two grid-based environments and multiple tabular control algorithms. It demonstrates how to:

- Define custom environments with Gymnasium-style APIs.
- Formulate each problem as a Markov Decision Process (MDP).
- Train tabular agents using SARSA and n-step Double Q-Learning.
- Tune hyperparameters with Optuna and evaluate greedy policies.
- Visualize agent behavior in grid worlds with static plots and GIFs.

The notebooks are designed for exploration, experimentation, and visualization rather than for packaging as a Python library. All code lives inside Jupyter notebooks.

## 2. Repository layout
Core content is organized as follows:

- [README.md](README.md): High-level overview and setup instructions.
- [RL_environment_Treasure_Hunt.ipynb](RL_environment_Treasure_Hunt.ipynb): Treasure Hunt environment definition with image-based rendering utilities.
- [RL_Grid_World_VIsvualization.ipynb](RL_Grid_World_VIsvualization.ipynb): Grid world visualization and GIF generation for the Treasure Hunt environment.
- [RL_SARSA.ipynb](RL_SARSA.ipynb): SARSA implementation on the Treasure Hunt environment with plots and Optuna tuning.
- [RL_Double_Q_Learning.ipynb](RL_Double_Q_Learning.ipynb): SARSA plus n-step Double Q-Learning on Treasure Hunt, including tuning and evaluation for multiple n values.
- [RL_Warehouse_Robot_Environment.ipynb](RL_Warehouse_Robot_Environment.ipynb): Warehouse robot environment and SARSA agent for pick-up/drop-off tasks.
- [images/](images/): Sprite assets for visual rendering of the grid world.

## 3. Dependencies and runtime
The notebooks rely on standard scientific Python tooling plus Gymnasium and Optuna. Install with:

```bash
pip install gymnasium numpy matplotlib optuna opencv-python pillow
```

Key libraries by usage:

- Gymnasium: environment base class and discrete spaces.
- NumPy: state indexing, Q-table storage, sampling.
- Matplotlib: grid rendering and performance plots.
- Optuna: hyperparameter search.
- OpenCV and Pillow: image preprocessing and GIF generation.

Note: Several notebooks use `%pip install` cells to install dependencies inside the notebook runtime.

## 4. Treasure Hunt environment (5x5 grid)
The Treasure Hunt environment is implemented in multiple notebooks with small variations, but the core MDP structure is consistent.

### 4.1 State, action, and observation design
- Grid size: 5 x 5, giving 25 discrete positions.
- Action space: 4 actions: up, right, down, left.
- Observation space: `Discrete(25)` with the agent position flattened via `np.ravel_multi_index`.
- Observations: the environment returns `agent_pos` plus a flattened grid array representing rewards/agent location.

### 4.2 Transition and termination
- The agent position is updated based on the action, then clipped to grid bounds.
- Episode terminates when the agent reaches the goal or when a max timestep limit is reached.
- Some notebooks allow `max_timesteps = 0` to run until the goal is reached (no truncation).

### 4.3 Reward shaping
Rewards are shaped to encourage reaching the goal and collecting treasures while avoiding traps:

- Goal: +100 (episode terminates).
- Treasure: +20 (collected once in some variants).
- Trap: -20.
- Step penalty: -0.5 (dense shaping for faster convergence).

Treasure collection behavior differs by notebook:

- In [RL_environment_Treasure_Hunt.ipynb](RL_environment_Treasure_Hunt.ipynb), treasures can be removed after collection.
- In [RL_Grid_World_VIsvualization.ipynb](RL_Grid_World_VIsvualization.ipynb), treasures may persist for visualization, with removal handled during rendering.

### 4.4 Rendering and visualization
Rendering is implemented in two styles:

1. Numeric grid rendering (simple `imshow`): a matrix of reward values with the agent highlighted.
2. Image-based rendering (sprite overlays): uses assets in [images/](images/) and places themed sprites for the agent, traps, treasure, and goal. This version can also return a preprocessed image (84 x 84) as a simulated visual observation.

### 4.5 GIF generation
The visualization notebook collects frames and writes an animated GIF to `./treasure_hunt.gif`. This is meant as a qualitative demonstration of the agent trajectory rather than as training input.

## 5. SARSA (on-policy TD control)
SARSA is implemented as a tabular on-policy method in both [RL_SARSA.ipynb](RL_SARSA.ipynb) and [RL_Double_Q_Learning.ipynb](RL_Double_Q_Learning.ipynb).

### 5.1 Update rule
The Q-table update follows the standard SARSA equation:

$$Q(s,a) \leftarrow Q(s,a) + \alpha \left(r + \gamma Q(s',a') - Q(s,a)\right)$$

Where:

- $\alpha$ is the learning rate.
- $\gamma$ is the discount factor.
- $(s,a)$ is the current state-action pair.
- $(s',a')$ is the next state-action pair sampled by the current policy.

### 5.2 Policy and exploration
- Epsilon-greedy policy with decaying $\epsilon$.
- $\epsilon$ decays each episode with a floor (minimum epsilon).

### 5.3 Evaluation
After training:

- Reward-per-episode curves are plotted to show learning progression.
- Epsilon decay curves are plotted to show exploration reduction.
- A greedy evaluation (always choose `argmax Q`) is executed for multiple episodes and visualized.

### 5.4 Hyperparameter tuning
Optuna is used to tune:

- $\gamma$ (discount factor)
- $\epsilon$ decay

The objective is typically the mean reward across the final training window (e.g., last 200 episodes).

## 6. n-step Double Q-Learning
The n-step Double Q-Learning implementation is in [RL_Double_Q_Learning.ipynb](RL_Double_Q_Learning.ipynb). It combines Double Q-Learning with n-step returns to reduce overestimation bias and incorporate longer reward horizons.

### 6.1 Two Q-tables
The algorithm maintains two independent Q-tables:

- $Q_A$ and $Q_B$
- Behavior policy chooses actions based on $Q_A + Q_B$.

### 6.2 n-step return
For each episode, a small buffer of length $n$ is used to compute the n-step return:

$$G = \sum_{i=0}^{n-1} \gamma^i r_{t+i} + \gamma^n \frac{Q_A(s_{t+n}, a_{t+n}) + Q_B(s_{t+n}, a_{t+n})}{2}$$

The update is applied to either $Q_A$ or $Q_B$ at random, which helps reduce maximization bias.

### 6.3 Evaluation across n
The notebook performs manual evaluation across $n = 1$ to $5$, plotting:

- Training reward curves
- Epsilon decay curves
- Greedy policy evaluation curves

### 6.4 Hyperparameter tuning
Optuna is used to tune:

- $\gamma$ (discount factor)
- $\epsilon$ decay

The objective is mean reward over the last segment of training episodes.

## 7. Warehouse Robot environment (6x6 grid)
A separate environment focuses on a pick-up and drop-off task, defined in [RL_Warehouse_Robot_Environment.ipynb](RL_Warehouse_Robot_Environment.ipynb).

### 7.1 State and action space
- Grid size: 6 x 6.
- Action space: 6 actions:
  - Up, down, left, right, pick-up, drop-off.
- Observation space: `Discrete(36)` to represent agent positions, while internal state is stored as a dict keyed by grid coordinates.

### 7.2 Task dynamics
- The agent and goal positions are randomized at reset (ensuring they differ).
- A fixed item starts at a specific location.
- Obstacles block movement and apply penalties.
- The agent must pick up the item and drop it at the goal location.

### 7.3 Reward shaping
- Successful drop-off at goal with item: +100 (terminal).
- First-time pick-up at item location: +25.
- Moving into obstacles: -20 and position is reverted.
- Default step cost: -1.

### 7.4 SARSA agent
A custom SARSA agent class is implemented for the warehouse environment:

- Q-table shape: 36 x 6.
- Epsilon-greedy action selection with decay.
- Trains for a configurable number of episodes and steps.
- Includes a test routine that renders the environment step-by-step.

### 7.5 Hyperparameter tuning
Optuna is used to explore:

- $\gamma$ in a continuous range.
- $\epsilon$ decay.
- $\alpha$ learning rate.

The objective is mean reward over all training episodes.

## 8. Visualization assets
The image-based renderers use the following sprites located in [images/](images/):

- AGENT.png
- AGENT_WITH_GOAL.png
- AGENT_WITH_TRAP.png
- AGENT_WITH_TREASURE.png
- GOAL.png
- TRAP.png
- TREASURE.png

These are used as overlay icons for each grid cell during rendering.

## 9. Outputs and artifacts
The notebooks generate a number of runtime artifacts:

- Reward curves for training and evaluation.
- Epsilon decay curves.
- Optional GIF capture: `treasure_hunt.gif` (generated in the visualization notebook).

No pretrained models, datasets, or serialized Q-tables are saved to disk by default.

## 10. Practical usage notes
- Code execution is nondeterministic because random seeds are not fixed.
- The environment APIs are Gymnasium-like but not fully standard. `step` commonly returns `(agent_pos, reward, terminated, truncated, observation, info)` rather than the canonical `(observation, reward, terminated, truncated, info)`.
- The notebooks duplicate some environment definitions to keep each notebook self-contained.
- For RAG ingestion, consider chunking by notebook and section so that environment definitions and algorithm implementations are discoverable separately.

## 11. How to run
1. Open a notebook listed in section 2.
2. Run the install cell (if present) or install dependencies manually.
3. Execute cells top to bottom to generate plots and artifacts.
4. For GIF generation, run the visualization notebook and call `SAVEGIF()` after rendering frames.

## 12. Summary of "things done" in this project
- Implemented two custom grid-world environments with reward shaping and termination logic.
- Built SARSA agents for both the Treasure Hunt and Warehouse Robot tasks.
- Implemented n-step Double Q-Learning with two Q-tables and n-step returns.
- Added evaluation loops and visualization for greedy policies.
- Tuned hyperparameters with Optuna for SARSA and Double Q-Learning.
- Rendered environments both as numeric heatmaps and as sprite-based grids.
- Generated optional GIFs to visualize agent trajectories.
