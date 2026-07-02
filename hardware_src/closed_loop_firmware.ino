#include <Wire.h>

const int EMG_PIN = 34;

// I2C Addresses
const uint8_t MPU9250_ADDR = 0x68;
const uint8_t AK8963_ADDR = 0x0C;

const unsigned long SAMPLE_INTERVAL_MS = 50; // 20 Hz
unsigned long nextSampleTime = 0;
bool magEnabled = false;

// Highly Optimized Binary Structure
// __attribute__((packed)) ensures the compiler doesn't add empty padding bytes
struct __attribute__((packed)) SensorData {
  uint8_t sync1 = 0xAA; // Hi hello
  uint8_t sync2 = 0xBB; // Sync byte 2
  uint32_t timestamp;   // 4 bytes
  uint16_t emgRaw;      // 2 bytes
  int16_t accelX;       // 2 bytes
  int16_t accelY;       // 2 bytes
  int16_t accelZ;       // 2 bytes
  int16_t gyroX;        // 2 bytes
  int16_t gyroY;        // 2 bytes
  int16_t gyroZ;        // 2 bytes
  int16_t magX;         // hhhhh
  int16_t magY;         // 2 bytes
  int16_t magZ;         // 2 bytes
};

SensorData packet; // Create an instance of our packet

// --- Helper Functions ---
inline void writeRegister(uint8_t address, uint8_t reg, uint8_t value) {
  Wire.beginTransmission(address);
  Wire.write(reg);
  Wire.write(value);
  Wire.endTransmission();
}

uint8_t readRegister(uint8_t address, uint8_t reg) {
  Wire.beginTransmission(address);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0)
    return 0;
  if (Wire.requestFrom(address, (uint8_t)1) == 1)
    return Wire.read();
  return 0;
}

bool readRegisters(uint8_t address, uint8_t reg, uint8_t count, uint8_t *dest) {
  Wire.beginTransmission(address);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0)
    return false;
  if (Wire.requestFrom(address, count) == count) {
    Wire.readBytes(dest, count);
    return true;
  }
  return false;
}

inline int16_t readInt16(uint8_t highByte, uint8_t lowByte) {
  return (int16_t)((highByte << 8) | lowByte);
}

// --- Init Functions ---
bool initMPU9250() {
  writeRegister(MPU9250_ADDR, 0x6B, 0x00); // PWR_MGMT_1 wake up
  delay(10);
  writeRegister(MPU9250_ADDR, 0x37, 0x02); // INT_PIN_CFG bypass mode for Mag
  return readRegister(MPU9250_ADDR, 0x75) == 0x71; // WHO_AM_I
}

bool initAK8963() {
  writeRegister(AK8963_ADDR, 0x0A, 0x16); // CNTL1: 100Hz continuous measurement
  return true;
}

void setup() {
  Serial.begin(115200);       // Or try 921600 for even faster transmission
  Wire.begin(21, 22, 400000); // I2C Fast Mode

  if (initMPU9250()) {
    magEnabled = initAK8963();
  }

  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
  pinMode(EMG_PIN, INPUT);

  nextSampleTime = millis();
}

void loop() {
  unsigned long now = millis();
  if (now < nextSampleTime)
    return;

  nextSampleTime += SAMPLE_INTERVAL_MS;
  if (now - nextSampleTime >= SAMPLE_INTERVAL_MS) {
    nextSampleTime = now + SAMPLE_INTERVAL_MS;
  }

  packet.timestamp = now;
  packet.emgRaw = analogRead(EMG_PIN);

  uint8_t buffer[14];
  if (readRegisters(MPU9250_ADDR, 0x3B, 14, buffer)) {
    packet.accelX = readInt16(buffer[0], buffer[1]);
    packet.accelY = readInt16(buffer[2], buffer[3]);
    packet.accelZ = readInt16(buffer[4], buffer[5]);
    packet.gyroX = readInt16(buffer[8], buffer[9]);
    packet.gyroY = readInt16(buffer[10], buffer[11]);
    packet.gyroZ = readInt16(buffer[12], buffer[13]);
  }

  if (magEnabled && (readRegister(AK8963_ADDR, 0x02) & 0x01)) {
    uint8_t magData[7];
    if (readRegisters(AK8963_ADDR, 0x03, 7, magData)) {
      packet.magX = readInt16(magData[1], magData[0]);
      packet.magY = readInt16(magData[3], magData[2]);
      packet.magZ = readInt16(magData[5], magData[4]);
    }
  }

  // Blast the memory block directly to the Serial port
  Serial.write((uint8_t *)&packet, sizeof(packet));
}
