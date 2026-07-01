import time
import sys
import os
import threading
import multiprocessing
import math
import random

# Add the root directory to path to allow imports if running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python_src.acquisition.serial_io import SerialDataAcquisition
from python_src.processing.emg_filter import EMGProcessor
from python_src.processing.imu_filter import IMUProcessor
from python_src.visualization.plot_emg import run_visualizer

class MockSerialDataAcquisition(threading.Thread):
    """Fallback thread to generate simulated data if ESP32 is not connected."""
    def __init__(self, data_queue):
        super().__init__()
        self.data_queue = data_queue
        self.running = False
        self.daemon = True

    def run(self):
        self.running = True
        print("[MockSerial] Generating simulated tremor data...")
        t = 0
        while self.running:
            # Simulate a 5Hz tremor
            tremor = math.sin(2 * math.pi * 5 * t)
            
            # EMG: simulated burst of noise during the tremor
            emg_raw = 2000 + int((abs(tremor) * 1000) + random.randint(-200, 200))
            
            # Accel: simulate physical oscillation
            ax = int(tremor * 4000)
            ay = int(tremor * 2000)
            az = 16384 + random.randint(-100, 100) # 1g on Z axis
            
            parsed_data = {
                'timestamp': int(t * 1000),
                'emg': emg_raw,
                'accel': (ax, ay, az),
                'gyro': (0, 0, 0),
                'mag': (0, 0, 0)
            }
            if not self.data_queue.full():
                self.data_queue.put(parsed_data)
                
            t += 0.05 # 20Hz
            time.sleep(0.05)

    def stop(self):
        self.running = False
        self.join()

def main():
    print("Initializing Active Tremor Cancellation System...")

    # Initialize Queues
    # Use multiprocessing.Queue for the visualizer to cross process boundaries
    data_queue = multiprocessing.Queue(maxsize=100)
    viz_queue = multiprocessing.Queue(maxsize=100)

    # Initialize Processors
    emg_proc = EMGProcessor(fs=20, rms_window=5)
    imu_proc = IMUProcessor(alpha=0.3)

    # Start the Visualization Process
    viz_process = multiprocessing.Process(target=run_visualizer, args=(viz_queue,))
    viz_process.daemon = True
    viz_process.start()

    # Try starting real serial, fallback to mock if failed
    serial_port = '/dev/ttyUSB0' 
    acquisition_thread = SerialDataAcquisition(data_queue, port=serial_port, baud_rate=115200)
    
    try:
        acquisition_thread.start()
        time.sleep(1) # Give it time to try connection
        if not acquisition_thread.running:
            print("Falling back to Mock Serial Generator.")
            acquisition_thread = MockSerialDataAcquisition(data_queue)
            acquisition_thread.start()

        print("Main Loop Started. Processing data...")
        while True:
            # Block until an item is available in the queue
            if not data_queue.empty():
                data = data_queue.get()
                
                # Signal Processing
                emg_filtered, emg_rms = emg_proc.process(data['emg'])
                accel_smooth, gyro_smooth = imu_proc.process(data['accel'], data['gyro'])
                
                # Push to visualizer
                viz_data = {
                    'emg_raw': data['emg'],
                    'emg_rms': emg_rms,
                    'accel_smooth': accel_smooth,
                    'gyro_smooth': gyro_smooth
                }
                
                if not viz_queue.full():
                    viz_queue.put(viz_data)
                
            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\nKeyboard Interrupt received. Shutting down...")
    finally:
        print("\nStopping threads and processes...")
        acquisition_thread.stop()
        if viz_process.is_alive():
            viz_process.terminate()
            viz_process.join()
        print("System shutdown complete.")

if __name__ == "__main__":
    main()
