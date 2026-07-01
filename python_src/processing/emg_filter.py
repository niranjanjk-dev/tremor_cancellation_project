import numpy as np
from scipy import signal

class EMGProcessor:
    def __init__(self, fs=20, notch_freq=50.0, lowcut=5.0, highcut=9.99, rms_window=5):
        """
        Initialize the EMG signal processor.
        :param fs: Sampling frequency (Hz). Note: 20Hz is very low for EMG (usually >1000Hz).
                   Adjusting filters to be within the Nyquist limit (fs/2 = 10Hz) for the current 20Hz hardware rate.
        :param notch_freq: Frequency to notch filter (Hz).
        :param lowcut: Bandpass lower cutoff (Hz).
        :param highcut: Bandpass upper cutoff (Hz).
        :param rms_window: Number of samples for RMS window.
        """
        self.fs = fs
        self.nyquist = 0.5 * fs
        
        # 1. Notch Filter Initialization
        if notch_freq < self.nyquist:
            self.b_notch, self.a_notch = signal.iirnotch(notch_freq, 30.0, self.fs)
            self.zi_notch = signal.lfilter_zi(self.b_notch, self.a_notch)
        else:
            self.b_notch = None

        # 2. Bandpass Filter Initialization
        if lowcut > 0 and highcut < self.nyquist:
            self.b_band, self.a_band = signal.butter(2, [lowcut/self.nyquist, highcut/self.nyquist], btype='band')
            self.zi_band = signal.lfilter_zi(self.b_band, self.a_band)
        else:
            self.b_band = None

        self.rms_window = rms_window
        self.history = []
        
        # For DC-Blocking EMA Filter
        self.dc_bias = None
        
        # For RMS Smoothing
        self.smoothed_rms = 0.0

    def process(self, raw_value):
        """
        Process a single new EMG data point.
        """
        # 1. DC-Blocking High-Pass Filter (EMA)
        if self.dc_bias is None:
            self.dc_bias = raw_value
            
        # Slow EMA to track and isolate the DC bias (e.g. ~2000 resting voltage)
        alpha_dc = 0.05
        self.dc_bias = alpha_dc * raw_value + (1.0 - alpha_dc) * self.dc_bias
        
        # Continuously subtract the resting voltage to force resting state to exactly 0.0
        ac_value = raw_value - self.dc_bias
        filtered_val = ac_value

        # 2. 50Hz/60Hz Notch Filter (if sampling rate allows)
        if self.b_notch is not None:
            filtered_val, self.zi_notch = signal.lfilter(
                self.b_notch, self.a_notch, [filtered_val], zi=self.zi_notch
            )
            filtered_val = filtered_val[0]

        # 3. Bandpass Filter
        if self.b_band is not None:
            filtered_val, self.zi_band = signal.lfilter(
                self.b_band, self.a_band, [filtered_val], zi=self.zi_band
            )
            filtered_val = filtered_val[0]

        # Maintain buffer size for RMS
        self.history.append(filtered_val)
        if len(self.history) > max(50, self.rms_window):
            self.history.pop(0)

        # Calculate RMS of the last N samples
        if len(self.history) >= self.rms_window:
            window = self.history[-self.rms_window:]
            rms_val = np.sqrt(np.mean(np.square(window)))
        else:
            rms_val = np.abs(filtered_val)
            
        # 4. Noise and Value Filters for the Raw Signal (No Fluctuations)
        # Apply a noise gate (deadzone) to eliminate idle noise completely
        raw_noise_gate = 100.0
        if abs(filtered_val) < raw_noise_gate:
            filtered_val = 0.0
        else:
            # Soften the jump to avoid harsh staircases
            filtered_val = filtered_val - raw_noise_gate if filtered_val > 0 else filtered_val + raw_noise_gate

        # Add a slight EMA smoothing to the raw signal to make it look cleaner
        if not hasattr(self, 'smoothed_raw'):
            self.smoothed_raw = 0.0
        alpha_raw = 0.3
        self.smoothed_raw = alpha_raw * filtered_val + (1.0 - alpha_raw) * self.smoothed_raw
        filtered_val = self.smoothed_raw

        # 5. Smooth the RMS Envelope for stability
        # A small alpha means more smoothing (less sensitive to sudden noise spikes)
        alpha_rms = 0.1 
        if self.smoothed_rms == 0.0:
            self.smoothed_rms = rms_val
        else:
            self.smoothed_rms = alpha_rms * rms_val + (1.0 - alpha_rms) * self.smoothed_rms

        # 6. Subtract Noise Floor to force idle to exactly 0, AND make it 2x sensitive
        noise_floor = 150.0
        # Subtract the floor, floor it at 0, then multiply by 2 for 2x sensitivity
        final_rms = max(0.0, self.smoothed_rms - noise_floor) * 2.0

        return filtered_val, final_rms
