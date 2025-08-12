"""
TODO:
- generate PNG from 2d array (rotated) of RGBA colors (truecolor + alpha)
- generate PNG from 2d array (rotated) color indexes (palette based)
- generate PNG from array of strings (packed image format, palette based)
- generate PNG from array of RGBA colors (truecolor + alpha)

- make it  apython module, with a single class

"""

import zlib

# Flags
PNG_READ = 1 << 0 # Image reading mode
PNG_WRITE = 1 << 1 # Image writing mode (creating images)
PNG_COLOR_RGBA = 1 << 2 # Truecolor mode
PNG_COLOR_PALETTE = 1 << 3 # Plette mode
PNG_INPUT_MATRIX = 1 << 4 # Input is a 2d array
PNG_INPUT_ARRAY = 1 << 5 # Input is a 1d array

class PNG:
    log_level : int = 0

    flags : int
    image_data : list
    palette : list
    image_width : int
    image_height : int

    _file_data : bytearray

    def __init__(self, flags : int = PNG_COLOR_RGBA|PNG_INPUT_MATRIX, image_data : list = [], width : int = None, height : int = None, palette : list|None = None) -> None:
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
        - PNG_WRITE: The constructor is in image wriring mode, this is used for creating new images
        - PNG_COLOR_RGBA: The image will use true color + alpha (1 byte for R, G, B and A, each.) *Pixel values expected to be a 4 items long array*
        - PNG_COLOR_PALETTE: The image will be in palette mode. *Pixel values expected to be a single integer.*
        - PNG_INPUT_MATRIX: The image_data must be in a matrix form (2d array, where the first dimension contains the scanlines)
        - PNG_INPUT_ARRAY: The image_data is expected to be an arry, containing pixel values, from top left, to top right,
        then down, mimicking scanlines.
        """
        
        self.flags = flags
        self.image_data = image_data
        self.palette = palette
        self.image_width = width
        self.image_height = height

        self._file_data = None

        if len(image_data) == 0:
            raise ValueError("Image data can not be empty!")

        # Set default values
        if self.flags & PNG_INPUT_MATRIX and self.image_width == None:
            self.image_width = len(self.image_data[0])

        if self.flags & PNG_INPUT_MATRIX and self.image_height == None:
            self.image_height = len(self.image_data)

        # Generate image data if in write mode
        if self.flags & PNG_WRITE:
            self._generate_image()

    def write(self, file_name : str) -> None:
        """
        **Description:**
        
        The function will crate a new file, with the specified name (overwriting previous files) and puts the image into it, as a valid PNG image

        **Parameters:**
        - file_name(str) The name of the file, where the image data will be written into.
        """
        if not self._file_data:
            raise ValueError("No image data found!")

        f = open(file_name, "wb")
        f.write(self._file_data)
        f.close()

    def get_bytes(self) -> bytearray:
        """
        **Description:**

        Returns with the raw bytes read from the image.
        """
        if not self._file_data:
            raise ValueError("No image data found!")

        return self._file_data

    def get_meta(self) -> dict:
        """
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

        pass





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
