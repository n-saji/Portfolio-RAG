# Neural Networks 

**Scope**
- Tabular binary classification from a CSV dataset.
- Image classification on grayscale characters (alphabets and digits).
- VGG-13 style CNN for grayscale classification.
- ResNet-34 for the Oxford 102 Flowers dataset.
- Training, evaluation, and optimization experiments across multiple architectures.

**Repository Entry Points (Notebooks)**
- [EDA_NN.ipynb](EDA_NN.ipynb)
- [optimising_nn.ipynb](optimising_nn.ipynb)
- [cnn.ipynb](cnn.ipynb)
- [vgg13.ipynb](vgg13.ipynb)
- [resnet34.ipynb](resnet34.ipynb)

## Data Assets and Inputs

**Tabular Dataset (Binary Classification)**
- Source file: [dataset.csv](dataset.csv).
- Target column: `target` (binary, mapped to float).
- Feature columns: 7 numeric features (some entries are strings and are coerced).
- Preprocessed file: [pre-processed.csv](pre-processed.csv).

**Grayscale Image Dataset (Characters)**
- Expected folder structure: `cnn_dataset/` in ImageFolder format (class subfolders).
- Image preprocessing is handled inside the notebooks.
- Output classes: 36 (26 letters + 10 digits).

**Oxford 102 Flowers Dataset (ResNet-34)**
- Expected files: [imagelabels.mat](imagelabels.mat), [setid.mat](setid.mat), and a `jpg/` directory.
- The dataset is split using indices stored in `setid.mat`.

## Part 1 - EDA and Baseline Fully Connected Network
Notebook: [EDA_NN.ipynb](EDA_NN.ipynb)

### Data Loading and Inspection
- `pandas` loads `dataset.csv` into a DataFrame.
- The notebook inspects shape, schema, NA counts, and descriptive statistics.
- A per-column loop prints unique values to detect non-numeric entries.

### Cleaning and Imputation
- Any string entry (alphabetic tokens) in feature columns is converted to `NaN`.
- All `NaN` values are filled with the column mean.
- `target` is coerced to float to ensure numeric consistency.

### Exploratory Visualization
- Multiple chart types are created for each feature:
  - Histograms (`seaborn.histplot`) for feature distributions.
  - Swarm, box, and violin plots of feature vs target.
- Plots use a manual color palette and simplified axes styling.

### Scaling and Class Balancing
- Features are standardized with `StandardScaler`.
- Target is added back to the scaled features for analysis and plotting.
- Class imbalance is corrected using `RandomOverSampler` from `imblearn`.
- The balanced dataset is saved as [pre-processed.csv](pre-processed.csv).

### Train, Validation, and Test Split
- Splits use `train_test_split` twice:
  - 10% test split.
  - From the remaining, 10% validation.

### Baseline Neural Network Architecture
- Implemented in `torch.nn.Module` as a feedforward network:
  - Input: 7 features.
  - Hidden stack: 256 -> 128 -> 64 -> 32, `ReLU` activations.
  - Dropout of 0.3 applied after the second hidden block.
  - Output: single logit (no sigmoid in the model).
- The loss is `BCEWithLogitsLoss`, consistent with a single-logit binary classifier.

### Training Loop and Evaluation
- Optimizer: `Adam` with `lr=0.01` and `weight_decay=1e-5`.
- Metric: `BinaryAccuracy` from `torchmetrics`.
- 500 epochs of training, with validation each epoch.
- The best validation model is saved as [eda_nn.pt](eda_nn.pt).
- After training, the test set is evaluated:
  - Predictions use `torch.sigmoid` and `round()`.
  - Confusion matrix is computed with `sklearn.metrics.confusion_matrix`.
- Accuracy plots are generated for train, validation, and test accuracy over epochs.

## Part 2 - Optimization Experiments on the Tabular Model
Notebook: [optimising_nn.ipynb](optimising_nn.ipynb)

This notebook builds on the baseline MLP model and systematically explores architectural and training hyperparameters. It also measures training time and compares several stabilization methods.

### Data and Baseline Loading
- Loads [pre-processed.csv](pre-processed.csv).
- Loads the baseline weights from [eda_nn.pt](eda_nn.pt).
- Recreates the baseline architecture with parameterized dropout and activation.

### Hyperparameter Search - Dropout
- Tries dropout rates: 0.1, 0.4, 0.5.
- For each dropout rate:
  - Trains the model for 500 epochs.
  - Tracks train and validation accuracy.
  - Evaluates on the test set.
- Best dropout model is saved as `best_dropout`.

### Hyperparameter Search - Activation
- Tries `ReLU`, `LeakyReLU`, and `Sigmoid` with the best dropout.
- Loads weights from `best_dropout` and fine-tunes.
- Best activation model is saved as `best_activation`.

### Hyperparameter Search - Optimizer
- Compares `Adam`, `SGD`, and `RMSprop` with best dropout and activation.
- Best optimizer model is saved as `base_model`.

### Performance Tuning and Training Strategies
1) **Baseline Comparison**
- Trains the base model without early stopping and records time (`base_time`).

2) **Early Stopping**
- Patience: 15 epochs, min delta: 0.001.
- Saves the best model as `early_stopping_best_model`.
- Compares training time with the baseline.

3) **K-Fold Cross Validation**
- Uses 5 folds on the training set.
- Trains a fresh model per fold using the base weights.
- Saves the final model as `Kfold_model`.

4) **Gradient Accumulation**
- Gradient accumulation steps: 4.
- Saves the best model as `Gradient_Accumulation_model`.

5) **Learning Rate Scheduler**
- Uses `ReduceLROnPlateau` with mode `max`, patience 15, factor 0.1.
- Saves the best model as `LRS_Model`.

### Final Output
- The final optimized weights are saved to [optimising_nn.pt](optimising_nn.pt).
- Intermediate weight files are removed to keep the workspace clean.

## Part 3 - CNN for Grayscale Alphabet and Digit Recognition
Notebook: [cnn.ipynb](cnn.ipynb)

### Dataset and Transformations
- Uses `torchvision.datasets.ImageFolder` with root `cnn_dataset`.
- Transform pipeline:
  - `Grayscale(num_output_channels=1)`
  - `Resize((28, 28))`
  - `ToTensor()`
  - `Normalize((0.5,), (0.5,))`
- Dataset split: 80% train, 10% validation, 10% test.

### CNN Architecture
- Two convolution blocks with max pooling:
  - Conv1: 1 -> 32, kernel 3x3.
  - Conv2: 32 -> 64, kernel 3x3.
  - MaxPool after each conv.
- Dropout:
  - 0.25 after each pool.
  - 0.5 before the final classifier.
- Fully connected:
  - 64 * 7 * 7 -> 128 -> 36.
- Output uses `log_softmax` for multi-class classification.

### Training
- Loss: `CrossEntropyLoss`.
- Optimizer: `Adam` with `lr=0.001` and `weight_decay=1e-5`.
- Epochs: 10.
- Early stopping implemented with patience 5.
- Best weights are intended to be saved as `cnn.pt` (the notebook currently saves to `cn.pt`).

### Evaluation and Diagnostics
- Test accuracy and loss are computed on the held-out set.
- Plots include:
  - Train/validation/test accuracy over epochs.
  - Train/validation/test loss over epochs.
- Confusion matrix heatmap across 36 classes.
- ROC curves per class with AUC.
- Per-class precision, recall, and F1 score, displayed as both plots and printed values.

## Part 4 - VGG-13 for Grayscale Character Dataset
Notebook: [vgg13.ipynb](vgg13.ipynb)

### Data Pipeline
- Uses the same `cnn_dataset` ImageFolder structure.
- Transform pipeline:
  - `Grayscale(num_output_channels=1)`
  - `ToTensor()`
  - `Normalize((0.1758,), (0.3270,))`
- Split ratios are the same: 80% train, 10% validation, 10% test.

### VGG-13 Architecture
- A VGG-13 style network tailored for single-channel input:
  - 5 convolution blocks with 2 conv layers each, followed by pooling.
  - Classifier uses two 4096-unit layers and a final output layer of 36 classes.
- Xavier weight initialization is applied to conv and linear layers.

### Training
- Optimizer: `SGD` with `lr=0.05` and `weight_decay=1e-5`.
- Scheduler: `StepLR` with `step_size=5`, `gamma=0.1`.
- Epochs: 15.
- Saves weights to `nikhil_kiran_assignment2_part4.pt` (not present in the workspace).

### Evaluation
- Tracks train and validation accuracy and loss per epoch.
- Computes weighted precision, recall, and F1.
- Produces:
  - Accuracy and loss curves.
  - Confusion matrix.
  - ROC curves per class.

## Part 5 - ResNet-34 for Oxford Flowers 102
Notebook: [resnet34.ipynb](resnet34.ipynb)

### ResNet-34 Implementation
- Custom `BasicBlock` and `ResNet34` classes.
- Standard ResNet-34 layout with 3, 4, 6, 3 block distribution.
- Output layer configured for 102 classes.

### Dataset Handling
- Custom `FlowerDataset` reads images from `./jpg`.
- Labels and splits are read from [imagelabels.mat](imagelabels.mat) and [setid.mat](setid.mat).
- Train data uses random horizontal flips for augmentation.
- All inputs are resized to 224x224 and normalized to ImageNet stats.

### Training and Validation
- Optimizer: `Adam` with `lr=0.01` and `weight_decay=1e-3`.
- Scheduler: `StepLR(step_size=10, gamma=0.5)`.
- Loss: `CrossEntropyLoss`.
- Best validation model saved as [best_resnet34.pth](best_resnet34.pth).

### Inference
- Loads the best weights.
- Predicts labels for the test set and prints predictions.

## Artifacts Generated in the Workspace

**Model Weights**
- [eda_nn.pt](eda_nn.pt) - Best validation model from the baseline tabular MLP.
- [optimising_nn.pt](optimising_nn.pt) - Final model after optimization experiments.
- [cnn.pt](cnn.pt) - CNN model weights (file exists; notebook uses `cn.pt`).
- [best_resnet34.pth](best_resnet34.pth) - Best ResNet-34 validation checkpoint.

**Preprocessed Data**
- [pre-processed.csv](pre-processed.csv) - Scaled and balanced version of `dataset.csv`.

## Implementation Notes and Observed Issues

These are technical observations from the notebook code and are useful if you plan to re-run or extend the workflows.

- In [cnn.ipynb](cnn.ipynb), the saved filename is `cn.pt` while the repository has [cnn.pt](cnn.pt). If re-running, standardize the filename.
- In [cnn.ipynb](cnn.ipynb), `formatedTime` uses `t` which is not defined. Replace with `totalTime` or `endTime - startTime`.
- In [cnn.ipynb](cnn.ipynb), the ROC section uses `predictions` as the `y_true` binarization and `yTrue` as the `y_score`. This is likely inverted; normally `yTrue` is ground truth and `predictions` or logits are scores.
- In [optimising_nn.ipynb](optimising_nn.ipynb), the cleanup list references `LRS_model` while the saved file is `LRS_Model`.
- In [optimising_nn.ipynb](optimising_nn.ipynb), the scheduler section prints `base_time` instead of `LRS_time`.

## Environment and Libraries

The notebooks rely on the following core libraries:
- `torch`, `torchvision`, `torchmetrics`
- `numpy`, `pandas`, `matplotlib`, `seaborn`
- `scikit-learn`, `imblearn`
- `scipy`, `PIL`

Device selection is dynamic and uses `cuda`, `mps`, or `cpu` depending on availability.

## High-Level Flow

1) Tabular dataset is cleaned, scaled, and balanced.
2) A baseline MLP is trained, evaluated, and saved.
3) The baseline MLP is optimized with dropout, activation, optimizer, and training strategy experiments.
4) A small CNN is built for grayscale characters and evaluated with multi-class metrics.
5) A deeper VGG-13 style model is trained on the same grayscale dataset for improved performance.
6) A ResNet-34 implementation is used for the Oxford 102 Flowers dataset with pretrained-like normalization and a custom loader.

This repository provides a complete progression from exploratory data analysis to multiple neural network architectures, along with practical experimentation on optimization techniques and evaluation metrics.
