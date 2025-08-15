import argparse
from png import *

 # Create the parser
parser = argparse.ArgumentParser()

# Add the filename argument
parser.add_argument('filename', type=str, help='File to open and show')

# Parse the arguments
args = parser.parse_args()

image_data = [
    [0, 0, 0, 0, 0],
    [0, 1, 0, 1, 0],
    [0, 0, 0, 0, 0],
    [0, 1, 1, 1, 0],
    [0, 0, 0, 0, 0],
]

palette = [
    (0, 0, 0, 255),
    (255, 255, 255, 255),
]

image_data2 = [
    [ (0,0,0,255), (0,0,0,255), (0,0,0,255), (0,0,0,255), (0,0,0,255) ],
    [ (0,0,0,255), (255,255,255,255), (0,0,0,255), (255,255,255,255), (0,0,0,255) ],
    [ (0,0,0,255), (0,0,0,255), (0,0,0,255), (0,0,0,255), (0,0,0,255) ],
    [ (0,0,0,255), (255,255,255,255), (255,255,255,255), (255,255,255,255), (0,0,0,255) ],
    [ (0,0,0,255), (0,0,0,255), (0,0,0,255), (0,0,0,255), (0,0,0,255) ],
]

#image = PNG(image_data2)
#print(image.get_meta())
#image.write("test.png")

image = PNG(args.filename, flags=PNG_READ)
_, image_data = image._read_image_data()

for key in image_data["chunks"]:
    print(f"{key}:")

    match key:
        case "IHDR":
            for data_key in image_data["chunks"][key]["data"]:
                print(f" - {data_key}: {image_data["chunks"][key]["data"][data_key]}")
        
        case "PLTE":
            for index, color in enumerate(image_data["chunks"][key]["data"]):
                ansi_code = f"\033[38;2;{color[0]};{color[1]};{color[2]}m"
                reset_code = "\033[0m"
                color_string = ", ".join([f"{c:>3}" for c in color])
                print(f" - {index:>3}: ({ansi_code}██{reset_code}) {color_string}")

        case "tRNS":
            for index, alpha in enumerate(image_data["chunks"][key]["data"]):
                ansi_code = f"\033[38;2;{alpha};{alpha};{alpha}m"
                reset_code = "\033[0m"
                print(f" - {index:>3}: ({ansi_code}██{reset_code}) {alpha}")

        case "IDAT":
            # for data_item in image_data["chunks"][key]["data"]["matrix"]:
            #     for pixel in data_item:
            #         # IMplement multiplied alpha
            #         a = pixel[3] / 255
            #         pixel = [int(c * a) for c in pixel[0:-1:1]]
            #         ansi_code = f"\033[38;2;{pixel[0]};{pixel[1]};{pixel[2]}m"
            #         reset_code = "\033[0m"
            #         print(f"{ansi_code}██", end=reset_code)
            #         #print(f"{ansi_code}##", end=reset_code)
            #     print()

            height = len(image_data["chunks"][key]["data"]["matrix"])
            if height % 2 != 0:
                # Add an additional black line at the bottom of the image to display the last odd row
                image_data["chunks"][key]["data"]["matrix"].append([[0, 0, 0, 0] for _ in range(len(image_data["chunks"][key]["data"]["matrix"][0]))])

            for y in range(0, height, 2):
                for x in range( len(image_data["chunks"][key]["data"]["matrix"][0]) ):
                    pixel_top = image_data["chunks"][key]["data"]["matrix"][y][x]
                    pixel_bottom = image_data["chunks"][key]["data"]["matrix"][y + 1][x]

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

            # Count filers
            filters = [0, 0, 0, 0, 0]

            for f in image_data["chunks"][key]["data"]["filter"]:   
                filters[f] += 1

            print("Filter types:")
            for i, f in enumerate(filters):
                print(f" - {i}: {f}")


        case "tEXt":
            print(f" '{image_data["chunks"][key]["data"]["key"]}': '{image_data["chunks"][key]["data"]["value"]}'")

        case "zTXt":
            print(f" '{image_data["chunks"][key]["data"]["key"]}': '{image_data["chunks"][key]["data"]["value"]}'")
            print(f" Compression method: {image_data["chunks"][key]["data"]["compression_method"]}")

        case "tIME":
            for data_key in image_data["chunks"][key]["data"]:
                print(f" - {data_key}: {image_data["chunks"][key]["data"][data_key]}")

        case "IEND":
            print(" end")

    print()