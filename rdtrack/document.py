#!/usr/bin/env python3
"""The track document: everything in the DSK image that describes the tracks,
as plain JSON, decoupled from where it sits in the ROM.

    python3 -m rdtrack.document racedriv.zip out.json      # decompile (raw level)

Raw level: placements, cells, segments, routes, names and awards are carried
field-for-field; the unknown per-track blocks and the whole front region
(0x00000-0x011D0: track records, route nodes, name strings, the small opaque
blocks) are carried as bytes so a compile can reproduce the image exactly.
Pieces (parts.json) are a later layer on top of the placements.
"""
import hashlib, json, sys
from . import dsk

FRONT = 0x011D0          # everything below this is kept verbatim (minus the fields we own)


def decompile(buf):
    D = dsk.Dsk(buf)
    doc = {"format": "rdtrack-document/1",
           "front": bytes(buf[:FRONT]).hex(),
           "checksum_at": dsk.CHECKSUM_AT,
           "tracks": [], "worlds": {}, "segments": {}, "routes": {}, "names": {}}
    wid = {a: "ABC"[i] for i, a in enumerate(D.worlds)}
    sid = {a: "ABC"[i] for i, a in enumerate(D.segs)}
    rid = {a: "R%d" % i for i, a in enumerate(D.routes)}
    nid = {a: "N%d" % i for i, a in enumerate(D.names)}
    def entities(a):
        out = []
        while True:
            name_at, typ = dsk.off(dsk.u32(buf, a)), dsk.u16(buf, a + 4)
            x, y, z = (dsk.s32(buf, a + 6 + 4*k) for k in range(3))
            out.append({"name_at": name_at, "type": typ, "x": x, "y": y, "z": z, "w18": dsk.u32(buf, a + 0x12), "heading": dsk.u16(buf, a + 0x16)})
            if typ == 0:
                return out
            a += 24
    for i, t in enumerate(D.tracks):
        ent_at = [dsk.off(dsk.u32(buf, t["at"] + 0x18)), dsk.off(dsk.u32(buf, t["at"] + 0x1C))]
        doc["tracks"].append({"slot": i, "record": t["raw"].hex(), "entities": [entities(a) for a in ent_at], "entities_at": ent_at,
                              "world": wid[t["descriptor"]], "segments": sid[t["segments"]],
                              "routes": [rid[h] for h in t["route"]], "names": nid[t["names"]],
                              "awards": t["awards"],
                              "block80": bytes(buf[t["block80"]:t["block80"] + dsk.BLOCK80]).hex(),
                              "at": {"descriptor": t["descriptor"], "segments": t["segments"], "routes": t["route"],
                                     "names": t["names"], "block80": t["block80"]}})
    for a, w in D.worlds.items():
        d = w["descriptor"]
        end = d["placements"] + dsk.PLACE_SZ*len(w["placements"])
        doc["worlds"][wid[a]] = {"desc_words": [d["stride"], d["w6"], d["w8"]],
                                 # stock follows every placement array with one 50-byte terminator record
                                 # (object 0xFFFF); carried verbatim until something is known to read it
                                 "tail": bytes(buf[end:end + dsk.PLACE_SZ]).hex(),
                                 "at": {"descriptor": a, "placements": d["placements"], "grid": d["grid"],
                                        "lists": [c["list_at"] for c in w["cells"]]},
                                 "placements": [{k: (v.hex() if isinstance(v, bytes) else v) for k, v in p.items()} for p in w["placements"]],
                                 "cells": [{"min": c["min"], "max": c["max"], "recs": c["recs"]} for c in w["cells"]]}
    for a, S in D.segs.items():
        h = S["header"]
        doc["segments"][sid[a]] = {"at": a, "bias": h["bias"], "start": h["start"], "header_raw": h["raw"].hex(), "segs": S["segs"]}
    for h, R in D.routes.items():
        ats = [n["at"] for n in R]
        nodes = []
        for n in R:
            node = {k: v for k, v in n.items() if k not in ("at", "next", "prev")}
            # prev links are not the mirror of next: heads point at themselves or at an
            # orphan node in the front region.  Keep them as data: an index into this
            # list, "self", or a raw front-region offset.
            node["prev"] = ats.index(n["prev"]) if n["prev"] in ats and n["prev"] != n["at"] else ("self" if n["prev"] == n["at"] else n["prev"])
            nodes.append(node)
        doc["routes"][rid[h]] = {"at": ats, "nodes": nodes}
    for a, N in D.names.items():
        doc["names"][nid[a]] = {"at": a, "str_at": [e["str_at"] for e in N["entries"]],
                                "entries": [{"name": e["name"], "v": e["v"]} for e in N["entries"]]}
    return doc


def main():
    src, out = sys.argv[1], sys.argv[2]
    buf = dsk.load(src)
    doc = decompile(buf)
    doc["source_sha1"] = hashlib.sha1(bytes(buf)).hexdigest()
    json.dump(doc, open(out, "w"), indent=1)
    print("wrote %s: %d tracks, worlds %s, segment tables %s, routes %s" % (
        out, len(doc["tracks"]), {k: len(w["placements"]) for k, w in doc["worlds"].items()},
        {k: len(s["segs"]) for k, s in doc["segments"].items()}, {k: len(r["nodes"]) for k, r in doc["routes"].items()}))


if __name__ == "__main__":
    main()
