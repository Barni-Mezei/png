"""
TODO:
- generate PNG from array of RGBA colors (truecolor + alpha)
- generate PNG from array of color indexes (palette based)

- handle multiple IDAT chunks
- handle interalcing

- zTXt correcly decompress text

- extract palette from any image

- fix bar display length on odd width terminals (0% is 1 character longer)

Resources:
https://www.nayuki.io/page/png-file-chunk-inspector
https://www.w3.org/TR/png-3/

"""

import zlib
import os
import time

# Flags
PNG_READ = 1 << 0 # Image reading mode
PNG_COLOR_PALETTE = 1 << 1 # Plette mode
PNG_INPUT_ARRAY = 1 << 2 # Input is a 1d array

class PNG:
    log_level : int = 0

    flags : int
    image_data : list
    palette : list
    image_meta : dict

    _file_data : bytearray
    _was_modified : bool

    # Constants
    _channels_per_color = [
        1, # Grayscale
       -1, # None
        3, # Truecolor (RGB)
        1, # Indexed
        2, # Grayscale + alpha
       -1, # None
        4, # Truecolor + alpha (RGBA)
    ]

    _color_type_grayscale : int = 0
    _color_type_truecolor : int = 2
    _color_type_indexed : int = 3
    _color_type_grayscale_alpha : int = 4
    _color_type_truecolor_alpha : int = 6

    def __init__(self, image_data : list = [], width : int = None, height : int = None, palette : list|None = None, flags : int = 0, ) -> None:
        """
        **Description:**
        
        The constructor will generate the image data, based on the given parameters, and the provided image data and palette.

        **Parameters:**
        - flags(int) The flags that determine the parameters of the image
        - image_data(list) The matrix of pixel color values, or palette indexes, or an array of colors, depending on the flags OR the name of the file to read in
        - width(int) The width of the image in pixels. If the input is a 2d matrix, and the width is not specified,
        it will be deermined by the first row in the matrix
        - height(int) The height of the image in pixels. If the input is a 2d matrix, and the height is not specified,
        it will be deermined by the length of the matrix
        - palette(list) An array of colors, each color will be shown in place of its index, if in palette mode,
        when set to None, the palette colors will be sampled from the image, this may took a while.

        **Possible flags:**
        - PNG_READ: The constructor is in image reading mode, meaning, the object expects only a file name, to read, and process later
        - PNG_WRITE (**default**): The constructor is in image wriring mode, this is used for creating new images
        - PNG_COLOR_RGBA (**default**): The image will use true color + alpha (1 byte for R, G, B and A, each.) *Pixel values expected to be a 4 items long array*
        - PNG_COLOR_PALETTE: The image will be in palette mode. *Pixel values expected to be a single integer.*
        - PNG_INPUT_MATRIX (**default**): The image_data must be in a matrix form (2d array, where the first dimension contains the scanlines)
        - PNG_INPUT_ARRAY: The image_data is expected to be an arry, containing pixel values, from top left, to top right,
        then down, mimicking scanlines.
        """

        self.flags = flags
        self.image_data = image_data
        self.palette = palette
        self.image_meta = {
            "width": width,
            "height": height,
        }

        self._file_data = None
        self._was_modified = False

        if len(image_data) == 0:
            raise ValueError("Image data can not be empty!")

        # Read mode
        if self.flags & PNG_READ:
            with open(image_data, "rb") as f:
                self._file_data = f.read()

            # Get image metadata
            self.image_meta, raw = self._read_image_data()

            # Get color matrix
            self.image_data = raw["chunks"]["IDAT"]["data"]["matrix"]

            # Get palette data
            if "PLTE" in raw["chunks"]:
                self.palette = raw["chunks"]["PLTE"]["data"]

        # Write mode
        else:
            # Set default values if input is in matrix form
            if not self.flags & PNG_INPUT_ARRAY and self.image_meta["width"] == None:
                self.image_meta["width"] = len(self.image_data[0])

            if not self.flags & PNG_INPUT_ARRAY and self.image_meta["height"] == None:
                self.image_meta["height"] = len(self.image_data)

    def fill(self, color):
        """
        ### READ & WRITE MODE

        **Description:**

        Fills the entire image with the specified color.

        **Parameters:**
        - color(tuple): (r : int, g : int, b : int, a : int) The color to fill with
        """

        self.image_data = [[color for x in range(self.image_meta["width"])] for y in range(self.image_meta["height"])]
        self._file_data = None
        self._was_modified = True

        pass

    def write(self, file_name : str, use_palette : bool|None = None) -> None:
        """
        ### READ & WRITE MODE

        **Description:**
        
        The function will crate a new file, with the specified name (overwriting previous files) and puts the image into it, as a valid PNG image

        **Parameters:**
        - file_name(str) The name of the file, where the image data will be written into.
        - use_palette(bool) decides whenever to use paletted image generation for the ouput image, or regular RGBA
        """

        if not self._file_data or self._was_modified:
            self._file_data = self._generate_image(use_palette)

        f = open(file_name, "wb")
        f.write(self._file_data)
        f.close()

    def get_bytes(self) -> bytearray:
        """
        ### READ & WRITE MODE

        **Description:**

        Returns with the raw bytes read from the image.
        """

        if not self._file_data:
            self._file_data = self._generate_image()

        return self._file_data

    def get_matrix(self) -> list:
        """
        ### READ & WRITE MODE

        **Description:**

        Returns with a 2d matrix of RGBA colors, read from the image.
        """

        return self.image_data

    def get_meta(self) -> dict:
        """
        ### READ MODE

        **Description:**

        Returns with a dictionary containing metadata about the read image. The structure looks like this:
        - width: int
        - height: int
        """

        return self.image_meta

    def shader(self, callback : callable, shader_args : list = [], output : str|None = None) -> any:
        """
        ### READ & WRITE MODE

        **Description:**

        This function will itrate over every pixel in the image, calling the provided callback function on every pixel, essentially acting a a shader.
        The return value of the callback function, will replace the pixel value in the image. **NOTE: The return values are recorded in to a buffer, and
        the original image data is replaced at the end of the iteration**

        **Parameters:**
        - callback: A function, that will be called on every pixel of the image, looks like the following:
            - **Parameters:**
            - uv_position(tuple): (x : float, y : float) The UV position of this pixel, values range from 0 to 1 inclusive.
            - pixel_position(tuple): (x : int, y : int) The coordinate of the current pixel, as whole integers.
            - color(tuple): (r : int, g : int, b : int, a : int) The color of the current pixel, as an RGBA tuple. Color values are integers, from 0 to 255 inclusive.
            - **Returns:**
            - output_color(touple): (r : int, g : int, b : int, a: int)
            - *args: THe passed arguments to the shader
        - output(str):
            - None: The funcion will output nothing
            - print: The function wil print out the progress like so: Processing... {completed} / {total} ({percent}%) and prints a carridge return (\\r) after it.
            - bar: The function will print a progress bar after each scanline. The progress bar's width is the whole screen, and it is 1 character high
        - shader_args(list): Any additional arguments that will be passed to the callback function, in an unpacked form
        """

        buffer = []

        for y, scanline in enumerate(self.image_data):
            buffer_line = []

            for x, pixel in enumerate(scanline):
                uv_x = x / self.image_meta["width"]
                uv_y = y / self.image_meta["height"]

                try:
                    color_out = callback((uv_x, uv_y), (x, y), pixel, *shader_args)
                except Exception as e:
                    raise e

                for i, channel in enumerate(color_out):
                    color_out[i] =  int(channel) % 256

                buffer_line.append(color_out)

            progress = (y / len(self.image_data))

            match output:
                case "print":
                    print(f"Processing {y}/{len(self.image_data)} ({int(progress * 100)}%)", end="\r")
                case "bar":
                    w, _ = os.get_terminal_size()
                    w -= 15 # Numbers on the side
                    progress += 0.001
                    filled = int(progress * w)
                    empty = int((1 - progress) * w)
                    print(f"{y:>4}/{len(self.image_data):>4}|{"#"*filled}{"."*empty}|{int(progress * 100):>3}%", end="\r")

            buffer.append(buffer_line)

        # Add a new line if printing was done
        if not output is None: print()

        # Set image data to the modified buffer
        self.image_data = buffer

        # MArk the image as modified
        self._was_modified = True

    def print(self, step : int|None = None) -> None:
        """
        **Description:**

        Prints the image to the console, using the BOTTOM HALF (▄) ascii character and ansi escape sequences,
        to set the foreground and background color of a character. Each character represents 2 pixels above each other.
        If the image height is odd, then a single black line will be preinted at the bottom (This is not part of the image data)

        **Parameters:**
        - step(int) The number of steps to take, to reach the next pixel. **MUST BE >= 1** For example, when set to 2,
        then a single pixel will be skipped over, and the image will be half as big on both axis.
        If set to None (default) then the image wil be scaled automatically to fully fit inside the terminal
        """
        
        if step is None or step < 1:
            w, _ = os.get_terminal_size()
            step = int((self.image_meta["width"] / w) + 1) if self.image_meta["width"] > w else 1

        buffer = self.image_data

        # Correct image height
        height = self.image_meta["height"]
        if height % 2 != 0:
            # Add an additional black line at the bottom of the image to display the last odd row
            buffer.append([[0, 0, 0, 0] for _ in range(self.image_meta["width"])])

        # Draw pixels as characters
        for y in range(0, height, 2 * step):
            for x in range( 0, self.image_meta["width"], step ):
                pixel_top = buffer[y][x]
                pixel_bottom = buffer[y + 1][x]

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

    def _paeth_predictor_o(self, a, b, c) -> float:
        p = a + b - c
        pa = abs(p - a)
        pb = abs(p - b)
        pc = abs(p - c)

        if pa <= pb and pa <= pc: return a
        if pb <= pc: return b
        return c

    def _paeth_predictor(self, a : int, b : int, c : int) -> float:
        p = a + b - c
        pa = abs(p - a)
        pb = abs(p - b)
        pc = abs(p - c)

        if pa <= pb and pa <= pc: return a
        if pb <= pc: return b
        return c


    def _read_image_data(self) -> tuple:
        """
        **Description:**

        Reads the image data from self._file_data and parses it, retrieving IHDR metadata palette data and text data.

        **Returns:**

        This function returns with 2 values, as a tuple.
        - The first one is a nicely formatted dictionary holding only the necessary data
        - The second value is a dictionary holding every data read from the image

        """

        if not self._file_data:
            raise ValueError("No image data found!")

        magic_header = bytearray([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])

        buffer = self._file_data

        # Check for the magic header
        if buffer[:len(magic_header)] == magic_header:
            buffer = buffer[len(magic_header):]
        else:
            raise ValueError("Invalid PNG image (Invalid header)")

        out = {
            "size": len(self._file_data),
            "chunks": {},
        }

        while len(buffer) > 0:
            chunk_length = int.from_bytes(buffer[:4])
            buffer = buffer[4:]

            chunk_type = str(buffer[:4], encoding="ascii")
            buffer = buffer[4:]

            chunk_data_bytes = buffer[:chunk_length]
            buffer = buffer[chunk_length:]

            chunk_crc = buffer[:4]
            buffer = buffer[4:]

            out["chunks"][chunk_type] = {
                "length": chunk_length,
                "data_bytes": chunk_data_bytes,
                "data": {},
                "crc": chunk_crc,
            }

        for key in out["chunks"]:
            match key:
                case "IHDR":
                    chunk_data_bytes = out["chunks"]["IHDR"]["data_bytes"]

                    out["chunks"]["IHDR"]["data"] = {
                        "width": 0,
                        "height": 0,
                        "bit_depth": 0,
                        "color_type": 0,
                        "compression_method": 0,
                        "filter_method": 0,
                        "interlace_method": 0,
                    }                    

                    out["chunks"]["IHDR"]["data"]["width"] = int.from_bytes(chunk_data_bytes[:4])
                    chunk_data_bytes = chunk_data_bytes[4:]
                    out["chunks"]["IHDR"]["data"]["height"] = int.from_bytes(chunk_data_bytes[:4])
                    chunk_data_bytes = chunk_data_bytes[4:]
                    out["chunks"]["IHDR"]["data"]["bit_depth"] = int.from_bytes(chunk_data_bytes[:1])
                    chunk_data_bytes = chunk_data_bytes[1:]
                    out["chunks"]["IHDR"]["data"]["color_type"] = int.from_bytes(chunk_data_bytes[:1])
                    chunk_data_bytes = chunk_data_bytes[1:]
                    out["chunks"]["IHDR"]["data"]["compression_method"] = int.from_bytes(chunk_data_bytes[:1])
                    chunk_data_bytes = chunk_data_bytes[1:]
                    out["chunks"]["IHDR"]["data"]["filter_method"] = int.from_bytes(chunk_data_bytes[:1])
                    chunk_data_bytes = chunk_data_bytes[1:]
                    out["chunks"]["IHDR"]["data"]["interlace_method"] = int.from_bytes(chunk_data_bytes[:1])
                    chunk_data_bytes = chunk_data_bytes[1:]

                    if self.log_level > 1: print(out["chunks"]["IHDR"]["data"])

                case "PLTE":
                    chunk_data_bytes = out["chunks"]["PLTE"]["data_bytes"]

                    out["chunks"]["PLTE"]["data"] = []

                    for i in range(int(len(chunk_data_bytes) / 3)):
                        data_offset = i * 3

                        r = int.from_bytes(chunk_data_bytes[data_offset:data_offset+1])
                        g = int.from_bytes(chunk_data_bytes[data_offset+1:data_offset+2])
                        b = int.from_bytes(chunk_data_bytes[data_offset+2:data_offset+3])
                        
                        out["chunks"]["PLTE"]["data"].append([r, g, b, 255])

                    if self.log_level > 1: print(out["chunks"]["PLTE"]["data"])

                case "tRNS":
                    chunk_data_bytes = out["chunks"]["tRNS"]["data_bytes"]

                    out["chunks"]["tRNS"]["data"] = []

                    match out["chunks"]["IHDR"]["data"]["color_type"]:
                        case PNG._color_type_grayscale:
                            # Image global alpha
                            out["chunks"]["tRNS"]["data"].append( int.from_bytes(chunk_data_bytes[data_offset+1:data_offset+2]) )

                        case PNG._color_type_truecolor:
                            # Image global alpha per channel
                            out["chunks"]["tRNS"]["data"].append( int.from_bytes(chunk_data_bytes[data_offset+1:data_offset+2]) )

                        case PNG._color_type_indexed:
                            for i, byte in enumerate(chunk_data_bytes):
                                a = byte

                                # Set alpha values in the palette                                
                                out["chunks"]["PLTE"]["data"][i][3] = a
                                
                                # Add to chunk data
                                out["chunks"]["tRNS"]["data"].append( a )

                    if self.log_level > 1: print(out["chunks"]["tRNS"]["data"])

                case "IDAT":
                    chunk_data_bytes = zlib.decompress( out["chunks"]["IDAT"]["data_bytes"])

                    out["chunks"]["IDAT"]["data"] = {
                        "matrix": [], # The completed color matrix, after applying the filter
                    }

                    channel_count = self._channels_per_color[out["chunks"]["IHDR"]["data"]["color_type"]]
                    pixel_size = int(channel_count * (out["chunks"]["IHDR"]["data"]["bit_depth"] / 8))

                    for y in range(out["chunks"]["IHDR"]["data"]["height"]):
                        scanline = []

                        # Save line filter type
                        data_offset = (y*out["chunks"]["IHDR"]["data"]["width"]) * pixel_size + y
                        filter_type = int.from_bytes(chunk_data_bytes[data_offset:data_offset + 1])

                        for x in range(out["chunks"]["IHDR"]["data"]["width"]):
                            data_offset = (y*out["chunks"]["IHDR"]["data"]["width"] + x) * pixel_size + (y + 1) # For filter bytes

                            raw_pixel_data = chunk_data_bytes[data_offset:data_offset + pixel_size]

                            if self.log_level > 1: print(f"Read {pixel_size} bytes ({channel_count}*{int(out["chunks"]["IHDR"]["data"]["bit_depth"]/8)}) on offset {data_offset}: {list(raw_pixel_data)}")

                            """
                            c b
                            a x
                            Where X is the current pixel
                            """

                            a = scanline[x - 1] if x > 0 else [0, 0, 0, 0]
                            b = out["chunks"]["IDAT"]["data"]["matrix"][y - 1][x] if y > 0 else [0, 0, 0, 0]
                            c = out["chunks"]["IDAT"]["data"]["matrix"][y - 1][x - 1] if x > 0 and y > 0 else [0, 0, 0, 0]

                            pixel_value : list

                            # Iterate over each channel in the pixel and apply the filter
                            if filter_type == 0:
                                # No filter
                                """ Recon(x) = Filt(x) """

                                pixel_value = [raw_pixel_data[channel] for channel in range(channel_count)]

                            if filter_type == 1:
                                # Sub filter
                                """ Recon(x) = Filt(x) + Recon(a) """

                                pixel_value = [raw_pixel_data[channel] + a[channel] for channel in range(channel_count)]

                            if filter_type == 2:
                                # Up filter
                                """ Recon(x) = Filt(x) + Recon(b) """

                                pixel_value = [raw_pixel_data[channel] + b[channel] for channel in range(channel_count)]

                            if filter_type == 3:
                                # Average filter
                                """ Recon(x) = Filt(x) + floor((Recon(a) + Recon(b)) / 2) """

                                pixel_value = [raw_pixel_data[channel] + int((a[channel] + b[channel]) / 2) for channel in range(channel_count)]

                            if filter_type == 4:
                                # Paeth filter
                                """ Recon(x) = Filt(x) + PaethPredictor(Recon(a), Recon(b), Recon(c)) """

                                pixel_value = [raw_pixel_data[channel] + self._paeth_predictor(a[channel], b[channel], c[channel]) for channel in range(channel_count)]

                            # Create RGBA format
                            match out["chunks"]["IHDR"]["data"]["color_type"]:
                                case PNG._color_type_grayscale:
                                    # Convert to grayscale image
                                    pixel_value += [pixel_value[0], pixel_value[0], 255]

                                case PNG._color_type_truecolor:
                                    # Add alpha
                                    pixel_value += [255]

                                case PNG._color_type_indexed:
                                    # Replace with color from the palette
                                    pixel_value = out["chunks"]["PLTE"]["data"][pixel_value[0]]

                            scanline.append([c % 256 for c in pixel_value])

                        out["chunks"]["IDAT"]["data"]["matrix"].append(scanline)
                        if self.log_level > 0: print(f"Reading IDAT chunk: {y+1}/{out["chunks"]["IHDR"]["data"]["height"]}", end="\r")

                    if self.log_level > 0: print(f"\n")

                case "tEXt":
                    chunk_data_bytes = out["chunks"]["tEXt"]["data_bytes"]

                    out["chunks"]["tEXt"]["data"] = {
                        "key": "",
                        "value": "",
                    }

                    destination = "key"

                    while len(chunk_data_bytes) > 0:
                        character = chunk_data_bytes[:1]
                        chunk_data_bytes = chunk_data_bytes[1:]
                        
                        if character == b"\00":
                            destination = "value"
                            continue

                        out["chunks"]["tEXt"]["data"][destination] += str(character, encoding="ascii")
                
                case "zTXt":
                    chunk_data_bytes = out["chunks"]["zTXt"]["data_bytes"]

                    out["chunks"]["zTXt"]["data"] = {
                        "key": bytearray(),
                        "value": bytearray(),
                    }

                    destination = "key"

                    while len(chunk_data_bytes) > 0:
                        character = chunk_data_bytes[:1]
                        chunk_data_bytes = chunk_data_bytes[1:]
                        
                        if character == b"\x00":
                            destination = "value"
                        
                            compression_method = int.from_bytes(chunk_data_bytes[:1])
                            chunk_data_bytes = chunk_data_bytes[1:]
                        
                            out["chunks"]["zTXt"]["data"]["compression_method"] = compression_method

                            continue

                        out["chunks"]["zTXt"]["data"][destination] += character

                    # Decode key and value
                    out["chunks"]["zTXt"]["data"]["key"] = out["chunks"]["zTXt"]["data"]["key"].decode('ISO-8859-1')
                    #out["chunks"]["zTXt"]["data"]["value"] = zlib.decompress(out["chunks"]["zTXt"]["data"]["value"], wbits=8).decode('ISO-8859-1')

                case "tIME":
                    chunk_data_bytes = out["chunks"]["tIME"]["data_bytes"]

                    out["chunks"]["tIME"]["data"]["year"] = int.from_bytes(chunk_data_bytes[:2])
                    chunk_data_bytes = chunk_data_bytes[2:]

                    out["chunks"]["tIME"]["data"]["month"] = int.from_bytes(chunk_data_bytes[:1])
                    chunk_data_bytes = chunk_data_bytes[1:]

                    out["chunks"]["tIME"]["data"]["day"] = int.from_bytes(chunk_data_bytes[:1])
                    chunk_data_bytes = chunk_data_bytes[1:]

                    out["chunks"]["tIME"]["data"]["hour"] = int.from_bytes(chunk_data_bytes[:1])
                    chunk_data_bytes = chunk_data_bytes[1:]

                    out["chunks"]["tIME"]["data"]["minute"] = int.from_bytes(chunk_data_bytes[:1])
                    chunk_data_bytes = chunk_data_bytes[1:]

                    out["chunks"]["tIME"]["data"]["second"] = int.from_bytes(chunk_data_bytes[:1])
                    chunk_data_bytes = chunk_data_bytes[1:]

                case "IEND":
                    out["chunks"]["IEND"]["data"] = None

        # Get necessary data from the chunks, and format it nicely
        # Default values
        formatted = {
            "width": 0,
            "height": 0,
            "bit_depth": 8,
            "color_type": 6,
            "interlace_method": 0,
            "palette": [],
            "text": {},
            "time": {},
        }

        # Set values if corresponding chunk was found
        if "IHDR" in out["chunks"]:
            formatted["width"] = out["chunks"]["IHDR"]["data"]["width"]
            formatted["height"] = out["chunks"]["IHDR"]["data"]["height"]
            formatted["bit_depth"] = out["chunks"]["IHDR"]["data"]["bit_depth"]
            formatted["color_type"] = out["chunks"]["IHDR"]["data"]["color_type"]
            formatted["interlace_method"] = out["chunks"]["IHDR"]["data"]["interlace_method"]

        if "tIME" in out["chunks"]:
            formatted["time"] = out["chunks"]["tIME"]["data"]

        if "PLTE" in out["chunks"]:
            formatted["palette"] = out["chunks"]["PLTE"]["data"]

        if "tEXt" in out["chunks"]:
            formatted["text"] = out["chunks"]["tEXt"]["data"]
            formatted["text"]["value"] = out["chunks"]["tEXt"]["data"]["key"] + ": " + out["chunks"]["tEXt"]["data"]["value"]

        return formatted, out


    def _generate_crc(self, data : bytearray) -> int:
        crc = 0xFFFFFFFF
        poly = 0xEDB88320

        for byte in data:
            crc = crc ^ byte

            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ poly
                else:
                    crc = crc >> 1

        return crc ^ 0xFFFFFFFF

    def _generate_chunk_IHDR(self) -> bytearray:
        if self.log_level > 0: print("Generating IHDR chunk...")

        out = bytearray()

        chunk_data = {
            "width": self.image_meta["width"],
            "height": self.image_meta["height"],
            "bit_depth": 8, # 8 bit color depth
            "color_type": 6, # 3: Palette, 6: True color with alpha
            "compression_method": 0, # Deflate compression
            "filter_method": 0, # No filter
            "interlace_method": 0, # No interlacing
        }

        if self.flags & PNG_COLOR_PALETTE:
            chunk_data["color_type"] = 3

        chunk_data_bytes = bytearray([0x49, 0x48, 0x44, 0x52]) # Chunk name IHDR
        chunk_data_bytes += bytearray(chunk_data['width'].to_bytes(4, 'big')) 
        chunk_data_bytes += bytearray(chunk_data['height'].to_bytes(4, 'big')) 
        chunk_data_bytes += bytearray(chunk_data['bit_depth'].to_bytes(1, 'big')) 
        chunk_data_bytes += bytearray(chunk_data['color_type'].to_bytes(1, 'big')) 
        chunk_data_bytes += bytearray(chunk_data['compression_method'].to_bytes(1, 'big')) 
        chunk_data_bytes += bytearray(chunk_data['filter_method'].to_bytes(1, 'big')) 
        chunk_data_bytes += bytearray(chunk_data['interlace_method'].to_bytes(1, 'big')) 

        chunk_crc = self._generate_crc(chunk_data_bytes)

        chunk_size = len(chunk_data_bytes) - 4 # Not counting the chunk name (4 bytes)

        out += chunk_size.to_bytes(4, 'big')
        out += chunk_data_bytes
        out += chunk_crc.to_bytes(4, 'big')

        return out

    def _generate_chunk_PLTE(self, palette : list) -> bytearray:
        if self.log_level > 0: print("Generating PLTE chunk...")

        out = bytearray()

        chunk_data_bytes = bytearray([0x50, 0x4c, 0x54, 0x45]) # Chunk name PLTE

        for color in palette:
            chunk_data_bytes += bytearray(color[0].to_bytes(1, 'big'))
            chunk_data_bytes += bytearray(color[1].to_bytes(1, 'big'))
            chunk_data_bytes += bytearray(color[2].to_bytes(1, 'big'))

        chunk_crc = self._generate_crc(chunk_data_bytes)

        chunk_size = len(chunk_data_bytes) - 4 # Not counting the chunk name (4 bytes)

        out += chunk_size.to_bytes(4, 'big')
        out += chunk_data_bytes
        out += chunk_crc.to_bytes(4, 'big')

        return out

    def _generate_chunk_tRNS(self, palette : list) -> bytearray:
        if self.log_level > 0: print("Generating tRNS chunk...")

        out = bytearray()

        chunk_data_bytes = bytearray([0x74, 0x52, 0x4e, 0x53]) # Chunk name PLTE

        if self.flags & PNG_COLOR_PALETTE:
            for color in palette:
                chunk_data_bytes += bytearray(color[3].to_bytes(1, 'big'))

        chunk_crc = self._generate_crc(chunk_data_bytes)

        chunk_size = len(chunk_data_bytes) - 4 # Not counting the chunk name (4 bytes)

        out += chunk_size.to_bytes(4, 'big')
        out += chunk_data_bytes
        out += chunk_crc.to_bytes(4, 'big')

        return out

    def _generate_chunk_IDAT_rgb(self, rgb_2d_matrix : list) -> bytearray:
        if self.log_level > 0: print("Generating (rgba) IDAT chunk...")

        out = bytearray()

        chunk_data_bytes = bytearray([0x49, 0x44, 0x41, 0x54]) # Chunk name IDAT

        pixel_data = bytearray()

        for line in rgb_2d_matrix:
            pixel_data += bytearray([0x00]) # Scanline filtering method
        
            for r, g, b, a in line:
                pixel_data += bytearray(r.to_bytes(1, 'big'))
                pixel_data += bytearray(g.to_bytes(1, 'big'))
                pixel_data += bytearray(b.to_bytes(1, 'big'))
                pixel_data += bytearray(a.to_bytes(1, 'big'))

        chunk_data_bytes += bytearray(zlib.compress(pixel_data))

        chunk_crc = self._generate_crc(chunk_data_bytes)

        chunk_size = len(chunk_data_bytes) - 4 # Not counting the chunk name (4 bytes)

        out += chunk_size.to_bytes(4, 'big')
        out += chunk_data_bytes
        out += chunk_crc.to_bytes(4, 'big')

        return out

    def _generate_chunk_IDAT_palette(self, palette_2d_matrix : list) -> bytearray:
        if self.log_level > 0: print("Generating (palette) IDAT chunk...")

        out = bytearray()

        chunk_data_bytes = bytearray([0x49, 0x44, 0x41, 0x54]) # Chunk name IDAT

        pixel_data = bytearray()

        for line in palette_2d_matrix:
            pixel_data += bytearray([0x00]) # Scanline filtering method
        
            for index in line:
                pixel_data += bytearray(index.to_bytes(1, 'big'))

        chunk_data_bytes += bytearray(zlib.compress(pixel_data))

        chunk_crc = self._generate_crc(chunk_data_bytes)

        chunk_size = len(chunk_data_bytes) - 4 # Not counting the chunk name (4 bytes)

        out += chunk_size.to_bytes(4, 'big')
        out += chunk_data_bytes
        out += chunk_crc.to_bytes(4, 'big')

        return out


    def _generate_chunk_IEND(self) -> bytearray:
        if self.log_level > 0: print("Generating IEND chunk...")

        out = bytearray() # Size of the chunk

        chunk_data_bytes = bytearray([0x49, 0x45, 0x4E, 0x44]) # Chunk name IEND

        chunk_size = len(chunk_data_bytes) - 4 # Not counting the chunk name (4 bytes)

        chunk_crc = self._generate_crc(chunk_data_bytes)

        out += chunk_size.to_bytes(4, 'big')
        out += chunk_data_bytes
        out += chunk_crc.to_bytes(4, 'big')

        return out

    def _generate_image(self, use_palette : bool|None = None) -> bytearray:
        """
        ** Description: **

        Generates a PNG image, and returns with a bytearray

        **Parameters:**

        - use_palette(bool) Decides whenever to use paletted image generation or regular RGBA
        """

        if self.log_level > 0: print("Stated generation...")

        # Set default value for paletted generation
        if use_palette == None: use_palette = self.flags & PNG_COLOR_PALETTE

        # The magic header for every PNG
        out = bytearray([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])

        out += self._generate_chunk_IHDR()

        if use_palette:
            out += self._generate_chunk_PLTE(self.palette)
            out += self._generate_chunk_tRNS(self.palette)
            out += self._generate_chunk_IDAT_palette(self.image_data)
        else:
            out += self._generate_chunk_IDAT_rgb(self.image_data)
        
        out += self._generate_chunk_IEND()

        if self.log_level > 0: print("End generation...")

        return out