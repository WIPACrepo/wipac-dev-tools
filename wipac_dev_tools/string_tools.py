"""String manipulation utilities."""

import re


def regex_named_groups_to_template(rstring: str, rstrip_dollar: bool = True) -> str:
    """Transform a regex string with named capture groups into a template string.

    Examples:
        In  = r"/TransferRequests/(?P<request_id>...+)"
        Out = "/TransferRequests/{request_id}"
        ---
        *with 'rstrip_dollar=True'*
        In  = r"USER=(?P<user>[A-Za-z0-9_]+)\s+IP=(?P<ip>\d+\.\d+\.\d+\.\d+)$"
        Out = "USER={user} IP={ip}"
    """
    out = re.sub(
        # match named capture groups like "...(?P<request_id>\w+)..."
        r"\(\?P<([A-Za-z_][A-Za-z0-9_]*)>(?:\\.|[^\\)])+\)",
        # and replace with "...{request_id}..."
        r"{\1}",
        rstring,
    )
    if rstrip_dollar:
        out = out.rstrip("$")
    return out
