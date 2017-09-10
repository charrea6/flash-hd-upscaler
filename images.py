import os
import struct
import zlib

import shutil
from PIL import Image

# Format (https://stackoverflow.com/questions/4082812/xfl-what-are-the-bin-dat-files)
#
# 0305     ;raw bitmap identifier?
# 0400     ;length of decompressed row data
# 0100     ;width
# 0100     ;height
# 00000000 ;unknown
# 14000000 ;width in twips
# 00000000 ;unknown
# 14000000 ;height in twips
# 00       ;some flags - 01=image has transparency
#
# variant 1.:
# 01       ;compressed data flag
# 0200     ;length of compressed chunk
# 7801     ;compressed chunk
# 0A00     ;length of compressed chunk
# FBFFFFFF7F0009FA03FD ;compressed chunk
# 0000     ;end of compressed stream
#
# variant 2.:
# 00       ;data are uncompressed
# 00000000
# 00000000 ;unknown data - always zero?
# FFFFFFFF ;raw uncompressed ARGB data
from scaling import scale_horizontal, scale_vertical, pixels_to_twips

JPEG_MAGIC = 0xd8ff
ARGB_MAGIC = 0x0503
CLUT_MAGIC = 0x0303


def get_header(f, fmt):
    l = struct.calcsize(fmt)
    data = f.read(l)
    return struct.unpack(fmt, data)


def read_compressed_data(f):
    more = True
    decompressor = zlib.decompressobj()
    result = ''
    while more:
        l = struct.unpack('<H', f.read(2))[0]
        if l == 0:
            break
        data = f.read(l)
        result += decompressor.decompress(data)
    result += decompressor.flush()
    return result


def load_flash_format_0503(fn):
    """Load a flash formated file 32 bit ARGB file and return an Image object"""
    with open(fn, 'rb') as f:
        header = get_header(f, b'<HHHHIIIIB')

        if header[0] != ARGB_MAGIC:
            raise RuntimeError('Unexpected magic! Got 0x%04x' % header[0])

        w = header[2]
        h = header[3]

        variant = get_header(f, b'<B')
        if variant[0] != 1:
            print '%s: Unknown variant! %r' % (fn, variant)
            return None

        #
        # Extract the pixels and decompress...
        #
        result = read_compressed_data(f)

    # Convert ARGB to RGBA for PIL
    converted = ''
    for x in range(0, len(result), 4):
        converted += result[x + 1:x + 4] + result[x]

    return Image.frombytes('RGBA', (w, h), converted)


def load_flash_format_0303(fn):
    """Load a flash formated file in an unknown format and return an Image object"""
    with open(fn, 'rb') as f:
        header = get_header(f, b'<HHHHIIIIBBH')

        if header[0] != CLUT_MAGIC:
            raise RuntimeError('Unexpected magic! Got 0x%04x' % header[0])
        row_len = header[1]
        w = header[2]
        h = header[3]

        clut = []
        nrof_colours = header[9]
        if nrof_colours == 0:
            nrof_colours = 256

        for i in range(nrof_colours):
            ARGB = f.read(4)
            clut.append(ARGB[1:] + ARGB[0])

        result = read_compressed_data(f)

        pixels = ''
        for p in result:
            pixels += clut[ord(p)]

    return Image.frombytes('RGBA', (row_len, h), pixels)


def load_jpeg(fn):
    """Load a JPEG file and return an Image object"""
    image = Image.open(fn)
    return image.convert(mode='RGBA')


def load_dat(input_file):
    output_file = input_file.replace('.dat', '.png')

    f = open(input_file, 'rb')

    # Format (https://stackoverflow.com/questions/4082812/xfl-what-are-the-bin-dat-files)
    #
    # 0305/0303     ;raw bitmap identifier?
    # 0400     ;length of decompressed row data
    # 0100     ;width
    # 0100     ;height
    # 00000000 ;unknown
    # 14000000 ;width in twips
    # 00000000 ;unknown
    # 14000000 ;height in twips
    # 00       ;some flags - 01=image has transparency
    # <Format Specific data follows>
    #
    # Format Specific Data:
    # ---------------------
    # 0305: ARGB
    #
    # variant 1.:
    # 01       ;compressed data flag
    # 0200     ;length of compressed chunk
    # 7801     ;compressed chunk
    # 0A00     ;length of compressed chunk
    # FBFFFFFF7F0009FA03FD ;compressed chunk
    # 0000     ;end of compressed stream
    #
    # variant 2.:
    # 00       ;data are uncompressed
    # 00000000
    # 00000000 ;unknown data - always zero?
    # FFFFFFFF ;raw uncompressed ARGB data
    #
    # 0303: Colour Lookup Table Based
    #
    # XX       ;Number of colours in the colour table
    # 0000     ;unknown always 0
    # AARRGGBB*; ARGB colour data
    # ..
    # 0200     ;length of compressed chunk
    # 7801     ;compressed chunk
    # 0A00     ;length of compressed chunk
    # FBFFFFFF7F0009FA03FD ;compressed chunk
    # 0000     ;end of compressed stream

    header = get_header(f, b'<H')
    f.close()

    if header[0] == JPEG_MAGIC:
        return load_jpeg(input_file)

    elif header[0] == ARGB_MAGIC:
        return load_flash_format_0503(input_file)

    elif header[0] == CLUT_MAGIC:
        return load_flash_format_0303(input_file)
        # return
    else:
        print '%s: Unknown type of dat file (0x%04x)' % (input_file,header[0])


def write_compressed_chunk(f, data):
    # print 'Chunk size', len(data)
    left_over = ''
    if len(data) > 2048:
        left_over = data[2048:]
        data = data[:2048]
        # print len(data), len(left_over)
    header = struct.pack('<H', len(data))
    f.write(header)
    f.write(data)
    return left_over


def write_compressed_data(f, data):
    # IntelliJ warning due to incomplete signature in header
    compressor = zlib.compressobj(6, zlib.DEFLATED, 9, 5)
    left_over = ''
    left = data
    while left:
        to_write = left_over + compressor.compress(left[:2048])
        if to_write:
            left_over = write_compressed_chunk(f, to_write)
        left = left[2048:]

    to_write = left_over + compressor.flush()
    while to_write:
        to_write = write_compressed_chunk(f, to_write)
    f.write('\0\0')


class DatImage:
    def __init__(self, src_dat_file):
        self.src_dat_file = src_dat_file
        self.dest_dat_file = src_dat_file + '.up.dat'

        self.src_png_file = src_dat_file.replace('.dat', '.png')
        self.dest_png_file = self.src_png_file + '.up.png'

        self.src_w = 0
        self.src_h = 0

        self.dest_w = 0
        self.dest_h = 0

        self.dest_header = None

        self.src_image = None
        self.dest_image = None

        self.invalid = False

    def is_valid(self):
        return not self.invalid

    def _decode_src_image(self):
        if self.invalid:
            return

        self.src_image = load_dat(self.src_dat_file)
        if self.src_image is None:
            self.invalid = True
            return self

        self.src_w,self.src_h = self.src_image.size

        self.dest_w = int(scale_horizontal(self.src_w))
        self.dest_h = int(scale_vertical(self.src_h))

    def get_src_dimensions(self):
        self._decode_src_image()
        return self.src_w, self.src_h

    def get_dest_dimensions(self):
        self._decode_src_image()
        return self.dest_w, self.dest_h

    def extract_src_png(self):
        if self.invalid or self.src_image:
            return

        self._decode_src_image()
        if self.src_image:
            self.src_image.save(self.src_png_file)

    def create_dest_png(self):
        if self.invalid or self.dest_image:
            return

        self.extract_src_png()

        if self.src_image:
            self.dest_image = self.src_image.resize((self.dest_w, self.dest_h))
            self.dest_image.save(self.dest_png_file)

    def insert_alternate_dest_png(self, alternate_png):
        self.dest_image = Image.open(alternate_png)
        self.dest_image.save(self.dest_png_file)

    def insert_dest_png(self):
        if self.invalid or self.dest_header:
            return

        self.create_dest_png()

        if not self.dest_image:
            return


        self.dest_header = struct.pack('<HHHHIIIIBB', ARGB_MAGIC, self.dest_w * 4, self.dest_w, self.dest_h, 0,
                                       pixels_to_twips(self.dest_w), 0, pixels_to_twips(self.dest_h), 1, 1)
        data = self.dest_image.tobytes()
        converted = ''
        for x in range(0, len(data), 4):
            converted += data[x + 3] + data[x:x + 3]

        with open(self.dest_dat_file, 'wb') as f:
            f.write(self.dest_header)
            write_compressed_data(f, converted)

    def copy_dest_to_src(self):
        self.insert_dest_png()

        if os.path.exists(self.dest_dat_file):
            os.remove(self.src_dat_file)
            shutil.move(self.dest_dat_file, self.src_dat_file)

    def get_src_image_filename(self):
        self.extract_src_png()
        return self.src_png_file

    def get_dest_image_filename(self):
        # --- Upscale or inserted?
        return self.dest_png_file

    # def extract_dest_image(self, dest_file):
    #     self.extract_src_png()
    #
    #     shutil.copy(self.src_png_file, dest_file)

    def tidy(self):
        if True:
            if os.path.exists(self.src_png_file):
                os.remove(self.src_png_file)
            if os.path.exists(self.dest_png_file):
                os.remove(self.dest_png_file)
