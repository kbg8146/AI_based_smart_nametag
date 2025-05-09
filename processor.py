import math

def rssi_to_distance(rssi, tx_power=-59, n=2.0):
    if rssi == 0:
        return -1.0
    ratio = (tx_power - rssi) / (10 * n)
    distance = math.pow(10, ratio)
    return round(distance, 2)

def determine_zone_by_group(devices):
    """
    비콘 그룹별로 거리를 비교해서 A존/B존 판별
    - A 그룹: Beacon_1, Beacon_4
    - B 그룹: Beacon_2, Beacon_3
    """
    a_group = []
    b_group = []

    for d in devices:
        distance = rssi_to_distance(d.rssi)
        if "Beacon_1" in d.name or "Beacon_4" in d.name:
            a_group.append(distance)
        elif "Beacon_2" in d.name or "Beacon_3" in d.name:
            b_group.append(distance)

    # 평균 계산
    a_avg = sum(a_group) / len(a_group) if a_group else float('inf')
    b_avg = sum(b_group) / len(b_group) if b_group else float('inf')

    print(f"▶ A존 그룹 평균 거리: {round(a_avg, 2)}m")
    print(f"▶ B존 그룹 평균 거리: {round(b_avg, 2)}m")

    if a_avg < b_avg:
        return "A존"
    elif b_avg < a_avg:
        return "B존"
    else:
        return "Unknown"

def process_ble_data(devices):
    """
    BLE 데이터 처리 + 개별 거리 + 그룹 존 판별
    """
    print("=== 개별 비콘 ===")
    for d in devices:
        distance = rssi_to_distance(d.rssi)
        print(f"Device: {d.name}, Address: {d.address}, RSSI: {d.rssi}, Estimated Distance: {distance}m")

    print("\n=== 존 판별 결과 ===")
    zone = determine_zone_by_group(devices)
    print(f"▶ 최종 Zone: {zone}")
