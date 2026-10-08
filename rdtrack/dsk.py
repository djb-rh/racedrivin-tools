#!/usr/bin/env python3
"""The DSK ROM pair (136077-4030.30e / 4031.10e) as structures.

    python3 -m rdtrack.dsk /path/to/racedriv.zip     # round-trip + coverage report

The two 64 KB halves interleave (4030 = even bytes) into one 128 KB image that
the 68010 sees at 0x940000.  Everything here is offsets into that image.
Every structure parses into plain dicts and encodes back to the identical
bytes; `coverage()` lists what the known structures account for and what is
still opaque.  Field meanings: NOTES.md / WORLD.md / PLAN.md.
"""
import os, struct, sys, zipfile

BASE68K = 0x940000
SIZE = 0x20000
PARTS = [("136077-4030.30e", 0x30), ("136077-4031.10e", 0x31)]   # name, byte-sum low byte
CHECKSUM_AT = 0x1C044          # one pad byte per half keeps the sum right
TRACK_REC = 0xA4               # 164-byte track records at 0x00000: speed/stunt, autocross, super stunt
NTRACKS = 3
BLOCK80 = 0x300                # each record's +0x80 block is 768 bytes; the three end at the checksum byte
PLACE_SZ, CELL_SZ, SEG_SZ, NODE_SZ, NAME_SZ = 50, 28, 64, 26, 12

u16 = lambda b, o: struct.unpack_from(">H", b, o)[0]
s16 = lambda b, o: struct.unpack_from(">h", b, o)[0]
u32 = lambda b, o: struct.unpack_from(">I", b, o)[0]
s32 = lambda b, o: struct.unpack_from(">i", b, o)[0]


def sw32(b, o):
    """s32 stored LOW WORD FIRST (segment records, DSP32C convention)."""
    return struct.unpack(">i", bytes([b[o+2], b[o+3], b[o], b[o+1]]))[0]


def psw32(v):
    w = struct.pack(">i", v)
    return bytes([w[2], w[3], w[0], w[1]])


def is_ptr(v):
    return BASE68K <= v < BASE68K + SIZE


def off(v):
    """68k address -> image offset (None if not a DSK pointer)."""
    return v - BASE68K if is_ptr(v) else None


# ---------------------------------------------------------------- loading ---
def load(path):
    """Interleave the two halves from a MAME zip, a directory, or a directory of patched halves."""
    if os.path.isdir(path):
        rd = lambda n: open(os.path.join(path, n), "rb").read()
    else:
        z = zipfile.ZipFile(path); rd = z.read
    a, b = rd(PARTS[0][0]), rd(PARTS[1][0])
    buf = bytearray(len(a) * 2); buf[0::2] = a; buf[1::2] = b
    return buf


def split(buf, out_dir):
    """Write the two halves with their checksum bytes fixed.  Returns the paths."""
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for phase, (name, want) in enumerate(PARTS):
        half = bytearray(buf[phase::2])
        half[CHECKSUM_AT // 2] = 0
        half[CHECKSUM_AT // 2] = (want - (sum(half) & 0xFF)) & 0xFF
        p = os.path.join(out_dir, name); open(p, "wb").write(bytes(half)); paths.append(p)
    return paths


# ------------------------------------------------------------- structures ---
def track_record(buf, i):
    a = i * TRACK_REC
    r = {"at": a, "raw": bytes(buf[a:a + TRACK_REC])}
    r["descriptor"] = off(u32(buf, a + 0x00))
    r["segments"] = off(u32(buf, a + 0x04))
    r["route"] = [off(u32(buf, a + 0x08)), off(u32(buf, a + 0x0C))]
    r["names"] = off(u32(buf, a + 0x10))
    r["awards"] = [[u16(buf, a + 0x40 + (m*4 + k)*2) for k in range(4)] for m in range(4)]
    r["block80"] = off(u32(buf, a + 0x80))
    r["ptrs"] = {o: off(u32(buf, a + o)) for o in range(0, TRACK_REC, 4) if is_ptr(u32(buf, a + o))}
    return r


def enc_track_record(r):
    raw = bytearray(r["raw"])
    for o, v in ((0x00, r["descriptor"]), (0x04, r["segments"]), (0x08, r["route"][0]), (0x0C, r["route"][1]), (0x10, r["names"])):
        struct.pack_into(">I", raw, o, v + BASE68K)
    for m in range(4):
        for k in range(4):
            struct.pack_into(">H", raw, 0x40 + (m*4 + k)*2, r["awards"][m][k])
    return bytes(raw)


def descriptor(buf, a):
    return {"at": a, "placements": off(u32(buf, a)), "stride": u16(buf, a + 4),
            "w6": u16(buf, a + 6), "w8": u16(buf, a + 8), "grid": off(u32(buf, a + 10))}


def enc_descriptor(d):
    return struct.pack(">IHHHI", d["placements"] + BASE68K, d["stride"], d["w6"], d["w8"], d["grid"] + BASE68K)


def placement(buf, a):
    return {"obj": u16(buf, a), "m": [s16(buf, a + 2 + 2*k) for k in range(9)],
            "x": s32(buf, a + 0x14), "y": s32(buf, a + 0x18), "z": s32(buf, a + 0x1C),
            "bias": s16(buf, a + 0x20), "flags": u16(buf, a + 0x22),
            "rt": bytes(buf[a + 0x24:a + 0x30]), "w30": u16(buf, a + 0x30)}


def enc_placement(p):
    return struct.pack(">H9hiiihH", p["obj"], *p["m"], p["x"], p["y"], p["z"], p["bias"], p["flags"]) + p["rt"] + struct.pack(">H", p["w30"])


def cell(buf, a):
    lp = off(u32(buf, a + 0x18))
    recs, p = [], lp
    while u16(buf, p) != 0xFFFF:
        recs.append(u16(buf, p) // PLACE_SZ); p += 2
    return {"at": a, "min": [s32(buf, a + 4*k) for k in range(3)], "max": [s32(buf, a + 12 + 4*k) for k in range(3)],
            "list_at": lp, "recs": recs}


def enc_cell(c):
    return struct.pack(">6iI", *c["min"], *c["max"], c["list_at"] + BASE68K)


def enc_cell_list(c):
    return b"".join(struct.pack(">H", r * PLACE_SZ) for r in c["recs"]) + b"\xff\xff"


def world(buf, desc_at):
    d = descriptor(buf, desc_at)
    # headers run until the first cell list begins (16 for the 4x4 worlds, 1 for autocross)
    ncells, nearest = 0, SIZE
    while d["grid"] + CELL_SZ*ncells < nearest:
        p = off(u32(buf, d["grid"] + CELL_SZ*ncells + 0x18))
        if p is None:
            break
        nearest = min(nearest, p); ncells += 1
    cells = [cell(buf, d["grid"] + CELL_SZ*k) for k in range(ncells)]
    n = max(r for c in cells for r in c["recs"]) + 1
    pl = [placement(buf, d["placements"] + PLACE_SZ*k) for k in range(n)]
    return {"descriptor": d, "placements": pl, "cells": cells}


def segment(buf, a):
    return {"x": sw32(buf, a), "z": sw32(buf, a + 4), "elev": sw32(buf, a + 8),
            "m": [s16(buf, a + 0x0C + 2*k) for k in range(9)], "w1E": u16(buf, a + 0x1E),
            "flags": sw32(buf, a + 0x20),
            "ahead": s16(buf, a + 0x24), "w26": u16(buf, a + 0x26), "behind": s16(buf, a + 0x28), "w2A": u16(buf, a + 0x2A),
            "laneL": s16(buf, a + 0x2C), "w2E": u16(buf, a + 0x2E), "laneR": s16(buf, a + 0x30), "w32": u16(buf, a + 0x32),
            "hi": s16(buf, a + 0x34), "w36": u16(buf, a + 0x36), "lo": s16(buf, a + 0x38), "w3A": u16(buf, a + 0x3A),
            "edgeL": s16(buf, a + 0x3C), "edgeR": s16(buf, a + 0x3E)}


def enc_segment(s):
    return (psw32(s["x"]) + psw32(s["z"]) + psw32(s["elev"]) + struct.pack(">9hH", *s["m"], s["w1E"]) + psw32(s["flags"])
            + struct.pack(">hHhHhHhHhHhHhh", s["ahead"], s["w26"], s["behind"], s["w2A"], s["laneL"], s["w2E"], s["laneR"], s["w32"],
                          s["hi"], s["w36"], s["lo"], s["w3A"], s["edgeL"], s["edgeR"]))


def segments(buf, a):
    """Header record 0 (count, bias, start) then `count` segments."""
    hdr = {"count": sw32(buf, a), "bias": sw32(buf, a + 4), "start": sw32(buf, a + 8), "raw": bytes(buf[a + 12:a + SEG_SZ])}
    return {"at": a, "header": hdr, "segs": [segment(buf, a + SEG_SZ*(k + 1)) for k in range(hdr["count"])]}


def enc_segments(S):
    h = S["header"]
    return psw32(h["count"]) + psw32(h["bias"]) + psw32(h["start"]) + h["raw"] + b"".join(enc_segment(s) for s in S["segs"])


def route(buf, head):
    out, seen, a = [], set(), head
    while a is not None and a not in seen:
        seen.add(a)
        out.append({"at": a, "value": u16(buf, a), "value2": u16(buf, a + 2), "w4": u32(buf, a + 4), "flags": u16(buf, a + 8),
                    "next": off(u32(buf, a + 0x0A)), "wE": u32(buf, a + 0x0E), "prev": off(u32(buf, a + 0x12)), "w16": u32(buf, a + 0x16)})
        a = out[-1]["next"]
    return out


def enc_node(n):
    return struct.pack(">HHIHIIII", n["value"], n["value2"], n["w4"], n["flags"], n["next"] + BASE68K, n["wE"], n["prev"] + BASE68K, n["w16"])


def names(buf, a):
    out = []
    while True:
        sp = off(u32(buf, a + NAME_SZ*len(out)))
        if sp is None:
            break
        e = buf.index(b"\0", sp)
        out.append({"str_at": sp, "name": buf[sp:e].decode("ascii", "replace"), "v": [u16(buf, a + NAME_SZ*len(out) + 4 + 2*k) for k in range(4)]})
    return {"at": a, "entries": out}


def enc_names(N):
    return b"".join(struct.pack(">I4H", e["str_at"] + BASE68K, *e["v"]) for e in N["entries"])


# --------------------------------------------------------------- the image ---
class Dsk:
    def __init__(self, buf):
        self.buf = bytearray(buf)
        self.tracks = [track_record(buf, i) for i in range(NTRACKS)]
        self.worlds = {t["descriptor"]: world(buf, t["descriptor"]) for t in self.tracks}
        self.segs = {t["segments"]: segments(buf, t["segments"]) for t in self.tracks}
        self.routes = {}
        for t in self.tracks:
            for h in t["route"]:
                if h not in self.routes:
                    self.routes[h] = route(buf, h)
        self.names = {t["names"]: names(buf, t["names"]) for t in self.tracks}

    def spans(self):
        """(start, end, label, encoded bytes) for every structure we can re-emit."""
        out = []
        for i, t in enumerate(self.tracks):
            out.append((t["at"], t["at"] + TRACK_REC, "track record %d" % i, enc_track_record(t)))
        for a, w in self.worlds.items():
            d = w["descriptor"]
            out.append((a, a + 14, "descriptor", enc_descriptor(d)))
            pa = d["placements"]
            out.append((pa, pa + PLACE_SZ*len(w["placements"]), "placements x%d" % len(w["placements"]), b"".join(enc_placement(p) for p in w["placements"])))
            out.append((d["grid"], d["grid"] + CELL_SZ*len(w["cells"]), "grid x%d" % len(w["cells"]), b"".join(enc_cell(c) for c in w["cells"])))
            for k, c in enumerate(w["cells"]):
                e = enc_cell_list(c); out.append((c["list_at"], c["list_at"] + len(e), "cell list %d" % k, e))
        for i, t in enumerate(self.tracks):
            b = t["block80"]; out.append((b, b + BLOCK80, "+0x80 block %d (opaque)" % i, bytes(self.buf[b:b + BLOCK80])))
        for a, S in self.segs.items():
            e = enc_segments(S); out.append((a, a + len(e), "segments x%d" % S["header"]["count"], e))
        for h, R in self.routes.items():
            for n in R:
                out.append((n["at"], n["at"] + NODE_SZ, "route node", enc_node(n)))
        for a, N in self.names.items():
            e = enc_names(N); out.append((a, a + len(e), "name table", e))
            for en in N["entries"]:
                s = en["name"].encode() + b"\0"; out.append((en["str_at"], en["str_at"] + len(s), "name string", s))
        return sorted(out)

    def roundtrip(self):
        """Every structure re-encodes to the bytes it was read from.  Returns the mismatches."""
        bad = []
        for a, b, label, enc in self.spans():
            if bytes(self.buf[a:b]) != enc:
                bad.append((a, label))
        return bad

    def coverage(self):
        """Merge the known spans; return (known, gaps) as lists of (start, end, label)."""
        known, gaps = [], []
        cur = 0
        for a, b, label, _e in self.spans():
            if a > cur:
                gaps.append((cur, a))
            known.append((a, b, label)); cur = max(cur, b)
        if cur < SIZE:
            gaps.append((cur, SIZE))
        return known, gaps


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "racedriv.zip"
    D = Dsk(load(src))
    bad = D.roundtrip()
    print("round trip: %d structures, %d mismatches %s" % (len(D.spans()), len(bad), bad[:5]))
    known, gaps = D.coverage()
    total = sum(b - a for a, b, _l in known)
    print("known: %d bytes (%.1f%%) in %d spans" % (total, 100.0*total/SIZE, len(known)))
    print("gaps:")
    for a, b in gaps:
        nz = sum(1 for x in D.buf[a:b] if x)
        print("  0x%05X..0x%05X  %6d bytes, %6d non-zero" % (a, b, b - a, nz))
    for i, t in enumerate(D.tracks):
        d = D.worlds[t["descriptor"]]["descriptor"]
        print("track %d descriptor @0x%05X: placements 0x%05X stride %d w6 %d w8 %d grid 0x%05X; other ptrs %s" % (
            i, d["at"], d["placements"], d["stride"], d["w6"], d["w8"], d["grid"],
            {"+0x%02X" % o: "0x%05X" % v for o, v in sorted(t["ptrs"].items()) if o not in (0, 4, 8, 0xC, 0x10, 0x80)}))
    for i, t in enumerate(D.tracks):
        w = D.worlds[t["descriptor"]]; S = D.segs[t["segments"]]
        print("track %d: %d placements in %d cells, %d segments (start %d), routes %s, names %s" % (
            i, len(w["placements"]), len(w["cells"]), S["header"]["count"], S["header"]["start"],
            [len(D.routes[h]) for h in t["route"]], [e["name"] for e in D.names[t["names"]]["entries"]]))


if __name__ == "__main__":
    main()
