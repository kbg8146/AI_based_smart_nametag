#include <BLEDevice.h>
#include <BLEServer.h>

void setup() {
  Serial.begin(115200);
  BLEDevice::init("ESP32_Advertiser");

  BLEServer *pServer = BLEDevice::createServer();
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();

  // ▶ 광고 인터벌 설정 (200ms = 320 x 0.625ms)
  pAdvertising->setMinInterval(0x0140);  // 320
  pAdvertising->setMaxInterval(0x0140);  // 고정 주기

  pAdvertising->start();
  Serial.println("Advertising started with 200ms interval...");
}

void loop() {
  delay(2000);  // 메인 루프는 단순 대기
}
