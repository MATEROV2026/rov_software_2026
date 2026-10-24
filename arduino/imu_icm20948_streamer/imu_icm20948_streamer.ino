#include <Wire.h>
#include "ICM_20948.h"

constexpr uint32_t SERIAL_BAUD = 115200;
ICM_20948_I2C imu;

bool beginImu() {
  imu.begin(Wire, true);  // AD0 high: I2C address 0x69
  if (imu.status == ICM_20948_Stat_Ok) {
    return true;
  }

  delay(20);
  imu.begin(Wire, false); // AD0 low: I2C address 0x68
  return imu.status == ICM_20948_Stat_Ok;
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  Wire.begin();
  Wire.setClock(400000);
  delay(100);

  if (!beginImu()) {
    Serial.print(F("# ICM-20948 initialization failed: "));
    Serial.println(imu.statusString());
    while (true) {
      delay(1000);
    }
  }
  Serial.println(F("# ICM-20948 ready; CSV is ax,ay,az in g then gx,gy,gz in deg/s"));
}

void loop() {
  if (!imu.dataReady()) {
    return;
  }

  imu.getAGMT();
  Serial.print(imu.accX() / 1000.0f, 4); // SparkFun reports acceleration in milli-g
  Serial.print(',');
  Serial.print(imu.accY() / 1000.0f, 4);
  Serial.print(',');
  Serial.print(imu.accZ() / 1000.0f, 4);
  Serial.print(',');
  Serial.print(imu.gyrX(), 4);          // SparkFun reports angular rate in degrees/second
  Serial.print(',');
  Serial.print(imu.gyrY(), 4);
  Serial.print(',');
  Serial.println(imu.gyrZ(), 4);
}

// Built by Raneem Mousa
