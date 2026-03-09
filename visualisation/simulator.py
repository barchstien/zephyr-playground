import socket
import struct
import time
import math

# --- CONFIGURATION ---
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
FPS = 15  # How many packets to send per second

def main():
    print(f"Starting simulated ToF sensor stream to {UDP_IP}:{UDP_PORT}...")
    print("Press Ctrl+C to stop.")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Initial dummy timestamp
    timestamp = 10000
    frame_count = 0

    try:
        while True:
            # 1. Create a dynamic pattern for the 8x8 matrix (64 values)
            # We use a sine wave based on time to make the 'lidar' look alive
            matrix = []
            frame_count += 0.1
            
            for y in range(8):
                for x in range(8):
                    # Create a "blob" that moves around the grid
                    val = 2000 + 1500 * math.sin(x/2.0 + frame_count) * math.cos(y/2.0 + frame_count)
                    # Ensure it's within 0-4000 range and an integer
                    matrix.append(int(max(0, min(4000, val))))

            # 2. Pack the data
            # Format string:
            # < : Little-endian
            # B : 1 byte (Length)
            # Q : 8 bytes (Unsigned 64-bit Timestamp)
            # 64H : 64 unsigned shorts (2 bytes each)
            
            # Packet size: 1 + 8 + (64 * 2) = 137 bytes
            #packet_len = 137 
            packet = struct.pack('<B I 64H', int(64), timestamp, *matrix)

            # 3. Send via UDP
            sock.sendto(packet, (UDP_IP, UDP_PORT))

            # 4. Increment state
            timestamp += 66 # roughly 15fps in ms
            time.sleep(1/FPS)

    except KeyboardInterrupt:
        print("\nSimulator stopped.")
    finally:
        sock.close()

if __name__ == "__main__":
    main()