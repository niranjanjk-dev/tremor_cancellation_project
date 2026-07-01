import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
import sys
import multiprocessing

def run_visualizer(viz_queue):
    """
    Runs a PyQtGraph application in a separate process.
    """
    app = QtWidgets.QApplication([])
    
    win = pg.GraphicsLayoutWidget(show=True, title="Real-Time Tremor Cancellation Telemetry")
    win.resize(1000, 600)
    win.setWindowTitle('EMG & IMU Telemetry')

    # Enable antialiasing for prettier plots
    pg.setConfigOptions(antialias=True)

    # --- Plot 1: EMG ---
    p1 = win.addPlot(title="EMG Signal (Raw & Filtered RMS)")
    p1.setYRange(0, 4095)
    curve_emg_raw = p1.plot(pen=pg.mkPen('b', width=1), name="Raw")
    curve_emg_rms = p1.plot(pen=pg.mkPen('r', width=2), name="RMS Envelope")
    
    win.nextRow()

    # --- Plot 2: IMU Accel ---
    p2 = win.addPlot(title="IMU Accelerometer (Smoothed)")
    curve_ax = p2.plot(pen=pg.mkPen('r', width=1.5))
    curve_ay = p2.plot(pen=pg.mkPen('g', width=1.5))
    curve_az = p2.plot(pen=pg.mkPen('b', width=1.5))

    # Data arrays
    window_size = 200
    data_emg_raw = [0] * window_size
    data_emg_rms = [0] * window_size
    data_ax = [0] * window_size
    data_ay = [0] * window_size
    data_az = [0] * window_size

    def update():
        # Consume all available items in the queue
        while not viz_queue.empty():
            try:
                data = viz_queue.get_nowait()
                
                # Append and pop
                data_emg_raw.append(data['emg_raw'])
                data_emg_raw.pop(0)
                
                data_emg_rms.append(data['emg_rms'])
                data_emg_rms.pop(0)

                ax, ay, az = data['accel_smooth']
                data_ax.append(ax)
                data_ax.pop(0)
                data_ay.append(ay)
                data_ay.pop(0)
                data_az.append(az)
                data_az.pop(0)

            except Exception:
                break
        
        # Update plot curves
        curve_emg_raw.setData(data_emg_raw)
        curve_emg_rms.setData(data_emg_rms)
        
        curve_ax.setData(data_ax)
        curve_ay.setData(data_ay)
        curve_az.setData(data_az)

    # Timer to update GUI smoothly
    timer = QtCore.QTimer()
    timer.timeout.connect(update)
    timer.start(30) # ~30 fps update rate

    sys.exit(app.exec_())
