"""Panorama pod stream on Serial B for Race Drivin' (cockpit or compact).

The Panorama's centre board tells its side pods where the car is over Serial A
(38400 8N1, `BA type body checksum`).  Race Drivin' has no such sender, but it
does have a complete, unused interrupt-driven transmitter for Serial B (J3).
This module lifts the Panorama's own packet builder out of the user's Panorama
program at build time, retargets it to the target program's variables and to
its Serial B routines, and calls it once per game frame - so the machine feeds
pods (or the open renderer) on J3 while Serial A stays free for a linked race.

Nothing here is ROM data: the code that is moved comes from the Panorama dump
the user supplies, exactly as the Stock Car track does.  Nothing about the
target program is assumed either: every routine and variable is found by
matching code against the Panorama's, so the cockpit and the compact programs
(and the Stock Car build) all go through the same path.

What is sent: type 01 (roster) whenever the track or the set of cars changes,
otherwise type 02 (camera position, 3x3 matrix, steering, the cars a pod could
see, including the other player in a linked race).  Menus, the track dial and the
heartbeat (types 04/05/06) are not sent.

Stand-alone use, for a stock program:

    python3 -m rdtrack.podlink RACEDRIV.zip RACEDRIVPAN.zip -o OUT --set cockpit|compact

writes the main-board EPROMs that change (byte sums preserved).  A folder of
already-modified EPROM files (a slapstic-free set, say) can follow the zips on
the command line; later sources win.  The Stock Car build has `--pods` instead.
"""
import argparse, os, re, struct, sys, zlib

# ---- the Panorama centre program (136088-1001..1016, v2.1) ---------------------------
PAN_BLOCK = (0x276A0, 0x27D6E)     # send(type) .. the car packer, one contiguous module
PAN_SEND, PAN_PICK = 0x276A0, 0x27770      # send(type); pick() -> 1 roster / 2 pose / 3
PAN_BLOCK_CRC = 0xAAB0F8A9         # a different Panorama revision stops the build
PAN_XLAT_SITES = (0x27888, 0x278EA)        # "move.w d0,d0 / ext.l d0 / move.b d0,d0" after the catalogue-index divide
PAN_MAXDIST = 0x46A4E              # long: how far away a car may be and still be sent
PAN_STUB_CALL = 0x2769C            # the empty routine the frame function calls just before the pod send
PAN_OBJTAB = 0x444CE

# game variables the module reads, located in the target by the code around each use
PAN_LINK_CAR = 0xFFECB2            # the linked opponent's car object; the Panorama's module ignores it, the glue reads it
PAN_GAME = {
    0xFF8044: "camera position",
    0xFF8054: "camera matrix",
    0xFF8140: "steering",
    0xFFA468: "car table",
    0xFFA438: "car count",
    0xFF9B6E: "track",
    0xFF9A51: "flags",
    PAN_LINK_CAR: "linked car",
}
PAN_FUNCS = {0x4EC02: "vector to object", 0x4E872: "rotate vector", 0x366F0: "matrix to angles"}
# the serial library: the module calls the channel A routines; the target's channel B twins replace them
PAN_SERIAL = {0x4EFA8: (0x4EFEE, 0x46, "putc"), 0x4F106: (0x4F14C, 0x22, "tx queue depth"), 0x240AA: (0x24158, 0x36, "write block")}
# the module's own working storage, and a second car table Race Drivin' does not have
PAN_PRIVATE = (0xFF8F7E, 0xFF9344)
PAN_TABLE2 = {0xFFDE24: 0x400, 0xFFDE25: 0x401, 0xFFDE26: 0x402}     # count, its low byte, the table
PAN_CHECKSUM = 0xFF9590

PRIVATE = 0x90F000                 # DSK RAM neither program touches (measured in MAME: attract, races, linked races)
CODE_END = 0x60000
GLUE = 42 + 14 + 4 + 0x100 + 2     # tick, xlat, the distance constant, the catalogue table, two sum pads

COCKPIT_MAIN = [("136077-5002.200r", "136077-5001.210r"), ("136077-5004.200s", "136077-5003.210s"),
                ("136077-5006.200t", "136077-5005.210t"), ("136077-4008.200u", "136077-4007.210u"),
                ("136077-4010.200v", "136077-4009.210v"), ("136077-1012.200w", "136077-1011.210w"),
                ("136077-1014.200x", "136077-1013.210x"), ("136077-1016.200y", "136077-4015.210y")]


def _addr_like(v):
    return (0xFF0000 <= v <= 0xFFFFFF) or v >= 0xFFFF0000 or (0x900000 <= v <= 0x91FFFF) or (0x800000 <= v <= 0x83FFFF) \
        or (0x600000 <= v <= 0x60FFFF) or (0xA00000 <= v <= 0xC0FFFF) or (0x400000 <= v <= 0x40FFFF) or (0x000200 <= v <= 0x0FFFFF)


def _pattern(img, lo, hi, also=()):
    """bytes lo..hi of img as a regex with every absolute address wildcarded"""
    wild = set(also)
    for j in range(lo - (lo & 1), hi - 3, 2):
        if _addr_like(struct.unpack_from(">I", img, j)[0]):
            wild.update(range(j, j + 4))
    return b"".join(b"." if j in wild else re.escape(img[j:j + 1]) for j in range(lo, hi))


def _sites(img, addr):
    pat, i, out = struct.pack(">I", addr), 0, []
    while True:
        i = img.find(pat, i, CODE_END)
        if i < 0:
            return out
        if i % 2 == 0:
            out.append(i)
        i += 2


def locate(pan, target, addr, before=14, after=14):
    """The target's equivalent of a Panorama address: match the code round every use
    with all absolute addresses wildcarded and take the vote.  -> (address, votes, uses)"""
    votes = {}
    uses = _sites(pan, addr)
    code = bytes(target[:CODE_END])
    for i in uses:
        lo = i - before
        pat = _pattern(pan, lo, i + 4 + after, also=range(i, i + 4))
        hits = [m.start() for m in re.finditer(pat, code, re.S) if m.start() % 2 == lo % 2]
        if len(hits) == 1:
            v = struct.unpack_from(">I", target, hits[0] + before)[0]
            votes[v] = votes.get(v, 0) + 1
    if not votes:
        return None, 0, len(uses)
    best = max(votes, key=votes.get)
    return best, votes[best], len(uses)


def twin(pan, target, addr, n, near=None):
    """The target's copy of the Panorama routine at `addr` (n bytes).  Routines that differ
    only in the addresses they use (the channel A and B halves of the serial library) match
    the same pattern, so the copy is picked by its position among the matches.  `near` =
    (Panorama address, target address) keeps the search inside the same library."""
    pat = _pattern(pan, addr, addr + n)
    mine = [m.start() for m in re.finditer(pat, bytes(pan[:CODE_END]), re.S) if m.start() % 2 == 0]
    theirs = [m.start() for m in re.finditer(pat, bytes(target[:CODE_END]), re.S) if m.start() % 2 == 0]
    if near:
        mine = [x for x in mine if abs(x - near[0]) < 0x600]
        theirs = [x for x in theirs if abs(x - near[1]) < 0x600]
    if addr not in mine or len(mine) != len(theirs):
        return None
    return theirs[mine.index(addr)]


def object_table(img):
    """(address, entries, names) of a program's object catalogue (28-byte entries, name pointer at +20)."""
    s = img.find(b"DOTLINE\0"); k = img.find(struct.pack(">I", s)); e = k - 0x14
    def ok(a): return 0x40000 < struct.unpack_from(">I", img, a + 0x14)[0] < 0x100000
    while ok(e - 28): e -= 28
    n = 0
    while ok(e + n*28): n += 1
    names = []
    for i in range(n):
        p = struct.unpack_from(">I", img, e + i*28 + 0x14)[0]
        names.append(bytes(img[p:img.index(b"\0", p)]).decode("ascii", "replace"))
    return e, n, names


def catalogue_map(target_names, pan_names):
    """256 bytes: the target's object index -> the Panorama's index for the same name."""
    where = {}
    for i, n in enumerate(pan_names):
        where.setdefault(n, i)
    return bytes(where.get(target_names[i], i) & 0xFF if i < len(target_names) else i for i in range(256))


def free_block(main, size):
    for a in range(0x20000, 0xE0000, 0x1000):
        if not any(main[a - 0x10:a + size + 0x10]):
            return a
    raise SystemExit("pod link: no free space in this program")


def apply(main, pan, target_names=None, pan_names=None, target_objtab=None, verbose=print, balance=False):
    """Patch the program image `main` (bytearray) in place.  `pan` is the Panorama centre
    program image.  The object catalogues are found if not given.  With `balance` the byte
    sums of every EPROM touched are restored using bytes this patch owns."""
    before = bytes(main)
    a, b = PAN_BLOCK
    block = bytearray(pan[a:b])
    if zlib.crc32(block) != PAN_BLOCK_CRC:
        raise SystemExit("pod link: this is not the Panorama centre program the pod module was located in")
    ptab, _pn, pnames = object_table(pan)
    if ptab != PAN_OBJTAB:
        raise SystemExit("pod link: Panorama object table not where expected")
    if target_objtab is None:
        target_objtab, _n, target_names = object_table(main)
    pan_names = pan_names or pnames
    dest = free_block(main, len(block) + GLUE)

    # --- where everything lives in the target ----------------------------------------------
    amap = {}
    for addr, what in list(PAN_GAME.items()) + list(PAN_FUNCS.items()) + [(PAN_STUB_CALL, "frame stub")]:
        got, votes, uses = locate(pan, main, addr)
        if got is None:
            raise SystemExit("pod link: cannot find this program's %s (Panorama 0x%06X)" % (what, addr))
        amap[addr] = got
        verbose("  pod link: %-18s Panorama %06X -> %06X  (%d of %d uses agree)" % (what, addr, got & 0xFFFFFF, votes, uses))
    anchor = None                                                     # putc comes first; the rest of the library sits beside it
    for chan_a, (chan_b, n, what) in PAN_SERIAL.items():
        got = twin(pan, main, chan_b, n, anchor if what == "tx queue depth" else None)
        if what == "putc" and got is not None:
            anchor = (chan_b, got)
        if got is None:
            raise SystemExit("pod link: cannot find this program's Serial B %s routine" % what)
        amap[chan_a] = got
        verbose("  pod link: %-18s Panorama %06X -> %06X  (Serial B twin)" % (what, chan_b, got))
    putc_b = amap[0x4EFA8]
    if bytes(main[putc_b + 0x24:putc_b + 0x26]) != b"\xd3\x39":          # add.b d1,<checksum accumulator>
        raise SystemExit("pod link: Serial B putc is not the expected routine")
    amap[PAN_CHECKSUM] = struct.unpack_from(">I", main, putc_b + 0x26)[0]
    amap[0xFF9B6F] = amap[0xFF9B6E] + 1
    amap[PAN_OBJTAB] = target_objtab
    for k, off in PAN_TABLE2.items():
        amap[k] = PRIVATE + off
    link_car = amap.pop(PAN_LINK_CAR)
    stub = amap.pop(PAN_STUB_CALL)
    if bytes(main[stub:stub + 2]) != b"\x4e\x75":
        raise SystemExit("pod link: the frame function's stub at 0x%05X is not empty" % stub)
    for j in range(0, CODE_END - 3, 2):
        if PRIVATE <= struct.unpack_from(">I", main, j)[0] < PRIVATE + 0x500 and \
                bytes(main[j - 2:j]) in (b"\x13\xfc", b"\x33\xfc", b"\x23\xfc", b"\x42\x79", b"\x42\xb9", b"\x4a\x79", b"\x4a\xb9"):
            raise SystemExit("pod link: this program already uses RAM at 0x%06X" % PRIVATE)

    # --- layout of the new code --------------------------------------------------------------
    tick = dest + len(block)       # 42 bytes
    xlat = tick + 42               # 14 bytes
    maxdist = xlat + 14            # one long
    table = maxdist + 4            # 256 bytes
    pads = table + 0x100           # two bytes, one per EPROM of the pair
    amap[PAN_MAXDIST] = maxdist
    t2count, t2entry = PRIVATE + PAN_TABLE2[0xFFDE24], PRIVATE + PAN_TABLE2[0xFFDE26]
    glue = bytearray()
    # The Panorama keeps a second car table Race Drivin' has no use for.  Fill its first
    # entry with the linked opponent, so a pod sees the other player as well as the drones.
    glue += b"\x20\x39" + struct.pack(">I", link_car)                 # tick: move.l linkcar,d0
    glue += b"\x23\xc0" + struct.pack(">I", t2entry)                  #       move.l d0,table2[0].object
    glue += b"\x56\xc0\x44\x00\x48\x80"                               #       sne d0 / neg.b d0 / ext.w d0   -> 0 or 1
    glue += b"\x33\xc0" + struct.pack(">I", t2count)                  #       move.w d0,table2.count
    glue += b"\x4e\xb9" + struct.pack(">I", dest + PAN_PICK - a)      #       jsr   pick     -> d0 = 1 roster / 2 pose
    glue += b"\x2f\x00"                                               #       move.l d0,-(a7)
    glue += b"\x4e\xb9" + struct.pack(">I", dest + PAN_SEND - a)      #       jsr   send
    glue += b"\x58\x8f\x4e\x75"                                       #       addq.l #4,a7 / rts
    assert len(glue) == xlat - tick
    glue += b"\x41\xfa" + struct.pack(">h", table - (xlat + 2))       # xlat: lea   table(pc),a0
    glue += b"\x02\x40\x00\xff"                                       #       andi.w #$ff,d0
    glue += b"\x10\x30\x00\x00"                                       #       move.b (a0,d0.w),d0
    glue += b"\x4e\x75"                                               #       rts
    assert len(glue) == maxdist - tick
    glue += struct.pack(">I", struct.unpack_from(">I", pan, PAN_MAXDIST)[0])
    glue += catalogue_map(target_names, pan_names)

    # --- retarget the module -------------------------------------------------------------
    moved = 0
    for j in range(0, len(block) - 3, 2):
        v = struct.unpack_from(">I", block, j)[0]
        if PAN_PRIVATE[0] <= v < PAN_PRIVATE[1]:
            new = v - PAN_PRIVATE[0] + PRIVATE
        elif v in amap:
            new = amap[v]
        else:
            continue
        struct.pack_into(">I", block, j, new); moved += 1
    for site in PAN_XLAT_SITES:                                       # catalogue index -> the Panorama's numbering
        o = site - a
        if bytes(block[o:o + 6]) != bytes.fromhex("300048c01000"):
            raise SystemExit("pod link: roster code not as expected at Panorama 0x%05X" % site)
        block[o:o + 6] = b"\x4e\xb9" + struct.pack(">I", xlat)
    left = sorted({struct.unpack_from(">I", block, j)[0] for j in range(0, len(block) - 3, 2)
                   if 0xFF8000 <= struct.unpack_from(">I", block, j)[0] <= 0xFFFFFF})
    if left:
        raise SystemExit("pod link: Panorama addresses left in the moved code: %s" % ", ".join("%06X" % v for v in left))
    calls = sorted({struct.unpack_from(">I", block, j + 2)[0] for j in range(0, len(block) - 5, 2)
                    if block[j:j + 2] in (b"\x4e\xb9", b"\x4e\xf9")})
    known = {amap[k] for k in PAN_SERIAL} | {xlat} | {amap[k] for k in PAN_FUNCS}
    if set(calls) - known:
        raise SystemExit("pod link: calls to unmapped routines: %s" % ", ".join("%06X" % v for v in sorted(set(calls) - known)))

    # --- install ---------------------------------------------------------------------------
    main[dest:dest + len(block)] = block
    main[tick:tick + len(glue)] = glue
    call = b"\x48\x78\x00\x03\x4e\xb9" + struct.pack(">I", stub)      # pea 3 / jsr stub, in the frame function
    hook = bytes(main[:CODE_END]).find(call)
    if hook < 0 or bytes(main[:CODE_END]).count(call) != 1:
        raise SystemExit("pod link: frame hook not found")
    struct.pack_into(">I", main, hook + 6, tick)
    if balance:
        # Restore each EPROM's byte sum.  The two bytes after the table are ours; in the
        # hooked pair the operand of "pea 3" is free, because nothing reads that argument now.
        spare = {dest >> 17: [pads, pads + 1]}
        spare.setdefault(hook >> 17, [hook + 2, hook + 3])
        for pair, (even, odd) in spare.items():
            lo = pair << 17
            for lane, at in ((0, even), (1, odd)):
                delta = (sum(main[lo + lane:lo + 0x20000:2]) - sum(before[lo + lane:lo + 0x20000:2])) & 0xFF
                main[at] = (main[at] - delta) & 0xFF
    verbose("  pod link: %d bytes of Panorama code at 0x%05X (%d addresses retargeted), tick 0x%05X hooked at 0x%05X, working RAM 0x%06X"
            % (len(block), dest, moved, tick, hook + 4, PRIVATE))
    return {"dest": dest, "tick": tick, "hook": hook + 4, "private": PRIVATE, "link_car": link_car, "map": amap}


def main(argv=None):
    from rdtrack import stockcar as sc
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sources", nargs="+", help="racedriv.zip, racedrivpan.zip, and optionally folders of modified EPROM files")
    ap.add_argument("-o", "--out", default="racedriv_pods")
    ap.add_argument("--set", choices=["cockpit", "compact"], default="cockpit", help="which stock program to patch (rev 5 of either)")
    ap.add_argument("--all", action="store_true", help="write all sixteen main-board EPROMs and main_image.bin, not only the ones that change")
    ap.add_argument("--romstack", action="store_true", help="also write the two 27C040 lane images for the ROM stack adapters")
    args = ap.parse_args(argv)
    blobs = sc.load_sources(args.sources)
    plist = COCKPIT_MAIN if args.set == "cockpit" else sc.COMPACT_MAIN
    # slapfree.py names its output by socket ("200R-noslapstic.bin"); let those replace the stock files
    for name in list(blobs):
        m = re.match(r"(2[01]0[R-Y])\b", name, re.I)
        if m:
            for e, o in plist:
                for n in (e, o):
                    if n.lower().endswith("." + m.group(1).lower()):
                        blobs[n] = blobs[name]
    missing = [n for p in plist + sc.PAN_MAIN for n in p if n not in blobs]
    if missing:
        sys.exit("missing ROMs: %s" % ", ".join(missing))
    prog = sc.pairs(blobs, plist); pan = sc.pairs(blobs, sc.PAN_MAIN)
    apply(prog, pan, balance=True)
    os.makedirs(args.out, exist_ok=True)
    wrote = []
    for n, data in sc.unpair(prog, plist).items():
        if args.all or data != blobs[n]:
            open(os.path.join(args.out, n), "wb").write(data); wrote.append(n)
            if (sum(data) - sum(blobs[n])) & 0xFF:
                sys.exit("byte sum of %s not preserved" % n)
    rows = "\n".join("| **%s** | `%s` | 27C512 | `%08X` | `%02X` |" % (n.rsplit(".", 1)[1].upper(), n, zlib.crc32(data) & 0xFFFFFFFF, sum(data) & 0xFF)
                     for n, data in sorted(sc.unpair(prog, plist).items()) if args.all or data != blobs[n])
    open(os.path.join(args.out, "README.md"), "w").write("""# Race Drivin' %s with the pod stream on Serial B

Built by `rdtrack.podlink --set %s`.  Burn these and fit them in the sockets named; every
other main-board EPROM stays as it was.  Byte sums are preserved, so the self-test's ROM
check still passes.

| Socket | File | Type | CRC32 | Byte sum |
|---|---|---|---|---|
%s

The program sends the Panorama side-pod packets (car position and orientation, steering, the
cars a pod could see, including the other player in a linked race) on **Serial B (J3)** at
38400 8N1.  Serial A (J2) is untouched, so the machine can still be linked head to head.
%s""" % (args.set, args.set, rows, "\nThe `*-lane*-27C040.bin` files are the ROM stack adapter images (banks R..Y of each lane).\n" if args.romstack else ""))
    wrote.append("README.md")
    if args.all:
        open(os.path.join(args.out, "main_image.bin"), "wb").write(bytes(prog))
    if args.romstack:
        from rdtrack import romstack as rs, stockcar_edits
        if stockcar_edits.is_free(bytes(prog)) is not True:
            sys.exit("--romstack needs a slapstic-free program: the ROM stack adapter bypasses the slapstic. "
                     "Run slapfree.py on the set first and put its output folder after the zips on this command line.")
        wrote += rs.write(args.out, sc.unpair(prog, plist), plist, "racedriv-%s-pods" % args.set)
    print("wrote %s: %s" % (args.out, ", ".join(sorted(wrote))))


if __name__ == "__main__":
    main()
