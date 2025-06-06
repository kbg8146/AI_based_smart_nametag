#include <GxEPD2_BW.h>
#include <SPI.h>
#include <FS.h>
#include <SPIFFS.h>
// GxEPD2_3C는 흑백 디스플레이에서는 필요하지 않을 수 있습니다.
// <GxEPD_BitmapExamples.h>는 더 이상 사용하지 않으므로 제거합니다.

#define EPD_CS   5
#define EPD_DC   17
#define EPD_RST  16
#define EPD_BUSY 4

// 사용하는 디스플레이 모델에 맞게 정확한 클래스를 사용해야 합니다.
// GxEPD2_583_GDEQ0583T31은 5.83인치 흑백 디스플레이입니다.
GxEPD2_BW<GxEPD2_583_GDEQ0583T31, GxEPD2_583_GDEQ0583T31::HEIGHT> display(GxEPD2_583_GDEQ0583T31(EPD_CS, EPD_DC, EPD_RST, EPD_BUSY));

// BMP 파일에서 픽셀을 읽어와 디스플레이에 그리는 함수
// 이 함수는 24비트 비압축 BMP 파일에 최적화되어 있습니다.
// 흑백 디스플레이이므로 픽셀 데이터를 흑백으로 변환하여 그립니다.
void drawBMP(File &bmpFile, int16_t x, int16_t y) {
  if (!bmpFile) {
    Serial.println("BMP 파일이 유효하지 않습니다.");
    return;
  }

  uint32_t bmpReadHeader;
  bmpFile.readBytes((char *)&bmpReadHeader, sizeof(bmpReadHeader)); // 'BM' 매직 넘버 (2 bytes) + 파일 크기 (4 bytes) + 예약 (4 bytes) + 데이터 오프셋 (4 bytes)
  if (bmpReadHeader != 0x4D42) { // 'BM' ASCII 값 (Little-endian)
    Serial.println("BMP 파일이 아닙니다. (매직 넘버 오류)");
    bmpFile.close();
    return;
  }

  // BMP 파일 헤더 정보 읽기
  bmpFile.seek(0x0A); // 데이터 오프셋 위치로 이동 (헤더 시작점부터 10번째 바이트)
  uint32_t dataOffset;
  bmpFile.readBytes((char *)&dataOffset, sizeof(dataOffset));

  bmpFile.seek(0x12); // 이미지 폭 (width) 위치로 이동
  int32_t bmpWidth;
  bmpFile.readBytes((char *)&bmpWidth, sizeof(bmpWidth));

  bmpFile.seek(0x16); // 이미지 높이 (height) 위치로 이동
  int32_t bmpHeight;
  bmpFile.readBytes((char *)&bmpHeight, sizeof(bmpHeight));

  bmpFile.seek(0x1C); // 비트 깊이 (bits per pixel) 위치로 이동
  uint16_t bitsPerPixel;
  bmpFile.readBytes((char *)&bitsPerPixel, sizeof(bitsPerPixel));

  // 24비트 비압축 BMP인지 확인 (다른 형식은 지원하지 않음)
  if (bitsPerPixel != 24) {
    Serial.printf("지원되지 않는 BMP 형식 (bitsPerPixel: %d). 24비트 비압축 BMP를 사용하세요.\n", bitsPerPixel);
    bmpFile.close();
    return;
  }

  // BMP 픽셀 데이터 시작 위치로 이동
  bmpFile.seek(dataOffset);

  // BMP 이미지는 아래에서 위로 그려지므로 역순으로 처리
  int16_t rowBytes = ((bmpWidth * bitsPerPixel + 31) / 32) * 4; // 각 라인의 바이트 수 (4바이트 정렬)

  // 픽셀 버퍼 (한 줄을 읽기 위한 버퍼)
  uint8_t *rowBuffer = (uint8_t *)malloc(rowBytes);
  if (!rowBuffer) {
    Serial.println("메모리 할당 실패!");
    return;
  }

  for (int16_t row = 0; row < bmpHeight; row++) {
    // BMP는 아래에서 위로 그려지므로 디스플레이에 맞게 조정
    int16_t yPos = y + (bmpHeight - 1 - row);
    
    // 파일에서 한 줄의 픽셀 데이터를 읽어옴
    bmpFile.readBytes((char *)rowBuffer, rowBytes);

    for (int16_t col = 0; col < bmpWidth; col++) {
      // 24비트 BMP: BGR 형식
      uint8_t b = rowBuffer[col * 3 + 0];
      uint8_t g = rowBuffer[col * 3 + 1];
      uint8_t r = rowBuffer[col * 3 + 2];

      // RGB를 그레이스케일로 변환 (간단한 방법)
      // 그레이스케일 값이 특정 임계값보다 작으면 검정, 크면 흰색으로 변환
      uint16_t gray = (r * 299 + g * 587 + b * 114) / 1000;
      
      // 임계값 설정 (조정 가능)
      if (gray < 128) { // 어두운 색은 검정
        display.drawPixel(x + col, yPos, GxEPD_BLACK);
      } else { // 밝은 색은 흰색
        display.drawPixel(x + col, yPos, GxEPD_WHITE);
      }
    }
  }
  free(rowBuffer);
  Serial.println("BMP 이미지 그리기 완료");
}


void setup()
{
  Serial.begin(115200);
  delay(100);

  // SPI 설정
  SPI.begin(18, -1, 23, 5);  // SCK, MISO, MOSI, SS

  // 디스플레이 초기화
  display.init();
  display.setRotation(1);

  // SPIFFS 마운트
  if (!SPIFFS.begin(true)) {
    Serial.println("SPIFFS 마운트 실패!");
    return;
  }

  // BMP 이미지 열기
  File bmpFile = SPIFFS.open("/tiger_320x200x24.bmp", "r");
  if (!bmpFile) {
    Serial.println("BMP 파일을 열 수 없습니다! 파일이 SPIFFS에 업로드되었는지 확인하세요.");
    return;
  }

  // 화면 초기화 후 이미지 출력
  display.firstPage();
  do {
    display.fillScreen(GxEPD_WHITE);
    drawBMP(bmpFile, 0, 0); // 새로 구현한 drawBMP 함수 호출
  } while (display.nextPage());

  bmpFile.close();
  Serial.println("이미지 출력 완료");
}

void loop() {
  // 반복 없음
}
