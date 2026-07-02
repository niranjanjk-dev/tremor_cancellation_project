import sys
import os

# Ensure pyqtgraph uses PyQt5 consistently across all OS (fixes Windows TypeError)
os.environ["PYQTGRAPH_QT_LIB"] = "PyQt5"
# Silence Windows DPI awareness warnings
os.environ["QT_SCALE_FACTOR"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets, QtGui
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
            p_emg_raw.setYRange(-1000, 1000)
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
    status_layout.addWidget(lbl_fps)
    
    main_layout.addLayout(status_layout)
    
    # --- Data Logging Bar ---
    logging_layout = QtWidgets.QHBoxLayout()
    
    lbl_log_title = QtWidgets.QLabel("DATA LOGGING:")
    lbl_log_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF;")
    
    lbl_user = QtWidgets.QLabel("User:")
    lbl_user.setStyleSheet("font-size: 14px; color: #d3d3d3;")
    input_user = QtWidgets.QComboBox()
    input_user.setEditable(True)
    input_user.setStyleSheet("background-color: #333333; color: white; padding: 4px; font-size: 14px; border: 1px solid #555;")
    input_user.setFixedWidth(120)
    
    # scan for existing users
    default_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    existing_users = set()
    if os.path.exists(default_dir):
        for f in os.listdir(default_dir):
            if f.startswith("log_") and f.endswith(".csv"):
                parts = f.split("_")
                if len(parts) >= 2:
                    existing_users.add(parts[1])
    input_user.addItems(list(existing_users))
    if not existing_users:
        input_user.setEditText("Guest")
    
    lbl_action = QtWidgets.QLabel("Action:")
    lbl_action.setStyleSheet("font-size: 14px; color: #d3d3d3;")
    combo_action = QtWidgets.QComboBox()
    combo_action.addItems([
        "Rest", "Picking and placing", "Spiral Moving", "Reaching a object",
        "Postural Hold", "Kinetic Movement", "Pointing", "Pouring Water"
    ])
    combo_action.setEditable(True)
    combo_action.setStyleSheet("background-color: #333333; color: white; padding: 4px; font-size: 14px; border: 1px solid #555;")
    
    lbl_duration = QtWidgets.QLabel("Duration (s):")
    lbl_duration.setStyleSheet("font-size: 14px; color: #d3d3d3;")
    spin_duration = QtWidgets.QSpinBox()
    spin_duration.setRange(1, 3600)
    spin_duration.setValue(30)
    spin_duration.setStyleSheet("background-color: #333333; color: white; padding: 4px; font-size: 14px; border: 1px solid #555;")
    
    btn_record = QtWidgets.QPushButton("Start Recording")
    btn_record.setStyleSheet("background-color: #883333; color: white; padding: 6px 15px; font-weight: bold; border-radius: 4px;")
    
    lbl_dir = QtWidgets.QLabel("Save Dir:")
    lbl_dir.setStyleSheet("font-size: 14px; color: #d3d3d3;")
    input_dir = QtWidgets.QLineEdit()
    input_dir.setText(default_dir)
    input_dir.setStyleSheet("background-color: #333333; color: white; padding: 4px; font-size: 14px; border: 1px solid #555;")
    input_dir.setFixedWidth(150)
    
    btn_browse = QtWidgets.QPushButton("...")
    btn_browse.setStyleSheet("background-color: #555555; color: white; padding: 4px; font-weight: bold;")
    def on_browse():
        directory = QtWidgets.QFileDialog.getExistingDirectory(win, "Select Save Directory", input_dir.text())
        if directory:
            input_dir.setText(directory)
    btn_browse.clicked.connect(on_browse)
    
    lbl_rec_status = QtWidgets.QLabel("Ready")
    lbl_rec_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #AAAAAA;")
    
    chk_tremor = QtWidgets.QCheckBox("Tremor Present")
    chk_tremor.setStyleSheet("color: white; font-size: 14px; font-weight: bold; border: 2px solid #666; border-radius: 4px; padding: 4px; background-color: #222;")
    def on_tremor_toggled(state):
        command_queue.put({'action': 'SET_TREMOR', 'state': bool(state)})
    chk_tremor.stateChanged.connect(on_tremor_toggled)
    
    def on_record():
        user = input_user.currentText()
        action = combo_action.currentText()
        duration = spin_duration.value()
        save_dir = input_dir.text()
        
        command_queue.put({
            'action': 'START_LOG',
            'user': user,
            'action_name': action,
            'duration': duration,
            'save_dir': save_dir
        })
        lbl_rec_status.setText(f"Requesting log for {duration}s...")
        lbl_rec_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFF00;")

    btn_record.clicked.connect(on_record)
    
    logging_layout.addWidget(lbl_log_title)
    logging_layout.addSpacing(10)
    logging_layout.addWidget(lbl_user)
    logging_layout.addWidget(input_user)
    logging_layout.addSpacing(10)
    logging_layout.addWidget(lbl_action)
    logging_layout.addWidget(combo_action)
    logging_layout.addSpacing(10)
    logging_layout.addWidget(lbl_duration)
    logging_layout.addWidget(spin_duration)
    logging_layout.addSpacing(10)
    logging_layout.addWidget(btn_record)
    logging_layout.addSpacing(10)
    logging_layout.addWidget(lbl_dir)
    logging_layout.addWidget(input_dir)
    logging_layout.addWidget(btn_browse)
    logging_layout.addSpacing(20)
    logging_layout.addWidget(chk_tremor)
    logging_layout.addSpacing(20)
    logging_layout.addWidget(lbl_rec_status)
    logging_layout.addStretch()
    
    main_layout.addLayout(logging_layout)
    
    # --- Graphics Layout for Plots ---
    plot_layout = pg.GraphicsLayoutWidget()
    main_layout.addWidget(plot_layout)
    
    # --- Row 1: EMG Raw & Accel ---
    p_emg_raw = plot_layout.addPlot(title="EMG Signal (Filtered & Centered)")
    p_emg_raw.setYRange(-1000, 1000) # Give it a centered range
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
        log_status = None
        log_remaining = 0
        
        # Consume all available items in the queue
        while not viz_queue.empty():
            try:
                data = viz_queue.get_nowait()
                has_new_data = True
                
                sys_status = data.get('status')
                
                if 'log_status' in data:
                    log_status = data['log_status']
                    log_remaining = data.get('log_remaining', 0)
                
                # Check if data contains actual graph updates
                if 'emg_filtered' in data:
                    data_emg.append(data['emg_filtered'])
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
                
            if log_status:
                if log_status == "RECORDING":
                    lbl_rec_status.setText(f"Recording... {int(log_remaining)}s left")
                    lbl_rec_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #FF0000;")
                elif log_status == "STOPPED":
                    lbl_rec_status.setText("Ready")
                    lbl_rec_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #AAAAAA;")

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
