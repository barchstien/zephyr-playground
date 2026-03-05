import socket
import struct
import pygame
import sys

# --- CONFIGURATION ---
UDP_IP = "0.0.0.0"
UDP_PORT = 5005
MAX_DISTANCE = 4000  # mm
EXPECTED_SIZE = 137  # 1 (Length) + 8 (Timestamp) + 128 (64 * 2 bytes)

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
    last_length = 0
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
        except BlockingIOError:
            pass # No more data in the socket buffer

        # 3. Parse Data
        if packet_data:
            # Format: < (Little Endian), B (1 Byte), Q (8 Bytes), 64H (64 x 2-byte unsigned shorts)
            unpacked = struct.unpack('<B Q 64H', packet_data)
            last_length = unpacked[0]
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
                
                cell_bg = get_cell_color(val) if has_data else EMPTY_CELL_COLOR
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
            len_text = font_large.render(f"Packet Length: {last_length} bytes", True, TEXT_COLOR)
            ts_text = font_large.render(f"Timestamp: {last_timestamp}", True, TEXT_COLOR)
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