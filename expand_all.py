#!/usr/bin/env python2.7
from archives import *

SRC_DIR = 'original'
OUTPUT_DIR = 'expanded'

if __name__ == '__main__':
    empty_dir(OUTPUT_DIR)

    for fla_file in fla_files_in_dir(SRC_DIR):
        base_name = fla_file.lstrip(SRC_DIR)[1:].rstrip('.%s' % FLA_EXTENSION)
        print base_name

        unzip_fla_to_directory(fla_file, os.path.join(OUTPUT_DIR, base_name))
