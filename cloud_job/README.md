# Cloud Job Workflow for QCrank Quantum Circuit Execution

This directory contains tools for submitting, retrieving, and analyzing QCrank quantum circuit jobs on various cloud quantum computing platforms (IBM Quantum, IQM, Quantinuum, Q-CTRL Fire Opal).

## Table of Contents
- [Overview](#overview)
- [Workflow](#workflow)
- [Programs](#programs)
  - [Job Submission](#job-submission)
  - [Job Retrieval](#job-retrieval)
  - [Post-Processing](#post-processing)
  - [Visualization](#visualization)
  - [Utilities](#utilities)
- [Directory Structure](#directory-structure)
- [Usage Examples](#usage-examples)
- [Dependencies](#dependencies)

## Overview

The QCrank workflow enables quantum circuit execution and analysis across multiple quantum computing platforms with:
- **Parametric circuit generation** for efficient multi-sample execution
- **Multi-platform support**: IBM Quantum, IQM, Quantinuum, Q-CTRL Fire Opal
- **Automated calibration** using 1M1 (±1 pattern) circuits
- **Error mitigation** via Q-CTRL Fire Opal
- **Comprehensive visualization** and analysis tools

## Workflow

The typical workflow consists of three stages:

```
1. SUBMIT → 2. RETRIEVE → 3. POST-PROCESS & PLOT
```

### Stage 1: Submit Job
Submit parametric quantum circuits to a backend (local simulator or cloud QPU):
- Generate random input data
- Create and transpile parametric circuits
- Submit job to selected backend
- Save metadata and input data to HDF5

### Stage 2: Retrieve Results
Poll and retrieve completed job results:
- Monitor job status
- Download measurement counts
- Decode yields to reconstructed data
- Save results to HDF5

### Stage 3: Post-Process & Visualize
Analyze reconstructed data:
- Apply automatic calibration (optional)
- Compute error metrics (RMSE, correlation)
- Generate visualization plots
- Save processed results

## Programs

### Job Submission

#### `submit_ibmq_job.py`
Submit QCrank circuits to IBM Quantum backends (real hardware or simulators).

**Features:**
- Supports IBM Quantum hardware and fake backends
- Parametric circuit generation with data binding
- Optional Randomized Compilation (RC) and Dynamical Decoupling (DD)
- Automatic transpilation with seed control
- Export circuits as QPY format

**Usage:**
```bash
./submit_ibmq_job.py -E --numQubits 3 2 --numSample 15 --numShot 8000 --backend ibm_brussels
./submit_ibmq_job.py --numQubits 2 2 --numSample 10 --backend fake_cusco  # Local simulation
```

#### `submit_iqm_job.py`
Submit QCrank circuits to IQM cloud quantum computers.

**Supported backends:** `garnet`, `sirius`, `emerald`

**Usage:**
```bash
./submit_iqm_job.py -n 100 -E -i 2 --backend sirius
```

#### `submit_qtuum_job.py`
Submit QCrank circuits to Quantinuum (formerly Honeywell) quantum computers via qnexus API.

**Supported backends:** `H1-1`, `H1-1E` (emulator), `H2-1`, etc.

**Usage:**
```bash
./submit_qtuum_job.py -n 100 -E -i 2 --backend H1-1E
```

#### `submit_qctrl_job.py`
Submit QCrank circuits to IBM Quantum hardware with Q-CTRL Fire Opal error suppression and mitigation.

**Features:**
- Automatic error suppression via optimized compilation
- Hardware error mitigation
- Uses ideal (non-transpiled) circuits - Fire Opal handles transpilation

**Usage:**
```bash
./submit_qctrl_job.py -n 100 -E -i 2 --backend ibm_kingston
```

#### `submit_multXY_job.py`
Submit multi-XY Jacobian measurement circuits for testing quantum gradients.

**Usage:**
```bash
./submit_multXY_job.py -E --numQubits 3 2 --numSample 15 --backend ibm_brussels
```

### Job Retrieval

#### `retrieve_ibmq_job.py`
Retrieve results from IBM Quantum jobs.

**Usage:**
```bash
./retrieve_ibmq_job.py --basePath out --expName brussels_abc123
```

#### `retrieve_iqm_job.py`
Retrieve results from IQM cloud jobs.

**Usage:**
```bash
./retrieve_iqm_job.py --basePath out --expName sirius_abc123
```

#### `retrieve_qtuum_job.py`
Retrieve results from Quantinuum jobs using qnexus API.

**Usage:**
```bash
./retrieve_qtuum_job.py --basePath out --expName emu_abc123
```

#### `retrieve_qctrl_job.py`
Retrieve results from Q-CTRL Fire Opal jobs.

**Usage:**
```bash
./retrieve_qctrl_job.py --basePath out --expName kingstonFO_abc123
```

### Monitoring

#### `status_qctrl.py`
List and monitor Q-CTRL Fire Opal jobs from the last 24 hours.

**Features:**
- Display jobs in formatted table
- Filter by status (SUCCESS, FAILURE, PENDING, etc.)
- Filter by function (execute, iterate, solve_qaoa)
- Show warnings and calibration issues

**Usage:**
```bash
./status_qctrl.py --limit 10
./status_qctrl.py --status SUCCESS --warn  # Show successful jobs with warnings
./status_qctrl.py --function execute --limit 5
./status_qctrl.py --simple  # Use basic activity monitor
```

### Post-Processing

#### `postproc_qcrank.py`
Analyze QCrank experiment results with automatic calibration.

**Features:**
- Automatic amplitude calibration using 1M1 circuits
- Compute error metrics (mean, RMSE, standard error)
- Can disable auto-calibration with `-N` flag

**Usage:**
```bash
./postproc_qcrank.py --basePath out --expName brussels_abc123 -p a -Y
./postproc_qcrank.py --expName sirius_abc123 -p ab -N  # Disable auto-calibration
```

#### `postproc_multXY.py`
Analyze multi-XY Jacobian measurement experiments.

**Usage:**
```bash
./postproc_multXY.py --basePath out --expName brussels_xy123 -p a -Y
```

### Visualization

#### `PlotterQCrankV2.py`
Plotting class for QCrank experiment analysis.

**Features:**
- Correlation plots (ground truth vs reconstructed data)
- Residual distribution histograms
- Error metrics display
- Circuit metadata summary

#### `PlotterMultXY.py`
Plotting class for multi-XY Jacobian experiments.

**Features:**
- Jacobian component visualization
- Error distribution analysis

### Utilities

#### `merge_shots.py`
Merge measurement results from multiple jobs (e.g., to increase shot count).

**Usage:**
```bash
./merge_shots.py --dataPath out/meas --expName job_abc_* --numJobs 3
```

#### `run_qpy_bound.py`
Load and execute quantum circuits from QPY files on fake backends, with visualization.

**Features:**
- Load circuits from QPY files
- Run on AerSimulator, FakeTorino, or FakeCusco
- Built-in QCrank decoder for 1 data qubit
- Auto-scaling calibration
- Correlation and residual plots

**Usage:**
```bash
./run_qpy_bound.py --input out/qcrank_nqa4_nqd1_bound.qpy --nshot 50000 --backendType 0
./run_qpy_bound.py -i out/qcrank_nqa2_nqd2_bound.qpy -n 100000 -b 2  # FakeCusco
```

**Backend types:**
- `0`: AerSimulator (ideal, perfect performance)
- `1`: FakeTorino (medium performance)
- `2`: FakeCusco (poor performance)

### Toolbox

#### `toolbox/Util_H5io4.py`
HDF5 I/O utilities for reading/writing experiment data and metadata.

#### `toolbox/Util_QiskitV2.py`
Qiskit utilities for circuit depth analysis, transpilation metadata, and count packing.

#### `toolbox/Util_IOfunc.py`
General I/O functions including timestamp conversion and date formatting.

#### `toolbox/PlotterBackbone.py`
Base class for all plotters with common matplotlib configuration.

## Directory Structure

```
cloud_job/
├── out/                          # Output directory (created during runs)
│   ├── jobs/                     # Submitted job metadata (*.ibm.h5, *.iqm.h5, etc.)
│   ├── meas/                     # Retrieved measurement results (*.meas.h5)
│   ├── post/                     # Post-processed results (*.h5)
│   └── *.png                     # Generated plots
├── toolbox/                      # Utility modules
│   ├── Util_H5io4.py
│   ├── Util_QiskitV2.py
│   ├── Util_IOfunc.py
│   └── PlotterBackbone.py
├── submit_*.py                   # Job submission scripts
├── retrieve_*.py                 # Job retrieval scripts
├── postproc_*.py                 # Post-processing scripts
├── Plotter*.py                   # Visualization classes
├── merge_shots.py                # Shot merging utility
├── run_qpy_bound.py              # QPY circuit executor
├── status_qctrl.py               # Q-CTRL job monitoring
└── README.md                     # This file
```

## Usage Examples

### Complete Workflow Example (IBM Quantum)

```bash
# 1. Submit job to IBM simulator
./submit_ibmq_job.py -E --numQubits 3 2 --numSample 20 --numShot 10000 \
    --backend fake_cusco --add1M1data

# Output: expName = cusco_abc123

# 2. For real hardware (job submitted to cloud):
./submit_ibmq_job.py -E --numQubits 3 2 --numSample 20 --numShot 10000 \
    --backend ibm_brussels --useRC --useDD --add1M1data

# 3. Retrieve results (for cloud jobs only)
./retrieve_ibmq_job.py --basePath out --expName brussels_abc123

# 4. Post-process and visualize
./postproc_qcrank.py --basePath out --expName brussels_abc123 -p a -Y
```

### Complete Workflow Example (Q-CTRL Fire Opal)

```bash
# 1. Submit job with Fire Opal error mitigation
./submit_qctrl_job.py -E --numQubits 3 2 --numSample 20 --numShot 10000 \
    --backend ibm_kingston --add1M1data

# Output: expName = kingstonFO_xyz789

# 2. Monitor job status
./status_qctrl.py --limit 5 --status PENDING

# 3. Retrieve results (waits for completion)
./retrieve_qctrl_job.py --basePath out --expName kingstonFO_xyz789

# 4. Post-process and visualize
./postproc_qcrank.py --basePath out --expName kingstonFO_xyz789 -p ab -Y
```

### Export and Test Circuits Locally

```bash
# 1. Export circuits as QPY (no execution)
./submit_ibmq_job.py --numQubits 4 1 --numSample 16 --add1M1data -e2

# Output: out/qcrank_nqa4_nqd1_bound.qpy

# 2. Test on local fake backend
./run_qpy_bound.py --input out/qcrank_nqa4_nqd1_bound.qpy \
    --nshot 50000 --backendType 2

# Output: out/qcrank_nqa4_nqd1_bound_b2.png
```

### Merge Multiple Jobs

```bash
# Run same experiment 3 times with different job IDs
./submit_ibmq_job.py ... --expName job_run_1 ...
./submit_ibmq_job.py ... --expName job_run_2 ...
./submit_ibmq_job.py ... --expName job_run_3 ...

# Retrieve all results
./retrieve_ibmq_job.py --expName job_run_1
./retrieve_ibmq_job.py --expName job_run_2
./retrieve_ibmq_job.py --expName job_run_3

# Merge shots for better statistics
./merge_shots.py --dataPath out/meas --expName job_run_* --numJobs 3

# Post-process merged results
./postproc_qcrank.py --expName job_run_1x3 -p a -Y
```

## Dependencies

### Python Packages
- `qiskit` (>=1.2): Quantum circuit framework
- `qiskit-ibm-runtime`: IBM Quantum access
- `qiskit-aer`: Local quantum simulation
- `fireopal`: Q-CTRL Fire Opal error mitigation
- `iqm-qiskit-iqm`: IQM cloud access
- `qnexus`: Quantinuum cloud access (with pytket)
- `numpy`: Numerical operations
- `matplotlib`: Visualization
- `h5py`: HDF5 file I/O

### Environment Variables

**For IBM Quantum:**
```bash
export QISKIT_IBM_TOKEN="your_ibm_token"
export QISKIT_IBM_INSTANCE="your_ibm_instance"
```

**For Q-CTRL Fire Opal:**
```bash
export QCTRL_API_KEY="your_qctrl_api_key"
export QISKIT_IBM_TOKEN="your_ibm_token"
export QISKIT_IBM_INSTANCE="your_ibm_instance"
```

**For IQM:**
- Credentials configured via IQMProvider URL

**For Quantinuum:**
```bash
qnx.login_with_credentials()  # Interactive login
```

### Container Setup
See `../container/` directory for Podman/Docker container configurations with all dependencies pre-installed.

## Key Features

### Parametric Circuits
QCrank uses parametric circuits to efficiently encode multiple data samples in a single batch, reducing compilation overhead and improving throughput.

### Automatic Calibration
The `--add1M1data` flag (or `-A`) appends a calibration circuit with ±1 pattern to automatically correct amplitude scaling errors on real hardware.

### Error Mitigation
Q-CTRL Fire Opal provides:
- Optimized circuit compilation for target hardware
- Measurement error mitigation
- Gate error suppression

### Flexible Backends
- **Local simulators**: Fast testing without cloud access
- **Fake backends**: Realistic noise models based on real hardware
- **Cloud QPUs**: Access to actual quantum hardware

## Notes

- All output files use HDF5 format (`.h5`) for efficient storage of arrays and metadata
- Job metadata includes circuit info, backend details, execution timestamps, and error metrics
- Plots are saved as PNG files in the `out/` directory
- Use `-v` or `--verb` flags to increase verbosity for debugging

## Author
**Jan Balewski**  
Email: janstar1122@gmail.com

For more information about the QCrank algorithm, see `../datacircuits/` and `../examples/`.

