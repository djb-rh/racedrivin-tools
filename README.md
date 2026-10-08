# Race Drivin' ROM tools

Patch tools for running Atari **Race Drivin'** on real hardware with changes the factory never
offered: no slapstic, the Panorama's Stock Car track on a compact, and a side-pod data stream on
the spare serial port.  Everything here is a *patcher*: it reads your own ROM dumps (the MAME
sets `racedriv.zip` and `racedrivpan.zip`) and writes modified EPROM images.  No ROM data is in
this repository.

Targets are the two Race Drivin' boardsets:

| | Cockpit | Compact |
|---|---|---|
| Main board | A045988 ("driver" board) | A046901 (MultiSync) |
| Slapstic | 137412-117 at 200K | 137412-117 at 200K |
| Program | `racedriv` (rev 5) | `racedrivc` (rev 5) |

## Before you start

You do not need to be a programmer to use these.  Each tool is one command typed into a
terminal window, and the only software it needs is Python.

**What you need**

- A computer with **Python 3.8 or newer**.  Nothing else is installed: the tools use only
  what comes with Python, so there is no `pip install` step and no internet access needed
  once you have the files.
- **Your own ROM dumps**, as MAME-style zips: `racedriv.zip` (a merged set that also holds
  the compact ROMs, or the separate `racedrivc.zip` beside its parent) and, for the Stock
  Car and pod-stream builds, `racedrivpan.zip`.  The tools check the dumps against the
  known checksums and stop if a file is not the stock one.
- An **EPROM programmer** and blank chips: 27C512 for the main, ADSP and sound boards,
  27C010 for the Stock Car DSK pair, 27C040 (150 ns or faster) for ROM stack adapters.

**Which systems**

Plain Python, no platform-specific code, so it should run the same on **macOS, Windows and
Linux**.  It has only been **tested on macOS**.  If you run it elsewhere and something
breaks, open an issue with the command and the message.

**Setting up, step by step**

1. Install Python if you do not have it.
   - macOS: open Terminal and type `python3 --version`.  If it offers to install the
     command line tools, accept; otherwise get the installer from python.org.
   - Windows: install from python.org and tick **"Add python.exe to PATH"**.  In the
     commands below, type `py -3` where they say `python3`.
   - Linux: `sudo apt install python3` (or your distribution's equivalent); usually already there.
2. Download this repository: the green **Code** button above, then **Download ZIP**, and
   unzip it.  No git needed.
3. Put your ROM zips in the unzipped folder, next to `slapfree.py`.
4. Open a terminal **in that folder** (macOS: drag the folder onto the Terminal icon, or
   `cd` to it; Windows: right-click inside the folder, "Open in Terminal").
5. Type the command for the build you want (next section).  Output goes into a new folder
   (`-o` chooses the name).  The Stock Car and pod-stream builds put a README in it saying
   which file goes in which socket; `slapfree.py` names its files by socket
   (`200R-noslapstic.bin`) and prints the jumper instructions.
6. Burn the files that README lists, verify each chip in the programmer, and check the
   printed byte sum: its low byte matches the last two digits of the Atari part number
   (`136078-5002` sums to `..02`), which is also what the game's self-test checks.

The "Testing in MAME" section at the end is for people who build MAME from source; it is
not needed to make or burn a set.


## What you can build

(On Windows, replace `python3` with `py -3` in every command.)

| Build | Boardset | Command | Hardware status |
|---|---|---|---|
| Slapstic-free | cockpit, compact, Panorama | `python3 slapfree.py racedriv.zip` | proven on a Panorama centre board and in a slapstic-free compact |
| Compact + Stock Car track | compact | `python3 -m rdtrack.stockcar racedriv.zip racedrivpan.zip -o OUT --slapstic free` | **running on hardware** |
| Pod stream on Serial B | cockpit, compact | `python3 -m rdtrack.podlink racedriv.zip racedrivpan.zip -o OUT --set cockpit` (or `--set compact`, or `--pods` on the Stock Car build) | MAME only |
| ROM stack lane images | any slapstic-free build | add `--romstack` | the Stock Car images run on hardware |

The Y2K clock fix (Jed Margolin's) is folded into every slapstic-free build.

### Slapstic-free

Pull the slapstic and fit two jumpers (`200X pin 27 -> 200Y pin 27`, `200X pin 1 -> 200Y pin 1`;
the 210 lane shares those nets, so jumpering one lane is enough, four jumpers if you prefer).
Then burn the four EPROMs `slapfree.py` writes.  Details, including the Panorama's three
boards: [docs/slapfree.md](docs/slapfree.md) and [build-guides/](build-guides/).

### Compact + Stock Car

Puts the Panorama's Stock Car track (the speed track with stock-car traffic) in the compact's
Autocross slot.  Needs an **ADSP II** board (A047046, the six-socket one) because the stock-car
models go in 9H/9K, and two 27C010s on the DSK.  The output folder gets a README listing every
file's socket **by the names printed on the ADSP II** (`9/10H`, `10H`, ...), because MAME's file
names for those ROMs come from the older ADSP board and will send chips to the wrong sockets.
Details: [docs/stockcar.md](docs/stockcar.md).

`--slapstic free` is for a board with the chip pulled; `115` / `117` keep the chip.
`--pods` adds the Serial B pod stream; `--romstack` adds the two 27C040 lane images.

### Pod stream on Serial B

Makes the game send the Panorama side-pod packets (car position and orientation, the cars in
view, the other player in a linked race) out of **Serial B (J3)** at 38400 8N1, in the
Panorama's own format, while Serial A stays free for a linked race.  The code is lifted from
your Panorama dump at build time.  Verified in MAME only, end to end against an unmodified
Panorama pod program; not yet tried on real hardware.  Details and the method:
[docs/pod-stream-serial-b.md](docs/pod-stream-serial-b.md).

`--romstack` here needs a slapstic-free program; run `slapfree.py` first and put its output
folder after the two zips on the command line.

### Linked play

Needs no patch: both programs have the link game built in (operator option GAME TYPE).  Only
TX, RX and ground are needed between cabinets: J2-7, J2-6 and J2-4/5.  Neither program reads
the handshake or link-present lines outside the self-test.  [docs/linked-play-in-mame.md](docs/linked-play-in-mame.md)
shows two MAME instances racing each other.

## Testing in MAME

`mame/serial-b.patch` adds a `-mainpcb:rs232b` slot to MAME's Hard Drivin' driver so a patched
program's Serial B traffic can be watched; `mame/*.lua` are the scripts used for the linked
and pod tests; `tools/rdplink.py` decodes the pod stream.

## Checking a burn

Atari's self-test compares the low byte of each EPROM's byte sum with its part number, and the
tools preserve that, so PROGRAM ROM CHECKSUMS passes.  The exceptions are documented in each
output README (the Stock Car DSK pair, which the compact's test sums only half of).

## License

GPL-3.0.  Hardware findings behind these tools (schematics read, code traced, things measured
on real boards) are in the docs.
