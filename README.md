Active Tremor Cancellation System via Sensor Fusion and FES

1. Problem Statement

Involuntary tremors, such as those caused by Essential Tremor or Parkinson's Disease, severely impact the quality of life and daily functioning of patients. Traditional treatments rely heavily on pharmacological interventions (which often have systemic side effects) or invasive surgical procedures like Deep Brain Stimulation (DBS). There is a critical need for a non-invasive, wearable, and adaptive system that can detect involuntary movements in real-time and actively counteract them without suppressing the user's intended, voluntary movements.

2. Proposed Solution

This project introduces a non-invasive, closed-loop neuromodulation system.

Sensor Fusion: It uses an Electromyography (EMG) sensor to read neuromuscular activation and an Inertial Measurement Unit (IMU) to track physical kinematics.

Machine Learning: Filtered data is fed into a trained Machine Learning classifier that runs continuously to differentiate between voluntary movements and involuntary tremor frequencies.

Active Cancellation (FES): Upon detecting a tremor, the system calculates the phase and amplitude of the oscillation. It then sends targeted commands back to a Functional Electrical Stimulation (FES/TENS) module. The FES delivers out-of-phase electrical pulses to antagonist muscles to dampen and biomechanically cancel the tremor in real-time.

3. Reality Check & Key Engineering Challenges

Building a closed-loop human-machine interface is highly complex. You must address the following critical challenges:

Latency (The Phase Problem): If your Python script takes 100ms to read, filter, classify, and send the FES command, the tremor's physical position will have already moved. If the stimulation arrives out-of-phase, you might amplify the tremor instead of canceling it. Your entire system loop must run in under 20-30 milliseconds.

Stimulation Artifact (Sensor Blinding): When the TENS module fires (sending 50V+ pulses into the skin), your sensitive EMG sensor (reading millivolts) will pick up a massive spike. This will blind your classifier. You need software "blanking" (ignoring EMG data for a few milliseconds during stimulation) or hardware isolation.

Electrical Safety: You are attaching sensors and high-voltage stimulators to a human. The Arduino must be electrically isolated from mains power (run entirely on batteries or use medical-grade optoisolators) to prevent dangerous electrical shocks.

Muscle Fatigue: Constant electrical stimulation causes rapid muscle fatigue. The control algorithm must only stimulate exactly when necessary, using the minimum required current.

4. Closed-Loop Data Flow Map

      ┌─────────────────────────────────────────────────────────────────────────────────┐
      │                                                                                 │
      v                                                                         		│
[ PHYSICAL WORLD (Patient) ]                                                    		│
      |                                                                         		│
      ├─> EMG Sensor (Muscle intent) ──┐                                        		│
      |                                v                                        		│
      ├─> IMU Sensor (Movement) ─────> [ ARDUINO (Data Acquisition) ]           		│
                                           |                                   		    │
                                           | (Serial Tx: Raw Data)              		│
                                           v                                    		│
                              [ python/acquisition/serial_io.py ]               		│
                                           |                                    		│
      ┌────────────────────────────────────┴──────────────────────────────┐     		│
      v                                                                   v     		│
[ python/processing/emg_filter.py ]                 [ python/processing/imu_filter.py ] │
      |                                                                   |     		│
      └────────────────────────────────────┬──────────────────────────────┘     		│
                                           | (Synchronized Filtered Data)       		│
      ┌────────────────────────────────────┼──────────────────────────────┐     		│
      v                                    v                              v     		│
[ python/ml_model/inference.py ]     [ python/visualization/ ]    [ python/storage/ ]	│
 (Runs trained model)                 (Plots 2D / 3D data)         (Logs to CSV)		│
      |                                                                         		│
      | (If Tremor == TRUE)                                                     		│
      v                                                                         		│
[ python/control/stim_calculator.py ]                                           		│
 (Calculates phase, intensity, duration for antagonist muscle)                  		│
      |                                                                         		│
      | (Stimulation Command)                                                   		│
      v                                                                         		│
[ python/acquisition/serial_io.py ] (Sends command via Serial Rx)               		│
      |                                                                         		│
      v                                                                         		│
[ ARDUINO (Stimulation Controller) ]                                            		│
      |                                                                         		│
      └─> FES / TENS Module ────────────────────────────────────────────────────────────┘
          (Applies counter-stimulation to the patient)


5. Project Directory Structure

tremor_cancellation_project/
│
├── docs/
│   └── Project Report.pdf        # Project documentation and reports
├── README.md                     # Project documentation
├── requirements.txt              # Python dependencies
│
├── hardware_src/
│   ├── .pio/                     # PlatformIO auto-generated build files
│   ├── .vscode/                  # PlatformIO VSCode configurations
│   ├── .gitignore                # PlatformIO gitignore
│   ├── platformio.ini            # PlatformIO configuration (ESP32)
│   └── closed_loop_firmware.ino  # Reads sensors AND triggers TENS/FES module
│
├── python_src/
│   ├── __init__.py               # Treats directory as a python module
│   ├── main.py                   # System orchestrator
│   │
│   ├── acquisition/
│   │   ├── __init__.py
│   │   └── serial_io.py          # Bi-directional Serial Comm
│   │
│   ├── processing/
│   │   ├── __init__.py
│   │   ├── emg_filter.py         # Bandpass/Notch filters, RMS envelope
│   │   └── imu_filter.py         # Sensor fusion (Madgwick/Kalman)
│   │
│   ├── visualization/
│   │   ├── __init__.py
│   │   ├── dashboard.py          # Real-time scrolling plot and telemetry dashboard
│   │   └── plot_imu.py           # 3D visualization of limb orientation
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   └── data_logger.py        # Background thread saving synchronized data
│   │
│   ├── ml_model/
│   │   ├── __init__.py
│   │   ├── train_model.py        # Offline script for training
│   │   ├── inference.py          # Real-time script predicting tremor presence
│   │   └── saved_models/         # Contains .pkl/.h5 trained weights
│   │
│   └── control/
│       ├── __init__.py
│       └── stim_calculator.py    # Logic determining FES parameters (amplitude/phase)


6. System File Breakdown

Hardware Component

closed_loop_firmware.ino: Dual-purpose firmware. Continuously reads analog EMG and I2C IMU data, packaging it into a fast serial stream. Concurrently listens for incoming serial commands from Python (e.g., <STIM, intensity, duration>) to trigger the electrical stimulation module safely via a relay or DAC.

Core & IO (Python)

main.py: The central orchestrator. Initializes thread-safe queues, loads the trained ML model into memory, and spawns parallel threads for reading, processing, visualization, logging, and inference.

serial_io.py: Handles bi-directional communication. Runs a background thread to read sensor data into a queue, and provides a function to push commands back to the Arduino without blocking the read thread.

Processing & Control

emg_filter.py & imu_filter.py: Cleans the raw data. Removes 50/60Hz powerline noise, extracts the signal envelope, and resolves acceleration/gyro data into physical orientation angles.

inference.py: Extracts features (e.g., peak frequency, amplitude) from a sliding window of recent data (e.g., the last 1.5 seconds) and feeds it into the trained model. Outputs a boolean: Tremor_Detected: True/False.

stim_calculator.py: If a tremor is flagged, this module analyzes the IMU data to find the current phase of the oscillation. It calculates the exact millisecond to trigger the FES module (aiming to contract the antagonist muscle) and passes that command back to serial_io.py.

Visualization & Storage

dashboard.py & plot_imu.py: Consumes data from the processing queues strictly for UI updates. Runs in isolated processes to prevent visual lag from slowing down the safety-critical ML control loop.

data_logger.py: Records raw data, filtered data, ML predictions, and FES stimulation timestamps to a .csv file for post-experiment analysis.
