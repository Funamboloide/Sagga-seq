-- caramello
-- autotune caramelloso:
-- da pulitissimo a hyperpop
--
-- E1 pagina  E2 E3 valori
-- K1 tenuto: valori sotto
-- K2 freeze (tocco/tenuto)
-- K3 bypass
-- K1+K2 nightcore
-- K1+K3 note MIDI on/off
--
-- v0.1 dal patch Ksoloti Gills

engine.name = "GillsCaramello"

local NOTE = { "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B" }
local SCALES = { "CHROMATIC", "MAJOR", "MINOR", "MAJ-PENTA", "MIN-PENTA", "BLUES", "HARM-MINOR", "DORIAN", "MIXOLYDIAN" }
-- bit p = grado p (in semitoni dalla tonica) presente nella scala
local SHORT = { "CHROM", "MAJOR", "MINOR", "MAJ-PENT", "MIN-PENT", "BLUES", "HARM-MIN", "DORIAN", "MIXO" }
local MASKS = { 0xFFF, 0xAB5, 0x5AD, 0x295, 0x4A9, 0x4E9, 0x9AD, 0x6AD, 0x6B5 }
local HARMS = { "OTTAVA SU", "OTTAVA GIU", "QUINTA SU", "QUINTA GIU", "QUARTA SU", "TERZA SU", "TERZA GIU",
  "SESTA SU", "POWER", "TRIADE", "TRIADE+8a", "GECS STACK", "OTTAVE", "SUS" }
-- program change: PC = 12 x scala + tonalita', blocchi di 12 nell'ordine del Gills
local PC_SCALE = { 2, 3, 1, 4, 5, 6, 7, 8, 9 }

local RECIPES = {
  { name = "pulito naturale", v = { retune = 0.55, amount = 80, pitch = 0, formant = 0, sugar = 0, drive = 0, crush = 0,
    space = 0.15, harmony = 0, mix = 1, nightcore = 0, freeze = 0 } },
  { name = "hard tune", v = { retune = 0, amount = 100, pitch = 0, formant = 0, sugar = 0, drive = 0, crush = 0,
    space = 0.1, harmony = 0, mix = 1, nightcore = 0, freeze = 0 } },
  { name = "caramello gecs", v = { retune = 0, amount = 100, pitch = 0, formant = 4, sugar = 0.8, drive = 0.4, crush = 0.18,
    space = 0.3, harmony = 0.5, harm_type = 12, mix = 1, nightcore = 0, freeze = 0 } },
  { name = "nightcore", v = { retune = 0, amount = 100, pitch = 12, formant = 0, sugar = 0.5, drive = 0, crush = 0,
    space = 0.2, harmony = 0, mix = 1, nightcore = 1, freeze = 0 } },
  { name = "robot", v = { retune = 0, amount = 100, pitch = 0, formant = 0, sugar = 0, drive = 0.1, crush = 0,
    space = 0.15, harmony = 0, mix = 1, nightcore = 0, freeze = 1 } },
}

-- pagine: E2/E3, e con K1 tenuto la seconda coppia
local PAGES = {
  { name = "TUNE", a = { "retune", "amount" }, b = { "key", "scale" } },
  { name = "PITCH", a = { "pitch", "formant" }, b = { "fine", "vibrato" } },
  { name = "SUGAR", a = { "sugar", "drive" }, b = { "width", "tone" } },
  { name = "HARMONY", a = { "harmony", "harm_type" }, b = { "crush", "gate" } },
  { name = "SPACE", a = { "space", "mix" }, b = { "size", "output" } },
}
local LABEL = { retune = "RETUNE", amount = "AMOUNT", key = "KEY", scale = "SCALE", pitch = "PITCH", formant = "FORMANT",
  fine = "FINE", vibrato = "VIBRATO", sugar = "SUGAR", drive = "DRIVE", width = "WIDTH", tone = "TONE",
  harmony = "HARMONY", harm_type = "TIPO", crush = "CRUSH", gate = "GATE", space = "SPACE", mix = "MIX",
  size = "SIZE", output = "OUTPUT" }

local page, alt = 1, false
local tun = { A = { note = 0, tgt = 0, out = 0, vcd = 0 }, B = { note = 0, tgt = 0, out = 0, vcd = 0 } }
local peak, clip_until = 0, 0
local held = {}                -- note MIDI tenute, in ordine di pressione
local mdev
local k2_down, k2_was_off = nil, false
local polls = {}
local redraw_metro
local saved = {}
local msg, msg_until = "", 0

local function now() return util.time() end

local function flash(s)
  msg, msg_until = s, now() + 1.5
end

-- ---------------------------------------------------------------- scala e armonie
local function in_scale(m, mask)
  return ((mask >> (m % 12)) & 1) == 1
end

-- sposta di 'steps' gradi della scala (in cromatica: 'chrom' semitoni)
local function deg(n, steps, chrom, sc)
  if sc == 1 then return n + chrom end
  local mask = MASKS[sc]
  local m, dir, k = n, steps > 0 and 1 or -1, math.abs(steps)
  while k > 0 do
    m = m + dir
    if in_scale(m, mask) then k = k - 1 end
  end
  return m
end

-- intervalli delle armonie (semitoni sopra/sotto il target) per la nota t, come nel Gills
local function harm(t, ht, sc)
  if ht == 1 then return { 12 }
  elseif ht == 2 then return { -12 }
  elseif ht == 3 then return { 7 }
  elseif ht == 4 then return { -7 }
  elseif ht == 5 then return { 5 }
  elseif ht == 6 then return { deg(t, 2, 4, sc) - t }
  elseif ht == 7 then return { deg(t, -2, -4, sc) - t }
  elseif ht == 8 then return { deg(t, 5, 9, sc) - t }
  elseif ht == 9 then return { 7, 12 }
  elseif ht == 10 then return { deg(t, 2, 4, sc) - t, deg(t, 4, 7, sc) - t }
  elseif ht == 11 then return { deg(t, 2, 4, sc) - t, deg(t, 4, 7, sc) - t, 12 }
  elseif ht == 12 then return { -12, 7, 12 }
  elseif ht == 13 then return { -12, 12 }
  else return { 5, 7 } end
end

local function send_scale()
  local sc = params:get("scale")
  local mask = {}
  for p = 0, 11 do mask[p + 1] = (MASKS[sc] >> p) & 1 end
  engine.mask(table.unpack(mask))
  -- una tabella per voce di armonia, indicizzata dal grado (target - tonica) % 12
  local ht = params:get("harm_type")
  local iv = { {}, {}, {} }
  local nh = 1
  for p = 0, 11 do
    local h = harm(p, ht, sc)
    nh = #h
    for j = 1, 3 do iv[j][p + 1] = h[j] or 0 end
  end
  engine.iv0(table.unpack(iv[1]))
  engine.iv1(table.unpack(iv[2]))
  engine.iv2(table.unpack(iv[3]))
  engine.set("nh", nh)
end

-- ---------------------------------------------------------------- MIDI
local function send_notes()
  if params:get("midi_notes") == 0 or #held == 0 then
    engine.set("midiNote", -1)
    for i = 1, 3 do engine.set("hn" .. i, -1) end
  else
    engine.set("midiNote", held[#held])
    for i = 1, 3 do engine.set("hn" .. i, held[#held - i] or -1) end
  end
end

local function note_on(n)
  for i = #held, 1, -1 do if held[i] == n then table.remove(held, i) end end
  table.insert(held, n)
  while #held > 8 do table.remove(held, 1) end
  send_notes()
end

local function note_off(n)
  for i = #held, 1, -1 do if held[i] == n then table.remove(held, i) end end
  send_notes()
end

local function midi_event(data)
  local m = midi.to_msg(data)
  if m.ch == nil then return end                      -- messaggi di sistema: niente da fare
  local ch = params:get("midi_ch") - 1                -- 0 = omni
  if ch > 0 and m.ch ~= ch then return end
  if m.type == "note_on" then note_on(m.note)
  elseif m.type == "note_off" then note_off(m.note)
  elseif m.type == "cc" then
    if m.cc == 64 then params:set("freeze", m.val >= 64 and 1 or 0)
    elseif m.cc == 80 then params:set("bypass", m.val >= 64 and 1 or 0)
    elseif m.cc == 81 then params:set("harm_off", m.val >= 64 and 1 or 0)
    elseif m.cc == 123 or m.cc == 120 then held = {}; send_notes() end   -- all notes off / all sound off, come sul Gills
  elseif m.type == "program_change" then
    local pc = m.val
    params:set("key", pc % 12 + 1)
    params:set("scale", PC_SCALE[(pc // 12) % 9 + 1])
    flash(NOTE[params:get("key")] .. " " .. SCALES[params:get("scale")])
  end
end

local function connect_midi()
  if mdev then mdev.event = nil end
  mdev = midi.connect(params:get("midi_port"))
  mdev.event = midi_event
end

-- ---------------------------------------------------------------- polls
local function start_polls()
  for _, p in pairs(polls) do p:stop() end
  polls = {}
  local function add(name, f, t)
    local p = poll.set(name)
    if not p then return end                         -- engine non caricato
    p.callback = f
    p.time = t
    p:start()
    polls[name] = p
  end
  for _, s in ipairs({ "A", "B" }) do
    if s == "A" or params:get("input") == 3 then
      add("note" .. s, function(v) tun[s].note = v end, 1 / 20)
      add("tgt" .. s, function(v) tun[s].tgt = v end, 1 / 20)
      add("out" .. s, function(v) tun[s].out = v end, 1 / 20)
      add("vcd" .. s, function(v) tun[s].vcd = v end, 1 / 20)
    end
  end
  add("peak", function(v)
    peak = v
    if v > 0.98 then clip_until = now() + 0.5 end
  end, 1 / 15)
end

-- ---------------------------------------------------------------- params
local function retune_ms(r)
  if r <= 0.01 then return 0 end
  return (1 + 1.8 * 2 ^ (r * 9.5)) * 6.9 / 3000 * 1000
end

local function pct(p) return string.format("%d%%", math.floor(p:get() * 100 + 0.5)) end

local function add_params()
  local cs = controlspec
  params:add_separator("caramello", "CARAMELLO")

  params:add_group("caramello_io", "INGRESSO / USCITA", 6)
  params:add_option("input", "ingresso", { "mono L", "L+R", "stereo (2 voci)" }, 1)
  params:set_action("input", function(v)
    engine.mode(v)
    start_polls()
  end)
  params:add_option("out_mode", "uscita", { "stereo", "mono" }, 1)
  params:set_action("out_mode", function(v) engine.set("omono", v - 1) end)
  params:add_option("latency", "latenza", { "live", "studio" }, 1)
  params:set_action("latency", function(v) engine.set("live", v == 1 and 1 or 0) end)
  params:add_control("gate", "gate", cs.new(-90, -20, "lin", 1, -54, "dB"),
    function(p) return p:get() <= -89.5 and "off" or string.format("%d dB", p:get()) end)
  params:set_action("gate", function(v) engine.set("gate", v <= -89.5 and 0 or util.dbamp(v)) end)
  params:add_control("output", "output", cs.new(0, 1, "lin", 0, 0.5, ""),
    function(p) return string.format("%+.1f dB", 20 * math.log(math.max(p:get() * 2, 0.0001), 10)) end)
  params:set_action("output", function(v) engine.set("olev", v) end)
  params:add_binary("bypass", "bypass", "toggle", 0)
  params:set_action("bypass", function(v) engine.set("bypass", v) end)

  params:add_group("caramello_tune", "INTONAZIONE", 6)
  params:add_option("key", "tonalita'", NOTE, 1)
  params:set_action("key", function(v) engine.set("key", v - 1) end)
  params:add_option("scale", "scala", SCALES, 2)
  params:set_action("scale", function() send_scale() end)
  params:add_control("retune", "retune", cs.new(0, 1, "lin", 0, 0, ""),
    function(p)
      local ms = retune_ms(p:get())
      if ms == 0 then return "0 ms robot" end
      if ms >= 1000 then return string.format("%.1f s", ms / 1000) end
      return string.format("%d ms", math.floor(ms + 0.5))
    end)
  params:set_action("retune", function(v) engine.set("retune", v) end)
  params:add_control("amount", "amount", cs.new(0, 100, "lin", 1, 100, "%"))
  params:set_action("amount", function(v) engine.set("amount", v / 100) end)
  params:add_binary("freeze", "freeze", "toggle", 0)
  params:set_action("freeze", function(v) engine.set("freeze", v) end)
  params:add_control("vibrato", "vibrato", cs.new(0, 1, "lin", 0, 0, ""), pct)
  params:set_action("vibrato", function(v) engine.set("vib", v) end)

  params:add_group("caramello_pitch", "PITCH E FORMANTI", 4)
  params:add_number("pitch", "pitch", -24, 24, 0, function(p) return string.format("%+d st", p:get()) end)
  params:set_action("pitch", function(v) engine.set("pitch", v) end)
  params:add_number("fine", "fine", -50, 50, 0, function(p) return string.format("%+d c", p:get()) end)
  params:set_action("fine", function(v) engine.set("fine", v / 100) end)
  params:add_number("formant", "formant", -12, 12, 0, function(p) return string.format("%+d", p:get()) end)
  params:set_action("formant", function(v) engine.set("formant", v) end)
  params:add_binary("nightcore", "nightcore", "toggle", 0)
  params:set_action("nightcore", function(v) engine.set("ncore", v) end)

  params:add_group("caramello_candy", "ZUCCHERO", 5)
  params:add_control("sugar", "sugar", cs.new(0, 1, "lin", 0, 0, ""), pct)
  params:set_action("sugar", function(v) engine.set("sugar", v) end)
  params:add_control("width", "width", cs.new(0, 1, "lin", 0, 0.8, ""), pct)
  params:set_action("width", function(v) engine.set("width", v) end)
  params:add_control("drive", "drive", cs.new(0, 1, "lin", 0, 0, ""), pct)
  params:set_action("drive", function(v) engine.set("drive", v) end)
  params:add_control("tone", "tone", cs.new(0, 1, "lin", 0, 0.5, ""),
    function(p) return string.format("%+d", math.floor((p:get() - 0.5) * 20 + 0.5)) end)
  params:set_action("tone", function(v) engine.set("tone", v) end)
  params:add_control("crush", "crush", cs.new(0, 1, "lin", 0, 0, ""), pct)
  params:set_action("crush", function(v) engine.set("crush", v) end)

  params:add_group("caramello_harm", "ARMONIE", 3)
  params:add_control("harmony", "livello", cs.new(0, 1, "lin", 0, 0, ""), pct)
  params:set_action("harmony", function(v) engine.set("harm", v) end)
  params:add_option("harm_type", "tipo", HARMS, 3)
  params:set_action("harm_type", function() send_scale() end)
  params:add_binary("harm_off", "armonie off", "toggle", 0)
  params:set_action("harm_off", function(v) engine.set("hoff", v) end)

  params:add_group("caramello_space", "SPAZIO E MIX", 3)
  params:add_control("space", "space", cs.new(0, 1, "lin", 0, 0, ""), pct)
  params:set_action("space", function(v) engine.set("space", v) end)
  params:add_control("size", "size", cs.new(0, 1, "lin", 0, 0.4, ""), pct)
  params:set_action("size", function(v) engine.set("size", v) end)
  params:add_control("mix", "mix", cs.new(0, 1, "lin", 0, 1, ""), pct)
  params:set_action("mix", function(v) engine.set("mix", v) end)

  params:add_group("caramello_midi", "MIDI", 3)
  local ports = {}
  for i = 1, 16 do ports[i] = i .. ": " .. ((midi.vports[i] and midi.vports[i].name) or "none") end
  params:add_option("midi_port", "porta", ports, 1)
  params:set_action("midi_port", function() connect_midi() end)
  local chs = { "omni" }
  for i = 1, 16 do chs[i + 1] = tostring(i) end
  params:add_option("midi_ch", "canale", chs, 1)
  params:add_binary("midi_notes", "note MIDI", "toggle", 1)
  params:set_action("midi_notes", function() send_notes() end)

  params:add_group("caramello_recipes", "RICETTE", 2)
  local names = {}
  for i, r in ipairs(RECIPES) do names[i] = r.name end
  params:add_option("recipe", "ricetta", names, 2)
  params:add_trigger("recipe_load", "carica la ricetta")
  params:set_action("recipe_load", function()
    local r = RECIPES[params:get("recipe")]
    for id, v in pairs(r.v) do params:set(id, v) end
    flash(r.name)
  end)
end

-- ---------------------------------------------------------------- init / cleanup
function init()
  saved.monitor = params:get("monitor_level")
  -- il dry passa dentro l'engine: il monitor diretto di norns raddoppierebbe la voce
  audio.level_monitor(0)
  audio.rev_off()
  audio.comp_off()
  audio.pitch_off()

  add_params()
  params:default()
  send_scale()
  send_notes()
  connect_midi()
  start_polls()

  redraw_metro = metro.init(function() redraw() end, 1 / 15, -1)
  redraw_metro:start()
end

function cleanup()
  if redraw_metro then redraw_metro:stop() end
  for _, p in pairs(polls) do p:stop() end
  if mdev then mdev.event = nil end
  -- rimette il mixer di norns come lo trova il resto del sistema
  audio.level_monitor(util.dbamp(params:get("monitor_level")))
  if params:get("reverb") == 2 then audio.rev_on() end
  if params:get("compressor") == 2 then audio.comp_on() end
  audio.pitch_on()
end

-- ---------------------------------------------------------------- controlli
function enc(n, d)
  if n == 1 then
    page = util.clamp(page + d, 1, #PAGES)
    return
  end
  local ids = alt and PAGES[page].b or PAGES[page].a
  params:delta(ids[n - 1], d)
end

function key(n, z)
  if n == 1 then
    alt = z == 1
    return
  end
  if n == 2 then
    if alt then
      if z == 1 then
        params:set("nightcore", 1 - params:get("nightcore"))
        flash(params:get("nightcore") == 1 and "NIGHTCORE" or "nightcore off")
      end
      return
    end
    -- tocco = on/off, tenuto = finche' premi
    if z == 1 then
      k2_down = now()
      k2_was_off = params:get("freeze") == 0
      params:set("freeze", 1)
    elseif k2_down then
      local long = now() - k2_down > 0.35
      if (k2_was_off and long) or not k2_was_off then params:set("freeze", 0) end
      k2_down = nil
    end
  elseif n == 3 and z == 1 then
    if alt then
      params:set("midi_notes", 1 - params:get("midi_notes"))
      flash(params:get("midi_notes") == 1 and "note MIDI on" or "note MIDI off")
    else
      params:set("bypass", 1 - params:get("bypass"))
    end
  end
end

-- ---------------------------------------------------------------- schermo
local function note_name(n)
  local r = math.floor(n + 0.5)
  return NOTE[r % 12 + 1] .. tostring(r // 12 - 1)
end

local function cents(a, b)
  local c = math.floor((a - b) * 100 + 0.5)
  return string.format("%+d", util.clamp(c, -99, 99))
end

local function tuner(x, y, w, s)
  screen.level(3)
  screen.move(x, y)
  screen.line(x + w, y)
  screen.stroke()
  screen.level(8)
  screen.move(x + w / 2, y - 3)
  screen.line(x + w / 2, y + 3)
  screen.stroke()
  if s.vcd > 0.5 and s.note > 0 then
    local dev = util.clamp(s.note - s.tgt, -0.5, 0.5)
    local px = math.floor(x + w / 2 + dev * w + 0.5)
    local good = math.abs(s.note - s.tgt) < 0.15
    screen.level(good and 15 or 10)
    screen.rect(px - 1, y - 2, 3, 5)
    screen.fill()
  end
end

local function sung(s)
  if s.vcd > 0.5 and s.note > 0 then
    return note_name(s.note) .. " " .. cents(s.note, s.tgt), note_name(s.out)
  end
  return "--", "--"
end

function redraw()
  screen.clear()
  screen.aa(0)
  screen.font_face(1)
  screen.font_size(8)
  -- riga 1: tonalita', scala e flag
  screen.level(15)
  screen.move(0, 7)
  screen.text(NOTE[params:get("key")] .. " " .. SHORT[params:get("scale")])
  local flags = {}
  if params:get("bypass") == 1 then flags[#flags + 1] = "BYP" end
  if params:get("freeze") == 1 then flags[#flags + 1] = "FRZ" end
  if params:get("nightcore") == 1 then flags[#flags + 1] = "NC" end
  if params:get("midi_notes") == 1 and #held > 0 then flags[#flags + 1] = "MIDI" end
  if params:get("harm_off") == 1 then flags[#flags + 1] = "H0" end
  if now() < clip_until then flags[#flags + 1] = "CLIP" end
  screen.move(127, 7)
  screen.text_right(table.concat(flags, " "))

  if params:get("input") == 3 then
    -- due cantanti: nota e cent, sotto la nota in uscita
    local a1, a2 = sung(tun.A)
    local b1, b2 = sung(tun.B)
    screen.level(15)
    screen.move(0, 17)
    screen.text("A " .. a1)
    screen.move(66, 17)
    screen.text("B " .. b1)
    screen.level(6)
    screen.move(0, 26)
    screen.text("> " .. a2)
    screen.move(66, 26)
    screen.text("> " .. b2)
    tuner(2, 33, 58, tun.A)
    tuner(68, 33, 58, tun.B)
  else
    -- nota cantata e cent dal target | nota in uscita
    local s1, s2 = sung(tun.A)
    screen.font_size(16)
    screen.level(15)
    screen.move(0, 24)
    screen.text(s1)
    screen.font_size(8)
    screen.level(8)
    screen.move(127, 24)
    screen.text_right("> " .. s2)
    tuner(4, 33, 120, tun.A)
  end

  -- pagina (o messaggio), poi i due valori: nome a sinistra, valore a destra
  local pg = PAGES[page]
  local ids = alt and pg.b or pg.a
  screen.move(0, 44)
  if now() < msg_until then
    screen.level(15)
    screen.text(msg)
  else
    screen.level(4)
    screen.text(page .. "/" .. #PAGES .. " " .. pg.name)
    screen.move(127, 44)
    screen.text_right(alt and "K1" or "")
  end
  for i = 1, 2 do
    local y = 44 + 10 * i - 1
    screen.level(alt and 6 or 4)
    screen.move(0, y)
    screen.text("E" .. (i + 1) .. " " .. LABEL[ids[i]])
    screen.level(15)
    screen.move(127, y)
    screen.text_right(params:string(ids[i]))
  end
  screen.update()
end
