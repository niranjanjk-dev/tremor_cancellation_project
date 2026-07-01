class IMUProcessor:
    def __init__(self, alpha=0.2):
        """
        Initialize the IMU signal processor.
        :param alpha: Smoothing factor for Exponential Moving Average (EMA).
                      0 < alpha <= 1 (Lower = more smooth, higher latency).
        """
        self.alpha = alpha
        self.filtered_accel = None
        self.filtered_gyro = None

    def process(self, accel_tuple, gyro_tuple):
        """
        Process a single new IMU data point (accel, gyro).
        Returns smoothed tuples.
        """
        ax, ay, az = accel_tuple
        gx, gy, gz = gyro_tuple

        if self.filtered_accel is None:
            self.filtered_accel = [ax, ay, az]
            self.filtered_gyro = [gx, gy, gz]
        else:
            # Apply EMA to Accel
            self.filtered_accel[0] = self.alpha * ax + (1 - self.alpha) * self.filtered_accel[0]
            self.filtered_accel[1] = self.alpha * ay + (1 - self.alpha) * self.filtered_accel[1]
            self.filtered_accel[2] = self.alpha * az + (1 - self.alpha) * self.filtered_accel[2]

            # Apply EMA to Gyro
            self.filtered_gyro[0] = self.alpha * gx + (1 - self.alpha) * self.filtered_gyro[0]
            self.filtered_gyro[1] = self.alpha * gy + (1 - self.alpha) * self.filtered_gyro[1]
            self.filtered_gyro[2] = self.alpha * gz + (1 - self.alpha) * self.filtered_gyro[2]

        return tuple(self.filtered_accel), tuple(self.filtered_gyro)
