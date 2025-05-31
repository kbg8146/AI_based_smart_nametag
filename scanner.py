# scanner.py
import socket
import json

def udp_scan(udp_ip="0.0.0.0", udp_port=12345):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((udp_ip, udp_port))
    print(f"[Scanner] Listening on {udp_ip}:{udp_port}...")

    while True:
        try:
            data, addr = sock.recvfrom(4096)
            decoded = data.decode()
            parsed = json.loads(decoded)
            yield parsed
        except Exception as e:
            print(f"[Scanner] ⚠️ Error: {e}")
