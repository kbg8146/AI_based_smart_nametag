#include <SPI.h>
#include <Adafruit_PN532.h>

#define PN532_SS 5
Adafruit_PN532 nfc(PN532_SS);

void setup(void) {
  Serial.begin(115200);
  Serial.println("🚀 PN532 NFC URL 쓰기 시작");

  nfc.begin();

  uint32_t versiondata = nfc.getFirmwareVersion();
  if (!versiondata) {
    Serial.println("❌ PN532 인식 실패");
    while (1);
  }

  nfc.SAMConfig();
  Serial.println("✅ PN532 준비 완료! NTAG216 태그를 올려주세요.");
}

void loop(void) {
  if (nfc.inListPassiveTarget()) {
    Serial.println("📶 태그 감지됨. URL 쓰는 중...");

    // 정확히 맞는 길이: https://naver.com (12바이트)
    uint8_t ndef[20] = {
      0x03, 0x11,              // NDEF 메시지 총 길이 = 17
      0xD1, 0x01, 0x0D,        // NDEF 헤더
      0x55,                   // URI 타입
      0x03,                   // "https://"
      'n','a','v','e','r','.','c','o','m',
      0xFE, 0x00, 0x00, 0x00  // 종료 마커 + 패딩
    };

    // 페이지 4~8까지 총 5페이지에 걸쳐 쓰기 (20바이트)
    for (int i = 0; i < 5; i++) {
      nfc.ntag2xx_WritePage(4 + i, &ndef[i * 4]);
    }

    Serial.println("✅ URL 기록 완료! 아이폰으로 스캔해보세요.");
    delay(5000);
  }
}
