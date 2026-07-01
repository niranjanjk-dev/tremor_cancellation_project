import math

class IMUProcessor:
    def __init__(self, alpha=0.2):
        """
        Initialize the IMU signal processor.
        :param alpha: Smoothing factor for Exponential Moving Average (EMA).
        """
        self.alpha = alpha
        self.filtered_accel = None
        self.filtered_gyro = None

    def process(self, accel_tuple, gyro_tuple):
        """
        Process a single new IMU data point (accel, gyro).
        Returns smoothed tuples and orientation (roll, pitch).
        """
        ax, ay, az = accel_tuple
        gx, gy, gz = gyro_tuple

        if self.filtered_accel is None:
            self.filtered_accel = [ax, ay, az]
            self.filtered_gyro = [gx, gy, gz]
        else:
            self.filtered_accel[0] = self.alpha * ax + (1 - self.alpha) * self.filtered_accel[0]
            self.filtered_accel[1] = self.alpha * ay + (1 - self.alpha) * self.filtered_accel[1]
            self.filtered_accel[2] = self.alpha * az + (1 - self.alpha) * self.filtered_accel[2]

            self.filtered_gyro[0] = self.alpha * gx + (1 - self.alpha) * self.filtered_gyro[0]
            self.filtered_gyro[1] = self.alpha * gy + (1 - self.alpha) * self.filtered_gyro[1]
            self.filtered_gyro[2] = self.alpha * gz + (1 - self.alpha) * self.filtered_gyro[2]

        fax, fay, faz = self.filtered_accel
        
        # Calculate Roll and Pitch from gravity vector (accelerometer)
        # Prevent division by zero with small epsilon
        faz = faz if faz != 0 else 0.001
        
        roll = math.atan2(fay, faz) * 180.0 / math.pi
        pitch = math.atan2(-fax, math.sqrt(fay * fay + faz * faz)) * 180.0 / math.pi

        return tuple(self.filtered_accel), tuple(self.filtered_gyro), roll, pitch
