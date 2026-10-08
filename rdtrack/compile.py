#!/usr/bin/env python3
"""Compile a track document into a DSK image.

    python3 -m rdtrack.compile doc.json out_dir [--fixed]

--fixed puts every structure back at the offset it was decompiled from (the
byte-identical round trip); otherwise everything above the front region is
laid out afresh from 0x011D0 up and every pointer regenerated.
"""
import json, os, struct, sys
from . import dsk

FRONT = 0x011D0
LIMIT = dsk.CHECKSUM_AT


class Layout:
    """Bump allocator over the free area, or a fixed-address map for the round trip."""
    def __init__(self, fixed):
        self.fixed = fixed
        self.cur = FRONT
        self.used = []

    def place(self, size, want=None, align=2):
        if want is not None and (self.fixed or want + size <= FRONT):
            # the front region is carried verbatim, so a structure that lives there
            # (route nodes, name tables, strings) is already in place
            a = want
        else:
            a = (self.cur + align - 1) // align * align
            self.cur = a + size
        if a + size > LIMIT:
            raise SystemExit("out of DSK space: need 0x%X, limit 0x%X" % (a + size, LIMIT))
        self.used.append((a, a + size))
        return a


def compile_doc(doc, fixed=False):
    buf = bytearray(dsk.SIZE)
    buf[:FRONT] = bytes.fromhex(doc["front"])
    L = Layout(fixed)
    ptr = lambda a: a + dsk.BASE68K

    # --- worlds: placements, grid headers, cell lists ------------------------
    world_at = {}
    for wid, w in doc["worlds"].items():
        at = w.get("at", {})
        pl = b"".join(dsk.enc_placement({k: (bytes.fromhex(v) if k == "rt" else v) for k, v in p.items()}) for p in w["placements"])
        pl += bytes.fromhex(w.get("tail", "ff" * 2 + "00" * 48))
        pa = L.place(len(pl), at.get("placements")); buf[pa:pa + len(pl)] = pl
        da = L.place(14, at.get("descriptor"))
        ga = L.place(dsk.CELL_SZ*len(w["cells"]), at.get("grid"))
        lists = []
        for k, c in enumerate(w["cells"]):
            e = dsk.enc_cell_list(c)
            la = L.place(len(e), at.get("lists", [None]*99)[k]); buf[la:la + len(e)] = e; lists.append(la)
        for k, c in enumerate(w["cells"]):
            buf[ga + dsk.CELL_SZ*k: ga + dsk.CELL_SZ*(k+1)] = dsk.enc_cell({"min": c["min"], "max": c["max"], "list_at": lists[k]})
        s, w6, w8 = w["desc_words"]
        buf[da:da + 14] = dsk.enc_descriptor({"placements": pa, "stride": s, "w6": w6, "w8": w8, "grid": ga})
        world_at[wid] = da

    # --- segment tables ---------------------------------------------------------
    seg_at = {}
    for sid, S in doc["segments"].items():
        e = dsk.enc_segments({"header": {"count": len(S["segs"]), "bias": S["bias"], "start": S["start"], "raw": bytes.fromhex(S["header_raw"])}, "segs": S["segs"]})
        a = L.place(len(e), S.get("at")); buf[a:a + len(e)] = e; seg_at[sid] = a

    # --- routes: circular doubly linked lists ----------------------------------------
    route_at = {}
    for rid, R in doc["routes"].items():
        n = len(R["nodes"]); ats = R.get("at", [None]*n)
        addrs = [L.place(dsk.NODE_SZ, ats[k]) for k in range(n)]
        for k, node in enumerate(R["nodes"]):
            rec = dict(node); rec["next"] = addrs[node["next"] if isinstance(node.get("next"), int) else (k+1) % n]
            pv = node.get("prev", k - 1)
            rec["prev"] = addrs[k] if pv == "self" else (addrs[pv % n] if isinstance(pv, int) and pv < FRONT and pv < n else pv)
            buf[addrs[k]:addrs[k] + dsk.NODE_SZ] = dsk.enc_node(rec)
        route_at[rid] = addrs[0]

    # --- name tables + strings --------------------------------------------------------
    names_at = {}
    for nid, N in doc["names"].items():
        strs = []
        for k, e in enumerate(N["entries"]):
            s = e["name"].encode("ascii") + b"\0"
            sa = L.place(len(s), N.get("str_at", [None]*99)[k], align=1); buf[sa:sa + len(s)] = s; strs.append(sa)
        table = b"".join(struct.pack(">I4H", ptr(strs[k]), *e["v"]) for k, e in enumerate(N["entries"]))
        a = L.place(len(table), N.get("at")); buf[a:a + len(table)] = table; names_at[nid] = a

    # --- track records: fixed fields into the verbatim record bytes ---------------------
    for t in doc["tracks"]:
        a = t["slot"] * dsk.TRACK_REC
        raw = bytearray(bytes.fromhex(t["record"]))
        b80 = bytes.fromhex(t["block80"])
        ba = L.place(len(b80), t.get("at", {}).get("block80")); buf[ba:ba + len(b80)] = b80
        for o, v in ((0x00, world_at[t["world"]]), (0x04, seg_at[t["segments"]]), (0x08, route_at[t["routes"][0]]),
                     (0x0C, route_at[t["routes"][1]]), (0x10, names_at[t["names"]]), (0x80, ba)):
            struct.pack_into(">I", raw, o, ptr(v))
        # the positioned entities (start line, gates) per route: 24-byte entries, type 0 ends the list
        if "entities" in t:
            ent_at = {}
            for r, ents in enumerate(t["entities"]):
                want = t.get("entities_at", [None, None])[r]
                if want in ent_at:
                    ea = ent_at[want]
                else:
                    blob = b"".join(struct.pack(">IHiiiIH", ptr(e["name_at"]), e["type"], e["x"], e["y"], e["z"], e.get("w18", 0), e["heading"]) for e in ents)
                    ea = L.place(len(blob), want); buf[ea:ea + len(blob)] = blob; ent_at[want] = ea
                struct.pack_into(">I", raw, 0x18 + 4*r, ptr(ea))
        for m in range(4):
            for k in range(4):
                struct.pack_into(">H", raw, 0x40 + (m*4 + k)*2, t["awards"][m][k])
        buf[a:a + dsk.TRACK_REC] = raw
    return buf, L


def main():
    doc = json.load(open(sys.argv[1])); out = sys.argv[2]; fixed = "--fixed" in sys.argv
    buf, L = compile_doc(doc, fixed)
    top = max(b for a, b in L.used)
    print("compiled: %s layout, top of data 0x%05X, %d bytes free below the checksum" % ("fixed" if fixed else "fresh", top, LIMIT - top))
    dsk.split(buf, out)
    open(os.path.join(out, "dsk_image.bin"), "wb").write(bytes(buf))
    print("wrote", out)


if __name__ == "__main__":
    main()
