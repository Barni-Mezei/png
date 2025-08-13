"""
TODO:
- generate PNG from 2d array (rotated) of RGBA colors (truecolor + alpha)
- generate PNG from 2d array (rotated) color indexes (palette based)
- generate PNG from array of strings (packed image format, palette based)
- generate PNG from array of RGBA colors (truecolor + alpha)

- paeth filter (4)
- handle multiple IDAT chunks

Resources:
https://www.nayuki.io/page/png-file-chunk-inspector

"""

import zlib
import time

# Flags
PNG_READ = 1 << 0 # Image reading mode
PNG_COLOR_PALETTE = 1 << 1 # Plette mode
PNG_INPUT_ARRAY = 1 << 2 # Input is a 1d array

class PNG:
    log_level : int = 1

    flags : int
    image_data : list
    palette : list
    image_meta : dict

    _file_data : bytearray
    _was_modified : bool

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

    def write(self, file_name : str) -> None:
        """
        ### READ & WRITE MODE

        **Description:**
        
        The function will crate a new file, with the specified name (overwriting previous files) and puts the image into it, as a valid PNG image

        **Parameters:**
        - file_name(str) The name of the file, where the image data will be written into.
        """

        if not self._file_data:
            self._file_data = self._generate_image()

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
        ### READ MODE

        **Description:**

        Returns with a 2d matrix of RGBA colors, read from the image.
        """

        if self._was_modified:
            return self.image_data
        else:
            self.get_meta()
        if not self._file_data: self._file_data = self._generate_image()

        return self._file_data


    def get_meta(self) -> dict:
        """
        ### READ MODE

        **Description:**

        Returns with a dictionary containing metadata about the read image. The structure looks like this:
        - width: int
        - height: int
        """

        return {
            "width": self.image_width,
            "height": self.image_height,
        }

    def shader(self, callback) -> None:
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
        """

        self._was_modified = True

        pass


    def _paeth_predictor(self, a, b, c) -> float:
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

        Reads the image dtaa from self._file_data and parses it, retrieving IHDR metadata and color data

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

                    if self.log_level > 0: print(out["chunks"]["IHDR"]["data"])

                case "IDAT":
                    chunk_data_bytes = zlib.decompress( out["chunks"]["IDAT"]["data_bytes"])

                    out["chunks"]["IDAT"]["data"] = {
                        "pre_matrix": [], # Raw matrix of colors or palette indexes
                        "filter": [], # Filter method for ecah scanline
                        "matrix": [], # The completed color matrix, after applying the filter
                    }

                    channel_count = 1

                    if out["chunks"]["IHDR"]["data"]["color_type"] == 0 or out["chunks"]["IHDR"]["data"]["color_type"] == 3: channel_count = 1
                    if out["chunks"]["IHDR"]["data"]["color_type"] == 4: channel_count = 2
                    if out["chunks"]["IHDR"]["data"]["color_type"] == 2: channel_count = 3
                    if out["chunks"]["IHDR"]["data"]["color_type"] == 6: channel_count = 4

                    pixel_size = int(channel_count * (out["chunks"]["IHDR"]["data"]["bit_depth"] / 8))

                    for y in range(out["chunks"]["IHDR"]["data"]["height"]):
                        scanline = []

                        # Save line filter type
                        data_offset = (y*out["chunks"]["IHDR"]["data"]["width"]) * pixel_size + y
                        out["chunks"]["IDAT"]["data"]["filter"].append( int.from_bytes(chunk_data_bytes[data_offset:data_offset + 1]) )

                        for x in range(out["chunks"]["IHDR"]["data"]["width"]):
                            data_offset = (y*out["chunks"]["IHDR"]["data"]["width"] + x) * pixel_size + (y + 1) # For filter bytes

                            raw_pixel_data = chunk_data_bytes[data_offset:data_offset + pixel_size]
                            #chunk_data_bytes = chunk_data_bytes[pixel_size:]

                            if self.log_level > 1: print(f"Read {pixel_size} bytes ({channel_count}*{int(out["chunks"]["IHDR"]["data"]["bit_depth"]/8)}) on offset {data_offset}: {list(raw_pixel_data)}")

                            # Split into colors.
                            pixel_data = [raw_pixel_data[i] for i in range(0, channel_count, 1)]

                            scanline.append(pixel_data)

                        out["chunks"]["IDAT"]["data"]["matrix"].append(scanline)
                        if self.log_level > 0: print(f"Reading IDAT chunk: {y+1}/{out["chunks"]["IHDR"]["data"]["height"]}", end="\r")

                    if self.log_level > 0: print(f"\n")

                    # Process filters
                    for y, scanline in enumerate(out["chunks"]["IDAT"]["data"]["matrix"]):
                        filter_type = out["chunks"]["IDAT"]["data"]["filter"][y]

                        """
                        c b
                        a x
                        Where X is the current pixel
                        """

                        match filter_type:
                            case 0:
                                """ Recon(x) = Filt(x) """
                                # No filter
                                pass

                            case 1:
                                """ Recon(x) = Filt(x) + Recon(a) """
                                # Sub filter
                                for x, pixel in enumerate(scanline):
                                    pixel_value = pixel

                                    if x > 0:
                                        for channel_index, channel in enumerate(pixel):
                                            pixel_value[channel_index] += scanline[x - 1][channel_index]
                                            pixel_value[channel_index] = pixel_value[channel_index] % 256

                                    out["chunks"]["IDAT"]["data"]["matrix"][y][x] = pixel_value

                            case 2:
                                """ Recon(x) = Filt(x) + Recon(b) """
                                # Up filter
                                for x, pixel in enumerate(scanline):
                                    pixel_value = pixel

                                    if y > 0:
                                        for channel_index, channel in enumerate(pixel):
                                            pixel_value[channel_index] += out["chunks"]["IDAT"]["data"]["matrix"][y - 1][x][channel_index]
                                            pixel_value[channel_index] = pixel_value[channel_index] % 256

                                    out["chunks"]["IDAT"]["data"]["matrix"][y][x] = pixel_value
                            
                            case 3:
                                # Average filter
                                """ Recon(x) = Filt(x) + floor((Recon(a) + Recon(b)) / 2) """
                                for x, pixel in enumerate(scanline):
                                    pixel_value = pixel

                                    if x > 0 and y > 0:
                                        for channel_index, channel in enumerate(pixel):
                                            top = out["chunks"]["IDAT"]["data"]["matrix"][y - 1][x][channel_index]
                                            left = out["chunks"]["IDAT"]["data"]["matrix"][y][x - 1][channel_index]
                                            avg = int((left + top) / 2)
                                            pixel_value[channel_index] += avg
                                            pixel_value[channel_index] = pixel_value[channel_index] % 256

                                    out["chunks"]["IDAT"]["data"]["matrix"][y][x] = pixel_value

                            case 4:
                                # Paeth filter
                                """ Recon(x) = Filt(x) + PaethPredictor(Recon(a), Recon(b), Recon(c)) """
                                for x, pixel in enumerate(scanline):
                                    pixel_value = pixel

                                    if x > 0 and y > 0:
                                        for channel_index, channel in enumerate(pixel):
                                            top_left = out["chunks"]["IDAT"]["data"]["matrix"][y - 1][x - 1][channel_index]
                                            top = out["chunks"]["IDAT"]["data"]["matrix"][y - 1][x][channel_index]
                                            left = out["chunks"]["IDAT"]["data"]["matrix"][y][x - 1][channel_index]
                                            pixel_value[channel_index] += self._paeth_predictor(left, top, top_left)
                                            pixel_value[channel_index] = pixel_value[channel_index] % 256
                                        #pixel_value = [0, 0, 0, 255]

                                    out["chunks"]["IDAT"]["data"]["matrix"][y][x] = pixel_value

                case "tEXT":
                    chunk_data_bytes = out["chunks"]["tEXT"]["data_bytes"]

                    out["chunks"]["tEXT"]["data"] = {
                        "key": "",
                        "value": "",
                    }

                    destination = "key"

                    while len(chunk_data_bytes) > 0:
                        character = int.from_bytes(chunk_data_bytes[:1])
                        chunk_data_bytes = chunk_data_bytes[1:]
                        
                        if character == 0:
                            destination = "value"
                            continue

                        out["chunks"]["tEXT"]["data"][destination] += str(character, encoding="ascii")
                
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

        return out


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
            "width": self.image_width,
            "height": self.image_height,
            "bit_depth": 8, # 8 bit color depth
            "color_type": 6, # 3: Palette, 6: True color with alpha
            "compression_method": 0, # Deflate compression
            "filter_method": 0, # No filter
            "interlace_method": 0, # No interlacing
        }

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

    def _generate_chunk_IDAT_rgb(self, rgb_2d_matrix : list) -> bytearray:
        if self.log_level > 0: print("Generating IDAT chunk...")

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

    def _generate_image(self) -> None:
        if self.log_level > 0: print("Stated generation...")

        # The magic header for every PNG
        self._file_data = bytearray([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])

        self._file_data += self._generate_chunk_IHDR()
        self._file_data += self._generate_chunk_IDAT_rgb(self.image_data)
        self._file_data += self._generate_chunk_IEND()

        if self.log_level > 0: print("End generation...")
