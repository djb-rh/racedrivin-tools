# Race Drivin' without the slapstic

Run Atari Race Drivin' — cockpit, compact, or Panorama — with the slapstic
removed from its socket.

Supported boards:

| target       | board                                  | chip           | qty |
|--------------|----------------------------------------|----------------|-----|
| `racedriv`   | Race Drivin' cockpit / compact main    | 137412-117     | 1   |
| `rdp-centre` | Panorama centre monitor, A045988       | 137412-115     | 1   |
| `rdp-side`   | Panorama side monitor, A046901         | 137412-115     | 2   |

A Panorama cabinet has three of these boards and therefore three slapstics.

## 1. The hardware change

Identical on every board. Take the slapstic **out** of its socket, then add four
jumpers between identically numbered pins on adjacent ROM sockets:

    200X pin 27  ->  200Y pin 27      (AB15 -> A14, bank bit 0)
    200X pin  1  ->  200Y pin  1      (AB16 -> A15, bank bit 1)
    210X pin 27  ->  210Y pin 27
    210X pin  1  ->  210Y pin  1

With the chip out of its socket, those two nets on 200Y/210Y are driven by
nothing else, so no traces need cutting and the change is reversible.

The bit order is not arbitrary. Bank n lives at ROM offset n * 0x8000, so A14
must come from AB15 and A15 from AB16. Swap them and the game will not boot.

## 2. The ROM change

    python3 slapfree.py racedriv.zip
    python3 slapfree.py /path/to/racedrivpan

Reads your own dump (a zip or a folder), patches whichever supported boards it
recognises, and writes the images to `<outdir>/<target>/`, one subfolder per board type. Nothing but
Python 3.8+ is required — no pip install, and it works the same on Windows,
macOS and Linux.

    --minimal      skip the self-test edits
    --no-y2k       leave the year-2000 clock bug alone (it is fixed by default)
    --target NAME  patch just one board type
    --mame-set     also build a romset to test in MAME
    --show-patch   print every byte it writes
    --check        verify your dump, write nothing

Default (`core + self-test`) changes four EPROMs per board: **200R, 210R, 200S,
210S**. `--minimal` changes only **200S and 210S**; the game runs identically,
but the operator self-test will report 200Y/210Y and 200S/210S as bad.

Every other program EPROM — **including 200Y and 210Y** — is burned unchanged
from your stock dump. For a Panorama, the two side pods take identical sets.

Source ROMs are matched by SHA-1, so filenames don't matter, but the contents
must be a set the tool knows.

## What the patch does

* the runtime accessor masks CPU address bits 15 and 16 out of every pointer
  into the banked region, because the hardware window sits at 0x0E0000. With
  flat decoding that mask is wrong; it is neutralised.
* the power-up probe halts with `BAD IC 137412-XXX` when it cannot identify a
  slapstic. That branch is made unconditional.
* twelve `lea` substitutions — the program-ROM checksum reads the same 32 KB
  window four times, relying on bank switching. Each pass is pointed at its own
  window instead. (Omitted by `--minimal`.)
* four compensation bytes — Atari's self-test compares the low byte of each
  EPROM's byte-sum against that ROM's own part-number suffix, so any patch has
  to be sum-neutral modulo 256. The tool recomputes these automatically.

`slapfree.py` contains no ROM data. It carries replacement instruction bytes and
hashes only, and cannot produce anything without your own dump as input.

## Status

**Confirmed working on real hardware.** A Race Drivin' Panorama main board running
the patched EPROMs, with the four jumpers fitted and no slapstic in socket 200K,
works correctly on the bench.

Verified in MAME 0.289 beforehand, against the stock slapstic hardware:

* **racedriv** - bit-identical video output through power-up, the full operator
  self-test, coin-in, track and car select, and driving. Re-checked with the
  year-2000 fix included: still 13/13 frames identical to a stock board.
* **Panorama, all three boards** - bit-identical through power-up and the entire
  operator self-test. Afterwards the attract sequence runs a fraction of a second
  out of step: the same screens, at a slightly different animation phase. That
  offset comes from the power-up probe finding no chip to identify and so
  executing fewer cycles; it is not caused by the ROM patch (the minimal and
  full patches produce identical output to each other).

Still untested on real hardware: the **side pods** (same modification, same
sockets, but nobody has done one yet) and the plain **racedriv** target.

Only the sets listed by `--show-patch` are supported. Other revisions have the
same code at shifted offsets — search for `02 80 FF FE 7F FF`, which occurs
exactly once per 1 MB image. The tool refuses unknown sets rather than guessing.

## Build guides

Step-by-step EPROM lists for each board type, generated from the actual images:

    build-guides/RDP-centre-board.md   Panorama centre board stack (31 EPROMs, 4 patched)
    build-guides/RDP-side-pod.md       Panorama side pod, x2       (22 EPROMs, 4 patched)

The centre-board guide ends with an appendix on **converting a Race Drivin' boardset
to Panorama** - what changes on each of the four boards, socket by socket.

Regenerate them after rebuilding the images with `python3 build-guides/generate.py`.

## Files

    slapfree.py               the tool - this is what you distribute
    README.md                 this file
    mame_pan_linear.lua       MAME harness (all three Panorama boards)
    mame_linear_decode.lua    MAME harness (single board)
    slapstic-free-racedriv/   build output for the cockpit/compact board
    slapstic-free-panorama/   build output for the three Panorama boards
                              (your patched images - local only, not distributable)
