import csv
import os


def _decode_href(href):
    href = href.replace('&#60', '<')
    href = href.replace('&#62', '>')
    return href.encode('utf-8')


class BitmapsCSV:
    def __init__(self, extracted_dir):
        self.csv_file = open(os.path.join(extracted_dir, 'images.csv'), 'wb') if extracted_dir else None
        if extracted_dir:
            self.csv_writer = csv.writer(self.csv_file, delimiter=',')

            titles = ['FLA', 'VALID', 'ID', 'REF', 'SD-W', 'SD-H', 'HD-W', 'HD-H', 'CRC', 'NAME', 'EXTERNAL']
            self.csv_writer.writerow(titles)

    def add_bitmap_details(self, fla_file, bitmap_details_list):
        if self.csv_file:
            fla = os.path.basename(fla_file).split('.')[0]
            for bitmap_name in bitmap_details_list:
                bitmap_details = bitmap_details_list[bitmap_name]
                self.csv_writer.writerow([
                    fla,
                    bitmap_details['is_valid'],
                    bitmap_details['id'],
                    bitmap_name,
                    bitmap_details['src_w'],
                    bitmap_details['src_h'],
                    bitmap_details['dest_w'],
                    bitmap_details['dest_h'],
                    bitmap_details['crc'],
                    _decode_href(bitmap_details['href']),
                    bitmap_details['external']
                ])

    def __exit__(self):
        if self.csv_file:
            self.csv_file.close()
