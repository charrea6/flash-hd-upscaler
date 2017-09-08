#!/usr/bin/env python2.7
import argparse
import filecmp
import os
import shutil
import re

from bs4 import BeautifulSoup
# --- Following slash is used in rebuilding output path later on
from archives import unzip_fla_to_directory, create_temp_dir, fla_files_in_dir, \
    create_zip_from_directory, dat_files_in_dir, xml_files_in_dir, get_fla_name, ensure_dir_exists_for_file, \
    CRC32_from_file, get_basename
from bitmaps_csv import BitmapsCSV
from edges import scale_edges
from elements import *
# --- Debug option to avoid overwriting output
from images import DatImage
from scaling import scale_horizontal, scale_vertical, format_as_float, format_as_int
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

# --- Seems like an odd list of fonts
SD_TO_HD_FONT_MAPPINGS = {
    'SkyText-Medium': 'SkyScreenRegular',
    'SkyText-Bold2': 'SkyScreenBold',

    'ArialMT': 'SkyScreenRegular',
    'Arial-BoldMT': 'SkyScreenBold',
    'Swiss721BT-Roman': 'SkyScreenRegular',
    'Swis721CnBT': 'SkyScreenRegular'
}

# --- Very long list of options, and there are floating point sizes as well
SD_FONT_SIZES = [14, 15, 16, 17, 18, 19, 20, 21, 22, 25, 26, 28, 29]
HD_FONT_SIZES = [16, 17, 18, 19, 20, 21, 22, 23, 24, 27, 28, 30, 31]

STROKE_WEIGHT_MAPPINGS = {
    '3': '5',
    '0.25': '0.5'
}


def scale_attribute(node, attribute, fn, format=format_as_float):
    if node.has_attr(attribute):
        value = float(node.attrs[attribute])
        node.attrs[attribute] = format(fn(value))


def transform_point_coordinates(point):
    scale_attribute(point, ATTR_X, scale_horizontal)
    scale_attribute(point, ATTR_Y, scale_vertical)


def change_text_sizing(domtext):
    scale_attribute(domtext, ATTR_WIDTH, scale_horizontal)
    scale_attribute(domtext, ATTR_HEIGHT, scale_vertical)
    scale_attribute(domtext, ATTR_LEFT, scale_horizontal)


def change_font_name(domtextattrs):
    face = domtextattrs.attrs[ATTR_FACE]
    if face in SD_TO_HD_FONT_MAPPINGS:
        domtextattrs.attrs[ATTR_FACE] = SD_TO_HD_FONT_MAPPINGS[face]
    else:
        print "UNKNOWN: Font face of %s" % face


def old_change_font_size(domtextattrs):
    size = str(domtextattrs.attrs[ATTR_SIZE])
    if not size.isdigit():
        print "ERROR: Font size is not an integer %s" % size
        size = size.split('.')[0]

    size = int(size)
    if size in SD_FONT_SIZES:
        domtextattrs.attrs[ATTR_SIZE] = HD_FONT_SIZES[SD_FONT_SIZES.index(size)]
    else:
        print "UNKNOWN: Font size of %s" % size


def change_font_size(domtextattrs):
    scale_attribute(domtextattrs, ATTR_SIZE, scale_vertical)


def change_shapes(edge):
    if edge.has_attr(ATTR_EDGES):
        edge.attrs[ATTR_EDGES] = scale_edges(edge.attrs[ATTR_EDGES])


def change_matrix(matrix):
    scale_attribute(matrix, ATTR_TX, scale_horizontal)
    scale_attribute(matrix, ATTR_TY, scale_vertical)


def change_symbol_instance(symbol_instance):
    scale_attribute(symbol_instance, ATTR_CENTER_POINT_3D_X, scale_horizontal)
    scale_attribute(symbol_instance, ATTR_CENTER_POINT_3D_Y, scale_vertical)


def change_text_bitmap_size(text_attr):
    scale_attribute(text_attr, ATTR_BITMAP_SIZE, scale_horizontal)


def change_video_instance(video_instance):
    scale_attribute(video_instance, ATTR_FRAME_RIGHT, scale_horizontal)
    scale_attribute(video_instance, ATTR_FRAME_BOTTOM, scale_vertical)


def change_text_height(input_text):
    scale_attribute(input_text, ATTR_HEIGHT, scale_vertical)


def change_height_literal(layer):
    scale_attribute(layer, ATTR_HEIGHT_LITERAL, scale_vertical)


def change_text_margins(text_attr):
    scale_attribute(text_attr, ATTR_LEFT_MARGIN, scale_horizontal)
    scale_attribute(text_attr, ATTR_RIGHT_MARGIN, scale_horizontal)


def change_document_size(document):
    scale_attribute(document, ATTR_WIDTH, scale_horizontal, format=format_as_int)
    scale_attribute(document, ATTR_HEIGHT, scale_vertical, format=format_as_int)


def change_stroke_weight(stroke):
    if ATTR_WEIGHT in stroke.attrs:
        weight = stroke.attrs[ATTR_WEIGHT]
        if weight in STROKE_WEIGHT_MAPPINGS:
            stroke.attrs[ATTR_WEIGHT] = STROKE_WEIGHT_MAPPINGS[weight]
        else:
            print "UNKNOWN: Stroke weight of %s" % weight


def scale_and_replace_regex(line, regex, scaler):
    m = regex.search(line)
    if m:
        s, e = m.span(1)
        v = m.group(1)
        line = line[:s] + scaler(v) + line[e:]
    return line


def process_number(value, scaler):
    if '.' in value:
        format_func = format_as_float
        v = float(value)
    else:
        format_func = format_as_int
        v = int(value)
    return format_func(scaler(v))


def process_horizontal(value):
    return process_number(value, scale_horizontal)


def process_vertical(value):
    return process_number(value, scale_vertical)


TRANSFORM_REGEX = [(re.compile(regex), scaler) for regex, scaler in ((' width="(\d+(\.\d+)?)"',process_horizontal),
                                                                     (' x="(\d+(\.\d+)?)"', process_horizontal),
                                                                     (' tx="(\d+(\.\d+)?)"', process_horizontal),
                                                                     (' height="(\d+(\.\d+)?)"', process_vertical),
                                                                     (' y="(\d+(\.\d+)?)"', process_vertical),
                                                                     (' ty="(\d+(\.\d+)?)"', process_vertical),
                                                                     (' edges="([^"]+)"', scale_edges))]


def convert_xml_file(old_xml_file, new_xml_file, transformation):
    if SHOW_DEBUG:
        print "Processing XML: %s" % old_xml_file

    if is_dom_document(old_xml_file):
        # DOMDocument is extremely brittle!!!
        with open(old_xml_file, "r") as f:
            contents = ''

            for line in f:
                for regex,scaler in TRANSFORM_REGEX:
                   line = scale_and_replace_regex(line, regex, scaler)
                contents += line

        with open(new_xml_file, 'wb') as output_file:
            output_file.write(contents)





    else:

        # test_xml_correctness(old_xml_file)

        with open(old_xml_file, "r") as f:

            soup = BeautifulSoup(f, "lxml-xml")

            # --- Should trial this without any transformation just pipe cleaning
            if ENABLE_TRANSFORMS:
                # --- <Point/> Modify x/y co-ordinates
                [transform_point_coordinates(node) for node in soup.findAll(NODE_POINT)]

                # --- <DOMTextAttrs/> Change font face
                if transformation.font:
                    [change_font_name(node) for node in soup.findAll(NODE_DOM_TEXT_ATTRS)]

                # --- <DOMTextAttrs/> Change font sizes
                [change_font_size(node) for node in soup.findAll(NODE_DOM_TEXT_ATTRS)]

                # --- <DOMFontItem/> Change font sizes
                [change_font_size(node) for node in soup.findAll(NODE_DOM_FONT_ITEM)]

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

                # --- <DOMInputText/> Change height
                [change_text_height(node) for node in soup.findAll(NODE_DOM_INPUT_TEXT)]

                # --- <DOMLayer/> Change heightLiteral
                [change_height_literal(node) for node in soup.findAll(NODE_DOM_LAYER)]

                # --- <SolidStroke/> Change weight
                [change_stroke_weight(node) for node in soup.findAll(NODE_SOLID_STROKE)]



                # --- Write the modified soup out to the new directory
            if WRITE_FILES:
                # print new_xml_file
                with open(new_xml_file, "wb") as output_file:
                    output_file.write(str(soup))


def process_publish_settings(xml_file):
    f = open(xml_file, 'r')
    xml_data = f.read()
    f.close()

    xml_data = xml_data.replace('<Width>720</Width>',   '<Width>1280</Width>')
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
        if not filecmp.cmp(src_file, dest_file, shallow=False):
            print "DIFF FILE", src_file
    else:
        ensure_dir_exists_for_file(dest_file)
        shutil.copy(src_file, dest_file)


def scan_and_convert_dat(directory, bitmap_details, transformation):

    for dat_file in dat_files_in_dir(directory):
        if SHOW_DEBUG:
            print "CONVERT %s" % dat_file

        dat_image = DatImage(dat_file)

        if transformation.alternates:
            key = os.path.basename(dat_file)
            if key in bitmap_details:
                alternate_png = os.path.join(transformation.alternates, get_basename(bitmap_details[key]['href']))

                if os.path.exists(alternate_png):
                    dat_image.insert_alternate_dest_png(alternate_png)
            else:
                print "ERROR: Don't understand dat: %s" % dat_file

        dat_image.copy_dest_to_src()

        # --- Only needed for export of images
        if transformation.extract and dat_image.is_valid():
            dat_base = os.path.basename(dat_file)
            details = bitmap_details[dat_base]
            filename = translate_windows_path(details['href'])
            flattened_filename = get_basename(filename)

            extracted_dir = transformation.extract

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

    # --- We need a temporary directory
    temp_dir_path = create_temp_dir(fla_file)
    unzip_fla_to_directory(fla_file, temp_dir_path)
    # shell_unzip_fla_to_directory(fla_file, temp_dir_path)

    bitmap_details = scan_bitmap_details(temp_dir_path)
    bitmaps_csv.add_bitmap_details(fla_file, bitmap_details)

    if transformation.xml:
        scan_and_convert_xml(temp_dir_path, transformation)
    if transformation.dat:
        scan_and_convert_dat(temp_dir_path, bitmap_details, transformation)

    archive_file = fla_file.strip('.fla')
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

    parser.add_argument('-xml', action='store_true', help='Process the xml files to upscale co-ordinates',
                        default=False)
    parser.add_argument('-dat', action='store_true', help='Process the dat files to upscale images', default=False)
    parser.add_argument('-font', action='store_true', help='Mapping of font families (untested)', default=False)

    parser.add_argument('-extract', help='Directory to store image information to', type=str, default='')
    parser.add_argument('-alternates', help='Directory to retrieve alternate image from', type=str, default='')

    parser.add_argument('path', help='Path to either the .FLA file or directory')

    config = parser.parse_args()

    if config.source == 'fla':
        print "Transforming .FLA: %s" % config.path
    if config.source == 'dir':
        print "Transforming directory: %s" % config.path

    if config.alternates:
        print "Using alternates: %s" % config.alternates

    if config.extract:
        print "Extracting images: %s" % config.extract

    if config.xml:
        print "Transforming XML"
    if config.dat:
        print "Transforming DAT"
    if config.font:
        print "Mapping font families"

    bitmaps_csv = BitmapsCSV()

    if config.source == 'fla':
        convert_fla(config.path, config, bitmaps_csv)
    else:
        scan_and_convert_fla(config.path, config, bitmaps_csv)
