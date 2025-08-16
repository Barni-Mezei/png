"""

Resources:
https://konvertor.vercel.app/#app

"""

import argparse
from png import *
import os
import shutil
import math
import random

# Create the parser
parser = argparse.ArgumentParser()

# Add the filename argument
parser.add_argument('filename', type=str, help='File to open and manipulate')
parser.add_argument('filename2', type=str, help='2nd file to open and manipulate')

# Parse the arguments
args = parser.parse_args()

"""
Shader utility functions
"""

def mix(value_a : float, value_b : float, mix : float) -> float:
    """
    mix:
    - 0.0 : value_a
    - 0.5 : value_a/2 + value_b/2
    - 1.0 : value_b
    """

    return (value_b * mix) + (value_a * (1 - mix))

def clamp(value : float, min : float, max : float) -> float:
    return min if value < min else (max if value > max else value)

def band(color_value : int, number_of_bands : int) -> int:
    band_size = (255 / number_of_bands)

    return round(color_value / band_size) * band_size

def wrap(value : float, min : float, max : float) -> float:
    diff = max - min

    return min + value % diff

def distance(p1 : tuple, p2 : tuple) -> float:
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]

    return math.sqrt(dx*dx + dy*dy)

def smoothstep(value : float) -> float:
    value = max(0, min(1, value))
    return value*value * (3 - value * 2)

"""
Some sahders
"""

def grayscale_shader(uv, pos, color : tuple, *args) -> tuple:
    brightness = sum(color[0:3]) / 3

    color[0] = brightness
    color[1] = brightness
    color[2] = brightness

    return color

def alpha_grayscale_shader(uv, pos, color : tuple, *args) -> tuple:
    brightness = sum(color[0:3]) / 3

    color[0] = 255
    color[1] = 255
    color[2] = 255
    color[3] = brightness

    return color

def alpha_monochrome_shader(uv, pos, color : tuple, *args) -> tuple:
    color[0] = color[3]
    color[1] = color[3]
    color[2] = color[3]

    return color

def alpha_edge_shader(uv, pos, color : tuple, *args) -> tuple:
    alpha = 1 if color[3] > 0 and color[3] < 255 else 0

    out_color = [
        alpha * 255,
        alpha * 255,
        alpha * 255,
        255
    ]

    return out_color

def blur_shader(uv, pos, color : tuple, blur_size) -> tuple:
    global color_matrix, image_meta

    BOX_SIZE = blur_size

    color_sum = [0, 0, 0, 0]

    for y in range(int(-BOX_SIZE / 2), int(BOX_SIZE / 2 + 0.5), 1):
        for x in range(int(-BOX_SIZE / 2), int(BOX_SIZE / 2 + 0.5), 1):
            pos_x = wrap(pos[0] + x, 0, image_meta["width"])
            pos_y = wrap(pos[1] + y, 0, image_meta["height"])

            pixel = color_matrix[pos_y][pos_x]

            for channel in range(4):
                color_sum[channel] += pixel[channel]

    color_count = BOX_SIZE * BOX_SIZE

    out_color = [c / color_count for c in color_sum]

    return out_color

def alpha_checkerboard_shader(uv, pos, color : tuple, patter_brightness : float = 1) -> tuple:
    GRID_SIZE = 16

    alpha = color[3] / 255

    columns = 1 if ((pos[0]) % (GRID_SIZE * 2)) >= GRID_SIZE else 0
    rows = 1 if ((pos[1]) % (GRID_SIZE * 2)) >= GRID_SIZE else 0

    grid = ((columns + rows) % 2) / 2 + 0.25
    grid = clamp(grid * patter_brightness * 255, 0, 255)

    out_color = [
        mix(grid, color[0], alpha),
        mix(grid, color[1], alpha),
        mix(grid, color[2], alpha),
        255
    ]

    return out_color


def uv_shader(uv, pos, color : tuple) -> tuple:
    blue = math.sin(uv[0] * math.pi * 5)
    blue += math.sin(uv[1] * math.cos(uv[1] * math.pi * 2))

    return [
        clamp(mix(0, 255, uv[0]), 0, 255),
        clamp(mix(0, 255, uv[1]), 0, 255),
        clamp(mix(0, 255, blue), 0, 255),
        255
    ]

def uv_warp_shader(uv, pos, color : tuple, offset) -> tuple:
    global color_matrix, image_meta
    
    uv_x = uv[0] + math.sin((pos[0] + offset) * math.pi / 180 * 3)
    uv_y = uv[1] + math.sin((pos[0] + pos[1]) * math.pi / 180 * 5)

    uv_x = uv_x * 5
    uv_y = uv_y * 5

    pos_x = wrap( int(pos[0] + uv_x), 0, image_meta["width"] )
    pos_y = wrap( int(pos[1] + uv_y), 0, image_meta["height"] )

    return color_matrix[pos_y][pos_x]

def uv_whirlpool_shader(uv, pos, color : tuple, time) -> tuple:
    global color_matrix, image_meta
    
    RADIUS = 0.75
    RING_AMOUNT = 2
    DEPTH_AMOUNT = 0.25
    SPEED = 1
    CENTER = (0.5 + math.sin(time) * 0.25, 0.5)
    #CENTER = (0.5, 0.5)

    dist = distance(uv, CENTER)

    if dist < RADIUS:
        # Calculate angle and new distance
        #angle = math.atan2(uv[1], uv[0]) + AMOUNT * (RADIUS - dist) * math.cos(time + dist * 10)
        #newDist = dist * (1.0 - (dist / RADIUS))

        new_dist = (RADIUS - dist) * DEPTH_AMOUNT
        angle = math.atan2(uv[0], uv[1]) + (RADIUS - dist) * RING_AMOUNT * (RADIUS - dist) - time * SPEED

        # Calculate new UV coordinates
        uv_x = CENTER[0] + math.cos(angle) * new_dist
        uv_y = CENTER[1] + math.sin(angle) * new_dist

        # Blend on to the original texture
        uv_x = mix(uv[0], uv_x, 1 - dist / RADIUS)
        uv_y = mix(uv[1], uv_y, 1 - dist / RADIUS)

        # return [
        #     clamp(mix(0, 255, uv_x), 0, 255),
        #     clamp(mix(0, 255, uv_y), 0, 255),
        #     0,
        #     255
        # ]

        pos_x = wrap( int(uv_x * image_meta["width"]), 0, image_meta["width"] )
        pos_y = wrap( int(uv_y * image_meta["height"]), 0, image_meta["height"] )

        return color_matrix[pos_y][pos_x]

    # return [
    #     clamp(mix(0, 255, uv[0]), 0, 255),
    #     clamp(mix(0, 255, uv[1]), 0, 255),
    #     0,
    #     255
    # ]

    return color
        

def band_shader(uv, pos, color : tuple, number_of_bands : int) -> tuple:
    return [
        band(color[0], number_of_bands),
        band(color[1], number_of_bands),
        band(color[2], number_of_bands),
        band(color[3], number_of_bands),
    ]

def band_diff_shader(uv, pos, color : tuple) -> tuple:
    return [
        color[0] - band(color[0], 8),
        color[1] - band(color[1], 8),
        color[2] - band(color[2], 8),
        color[3] - band(color[3], 8),
    ]

def mask_shader(uv, pos, color : tuple, mask_matrix : list, mask_meta : dict) -> tuple:
    """
    **Description:**

    Multiplies the original image with the mask
    
    ** Parameters:**
    - mask_matrix(list) The mask color matrix (will be repeated)
    - mask_meta(dict) The metadata from the mask image (needed for mask size)
    """

    mask_pos_x = wrap(pos[0], 0, mask_meta["width"])
    mask_pos_y = wrap(pos[1], 0, mask_meta["height"])

    mask_brightness = sum(mask_matrix[mask_pos_y][mask_pos_x][0:3]) / 3
    mask_brightness *= mask_matrix[mask_pos_y][mask_pos_x][3] / 255
    mask_brightness /= 255 # Normalise to 0 - 1

    # Move range to 0.25 - 1
    mask_brightness *= 0.75
    mask_brightness += 0.25

    return [
        clamp(color[0] * mask_brightness, 0, 255),
        clamp(color[1] * mask_brightness, 0, 255),
        clamp(color[2] * mask_brightness, 0, 255),
        color[3],
    ]


# Prepare folder
if os.path.exists("renders/"):
    shutil.rmtree("renders/")
    
    # Re-create the folder
    os.makedirs("renders/")

for i in range(1):
    # Read image data
    print("Reading...")
    image = PNG(args.filename, flags=PNG_READ)

    # Apply shader to the image
    #print("Alpha monchrome...")
    #image.shader(alpha_monochrome_shader)
    #print("Alpha edge...")
    #image.shader(alpha_edge_shader)
    #print("Blur...")
    #color_matrix = image.get_matrix()
    #image.shader(blur_shader, [3])
    #print("UV...")
    #image.shader(uv_shader)
    #print("UV warp...")
    #color_matrix = image.get_matrix()
    #image.shader(uv_whirlpool_shader, [i * 0.05])
    #print("Band...")
    #image.shader(band_shader, [2**0])
    #image.shader(alpha_monochrome_shader)
    #print("Alpha checkerboard...")

    image.print()

    image_meta = image.get_meta()
    color_matrix = image.get_matrix()
    print("Blurring...")
    
    #for current, total, percent in image.shader(blur_shader, [5], output = "yield"):
    #    print(f"Processing {current}/{total} ({percent}%)", end="\r")
    #print()
    
    image.shader(blur_shader, [5], output = "print")
    image.shader(alpha_monochrome_shader)
    #image.shader(alpha_checkerboard_shader, [0.5])

    exit()

    color_mask = image.get_matrix()
    mask_meta = image.get_meta()

    w, _ = os.get_terminal_size()
    scale = int((image_meta["width"] / w) + 1) if image_meta["width"] > w else 1
    image.print(scale)

    # Load second image
    image = PNG(args.filename2, flags=PNG_READ)

    image.shader(mask_shader, color_mask, mask_meta)

    image_meta = image.get_meta()

    w, _ = os.get_terminal_size()
    scale = int((image_meta["width"] / w) + 1) if image_meta["width"] > w else 1
    image.print(scale)

    image.write(f"renders/frame_{i:>03}.png")