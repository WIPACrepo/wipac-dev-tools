"""The useful `strtobool()`, originally from the deprecated `distutils.util`."""


def strtobool(string: str) -> bool:
    """Smart-cast a string to a bool using common-sense interpretations.

    Unlike the since deprecated `distutils.util.strtobool`, this
    returns an actual bool.

    True: 'y', 'yes', 't', 'true', 'on', '1'
    False: 'n', 'no', 'f', 'false', 'off', '0'

    Raises:
        ValueError: if the string does not match any of the about
    """
    if string.lower() in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif string.lower() in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        raise ValueError(f"Invalid truth value: {string}")
