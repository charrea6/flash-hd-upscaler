#!/usr/bin/env python2.7
import csv
import os


def all_elements_equal(values):
    for value in values[1:]:
        if value != values[0]:
            return False
    return True


def examine_mappings(mappings):
    single = 0
    identical = 0
    same_name = 0
    other = 0

    for crc in mappings:
        refs = mappings[crc]
        if len(refs) == 1:
            single += 1
        else:
            if all_elements_equal(refs):
                identical += 1
            else:
                bases = []
                for ref in refs:
                    bases.append(ref.split('\\')[-1])

                if all_elements_equal(bases):
                    same_name += 1
                else:
                    for ref in list(set(refs)):
                        print "%s,%s" % (crc, ref)
                    other += 1

    print "Single maps:", single
    print "Identical names:", identical
    print "Same name:", same_name
    print "Other:", other


if __name__ == '__main__':
    overrides = {}

    with open('output/overrides.csv', 'r') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')

        for row in csv_reader:
            crc = row[0]
            ref = row[1]
            overrides[crc] = ref

    with open('output/images.csv', 'r') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')

        mappings = {}
        duplicates = {}

        for row in csv_reader:
            break

        for row in csv_reader:
            crc = row[8]
            ref = row[9] if crc not in overrides else overrides[crc]

            base = ref.split('\\')[-1]

            if base not in duplicates:
                duplicates[base] = []

            duplicates[base].append(crc)

            if crc not in mappings:
                mappings[crc] = []

            mappings[crc].append(ref)

    print "Unique crcs:", len(mappings.keys())

    examine_mappings(mappings)
    examine_mappings(duplicates)
