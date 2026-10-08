#!/usr/bin/env python3
"""Race Drivin' Panorama link decoder (centre board -> side pods, 38400 8N1, one-way).

Framing:  BA <type> <body> <checksum>, checksum = low byte of sum(type + body).
Body length is NOT fixed per type (the 2017-era note "02 -> 34" was the common
case only): frame by checksum + next byte being BA.  Decoded 2026-09-15 by
logging the centre board's DUART in MAME racedrivpan beside its draw list.

  01  roster       track u8, 00, count u8, then `count` object-catalogue ids: the
                   drone models for slots 0..count-1 (sent at race start; the
                   short 4-byte form 02 00 01 01 appears at boot)
  06  dial         s16: track the CHOOSE YOUR TRACK dial is on (-1/-3 = none)
  04  key          u8, sent when the car is confirmed
  05  heartbeat    00 00 while idle
  02  pose         the camera (player) pose plus the cars the PODS may need:
        s32 x, s32 y, s32 z                       world units (1/40 ft)
        9 x s16 orientation matrix, 1.14 fixed    columns are the car axes:
                                                  forward = (m[2], m[8]) in x,z
        s16 steer                                 signed, follows yaw rate
        u8  ncars                                 records that follow
        ncars x 11 bytes:
          u8  slot            index into the roster (model)
          56 bits packed BE:  x s20 | y u16 (quarter units) | z s20
          s8  pitch, s8 roll  (256ths of a turn, small)
          u8  heading         256ths of a turn; forward = (sin, cos) in x,z
        a slot that is not present carries x = 0x7FFFD (all-ones fields).
      Which cars are included: those in the SIDE sectors, roughly 30-110 degrees
      off the camera's forward axis on either side, at any distance - i.e. what a
      pod at yaw 53/80/106 could see.  Cars straight ahead (the centre's own view)
      and behind are NOT sent.  The race-start packet lists all slots once.

The pod's camera (measured on racedrivpans, 2026-09-15, phase0/podcam.lua):
  viewpoint block in ADSP data at 68k 0x80BFCE: u16 20000 (draw distance?),
  s32 x @0x80BFD2, s32 y @D6, s32 z @DA = the packet position, UNCHANGED (no
  seat offset); 9 x s16 matrix @0x80BFEA.  With the yaw/pitch option = 0 the
  matrix IS the packet matrix.  Columns are the car's axes: c0 = right,
  c1 = up, c2 = forward.  A pod at yaw a, pitch b (the option tables at ROM
  0x47420/0x47430, degrees) rotates the axes in the car's own frame:
      yaw:   c2' = cos a * c2 + sin a * c0,   c0' = cos a * c0 - sin a * c2
      pitch: c2' = cos b * c2 + sin b * c1,   c1' = cos b * c1 - sin b * c2
  (+53 = "RIGHT DISPLAY" turns the view toward c0; +pitch looks up.)
  The pod does NOT interpolate: camera and cars step once per pose packet
  (about every 5 frames while racing) about one frame after its last byte,
  and hold.  Cars are drawn at the record's x/y/z with the heading byte.
"""
import struct, sys


def frames(data):
    """-> [(offset, type, body)] framed by checksum; stray bytes are skipped."""
    out, i, n = [], 0, len(data)
    while i < n - 2:
        if data[i] != 0xBA:
            i += 1; continue
        t, found = data[i + 1], None
        for L in range(1, 200):
            e = i + 2 + L
            if e >= n:
                break
            if (t + sum(data[i + 2:e])) & 0xFF == data[e] and (e + 1 >= n or data[e + 1] == 0xBA):
                found = L; break
        if found is None:
            i += 1; continue
        out.append((i, t, bytes(data[i + 2:i + 2 + found]))); i += 3 + found
    return out


def s20(v): return v - (1 << 20) if v & (1 << 19) else v


def car(rec):
    v = int.from_bytes(rec[1:8], "big")
    x, y4, z = s20(v >> 36), (v >> 20) & 0xFFFF, s20(v & 0xFFFFF)
    if x == 0x7FFFD:
        return None
    return {"slot": rec[0], "x": x, "y": y4 * 4, "z": z,
            "pitch": struct.unpack("b", rec[8:9])[0], "roll": struct.unpack("b", rec[9:10])[0],
            "heading": rec[10] * 360.0 / 256}


def pose(body):
    if len(body) < 33:
        return None
    x, y, z = struct.unpack_from(">iii", body, 0)
    m = [v / 16384.0 for v in struct.unpack_from(">9h", body, 12)]
    steer, ncars = struct.unpack_from(">hB", body, 30)
    cars = [c for c in (car(body[33 + 11 * k:44 + 11 * k]) for k in range((len(body) - 33) // 11)) if c]
    return {"x": x, "y": y, "z": z, "m": m, "steer": steer, "ncars": ncars, "cars": cars}


def pod_view(p, yaw_deg=0.0, pitch_deg=0.0):
    """The pod's camera matrix for a decoded pose: columns rotated in the car frame."""
    import math
    m = p["m"]; c = [[m[0], m[3], m[6]], [m[1], m[4], m[7]], [m[2], m[5], m[8]]]   # c0 right, c1 up, c2 forward
    a, b = math.radians(yaw_deg), math.radians(pitch_deg)
    c0, c1, c2 = c
    c2, c0 = [math.cos(a) * f + math.sin(a) * r for f, r in zip(c2, c0)], [math.cos(a) * r - math.sin(a) * f for f, r in zip(c2, c0)]
    c2, c1 = [math.cos(b) * f + math.sin(b) * u for f, u in zip(c2, c1)], [math.cos(b) * u - math.sin(b) * f for f, u in zip(c2, c1)]
    return {"right": c0, "up": c1, "forward": c2, "x": p["x"], "y": p["y"], "z": p["z"]}


if __name__ == "__main__":
    data = open(sys.argv[1], "rb").read()
    pk = frames(data)
    import collections
    print("%d packets, %d bytes; by (type,len): %s" % (len(pk), len(data), sorted(collections.Counter((t, len(b)) for _, t, b in pk).items())))
    for off, t, b in pk:
        if t == 1: print("roster:", b.hex(" "))
    shown = 0
    for off, t, b in pk:
        if t == 2 and len(b) > 33 and shown < 5:
            p = pose(b); print("pose", p["x"], p["y"], p["z"], "steer", p["steer"], "cars", p["cars"]); shown += 1
