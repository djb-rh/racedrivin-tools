#!/usr/bin/env python3
"""
slapfree.py - patch Atari Race Drivin' program ROMs to run without the slapstic.

Companion to the hardware modification that removes the slapstic from its socket
and drives the 200Y/210Y bank-select pins from the CPU address bus instead:

    200X pin 27  ->  200Y pin 27      (AB15 -> A14, bank bit 0)
    200X pin  1  ->  200Y pin  1      (AB16 -> A15, bank bit 1)
    210X pin 27  ->  210Y pin 27
    210X pin  1  ->  210Y pin  1

With that done, the 128 KB at 0x0E0000-0x0FFFFF decodes flat. The game already
addresses that region linearly, so only four of the sixteen program EPROMs
change - and 200Y/210Y themselves are burned from the stock dumps, unmodified.

Supported boards:

    racedriv     Race Drivin' cockpit / compact main board   (137412-117)
    rdp-centre   Race Drivin' Panorama, centre monitor       (137412-115)
    rdp-side     Race Drivin' Panorama, side monitors x2     (137412-115 each)

A Panorama archive contains both Panorama boards; the tool patches whichever
targets it recognises and leaves the rest alone.

Requires nothing but Python 3.8+ (Windows, macOS, Linux). No pip install.

    python3 slapfree.py racedriv.zip
    python3 slapfree.py /path/to/racedrivpan --mame-set
    python3 slapfree.py racedriv.zip --show-patch

This tool contains no ROM data. It carries only replacement instruction bytes
and hashes; it cannot produce anything without your own dump as input.
"""

import argparse
import binascii
import hashlib
import os
import shutil
import sys
import zipfile

VERSION = "2.0"

# --------------------------------------------------------------------------
# Patch definitions, one per board type.
#
# Offsets are into the interleaved 68010 address space, exactly as they appear
# in a disassembly.  200x EPROMs hold the even CPU bytes, 210x the odd, so CPU
# offset A in the pair based at B lands at file offset (A - B) // 2.
#
# "fill" holds one spare byte per device, in file coordinates, used to restore
# Atari's byte-sum signature: the low byte of each EPROM's byte-sum equals that
# ROM's own part-number suffix, and the self-test checks it.  The R-pair byte
# sits in the zero pad that fills out the 27512; the S-pair byte sits inside the
# instruction bytes that the patched bra.b jumps over.
# --------------------------------------------------------------------------

TARGETS = [
    {
        "name": 'racedriv',
        "label": "Race Drivin' (main board, 137412-117 or -115 at 200K)",
        "roms": {
            "200R": ('136077-5002.200r', 0x00000, 'even', 'a44722340ff7c99253107be092bec2e87cae340b', 0x02),
            "210R": ('136077-5001.210r', 0x00000, 'odd', '48fc4344c092c9eb14249874ac305b87bba53e7e', 0x01),
            "200S": ('136077-5004.200s', 0x20000, 'even', '8c7f4f79e90dc7206d9d83d588822000a7a53c52', 0x04),
            "210S": ('136077-5003.210s', 0x20000, 'odd', 'ccbc021c1230f5fbc2f51bdd4b82014f4a043d4a', 0x03),
        },
        "edits": [
            (0x27DAC, "FFFFFFFF", "core",
             "andi.l #$FFFE7FFF,d0 -> #$FFFFFFFF   stop folding A15/A16 out of the pointer"),
            (0x27E1E, "60", "core",
             "bne.b -> bra.b                       skip the 'BAD IC 137412-XXX' halt"),
            (0x0268E, "45F9000EFFFF", "selftest",
             "self-test 200Y pass 2: lea $0EFFFF,a2"),
            (0x02696, "45F9000F7FFF", "selftest",
             "self-test 200Y pass 3: lea $0F7FFF,a2"),
            (0x0269E, "45F9000FFFFF", "selftest",
             "self-test 200Y pass 4: lea $0FFFFF,a2"),
            (0x026DE, "45F9000F0000", "selftest",
             "self-test 210Y pass 2: lea $0F0000,a2"),
            (0x026EE, "45F9000F8000", "selftest",
             "self-test 210Y pass 3: lea $0F8000,a2"),
            (0x026FE, "45F900100000", "selftest",
             "self-test 210Y pass 4: lea $100000,a2"),
            (0x07A4C, "45F9000F0000", "selftest",
             "boot check 210Y pass 2: lea $0F0000,a2"),
            (0x07A60, "45F9000F8000", "selftest",
             "boot check 210Y pass 3: lea $0F8000,a2"),
            (0x07A74, "45F900100000", "selftest",
             "boot check 210Y pass 4: lea $100000,a2"),
            (0x07ADE, "45F9000EFFFF", "selftest",
             "boot check 200Y pass 2: lea $0EFFFF,a2"),
            (0x07AEC, "45F9000F7FFF", "selftest",
             "boot check 200Y pass 3: lea $0F7FFF,a2"),
            (0x07AFA, "45F9000FFFFF", "selftest",
             "boot check 200Y pass 4: lea $0FFFFF,a2"),
            (0x0808B, "00", "y2k",
             "clock table: year field start 88 -> 00, so the year wraps 00-99"),
            (0x080BE, "63", "y2k",
             "ble.w -> bls.w: compare BCD years unsigned, not signed"),
            (0x0840B, "32", "y2k",
             "century shown by the clock screen: '1' -> '2'"),
            (0x08415, "30", "y2k",
             "century shown by the clock screen: '9' -> '0'"),
        ],
        "fill": {"200R": 0xFFFF, "210R": 0xFFFF, "200S": 0x3F14, "210S": 0x3F14},
    },
    {
        "name": 'rdp-centre',
        "label": "Race Drivin' Panorama, centre monitor (Panorama Main PCB A045988, 137412-115)",
        "roms": {
            "200R": ('088-1002.bin', 0x00000, 'even', 'dbe4086cd87669a02d2a2133d0d9e2895946b383', 0x02),
            "210R": ('088-1001.bin', 0x00000, 'odd', '099bda6cfe31d4e53cbe74046679ddf8b874982d', 0x01),
            "200S": ('088-1004.bin', 0x20000, 'even', '9e3cafadfb23bfc4a44e503043cc05db27d939a9', 0x04),
            "210S": ('088-1003.bin', 0x20000, 'odd', '1bd308eff51588edfde21f3df1e84d3223d5d57a', 0x03),
        },
        "edits": [
            (0x27F52, "FFFFFFFF", "core",
             "andi.l #$FFFE7FFF,d0 -> #$FFFFFFFF   stop folding A15/A16 out of the pointer"),
            (0x27F96, "60", "core",
             "bne.b -> bra.b                       skip the 'BAD IC 137412-XXX' halt"),
            (0x0268E, "45F9000EFFFF", "selftest",
             "self-test 200Y pass 2: lea $0EFFFF,a2"),
            (0x02696, "45F9000F7FFF", "selftest",
             "self-test 200Y pass 3: lea $0F7FFF,a2"),
            (0x0269E, "45F9000FFFFF", "selftest",
             "self-test 200Y pass 4: lea $0FFFFF,a2"),
            (0x026DE, "45F9000F0000", "selftest",
             "self-test 210Y pass 2: lea $0F0000,a2"),
            (0x026EE, "45F9000F8000", "selftest",
             "self-test 210Y pass 3: lea $0F8000,a2"),
            (0x026FE, "45F900100000", "selftest",
             "self-test 210Y pass 4: lea $100000,a2"),
            (0x07A5C, "45F9000F0000", "selftest",
             "boot check 210Y pass 2: lea $0F0000,a2"),
            (0x07A70, "45F9000F8000", "selftest",
             "boot check 210Y pass 3: lea $0F8000,a2"),
            (0x07A84, "45F900100000", "selftest",
             "boot check 210Y pass 4: lea $100000,a2"),
            (0x07AEE, "45F9000EFFFF", "selftest",
             "boot check 200Y pass 2: lea $0EFFFF,a2"),
            (0x07AFC, "45F9000F7FFF", "selftest",
             "boot check 200Y pass 3: lea $0F7FFF,a2"),
            (0x07B0A, "45F9000FFFFF", "selftest",
             "boot check 200Y pass 4: lea $0FFFFF,a2"),
            (0x0809B, "00", "y2k",
             "clock table: year field start 88 -> 00, so the year wraps 00-99"),
            (0x080CE, "63", "y2k",
             "ble.w -> bls.w: compare BCD years unsigned, not signed"),
            (0x0841B, "32", "y2k",
             "century shown by the clock screen: '1' -> '2'"),
            (0x08425, "30", "y2k",
             "century shown by the clock screen: '9' -> '0'"),
        ],
        "fill": {"200R": 0xFFFF, "210R": 0xFFFF, "200S": 0x3FD0, "210S": 0x3FD0},
    },
    {
        "name": 'rdp-side',
        "label": "Race Drivin' Panorama, side monitors (Multisync PCB A046901, 137412-115, two boards)",
        "roms": {
            "200R": ('088-2002.bin', 0x00000, 'even', '5862f30f7e2ab9c0beb06cf5599bcb1ff97f3a47', 0x02),
            "210R": ('088-2001.bin', 0x00000, 'odd', 'bf6dcefc98e1fe27bef0ddacc265d8782c486c83', 0x01),
            "200S": ('088-2004.bin', 0x20000, 'even', '330cf39bcbdb9c73da48b4e947086a7988e37496', 0x04),
            "210S": ('088-2003.bin', 0x20000, 'odd', '106f1a23ac200a868959181fa1c47419806e8366', 0x03),
        },
        "edits": [
            (0x28F1E, "FFFFFFFF", "core",
             "andi.l #$FFFE7FFF,d0 -> #$FFFFFFFF   stop folding A15/A16 out of the pointer"),
            (0x28F62, "60", "core",
             "bne.b -> bra.b                       skip the 'BAD IC 137412-XXX' halt"),
            (0x029DE, "45F9000EFFFF", "selftest",
             "self-test 200Y pass 2: lea $0EFFFF,a2"),
            (0x029E6, "45F9000F7FFF", "selftest",
             "self-test 200Y pass 3: lea $0F7FFF,a2"),
            (0x029EE, "45F9000FFFFF", "selftest",
             "self-test 200Y pass 4: lea $0FFFFF,a2"),
            (0x02A2E, "45F9000F0000", "selftest",
             "self-test 210Y pass 2: lea $0F0000,a2"),
            (0x02A3E, "45F9000F8000", "selftest",
             "self-test 210Y pass 3: lea $0F8000,a2"),
            (0x02A4E, "45F900100000", "selftest",
             "self-test 210Y pass 4: lea $100000,a2"),
            (0x0746E, "45F9000F0000", "selftest",
             "boot check 210Y pass 2: lea $0F0000,a2"),
            (0x07482, "45F9000F8000", "selftest",
             "boot check 210Y pass 3: lea $0F8000,a2"),
            (0x07496, "45F900100000", "selftest",
             "boot check 210Y pass 4: lea $100000,a2"),
            (0x07500, "45F9000EFFFF", "selftest",
             "boot check 200Y pass 2: lea $0EFFFF,a2"),
            (0x0750E, "45F9000F7FFF", "selftest",
             "boot check 200Y pass 3: lea $0F7FFF,a2"),
            (0x0751C, "45F9000FFFFF", "selftest",
             "boot check 200Y pass 4: lea $0FFFFF,a2"),
            (0x07B9B, "00", "y2k",
             "clock table: year field start 88 -> 00, so the year wraps 00-99"),
            (0x07BCE, "63", "y2k",
             "ble.w -> bls.w: compare BCD years unsigned, not signed"),
            (0x07F1B, "32", "y2k",
             "century shown by the clock screen: '1' -> '2'"),
            (0x07F25, "30", "y2k",
             "century shown by the clock screen: '9' -> '0'"),
        ],
        "fill": {"200R": 0xFFFF, "210R": 0xFFFF, "200S": 0x47B6, "210S": 0x47B6},
    },
]

ROM_SIZE = 0x10000
GROUPS = ("core", "y2k", "selftest")
ROLES = ("200R", "210R", "200S", "210S")


class Fail(Exception):
    pass


def sha1(b):
    return hashlib.sha1(b).hexdigest()


def crc32(b):
    return "%08x" % (binascii.crc32(b) & 0xFFFFFFFF)


def split_edit(target, cpu_offset, blob):
    """Split one CPU-space edit into (role, file_offset, byte) triples."""
    base = (cpu_offset // 0x20000) * 0x20000
    for i, value in enumerate(blob):
        addr = cpu_offset + i
        half = "even" if addr % 2 == 0 else "odd"
        role = None
        for r, (_, rbase, rhalf, _, _) in target["roms"].items():
            if rbase == base and rhalf == half:
                role = r
                break
        if role is None:
            raise Fail("%s: no ROM covers CPU 0x%05X" % (target["name"], addr))
        yield role, (addr - base) // 2, value


def build_edit_map(target, groups):
    out = {role: {} for role in target["roms"]}
    for cpu_offset, hexbytes, group, _ in target["edits"]:
        if group not in groups:
            continue
        for role, off, value in split_edit(target, cpu_offset, bytes.fromhex(hexbytes)):
            out[role][off] = value
    return out


# ------------------------------ input ------------------------------------

def load_source(path):
    """Return {name: bytes} for every member of a zip or a directory."""
    blobs = {}
    if os.path.isdir(path):
        for name in sorted(os.listdir(path)):
            full = os.path.join(path, name)
            if os.path.isfile(full) and os.path.getsize(full) <= 0x100000:
                with open(full, "rb") as fh:
                    blobs[name] = fh.read()
    elif zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            for info in zf.infolist():
                if info.is_dir() or info.file_size > 0x100000:
                    continue
                blobs[os.path.basename(info.filename)] = zf.read(info)
    else:
        raise Fail("%s is neither a zip archive nor a directory" % path)
    if not blobs:
        raise Fail("no usable files found in %s" % path)
    return blobs


def identify(blobs, target):
    """Match a target's four program EPROMs by content hash, not by name."""
    by_hash = {}
    for name, data in blobs.items():
        by_hash.setdefault(sha1(data), []).append(name)
    found = {}
    for role in ROLES:
        want = target["roms"][role][3]
        names = by_hash.get(want)
        if names:
            found[role] = (sorted(names)[0], blobs[sorted(names)[0]])
    return found


# ------------------------------ patching ---------------------------------

def patch_rom(target, role, data, edits):
    canonical, base, half, want_sha1, want_sum = target["roms"][role]
    if len(data) != ROM_SIZE:
        raise Fail("%s %s is %d bytes, expected %d" % (target["name"], role, len(data), ROM_SIZE))
    if sha1(data) != want_sha1:
        raise Fail("%s %s does not match the expected stock dump" % (target["name"], role))

    out = bytearray(data)
    for off, value in edits.items():
        if not 0 <= off < ROM_SIZE:
            raise Fail("%s %s: patch offset 0x%X out of range" % (target["name"], role, off))
        out[off] = value

    fill = target["fill"][role]
    out[fill] = 0
    out[fill] = (want_sum - (sum(out) & 0xFF)) & 0xFF
    got = sum(out) & 0xFF
    if got != want_sum:
        raise Fail("%s %s: checksum signature 0x%02X, wanted 0x%02X"
                   % (target["name"], role, got, want_sum))
    return bytes(out)


# ------------------------------ reporting --------------------------------

def show_patch(groups, only=None):
    print("slapfree %s - patch listing (groups: %s)" % (VERSION, ", ".join(groups)))
    for target in TARGETS:
        if only and target["name"] != only:
            continue
        print("\n%s\n  %s" % (target["label"], "-" * 84))
        print("  %-9s %-6s %-8s %-14s  %s" % ("CPU", "ROM", "OFFSET", "WRITE", "PURPOSE"))
        for cpu_offset, hexbytes, group, comment in target["edits"]:
            if group not in groups:
                continue
            per = {}
            for role, off, value in split_edit(target, cpu_offset, bytes.fromhex(hexbytes)):
                per.setdefault(role, []).append((off, value))
            first = True
            for role in sorted(per):
                items = sorted(per[role])
                print("  %-9s %-6s 0x%04X   %-14s  %s" % (
                    ("0x%05X" % cpu_offset) if first else "",
                    role, items[0][0], " ".join("%02X" % v for _, v in items),
                    comment if first else ""))
                first = False
        print("  plus one checksum-compensation byte per device:")
        for role in ROLES:
            print("    %-6s 0x%04X   computed so the byte-sum's low byte stays 0x%02X"
                  % (role, target["fill"][role], target["roms"][role][4]))


# ------------------------------ main -------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="slapfree.py",
        description="Patch Race Drivin' program ROMs for slapstic-free hardware.",
        epilog="Patched images go in sockets 200R, 210R, 200S and 210S of the board they "
               "belong to. Every other EPROM, including 200Y and 210Y, is burned unchanged.")
    ap.add_argument("source", nargs="?", help="a ROM archive (.zip) or a folder of dumps")
    ap.add_argument("-o", "--out", default="slapstic-free", help="output directory (default: slapstic-free)")
    ap.add_argument("-t", "--target", choices=[t["name"] for t in TARGETS],
                    help="patch only this board type (default: every one recognised)")
    ap.add_argument("--minimal", action="store_true",
                    help="skip the self-test edits; the operator self-test will then "
                         "flag 200Y/210Y and 200S/210S")
    ap.add_argument("--no-y2k", action="store_true",
                    help="leave the year-2000 clock bug in place (it is fixed by default)")
    ap.add_argument("--mame-set", action="store_true",
                    help="also write a complete romset zip for testing in MAME")
    ap.add_argument("--show-patch", action="store_true", help="print every byte this tool writes, and exit")
    ap.add_argument("--check", action="store_true", help="verify the source dumps and report, without writing")
    ap.add_argument("-f", "--force", action="store_true", help="overwrite an existing output directory")
    ap.add_argument("--version", action="version", version="slapfree " + VERSION)
    args = ap.parse_args(argv)

    groups = ["core"]
    if not args.no_y2k:
        groups.append("y2k")
    if not args.minimal:
        groups.append("selftest")
    groups = tuple(groups)
    wanted = [t for t in TARGETS if not args.target or t["name"] == args.target]

    if args.show_patch:
        show_patch(groups, args.target)
        return 0
    if not args.source:
        ap.error("a source archive or folder is required")

    blobs = load_source(args.source)
    print("slapfree %s" % VERSION)
    print("source: %s  (%d files)\n" % (args.source, len(blobs)))

    hits = []
    for target in wanted:
        found = identify(blobs, target)
        if len(found) == 4:
            hits.append((target, found))
            print("  [found]   %-11s %s" % (target["name"], target["label"]))
            for role in ROLES:
                print("              %-6s %s" % (role, found[role][0]))
        elif found:
            print("  [partial] %-11s %d of 4 program ROMs present - skipped"
                  % (target["name"], len(found)))

    if not hits:
        print("  no supported board recognised in this source.\n")
        print("Files are matched by SHA-1, so names do not matter, but the contents must be")
        print("one of the sets below. Other revisions have the same code at shifted offsets;")
        print("this tool refuses them rather than guessing.")
        for t in TARGETS:
            print("\n  %s" % t["label"])
            for role in ROLES:
                canonical, _, _, want, _ = t["roms"][role]
                print("    %-6s %-20s sha1 %s" % (role, canonical, want))
        return 2

    if args.check:
        print("\n%d board type(s) verified. Nothing written (--check)." % len(hits))
        return 0

    if os.path.exists(args.out):
        if not args.force:
            raise Fail("%s already exists (use --force to overwrite)" % args.out)
        shutil.rmtree(args.out)
    os.makedirs(args.out)

    patched_by_sha1 = {}
    for target, found in hits:
        edit_map = build_edit_map(target, groups)
        outdir = os.path.join(args.out, target["name"])
        os.makedirs(outdir)
        written = []
        print("\n%s  (%s)" % (target["label"], " + ".join(groups)))
        for role in ROLES:
            data = patch_rom(target, role, found[role][1], edit_map[role])
            changed = sum(1 for a, b in zip(found[role][1], data) if a != b)
            patched_by_sha1[sha1(found[role][1])] = data
            if not changed:
                print("  %-6s -- unchanged by this patch, keep your existing EPROM" % role)
                continue
            name = "%s-noslapstic.bin" % role
            with open(os.path.join(outdir, name), "wb") as fh:
                fh.write(data)
            written.append(role)
            print("  %-6s -> %s/%-24s %2d bytes changed   crc32 %s  sum %02X"
                  % (role, target["name"], name, changed, crc32(data), sum(data) & 0xFF))
        note = "  burn into %s" % ", ".join(written)
        if target["name"] == "rdp-side":
            note += "   (two identical sets, one per side pod)"
        print(note)

    if args.mame_set:
        stem = os.path.basename(os.path.abspath(args.source))
        if stem.lower().endswith(".zip"):
            stem = stem[:-4]
        zpath = os.path.join(args.out, stem + ".zip")
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, data in sorted(blobs.items()):
                zf.writestr(name, patched_by_sha1.get(sha1(data), data))
        print("\n  test set -> %s" % zpath)
        print("  mame %s -rompath %s" % (stem, os.path.abspath(args.out)))
        print("  (MAME will warn about incorrect checksums; that is expected)")

    print("\nEvery other program EPROM - including 200Y and 210Y - is burned unchanged.")
    print("Remove the slapstic from its socket before fitting the four jumpers.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Fail as exc:
        print("error: %s" % exc, file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
