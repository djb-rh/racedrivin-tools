-- one of two linked compacts.  LINKNO=1|2, INPUTS="coin:240-285,key:480-525,whl:300:-112,..." , SNAPEVERY, FRAMES
local mach = manager.machine
local rgn  = mach.memory.regions[":mainpcb:maincpu"]
local cpu  = mach.devices[":mainpcb:maincpu"]
local sp   = cpu.spaces["program"]
local tag  = "[L" .. (os.getenv("LINKNO") or "?") .. "]"
_G.k = {}
-- serial bridge to 38400 8N1 (set once, then soft reset so the null modem picks it up)
local changed = false
for ptag, port in pairs(mach.ioport.ports) do
  if string.find(ptag, "null_modem") then
    for name, f in pairs(port.fields) do
      if (name == "TX Baud" or name == "RX Baud") and f.user_value ~= 0x0b then f.user_value = 0x0b; changed = true end
    end
  end
end
if changed then print(tag .. " serial bridge set to 38400, soft reset"); mach:soft_reset(); return end
_G.k.lin = sp:install_read_tap(0xe0000, 0xfffff, "lin", function (off) return rgn:read_u8(off) * 256 + rgn:read_u8(off + 1) end)
local linkno = tonumber(os.getenv("LINKNO") or "1")
local ntx, nrx = 0, 0
_G.k.tx = sp:install_write_tap(0xff0006, 0xff0007, "tx", function (off, data, mask) ntx = ntx + 1 end)
_G.k.rx = sp:install_read_tap(0xff0006, 0xff0007, "rx", function (off, data, mask) nrx = nrx + 1 end)
local function findf(name) for _, p in pairs(mach.ioport.ports) do if p.fields[name] then return p.fields[name] end end end
local coin, key, abort, whl, g1 = findf("Coin 1"), findf("Key"), findf("Abort"), findf("Steering Wheel"), findf("1st Gear")
local centre = whl and whl.defvalue or 0x800
local sel = centre
local holds, steps = {}, {}
for name, a, b in string.gmatch(os.getenv("INPUTS") or "", "(%a+):(%d+)%-(%d+)") do holds[#holds + 1] = {name, tonumber(a), tonumber(b)} end
for f, d in string.gmatch(os.getenv("INPUTS") or "", "whl:(%d+):(-?%d+)") do steps[tonumber(f)] = tonumber(d) end
local fields = {coin = coin, key = key, abort = abort, gear = g1}
local n = 0
local every = tonumber(os.getenv("SNAPEVERY") or "120")
local stop = tonumber(os.getenv("FRAMES") or "3600")
_G.k.fn = emu.add_machine_frame_notifier(function ()
  n = n + 1
  local a0 = sp:read_u32(0x905964) & 0xffffff
  if a0 >= 0xff8000 then
    local w = sp:read_u16(a0 + 0x0c)
    local want = (w & ~0x30) | (linkno << 4)
    if w ~= want then sp:write_u16(a0 + 0x0c, want); print(string.format("%s f%d options %04X -> %04X", tag, n, w, want)) end
  end
  for _, h in ipairs(holds) do
    local f = fields[h[1]]
    if f then if n == h[2] then f:set_value(1) elseif n == h[3] then f:set_value(0) end end
  end
  if steps[n] then sel = sel + steps[n] end
  if whl then whl:set_value(sel) end
  if n % every == 0 then mach.video:snapshot(); print(string.format("%s f%d pc %06X tx %d rx %d", tag, n, cpu.state["PC"].value, ntx, nrx)) end
  if n >= stop then mach:exit() end
end)
