import os

import shutil
import tempfile
import zipfile
from glob import glob

import binascii

ZIP_EXTENSION = 'zip'
FLA_EXTENSION = 'fla'
XML_EXTENSION = 'xml'
DAT_EXTENSION = 'dat'
PNG_EXTENSION = 'png'


def get_basename(filename):
    return filename.split('\\')[-1].split('/')[-1]


def CRC32_from_file(filename):
    buf = open(filename, 'rb').read()
    buf = (binascii.crc32(buf) & 0xFFFFFFFF)
    return "%08X" % buf


def ensure_dir_exists(directory):
    if not os.path.exists(directory):
            os.makedirs(directory)


def ensure_dir_exists_for_file(filename):
    folder = os.path.dirname(filename)
    ensure_dir_exists(folder)


def get_fla_name(fla_file):
    fla_name = os.path.basename(fla_file).rstrip('.%s' % FLA_EXTENSION)
    return fla_name


def create_temp_dir(fla_file, expanded_dir=None):
    if expanded_dir:
        base_fla_file = get_basename(fla_file).rstrip('.%s' % FLA_EXTENSION)
        directory = os.path.join(expanded_dir, base_fla_file)
        if os.path.isdir(directory):
            shutil.rmtree(directory)
            ensure_dir_exists(directory)
        return directory
    else:
        return tempfile.mkdtemp()


def shell_unzip_fla_to_directory(fla_file, dir_path):
    os.system('unzip -qq -d "%s" "%s"' % (dir_path, fla_file))



def unzip_fla_to_directory(fla_file, directory):
    try:
        zip_ref = zipfile.ZipFile(fla_file, 'r')
        zip_ref.extractall(directory)
        zip_ref.close()
        return True
    except:
        print "WARN: Invalid FLA/ZIP %s" % fla_file
        shell_unzip_fla_to_directory(fla_file, directory)
        return True


def create_zip_from_directory(fla_file, dir_path):
    def addToZip(zf, path, zippath):
        if os.path.isfile(path):
            zf.write(path, zippath, zipfile.ZIP_DEFLATED)
        elif os.path.isdir(path):
            if zippath:
                zf.write(path, zippath)
            for nm in os.listdir(path):
                addToZip(zf, os.path.join(path, nm), os.path.join(zippath, nm))

    with zipfile.ZipFile(fla_file, 'w', allowZip64=True) as output:

        output.writestr(zipfile.ZipInfo('mimetype'), 'application/vnd.adobe.xfl')
        for nm in os.listdir(dir_path):
            if nm == 'mimetype':
                continue
            addToZip(output, os.path.join(dir_path, nm), nm)
    #shutil.make_archive(fla_file, ZIP_EXTENSION, dir_path)
    #os.rename('%s.%s' % (fla_file, ZIP_EXTENSION), fla_file)


def files_in_dir_of_type(directory, extension):
    return [y for x in os.walk(directory) for y in glob(os.path.join(x[0], '*.%s' % extension))]


def png_files_in_dir(directory):
    return files_in_dir_of_type(directory, PNG_EXTENSION)


def fla_files_in_dir(directory):
    return files_in_dir_of_type(directory, FLA_EXTENSION)


def dat_files_in_dir(directory):
    return files_in_dir_of_type(directory, DAT_EXTENSION)


def xml_files_in_dir(directory):
    return files_in_dir_of_type(directory, XML_EXTENSION)


def empty_dir(directory):
    if dir and os.path.isdir(directory):
        for path in glob(os.path.join(directory, '*')):
            if os.path.isfile(path):
                os.remove(path)
    for path in glob(os.path.join(directory, '*')):
        if os.path.isdir(path):
            shutil.rmtree(path)
