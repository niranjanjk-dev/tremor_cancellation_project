import math

class IMUProcessor:
    def __init__(self, alpha_smooth=0.2, alpha_baseline=0.02):
        """
        Initialize the IMU signal processor with a Bandpass approach.
        :param alpha_smooth: Fast EMA for smoothing high-frequency noise (Low Pass).
        :param alpha_baseline: Slow EMA for tracking static gravity/drift (High Pass).
        """
        self.alpha_smooth = alpha_smooth
        self.alpha_baseline = alpha_baseline
        
        self.filtered_accel = None
        self.filtered_gyro = None
        
        self.gravity_baseline = None
        self.gyro_baseline = None

    def process(self, accel_tuple, gyro_tuple):
        """
        Process a single new IMU data point.
        Converts to engineering units (g, deg/s), removes DC gravity/drift, and smooths noise.
        """
        # 1. Convert raw int16 to engineering units (g and deg/s)
        # 16384 LSB/g for MPU6050 at +/- 2g
        ax = accel_tuple[0] / 16384.0
        ay = accel_tuple[1] / 16384.0
        az = accel_tuple[2] / 16384.0
        
        # 131 LSB/(deg/s) for MPU6050 at +/- 250deg/s
        gx = gyro_tuple[0] / 131.0
        gy = gyro_tuple[1] / 131.0
        gz = gyro_tuple[2] / 131.0

        if self.filtered_accel is None:
            self.filtered_accel = [0.0, 0.0, 0.0]
            self.filtered_gyro = [0.0, 0.0, 0.0]
            self.gravity_baseline = [ax, ay, az]
            self.gyro_baseline = [gx, gy, gz]
            return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0.0, 0.0

        # 2. Track the slow-moving static baseline (Gravity & Gyro Drift)
        self.gravity_baseline[0] = self.alpha_baseline * ax + (1 - self.alpha_baseline) * self.gravity_baseline[0]
        self.gravity_baseline[1] = self.alpha_baseline * ay + (1 - self.alpha_baseline) * self.gravity_baseline[1]
        self.gravity_baseline[2] = self.alpha_baseline * az + (1 - self.alpha_baseline) * self.gravity_baseline[2]

        self.gyro_baseline[0] = self.alpha_baseline * gx + (1 - self.alpha_baseline) * self.gyro_baseline[0]
        self.gyro_baseline[1] = self.alpha_baseline * gy + (1 - self.alpha_baseline) * self.gyro_baseline[1]
        self.gyro_baseline[2] = self.alpha_baseline * gz + (1 - self.alpha_baseline) * self.gyro_baseline[2]

        # 3. Remove the baseline to isolate dynamic movement (High-Pass Filter)
        dynamic_ax = ax - self.gravity_baseline[0]
        dynamic_ay = ay - self.gravity_baseline[1]
        dynamic_az = az - self.gravity_baseline[2]

        dynamic_gx = gx - self.gyro_baseline[0]
        dynamic_gy = gy - self.gyro_baseline[1]
        dynamic_gz = gz - self.gyro_baseline[2]

        # 4. Smooth the dynamic signal to remove noise (Low-Pass Filter)
        self.filtered_accel[0] = self.alpha_smooth * dynamic_ax + (1 - self.alpha_smooth) * self.filtered_accel[0]
        self.filtered_accel[1] = self.alpha_smooth * dynamic_ay + (1 - self.alpha_smooth) * self.filtered_accel[1]
        self.filtered_accel[2] = self.alpha_smooth * dynamic_az + (1 - self.alpha_smooth) * self.filtered_accel[2]

        self.filtered_gyro[0] = self.alpha_smooth * dynamic_gx + (1 - self.alpha_smooth) * self.filtered_gyro[0]
        self.filtered_gyro[1] = self.alpha_smooth * dynamic_gy + (1 - self.alpha_smooth) * self.filtered_gyro[1]
        self.filtered_gyro[2] = self.alpha_smooth * dynamic_gz + (1 - self.alpha_smooth) * self.filtered_gyro[2]

        # Calculate Roll and Pitch (from the baseline gravity vector, not the dynamic movement!)
        # Prevent division by zero
        faz = self.gravity_baseline[2] if self.gravity_baseline[2] != 0 else 0.001
        
        roll = math.atan2(self.gravity_baseline[1], faz) * 180.0 / math.pi
        pitch = math.atan2(-self.gravity_baseline[0], math.sqrt(self.gravity_baseline[1]**2 + faz**2)) * 180.0 / math.pi

        return tuple(self.filtered_accel), tuple(self.filtered_gyro), roll, pitch
