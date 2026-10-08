# Slapstic-free Race Drivin' Panorama — centre board

How to build the centre-monitor board stack of a Race Drivin' Panorama with the
**137412-115** slapstic removed from socket 200K.

**31 EPROMs in total, of which 4 are patched.** Everything else is burned straight from a good stock dump — including **200Y and 210Y**, the pair the slapstic used to bank.

---

## 1. The hardware change

Take the slapstic **out** of socket **200K** — do not leave it fitted, or its
`BS0`/`BS1` outputs will fight the address bus. Then add four jumpers between
identically numbered pins on adjacent ROM sockets:

```
    200X pin 27  ->  200Y pin 27      (AB15 -> A14, bank bit 0)
    200X pin  1  ->  200Y pin  1      (AB16 -> A15, bank bit 1)
    210X pin 27  ->  210Y pin 27
    210X pin  1  ->  210Y pin  1
```

With the chip out of its socket those two nets on 200Y/210Y are driven by
nothing else, so **no traces need cutting** and the change is reversible.

The bit order is not arbitrary. Bank *n* lives at ROM offset *n* × 0x8000, so
A14 must come from AB15 and A15 from AB16. Swap them and the board will not boot.

---

## 2. EPROMs to burn

### Panorama Main PCB A045988

| Socket | Atari part | Image to burn | Type | CRC32 | CS | |
|---|---|---|---|---|---|---|
| **200R** | 136088-1002 | `rdp-centre/200R-noslapstic.bin` | 27512 | `2EDBACDE` | `0202` | **patched** |
| **200S** | 136088-1004 | `rdp-centre/200S-noslapstic.bin` | 27512 | `9C2E6F46` | `AA04` | **patched** |
| **200T** | 136088-1006 | `088-1006.bin` | 27512 | `1CAEB314` | `A006` | stock |
| **200U** | 136088-1008 | `088-1008.bin` | 27512 | `B0D60278` | `3408` | stock |
| **200V** | 136088-1010 | `088-1010.bin` | 27512 | `1B64BCE1` | `9410` | stock |
| **200W** | 136088-1012 | `088-1012.bin` | 27512 | `9A78B952` | `C312` | stock |
| **200X** | 136088-1014 | `088-1014.bin` | 27512 | `5B721420` | `9C14` | stock |
| **200Y** | 136088-1016 | `088-1016.bin` | 27512 | `E83A9C99` | `3C16` | stock |
| **210R** | 136088-1001 | `rdp-centre/210R-noslapstic.bin` | 27512 | `C4807C91` | `7301` | **patched** |
| **210S** | 136088-1003 | `rdp-centre/210S-noslapstic.bin` | 27512 | `B432F8B7` | `7403` | **patched** |
| **210T** | 136088-1005 | `088-1005.bin` | 27512 | `F23A73B8` | `3905` | stock |
| **210U** | 136088-1007 | `088-1007.bin` | 27512 | `C4FC82DC` | `4D07` | stock |
| **210V** | 136088-1009 | `088-1009.bin` | 27512 | `413F4110` | `EE09` | stock |
| **210W** | 136088-1011 | `088-1011.bin` | 27512 | `C5CD5491` | `5111` | stock |
| **210X** | 136088-1013 | `088-1013.bin` | 27512 | `C503B019` | `8F13` | stock |
| **210Y** | 136088-1015 | `088-1015.bin` | 27512 | `725806F3` | `E215` | stock |

### ADSP II PCB A047046-01 — unchanged

| Socket | Atari part | Image to burn | Type | CRC32 | CS | |
|---|---|---|---|---|---|---|
| **9H** | 136088-1022 | `088-1022.bin` | 27512 | `4F1E1C5D` | `0022` | stock |
| **9/10H** | 136088-1018 | `088-1018.bin` | 27512 | `11A0A8F5` | `6518` | stock |
| **10H** | 136088-1020 | `088-1020.bin` | 27512 | `311CEF99` | `BC20` | stock |
| **9K** | 136088-1021 | `088-1021.bin` | 27512 | `CE8E4886` | `A121` | stock |
| **9/10K** | 136088-1017 | `088-1017.bin` | 27512 | `D92251E8` | `4B17` | stock |
| **10K** | 136088-1019 | `088-1019.bin` | 27512 | `5BB00676` | `6219` | stock |

### DSK PCB A047724-01 — unchanged

| Socket | Atari part | Image to burn | Type | CRC32 | CS | |
|---|---|---|---|---|---|---|
| **30E** | — | `rdpd1026.bin` | 27C010 | `16572618` | `0626` | stock |
| **10E** | — | `rdpd1025.bin` | 27C010 | `57B8A266` | `4B25` | stock |

### Driver Sound PCB — unchanged

| Socket | Atari part | Image to burn | Type | CRC32 | CS | |
|---|---|---|---|---|---|---|
| **70N** | — | `rdps1032.bin` | 27512 | `33005F2A` | `A832` | stock |
| **45N** | — | `rdps1033.bin` | 27512 | `4FC800AC` | `E533` | stock |
| **65A** | 136052-1123 | `rdps1123.bin` | 27512 | `A88411DC` | `EE01` | stock |
| **55A** | 136052-1124 | `rdps1124.bin` | 27512 | `071A4309` | `5F02` | stock |
| **45A** | 136052-3125 | `rdps3125.bin` | 27512 | `856548FF` | `CC03` | stock |
| **30A** | 136052-1126 | `rdps1126.bin` | 27512 | `F46EF09C` | `2B09` | stock |
| **45C** | 136077-1017 | `rdps1017.bin` | 27512 | `E93129A3` | `DB09` | stock |

### Notes on the other boards

* The **ADSP II** board carries the same six EPROMs on every board in the cabinet,
  so a full Panorama needs three sets of these.
* The **DSK** board is fitted only to the centre board stack. Its two EPROMs are
  27C010s, not 27512s.
* Sockets **30F** and **10F** on the DSK board, and the DSK's own slapstic socket at
  **15A**, are for a second copy-protection scheme Atari designed but **never
  implemented** (per Jed Margolin). The parts were left on the bill of materials for a
  while, so some machines shipped with a 137412-115 in 15A and ROMs in 30F/10F that do
  nothing at all. On a Panorama they stay empty. The DSK ROM space is 256 KB and the
  board offers two ways to fill it: a pair of 27C010s at 30E/10E addressed linearly
  from PAB0-PAB16, or a pair of 27512s at 30E/10E plus a second, *slapstic-banked*
  pair at 30F/10F selected by /ROM0. Panorama takes the first route, so the DSK
  slapstic is never populated. (Race Drivin' needs only 128 KB and fits it in one
  27512 pair at 30E/10E; the Compact prototype `racedrivcp` is the set that does use
  30F/10F.)
* Location **30J** on the DSK board is *not* an EPROM — it is a TMS320P15 (the
  ASIC65 maths coprocessor) whose program lives in on-chip EPROM. It has never been
  dumped and cannot be replaced from a file.
* The **Driver Sound** board is fitted only to the centre stack.
* Sockets **200E** and **210E** hold a 48T02 and a 48Z02 timekeeper/NVRAM, not EPROMs.

---

## 3. What the patched EPROMs contain

Two independent changes, both produced by `slapfree.py`:

**The slapstic removal.** Two instructions in the S pair stop the code folding
CPU address bits 15/16 out of pointers into the banked ROM, and stop the power-up
probe halting when it finds no slapstic to identify. Twelve more in the R pair
point each pass of the program-ROM checksum at its own 32 KB window, so the
operator self-test still passes.

**Jed Margolin's year-2000 fix**, ported to this board. Four bytes in the R pair:

| What | Change |
|---|---|
| clock table, year field | start value `88` -> `00`, so the year wraps 00-99 rather than 88-99 |
| BCD compare | `ble.w` -> `bls.w`, so BCD years of 80 and above are not read as negative |
| century digits | `'1'` -> `'2'` and `'9'` -> `'0'`, so the clock screen reads 20xx |

Verified against Jed Margolin's own published 136077-5002 ROM: applying just the
`ble.w`/`bls.w` byte and recomputing the checksum byte reproduces his image
*exactly*, including his compensation value. The same four sites exist in all
three Panorama board images and are patched the same way.

The fix is applied by default. Pass `--no-y2k` to leave the clock bug alone.
As Jed notes, the timekeeper is then good until 2100.

---

## Labelling

The patch deliberately preserves Atari's checksum *signature* — the low byte of
each EPROM's byte sum still equals its part-number suffix, which is all the
self-test compares. The full 16-bit `CS` value does change, so the patched
images carry a different CS from the factory label. The `CS` column above is
the value for the image you are actually burning.

A label sheet for a stock set can be printed from the CS values below,
including the original CS values, if you want the factory numbers for comparison.

---

## Verification

Power up holding the self-test switch. The program ROM screen should read
**`PROGRAM ROM OK`** with all sixteen boxes filled — Y through R on both the 200
and 210 rows. A blank box means that EPROM's byte sum is wrong: either a bad burn,
or a stock image where a patched one belongs.

If the board shows **`BAD IC 137412-XXX`** and halts, the ROMs are stock, not
patched. If it boots but misbehaves once driving, check the four jumpers —
particularly that A14/A15 have not been swapped.

## Reversing it

Remove the four jumpers, refit the slapstic in 200K, and put the stock EPROMs
back in 200R/210R/200S/210S. Nothing else was altered.

---

## Status

**Confirmed working on real hardware.** A main board running these patched EPROMs
with the four jumpers fitted and no slapstic in 200K works correctly. Verified
first in MAME 0.289 against a stock slapstic board — bit-identical video output
from cold boot through the entire operator self-test — and then on the bench.

Patched images are produced by `slapfree.py` (one directory up) from your own
dump; it contains no ROM data itself. Regenerate with:

```bash
python3 slapfree.py racedrivpan.zip --out slapstic-free-panorama
```

---

## Appendix — converting a Race Drivin' boardset to Panorama

Determined by comparing the two ROM sets byte for byte, not by reading part
numbers. Of all the images in the two sets, only nine are identical.

| Board | ROMs | What changes |
|---|---|---|
| Main | 16 | **12 change.** 200W, 210W, 200Y and 210Y are byte-identical between the two games |
| ADSP II | 4 → **6** | **all change**, and two normally-empty sockets get populated |
| DSK | 2 | **both change**, and grow from 27512 to **27C010** |
| Driver Sound — program | 2 | **both change**, and grow from 27256 to **27512** |
| Driver Sound — samples | 5 | **nothing.** 65A, 55A, 45A, 30A and 45C are byte-identical |

### Main board, socket by socket

| Socket | Race Drivin' | Panorama centre | |
|---|---|---|---|
| **200R** | 136077-5002 | 136088-1002 | replace |
| **200S** | 136077-5004 | 136088-1004 | replace |
| **200T** | 136077-5006 | 136088-1006 | replace |
| **200U** | 136077-4008 | 136088-1008 | replace |
| **200V** | 136077-4010 | 136088-1010 | replace |
| **200W** | 136077-1012 | 136088-1012 | same image — leave it |
| **200X** | 136077-1014 | 136088-1014 | replace |
| **200Y** | 136077-1016 | 136088-1016 | same image — leave it |
| **210R** | 136077-5001 | 136088-1001 | replace |
| **210S** | 136077-5003 | 136088-1003 | replace |
| **210T** | 136077-5005 | 136088-1005 | replace |
| **210U** | 136077-4007 | 136088-1007 | replace |
| **210V** | 136077-4009 | 136088-1009 | replace |
| **210W** | 136077-1011 | 136088-1011 | same image — leave it |
| **210X** | 136077-1013 | 136088-1013 | replace |
| **210Y** | 136077-4015 | 136088-1015 | same image — leave it |

### The other boards

* **ADSP II** — Race Drivin' populates four object ROMs, Panorama populates six,
  and none are shared. The two extra go in sockets that are empty on a Race
  Drivin' board. Socket naming differs between sources, so check the silkscreen
  against the ADSP table above before fitting.
* **DSK** — both ROMs double in size, but the sockets are drawn on the DSK
  schematic as `27C512-170/27C010-170`, so the board takes either. No modification.
  Panorama gets its extra DSK capacity from the larger parts at 30E/10E, **not**
  by populating the banked pair at 30F/10F — those stay empty, along with the
  DSK's own slapstic socket at 15A.
* **Driver Sound** — the two 68000 program ROMs at **70N** and **45N** double in
  size. Pin 1 of both sockets is fed from an **E1/E2** link: **E1 = +5V** (VPP for
  a 27256), **E2 = A16** (which is ROM A15, for a 27512). One link serves both
  sockets. Panorama needs **E2** — but check before you cut anything, because
  boards are often already set there. The five sample ROMs are untouched.
* **ASIC65** — location 30J on the DSK board is **136077-1027 in both games**, so
  the one chip that has never been dumped does not need replacing for a conversion.
* **Slapstic** — a conversion would normally mean swapping the 200K chip from a
  **137412-117** to a **137412-115**. With the modification described above you
  need neither, which removes the hardest part to source.
  **And if you do want a 115, look at your DSK board first.** Atari left an
  abandoned second protection scheme on the bill of materials for a while, so
  many Race Drivin' boards shipped with a 137412-115 sitting in DSK socket 15A
  doing nothing whatsoever. On those machines the part needed to turn a Race
  Drivin' into a Panorama was already in the cabinet, one board away.
* **Side pods** are entirely additional hardware: two more Multisync boards, two
  more ADSP II boards, two monitors and the link harness. See the side pod guide.

### Caveats

This is a ROM-level comparison. It says nothing about board assembly numbers,
revisions, or whether the cabinet wiring, motor amp and control panel differ —
all of which a real conversion has to account for. Treat it as the ROM half of
the job.
