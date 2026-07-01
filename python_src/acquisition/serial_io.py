import serial
import struct
import time
import threading

# The struct format string must match the ESP32 C++ struct exactly.
# '<' = Little Endian (ESP32 standard)
# 'B' = unsigned char (1 byte)
# 'I' = unsigned int (4 bytes)
# 'H' = unsigned short (2 bytes)
# 'h' = signed short (2 bytes)
# Format: 2 Sync bytes, Timestamp, EMG, 3 Accel, 3 Gyro, 3 Mag
STRUCT_FORMAT = '<2B I H 9h'
PACKET_SIZE = struct.calcsize(STRUCT_FORMAT) # Should be 26 bytes

class SerialDataAcquisition(threading.Thread):
    def __init__(self, data_queue, port='/dev/ttyUSB0', baud_rate=115200):
        super().__init__()
        self.data_queue = data_queue
        self.port = port
        self.baud_rate = baud_rate
        self.running = False
        self.ser = None
        self.daemon = True # Allows thread to exit when main program exits

    def run(self):
        try:
            self.ser = serial.Serial(self.port, self.baud_rate, timeout=1)
            print(f"[Serial] Successfully connected to {self.port}.")
        except Exception as e:
            print(f"[Serial] Failed to connect to {self.port}: {e}")
            return

        self.running = True
        print("[Serial] Waiting for sync bytes...")

        # Flush the buffer to clear any old junk data
        self.ser.reset_input_buffer()

        while self.running:
            try:
                # 1. Align to the sync bytes (0xAA, 0xBB)
                if self.ser.in_waiting >= 2:
                    sync_bytes = self.ser.read(2)
                    if sync_bytes == b'\xaa\xbb':
                        
                        # 2. Wait for the rest of the packet (24 bytes remaining)
                        while self.ser.in_waiting < (PACKET_SIZE - 2):
                            if not self.running:
                                break
                            pass 
                        
                        if not self.running:
                            break
                        
                        # 3. Read the rest of the payload
                        payload = self.ser.read(PACKET_SIZE - 2)
                        
                        # 4. Unpack the data
                        # We pass the sync bytes + payload into the struct unpacker
                        data = struct.unpack(STRUCT_FORMAT, sync_bytes + payload)
                        
                        # Extract variables into a dictionary for clean queue transmission
                        parsed_data = {
                            'timestamp': data[2],
                            'emg': data[3],
                            'accel': (data[4], data[5], data[6]),
                            'gyro': (data[7], data[8], data[9]),
                            'mag': (data[10], data[11], data[12])
                        }

                        # Push to queue for the main thread or processing threads
                        if not self.data_queue.full():
                            self.data_queue.put(parsed_data)
                        
                    else:
                        # If sync failed, read 1 byte and try aligning again
                        self.ser.read(1) 

            except Exception as e:
                print(f"\n[Serial] Error during read: {e}")
                self.running = False
                break

        if self.ser and self.ser.is_open:
            self.ser.close()
            print("[Serial] Disconnected.")

    def stop(self):
        self.running = False
        self.join()
