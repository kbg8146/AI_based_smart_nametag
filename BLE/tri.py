import json
import math
import itertools
import os
import glob

# 비콘 실제 위치
beacon_locations = {
    "AA:BB:CC:11:22:33": (0, 0),
    "AA:BB:CC:11:22:34": (5, 0),
    "AA:BB:CC:11:22:35": (2.5, 5),
    "AA:BB:CC:11:22:36": (0, 5),
    "AA:BB:CC:11:22:37": (5, 5),
}

# RSSI → 거리 변환 (환경 보정 가능)
def rssi_to_distance(rssi, tx_power=-65, n=3.0):
    return 10 ** ((tx_power - rssi) / (10 * n))

# 삼변측량 계산
def trilaterate(p1, d1, p2, d2, p3, d3):
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3

    A = 2 * (x2 - x1)
    B = 2 * (y2 - y1)
    C = d1**2 - d2**2 - x1**2 + x2**2 - y1**2 + y2**2
    D = 2 * (x3 - x2)
    E = 2 * (y3 - y2)
    F = d2**2 - d3**2 - x2**2 + x3**2 - y2**2 + y3**2

    denom = A * E - B * D
    if denom == 0:
        return None

    x = (C * E - F * B) / denom
    y = (A * F - C * D) / denom
    return (x, y)

# filter 폴더 내 mocking 결과 반복
for filepath in glob.glob("filter/filtered_mocking*.json"):
    filename = os.path.basename(filepath)
    source = filename.replace("filtered_", "").replace(".json", "")  # e.g., mocking1

    with open(filepath, "r") as f:
        all_data = json.load(f)

    # source별로 MAC 주소 분리
    beacons = {}
    for full_key, rssi in all_data.items():
        try:
            _, addr = full_key.split("_", 1)
            beacons[addr] = rssi
        except ValueError:
            continue

    print(f"\n🧭 [Source: {source}]")
    top5 = sorted(beacons.items(), key=lambda x: x[1], reverse=True)[:5]

    found_valid = False
    for (a1, r1), (a2, r2), (a3, r3) in itertools.combinations(top5, 3):
        if all(a in beacon_locations for a in [a1, a2, a3]):
            d1, d2, d3 = map(rssi_to_distance, [r1, r2, r3])
            result = trilaterate(beacon_locations[a1], d1,
                                 beacon_locations[a2], d2,
                                 beacon_locations[a3], d3)
            if result:
                x, y = result
                print(f"📍 삼변측량 추정 위치: x = {x:.2f} m, y = {y:.2f} m")
                found_valid = True
                break

    if not found_valid:
        print("❌ 삼변측량 실패 (모든 조합이 일직선 또는 계산 오류)")
