import socket
import struct
import pygame
import sys
import colorsys
from math import exp2

# --- CONFIGURATION ---
UDP_IP = "0.0.0.0"
UDP_PORT = 5005
MAX_DISTANCE = 2000  # mm
EXPECTED_SIZE = 133  # 1 (Length) + 4 (Timestamp) + 128 (64 * 2 bytes)

# --- UI CONSTANTS ---
GRID_COLS, GRID_ROWS = 8, 8
CELL_SIZE = 70
MARGIN = 40
HEADER_HEIGHT = 20
FOOTER_HEIGHT = 100

WIDTH = (GRID_COLS * CELL_SIZE) + (MARGIN * 2)
HEIGHT = HEADER_HEIGHT + (GRID_ROWS * CELL_SIZE) + FOOTER_HEIGHT + (MARGIN * 2)

# Colors
BG_COLOR = (30, 30, 34)
TEXT_COLOR = (220, 220, 220)
EMPTY_CELL_COLOR = (50, 50, 55)


def get_cell_color(dist_mm):
    """
    Maximum Contrast Depth Map for 50-600mm range.
    Uses continuous HSV (Hue, Saturation, Value) math instead of stops.
    """
    MIN_GESTURE_DIST = 100
    MAX_GESTURE_DIST = 1200

    # 1. Handle Out-of-Bounds
    if dist_mm == 0 or dist_mm > 4000:
        return (10, 10, 15)  # Pitch black for no data
    if dist_mm > MAX_GESTURE_DIST:
        return (25, 25, 35)  # Very dark grey/blue for background

    # 2. Normalize Depth (0.0 to 1.0)
    val = max(MIN_GESTURE_DIST, min(dist_mm, MAX_GESTURE_DIST))
    ratio = (val - MIN_GESTURE_DIST) / float(MAX_GESTURE_DIST - MIN_GESTURE_DIST)

    # 3. CONTINUOUS HUE SWEEP
    # We map the ratio directly to a Hue on the color wheel.
    # We sweep from Hue 0.85 (Magenta/Pink - Close) down to Hue 0.35 (Green - Far).
    # Because we use 50% of the entire color wheel for just 550mm, 
    # a 50mm shift will result in a massive color jump (e.g., Blue to Cyan).
    hue = 0.85 - (ratio * 0.50) 
    
    # 4. SATURATION & BRIGHTNESS
    saturation = 1.0
    brightness = 1.0

    # Make the absolute closest objects 'glow' white
    if ratio < 0.1: 
        saturation = ratio * 10.0 # Fades from 0.0 (White) to 1.0 (Full Color)

    # 6. Convert HSV back to RGB for Pygame
    r, g, b = colorsys.hsv_to_rgb(hue, saturation, brightness)
    
    return (int(r * 255), int(g * 255), int(b * 255))

def get_text_color_for_bg(bg_color):
    """ Return black or white text depending on the luminance of the background. """
    r, g, b = bg_color
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return (20, 20, 20) if luminance > 128 else (240, 240, 240)

def main():
    # Initialize Pygame
    pygame.init()
    flags = pygame.DOUBLEBUF
    screen = pygame.display.set_mode((WIDTH, HEIGHT), flags, vsync=1)
    pygame.display.set_caption("ToF 8x8 Lidar Viewer")
    clock = pygame.time.Clock()

    # Fonts
    font_large = pygame.font.SysFont("segoeui, arial", 24, bold=True)
    font_small = pygame.font.SysFont("segoeui, arial", 16)
    font_cell  = pygame.font.SysFont("segoeui, arial", 16, bold=True)

    # Initialize UDP Socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.setblocking(False)  # Non-blocking so our UI loop never freezes
    #sock.settimeout(0.001)

    # State variables
    timestamp_ns = 0
    resolution = 0
    d_matrix = [0] * 64
    has_data = False

    running = True
    while running:
        # 1. Handle Window Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        # 2. Read UDP Data (Drain buffer to get the latest packet)
        packet_data = None
        try:
            while True:
                packet_data, addr = sock.recvfrom(1024)
        except BlockingIOError:
            pass # No more data in the socket buffer
        #except TimeoutError:
        #    pass

        # 3. Parse Data
        try:
            if packet_data:
                # Format: < (Little Endian), B (1 byte), I (32 bytes), Q (8 bytes), 64H (64 x 2-byte unsigned shorts)
                unpacked = struct.unpack('<Q H H I B B I 64H', packet_data)
                timestamp_ns = unpacked[0]
                reading_count = unpacked[1]
                # total 6 bytes padding
                padding1 = unpacked[2]
                padding2 = unpacked[3]
                shift = unpacked[4]
                resolution = unpacked[5]
                timestamp_delta = unpacked[6]
                d_matrix = list(unpacked[7:])
                has_data = True
                # convert data to meter, then mm
                for i in range(len(d_matrix)):
                    d_matrix[i] = (float(d_matrix[i]) / exp2(15-shift)) * 1000
        except struct.error as e:
            print(e, 'but got instead:', len(packet_data))

        # 4. Render UI
        screen.fill(BG_COLOR)

        # Draw Grid
        grid_start_y = MARGIN + HEADER_HEIGHT
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                idx = row * GRID_COLS + col
                val = d_matrix[idx] if has_data else 0
                
                cell_bg = get_cell_color(val) if has_data else EMPTY_CELL_COLOR
                x = MARGIN + col * CELL_SIZE
                y = grid_start_y + row * CELL_SIZE
                
                # Draw rounded rectangle for the cell
                rect = pygame.Rect(x, y, CELL_SIZE - 4, CELL_SIZE - 4)
                pygame.draw.rect(screen, cell_bg, rect, border_radius=8)

                # Draw distance text inside cell
                if has_data:
                    pass
                    #cell_text_color = get_text_color_for_bg(cell_bg)
                    #txt_surface = font_cell.render(str(int(round(val/10.0, 0))), True, cell_text_color)
                    #txt_rect = txt_surface.get_rect(center=rect.center)
                    #screen.blit(txt_surface, txt_rect)

        # Draw Footer Text
        footer_y = grid_start_y + (GRID_ROWS * CELL_SIZE) + 20
        
        if has_data:
            len_text = font_large.render(f"last zone count: {resolution}", True, TEXT_COLOR)
            ts_text = font_large.render(f"Timestamp: {timestamp_ns/1e9:.1f}", True, TEXT_COLOR)
        else:
            len_text = font_large.render("Waiting for data...", True, (200, 100, 100))
            ts_text = font_large.render(f"Listening on UDP {UDP_PORT}", True, TEXT_COLOR)

        screen.blit(len_text, (MARGIN, footer_y))
        screen.blit(ts_text, (MARGIN, footer_y + 35))

        # Update Display
        pygame.display.flip()
        clock.tick(120) # Cap at 60 FPS

    sock.close()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()