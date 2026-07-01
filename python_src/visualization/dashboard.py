import pyqtgraph as pg
import pyqtgraph.opengl as gl
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
    win.resize(1400, 800)
    
    central_widget = QtWidgets.QWidget()
    win.setCentralWidget(central_widget)
    main_layout = QtWidgets.QVBoxLayout(central_widget)
    
    # --- Top Status Bar ---
    status_layout = QtWidgets.QHBoxLayout()
    
    lbl_status = QtWidgets.QLabel("SYSTEM: DISCONNECTED")
    lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFA500;")
    
    lbl_fps = QtWidgets.QLabel("UI FPS: 0.0")
    lbl_fps.setStyleSheet("font-size: 16px; font-weight: bold; color: #00FF00;")
    
    lbl_ml = QtWidgets.QLabel("TREMOR: NONE")
    lbl_ml.setStyleSheet("font-size: 16px; font-weight: bold; color: #888888; background-color: #333333; padding: 5px; border-radius: 4px;")
    
    lbl_fes = QtWidgets.QLabel("FES STIMULATION: OFF")
    lbl_fes.setStyleSheet("font-size: 16px; font-weight: bold; color: #888888; background-color: #333333; padding: 5px; border-radius: 4px;")
    
    # Port Selection
    port_combo = QtWidgets.QComboBox()
    ports = [port.device for port in serial.tools.list_ports.comports()]
    port_combo.addItems(ports)
    
    btn_refresh = QtWidgets.QPushButton("Refresh")
    def refresh_ports():
        port_combo.clear()
        port_combo.addItems([port.device for port in serial.tools.list_ports.comports()])
    btn_refresh.clicked.connect(refresh_ports)
    
    btn_connect = QtWidgets.QPushButton("Connect")
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
    btn_pause.setStyleSheet("background-color: #444444; color: white;")
    def on_pause():
        nonlocal is_paused
        is_paused = not is_paused
        if is_paused:
            btn_pause.setText("Resume Plotting")
            btn_pause.setStyleSheet("background-color: #FF5555; color: white;")
        else:
            btn_pause.setText("Pause for Zoom/Inspect")
            btn_pause.setStyleSheet("background-color: #444444; color: white;")
    btn_pause.clicked.connect(on_pause)

    status_layout.addWidget(lbl_status)
    status_layout.addSpacing(20)
    status_layout.addWidget(QtWidgets.QLabel("Port:"))
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
    
    # --- Content Layout (Plots + 3D) ---
    content_layout = QtWidgets.QHBoxLayout()
    main_layout.addLayout(content_layout)
    
    # Graphics Layout for Plots
    plot_layout = pg.GraphicsLayoutWidget()
    content_layout.addWidget(plot_layout, stretch=3)
    
    # 3D GLViewWidget for Orientation
    gl_view = gl.GLViewWidget()
    gl_view.opts['distance'] = 40 # zoom out a bit
    gl_view.setWindowTitle('Live IMU Orientation')
    content_layout.addWidget(gl_view, stretch=1)
    
    # Add a grid to 3D view
    grid = gl.GLGridItem()
    grid.scale(2, 2, 2)
    gl_view.addItem(grid)
    
    # Add a 3D box representing the IMU/Limb
    cube = gl.GLBoxItem(size=QtGui.QVector3D(10, 10, 10), color=(0, 255, 255, 150))
    # Translate so the origin is at the center of the box for rotation
    cube.translate(-5, -5, -5)
    
    # Create a transform node to hold the rotation
    transform_node = gl.GLGLTFItem(glOptions='translucent') if hasattr(gl, 'GLGLTFItem') else None
    
    # Actually, GLBoxItem has an internal transform we can modify.
    # To rotate around its center, we need to apply the rotation matrix manually
    # or just use rotate on the item. But rotate accumulates, so we resetTransform.
    gl_view.addItem(cube)
    
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
    current_roll, current_pitch = 0, 0
    
    def update():
        nonlocal last_update_time, fps_frames, current_roll, current_pitch
        
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
                
                current_roll = data.get('roll', 0)
                current_pitch = data.get('pitch', 0)
                
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
                lbl_ml.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF; background-color: #FF0000; padding: 5px; border-radius: 4px;")
            else:
                lbl_ml.setText("TREMOR: NONE")
                lbl_ml.setStyleSheet("font-size: 16px; font-weight: bold; color: #888888; background-color: #333333; padding: 5px; border-radius: 4px;")
                
            if fes_active:
                lbl_fes.setText("FES STIMULATION: FIRING")
                lbl_fes.setStyleSheet("font-size: 16px; font-weight: bold; color: #000000; background-color: #00FFFF; padding: 5px; border-radius: 4px;")
            else:
                lbl_fes.setText("FES STIMULATION: OFF")
                lbl_fes.setStyleSheet("font-size: 16px; font-weight: bold; color: #888888; background-color: #333333; padding: 5px; border-radius: 4px;")

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
                
                # Update 3D Cube Rotation
                cube.resetTransform()
                # Rotate first, then translate back to origin so it spins on its center
                # PyQtGraph applies transforms in reverse order!
                cube.rotate(current_roll, 1, 0, 0)
                cube.rotate(current_pitch, 0, 1, 0)
                cube.translate(-5, -5, -5) 

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
