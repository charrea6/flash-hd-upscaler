#!/usr/bin/env python2.7
import argparse
import os
from random import randint

from PIL import Image

from archives import png_files_in_dir, ensure_dir_exists

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-extracted_dir', help='Directory where extracted images were stored', default='')
    parser.add_argument('-alternates_dir', help='Directory to store generated alternates', default='')

    config = parser.parse_args()

    ensure_dir_exists(config.alternates_dir)

    for src_png_file in png_files_in_dir(config.extracted_dir):
        dest_png_file = os.path.join(config.alternates_dir, os.path.basename(src_png_file))

        # --- Create a png of the correct size and random colour
        image = Image.open(src_png_file)

        solid_image = Image.new('RGB', image.size, '#%02x%02x%02x' % (randint(0, 255), randint(0, 255), randint(0, 255)))
        solid_image.save(dest_png_file)
