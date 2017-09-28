#!/usr/bin/env python2.7
import argparse
import copy
import re
import shutil

import simplejson
from bs4 import BeautifulSoup

from archives import create_temp_dir, shell_unzip_fla_to_directory, fla_files_in_dir, xml_files_in_dir, \
    ensure_dir_exists_for_file
from scanning import is_xfl_file


def process_fla_file_for_values(fla_file):
    node_attr_values = {}

    # --- Extract
    temp_dir_path = create_temp_dir(fla_file)

    shell_unzip_fla_to_directory(fla_file, temp_dir_path)

    for xml_file in xml_files_in_dir(temp_dir_path):
        if is_xfl_file(xml_file):
            with open(xml_file, "r") as f:
                for soup in BeautifulSoup(f, "lxml-xml"):
                    for node in soup.findAll():
                        node_name = node.name
                        if node_name not in node_attr_values.keys():
                            node_attr_values[node_name] = {}

                        attributes = node_attr_values[node_name]

                        for attr in node.attrs:
                            if attr not in attributes:
                                attributes[attr] = []

                            value = node.attrs[attr]

                            if value not in attributes[attr]:
                                attributes[attr].append(value)

    shutil.rmtree(temp_dir_path)

    return node_attr_values


def is_float(value):
    if re.match("^-?\d+\.?\d*$", value) is None:
        return False
    return True


def inspect_values_across_flas(directory):

    all_node_attr_values = {}

    for fla_file in fla_files_in_dir(directory):
        node_attr_values = process_fla_file_for_values(fla_file)

        # --- How to add the two together
        for node in node_attr_values:
            if node not in all_node_attr_values:
                all_node_attr_values[node] = copy.deepcopy(node_attr_values[node])
            else:
                for attr in node_attr_values[node]:
                    if attr not in all_node_attr_values[node]:
                        all_node_attr_values[node][attr] = copy.deepcopy(node_attr_values[node][attr])
                    else:
                        for value in node_attr_values[node][attr]:
                            if value not in all_node_attr_values[node][attr]:
                                all_node_attr_values[node][attr].append(value)

    # --- How to add the two together
    for node in all_node_attr_values:
        for attr in all_node_attr_values[node]:
            all_floats = True
            for value in all_node_attr_values[node][attr]:
                if not is_float(value):
                    all_floats = False
                    break
            if all_floats:
                # print node, attr
                all_node_attr_values[node][attr].sort(key=float)
            else:
                all_node_attr_values[node][attr].sort()

    return all_node_attr_values


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path', help='Path to the directory containing .FLA files')
    parser.add_argument('output', help='Name of file to write results to')
    config = parser.parse_args()

    print "Processing FLAs: %s" % config.path
    print "Output JSON: %s" % config.output

    result = inspect_values_across_flas(config.path)

    ensure_dir_exists_for_file(config.output)

    with open(config.output, 'w') as f:
        f.write(simplejson.dumps(result, indent=2, sort_keys=True))
