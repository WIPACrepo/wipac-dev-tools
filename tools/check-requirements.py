import json
import requests
import sys


def do_check_task(req_file: str) -> bool:
    """Check the versions of most dependencies against the latest from PyPi."""
    # flag: did we find anything to complain about?
    found = False
    # load the file by the name provided to us
    with open(req_file) as f:
        requirements_txt = f.read()
    requirements = requirements_txt.split("\n")
    # for each line in the requirements file
    for requirement in requirements:
        # if the requirement is pinned to something specific
        if "==" in requirement:
            # check to see if it matches the latest version
            equals_index = requirement.index("==")
            package_name = requirement[0:equals_index]
            package_version = requirement[equals_index+2:]
            url = f"https://pypi.python.org/pypi/{package_name}/json"
            r = requests.get(url)
            if r:
                data = json.loads(r.text)
                latest_version = data["info"]["version"]
                # if it doesn't match the latest version
                if package_version != latest_version:
                    # complain about it, and set our complain about it flag
                    print(f"{package_name} can be upgraded from {package_version} to {latest_version}")
                    found = True
    # tell the caller if we found anything to complain about
    return found


if __name__ == "__main__":
    if do_check_task(sys.argv[0]):
        sys.exit(1)
