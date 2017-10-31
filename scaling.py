# --- Debug option: Useful to isolate changes, and check rounding
IGNORE_SCALING = False

# --- Sizes of SD & HD Planes
SD_PLANE_WIDTH = 720
SD_PLANE_HEIGHT = 576

if IGNORE_SCALING:
    HD_PLANE_WIDTH = SD_PLANE_WIDTH
    HD_PLANE_HEIGHT = SD_PLANE_HEIGHT
else:
    HD_PLANE_WIDTH = 1280
    HD_PLANE_HEIGHT = 720

TWIPS_PER_PIXEL = 20


def rounding(value, delta):
    return value + delta if value >= 0 else value - delta


def format_as_float(value):
    return "%.2f" % rounding(value, 0.005)


def format_as_twips(value):
    new_value = rounding(value, 10)
    mod = new_value % 20
    return "%d" % (new_value - mod)


def format_as_int(value):
    return "%i" % int(rounding(value, 0.5))


def format_as_halves(value):
    return "%.1f" % (float(int(rounding(2 * float(value), 0.5))) / 2)


def scale_horizontal(x):
    return x * HD_PLANE_WIDTH / SD_PLANE_WIDTH


def scale_vertical(y):
    return y * HD_PLANE_HEIGHT / SD_PLANE_HEIGHT


def scale_by_multiplier(v, m):
    return v * m


def pixels_to_twips(pixels):
    return TWIPS_PER_PIXEL * pixels


def twips_to_pixels(twips):
    return int(twips) / TWIPS_PER_PIXEL
