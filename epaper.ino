#include <WiFi.h>
#include <WiFiUdp.h>
#include <BLEDevice.h>
#include <BLEScan.h>

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

const char* udpAddress = "192.168.0.100";
const int udpPort = 12345;

WiFiUDP udp;
BLEScan* pBLEScan;

#define MAX_DEVICES 5
#define SCAN_DURATION_MS 200
#define SCAN_REPEAT_COUNT 5

struct BeaconData {
    String name;
    String address;
    int rssi;
};

void setup() {
    Serial.begin(115200);
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("WiFi connected");

    BLEDevice::init("");
    pBLEScan = BLEDevice::getScan();
    pBLEScan->setActiveScan(true);
}

void loop() {
    for (int round = 0; round < SCAN_REPEAT_COUNT; round++) {
        BeaconData beacons[MAX_DEVICES];
        int beaconCount = 0;

        BLEScanResults results = pBLEScan->start(SCAN_DURATION_MS / 1000, false);

        for (int i = 0; i < results.getCount() && beaconCount < MAX_DEVICES; i++) {
            BLEAdvertisedDevice d = results.getDevice(i);
            BeaconData data;
            data.name = d.getName().c_str();
            data.address = d.getAddress().toString().c_str();
            data.rssi = d.getRSSI();
            beacons[beaconCount++] = data;
        }

        // JSON 생성
        String payload = "{";
        for (int i = 0; i < beaconCount; i++) {
            payload += "\"beacon" + String(i + 1) + "\":{";
            payload += "\"name\":\"" + beacons[i].name + "\",";
            payload += "\"address\":\"" + beacons[i].address + "\",";
            payload += "\"rssi\":" + String(beacons[i].rssi);
            payload += "}";
            if (i < beaconCount - 1) payload += ",";
        }
        payload += "}";

        // UDP 송신
        Serial.println("Sending: " + payload);
        udp.beginPacket(udpAddress, udpPort);
        udp.print(payload);
        udp.endPacket();

        // 다음 라운드까지 대기
        delay(200);
        pBLEScan->clearResults();  // 메모리 정리
    }

    delay(5000);  // 5회 송신 후 다음 루프까지 대기 (옵션)
}
