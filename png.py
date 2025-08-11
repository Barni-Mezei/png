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
PNG_COLOR_RGBA = 1 << 0
PNG_COLOR_PALETTE = 1 << 1
PNG_INPUT_MATRIX = 1 << 2
PNG_INPUT_ARRAY = 1 << 3

class PNG:
    def __init__(self, flags : int = PNG_COLOR_RGBA|PNG_INPUT_MATRIX, image_data : list = [], width : int = 16, height : int = 16, palette : list|None = None):
        """
        **Parameters:**
        - flags(int) The flags that determine the parameters of the image
        - image_data(list) The matrix of pixel color values, or palette indexes, or an array of colors, depending on the flags
        - width(int) The width of the image in pixels
        - height(int) The height of the image in pixels
        - palette(list) An array of colors, each color will be shown in place of its index, if in palette mode,
        when set to None, the palette colors will be sampled from the image, this may took a while.

        **Possible flags:**
        - PNG_COLOR_RGBA: The image will use true color + alpha (1 byte for R, G, B and A, each.) *Pixel values expected to be a 4 items long array*
        - PNG_COLOR_PALETTE: The image will be in palette mode. *Pixel values expected to be a single integer.*
        - PNG_INPUT_MATRIX: The image_data must be in a matrix form (2d array, where the first dimension contains the scanlines)
        - PNG_INPUT_ARRAY: The image_data is expected to be an arry, containing pixel values, from top left, to top right,
        then down, mimicking scanlines.
        """
        pass

    def generate_crc(data : bytearray) -> int:
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

    def generate_chunk_IHDR() -> bytearray:
        print("Generating IHDR chunk...")

        out = bytearray()

        chunk_data = {
            "width": 5,
            "height": 5,
            "bit_depth": 8, # 8 bit color depth
            "color_type": 6, # True color with alpha
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

        chunk_crc = generate_crc(chunk_data_bytes)

        chunk_size = len(chunk_data_bytes) - 4 # Not counting the chunk name (4 bytes)

        out += chunk_size.to_bytes(4, 'big')
        out += chunk_data_bytes
        out += chunk_crc.to_bytes(4, 'big')

        return out

    def generate_chunk_IDAT_2drgb(rgb_2d_matrix : list) -> bytearray:
        """
        color_matrix(list<list<tuple<r, g, b, a>>>) -> bytearray A 2 dimensional array containing arrays, which are containing touples, in the following format: `line: [(r, g, b, a), (r, g, b, a)]`
        """
        
        print("Generating IDAT chunk...")

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

        chunk_crc = generate_crc(chunk_data_bytes)

        chunk_size = len(chunk_data_bytes) - 4 # Not counting the chunk name (4 bytes)

        out += chunk_size.to_bytes(4, 'big')
        out += chunk_data_bytes
        out += chunk_crc.to_bytes(4, 'big')

        return out

    def generate_chunk_IEND() -> bytearray:
        print("Generating IEND chunk...")

        out = bytearray() # Size of the chunk

        chunk_data_bytes = bytearray([0x49, 0x45, 0x4E, 0x44]) # Chunk name IEND

        chunk_size = len(chunk_data_bytes) - 4 # Not counting the chunk name (4 bytes)

        chunk_crc = generate_crc(chunk_data_bytes)

        out += chunk_size.to_bytes(4, 'big')
        out += chunk_data_bytes
        out += chunk_crc.to_bytes(4, 'big')

        return out

if __name__ == "__main__":
    print("Opening file...")

    f = open("test.png", "bw")

    print("Stated generation...")

    image_data = [
        [ (0,0,0,255), (0,0,0,255), (0,0,0,255), (0,0,0,255), (0,0,0,255) ],
        [ (0,0,0,255), (255,255,255,255), (0,0,0,255), (255,255,255,255), (0,0,0,255) ],
        [ (0,0,0,255), (0,0,0,255), (0,0,0,255), (0,0,0,255), (0,0,0,255) ],
        [ (0,0,0,255), (255,255,255,255), (255,255,255,255), (255,255,255,255), (0,0,0,255) ],
        [ (0,0,0,255), (0,0,0,255), (0,0,0,255), (0,0,0,255), (0,0,0,255) ],
    ]

    # The magic header for every PNG
    f.write(bytearray([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])) 

    f.write( generate_chunk_IHDR() )
    f.write( generate_chunk_IDAT_2drgb(image_data) )
    f.write( generate_chunk_IEND() )

    print("Closing file...")

    f.close()

    print("Done!")
