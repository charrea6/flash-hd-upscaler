#!/usr/bin/env python2.7
import os
from random import randint

from PIL import Image
from PIL.ImageQt import rgb

from archives import png_files_in_dir

SRC_DIR = 'extracted/flattened/dest'
DEST_DIR = 'alternates'

if __name__ == '__main__':

    for src_png_file in png_files_in_dir(SRC_DIR):
        dest_png_file = os.path.join(DEST_DIR, os.path.basename(src_png_file))
        print src_png_file, dest_png_file

        # --- Create a png of the correct size and random colour
        image = Image.open(src_png_file)

        solid_image = Image.new('RGBA', image.size, rgb(randint(0, 255), randint(0, 255), randint(0, 255)))
        solid_image.save(dest_png_file)

