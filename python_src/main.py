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
from python_src.storage.data_logger import DataLogger

def main():
    print("Initializing Active Tremor Cancellation System...")

    # Initialize Queues
    data_queue = multiprocessing.Queue(maxsize=100)
    viz_queue = multiprocessing.Queue(maxsize=100)
    command_queue = multiprocessing.Queue()

    # Initialize Processors
    emg_proc = EMGProcessor(fs=20, rms_window=5)
    imu_proc = IMUProcessor(alpha_smooth=0.3)
    logger = DataLogger(data_dir=os.path.join(os.path.dirname(__file__), "data"))

    # Start the Visualization Process
    viz_process = multiprocessing.Process(target=run_dashboard, args=(viz_queue, command_queue))
    viz_process.daemon = True
    viz_process.start()

    acquisition_thread = None
    system_status = "DISCONNECTED"
    manual_tremor_present = False
    
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
                        
                elif cmd.get('action') == 'START_LOG':
                    user = cmd.get('user', 'unknown')
                    action_name = cmd.get('action_name', 'unknown')
                    duration = cmd.get('duration', 30)
                    save_dir = cmd.get('save_dir', None)
                    logger.start_recording(user, action_name, duration, custom_dir=save_dir)
                    
                elif cmd.get('action') == 'SET_TREMOR':
                    manual_tremor_present = cmd.get('state', False)

            # Check if logger duration has elapsed
            if logger.is_recording and logger.get_remaining_time() <= 0:
                logger.stop_recording()

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
                
                # Push to logger
                if logger.is_recording:
                    logger.log_data({
                        'emg': data['emg'],
                        'emg_filtered': emg_filtered,
                        'emg_rms': emg_rms,
                        'accel': data['accel'],
                        'accel_smooth': accel_smooth,
                        'gyro': data['gyro'],
                        'gyro_smooth': gyro_smooth,
                        'tremor_detected': manual_tremor_present
                    })
                
                # Push to visualizer
                viz_data = {
                    'status': system_status,
                    'emg_filtered': emg_filtered,
                    'emg_rms': emg_rms,
                    'accel_smooth': accel_smooth,
                    'gyro_smooth': gyro_smooth,
                    'log_status': 'RECORDING' if logger.is_recording else 'STOPPED',
                    'log_remaining': logger.get_remaining_time()
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
    multiprocessing.set_start_method('spawn', force=True)
    main()
