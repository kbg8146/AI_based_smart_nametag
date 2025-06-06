#include <WiFi.h>

const char* target_ssid = "T6";           // 연결할 SSID
const char* target_password = "19941994"; // 비밀번호 (없으면 "")

void connectToTarget() {
  Serial.printf("🔍 Scanning for \"%s\"...\n", target_ssid);
  int n = WiFi.scanNetworks();

  bool found = false;
  for (int i = 0; i < n; ++i) {
    String ssid = WiFi.SSID(i);
    Serial.printf("  %d: %s (%ddBm)\n", i + 1, ssid.c_str(), WiFi.RSSI(i));
    if (ssid == target_ssid) {
      found = true;
    }
  }

  if (!found) {
    Serial.println("❌ Target SSID not found. Check hotspot visibility and 2.4GHz support.");
    return;
  }

  Serial.printf("✅ \"%s\" found! Connecting...\n", target_ssid);
  WiFi.begin(target_ssid, target_password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n🎉 Connected!");
    Serial.print("📡 IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n❌ Failed to connect.");
    Serial.print("WiFi status: ");
    Serial.println(WiFi.status());
  }
}

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  WiFi.disconnect(true); // 이전 연결 제거
  delay(1000);

  connectToTarget();
}

void loop() {
  // 연결 유지 여부 확인
  static unsigned long lastCheck = 0;
  if (millis() - lastCheck > 10000) {
    lastCheck = millis();
    Serial.printf("🔄 WiFi status: %d\n", WiFi.status());
  }
}
# wifi status:3 뜨면 성공
