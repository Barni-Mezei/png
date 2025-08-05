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

def generate_chunk_IDAT(color_matrix : list) -> bytearray:
    """
    color_matrix(list) -> bytearray A 1 dimensional array containing touples, in the following format: `[(r, g, b, a), (r, g, b, a)]`
    """
    
    print("Generating IDAT chunk...")

    out = bytearray()

    chunk_data_bytes = bytearray([0x49, 0x44, 0x41, 0x54]) # Chunk name IDAT

    for r, g, b, a in color_matrix:
        chunk_data_bytes += bytearray(r.to_bytes(1, 'big')) 
        chunk_data_bytes += bytearray(g.to_bytes(1, 'big')) 
        chunk_data_bytes += bytearray(b.to_bytes(1, 'big')) 
        chunk_data_bytes += bytearray(a.to_bytes(1, 'big')) 

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
        (255,0,0,255), (255,0,0,255), (255,0,0,255), (255,0,0,255), (255,0,0,255),
        (255,0,0,255), (255,0,0,255), (255,0,0,255), (255,0,0,255), (255,0,0,255),
        (255,0,0,255), (255,0,0,255), (255,0,0,255), (255,0,0,255), (255,0,0,255),
        (255,0,0,255), (255,0,0,255), (255,0,0,255), (255,0,0,255), (255,0,0,255),
        (255,0,0,255), (255,0,0,255), (255,0,0,255), (255,0,0,255), (255,0,0,255),
    ]

    # The magic header for every PNG
    f.write(bytearray([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])) 

    f.write( generate_chunk_IHDR() )
    f.write( generate_chunk_IDAT(image_data) )
    f.write( generate_chunk_IEND() )

    print("Closing file...")

    f.close()

    print("Done!")
