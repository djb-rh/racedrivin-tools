# The Panorama pod stream on Serial B (2026-10-05)

`python3 -m rdtrack.stockcar RACEDRIV.zip RACEDRIVPAN.zip -o OUT --slapstic free --pods`
adds `rdtrack/podlink.py`'s patch: the compact sends the Panorama's side-pod packets on
Serial B (J3, 38400 8N1) while Serial A stays free for a linked race.

## How it works

- The compact program (rev 5) already has an unused interrupt-driven transmitter for
  channel B: IRQ handler 0x4D8CC, `putcB` 0x4DAEA (ring 0x90149C, head/tail
  0x901178/0x90117A, checksum accumulator 0x90117E), queue depth 0x4DC48, block write
  0x2467C.  Both DUART channels are set to 38400 8N1 at boot.
- The Panorama centre program's pod module is one contiguous block, 0x276A0-0x27D6E:
  `send(type)` 0x276A0, `pick()` 0x27770 (returns 1 = roster needed, 2 = pose), roster
  0x277F8, pose 0x27954, the two car scans 0x279E2 / 0x27AB6, the side-sector test 0x27BA0,
  the camera block 0x27C32 and the 10-byte car packer 0x27C58.  Its frame function calls
  `send(pick())` right after an empty stub; the compact's twin of that function (0x20158)
  still calls the stub (0x27CC8) and nothing else, which is where the hook goes.
- The patch copies that block to 0x4E000 (zeros in the stock program), rewrites 77 absolute
  addresses, and adds 42 bytes of glue.  Game variables and helper routines are found in
  the compact by matching the code round each Panorama use with every address wildcarded
  (`podlink.locate`): camera 0xFF8044/0xFF8054 -> 0x900044/0x900054, car table
  0xFFA468/0xFFA438 -> 0x901F70/0x901F40, track 0xFF9B6E -> 0x901756, and so on.  The three
  maths helpers were checked to be the same code in both programs.
- The module's own working storage moves to 0x90F000 (DSK RAM the game never touched in
  attract, one-player and linked races).
- Object-catalogue indices differ between the two programs (the Stock Car build parks the
  stock-car models in dead slots), so roster ids go through a 256-byte name-matched table.
- The Panorama's second car table has no equivalent in the compact.  Its one entry is fed
  from 0x90590C, the linked opponent's car object, so a pod sees the other player too.

## Testing in MAME

MAME exposed only channel A.  The local tree adds a second slot in `driver_nomsp`:

    m_duartn68681->b_tx_cb().set("rs232b", FUNC(rs232_port_device::write_txd));
    rs232_port_device &rs232b(RS232_PORT(config, "rs232b", default_rs232_devices, nullptr));
    rs232b.rxd_handler().set("duartn68681", FUNC(mc68681_device::rx_b_w));

Pod first (it listens), then the compact, both throttled:

    ./hd racedrivpans -rompath ROMS_WITH_THE_PANORAMA_SET -video none -sound none \
        -mainpcb:rs232 null_modem -bitb socket.127.0.0.1:6200 \
        -autoboot_script mame/e2e_pod.lua -autoboot_delay 0 ...
    ./hd racedrivcs -rompath ROMS_WITH_PODS -video none -sound none \
        -mainpcb:rs232b null_modem -bitb socket.127.0.0.1:6200 \
        -autoboot_script mame/e2e_compact.lua -autoboot_delay 0 ...

`e2e_pod.lua` points the pod straight ahead (yaw/pitch table entry 7 = 0) so its picture can
be compared with the compact's own; `e2e_compact.lua` sets the bridge to 38400 and supplies
the linear slapstic decode.  Give each instance its own nvram, cfg and snapshot directory.

## Results

- 100% of the Serial B bytes frame as Panorama packets (`tools/rdplink.py`); poses
  arrive about 12 times a second; the boot roster `02 00 01 01` is byte-identical to the one
  in a real Panorama capture.
- The unmodified pod program rendered the same scenes as the compact through an attract lap.
- Linked two-player Stock Car race with game 1 patched: Serial A carried 21.8 KB of link
  traffic and Serial B 39.7 KB of pod packets over the same minute; the roster became
  `01 00 02 00 47` and each pose listed the drone and the opponent at the opponent's own
  position.
- Not sent: types 04/05/06 (key, heartbeat, track dial).  Not tested: real hardware.

## Cockpit as well (later the same day)

`rdtrack/podlink.py` no longer assumes the compact.  Everything in the target program is
found from the Panorama's code: game variables by `locate` (code round each use, addresses
wildcarded), the Serial B routines by `twin` (the Panorama's own channel B routines at
0x4EFEE / 0x4F14C / 0x24158 matched in the target), the checksum accumulator read out of the
target's `putcB`, the linked-car pointer from the Panorama's 0xFFECB2, the destination from
the first free block at a 4 KB boundary above 0x20000.  The Stock Car build's output did not
change by a byte.

    python3 -m rdtrack.podlink RACEDRIV.zip RACEDRIVPAN.zip -o OUT --set cockpit|compact

writes the four EPROMs that change with their byte sums restored (two spare bytes after the
catalogue table, and the operand of the frame function's `pea 3`, which nothing reads once
the stub call is replaced).

Cockpit rev 5 in MAME: car table 0x901F58, track 0x90173E, linked car 0x9058F4, `putcB`
0x4D6BC, hook 0x20186, code at 0x4E000.  42 KB on Serial B in 70 s, 100% framed, 18.9 poses a
second, boot roster `02 00 01 01`; the pod program rendered the attract lap from it.  0x90F000
is untouched by the stock cockpit program too (free 0x90CC9C-0x90FFFF) and its boot code
clears DSK RAM (0x4AACC).  Not run: a linked race on the cockpit.

Neither program reads the DUART input port outside the self-test (cockpit 0x048FE-0x04B36,
compact 0x0450C-0x04744), so the link needs only TX, RX and ground.
