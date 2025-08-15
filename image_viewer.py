import argparse
from png import *

 # Create the parser
parser = argparse.ArgumentParser()

# Add the filename argument
parser.add_argument('filename', type=str, help='File to open and show')

# Parse the arguments
args = parser.parse_args()

# Read image data
image = PNG(args.filename, flags=PNG_READ)
color_matrix = image.get_matrix()
image_meta = image.get_meta()

# Correct image height
height = image_meta["height"]
if height % 2 != 0:
    # Add an additional black line at the bottom of the image to display the last odd row
    color_matrix.append([[0, 0, 0, 0] for _ in range(image_meta["width"])])

# Draw pixels as characters
for y in range(0, height, 2):
    for x in range( image_meta["width"] ):
        pixel_top = color_matrix[y][x]
        pixel_bottom = color_matrix[y + 1][x]

        # Multiplied alpha
        a_top = pixel_top[3] / 255
        pixel_top = [int(c * a_top) for c in pixel_top[0:-1:1]]
        top_ansi_code = f"\033[48;2;{pixel_top[0]};{pixel_top[1]};{pixel_top[2]}m"
        
        a_bottom = pixel_bottom[3] / 255
        pixel_bottom = [int(c * a_bottom) for c in pixel_bottom[0:-1:1]]
        bottom_ansi_code = f"\033[38;2;{pixel_bottom[0]};{pixel_bottom[1]};{pixel_bottom[2]}m"
        
        reset_code = "\033[0m"
        print(f"{top_ansi_code}{bottom_ansi_code}▄", end=reset_code)
    print()

print("Image data")

for key in image_meta:
    if type(image_meta[key]) is dict: continue
    if type(image_meta[key]) is list: continue

    print(f" - {key}: {image_meta[key]}")