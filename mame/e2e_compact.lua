-- patched compact feeding a pod from Serial B
local mach = manager.machine
local changed = false
for ptag, port in pairs(mach.ioport.ports) do
  if string.find(ptag, "null_modem") then
    for name, f in pairs(port.fields) do
      if (name == "TX Baud" or name == "RX Baud") and f.user_value ~= 0x0b then f.user_value = 0x0b; changed = true end
    end
  end
end
if changed then print("[cmp] serial bridge set to 38400, soft reset"); mach:soft_reset(); return end
local rgn  = mach.memory.regions[":mainpcb:maincpu"]
local cpu  = mach.devices[":mainpcb:maincpu"]
local sp   = cpu.spaces["program"]
_G.k = {}
_G.k.lin = sp:install_read_tap(0xe0000, 0xfffff, "lin", function (off) return rgn:read_u8(off) * 256 + rgn:read_u8(off + 1) end)
local nb = 0
_G.k.tb = sp:install_write_tap(0xff0016, 0xff0017, "tb", function () nb = nb + 1 end)
local function s32(a) local v = sp:read_u32(a); if v >= 0x80000000 then v = v - 0x100000000 end; return v end
local n = 0
local every = tonumber(os.getenv("SNAPEVERY") or "300")
_G.k.fn = emu.add_machine_frame_notifier(function ()
  n = n + 1
  if n % every == 0 then mach.video:snapshot(); print(string.format("[cmp] f%d t %.1f B bytes %d cam %d %d %d track %d", n, mach.time:as_double(), nb, s32(0x900044), s32(0x900048), s32(0x90004c), sp:read_u16(0x901756))) end
  if n >= tonumber(os.getenv("FRAMES") or "6000") then mach:exit() end
end)
