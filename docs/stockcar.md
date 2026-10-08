# Race Drivin' compact + the Panorama's Stock Car track

    python3 -m rdtrack.stockcar RACEDRIV.zip RACEDRIVPAN.zip -o OUT --slapstic free|115|117

Inputs are your own dumps: a MAME `racedriv.zip` that carries the compact ROMs
(a merged set with a `racedrivc/` folder inside, or a split `racedrivc.zip` plus
its parent), and the Panorama set `racedrivpan.zip`.  Output: `OUT/racedrivc/`,
a complete compact set whose Autocross slot is the Panorama's Stock Car track.

What changes on the boards:

| board | EPROMs | note |
|---|---|---|
| main (200R..210Y) | 200R/210R, 200S/210S, 200T/210T, 200X/210X | 200X/210X carry the Stock Car drone recordings at 0x0C5980; 200T/210T the 22 rewritten object-table entries; 200R..210S the selector text, the four slot-1 rule gates and the slapstic/Y2K edits |
| DSK PCB A047724-01 (30E/10E) | two **27C010** (128 KB) | as the Panorama fits it; three worlds of this size do not fit 27C512s |
| ADSP object board | 10H/10K rewritten; **9H/9K** added: `136088-1022.9h` / `136088-1021.9k` | the Panorama's third pair, verbatim; the compact ships with those sockets empty |

`--slapstic free` applies the slapfree core + self-test + Y2K edits (relocated
into the compact program by instruction signature) for a board with the chip
pulled and the four jumpers fitted.  `115` and `117` produce the same images:
the program probes both chip types at boot, so the stock arrangement plus the
Y2K fix serves either.

Every EPROM the tool touches has its byte-sum signature restored (low byte of
the sum = the part-number suffix), so the operator ROM test stays quiet.

Known leftovers: the CHOOSE YOUR TRACK map picture still says AUTOCROSS TRACK
(it is artwork), the help text "an AUTOCROSS track" is left because "a STOCK
CAR track" is longer, and the Stock Car gates and section names are the speed
track's, as in the Panorama prototype.

One deliberate side effect on every track: the roadside weed menu loses two of
its seven plant kinds (FLOWER2 and FLOWER3 become WEED1 and FLOWER) because
their object slots carry two of the stock-car models.

Testing in MAME needs a clone that loads 128 KB DSK halves and six object
EPROMs: experiments/racedrivcs_mame.md.  Run it with rd.lua: MAME's stock
compact NVRAM has the brake uncalibrated (range 0 = brake always on, the car
only creeps), and rd.lua writes the calibration once.  On a real cabinet the
operator's SET CONTROLS brake step does the same thing.
