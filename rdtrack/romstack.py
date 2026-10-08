"""ROM stack adapter images: one 27C040 per byte lane in place of eight 27C512s.

The adapter (a separate board project) sits in socket R of a lane and holds banks R..Y in
order, so a lane image is simply the eight EPROMs of that lane concatenated.  Only made
when asked for (`--romstack`); the full sixteen-EPROM set is always the primary output.
"""
import os


def lanes(files, plist):
    """files: {name: bytes}; plist: [(even_name, odd_name)] for banks R..Y -> {"200": bytes, "210": bytes}"""
    return {"200": b"".join(files[e] for e, _o in plist), "210": b"".join(files[o] for _e, o in plist)}


def write(out_dir, files, plist, prefix):
    os.makedirs(out_dir, exist_ok=True)
    out = []
    for lane, data in lanes(files, plist).items():
        if len(data) != 0x80000:
            raise SystemExit("lane %s is %d bytes, not 512 KB" % (lane, len(data)))
        n = "%s-lane%s-27C040.bin" % (prefix, lane)
        open(os.path.join(out_dir, n), "wb").write(data); out.append(n)
    return out
