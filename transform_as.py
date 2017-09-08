import argparse
import os
import re


def scale_x(x):
    return x * 1280 / 720


def scale_y(y):
    return y * 720 / 576


def process_dims(line, match):
    value_group = 3
    dim_type = match.group(1)

    try:
        value = int(match.group(value_group))
    except:
        value = float(match.group(value_group))

    if 'X' in dim_type or 'WIDTH' in dim_type:
        value = scale_x(value)

    elif 'Y' in dim_type or 'HEIGHT' in dim_type:
        value = scale_y(value)

    g_s,g_e = match.span(value_group)
    line_start = line[:g_s]
    line_end = line[g_e:]
    return line_start + str(value) + line_end


def process_rectangle(line, match):
    x = scale_x(int(match.group(1)))
    y = scale_y(int(match.group(2)))
    w = scale_x(int(match.group(3)))
    h = scale_y(int(match.group(4)))

    g_x = match.span(1)
    g_y = match.span(2)
    g_w = match.span(3)
    g_h = match.span(4)

    line_start = line[:g_x[0]]
    x_y = line[g_x[1]:g_y[0]]
    y_w = line[g_y[1]:g_w[0]]
    w_h = line[g_w[1]:g_h[0]]
    line_end = line[g_h[1]:]

    return line_start + str(x) + x_y + str(y) + y_w + str(w) + w_h + str(h) + line_end


REGEX = [(re.compile(regex), callback)
        for regex,callback in [
            ('set([XY])\(([^0-9]+)?(-?[0-9]+)\)', process_dims),
            ('(WIDTH[^:]+|HEIGHT[^:]+|X_POS|Y_POS|[ _]X|[ _]Y):Number *= ([A-Za-z_].* +)*(-?[0-9]+(\.[0-9])?);', process_dims),
            ('Rectangle\( *(-?[0-9]+), *(-?[0-9]+), *(-?[0-9]+), *(-?[0-9]+)\)', process_rectangle)
        ]
]


def process_file(filename, options):
    print 'Processing %s ....' % filename
    transform = False
    with open(filename, 'rb') as in_f:
        for line in in_f:
            for regex,_ in REGEX:
                m = regex.search(line)
                if m:
                    transform = True
                    break

            if transform:
                break

    if transform:
        print 'Transforming %s ....' % filename
        original_file = filename + '.orig'
        os.rename(filename, original_file)
        with open(original_file, 'rb') as in_f:
            with open(filename, 'wb') as out_f:
                for line in in_f:
                    for regex, callback in REGEX:
                        m = regex.search(line)
                        if m:
                            line = callback(line, m)
                            break
                    out_f.write(line)

        if not options.keep_original:
            os.unlink(original_file)
    print 'Done'


def process_dir(dirname, options):
    print 'Processing directory hierarchy %s' % dirname
    for dirpath,dirs,names in os.walk(dirname, followlinks=True):
        for name in names:
            if name.endswith('.as'):
                process_file(os.path.join(dirpath, name), options)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process as script looking for coordinates and dimensions and transforming them to 720p")
    parser.add_argument("toconvert", nargs="+")
    parser.add_argument('--keep-original',
                        action="store_true",
                        help="If specified keep the original code, by appending .original to the filename")
    args = parser.parse_args()

    for filename in args.toconvert:
        if os.path.isfile(filename):
            process_file(filename, args)
        elif os.path.isdir(filename):
            process_dir(filename, args)
        else:
            print 'Unsupported input! Skipping %s' % filename