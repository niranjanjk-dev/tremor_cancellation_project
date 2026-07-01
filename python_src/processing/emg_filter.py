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
        
        # At 20Hz sampling rate, a 50Hz notch filter is impossible (Nyquist is 10Hz).
        # We will design a simple bandpass filter within the available bandwidth.
        # In a real high-speed system, fs would be 1000Hz+ and we would use:
        # self.b_notch, self.a_notch = signal.iirnotch(notch_freq, 30.0, fs)
        # self.b_band, self.a_band = signal.butter(4, [20, 450], btype='bandpass', fs=fs)
        
        # For our 20Hz prototype, we will just use a simple lowpass/highpass if needed,
        # but to demonstrate the architecture, we'll configure a generic filter.
        if lowcut > 0 and highcut < self.nyquist:
            self.b_band, self.a_band = signal.butter(2, [lowcut/self.nyquist, highcut/self.nyquist], btype='band')
        else:
            # Fallback pass-through if Nyquist is too low
            self.b_band, self.a_band = None, None

        self.rms_window = rms_window
        self.history = []

    def process(self, raw_value):
        """
        Process a single new EMG data point.
        """
        self.history.append(raw_value)
        
        # Maintain buffer size
        if len(self.history) > max(50, self.rms_window):
            self.history.pop(0)

        # We need a minimum number of samples to apply scipy filters effectively
        # For real-time point-by-point, a stateful filter using `lfilter_zi` is preferred,
        # but for simplicity in this prototype, we'll apply it to the recent window.
        if self.b_band is not None and len(self.history) > 10:
            filtered_array = signal.lfilter(self.b_band, self.a_band, self.history)
            filtered_val = filtered_array[-1]
        else:
            filtered_val = raw_value

        # Calculate RMS of the last N samples
        if len(self.history) >= self.rms_window:
            window = self.history[-self.rms_window:]
            rms_val = np.sqrt(np.mean(np.square(window)))
        else:
            rms_val = np.abs(filtered_val)

        return filtered_val, rms_val
