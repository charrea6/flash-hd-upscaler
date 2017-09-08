#!/usr/bin/env python2.7
import argparse

from archives import *

SRC_DIR = 'current_epg'
DEST_DIR = 'original'


def repackage_fla(src_dir, fla_file, dest_dir):
    print fla_file

    temp_dir_path = create_temp_dir(fla_file)

    new_fla_file = dest_dir + fla_file.lstrip(src_dir)

    shell_unzip_fla_to_directory(fla_file, temp_dir_path)
    create_zip_from_directory(new_fla_file, temp_dir_path)


def fix_zips(src_dir, dest_dir):
    empty_dir(dest_dir)

    for fla_file in files_in_dir_of_type(src_dir, FLA_EXTENSION):
        repackage_fla(src_dir, fla_file, dest_dir)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('src_dir', help='Path to original .FLA files')
    parser.add_argument('dest_dir', help='Path to re-zipped .FLA files')

    config = parser.parse_args()

    fix_zips(config.src_dir, config.dest_dir)
