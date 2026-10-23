# The MultiSync main board (A046901): what we learned on the bench

Findings from bringing up a Race Drivin' compact on A046901 boards of unknown history, read
from the schematic (the STUN Runner package SP-338 draws this exact board; the Hard Drivin'
package SP-327 is the *driver* board A045988) and from the compact program.  A046901 is the
standard main board for Race Drivin' Compact, Hard Drivin' Compact, STUN Runner, Steel Talons
and the Panorama's side pods; the same ROM layout and slapstic wiring as the driver board.

## The four diagnostic LEDs

| LED | Label | Lit means |
|---|---|---|
| CR6 | +5 V | power |
| CR10 | CLOCK | the 8 MHz CPU clock is present |
| CR11 | DTACK | the CPU is completing bus cycles (it is executing something) |
| CR12 | RUN | not held in reset; blinks if the watchdog keeps resetting the board |
| CR9 | IRQS | interrupts are being raised **and acknowledged** |

So "CR10, CR11, CR12 lit, CR9 dark" is not a dead board: the CPU is running with interrupts
masked.  Two things produce exactly that pattern:

- **The self-test input (J6-3) held low.**  The boot code checks it before anything else and
  the self-test runs polled on VBLANK with interrupts masked.  Check the test switch wiring
  first; unplug J6 and power up.
- **A persistent fault in first-stage boot** (a bus error loop).  Before it enables interrupts
  the program touches the ADSP, sound and DSK boards over the expansion bus, then the GSP.

The watchdog is a 30 Hz counter cleared by writes to $608000; by our reading of the drawing
it bites about 0.26 s after the last kick.  WD-DIS on the board disables it.

## Boot order, and which ROM stops it where

Reset ($21C in the R pair) masks interrupts, kicks the watchdog, touches ADSP ($818060),
sound ($840000, $84C000) and DSK ($85C8xx), tests the self-test bit, initialises the GSP (about
half a second), then jumps through the vector table at $20000 (S pair) into the main program
in the T pair, which clears RAM and DSK RAM, reads the DSK ROMs, and enables interrupts about
1.7 s after reset.  Measured in MAME by blanking one ROM pair at a time:

| CR9 behaviour | Cause |
|---|---|
| never lights | main pair R, S, T or U bad; or the self-test line low |
| on for about a second, then dark | Y pair bad or mis-banked (the slapstic jumpers), or the DSK pair bad or swapped |
| on for about six seconds, then dark | X pair bad |
| stays on | V and W do not affect boot; neither do the ADSP object ROMs |

When the program crashes it shows the error name (WATCH DOG RESET, BUSS ERROR, ADDRESS ERROR,
BAD POLY BUFF ERROR, ADSP TIME OUT ERROR, GSP HANDSHAKE ERROR, ASIC 65 TIMEOUT ...) and
restarts itself.  BAD POLY BUFF ERROR a few seconds after boot means the ADSP's polygon list
is malformed: in practice an ADSP object ROM in the wrong socket or a marginal expansion bus
ribbon cable (both happened to us, in that order).

## Self-test, and what to expect from a modified set

- **ADSP ROM CHECKSUMS** shows the sockets by their ADSP II names and expects, in the last
  two digits, `9/10H = 21`, `10H = 22`, `9/10K = 23`, `10K = 24`; 9H and 9K are "do not care".
  Full 16-bit sums of the stock-compact-derived chips: 9/10H `6A21`, 10H `CB22`, 9/10K `1923`,
  10K `A724`; the Panorama pair reads 9H `0022`, 9K `A121`.  Two values exchanged within a
  column means the two chips are in each other's sockets.
- **DSK ROM CHECKSUMS** sums only the first 64 KB of each chip and expects `..30` / `..31`.
  The 128 KB Stock Car images read `..4F` (30E) and `..1C` (10E) there: expected, and proof
  the chips are being read.  The summary screen then shows `XROM` in red and DSK BOARD ERROR.
- **PROGRAM ROM CHECKSUMS** passes on every set the tools write: Atari's convention is that
  the low byte of each EPROM's byte sum equals the part-number suffix, and the tools keep it.
- The ADSP II socket names are `9H`, `9/10H`, `10H` and `9K`, `9/10K`, `10K`.  MAME's file
  names (`.10h`, `.10j`, `.10k`, `.10l`) come from the older four-socket board: the `.10h` file
  belongs in **9/10H** and the `.10j` file in **10H**.

## Connectors

- **J6** (coin door): 1 COIN1, 2 COIN2, 3 SELF-TEST, 4 and 8 ground, 5 key, 6 and 7 coin
  counters, 9 DIAGN.  All inputs active low.
- **J5** (controls): 8 key / engine start, 9 abort / game start, 7 aux coin, 10 and 11 ground.
- **J1** (power): 2, 3, 10, 11 +5 V; 1, 5, 8, 12 ground; 4, 9 +15 V; 6, 7 the negative rail.
- **J2** Serial A and **J3** Serial B, same pinout: 7 transmit, 6 receive, 4 and 5 ground, 9 a
  switched copy of transmit, 10 **+12 V through 10 ohms (never a supply)**, 11 +12 V through
  220 ohms, switched, read back as "link present".  Both channels are set to 38400 8N1 at boot.
  Serial B is fitted on every Hard/Race Drivin' board; the stock games never use it.

## Linking two cabinets

Atari's link cable is a null modem between male DB-25s on each cabinet: J2-7 to pin 2, J2-6
to pin 3, J2-4 to pin 7, J2-5 to pin 1, J2-11 to pins 4 and 5 joined.  Neither the cockpit nor
the compact program ever reads the link-present or handshake inputs outside the self-test,
so **transmit, receive and ground are all a link needs** (J2-7, J2-6, J2-4/5).  The link game
is a stock feature: operator option GAME TYPE = LINKED GAME 1 on one machine and 2 on the other.

## NVRAM

200E is an MK48T02B-15 (Timekeeper, with the clock) and 210E an MK48Z02B-15 (plain Zeropower
RAM); modern equivalents M48T02-150PC1 and M48Z02-150PC1.  A blank or dead pair is not fatal:
the game comes up at INITIALIZE POT INPUTS and asks for a key turn.

## Video

The compact program sets 308 lines at 60.3 Hz, about 18.6 kHz horizontal (the cockpit runs
25 kHz).  A monitor or converter set up for the cockpit may show nothing even though the
board is running; do not read "no picture" as "no boot".
