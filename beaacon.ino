#include <BLEDevice.h>
#include <BLEServer.h>

void setup() {
  Serial.begin(115200);
  
  // 📛 광고 이름 설정 (여기서 BeaconA로 설정)
  BLEDevice::init("BeaconA");

  // BLE 서버 및 광고 객체 생성
  BLEServer *pServer = BLEDevice::createServer();
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();

  // ▶ 광고 인터벌 설정 (200ms = 320 x 0.625ms)
  pAdvertising->setMinInterval(0x0140);  // 320
  pAdvertising->setMaxInterval(0x0140);

  // ✅ 광고 시작
  pAdvertising->start();
  Serial.println("📡 BLE Advertising started with name: BeaconA (interval 200ms)");
}

void loop() {
  delay(2000);  // 메인 루프는 대기
}
