-- MAME side pod listening on its Serial A; yaw/pitch default patched to straight ahead
local mach = manager.machine
local rgn  = mach.memory.regions[":mainpcb:maincpu"]
local cpu  = mach.devices[":mainpcb:maincpu"]
local sp   = cpu.spaces["program"]
rgn:write_u16(0x4742e, 0); rgn:write_u16(0x4743e, 0)
_G.k = {}
local nrx = 0
_G.k.rx = sp:install_read_tap(0xff0006, 0xff0007, "rx", function () nrx = nrx + 1 end)
local n = 0
local every = tonumber(os.getenv("SNAPEVERY") or "300")
_G.k.fn = emu.add_machine_frame_notifier(function ()
  n = n + 1
  if n % every == 0 then mach.video:snapshot(); print(string.format("[pod] f%d t %.1f rx reads %d", n, mach.time:as_double(), nrx)) end
  if n >= tonumber(os.getenv("FRAMES") or "6000") then mach:exit() end
end)
