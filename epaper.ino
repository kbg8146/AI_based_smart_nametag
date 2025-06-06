#include <WiFi.h>
#include <WiFiUdp.h>
#include <BLEDevice.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>

const char* target_ssid = "T6";
const char* target_password = "19941994";

const char* udpAddress = "192.168.72.160";
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
        Serial.println("❌ Target SSID not found.");
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
        Serial.println("\n✅ WiFi connected!");
        Serial.print("📡 IP address: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\n❌ Failed to connect.");
    }
}

void setup() {
    Serial.begin(115200);
    WiFi.mode(WIFI_STA);
    WiFi.disconnect(true);
    delay(1000);

    connectToTarget();

    BLEDevice::init("");
    pBLEScan = BLEDevice::getScan();
    pBLEScan->setActiveScan(true);
}

void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("❗ WiFi disconnected. Trying again...");
        connectToTarget();
        delay(3000);
        return;
    }

    for (int round = 0; round < SCAN_REPEAT_COUNT; round++) {
        BeaconData beacons[MAX_DEVICES];
        int beaconCount = 0;

        Serial.printf("📡 BLE scanning (%d/%d)...\n", round + 1, SCAN_REPEAT_COUNT);
        BLEScanResults* results = pBLEScan->start(SCAN_DURATION_MS / 1000, false);
        Serial.printf("📦 Found %d BLE devices\n", results->getCount());

        for (int i = 0; i < results->getCount() && beaconCount < MAX_DEVICES; i++) {
            BLEAdvertisedDevice d = results->getDevice(i);

            if (d.haveName()) {
                String devName = String(d.getName().c_str());

                if (devName.startsWith("Beacon")) {
                    Serial.println("🔖 " + devName);  // 이름만 출력

                    BeaconData data;
                    data.name = devName;
                    data.address = d.getAddress().toString().c_str();
                    data.rssi = d.getRSSI();
                    beacons[beaconCount++] = data;
                }
            }
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

        if (beaconCount > 0) {
            Serial.println("📤 Sending: " + payload);  // 전송 확인
            udp.beginPacket(udpAddress, udpPort);
            udp.print(payload);
            udp.endPacket();
        } else {
            Serial.println("⚠️ No matching Beacon* devices found.");
        }

        delay(200);
        pBLEScan->clearResults();
    }

    delay(5000);
}
