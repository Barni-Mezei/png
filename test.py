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
image_data = image._read_image_data()

for key in image_data["chunks"]:
    print(f"{key}:")

    match key:
        case "IHDR":
            for data_key in image_data["chunks"][key]["data"]:
                print(f" - {data_key}: {image_data["chunks"][key]["data"][data_key]}")
        
        case "PLTE":
            for data_key in image_data["chunks"][key]["data"]:
                print(f" - {data_key}: {image_data["chunks"][key]["data"][data_key]}")

        case "IDAT":
            for data_item in image_data["chunks"][key]["data"]["matrix"]:
                for pixel in data_item:
                    # IMplement multiplied alpha
                    a = pixel[3] / 255
                    pixel = [int(c * a) for c in pixel[0:-1:1]]
                    ansi_code = f"\033[38;2;{pixel[0]};{pixel[1]};{pixel[2]}m"
                    reset_code = "\033[0m"
                    print(f"{ansi_code}██", end=reset_code)
                    #print(f"{ansi_code}##", end=reset_code)
                print()

            # Count filers
            filters = [0, 0, 0, 0, 0]

            for f in image_data["chunks"][key]["data"]["filter"]:   
                filters[f] += 1

            print("Filter types:")
            for i, f in enumerate(filters):
                print(f" - {i}: {f}")


        case "tEXT":
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