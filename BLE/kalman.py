from scanner import udp_scan
import json
import os

class KalmanFilter:
    def __init__(self, process_noise=1e-2, measurement_noise=1, estimate_error=1, initial_value=0):
        self.q = process_noise
        self.r = measurement_noise
        self.p = estimate_error
        self.x = initial_value

    def update(self, measurement):
        self.p += self.q
        k = self.p / (self.p + self.r)
        self.x += k * (measurement - self.x)
        self.p *= (1 - k)
        return self.x

kalman_filters = {}  # (source, address) → KalmanFilter

output_dir = "filter"
os.makedirs(output_dir, exist_ok=True)  # 폴더 없으면 생성

for parsed_data in udp_scan():
    source = parsed_data.get("_source", "Unknown").replace(".json", "")  # e.g. mocking1
    result_dict = {}

    for key, beacon in parsed_data.items():
        if key == "_source" or not isinstance(beacon, dict):
            continue

        rssi = beacon.get("rssi")
        address = beacon.get("address", key)
        if rssi is None:
            continue

        filter_key = (source, address)
        if filter_key not in kalman_filters:
            kalman_filters[filter_key] = KalmanFilter(initial_value=rssi)

        kalman_filters[filter_key].update(rssi)

    # === 이 source에 해당하는 값만 모아 저장 ===
    for (src, addr), filt in kalman_filters.items():
        if src == source:
            result_dict[f"{src}.json_{addr}"] = round(filt.x, 2)

    save_path = os.path.join(output_dir, f"filtered_{source}.json")
    with open(save_path, "w") as f:
        json.dump(result_dict, f, indent=2)

    print(f"✔ {source} → {save_path}에 필터 결과 저장 완료 ({len(result_dict)}개)")
