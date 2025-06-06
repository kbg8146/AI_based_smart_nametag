import socket
import json
import random
import time
import os

UDP_IP = "127.0.0.1"
UDP_PORT = 12345

file_list = ["mocking1.json", "mocking2.json"]

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

for i in range(2):
    for file_name in file_list:
        if not os.path.exists(file_name):
            print(f"File not found: {file_name}")
            continue

        with open(file_name, "r") as file:
            original_data = json.load(file)

        for repeat in range(5):
            # 깊은 복사
            data = json.loads(json.dumps(original_data))

            for beacon in data.values():
                if "rssi" in beacon:
                    original_rssi = beacon["rssi"]
                    beacon["rssi"] = original_rssi + random.randint(-10, 10)

            # 👉 source 필드 추가
            data["_source"] = file_name

            message = json.dumps(data)
            sock.sendto(message.encode(), (UDP_IP, UDP_PORT))

            print(f"[{file_name}] Sent packet {repeat+1}/5 to {UDP_IP}:{UDP_PORT}")
            for key, beacon in data.items():
                if key == "_source":
                    continue
                print(f"{key}: Name={beacon['name']}, RSSI={beacon['rssi']}")

            time.sleep(0.2)
