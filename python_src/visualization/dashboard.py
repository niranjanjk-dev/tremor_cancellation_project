import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets, QtGui
import sys
import time
from collections import deque
import serial.tools.list_ports

def run_dashboard(viz_queue, command_queue):
    app = QtWidgets.QApplication(sys.argv)
    
    # --- Dark Mode Setup ---
    pg.setConfigOption('background', '#121212')
    pg.setConfigOption('foreground', '#d3d3d3')
    pg.setConfigOptions(antialias=True)
    
    # --- Main Window & Layout ---
    win = QtWidgets.QMainWindow()
    win.setWindowTitle('Active Tremor Cancellation - Live Telemetry')
    win.resize(1200, 800)
    
    central_widget = QtWidgets.QWidget()
    central_widget.setStyleSheet("background-color: #121212;")
    win.setCentralWidget(central_widget)
    main_layout = QtWidgets.QVBoxLayout(central_widget)
    
    # --- Top Status Bar ---
    status_layout = QtWidgets.QHBoxLayout()
    
    lbl_status = QtWidgets.QLabel("SYSTEM: DISCONNECTED")
    lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFA500;")
    
    lbl_fps = QtWidgets.QLabel("UI FPS: 0.0")
    lbl_fps.setStyleSheet("font-size: 16px; font-weight: bold; color: #00FF00;")
    
    lbl_ml = QtWidgets.QLabel("TREMOR: NONE")
    lbl_ml.setStyleSheet("font-size: 16px; font-weight: bold; color: #d3d3d3; background-color: #333333; padding: 6px; border-radius: 4px;")
    
    lbl_fes = QtWidgets.QLabel("FES STIMULATION: OFF")
    lbl_fes.setStyleSheet("font-size: 16px; font-weight: bold; color: #d3d3d3; background-color: #333333; padding: 6px; border-radius: 4px;")
    
    # Port Selection
    lbl_port = QtWidgets.QLabel("Port:")
    lbl_port.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF;")
    
    port_combo = QtWidgets.QComboBox()
    port_combo.setStyleSheet("background-color: #333333; color: white; padding: 4px; font-size: 14px; border: 1px solid #555;")
    ports = [port.device for port in serial.tools.list_ports.comports()]
    port_combo.addItems(ports)
    
    btn_refresh = QtWidgets.QPushButton("Refresh")
    btn_refresh.setStyleSheet("background-color: #444444; color: white; padding: 6px; font-weight: bold; border-radius: 4px;")
    def refresh_ports():
        port_combo.clear()
        port_combo.addItems([port.device for port in serial.tools.list_ports.comports()])
    btn_refresh.clicked.connect(refresh_ports)
    
    btn_connect = QtWidgets.QPushButton("Connect")
    btn_connect.setStyleSheet("background-color: #006600; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px;")
    def on_connect():
        selected_port = port_combo.currentText()
        if selected_port:
            command_queue.put({'action': 'CONNECT', 'port': selected_port})
            lbl_status.setText(f"SYSTEM: CONNECTING TO {selected_port}...")
            lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFF00;")
    btn_connect.clicked.connect(on_connect)
    
    # Pause Button for Zooming
    is_paused = False
    btn_pause = QtWidgets.QPushButton("Pause for Zoom/Inspect")
    btn_pause.setStyleSheet("background-color: #335588; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px;")
    
    def on_pause():
        nonlocal is_paused
        is_paused = not is_paused
        if is_paused:
            btn_pause.setText("Resume Plotting")
            btn_pause.setStyleSheet("background-color: #883333; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px;")
        else:
            btn_pause.setText("Pause for Zoom/Inspect")
            btn_pause.setStyleSheet("background-color: #335588; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px;")
            
            # Snap back to auto range when resuming
            p_emg_raw.enableAutoRange(axis=pg.ViewBox.XAxis)
            p_emg_raw.setYRange(0, 4095)
            p_emg_rms.enableAutoRange(axis=pg.ViewBox.XAxis)
            p_emg_rms.setYRange(0, 4095)
            p_accel.enableAutoRange(axis=pg.ViewBox.XYAxes)
            p_gyro.enableAutoRange(axis=pg.ViewBox.XYAxes)

    btn_pause.clicked.connect(on_pause)

    status_layout.addWidget(lbl_status)
    status_layout.addSpacing(20)
    status_layout.addWidget(lbl_port)
    status_layout.addWidget(port_combo)
    status_layout.addWidget(btn_refresh)
    status_layout.addWidget(btn_connect)
    status_layout.addSpacing(20)
    status_layout.addWidget(btn_pause)
    status_layout.addStretch()
    status_layout.addWidget(lbl_ml)
    status_layout.addSpacing(20)
    status_layout.addWidget(lbl_fes)
    status_layout.addStretch()
    status_layout.addWidget(lbl_fps)
    
    main_layout.addLayout(status_layout)
    
    # --- Graphics Layout for Plots ---
    plot_layout = pg.GraphicsLayoutWidget()
    main_layout.addWidget(plot_layout)
    
    # --- Row 1: EMG Raw & Accel ---
    p_emg_raw = plot_layout.addPlot(title="EMG Raw Signal (Muscle Activation)")
    p_emg_raw.setYRange(0, 4095)
    curve_emg = p_emg_raw.plot(pen=pg.mkPen('#00FFFF', width=1.5))
    
    p_accel = plot_layout.addPlot(title="IMU Accelerometer (Linear Movement)")
    curve_ax = p_accel.plot(pen=pg.mkPen('#FF5555', width=1.5), name="X")
    curve_ay = p_accel.plot(pen=pg.mkPen('#55FF55', width=1.5), name="Y")
    curve_az = p_accel.plot(pen=pg.mkPen('#5555FF', width=1.5), name="Z")
    
    plot_layout.nextRow()
    
    # --- Row 2: EMG RMS & Gyro ---
    p_emg_rms = plot_layout.addPlot(title="EMG RMS Envelope (Amplitude)")
    p_emg_rms.setYRange(0, 4095)
    curve_rms = p_emg_rms.plot(pen=pg.mkPen('#FF00FF', width=2.5))
    
    p_gyro = plot_layout.addPlot(title="IMU Gyroscope (Rotational Tremor)")
    curve_gx = p_gyro.plot(pen=pg.mkPen('#FF5555', width=1.5), name="X")
    curve_gy = p_gyro.plot(pen=pg.mkPen('#55FF55', width=1.5), name="Y")
    curve_gz = p_gyro.plot(pen=pg.mkPen('#5555FF', width=1.5), name="Z")
    
    # --- Data Buffers ---
    window_size = 200
    data_emg = deque([0]*window_size, maxlen=window_size)
    data_rms = deque([0]*window_size, maxlen=window_size)
    data_ax = deque([0]*window_size, maxlen=window_size)
    data_ay = deque([0]*window_size, maxlen=window_size)
    data_az = deque([0]*window_size, maxlen=window_size)
    data_gx = deque([0]*window_size, maxlen=window_size)
    data_gy = deque([0]*window_size, maxlen=window_size)
    data_gz = deque([0]*window_size, maxlen=window_size)
    
    # FPS Tracking
    last_update_time = time.time()
    fps_frames = 0
    
    def update():
        nonlocal last_update_time, fps_frames
        
        has_new_data = False
        sys_status = None
        tremor_detected = False
        fes_active = False
        
        # Consume all available items in the queue
        while not viz_queue.empty():
            try:
                data = viz_queue.get_nowait()
                has_new_data = True
                
                sys_status = data.get('status')
                tremor_detected = data.get('tremor', False)
                fes_active = data.get('fes', False)
                
                data_emg.append(data['emg_raw'])
                data_rms.append(data['emg_rms'])
                
                ax, ay, az = data['accel_smooth']
                data_ax.append(ax)
                data_ay.append(ay)
                data_az.append(az)
                
                gx, gy, gz = data['gyro_smooth']
                data_gx.append(gx)
                data_gy.append(gy)
                data_gz.append(gz)
                
            except Exception:
                break
        
        if has_new_data:
            # Update Top Bar Status
            if sys_status:
                if sys_status == "LIVE":
                    lbl_status.setText("SYSTEM: CONNECTED (LIVE)")
                    lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: #00FFFF;")
                elif sys_status.startswith("ERROR"):
                    lbl_status.setText(f"SYSTEM: {sys_status}")
                    lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: #FF0000;")
                elif sys_status == "DISCONNECTED":
                    lbl_status.setText("SYSTEM: DISCONNECTED")
                    lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFA500;")
                
            if tremor_detected:
                lbl_ml.setText("TREMOR: DETECTED")
                lbl_ml.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF; background-color: #FF0000; padding: 6px; border-radius: 4px;")
            else:
                lbl_ml.setText("TREMOR: NONE")
                lbl_ml.setStyleSheet("font-size: 16px; font-weight: bold; color: #d3d3d3; background-color: #333333; padding: 6px; border-radius: 4px;")
                
            if fes_active:
                lbl_fes.setText("FES STIMULATION: FIRING")
                lbl_fes.setStyleSheet("font-size: 16px; font-weight: bold; color: #000000; background-color: #00FFFF; padding: 6px; border-radius: 4px;")
            else:
                lbl_fes.setText("FES STIMULATION: OFF")
                lbl_fes.setStyleSheet("font-size: 16px; font-weight: bold; color: #d3d3d3; background-color: #333333; padding: 6px; border-radius: 4px;")

            if not is_paused:
                # Update plot curves
                curve_emg.setData(list(data_emg))
                curve_rms.setData(list(data_rms))
                
                curve_ax.setData(list(data_ax))
                curve_ay.setData(list(data_ay))
                curve_az.setData(list(data_az))
                
                curve_gx.setData(list(data_gx))
                curve_gy.setData(list(data_gy))
                curve_gz.setData(list(data_gz))
                
        # Calculate FPS
        fps_frames += 1
        now = time.time()
        if now - last_update_time >= 1.0:
            fps = fps_frames / (now - last_update_time)
            lbl_fps.setText(f"UI FPS: {fps:.1f}")
            last_update_time = now
            fps_frames = 0

    # Timer to update GUI smoothly
    timer = QtCore.QTimer()
    timer.timeout.connect(update)
    timer.start(30) # ~30 fps update rate

    win.show()
    sys.exit(app.exec_())
