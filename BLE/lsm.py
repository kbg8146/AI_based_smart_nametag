# 최소제곱법
import json
import numpy as np
import glob
import os

# 비콘 실제 좌표 (m 단위)
beacon_locations = {
    "AA:BB:CC:11:22:33": (0, 0),
    "AA:BB:CC:11:22:34": (5, 0),
    "AA:BB:CC:11:22:35": (2.5, 5),
    "AA:BB:CC:11:22:36": (0, 5),
    "AA:BB:CC:11:22:37": (5, 5),
}

# RSSI → 거리 변환 (실내 보정 버전)
def rssi_to_distance(rssi, tx_power=-65, n=3.0):
    return 10 ** ((tx_power - rssi) / (10 * n))

# 최소제곱법
def least_squares_trilateration(positions, distances):
    if len(positions) < 3:
        return None

    A = []
    b = []
    x0, y0 = positions[0]
    d0 = distances[0]

    for i in range(1, len(positions)):
        xi, yi = positions[i]
        di = distances[i]

        A.append([2 * (xi - x0), 2 * (yi - y0)])
        b.append((d0 ** 2 - di ** 2) - (x0 ** 2 - xi ** 2) - (y0 ** 2 - yi ** 2))

    A = np.array(A)
    b = np.array(b)

    try:
        result = np.linalg.lstsq(A, b, rcond=None)[0]
        return tuple(result)
    except np.linalg.LinAlgError:
        return None

# === 모든 filtered_mocking*.json 처리 ===
for filepath in glob.glob("filter/filtered_mocking*.json"):
    filename = os.path.basename(filepath)
    source = filename.replace("filtered_", "").replace(".json", "")  # mocking1, mocking2

    with open(filepath, "r") as f:
        rssi_data = json.load(f)

    positions = []
    distances = []

    print(f"\n🧭 [Source: {source}]")

    for full_key, rssi in rssi_data.items():
        try:
            _, mac = full_key.split("_", 1)
            if mac in beacon_locations and rssi > -85:
                distance = rssi_to_distance(rssi)
                print(f"🔎 {mac}: RSSI = {rssi} → 거리 = {distance:.2f}m")
                positions.append(beacon_locations[mac])
                distances.append(distance)
        except ValueError:
            continue

    if len(positions) >= 3:
        result = least_squares_trilateration(positions, distances)
        if result:
            x, y = result
            if abs(x) > 50 or abs(y) > 50:
                print(f"⚠️ 비정상 위치 추정: x = {x:.2f}, y = {y:.2f} (오차 가능성)")
            else:
                print(f"📍 최소제곱법 추정 위치: x = {x:.2f} m, y = {y:.2f} m")
        else:
            print("❌ 최소제곱법 계산 실패")
    else:
        print("❌ 사용 가능한 비콘 수 부족 (RSSI 필터링 후)")
