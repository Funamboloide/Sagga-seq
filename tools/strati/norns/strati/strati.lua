-- strati
-- the sounds strati made
-- from your samples
--
-- E2 sound   E3 volume
-- K2 play the note it was
-- K3 play an octave up
-- MIDI: notes, program
-- change picks the sound,
-- mod wheel: the noise
-- (on sounds that have it)
--
-- sounds: dust/data/strati/
-- sounds/*.strati

engine.name = "Strati"

local util = require "util"

local DIR = _path.data .. "strati/sounds/"
local names = {}
local roots = {}
local m = nil
local held_keys = {}

local function scan()
  util.make_dir(DIR)
  local files = {}
  for _, f in ipairs(util.scandir(DIR) or {}) do
    if string.sub(f, -7) == ".strati" then table.insert(files, f) end
  end
  table.sort(files)
  names, roots = {}, {}
  for i, f in ipairs(files) do
    if i > 128 then break end
    engine.load(i - 1, DIR .. f)
    names[i] = string.sub(f, 1, -8)
    -- the root note is on the file's third line (to play the sound at the note it was)
    local fh = io.open(DIR .. f, "r")
    local root = 60
    if fh then
      fh:read("*l"); fh:read("*l")
      local l = fh:read("*l") or "60"
      root = tonumber(string.match(l, "^%s*(%S+)")) or 60
      fh:close()
    end
    roots[i] = root
  end
  if #names == 0 then names = {"(no sounds)"}; roots = {60} end
end

local function connect(port)
  if m then m.event = nil end
  m = midi.connect(port)
  m.event = function(data)
    local msg = midi.to_msg(data)
    local ch = params:get("strati_ch")
    if ch ~= 0 and msg.ch ~= ch then return end
    if msg.type == "note_on" and msg.vel > 0 then
      engine.noteOn(msg.note, msg.note, msg.vel / 127)
    elseif msg.type == "note_off" or (msg.type == "note_on" and msg.vel == 0) then
      engine.noteOff(msg.note)
    elseif msg.type == "program_change" then
      if msg.val < #names then params:set("strati_sound", msg.val + 1) end
    elseif msg.type == "cc" and msg.cc == 1 then
      params:set("strati_noise", msg.val / 127)
    elseif msg.type == "cc" and msg.cc == 123 then
      engine.allOff()
    end
  end
end

function init()
  scan()
  params:add_separator("strati")
  params:add_option("strati_sound", "sound", names, 1)
  params:set_action("strati_sound", function(i) engine.select(i - 1); redraw() end)
  params:add_number("strati_port", "midi port", 1, 16, 1)
  params:set_action("strati_port", function(p) connect(p) end)
  params:add_number("strati_ch", "midi channel", 0, 16, 0, function(p)
    local v = p:get(); if v == 0 then return "all" end; return v end)
  params:add_control("strati_amp", "volume", controlspec.new(0, 1, "lin", 0, 0.5))
  params:set_action("strati_amp", function(v) engine.amp(v); redraw() end)
  params:add_control("strati_follow", "noise follows note", controlspec.new(0, 1, "lin", 0, 0))
  params:set_action("strati_follow", function(v) engine.follow(v) end)
  params:add_control("strati_pan", "pan", controlspec.new(-1, 1, "lin", 0, 0))
  params:set_action("strati_pan", function(v) engine.pan(v) end)
  params:add_control("strati_noise", "noise (mod wheel)", controlspec.new(0, 1, "lin", 0, 1))
  params:set_action("strati_noise", function(v) engine.noise(v); redraw() end)
  params:add_number("strati_poly", "voices", 1, 16, 6)
  params:set_action("strati_poly", function(v) engine.poly(v) end)
  params:bang()
  redraw()
end

function enc(n, d)
  if n == 2 then params:delta("strati_sound", d)
  elseif n == 3 then params:delta("strati_amp", d) end
end

function key(n, z)
  if n < 2 then return end
  local i = params:get("strati_sound")
  local note = math.floor((roots[i] or 60) + 0.5) + (n == 3 and 12 or 0)
  local id = 1000 + n
  if z == 1 then
    engine.noteOn(id, note, 0.8)
    held_keys[n] = true
  else
    engine.noteOff(id)
    held_keys[n] = nil
  end
  redraw()
end

function redraw()
  screen.clear()
  screen.level(4)
  screen.move(0, 10)
  screen.text("strati")
  screen.move(128, 10)
  screen.text_right(params:get("strati_sound") .. "/" .. #names)
  screen.level(15)
  screen.move(0, 34)
  screen.font_size(12)
  screen.text(names[params:get("strati_sound")] or "")
  screen.font_size(8)
  screen.level(4)
  screen.move(0, 60)
  screen.text("vol " .. string.format("%.2f", params:get("strati_amp")) ..
    "  noise " .. string.format("%d%%", math.floor(params:get("strati_noise") * 100 + 0.5)))
  screen.move(128, 60)
  local ch = params:get("strati_ch")
  screen.text_right("midi " .. (ch == 0 and "all" or ch))
  screen.update()
end

function cleanup()
  engine.allOff()
end
