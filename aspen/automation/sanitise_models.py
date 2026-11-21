"""Remove the Windows user name and host name that Aspen Plus stores in solved backup files.

Aspen writes the account and machine that produced a run into the run-status record of a ``.bkp``::

    DSET RUN-STATUS VERS @VERS ( "41.0" "WIN-X64" "" "<user>" "<host>" ...

Those two tokens are personal identifiers and have no effect on the model. This script replaces them
with neutral placeholders in every ``.bkp`` under ``aspen/models`` (in place) and verifies, unless
``--no-verify`` is given, that Aspen Plus still opens and solves each sanitised file.

``.apw`` documents are binary and embed the same identifiers; they are not edited and are kept out of
version control - the ``.inp`` and sanitised ``.bkp`` files reproduce the models.

Usage:  python aspen/automation/sanitise_models.py [--no-verify] [--check]
        --check   only report whether identifiers are present (exit 1 if they are)
"""
from __future__ import annotations

import getpass
import re
import socket
import sys

from amcrax.paths import ASPEN_MODELS

RUN_STATUS = re.compile(rb'(DSET RUN-STATUS VERS @VERS \(\s*"[^"]*"\s+"[^"]*"\s+"[^"]*"\s+)"([^"]*)"(\s+)"([^"]*)"')


def identifiers() -> list[bytes]:
    """Identifiers of the current account/machine that must not appear in a published model file."""
    out = []
    for value in (getpass.getuser(), socket.gethostname()):
        if value and len(value) >= 4:
            out += [value.encode(), value.lower().encode(), value.upper().encode()]
    return sorted(set(out))


def sanitise(data: bytes) -> tuple[bytes, int]:
    data, n = RUN_STATUS.subn(rb'\1"user"\3"host"', data)
    return data, n


def main() -> int:
    check_only = "--check" in sys.argv
    verify = "--no-verify" not in sys.argv and not check_only
    ids = identifiers()
    files = sorted(ASPEN_MODELS.glob("*.bkp"))
    dirty = 0
    for path in files:
        data = path.read_bytes()
        present = sum(data.count(i) for i in ids)
        if check_only:
            print(f"{path.name}: {'identifiers present' if present else 'clean'}")
            dirty += 1 if present else 0
            continue
        new, n = sanitise(data)
        left = sum(new.count(i) for i in ids)
        if new != data:
            path.write_bytes(new)
        print(f"{path.name}: run-status records rewritten: {n}; identifiers remaining: {left}")
        dirty += 1 if left else 0
    if check_only or not verify:
        return 1 if dirty else 0

    from amcrax.aspen.runner import aspen_lock
    from amcrax.aspen.session import AspenSession

    for path in files:
        with aspen_lock():
            with AspenSession() as s:
                s.open(path)
                seconds = s.run()
                x_out = s.get(r"\Data\Streams\S5\Output\MOLEFLOW\MIXED\NH3")
                x_in = s.get(r"\Data\Streams\S4\Output\MOLEFLOW\MIXED\NH3")
                print(f"{path.name}: opens and solves in Aspen Plus ({seconds:.1f} s); "
                      f"NH3 conversion {1 - float(x_out) / float(x_in):.6f}")
    return 1 if dirty else 0


if __name__ == "__main__":
    raise SystemExit(main())
