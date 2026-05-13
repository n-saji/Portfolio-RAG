# Bird Flock Simulation with Spark

## 1. Purpose and Scope

The repository combines multiple Spark-based experiments and one main simulation:

- A 3D bird flock simulation driven by simple behavioral rules (alignment-to-leader, cohesion, separation, and speed limits) with optional Spark parallelization.
- An edit distance benchmark that compares three execution strategies: Spark UDF, Python multiprocessing, and a plain for-loop.
- A PyTorch multi-layer perceptron (MLP) inference benchmark that compares Spark UDF evaluation against a local forward pass.
- Utility scripts for visualization, GIF compression, and a simple performance plot.

The emphasis is on comparing distributed execution (Spark) to non-distributed approaches, and on generating visual artifacts (frames, GIFs) for the flock simulation.

## 2. Repository Structure and Roles of Each File

- README.md
  - High-level description of the flock simulation rules and a rendered GIF reference.
- bird_spark.py
  - Spark-based flock simulation runner. Broadcasts parameters, parallelizes frame computation with Spark, and generates a GIF.
- birds.py
  - Non-Spark flock simulation runner. Same behavioral logic as bird_spark.py but executed in a single process.
- get_gif.py
  - Visualization and media utilities. Renders 3D frames to disk and compresses them into GIF or MP4.
- edit_dist.py
  - Edit distance benchmark: Spark UDF vs multiprocessing vs for-loop.
- MLP.py
  - MLP inference benchmark: Spark UDF vs local PyTorch forward pass.
- graph.py
  - Simple plotting script comparing time for Spark vs non-Spark for the bird simulation.
- simple-wiki-unique-has-end-punct-sentences.csv
  - Dataset of sentences used by edit_dist.py to build sentence pairs.

## 3. Core Simulation Logic (Bird Flocking)

Both bird_spark.py and birds.py implement the same flocking behavior. The Spark version parallelizes frame processing; the non-Spark version performs the same update loop locally.

### 3.1 State Representation

- Positions: a NumPy array of shape (num_birds, 3).
  - Each row is a bird position in 3D space.
  - Bird index 0 is the leader bird.
- Velocities: a NumPy array of shape (num_birds, 3).
  - Initialized to zeros for all birds.

### 3.2 Leader Trajectory

The leader bird follows a parametric figure-eight (infinity) trajectory in 3D:

- angle = lead_bird_speed * t / lead_bird_radius
- x = lead_bird_radius * cos(angle)
- y = lead_bird_radius * sin(angle) * cos(angle)
- z = lead_bird_radius * (1 + 0.5 * sin(angle / 5))

This gives a looping path in the X-Y plane with a slow vertical modulation in Z.

### 3.3 Behavioral Forces for Non-Leader Birds

For each non-leader bird, the total force is the sum of three components:

1) Leader attraction (alignment-to-leader)
- If the leader is farther than 10 units, apply a force toward the leader.
- Force magnitude scales with inverse distance: (positions[0] - bird_position) * (1 / d_lead)

2) Cohesion to nearest neighbor (when too far)
- Identify the nearest neighbor among all birds.
- If distance to nearest neighbor exceeds max_distance, apply a force toward that neighbor.
- Force scales with squared distance: (positions[nearest] - bird_position) * (d_near ** 2)

3) Separation (avoid crowding)
- For neighbors within min_distance, apply repulsive forces away from them.
- Each repulsion term is (bird_position - neighbor) / (dist ** 2)
- The final separation force is normalized by total weight of the close neighbors.

Total force = cohesion_force + separation_force + lead_force

### 3.4 Velocity Constraints

To keep movement stable, each bird velocity is clamped to a speed range:

- If speed < min_speed, scale up to min_speed.
- If speed > max_speed, scale down to max_speed.
- If speed is near zero, return a zero vector to avoid divide-by-zero.

### 3.5 Position Updates

Per frame:

1) Update leader position using the figure-eight trajectory.
2) For each other bird:
   - Compute behavioral forces from current positions.
   - Add forces to velocity.
   - Clamp velocity to the allowed speed range.
   - Update position with velocity * time_step.

### 3.6 Simulation Output

Each frame is appended to a list called simulation as a full copy of the positions array. After the run completes, the simulation list is passed to the visualization utility, which renders the frames and builds a GIF.

## 4. Spark-Based Flock Simulation (bird_spark.py)

bird_spark.py mirrors the logic of birds.py, but attempts to distribute frame computation across Spark.

### 4.1 Execution Flow

- Parse command line argument --num_birds (default 10000).
- Initialize simulation parameters, positions, velocities, and an empty simulation list.
- Create SparkSession.
- Broadcast a dictionary with time_step and positions.
- Create an RDD of frame indices: 0..num_frames-1.
- Map each frame index to process_frame(frame, time_step, positions), then collect results.

### 4.2 process_frame

process_frame performs the same update logic as the non-Spark loop:

- Update the leader position for the given frame.
- Update all other bird positions.
- Append a copy of the positions to the global simulation list.
- Return positions for collection.

### 4.3 Important Technical Notes

- The broadcasted positions are mutated inside process_frame, which means each Spark task begins with the same initial positions but runs independently on its worker. This means frames are not truly sequentially dependent in a distributed manner, but instead each frame computation starts from a similar base. The simulation data is reconstructed from the collected results.
- The overall design demonstrates Spark usage and mapping over frames, but the simulation is not a strict time-series dependency chain when distributed.
- The code measures total runtime and average time per bird (mean_time = total_time / num_birds).

### 4.4 Output Artifacts

- Frame images are saved to ./plot/frame_XXXX.png
- A GIF is generated by create_compressed_gif in get_gif.py
- The generated file name is bird_simulation.gif

## 5. Non-Spark Flock Simulation (birds.py)

birds.py runs the flock simulation entirely on a single process, frame by frame.

### 5.1 Execution Flow

- Initialize parameters (num_birds=1000 by default).
- For each frame:
  - Update leader position.
  - Update all other birds.
  - Record frame timing and append position snapshot to simulation list.
- Compute mean frame time.
- Render frames and generate GIF using get_gif.py.

This script provides a direct performance baseline for comparison with bird_spark.py.

## 6. Visualization and Media Utilities (get_gif.py)

get_gif.py provides reusable functions for rendering the simulation to images and combining them into videos.

### 6.1 visualize_simulation

- Creates a 3D plot with custom background, labels, and axis limits.
- For each frame in the simulation list:
  - Clear the axes.
  - Re-apply axis limits and title.
  - Plot leader bird with a star marker and yellow color.
  - Plot other birds with small, translucent markers.
  - Save the frame as ./plot/frame_XXXX.png

### 6.2 create_compressed_gif

- Loads frames from disk in order (based on frame number).
- Resizes each frame by resize_factor.
- Optionally reduces color palette to 128 colors.
- Saves a compressed GIF with the provided duration and loop settings.

### 6.3 create_mp4_from_images

- Loads frames, resizes them, and writes an MP4 using OpenCV.
- This is available but not used by default in bird_spark.py or birds.py.

## 7. Edit Distance Benchmark (edit_dist.py)

edit_dist.py measures the time to compute edit distances between sentence pairs using:

1) Spark + Pandas UDF
2) Multiprocessing
3) Plain for-loop

### 7.1 Data Preparation

- Reads sentence data from simple-wiki-unique-has-end-punct-sentences.csv
- Truncates to --num_sentences (default 300)
- Builds all pairwise combinations using itertools.combinations

### 7.2 Edit Distance Implementation

- edit_distance(pair) uses dynamic programming to compute Levenshtein distance.
- The DP table is (m+1) x (n+1).
- Base rows/columns handle empty prefix cases.

### 7.3 Spark Execution

- Create SparkSession.
- Create Spark DataFrame from sentence pairs.
- Define a pandas UDF to compute distances for each pair.
- Apply the UDF to create a distances column.

### 7.4 Multiprocessing Execution

- Uses multiprocessing.Pool with cpu_count() workers.
- Uses pool.imap for streaming computation with tqdm progress bar.

### 7.5 Plain Python Execution

- Iterates through all pairs in a for-loop with tqdm.

### 7.6 Output

- Prints time for each method and a summary array: [spark_time, mp_time, loop_time]

## 8. MLP Inference Benchmark (MLP.py)

MLP.py compares a Spark UDF approach to a direct PyTorch forward pass.

### 8.1 Model Architecture

- MLPClassifier is a standard feed-forward network:
  - Linear -> ReLU repeated for each hidden dimension
  - Final Linear layer for class logits
- The forward pass returns predicted class indices (argmax of logits).

### 8.2 Spark UDF Inference

- Generates random input tensor x with shape (n_input, input_dim).
- Converts x to a Spark DataFrame with one feature column per dimension.
- Defines a pandas UDF that stacks row inputs into a tensor and runs inference.
- Adds a prediction column to the Spark DataFrame.

### 8.3 Local Inference

- Runs mlp_model(x) directly.

### 8.4 Output

- Prints time for Spark inference and local inference.
- Prints a combined summary array.

## 9. Performance Plot Script (graph.py)

graph.py is a static plotting script that visualizes time vs number of birds.

- It contains hard-coded arrays for bird counts and execution times.
- Uses Matplotlib with log-scaled Y axis for time.
- Plots Spark vs non-Spark curves.

## 10. Inputs, Outputs, and Artifacts

Inputs:
- simple-wiki-unique-has-end-punct-sentences.csv
- CLI arguments for several scripts (num_birds, num_sentences, etc.)

Outputs:
- PNG frames in ./plot
- bird_simulation.gif
- Console timing logs for each benchmark

## 11. Execution Entry Points and CLI Arguments

bird_spark.py
- --num_birds: number of birds to simulate (default 10000)

birds.py
- No CLI arguments; parameters are defined in code.

edit_dist.py
- --csv_dir: path to CSV file (default simple-wiki-unique-has-end-punct-sentences.csv)
- --num_sentences: number of sentences to use (default 300)

MLP.py
- --n_input: number of input rows (default 10000)
- --hidden_dim: base hidden dimension (default 1024)
- --hidden_layer: multiplier (default 50), used to create one very large hidden layer

