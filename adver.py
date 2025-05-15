import socket
import json
import random
import time
import os

UDP_IP = "127.0.0.1"
UDP_PORT = 12345

# 순차 송신할 JSON 파일 리스트
file_list = ["mocking1.json", "mocking2.json"]

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

for i in range(2): 
    for file_name in file_list:
        # 파일 존재 여부 확인
        if not os.path.exists(file_name):
            print(f"File not found: {file_name}")
            continue

        # JSON 읽기
        with open(file_name, "r") as file:
            data = json.load(file)

        # RSSI 랜덤 덮어쓰기
        for beacon in data.values():
            beacon["rssi"] = random.randint(-90, -50)

        # UDP 송신
        message = json.dumps(data)
        sock.sendto(message.encode(), (UDP_IP, UDP_PORT))

        print(f"Sent {file_name} with random RSSI to {UDP_IP}:{UDP_PORT}")
        for key, beacon in data.items():
            print(f"{key}: Name={beacon['name']}, RSSI={beacon['rssi']}")

        time.sleep(2)  # 2초 간격 송신

