import argparse
from png import *
import os
import shutil
import math

# Create the parser
parser = argparse.ArgumentParser()

# Add the filename argument
parser.add_argument('filename', type=str, help='File to open and show')

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

    for y in range(BOX_SIZE):
        for x in range(BOX_SIZE):
            pos_x = wrap(pos[0] + x, 0, image_meta["width"])
            pos_y = wrap(pos[1] + y, 0, image_meta["height"])

            pixel = color_matrix[pos_y][pos_x]

            for channel in range(4):
                color_sum[channel] += pixel[channel]

    color_count = BOX_SIZE * BOX_SIZE

    out_color = [c / color_count for c in color_sum]

    return out_color

def alpha_checkerboard_shader(uv, pos, color : tuple) -> tuple:
    GRID_SIZE = 16

    alpha = color[3] / 255

    columns = 1 if ((pos[0]) % (GRID_SIZE * 2)) >= GRID_SIZE else 0
    rows = 1 if ((pos[1]) % (GRID_SIZE * 2)) >= GRID_SIZE else 0

    grid = ((columns + rows) % 2) / 2 + 0.25
    grid *= 255

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

    #if pos_x < 0 or pos_x >= image_meta["width"] or pos_y < 0 or pos_y >= image_meta["height"]:
    #    return [255, 0, 0, 255]
    #else:
    return color_matrix[pos_y][pos_x]

def band_shader(uv, pos, color : tuple, number_of_bands : int) -> tuple:
    return [
        band(color[0], number_of_bands),
        band(color[1], number_of_bands),
        band(color[2], number_of_bands),
        band(color[3], number_of_bands),
    ]


# Prepare folder
if os.path.exists("renders/"):
    shutil.rmtree("renders/")
    
    # Re-create the folder
    os.makedirs("renders/")


for i in range(23):
    # Read image data
    #print(f"Reading ({i})...")
    image = PNG(args.filename, flags=PNG_READ)

    image_meta = image.get_meta()

    # Apply shader to the image
    #print("Grayscale...")
    #image.shader(grayscale_shader)
    #print("Alpha monchrome...")
    #image.shader(alpha_monochrome_shader)
    #print("Alpha edge...")
    #image.shader(alpha_edge_shader)
    #print("Blur...")
    #color_matrix = image.get_matrix()
    #image.shader(blur_shader, 3)
    #print("UV...")
    #image.shader(uv_shader)
    #print("UV warp...")
    color_matrix = image.get_matrix()
    image.shader(blur_shader, 1 + int(math.sin(i * math.pi/180 * 8) * 10))
    #print("Band...")
    #image.shader(band_shader, 2**0)
    #image.shader(alpha_monochrome_shader)
    #print("Alpha checkerboard...")
    #image.shader(alpha_checkerboard_shader)

    w, _ = os.get_terminal_size()
    scale = int((image_meta["width"] / w) + 1) if image_meta["width"] > w else 1

    image.print(scale)

    image.write(f"renders/fish_{i:>03}.png")