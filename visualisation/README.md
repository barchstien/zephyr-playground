# ToF Lidar 8x8 Live Viewer

A real-time UDP visualizer for 8x8 Time-of-Flight (ToF) Lidar sensor data. 

It listens for UDP packets (expected size: 137 bytes) formatted as:
- `1 byte`: Length
- `8 bytes`: Timestamp (unsigned 64-bit integer)
- `128 bytes`: 64 x 2-byte values (8x8 matrix of unsigned 16-bit integers, representing distance in mm).

Distances are dynamically colored:
- **0 mm** = Red (Close)
- **2000 mm** = Yellow (Medium)
- **4000+ mm** = Green (Far)

## Prerequisites

- Python 3.7+
- `pip`

## Installation

Install the required visualization library (`pygame`):

```bash
python3 -m venv ./.venv
source .venv/bin/activate
pip install pygame
```