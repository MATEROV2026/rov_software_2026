/*
 * imu_stream.ino — raw IMU streamer for the ROV calibration bench.
 *
 * Streams raw accelerometer and gyroscope counts over USB serial so the
 * tuning page (imu_live.html) can apply calibration and attitude filtering
 * on the host. No maths happens here on purpose: keeping the model in one
 * place means what you tune is exactly what ships to the ROS node.
 *
 * Supports ICM-20649 (WHO_AM_I 0xE1) and ICM-20948 (0xEA). They share a
 * register map but differ by exactly 2x in full-scale at the same FS_SEL,
 * so the part is detected at boot and the scale factors are reported in
 * the banner line.
 *
 * Wiring (I2C):
 *   IMU VCC -> 3.3V        IMU SDA -> SDA (A4 on Uno/Nano, 20 on Mega)
 *   IMU GND -> GND         IMU SCL -> SCL (A5 on Uno/Nano, 21 on Mega)
 *   AD0 low  -> address 0x68      AD0 high -> address 0x69
 *
 * Both addresses are probed at boot, so AD0 can sit either way.
 *
 * Serial protocol, 115200 baud:
 *   #IMU,<part>,<accel LSB per g>,<gyro LSB per dps>,<addr>   banner, every 5 s
 *   #ERR,<message>                                            init failed
 *   #SCAN,<addr>,...                                          every address that ACKs
 *   <ax>,<ay>,<az>,<gx>,<gy>,<gz>                             raw signed counts
 */

#include <Wire.h>

// Probed at boot: 0x68 with AD0 low, 0x69 with AD0 high.
static uint8_t IMU_ADDR = 0x68;

// Bank 0
static const uint8_t REG_BANK_SEL  = 0x7F;
static const uint8_t WHO_AM_I      = 0x00;
static const uint8_t USER_CTRL     = 0x03;
static const uint8_t LP_CONFIG     = 0x05;
static const uint8_t PWR_MGMT_1    = 0x06;
static const uint8_t PWR_MGMT_2    = 0x07;
static const uint8_t ACCEL_XOUT_H  = 0x2D;

// Bank 2
static const uint8_t GYRO_SMPLRT_DIV    = 0x00;
static const uint8_t GYRO_CONFIG_1      = 0x01;
static const uint8_t ACCEL_SMPLRT_DIV_1 = 0x10;
static const uint8_t ACCEL_SMPLRT_DIV_2 = 0x11;
static const uint8_t ACCEL_CONFIG       = 0x14;

static const uint8_t ID_ICM20649 = 0xE1;
static const uint8_t ID_ICM20948 = 0xEA;

const char *partName  = "UNKNOWN";
float accelLsbPerG    = 8192.0f;
float gyroLsbPerDps   = 65.5f;

bool imuReady = false;
unsigned long lastBanner = 0;
unsigned long lastRetry  = 0;

void writeReg(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(IMU_ADDR);
  Wire.write(reg);
  Wire.write(val);
  Wire.endTransmission();
}

uint8_t readReg(uint8_t reg) {
  Wire.beginTransmission(IMU_ADDR);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(IMU_ADDR, (uint8_t)1);
  return Wire.available() ? Wire.read() : 0;
}

void selectBank(uint8_t bank) {
  writeReg(REG_BANK_SEL, bank << 4);
}

void printBanner() {
  Serial.print(F("#IMU,"));
  Serial.print(partName);
  Serial.print(',');
  Serial.print(accelLsbPerG, 1);
  Serial.print(',');
  Serial.print(gyroLsbPerDps, 2);
  Serial.print(F(",0x"));
  Serial.println(IMU_ADDR, HEX);
}

// Does anything acknowledge at this address?
bool acks(uint8_t addr) {
  Wire.beginTransmission(addr);
  return Wire.endTransmission() == 0;
}

// Walk the bus and report everything that answers, so a wiring fault is
// distinguishable from a wrong address.
void scanBus() {
  Serial.print(F("#SCAN"));
  bool any = false;
  for (uint8_t a = 0x08; a < 0x78; a++) {
    if (acks(a)) { Serial.print(F(",0x")); Serial.print(a, HEX); any = true; }
  }
  if (!any) Serial.print(F(",none"));
  Serial.println();
}

bool initIMU() {
  // The IMU sits at 0x68 with AD0 low, 0x69 with AD0 high. Take whichever
  // answers; several breakouts (SparkFun's ICM-20948 among them) ship high.
  uint8_t found = 0;
  if (acks(0x68)) found = 0x68;
  else if (acks(0x69)) found = 0x69;

  if (!found) {
    Serial.println(F("#ERR,no device acknowledges at 0x68 or 0x69"));
    scanBus();
    return false;
  }
  IMU_ADDR = found;

  selectBank(0);
  writeReg(PWR_MGMT_1, 0x80);     // reset
  delay(100);
  selectBank(0);
  writeReg(PWR_MGMT_1, 0x01);     // wake, auto clock source
  writeReg(PWR_MGMT_2, 0x00);     // all axes on
  writeReg(LP_CONFIG, 0x00);      // no duty cycling
  writeReg(USER_CTRL, 0x00);      // I2C master off
  delay(50);

  uint8_t who = 0;
  for (uint8_t attempt = 0; attempt < 5 && who == 0; attempt++) {
    selectBank(0);
    who = readReg(WHO_AM_I);
    if (who == 0) delay(20);
  }

  if (who == ID_ICM20649) {
    partName = "ICM20649";
    accelLsbPerG = 8192.0f;       // +/-4 g  at ACCEL_FS_SEL = 0
    gyroLsbPerDps = 65.5f;        // +/-500 dps at GYRO_FS_SEL = 0
  } else if (who == ID_ICM20948) {
    partName = "ICM20948";
    accelLsbPerG = 16384.0f;      // +/-2 g  at ACCEL_FS_SEL = 0
    gyroLsbPerDps = 131.0f;       // +/-250 dps at GYRO_FS_SEL = 0
  } else {
    Serial.print(F("#ERR,device at 0x"));
    Serial.print(IMU_ADDR, HEX);
    Serial.print(F(" returned WHO_AM_I 0x"));
    Serial.print(who, HEX);
    Serial.println(F(" (expected 0xE1 ICM-20649 or 0xEA ICM-20948)"));
    scanBus();
    return false;
  }

  selectBank(2);
  writeReg(GYRO_SMPLRT_DIV, 9);        // ~110 Hz
  writeReg(ACCEL_SMPLRT_DIV_1, 0x00);
  writeReg(ACCEL_SMPLRT_DIV_2, 9);
  writeReg(GYRO_CONFIG_1, 0x01);       // DLPF on, lowest full-scale
  writeReg(ACCEL_CONFIG, 0x01);        // DLPF on, lowest full-scale
  delay(50);
  selectBank(0);

  printBanner();
  return true;
}

void setup() {
  Serial.begin(115200);
  while (!Serial) { ; }           // needed on native-USB boards (Leonardo, Zero)

  Wire.begin();
  Wire.setClock(100000);          // 100 kHz tolerates long or unshielded leads

  imuReady = initIMU();
  lastBanner = millis();
  lastRetry  = millis();
}

int16_t be16(uint8_t hi, uint8_t lo) {
  return (int16_t)((uint16_t)hi << 8 | lo);
}

void loop() {
  uint8_t buf[12];

  // Nothing usable on the bus: keep retrying rather than streaming zeros,
  // so plugging a loose wire back in recovers without a reset.
  if (!imuReady) {
    if (millis() - lastRetry > 2000) {
      lastRetry = millis();
      imuReady = initIMU();
    }
    return;
  }

  Wire.beginTransmission(IMU_ADDR);
  Wire.write(ACCEL_XOUT_H);
  Wire.endTransmission(false);
  Wire.requestFrom(IMU_ADDR, (uint8_t)12);
  if (Wire.available() < 12) return;
  for (uint8_t i = 0; i < 12; i++) buf[i] = Wire.read();

  int16_t ax = be16(buf[0],  buf[1]);
  int16_t ay = be16(buf[2],  buf[3]);
  int16_t az = be16(buf[4],  buf[5]);
  int16_t gx = be16(buf[6],  buf[7]);
  int16_t gy = be16(buf[8],  buf[9]);
  int16_t gz = be16(buf[10], buf[11]);

  Serial.print(ax); Serial.print(',');
  Serial.print(ay); Serial.print(',');
  Serial.print(az); Serial.print(',');
  Serial.print(gx); Serial.print(',');
  Serial.print(gy); Serial.print(',');
  Serial.println(gz);

  if (millis() - lastBanner > 5000) {
    printBanner();
    lastBanner = millis();
  }

  delay(9);   // ~100 Hz
}
