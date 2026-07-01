import time
import sys
import os
import multiprocessing

# Add the root directory to path to allow imports if running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python_src.acquisition.serial_io import SerialDataAcquisition
from python_src.processing.emg_filter import EMGProcessor
from python_src.processing.imu_filter import IMUProcessor
from python_src.visualization.dashboard import run_dashboard

def main():
    print("Initializing Active Tremor Cancellation System...")

    # Initialize Queues
    data_queue = multiprocessing.Queue(maxsize=100)
    viz_queue = multiprocessing.Queue(maxsize=100)
    command_queue = multiprocessing.Queue()

    # Initialize Processors
    emg_proc = EMGProcessor(fs=20, rms_window=5)
    imu_proc = IMUProcessor(alpha=0.3)

    # Start the Visualization Process
    viz_process = multiprocessing.Process(target=run_dashboard, args=(viz_queue, command_queue))
    viz_process.daemon = True
    viz_process.start()

    acquisition_thread = None
    system_status = "DISCONNECTED"
    
    print("Main Loop Started. Awaiting UI Commands...")

    try:
        while True:
            # If the user closes the dashboard window, the process dies. Exit cleanly.
            if not viz_process.is_alive():
                print("Dashboard closed by user. Exiting main loop...")
                break

            # 1. Check for UI Commands
            if not command_queue.empty():
                cmd = command_queue.get()
                if cmd.get('action') == 'CONNECT':
                    port = cmd.get('port')
                    print(f"UI requested connection to port: {port}")
                    
                    # Stop existing thread if running
                    if acquisition_thread and acquisition_thread.running:
                        acquisition_thread.stop()
                    
                    # Empty the data queue to avoid old junk data
                    while not data_queue.empty():
                        data_queue.get_nowait()
                        
                    # Start new thread
                    acquisition_thread = SerialDataAcquisition(data_queue, port=port, baud_rate=115200)
                    acquisition_thread.start()
                    time.sleep(1) # Give it time to try connection
                    
                    if acquisition_thread.running:
                        system_status = "LIVE"
                        print(f"Successfully connected to {port}!")
                    else:
                        system_status = f"ERROR: Failed to open {port}"
                        print(system_status)
                        
                    # Push status update immediately
                    if not viz_queue.full():
                        viz_queue.put({'status': system_status})

            # 2. Process incoming data if connected
            if system_status == "LIVE" and acquisition_thread and not acquisition_thread.running:
                # Thread crashed or disconnected
                system_status = "ERROR: Disconnected"
                if not viz_queue.full():
                    viz_queue.put({'status': system_status})

            if not data_queue.empty():
                data = data_queue.get()
                
                # Signal Processing
                emg_filtered, emg_rms = emg_proc.process(data['emg'])
                accel_smooth, gyro_smooth, roll, pitch = imu_proc.process(data['accel'], data['gyro'])
                
                # Placeholder for ML and Control Output
                tremor_detected = emg_rms > 2500
                fes_active = tremor_detected
                
                # Push to visualizer
                viz_data = {
                    'status': system_status,
                    'tremor': tremor_detected,
                    'fes': fes_active,
                    'emg_raw': data['emg'],
                    'emg_rms': emg_rms,
                    'accel_smooth': accel_smooth,
                    'gyro_smooth': gyro_smooth,
                    'roll': roll,
                    'pitch': pitch
                }
                
                if not viz_queue.full():
                    viz_queue.put(viz_data)
                
            time.sleep(0.005)

    except KeyboardInterrupt:
        print("\nKeyboard Interrupt received. Shutting down...")
    finally:
        print("\nStopping threads and processes...")
        if acquisition_thread and hasattr(acquisition_thread, 'stop') and acquisition_thread.running:
            acquisition_thread.stop()
        if viz_process.is_alive():
            viz_process.terminate()
            viz_process.join()
        print("System shutdown complete.")

if __name__ == "__main__":
    main()
