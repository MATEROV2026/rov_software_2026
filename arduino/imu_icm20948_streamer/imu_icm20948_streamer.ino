/*
 * imu_icm20948_streamer.ino - IMU streamer for the ROV calibration bench.
 *
 * Streams accel, gyro, magnetometer and die temperature over USB serial for
 * imu_live.html. Calibration and attitude filtering happen on the host, so
 * what you tune on the bench is exactly what ships to the ROS node.
 *
 * Wiring (I2C): VCC->3.3V, GND->GND, SDA->SDA, SCL->SCL.
 * AD0 high -> address 0x69, AD0 low -> 0x68. Both are tried at boot.
 *
 * Serial protocol, 115200 baud:
 *   #IMU,ICM20948,1.0,1.0,0x69        banner, repeats every 5 s
 *   #ERR,<message>                    init failed
 *   ax,ay,az,gx,gy,gz,mx,my,mz,temp   g, deg/s, uT, degC
 *
 * The scale factors in the banner are 1.0 because this sketch already emits
 * g and deg/s; the host divides by them, so the division is a no-op. The
 * host reads only the first six fields - mag and temperature are logged for
 * later use (magnetometer calibration, gyro bias vs temperature) and are
 * ignored for now.
 */

#include <Wire.h>
#include "ICM_20948.h"

constexpr uint32_t SERIAL_BAUD = 115200;
constexpr uint32_t STREAM_HZ   = 100;
constexpr uint32_t STREAM_US   = 1000000UL / STREAM_HZ;
constexpr uint32_t BANNER_MS   = 5000;

ICM_20948_I2C imu;

bool     imuReady    = false;
uint8_t  imuAddress  = 0x69;
uint32_t lastBanner  = 0;
uint32_t lastSample  = 0;
uint32_t lastRetry   = 0;

bool beginImu() {
  imu.begin(Wire, true);                // AD0 high -> 0x69
  if (imu.status == ICM_20948_Stat_Ok) {
    imuAddress = 0x69;
    return true;
  }

  delay(20);
  imu.begin(Wire, false);               // AD0 low -> 0x68
  if (imu.status == ICM_20948_Stat_Ok) {
    imuAddress = 0x68;
    return true;
  }
  return false;
}

void printBanner() {
  // Host parses: #IMU,<part>,<accel LSB per g>,<gyro LSB per dps>,<addr>
  Serial.print(F("#IMU,ICM20948,1.0,1.0,0x"));
  Serial.println(imuAddress, HEX);
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  while (!Serial) { ; }                 // native-USB boards (Leonardo, Zero)

  Wire.begin();
  Wire.setClock(400000);
  delay(100);

  imuReady = beginImu();
  if (imuReady) {
    printBanner();
  } else {
    Serial.print(F("#ERR,ICM-20948 not found at 0x69 or 0x68: "));
    Serial.println(imu.statusString());
  }
  lastBanner = millis();
  lastRetry  = millis();
}

void loop() {
  // Keep retrying rather than halting, so reseating a loose wire recovers
  // without a reset.
  if (!imuReady) {
    if (millis() - lastRetry > 2000) {
      lastRetry = millis();
      imuReady = beginImu();
      if (imuReady) printBanner();
    }
    return;
  }

  if (millis() - lastBanner > BANNER_MS) {
    lastBanner = millis();
    printBanner();
  }

  // Decimate to a fixed rate. The sensor's own output rate can outrun
  // 115200 baud, and a backed-up serial buffer means the host is filtering
  // stale samples without any sign that it is.
  if (micros() - lastSample < STREAM_US) return;
  lastSample = micros();

  if (!imu.dataReady()) return;
  imu.getAGMT();

  Serial.print(imu.accX() / 1000.0f, 4);   // library reports milli-g
  Serial.print(',');
  Serial.print(imu.accY() / 1000.0f, 4);
  Serial.print(',');
  Serial.print(imu.accZ() / 1000.0f, 4);
  Serial.print(',');
  Serial.print(imu.gyrX(), 3);             // deg/s
  Serial.print(',');
  Serial.print(imu.gyrY(), 3);
  Serial.print(',');
  Serial.print(imu.gyrZ(), 3);
  Serial.print(',');
  Serial.print(imu.magX(), 2);             // uT
  Serial.print(',');
  Serial.print(imu.magY(), 2);
  Serial.print(',');
  Serial.print(imu.magZ(), 2);
  Serial.print(',');
  Serial.println(imu.temp(), 2);           // degC, on-die sensor
}
// Built by Raneem
