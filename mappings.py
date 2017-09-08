#!/usr/bin/env python2.7
import csv
import os
import tempfile
from glob import glob

import shutil
from bs4 import BeautifulSoup

from archives import create_temp_dir
from scanning import is_xfl_file

SCANNING_DIR = 'original'
OUTPUT_CSV = 'output/node_to_attr_map.csv'


if __name__ == '__main__':

    node_to_attr_map = {}

    fla_files = [y for x in os.walk(SCANNING_DIR) for y in glob(os.path.join(x[0], '*.fla'))]

    print len(fla_files)

    # --- Scan all FLA
    for fla_file in fla_files:
        print fla_file

        # --- Extract
        temp_dir_path = create_temp_dir(fla_file)

        os.system('unzip -qq -d "%s" "%s"' % (temp_dir_path, fla_file))

        xml_files = [y for x in os.walk(temp_dir_path) for y in glob(os.path.join(x[0], '*.xml'))]

        for xml_file in xml_files:
            # --- Only process files within LIBRARY directory
            if is_xfl_file(xml_file):
                with open(xml_file, "r") as f:
                    for soup in BeautifulSoup(f, "lxml-xml"):
                        for node in soup.findAll():
                            node_name = node.name
                            if node_name not in node_to_attr_map.keys():
                                node_to_attr_map[node_name] = []
                            for attr in node.attrs:
                                if attr not in node_to_attr_map[node_name]:
                                    node_to_attr_map[node_name].append(attr)

        shutil.rmtree(temp_dir_path)

    # --- Write map of nodes to attributes as csv
    sorted_node_names = sorted(list(node_to_attr_map.keys()))

    sorted_attribute_names = sorted(set(x for k in node_to_attr_map.keys() for x in node_to_attr_map[k]))

    with open(OUTPUT_CSV, 'wb') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',')

        titles = ['']
        titles.extend(sorted_attribute_names)

        csv_writer.writerow(titles)

        for node_name in sorted_node_names:
            row = [node_name]
            for attr in sorted_attribute_names:
                row.append('X' if attr in node_to_attr_map[node_name] else '')
            csv_writer.writerow(row)
