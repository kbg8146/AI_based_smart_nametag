from unittest import mock
import random
from processor import process_ble_data

def mock_ble_devices():
    devices = []

    b1 = mock.MagicMock()
    b1.name = "Beacon_1"
    b1.address = "AA:BB:CC:DD:EE:01"
    b1.rssi = -43
    devices.append(b1)

    b2 = mock.MagicMock()
    b2.name = "Beacon_2"
    b2.address = "AA:BB:CC:DD:EE:02"
    b2.rssi = -56
    devices.append(b2)

    b3 = mock.MagicMock()
    b3.name = "Beacon_3"
    b3.address = "AA:BB:CC:DD:EE:03"
    b3.rssi = -69
    devices.append(b3)

    b4 = mock.MagicMock()
    b4.name = "Beacon_4"
    b4.address = "AA:BB:CC:DD:EE:04"
    b4.rssi = -70
    devices.append(b4)

    b5 = mock.MagicMock()
    b5.name = "Beacon_5"
    b5.address = "AA:BB:CC:DD:EE:05"
    b5.rssi = -76
    devices.append(b5)

    return devices

if __name__ == "__main__":
    devices = mock_ble_devices()
    process_ble_data(devices)
