import argparse
from png import *
import os

# Create the parser
parser = argparse.ArgumentParser()

# Add the filename argument
parser.add_argument('filename', type=str, help='File to open and show')

# Parse the arguments
args = parser.parse_args()

def mix(value_a : float, value_b : float, mix : float) -> float:
    """
    mix 0 - 1 : value_a - value_b
    """

    return (value_b * mix) + (value_a * (1 - mix))

def grayscale_shader(uv, pos, color : tuple, *args) -> tuple:
    brightness = sum(color[0:3]) / 3

    color[0] = brightness
    color[1] = brightness
    color[2] = brightness

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
            pixel = []

            if pos[0] + x == 0 or pos[0] + x >= image_meta["width"]: pixel = color
            if pos[1] + y == 0 or pos[1] + y >= image_meta["height"]: pixel = color

            if pixel == []: pixel = color_matrix[pos[1] + y][pos[0] + x]

            for channel in range(4):
                color_sum[channel] += pixel[channel]

    color_count = BOX_SIZE * BOX_SIZE

    out_color = [c / color_count for c in color_sum]

    return out_color

def alpha_shader(uv, pos, color : tuple) -> tuple:
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


# Read image data
print("Reading...")
image = PNG(args.filename, flags=PNG_READ)

image_meta = image.get_meta()

# Apply shader to the image
#image.shader(grayscale_shader)
#print("Alpha monchrome...")
#image.shader(alpha_monochrome_shader)
print("Alpha...")
image.shader(alpha_shader)
#print("Alpha edge...")
#image.shader(alpha_edge_shader)
print("Blur...")
color_matrix = image.get_matrix()
image.shader(blur_shader, image_meta["width"])

w, _ = os.get_terminal_size()
scale = int((image_meta["width"] / w) + 1) if image_meta["width"] > w else 1

print("Print...")
image.print(scale)

print("Image data")

for key in image_meta:
    if type(image_meta[key]) is dict: continue
    if type(image_meta[key]) is list: continue

    print(f" - {key}: {image_meta[key]}")