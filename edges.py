import re

from scaling import scale_horizontal, scale_vertical, format_as_int, format_as_twips


def to_number(s):
    if s.startswith('#'):
        i, m = s[1:].split('.')
        if len(m) == 1:
            m += '0'
        return int(i, 16) + (int(m, 16) / 256.0)
    return float(s)


def split_edges(edges):
    segments = re.split('([!|S\[\]/])', edges)
    return [x for x in segments if x.strip() != '']


def scale_edge_pair(x_coord, y_coord):
    # print "X %s Y %s" % (x_coord, y_coord)
    x = format_as_twips(scale_horizontal(to_number(x_coord)))
    y = format_as_twips(scale_vertical(to_number(y_coord)))
    return '%s %s' % (x, y)


def scale_edges(edges):
    result = ''

    # if SHOW_DEBUG:
    #     print edges

    segments = split_edges(edges)

    while segments:
        segment = segments[0]
        if segment == 'S':
            segments.pop(0)
            result += 'S%s' % segments[0]
            segments.pop(0)
        elif segment in ['!', '|', '/', ']', '[']:
            result += segment
            segments.pop(0)

            coordinates = re.split('\s+', segments[0])
            segments.pop(0)
            result += scale_edge_pair(coordinates[0], coordinates[1])

            if segment in ['[', ']']:
                result += ' '
                result += scale_edge_pair(coordinates[2], coordinates[3])

        else:
            print "ERROR: Edge processing didn't expect %s" % segment
            break

    # if SHOW_DEBUG:
    #     print result

    return result
