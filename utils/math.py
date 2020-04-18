import math
import scipy


def clamp_incl(value, lower, upper):
    if value == float("inf"):
        return upper

    elif value == float("-inf"):
        return lower

    elif math.isnan(value):
        return lower

    value = int(value)

    if value < lower:
        return lower

    if value > upper:
        return upper

    return value
