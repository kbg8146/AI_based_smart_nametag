#include <WiFi.h>
#include <HTTPClient.h>
#include <GxEPD2_BW.h>
#include <SPI.h>

// GDEY0583T81 (5.83인치 흑백, 648x480)
GxEPD2_BW<GxEPD2_583, GxEPD2_583::HEIGHT> display(GxEPD2_583(/*CS=*/5, /*DC=*/17, /*RST=*/16, /*BUSY=*/4));

// Wi-Fi 정보
const char* ssid = "Wifi";
const char* password = "19941994";

// 서버 주소
const char* image_url = "http://192.168.72.211:8000/map.bmp";  // PC의 IP로 수정

void setup() {
  Serial.begin(115200);
  SPI.begin(18, 19, 23);  // SCK, MISO, MOSI (보통 기본값 사용)

  display.init();
  Serial.println("디스플레이 초기화 완료");

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(500);
  }
  Serial.println("\n✅ Wi-Fi 연결 성공");

  HTTPClient http;
  http.begin(image_url);
  int httpCode = http.GET();

  if (httpCode == 200) {
    Serial.println("✅ BMP 다운로드 성공");
    WiFiClient* stream = http.getStreamPtr();
    drawBMPFromStream(stream);
  } else {
    Serial.print("❌ 다운로드 실패: ");
    Serial.println(httpCode);
  }

  http.end();
}

void loop() {
  // 필요 시 반복 표시
}

void drawBMPFromStream(WiFiClient* stream) {
  uint8_t header[54];
  stream->readBytes(header, 54);

  int width = header[18] + (header[19] << 8);
  int height = header[22] + (header[23] << 8);
  Serial.printf("BMP 해상도: %d x %d\n", width, height);

  // Color Table 1024바이트 스킵 (8-bit BMP)
  for (int i = 0; i < 1024; i++) stream->read();

  display.setRotation(0);
  display.firstPage();
  do {
    for (int y = height - 1; y >= 0; y--) {
      for (int x = 0; x < width; x++) {
        uint8_t pixelIndex;
        stream->readBytes(&pixelIndex, 1);
        bool isBlack = pixelIndex < 128;
        display.drawPixel(x, y, isBlack ? GxEPD_BLACK : GxEPD_WHITE);
      }
    }
  } while (display.nextPage());

  Serial.println("✅ 이미지 표시 완료");
}
