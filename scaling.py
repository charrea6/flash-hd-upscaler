# --- Sizes of SD & HD Planes
SD_PLANE_WIDTH = 720
SD_PLANE_HEIGHT = 576

HD_PLANE_WIDTH = 1280
HD_PLANE_HEIGHT = 720

TWIPS_PER_PIXEL = 20


def format_as_float(value):
    return "%.2f" % (value + 0.005)


def format_as_int(value):
    return "%i" % int(value + 0.5)


def scale_horizontal(x):
    return x * HD_PLANE_WIDTH / SD_PLANE_WIDTH


def scale_vertical(y):
    return y * HD_PLANE_HEIGHT / SD_PLANE_HEIGHT


def pixels_to_twips(pixels):
    return TWIPS_PER_PIXEL * pixels


def twips_to_pixels(twips):
    return int(twips) / TWIPS_PER_PIXEL
