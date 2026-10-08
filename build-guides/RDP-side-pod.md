# Slapstic-free Race Drivin' Panorama — side pod

How to build a side-monitor board of a Race Drivin' Panorama with the **137412-115**
slapstic removed from socket 200K.

A Panorama has **two** of these, and they are identical — burn two sets.

**22 EPROMs in total, of which 4 are patched.** Everything else is burned straight from a good stock dump — including **200Y and 210Y**, the pair the slapstic used to bank.

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

### Multisync PCB A046901

| Socket | Atari part | Image to burn | Type | CRC32 | CS | |
|---|---|---|---|---|---|---|
| **200R** | 136088-2002 | `rdp-side/200R-noslapstic.bin` | 27512 | `6C787063` | `AC02` | **patched** |
| **200S** | 136088-2004 | `rdp-side/200S-noslapstic.bin` | 27512 | `6FF8D6F3` | `4604` | **patched** |
| **200T** | 136088-2006 | `088-2006.bin` | 27512 | `DE3A0C24` | `D406` | stock |
| **200U** | 136088-2008 | `088-2008.bin` | 27512 | `452D991C` | `BA08` | stock |
| **200V** | 136088-2010 | `088-2010.bin` | 27512 | `775BCA3D` | `FF10` | stock |
| **200W** | 136088-2012 | `088-2012.bin` | 27512 | `BACF08C0` | `2912` | stock |
| **200X** | 136088-2014 | `088-2014.bin` | 27512 | `3512537C` | `EB14` | stock |
| **200Y** | 136088-2016 | `088-2016.bin` | 27512 | `6A42B7E2` | `0D16` | stock |
| **210R** | 136088-2001 | `rdp-side/210R-noslapstic.bin` | 27512 | `4BCA391A` | `EA01` | **patched** |
| **210S** | 136088-2003 | `rdp-side/210S-noslapstic.bin` | 27512 | `3F4E1B4D` | `2303` | **patched** |
| **210T** | 136088-2005 | `088-2005.bin` | 27512 | `96AD705F` | `D305` | stock |
| **210U** | 136088-2007 | `088-2007.bin` | 27512 | `D6F526D3` | `2F07` | stock |
| **210V** | 136088-2009 | `088-2009.bin` | 27512 | `6AEDCCC5` | `1F09` | stock |
| **210W** | 136088-2011 | `088-2011.bin` | 27512 | `1E0C2F71` | `6E11` | stock |
| **210X** | 136088-2013 | `088-2013.bin` | 27512 | `8D7C4E80` | `DA13` | stock |
| **210Y** | 136088-2015 | `088-2015.bin` | 27512 | `334E2A3B` | `DF15` | stock |

### ADSP II PCB A047046-01 — unchanged

| Socket | Atari part | Image to burn | Type | CRC32 | CS | |
|---|---|---|---|---|---|---|
| **9H** | 136088-1022 | `088-1022.bin` | 27512 | `4F1E1C5D` | `0022` | stock |
| **9/10H** | 136088-1018 | `088-1018.bin` | 27512 | `11A0A8F5` | `6518` | stock |
| **10H** | 136088-1020 | `088-1020.bin` | 27512 | `311CEF99` | `BC20` | stock |
| **9K** | 136088-1021 | `088-1021.bin` | 27512 | `CE8E4886` | `A121` | stock |
| **9/10K** | 136088-1017 | `088-1017.bin` | 27512 | `D92251E8` | `4B17` | stock |
| **10K** | 136088-1019 | `088-1019.bin` | 27512 | `5BB00676` | `6219` | stock |

### Notes

* A side pod is display-only. It has a Multisync PCB and an ADSP II board, and
  **no DSK board, no sound board and no controls**. It renders the world from the
  car state broadcast by the centre board over the serial link (J2, Serial A) and
  will sit idle without that feed.
* The link is one-way, centre board → pods, 38400 8N1, so a pod never transmits.
* Each pod has its own **ADSP II** board needing the same six EPROMs.
* A pod's view angle lives in its NVRAM, not in the ROMs. `YAW ANGLE` and
  `PITCH ANGLE` are set from the pod's own operator screens; the factory values are
  +53° and −53°. Configuring a pod needs controls temporarily wired to it.
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

The modification is **identical** to the centre board's, which is confirmed working
on real hardware. The pod images themselves are verified in MAME 0.289 against a
stock slapstic board — bit-identical from cold boot through the whole operator
self-test — but **no pod has been done on real hardware yet.**

Patched images are produced by `slapfree.py` (one directory up) from your own
dump; it contains no ROM data itself. Regenerate with:

```bash
python3 slapfree.py racedrivpan.zip --out slapstic-free-panorama
```
