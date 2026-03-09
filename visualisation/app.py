import socket
import struct
import pygame
import sys

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
    """ Map distance (0-4000) to a Red -> Yellow -> Green colormap. """
    dist = max(0, min(dist_mm, MAX_DISTANCE))
    ratio = dist / float(MAX_DISTANCE)
    
    if ratio < 0.5:
        # Red to Yellow
        r = 255
        g = int((ratio * 2) * 255)
        b = 0
    else:
        # Yellow to Green
        r = int((1.0 - (ratio - 0.5) * 2) * 255)
        g = 255
        b = 0
        
    return (r, g, b)

def get_cell_color2(dist_mm):
    """ 
    High-granularity multi-stop color mapping.
    Maps 0-4000mm to a smooth Purple -> Blue -> Green -> Yellow -> Red gradient.
    """
    # 1. Clamp distance and normalize to 0.0 - 1.0
    val = max(0, min(dist_mm, MAX_DISTANCE))
    ratio = val / float(MAX_DISTANCE)

    # 2. Define color stops (R, G, B)
    # You can tweak these to change the 'feel' of the heatmap
    colors = [
        (255, 255, 255),   # 0%   - GESTURE PEAK (Pure White Glow)
        (0, 255, 255),     # 25%  - ACTIVE ZONE (Bright Cyan)
        (0, 100, 255),     # 50%  - VISIBLE (Azure Blue)
        (70, 0, 150),      # 75%  - BACKGROUND (Deep Purple)
        (20, 20, 30)       # 100% - SLEEP (Dark Navy Grey)
    ]

    # 3. Determine which segment of the gradient we are in
    segment_float = ratio * (len(colors) - 1)
    index = int(segment_float)
    inner_ratio = segment_float - index # How far between index and index + 1

    if index >= len(colors) - 1:
        return colors[-1]

    # 4. Linear Interpolation (Lerp) between the two colors
    c1 = colors[index]
    c2 = colors[index + 1]

    r = int(c1[0] + (c2[0] - c1[0]) * inner_ratio)
    g = int(c1[1] + (c2[1] - c1[1]) * inner_ratio)
    b = int(c1[2] + (c2[2] - c1[2]) * inner_ratio)

    return (r, g, b)

def get_cell_color3(dist_mm):
    """
    High-Granularity Gesture Colormap.
    Focuses the entire color resolution on the 0-1200mm range.
    """
    # 1. SETUP THE ACTIVE WINDOW
    # Gestures happen close to the sensor. By ignoring the 'far' background,
    # we 'zoom in' on the values that matter.
    MIN_GESTURE_DIST = 50   # mm
    MAX_GESTURE_DIST = 600 # mm 

    if dist_mm == 0 or dist_mm > MAX_DISTANCE: return (20, 20, 25) # Dark Background
    if dist_mm > MAX_GESTURE_DIST: return (40, 40, 60)      # Muted Far Plane

    # 2. NORMALIZE WITHIN THE WINDOW
    # This makes 50mm a much larger percentage of the total scale.
    val = max(MIN_GESTURE_DIST, min(dist_mm, MAX_GESTURE_DIST))
    ratio = (val - MIN_GESTURE_DIST) / float(MAX_GESTURE_DIST - MIN_GESTURE_DIST)

    # 3. TURBO-INSPIRED HIGH-DENSITY GRADIENT (11 STOPS)
    # Designed to maximize 'local' contrast so 50mm changes are visible.
    # Order: Near (0.0) -> Far (1.0)
    colors = [
        (255, 255, 255), # 0.00 - Touch (White)
        (255, 0, 255),   # 0.10 - Magenta
        (180, 0, 255),   # 0.20 - Deep Purple
        (0, 0, 255),     # 0.30 - Blue
        (0, 150, 255),   # 0.40 - Sky Blue
        (0, 255, 255),   # 0.50 - Cyan
        (0, 255, 150),   # 0.60 - Teal
        (0, 255, 0),     # 0.70 - Green
        (150, 255, 0),   # 0.80 - Lime
        (255, 255, 0),   # 0.90 - Yellow
        (255, 150, 0)    # 1.00 - Orange
    ]

    # 4. Interpolate
    segment_float = ratio * (len(colors) - 1)
    idx = int(segment_float)
    inner_ratio = segment_float - idx

    if idx >= len(colors) - 1: return colors[-1]

    c1, c2 = colors[idx], colors[idx + 1]
    return (
        int(c1[0] + (c2[0] - c1[0]) * inner_ratio),
        int(c1[1] + (c2[1] - c1[1]) * inner_ratio),
        int(c1[2] + (c2[2] - c1[2]) * inner_ratio)
    )

import colorsys # Make sure to add this at the top of your file!

def get_cell_color4(dist_mm):
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
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
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

    # State variables
    last_timestamp = 0
    last_zone_cnt = 0
    last_matrix = [0] * 64
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
                data, addr = sock.recvfrom(1024)
                if len(data) == EXPECTED_SIZE:
                    packet_data = data
                    #print(data.hex(' '), '\n')
                else:
                    print('wrong length: ', len(data))
        except BlockingIOError:
            pass # No more data in the socket buffer

        # 3. Parse Data
        if packet_data:
            # Format: < (Little Endian), B (1 Byte), Q (8 Bytes), 64H (64 x 2-byte unsigned shorts)
            unpacked = struct.unpack('<B I 64H', packet_data)
            last_zone_cnt = unpacked[0]
            last_timestamp = unpacked[1]
            last_matrix = unpacked[2:]
            has_data = True

        # 4. Render UI
        screen.fill(BG_COLOR)

        # Draw Grid
        grid_start_y = MARGIN + HEADER_HEIGHT
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                idx = row * GRID_COLS + col
                val = last_matrix[idx] if has_data else 0
                
                cell_bg = get_cell_color4(val) if has_data else EMPTY_CELL_COLOR
                x = MARGIN + col * CELL_SIZE
                y = grid_start_y + row * CELL_SIZE
                
                # Draw rounded rectangle for the cell
                rect = pygame.Rect(x, y, CELL_SIZE - 4, CELL_SIZE - 4)
                pygame.draw.rect(screen, cell_bg, rect, border_radius=8)

                # Draw distance text inside cell
                if has_data:
                    cell_text_color = get_text_color_for_bg(cell_bg)
                    txt_surface = font_cell.render(str(val), True, cell_text_color)
                    txt_rect = txt_surface.get_rect(center=rect.center)
                    screen.blit(txt_surface, txt_rect)

        # Draw Footer Text
        footer_y = grid_start_y + (GRID_ROWS * CELL_SIZE) + 20
        
        if has_data:
            len_text = font_large.render(f"last zone count: {last_zone_cnt}", True, TEXT_COLOR)
            ts_text = font_large.render(f"Timestamp: {last_timestamp*0.001:.1f}", True, TEXT_COLOR)
        else:
            len_text = font_large.render("Waiting for data...", True, (200, 100, 100))
            ts_text = font_large.render(f"Listening on UDP {UDP_PORT}", True, TEXT_COLOR)

        screen.blit(len_text, (MARGIN, footer_y))
        screen.blit(ts_text, (MARGIN, footer_y + 35))

        # Update Display
        pygame.display.flip()
        clock.tick(60) # Cap at 60 FPS

    sock.close()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()