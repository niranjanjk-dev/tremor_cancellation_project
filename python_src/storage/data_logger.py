import csv
import time
import os
from datetime import datetime

class DataLogger:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            
        self.is_recording = False
        self.file_path = None
        self.file_obj = None
        self.csv_writer = None
        
        self.start_time = 0
        self.duration = 0
        
        self.user_name = ""
        self.action_name = ""
        
        self.headers = [
            "timestamp", "user_name", "action",
            "emg_raw", "emg_filtered", "emg_rms",
            "accel_x_raw", "accel_y_raw", "accel_z_raw",
            "accel_x_smooth", "accel_y_smooth", "accel_z_smooth",
            "gyro_x_raw", "gyro_y_raw", "gyro_z_raw",
            "gyro_x_smooth", "gyro_y_smooth", "gyro_z_smooth",
            "tremor_detected", "pre_tremor_detected"
        ]

    def start_recording(self, user_name, action_name, duration_seconds, custom_dir=None):
        self.user_name = user_name
        self.action_name = action_name
        self.duration = duration_seconds
        
        target_dir = custom_dir if custom_dir else self.data_dir
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_user = "".join([c for c in user_name if c.isalpha() or c.isdigit() or c=='_']).strip()
        safe_action = "".join([c for c in action_name if c.isalpha() or c.isdigit() or c=='_']).strip()
        if not safe_user: safe_user = "unknown"
        if not safe_action: safe_action = "unknown"
        
        filename = f"log_{safe_user}_{safe_action}_{timestamp_str}.csv"
        self.file_path = os.path.join(target_dir, filename)
        
        self.file_obj = open(self.file_path, mode='w', newline='')
        self.csv_writer = csv.writer(self.file_obj)
        self.csv_writer.writerow(self.headers)
        
        self.start_time = time.time()
        self.is_recording = True
        print(f"Started recording to {self.file_path} for {self.duration} seconds.")

    def log_data(self, data_dict):
        if not self.is_recording:
            return
            
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        if elapsed >= self.duration:
            self.stop_recording()
            return
            
        # Extract data
        timestamp = current_time
        emg_raw = data_dict.get('emg', 0)
        emg_filt = data_dict.get('emg_filtered', 0)
        emg_rms = data_dict.get('emg_rms', 0)
        
        ax_r, ay_r, az_r = data_dict.get('accel', (0,0,0))
        ax_s, ay_s, az_s = data_dict.get('accel_smooth', (0,0,0))
        
        gx_r, gy_r, gz_r = data_dict.get('gyro', (0,0,0))
        gx_s, gy_s, gz_s = data_dict.get('gyro_smooth', (0,0,0))
        
        tremor = data_dict.get('tremor_detected', False)
        pre_tremor = data_dict.get('pre_tremor_detected', False)
        
        row = [
            timestamp, self.user_name, self.action_name,
            emg_raw, emg_filt, emg_rms,
            ax_r, ay_r, az_r,
            ax_s, ay_s, az_s,
            gx_r, gy_r, gz_r,
            gx_s, gy_s, gz_s,
            int(tremor), int(pre_tremor)
        ]
        
        try:
            self.csv_writer.writerow(row)
        except Exception as e:
            print(f"Error writing to CSV: {e}")

    def stop_recording(self):
        if self.is_recording:
            self.is_recording = False
            if self.file_obj:
                self.file_obj.close()
                self.file_obj = None
            print(f"Stopped recording. File saved: {self.file_path}")

    def get_remaining_time(self):
        if not self.is_recording:
            return 0
        elapsed = time.time() - self.start_time
        remaining = max(0, self.duration - elapsed)
        return remaining
