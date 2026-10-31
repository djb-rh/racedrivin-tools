# Race Drivin' hardware project: status

Last updated 2026-10-30. Donnie Barnes (djb-rh on GitHub). This page is kept in the racedrivin-tools repository and regenerated in forum formats from one source; the newest copy is always at https://github.com/djb-rh/racedrivin-tools/blob/main/STATUS.md (BBCode: STATUS.bbcode, HTML: STATUS.html, same folder).

## What this is

A set of open tools, documents and hardware for keeping Atari's Hard Drivin' / Race Drivin' / Race Drivin' Panorama cabinets running and extending what they can do: run without the slapstic security chip, put the Panorama's Stock Car track on a compact, send the side-pod data stream out of the spare serial port, build custom tracks, render the game's world on modern screens, and replace the whole Atari board stack with a MiSTer FPGA core and a custom cabinet interface board.

Everything is a patcher or a tool. The repositories contain no ROM data; each tool reads your own MAME-style ROM zips and checks them against the known checksums.

## Where to find the published work

- **racedrivin-tools** (the hardware-ready tools, start here): https://github.com/djb-rh/racedrivin-tools. Slapstic removal, compact + Stock Car, pod stream on Serial B, ROM stack lane images, bench notes for the MultiSync board, build guides for every Panorama board, linked-play notes. Plain Python 3, no packages to install; the README walks non-programmers through it.
- **rdp-fullscreen** (track tools and research notes): https://github.com/djb-rh/rdp-fullscreen. The DSK track compiler and library, the browser track editor, the east-loop speed-track mod, the artwork and 3D mesh tools, MAME Lua scripts, and NOTES.md with every ROM-format finding in date order.
- **rdp-renderer** (open side-pod renderer): https://github.com/djb-rh/rdp-renderer. Swift package plus Mac viewer and iOS app that draw the Panorama's pod view from the cabinet's 38400-baud link. MIT licence.
- **Arcade-RaceDrivin_MiSTer** (the FPGA core): https://github.com/djb-rh/Arcade-RaceDrivin_MiSTer. First cockpit release 2026-10-27 (RBF and MRAs in releases/), the DSP32C core, the whole-core simulation harness, and the cabinet interface board plan in docs/.
- **t48-for-tab5** (the programmer all of this was burned with): https://github.com/djb-rh/t48-for-tab5. A stand-alone EPROM/flash programmer built from an M5Stack Tab5 and an XGecu T48, with a Wi-Fi file manager, hex editor and One ROM support.
- **USB-C cable end caps** (3D print): https://makerworld.com/en/models/3375604-usb-c-cable-end-caps. Cover the metal shells of cables left plugged into One ROMs on a live board.
- Upstream work this builds on: Fulviuus' Hard Drivin' MiSTer core https://github.com/retrogarage/harddrivin-mister; Jed Margolin's Hard Drivin' pages, schematics and Y2K fix https://www.jmargolin.com; MAME's harddriv driver, the behavioural reference for all of it.

## Done

### ROM tools, proven on real hardware

- **Slapstic removal** (slapfree.py). The 137412-117/115 chip at 200K only banks the 200Y/210Y pair, and the game already addresses that region linearly, so two nets jumpered from a program ROM into the empty socket plus 81 patched bytes replace it. The operator self-test stays clean and every EPROM keeps its byte sum (the low byte matches the Atari part number). Covers the cockpit, the compact, and all three Panorama boards. Jed Margolin's Y2K clock fix is folded in and reproduces his published ROM byte for byte. Proven on a Panorama centre board and on compact hardware.
- **Compact + Stock Car** (rdtrack.stockcar). The Panorama's Stock Car track in the compact's Autocross slot: 33 EPROMs, needs the six-socket ADSP II board (A047046) and two 27C010s on the DSK. Running on an A046901 MultiSync stack since 2026-10-04. The output README names ADSP sockets as printed on the board (9/10H, 10H ...) because MAME's file names for those ROMs point at the wrong sockets.
- **ROM stack adapter** (romstack). A small board that plugs into one 27C512 socket and holds a 27C040 or a 32-pin One ROM carrying all eight banks of a lane, a 74LS148 encoding the chip selects into A16-A18. Two per main board. Works on hardware on a Panorama centre board (2026-09-27) with 27C040s and with One ROMs; the lane images come from the tools with the --romstack option.
- **Linked play, documented.** Both programs have the link game built in (operator option GAME TYPE). Only TX, RX and ground are needed between cabinets; neither program reads the handshake lines outside the self-test. Two MAME instances race each other in docs/linked-play-in-mame.md.
- **MultiSync A046901 bench notes.** What the diagnostic LEDs mean (CR9 interrupts, CR10 clock, CR11 DTACK, CR12 run), the boot order and what each failure looks like, self-test expectations for these sets, connector pinouts, the link cable, NVRAM part numbers, video rates.

### ROM tools, verified in MAME only

- **Pod stream on Serial B** (rdtrack.podlink). Lifts the Panorama's pod-packet sender out of your own Panorama dump and grafts it into the cockpit or compact program, so the game broadcasts car position, orientation and the cars in view on Serial B (J3) at 38400 8N1 in the Panorama's own format, while Serial A stays free for a linked race. Verified end to end against an unmodified Panorama pod program, including during a linked race. Not yet tried on real hardware.

### Track tools

- **Track compiler and browser editor** (rdp-fullscreen). The DSK track format is decoded well enough to compile new tracks from parts: an oval, a figure-8 with an underpass, scenery, paying gates, drones. The editor runs in a browser with a validator that runs the real compiler on every edit, lap recording through MAME, build, drive, and export of the EPROM images that differ from stock. Sets built through it drive in MAME; one has not yet been driven on hardware.
- **East loop mod.** The original project: a loop spliced into the cockpit's speed track. Drives clean in MAME.

### Side pods and rendering

- **Pod artwork and world decoded.** The pod's 70 compressed bitmaps (door cards, horizon sheets, overview maps) and their codec, with a tool that replaces them from PNG; the 3D world as a mesh in the ADSP object ROM, decoded to OBJ.
- **Open pod renderer** (rdp-renderer). Draws the pod view from the link packets: 95 to 97 percent pixel-identical to MAME's pod at matching poses, with the projection, horizon placement and lighting read from the pod's own code rather than fitted. Mac viewer, iOS app, runs live from MAME through a link mirror. This is the plan for side views: no real pod hardware is needed.

### MiSTer core

- **First hardware release, 2026-10-27.** The cockpit core fits the DE10-Nano (93 percent of the logic), meets timing, and boots from a standard MAME zip into the self-test, attract mode, champions and credits screens and the driving demo with the dashboard. In the core: the 68010, the TMS34010 GSP and display pipeline, the ADSP-2100, the DSK board with a DSP32C that is bit-exact against MAME's model, the ASIC65, the slapstic, the MC68681 DUART, the ADC inputs, the sound board, NVRAM, and the cabinet I/O link. Stock and slapstic-free MRAs are provided. Built on Fulviuus' Hard Drivin' core.
- **Whole-core simulation.** A Verilator harness with the real TG68K, lock-step DSP32C and DUART tests, and a comparison of the 68010's write sequence against an instrumented MAME.

### Supporting hardware

- **T48 for Tab5** programmer, public since 2026-10 with One ROM support.
- **USB-C cable end caps**, printed in TPU and published on Makerworld.

## In progress and still to finish

- **ROM stack rev C boards.** The first run had a factory jumper defect (a copper strip shorting VCC to GND, reworked with a knife cut); rev C boards are in hand and pass the meter check but none is built and tested yet. The board files get published once one has run on hardware.
- **Pod stream on real hardware.** Burn a --pods set and watch J3 with a terminal or the ESP32 bridge; MAME says it works, the hardware has not been asked.
- **Cockpit sets on hardware.** A plain slapstic-free cockpit set has never been burned, and a linked race between two real machines has not been run with these sets.
- **MiSTer core, next steps.** A long gameplay session with USB controls; sound, the force-feedback wheel link and the cabinet I/O board are all untested on hardware; the compact build exists as a feasibility port and is not released; link play between two cores (cable first, then ESP-NOW and LAN UDP, written up in docs/io-board-plan.md).
- **Cabinet interface board.** Planned in detail (connectors, pin maps, ESP32-S3 with an external SPI ADC, 5 V buffers, force-feedback and shifter interfaces, two RS-232 ports, link transport). Build order: breadboard link prototype, force path on the bench, shifter on the bench, first cockpit trial without a PCB, compact trial, then KiCad rev A for five boards. Goal: no Atari boards in the cabinet, updates by copying a file.
- **Wireless serial bridge.** One ESP32 with a single MAX3232 covers both Serial A and Serial B (two drivers, two receivers); designed on paper, not built. Also the transport for the pod stream to an iPad running the renderer.
- **Renderer.** One-pixel road-piece seams, the pod's 14 to 19 frame draw lag (matters only for offline diffs), a real iPad on Wi-Fi, then an enhanced mode (depth buffer, wider views, replacement meshes that keep the original mesh as collision truth).
- **Track editor.** Drive an editor-built set on hardware; an import path for real circuits (the hand-fitted Virginia International Raceway attempt is parked in favour of that).
- **HD/RD to VGA sync board.** Jed Margolin's hdvgad2 redrawn as an SMD board for JLCPCB assembly; files done, not ordered, the slide-switch direction to be confirmed on the first board.
- **Slapstic tap board.** A plug-in ROM pass-through with a two-pin header so the slapstic-free mod needs no soldered jumpers; two variants designed, not ordered.

## Future ideas

- **CAN bus on the MiSTer I/O chain.** Add a CAN transceiver to the cabinet interface board (the ESP32-S3 already has a CAN controller) and publish the car's state the way a real engine ECU does: RPM, speed, gear, throttle, brake, clutch, water and oil readings, lap and race flags, in a broadcast format the aftermarket race dashboards understand (the AiM, MoTeC, Racepak, Haltech, AEM, Holley class of displays, most of which accept a configurable CAN stream or a common ECU protocol). A real dash on the cabinet then replaces the on-screen dashboard, which takes the lower third of the picture, and the game's view can fill the whole screen. The game already keeps all of these values in RAM for its own dash; the work is locating them once, streaming them from the core to the board, and documenting a dash profile.
- **Panorama on MiSTer.** The centre board on the core with the side views coming from the open renderer, or from two more cores on the link.
- **Enhanced world.** The renderer's second mode: a wider, prettier world that still hits the same walls, with the game remaining the authority.
- **Editor-built tracks on the MiSTer core.** Once the core loads DSK ROMs from a zip, a new track is a file copy rather than two EPROMs.

## Decisions made along the way

- No four-socket ADSP adapter: the older Driver ADSP board (A044421) has one page bit, so a third object-ROM pair would need a board modification; ADSP II boards are the answer and MiSTer makes it moot.
- No real side pods on custom centre stacks: the renderer is the side-pod plan.
- Distribute patchers, never ROM images; every output is traceable to the user's own dumps and keeps Atari's byte-sum convention so the self-test passes.
