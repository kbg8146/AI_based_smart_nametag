import socket
import json

def process_beacon_data(data):
    A_zone_beacons = ["Beacon-A", "Beacon-D"]
    B_zone_beacons = ["Beacon-B", "Beacon-C"]

    a_rssi_values = []
    b_rssi_values = []

    for key, beacon in data.items():
        name = beacon['name']
        rssi = beacon['rssi']
        print(f"{key}: Name={name}, RSSI={rssi}")

        if name in A_zone_beacons:
            a_rssi_values.append(rssi)
        elif name in B_zone_beacons:
            b_rssi_values.append(rssi)

    avg_a_rssi = sum(a_rssi_values) / len(a_rssi_values) if a_rssi_values else None
    avg_b_rssi = sum(b_rssi_values) / len(b_rssi_values) if b_rssi_values else None

    print(f"Avg A Zone RSSI: {avg_a_rssi}")
    print(f"Avg B Zone RSSI: {avg_b_rssi}")

    if avg_a_rssi is None and avg_b_rssi is None:
        print("No valid beacons detected.")
    elif avg_a_rssi is None:
        print("Detected zone: B")
    elif avg_b_rssi is None:
        print("Detected zone: A")
    else:
        if avg_a_rssi > avg_b_rssi:
            print("Detected zone: A")
        else:
            print("Detected zone: B")

# UDP 수신기 + 실시간 계산
UDP_IP = "0.0.0.0"
UDP_PORT = 12345

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print(f"Listening on port {UDP_PORT}...")

while True:
    data, addr = sock.recvfrom(2048)
    print(f"\nReceived from {addr}: {data.decode()}")

    try:
        parsed = json.loads(data.decode())
        process_beacon_data(parsed)  # 수신 데이터 → 바로 처리
    except json.JSONDecodeError:
        print("Failed to decode JSON")

