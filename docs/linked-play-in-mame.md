# Two linked compacts in MAME (2026-10-05)

The compact program has the link game built in: operator option GAME TYPE = NOT LINKED /
LINKED GAME 1 / LINKED GAME 2 (bits 5-4 of option word 13, shadowed at [0x905964]+0x0C), DUART
channel A at 38400 8N1, packets framed `BA type data checksum` like the Panorama pod link.

`mame/link2.lua` runs one cabinet of a pair.  It forces the link option in RAM (it does
not go through the operator screen), sets MAME's null-modem bridge to 38400, and plays scripted
inputs.  Environment: `LINKNO=1|2`, `INPUTS="coin:240-285,key:480-525,whl:400:112,..."` (holds are
frame ranges, `whl:frame:delta` is one dial step), `SNAPEVERY`, `FRAMES`.

Two instances on one machine, joined by a local socket (start game 1 first, it listens):

    ./hd racedrivcs -rompath ROMS -video none -sound none -mainpcb:rs232 null_modem \
        -bitb socket.127.0.0.1:5200 -autoboot_script mame/link2.lua -autoboot_delay 0 \
        -nvram_directory NV1 -cfg_directory CFG1 -snapshot_directory SNAP1      # LINKNO=1
    (same again with LINKNO=2 and NV2/CFG2/SNAP2)

Run throttled (no -nothrottle) so both stay near real time, and give each its own nvram and
cfg directory.  For the slapstic-free set add the linear read tap (already in the script).

Result with the Stock Car set: game 1 `coin, coin, whl:400:112, whl:460:100, key` picks TWO
PLAYER / STOCK CAR TRACK and shows LINKED GAME - WAITING FOR OTHER PLAYER; game 2 shows ACCEPT
THE CHALLENGE and a key turn joins.  Both then show PREPARE FOR THE 2 LAP LINKED RACE with three
cars on the grid (two players in separate slots plus one drone), the rules screen, TURN KEY TO
START and LAP 1 with the clock running.  Not tested: driving a lap, the finish and win logic,
car-to-car contact, real hardware.  The track preview picture for the slot still reads
AUTOCROSS TRACK.
