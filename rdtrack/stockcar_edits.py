"""slapfree's program edits, located by the instruction bytes around them.

slapfree.py carries the cockpit rev 5 offsets; the compact program is the same
code shifted, so each site is found by its neighbourhood (8 bytes before, the
original bytes, 6 after) instead.  Groups: core (run without the chip),
selftest (keep the operator ROM test quiet), y2k (the clock).
"""
import re

SITES = [
    # before, original, replacement, after, group, what
    ("00900f3420020280", "fffe7fff", "ffffffff", "224032117000", "core", "andi.l #$FFFE7FFF,d0 -> #$FFFFFFFF: stop folding A15/A16 out of the pointer"),
    ("588f34803012b053", "66", "60", "0e4879000457", "core", "bne.b -> bra.b: skip the 'BAD IC 137412-XXX' halt"),
    ("3e39000e004061b8", "3e39000e0044", "45f9000effff", "61b03e39000e", "selftest", "self-test 200Y pass 2"),
    ("3e39000e004461b0", "3e39000e0048", "45f9000f7fff", "61a83e39000e", "selftest", "self-test 200Y pass 3"),
    ("3e39000e004861a8", "3e39000e004c", "45f9000fffff", "61a04e754240", "selftest", "self-test 200Y pass 4"),
    ("ff703e39000e0000", "3e39000e0044", "45f9000f0000", "6100ff603e39", "selftest", "self-test 210Y pass 2"),
    ("ff603e39000e0000", "3e39000e0048", "45f9000f8000", "6100ff503e39", "selftest", "self-test 210Y pass 3"),
    ("ff503e39000e0000", "3e39000e004c", "45f900100000", "6100ff404e75", "selftest", "self-test 210Y pass 4"),
    ("01543e39000e0000", "3e39000e0044", "45f9000f0000", "49fa00066000", "selftest", "boot check 210Y pass 2"),
    ("01403e39000e0000", "3e39000e0048", "45f9000f8000", "49fa00066000", "selftest", "boot check 210Y pass 3"),
    ("012c3e39000e0000", "3e39000e004c", "45f900100000", "49fa00066000", "selftest", "boot check 210Y pass 4"),
    ("49fa0006600000bc", "3e39000e0044", "45f9000effff", "49fa00066000", "selftest", "boot check 200Y pass 2"),
    ("49fa0006600000ae", "3e39000e0048", "45f9000f7fff", "49fa00066000", "selftest", "boot check 200Y pass 3"),
    ("49fa0006600000a0", "3e39000e004c", "45f9000fffff", "49fa00066000", "selftest", "boot check 200Y pass 4"),
    ("31ffff4ffe00ff00", "88", "00", "009940e746fc", "y2k", "clock table: year field start 88 -> 00"),
    ("1013c102b02a0009", "6f", "63", "000006102a00", "y2k", "ble.w -> bls.w: BCD years compared unsigned"),
    ("123c00", "31", "32", "4eb9........123c00", "y2k", "century shown by the clock screen: '1' -> '2'"),
    ("123c00", "39", "30", "4eb9........1239", "y2k", "century shown by the clock screen: '9' -> '0'"),
]


def locate(image):
    """-> [(cpu_offset, replacement bytes, group, what)]; every site must match exactly once."""
    out = []
    for before, orig, new, after, group, what in SITES:
        pat = re.escape(bytes.fromhex(before)) + b"(" + re.escape(bytes.fromhex(orig)) + b")" + _pat(after)
        hits = [m.start(1) for m in re.finditer(pat, bytes(image), re.DOTALL)]
        if group == "y2k" and what.startswith("century"):
            # the two move.b immediates sit 10 bytes apart around a print call
            hits = [h for h in hits if bytes(image[h + 1:h + 3]) == b"\x4e\xb9"]
        if len(hits) != 1:
            raise SystemExit("edit site '%s' matched %d times" % (what, len(hits)))
        out.append((hits[0], bytes.fromhex(new), group, what))
    return out


def _pat(hexs):
    """hex with '..' wildcards -> regex bytes."""
    out = b""
    for tok in re.findall(r"\.\.|[0-9a-f]{2}", hexs):
        out += b"." if tok == ".." else re.escape(bytes.fromhex(tok))
    return out


def is_free(image):
    """True when the two `core` edits are already in `image` (a slapstic-free program), False when
    the stock bytes are there, None when neither is found."""
    found = []
    for before, orig, new, after, group, _what in SITES:
        if group != "core":
            continue
        patched = re.search(_pat(before) + _pat(new) + _pat(after), image, re.S) is not None
        stock = re.search(_pat(before) + _pat(orig) + _pat(after), image, re.S) is not None
        found.append(True if patched and not stock else False if stock and not patched else None)
    return None if None in found or len(set(found)) != 1 else found[0]
