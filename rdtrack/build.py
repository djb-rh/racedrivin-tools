"""Stage a complete loose MAME set: the stock zip's files plus the two compiled DSK halves."""
import os, shutil, zipfile
from . import dsk


MAIN_PAIRS = [("136077-5002.200r", "136077-5001.210r"), ("136077-5004.200s", "136077-5003.210s"),
              ("136077-5006.200t", "136077-5005.210t"), ("136077-4008.200u", "136077-4007.210u"),
              ("136077-4010.200v", "136077-4009.210v"), ("136077-1012.200w", "136077-1011.210w"),
              ("136077-1014.200x", "136077-1013.210x"), ("136077-1016.200y", "136077-4015.210y")]


def main_image(romset):
    """The 68010 ROM as MAME maps it (even byte from the .200 file, odd from the .210)."""
    out = bytearray()
    for even, odd in MAIN_PAIRS:
        a, b = _read(romset, even), _read(romset, odd)
        pair = bytearray(len(a) * 2); pair[0::2], pair[1::2] = a, b
        out += pair
    return out


def _read(romset, name):
    if os.path.isdir(romset):
        return open(os.path.join(romset, name), "rb").read()
    with zipfile.ZipFile(romset) as z:
        return z.read(name)


def stage(romset, buf, out_dir, main=None, main_pairs=(5, 6)):
    """main: a modified 68010 image; the pairs listed (128 KB each) are rewritten from it."""
    out = os.path.join(out_dir, "racedriv")
    shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
    if os.path.isdir(romset):
        for n in os.listdir(romset):
            shutil.copy(os.path.join(romset, n), out)
    else:
        with zipfile.ZipFile(romset) as z:
            z.extractall(out)
    dsk.split(buf, out)
    if main is not None:
        for k in main_pairs:
            even, odd = MAIN_PAIRS[k]; chunk = main[k * 0x20000:(k + 1) * 0x20000]
            open(os.path.join(out, even), "wb").write(bytes(chunk[0::2]))
            open(os.path.join(out, odd), "wb").write(bytes(chunk[1::2]))
    return out
