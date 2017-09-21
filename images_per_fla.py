#!/usr/bin/env python2.7
import argparse
import csv

import os

import shutil

from archives import get_basename, ensure_dir_exists_for_file, ZIP_EXTENSION

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-extracted_dir', help='Directory containing images details extracted from conversion', type=str, required=True)
    parser.add_argument('-alternates_dir', help='Directory to retrieve alternate images from', type=str, required=True)
    parser.add_argument('-packs_dir', help='Directory to write image packs to', type=str, required=True)

    config = parser.parse_args()

    fla_image_mapping = {}

    csv_file = os.path.join(config.extracted_dir, 'images.csv')

    if not os.path.exists(csv_file):
        print "ERROR: Missing extraction details (CS3?)"
        exit(1)

    with open(csv_file) as f:
        csv_reader = csv.reader(f)

        for row in csv_reader:
            break

        for row in csv_reader:
            fla = row[0]
            image = get_basename(row[9])
            if fla not in fla_image_mapping:
                fla_image_mapping[fla] = []
            fla_image_mapping[fla].append(image)

    # --- Iterate over flas
    for fla in sorted(fla_image_mapping.keys()):
        image_set = set(fla_image_mapping[fla])
        # print fla, ','.join(image_set)

        # --- Copy files to new directory
        directory = os.path.join(config.packs_dir, fla)

        for image in image_set:
            alternate_image_filename = os.path.join(config.alternates_dir, image)
            flattened_image_filename = os.path.join(config.extracted_dir, 'flattened', 'dest', image)
            packs_image_filename = os.path.join(config.packs_dir, fla, image)

            ensure_dir_exists_for_file(packs_image_filename)

            if os.path.exists(alternate_image_filename):
                shutil.copyfile(alternate_image_filename, packs_image_filename)
            elif os.path.exists(flattened_image_filename):
                shutil.copyfile(flattened_image_filename, packs_image_filename)
            elif False:
                # --- Do we want to do any reporting
                print "Couldn't find a file for %s (%s)" % (image, fla)

        zip_filename = os.path.join(config.packs_dir, fla)
        shutil.make_archive(zip_filename, ZIP_EXTENSION, zip_filename)
