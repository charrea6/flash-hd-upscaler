#!/usr/bin/env python2.7
import argparse
import filecmp
import json
import os
import shutil
import re
import zipfile

from bs4 import BeautifulSoup
# --- Following slash is used in rebuilding output path later on
from archives import unzip_fla_to_directory, create_temp_dir, fla_files_in_dir, \
    create_zip_from_directory, dat_files_in_dir, xml_files_in_dir, get_fla_name, ensure_dir_exists_for_file, \
    CRC32_from_file, get_basename, ensure_dir_exists
from bitmaps_csv import BitmapsCSV
from edges import scale_edges
from elements import *
# --- Debug option to avoid overwriting output
from images import DatImage
from scaling import scale_horizontal, scale_vertical, format_as_float, format_as_int, format_as_halves, format_as_twips, \
    pixels_to_twips
from scanning import is_xfl_file, is_publish_settings, is_dom_document

WRITE_FILES = True

# --- Do we want to write back over .fla or leave as additional .zip
OVERWRITE_ORIGINAL = True

# --- Do we want to test the pipe-line without transforms
ENABLE_TRANSFORMS = True

# --- If we have any interim debug available
SHOW_DEBUG = False

# --- We may want to visually inspect the expanded/modified files
LEAVE_EXPANDED_FLA = True

# --- This extracts the images in src/dest sizes in both normal and flattened structures
EXTRACT_IMAGES = True

CONFIG_DELTA = "delta"
CONFIG_MAPPING_DOWN = "mapping_down"
CONFIG_DEFAULT_SIZE = "default_size"


def scale_attribute(node, attribute, fn, format=format_as_float):
    if node.has_attr(attribute):
        value = float(node.attrs[attribute])
        node.attrs[attribute] = format(fn(value))


def transform_point_coordinates(point):
    scale_attribute(point, ATTR_X, scale_horizontal, format=format_as_int)
    scale_attribute(point, ATTR_Y, scale_vertical, format=format_as_int)


def change_text_sizing(domtext):
    scale_attribute(domtext, ATTR_WIDTH, scale_horizontal, format=format_as_int)
    scale_attribute(domtext, ATTR_HEIGHT, scale_vertical, format=format_as_int)
    scale_attribute(domtext, ATTR_LEFT, scale_horizontal, format=format_as_int)


def get_mapping_value(mappings, attr, key):
    if attr in mappings:
        if key in mappings[attr]:
            return mappings[attr][key]
        elif 'default' in mappings[attr]:
            return mappings[attr]['default']
        else:
            print "UNKNOWN: %s of %s" % (attr, key)
    return key


def apply_mappings(node, mappings, attr):
    if attr in node.attrs:
        key = node.attrs[attr]
        node.attrs[attr] = get_mapping_value(mappings, attr, key)


def change_shapes(edge):
    if edge.has_attr(ATTR_EDGES):
        edge.attrs[ATTR_EDGES] = scale_edges(edge.attrs[ATTR_EDGES])


def change_matrix(matrix):
    scale_attribute(matrix, ATTR_TX, scale_horizontal, format=format_as_int)
    scale_attribute(matrix, ATTR_TY, scale_vertical, format=format_as_int)


def change_symbol_instance(symbol_instance):
    scale_attribute(symbol_instance, ATTR_CENTER_POINT_3D_X, scale_horizontal, format=format_as_int)
    scale_attribute(symbol_instance, ATTR_CENTER_POINT_3D_Y, scale_vertical, format=format_as_int)


def change_text_bitmap_size(text_attr):
    scale_attribute(text_attr, ATTR_BITMAP_SIZE, scale_horizontal, format=format_as_twips)


def change_video_instance(video_instance):
    scale_attribute(video_instance, ATTR_FRAME_RIGHT, scale_horizontal, format=format_as_twips)
    scale_attribute(video_instance, ATTR_FRAME_BOTTOM, scale_vertical, format=format_as_twips)


def change_height_literal(layer):
    scale_attribute(layer, ATTR_HEIGHT_LITERAL, scale_vertical, format=format_as_int)


def change_text_margins(text_attr):
    scale_attribute(text_attr, ATTR_LEFT_MARGIN, scale_horizontal, format=format_as_int)
    scale_attribute(text_attr, ATTR_RIGHT_MARGIN, scale_horizontal, format=format_as_int)


def change_document_size(document):
    scale_attribute(document, ATTR_WIDTH, scale_horizontal, format=format_as_int)
    scale_attribute(document, ATTR_HEIGHT, scale_vertical, format=format_as_int)


def change_stroke_weight(stroke):
    # --- Not clear whether to use vertical or horizontal
    scale_attribute(stroke, ATTR_WEIGHT, scale_vertical, format=format_as_halves)


def calculate_font_size(sd_size, font_mappings):

    hd_size = scale_vertical(sd_size)

    if not font_mappings:
        return hd_size

    possible_sizes = font_mappings[ATTR_SIZE]
    delta = font_mappings[CONFIG_DELTA]
    mapping_down = font_mappings[CONFIG_MAPPING_DOWN]

    # print delta, possible_sizes, mapping_down

    # --- Is there a delta to apply?
    hd_size += int(delta)

    if possible_sizes:

        smallest_possible = possible_sizes[0]
        largest_possible = possible_sizes[-1]

        if hd_size >= largest_possible:
            new_size = largest_possible
        else:

            if mapping_down:
                new_size = smallest_possible
                # --- Mapping down
                for possible_size in possible_sizes:
                    if hd_size >= possible_size:
                        new_size = possible_size
                    else:
                        break
            else:
                new_size = largest_possible
                # --- Mapping up
                for possible_size in possible_sizes:
                    if hd_size <= possible_size:
                        new_size = possible_size
                        break
    else:
        new_size = hd_size

    # print "MAPPING %.1f to %.1f" % (hd_size, new_size)
    return new_size


def change_font_size(node, font_mappings):

    if node.has_attr(ATTR_SIZE):
        sd_size = float(node.attrs[ATTR_SIZE])

        new_size = calculate_font_size(sd_size, font_mappings)

        node.attrs[ATTR_SIZE] = new_size

        # --- Make sure bitmapSize attribute matches the upscaling of the font size
        if node.has_attr(ATTR_BITMAP_SIZE):
            node.attrs[ATTR_BITMAP_SIZE] = pixels_to_twips(new_size)
    else:
        if CONFIG_DEFAULT_SIZE in font_mappings:
            default_size = font_mappings[CONFIG_DEFAULT_SIZE]
            node.attrs[ATTR_SIZE] = default_size
            node.attrs[ATTR_BITMAP_SIZE] = pixels_to_twips(default_size)
        else:
            print "No font size and no default available"


def process_and_replace_regex(line, regex, process_fn, transformation):
    m = regex.search(line)
    if m:
        s, e = m.span(1)
        v = m.group(1)
        line = line[:s] + str(process_fn(v, transformation)) + line[e:]
    return line


def process_number(value, scale_fn, format):
    if '.' in value:
        format_func = format_as_float
        v = float(value)
    else:
        format_func = format_as_int
        v = int(value)
    return format_func(scale_fn(v), format)


def process_horizontal(value, transformation, format=format_as_int):
    return format(scale_horizontal(float(value)))


def process_vertical(value, transformation, format=format_as_int):
    return format(scale_vertical(float(value)))


def process_weight(value, transformation):
    return process_vertical(value, format_as_halves)


def process_face(value, transformation):
    if transformation.font_mappings:
        return get_mapping_value(transformation.font_mappings, ATTR_FACE, value)
    return value


def process_edges(value, tranformation):
    return scale_edges(value)


def process_fill_color(value, transformation):
    if transformation.font_mappings:
        return get_mapping_value(transformation.font_mappings, ATTR_FILL_COLOR, value)


def process_font_size(value, transformation):
    sd_size = float(value)
    return calculate_font_size(sd_size, transformation.font_mappings)


TRANSFORM_REGEX = [(re.compile(regex), process_fn) for regex, process_fn in ((' width="(\d+(\.\d+)?)"', process_horizontal),
                                                                             (' x="(\-?\d+(\.\d+)?)"', process_horizontal),
                                                                             (' tx="(\-?\d+(\.\d+)?)"', process_horizontal),
                                                                             (' height="(\d+(\.\d+)?)"', process_vertical),
                                                                             (' y="(\-?\d+(\.\d+)?)"', process_vertical),
                                                                             (' ty="(\-?\d+(\.\d+)?)"', process_vertical),
                                                                             (' centerPoint3DX="(\-?\d+(\.\d+)?)"',
                                                                      process_horizontal),
                                                                             (' centerPoint3DY="(\-?\d+(\.\d+)?)"',
                                                                      process_vertical),
                                                                             (' weight="(\d+(\.\d+)?)"', process_weight),
                                                                             (' face="([^"]+)"', process_face),
                                                                             (' fillColor="([^"]+)"', process_fill_color),
                                                                             (' edges="([^"]+)"', process_edges),
                                                                             (' size="([^"]+)"', process_font_size))
                   ]


def apply_font_mappings(node, transformation, attr):
    if attr in transformation.font_mappings:
        apply_mappings(node, transformation.font_mappings, attr)


def convert_xml_file(old_xml_file, new_xml_file, transformation):
    if SHOW_DEBUG:
        print "Processing XML: %s" % old_xml_file

    if is_dom_document(old_xml_file):
        if transformation.coords:

            # --- DOMDocument is extremely brittle!!!
            with open(old_xml_file, "r") as f:
                contents = ''

                for line in f:
                    for reg_ex, process_fn in TRANSFORM_REGEX:
                        line = process_and_replace_regex(line, reg_ex, process_fn, transformation)
                    contents += str(line)

            with open(new_xml_file, 'wb') as output_file:
                output_file.write(contents)

    else:

        with open(old_xml_file, "r") as f:

            soup = BeautifulSoup(f, "lxml-xml")

            # --- Should trial this without any transformation just pipe cleaning
            if ENABLE_TRANSFORMS:

                if transformation.coords:
                    # --- <Point/> Modify x/y co-ordinates
                    [transform_point_coordinates(node) for node in soup.findAll(NODE_POINT)]

                    # --- <DOMTextAttrs/> Change bitmap size
                    [change_text_bitmap_size(node) for node in soup.findAll(NODE_DOM_TEXT_ATTRS)]

                    # --- <DOMTextAttrs/> Change left/right margins
                    [change_text_margins(node) for node in soup.findAll(NODE_DOM_TEXT_ATTRS)]

                    # --- <DOMDynamicText/> Change width/height/left sizings
                    [change_text_sizing(node) for node in soup.findAll(NODE_DOM_DYNAMIC_TEXT)]

                    # --- <DOMStaticText/> Change width/height/left sizings
                    [change_text_sizing(node) for node in soup.findAll(NODE_DOM_STATIC_TEXT)]

                    # --- <Matrix/> Change tx/ty coordinates
                    [change_matrix(node) for node in soup.findAll(NODE_MATRIX)]

                    # --- <Edge/> Change edges
                    [change_shapes(node) for node in soup.findAll(NODE_EDGE)]

                    # --- <DOMSymbolInstance/> Change 3D X/Y
                    [change_symbol_instance(node) for node in soup.findAll(NODE_DOM_SYMBOL_INSTANCE)]

                    # --- <DOMVideoInstance/> Change frameBottom/frameRight
                    [change_video_instance(node) for node in soup.findAll(NODE_DOM_VIDEO_INSTANCE)]

                    # --- <DOMLayer/> Change heightLiteral
                    [change_height_literal(node) for node in soup.findAll(NODE_DOM_LAYER)]

                    # --- <SolidStroke/> Change weight
                    [change_stroke_weight(node) for node in soup.findAll(NODE_SOLID_STROKE)]

                # --- <DOMTextAttrs/> Change font face
                if transformation.fonts:
                    for node in soup.findAll(NODE_DOM_TEXT_ATTRS):
                        apply_font_mappings(node, transformation, ATTR_FACE)
                        apply_font_mappings(node, transformation, ATTR_FILL_COLOR)
                        if transformation.font_mappings:
                            change_font_size(node, transformation.font_mappings)
                    for node in soup.findAll(NODE_DOM_FONT_ITEM):
                        apply_font_mappings(node, transformation, ATTR_FACE)
                        if transformation.font_mappings:
                            change_font_size(node, transformation.font_mappings)
                    for node in soup.findAll(NODE_DOM_INPUT_TEXT):
                        apply_font_mappings(node, transformation, ATTR_HEIGHT)
                        change_text_sizing(node)

            # --- Write the modified soup out to the new directory
            if WRITE_FILES:
                # print new_xml_file
                with open(new_xml_file, "wb") as output_file:
                    output_file.write(str(soup))


def process_publish_settings(xml_file):
    f = open(xml_file, 'r')
    xml_data = f.read()
    f.close()

    xml_data = xml_data.replace('<Width>720</Width>', '<Width>1280</Width>')
    xml_data = xml_data.replace('<Height>576</Height>', '<Height>720</Height>')

    f = open(xml_file, 'w')
    f.write(xml_data)
    f.close()


def scan_and_convert_xml(directory, transformation):
    for xml_file in xml_files_in_dir(directory):

        if is_xfl_file(xml_file):
            convert_xml_file(xml_file, xml_file, transformation)

        if is_publish_settings(xml_file):
            process_publish_settings(xml_file)


def translate_windows_path(path):
    path = path.replace('\\', os.path.sep)
    return path


def extract_image_file(src_file, dest_file):
    if os.path.exists(dest_file):
        pass
        # if not filecmp.cmp(src_file, dest_file, shallow=False):
        #     print "DIFF FILE", src_file
    else:
        ensure_dir_exists_for_file(dest_file)
        shutil.copy(src_file, dest_file)


def scan_and_convert_dat(directory, bitmap_details, transformation):
    for dat_file in dat_files_in_dir(directory):
        if SHOW_DEBUG:
            print "CONVERT %s" % dat_file

        dat_image = DatImage(dat_file)

        if transformation.alternates_dir:
            key = os.path.basename(dat_file)
            if key in bitmap_details:
                alternate_png = os.path.join(transformation.alternates_dir, get_basename(bitmap_details[key]['href']))

                if os.path.exists(alternate_png):
                    dat_image.insert_alternate_dest_png(alternate_png)
                    dat_image.copy_dest_to_src()
            else:
                print "ERROR: Don't understand dat: %s" % dat_file

        if transformation.images:
            dat_image.copy_dest_to_src()
        else:
            dat_image.create_dest_png()

        # --- Only needed for export of images
        if transformation.extracted_dir and dat_image.is_valid():
            dat_base = os.path.basename(dat_file)
            details = bitmap_details[dat_base]
            filename = translate_windows_path(details['href'])
            flattened_filename = get_basename(filename)

            extracted_dir = transformation.extracted_dir

            snapshot_src_file = os.path.join(extracted_dir, 'structured', 'src', filename)
            extract_image_file(dat_image.get_src_image_filename(), snapshot_src_file)

            flattened_src_file = os.path.join(extracted_dir, 'flattened', 'src', flattened_filename)
            extract_image_file(dat_image.get_src_image_filename(), flattened_src_file)

            snapshot_dest_file = os.path.join(extracted_dir, 'structured', 'dest', filename)
            extract_image_file(dat_image.get_dest_image_filename(), snapshot_dest_file)

            flattened_dest_file = os.path.join(extracted_dir, 'flattened', 'dest', flattened_filename)
            extract_image_file(dat_image.get_dest_image_filename(), flattened_dest_file)

        dat_image.tidy()


def scan_bitmap_details(directory):
    dom_document_filename = os.path.join(directory, DOM_DOCUMENT_XML)

    details = {}

    # --- Should always have a DOMDocument.xml file
    if not os.path.exists(dom_document_filename):
        print "ERROR: Was expecting a DOMDocument.xml file"
        return details

    with open(dom_document_filename, "r") as f:
        soup = BeautifulSoup(f, "lxml-xml")
        for node in soup.findAll('DOMBitmapItem'):
            internal_ref = node['bitmapDataHRef']
            internal_file = os.path.join(os.path.dirname(dom_document_filename), 'bin', internal_ref)

            dat_image = DatImage(internal_file)

            (src_w, src_h) = dat_image.get_src_dimensions()
            (dest_w, dest_h) = dat_image.get_dest_dimensions()

            crc = CRC32_from_file(internal_file)

            external = node['sourceExternalFilepath'] if node.has_attr('sourceExternalFilepath') else ''
            key = node['bitmapDataHRef']

            details[key] = {
                'is_valid': 'Y' if dat_image.is_valid() else 'N',
                'id': node['itemID'],
                'href': node['href'],
                'external': external,
                'src_w': src_w,
                'src_h': src_h,
                'dest_w': dest_w,
                'dest_h': dest_h,
                'crc': crc
            }

    return details


def convert_fla(fla_file, transformation, bitmaps_csv):
    print "Processing FLA: %s" % fla_file

    if not zipfile.is_zipfile(fla_file):
        print "ERROR: This is not a valid zip file (CS3?): %s" % fla_file
        return

    # --- We need a temporary directory
    temp_dir_path = create_temp_dir(fla_file, transformation.expanded_dir)
    unzip_fla_to_directory(fla_file, temp_dir_path)
    # shell_unzip_fla_to_directory(fla_file, temp_dir_path)

    bitmap_details = scan_bitmap_details(temp_dir_path)
    bitmaps_csv.add_bitmap_details(fla_file, bitmap_details)

    scan_and_convert_xml(temp_dir_path, transformation)
    scan_and_convert_dat(temp_dir_path, bitmap_details, transformation)

    archive_file = fla_file.rstrip('.fla')
    create_zip_from_directory(archive_file, temp_dir_path)

    if not LEAVE_EXPANDED_FLA:
        shutil.rmtree(temp_dir_path)

    if OVERWRITE_ORIGINAL:
        os.remove(fla_file)
        shutil.move(archive_file, fla_file)


def scan_and_convert_fla(scan_dir, transformation, bitmaps_csv):
    for fla_file in fla_files_in_dir(scan_dir):
        convert_fla(fla_file, transformation, bitmaps_csv)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-source', help='Specify whether the path is for a .FLA file or a directory to scan over',
                        type=str, choices=['fla', 'dir'], required=True)

    parser.add_argument('-coords', action='store_true', help='Process the xml files to upscale co-ordinates',
                        default=False)
    parser.add_argument('-images', action='store_true', help='Process the dat files to upscale images', default=False)
    parser.add_argument('-fonts', help='Configuration for font mappings (face, fillColor, size)', default='')

    parser.add_argument('-extracted_dir', help='Directory to store image information to', type=str, default='')
    parser.add_argument('-alternates_dir', help='Directory to retrieve alternate images from', type=str, default='')
    parser.add_argument('-expanded_dir', help='Directory to use for temporary expansion', type=str, default='')

    parser.add_argument('path', help='Path to either the .FLA file or directory')

    config = parser.parse_args()

    if config.source == 'fla':
        print "Transforming .FLA: %s" % config.path
    if config.source == 'dir':
        print "Transforming directory: %s" % config.path

    if config.alternates_dir:
        print "Using alternates dir: %s" % config.alternates_dir

    if config.expanded_dir:
        print "Using expanded dir: %s" % config.expanded_dir

    if config.extracted_dir:
        ensure_dir_exists(config.extracted_dir)
        print "Extracting images: %s" % config.extracted_dir

    if config.coords:
        print "Transforming co-ordinates"
    if config.images:
        print "Transforming images"
    if config.fonts:
        print "Transforming fonts: %s" % config.fonts
        with open(config.fonts) as f:
            config.font_mappings = json.load(f)
        if CONFIG_MAPPING_DOWN not in config.font_mappings:
            config.font_mappings[CONFIG_MAPPING_DOWN] = True
        if ATTR_SIZE in config.font_mappings:
            config.font_mappings[ATTR_SIZE].sort(key=int)
            print "- Tiering:", config.font_mappings[ATTR_SIZE]
            print "- Mapping: ", ("Down" if config.font_mappings[CONFIG_MAPPING_DOWN] else "Up")
        else:
            config.font_mappings[ATTR_SIZE] = None
            print "- Linear scaling"
        if CONFIG_DELTA not in config.font_mappings:
            config.font_mappings[CONFIG_DELTA] = 0
        else:
            print "- Delta: %d" % int(config.font_mappings[CONFIG_DELTA])
        if CONFIG_DEFAULT_SIZE in config.font_mappings:
            print "- Default size:", config.font_mappings[CONFIG_DEFAULT_SIZE]

    bitmaps_csv = BitmapsCSV(config.extracted_dir)

    if config.source == 'fla':
        convert_fla(config.path, config, bitmaps_csv)
    else:
        scan_and_convert_fla(config.path, config, bitmaps_csv)
