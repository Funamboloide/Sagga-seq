-- chroma
-- 4 moduli x 5 effetti
-- (stile Chroma Console)
--
-- E1 pagina  E2 E3 valori
-- K1 tenuto: valori sotto
-- pagine modulo:
--   K2 effetto dopo (K1+K2 prima)
--   K3 bypass del modulo
-- pagina PERF:
--   K2 CAPTURE  K3 BYPASS
--   K1+K2 GESTURE
-- K1+K3 TAP (tenuto: tempo off)
--
-- v0.2 dal patch Ksoloti Gills

engine.name = "GillsChroma"

local MODS = { "CHARACTER", "MOVEMENT", "DIFFUSION", "TEXTURE" }
local FX = {
  { "DRIVE", "SWEETEN", "FUZZ", "HOWL", "SWELL" },
  { "DOUBLER", "VIBRATO", "PHASER", "TREMOLO", "PITCH" },
  { "CASCADE", "REELS", "SPACE", "COLLAGE", "REVERSE" },
  { "FILTER", "SQUASH", "CASSETTE", "BROKEN", "INTERFERENCE" },
}
local SHORT = {
  { "DRIV", "SWTN", "FUZZ", "HOWL", "SWEL" },
  { "DUBL", "VIBR", "PHAS", "TREM", "PTCH" },
  { "CASC", "REEL", "SPAC", "COLG", "REVR" },
  { "FILT", "SQSH", "CASS", "BRKN", "INTF" },
}
local MLET = { "C", "M", "D", "T" }
-- le 24 permutazioni dei moduli (0 CHARACTER, 1 MOVEMENT, 2 DIFFUSION, 3 TEXTURE)
local PERMS = {
  { 0, 1, 2, 3 }, { 0, 1, 3, 2 }, { 0, 2, 1, 3 }, { 0, 2, 3, 1 }, { 0, 3, 1, 2 }, { 0, 3, 2, 1 },
  { 1, 0, 2, 3 }, { 1, 0, 3, 2 }, { 1, 2, 0, 3 }, { 1, 2, 3, 0 }, { 1, 3, 0, 2 }, { 1, 3, 2, 0 },
  { 2, 0, 1, 3 }, { 2, 0, 3, 1 }, { 2, 1, 0, 3 }, { 2, 1, 3, 0 }, { 2, 3, 0, 1 }, { 2, 3, 1, 0 },
  { 3, 0, 1, 2 }, { 3, 0, 2, 1 }, { 3, 1, 0, 2 }, { 3, 1, 2, 0 }, { 3, 2, 0, 1 }, { 3, 2, 1, 0 },
}
-- suddivisioni quando RATE e TIME seguono il tempo
local TDIV = { 0.25, 1 / 3, 0.5, 0.75, 1, 1.5, 2, 3 }               -- quarti
local TDIV_N = { "1/16", "1/8T", "1/8", "1/8.", "1/4", "1/4.", "1/2", "1/2." }
local RDIV = { 0.0625, 0.125, 0.25, 0.5, 1, 2, 3, 4 }               -- cicli per quarto
local RDIV_N = { "4 BAR", "2 BAR", "1 BAR", "1/2", "1/4", "1/8", "1/8T", "1/16" }
local FSTYLE = { "LOW-PASS", "TILT", "HIGH-PASS" }   -- the pedal's order, low-pass first
local FSTYLE_ENG = { 1, 0, 2 }                            -- engine: 0 tilt, 1 low-pass, 2 high-pass

local PAGES = {
  { name = "CHARACTER", m = 1, a = { "amt1", "tilt" }, b = { "vol1", "sens" } },
  { name = "MOVEMENT", m = 2, a = { "amt2", "rate" }, b = { "vol2", "drift_m" } },
  { name = "DIFFUSION", m = 3, a = { "amt3", "time" }, b = { "vol3", "drift_d" } },
  { name = "TEXTURE", m = 4, a = { "amt4", "fstyle" }, b = { "vol4", nil } },
  { name = "PERF", a = { "mix", "output" }, b = { "order", "cap_pre" } },
}
local LABEL = { amt1 = "AMOUNT", amt2 = "AMOUNT", amt3 = "AMOUNT", amt4 = "AMOUNT", vol1 = "VOL", vol2 = "VOL",
  vol3 = "VOL", vol4 = "VOL", tilt = "TILT", rate = "RATE", time = "TIME", fstyle = "STYLE", sens = "SENS",
  drift_m = "DRIFT", drift_d = "DRIFT", mix = "MIX", output = "OUTPUT", order = "ORDINE", cap_pre = "CAPTURE" }
-- i pot "primari" registrati dal GESTURE (come P1-P8 del Gills)
local GEST = { "tilt", "amt1", "rate", "amt2", "time", "amt3", "amt4", "mix" }

local page, alt = 1, false
local mdev
local peak, clip_until = 0, 0
local msg, msg_until = "", 0
local rz, tz = 5, 5                     -- zone (1..8) di RATE e TIME
local beat_sec = 0.5
local cap = { st = "empty", t0 = 0, mode = 0, held = false, from_play = false }
local gest = { rec = false, play = false, frames = {}, used = {}, pos = 1, t0 = 0 }
local taps = {}
local keyt = {}                         -- istante di pressione dei tasti
local redraw_metro, gest_metro
local beat_clock
local saved = {}

local function now() return util.time() end
local function flash(s) msg, msg_until = s, now() + 1.5 end

-- zona 1..n con un po' di isteresi, come il Gills
local function zone(v, n, cur)
  local w = 1 / n
  local lo, hi = (cur - 1) * w - 0.02, cur * w + 0.02
  if v >= lo and v <= hi then return cur end
  return util.clamp(math.floor(v * n) + 1, 1, n)
end

local function tempo_on() return params:get("tempo_sync") == 2 end

-- da dove arriva il tempo: BPM = clock interno, CLK = MIDI (TRS o USB), LINK = Ableton Link
-- sulla rete (Ethernet o Wi-Fi) con il numero di peer collegati, CROW = crow
local function clock_tag()
  local s = params:get("clock_source")
  if s == 2 then return "CLK" end
  if s == 3 then
    local ok, n = pcall(function() return clock.link.get_number_of_peers() end)
    return (ok and type(n) == "number") and ("LINK" .. n) or "LINK"
  end
  if s == 4 then return "CROW" end
  return "BPM"
end


local function send_divs()
  engine.set("rdiv", RDIV[rz])
  engine.set("tdiv", TDIV[tz])
end

-- ---------------------------------------------------------------- capture
local function cap_send(rec, play, mode) engine.cap(rec, play, mode) end

-- premi = registra finche' tieni, lasci = suona (meno di 1 s = SUSTAIN, altrimenti LOOP).
-- Premuto mentre suona: quello vecchio sfuma e si registra subito di nuovo;
-- un colpo breve (meno di 0.25 s) invece ferma e cancella.
local function cap_press()
  if cap.st == "rec" then return end
  cap.from_play = cap.st == "play"
  cap.st = "rec"
  cap.t0 = now()
  cap_send(1, 0, cap.mode)
end

local function cap_release()
  if cap.st ~= "rec" then return end
  local dt = now() - cap.t0
  if cap.from_play and dt < 0.25 then
    cap.st = "empty"
    cap_send(0, 0, 0)
    flash("capture cancellato")
    return
  end
  if dt < 0.05 then
    cap.st = "empty"
    cap_send(0, 0, 0)
    return
  end
  cap.mode = dt < 1 and 1 or 0           -- meno di 1 s = SUSTAIN, altrimenti LOOP
  cap.st = "play"
  cap_send(0, 1, cap.mode)
end

-- ---------------------------------------------------------------- tap tempo
local function tap()
  local t = now()
  if #taps > 0 and t - taps[#taps] > 2 then taps = {} end
  table.insert(taps, t)
  while #taps > 4 do table.remove(taps, 1) end
  if #taps >= 2 then
    local sum = 0
    for i = 2, #taps do sum = sum + (taps[i] - taps[i - 1]) end
    local bpm = util.clamp(60 / (sum / (#taps - 1)), 20, 300)
    if params:get("clock_source") == 1 then
      params:set("clock_tempo", math.floor(bpm + 0.5))
    end
    params:set("tempo_sync", 2)
    flash(string.format("TAP %d bpm", math.floor(clock.get_tempo() + 0.5)))
  else
    params:set("tempo_sync", 2)
  end
end

-- ---------------------------------------------------------------- gesture
local function gest_toggle()
  if gest.rec then
    gest.rec = false
    local any = false
    gest.used = {}
    for k, id in ipairs(GEST) do
      local first = gest.frames[1] and gest.frames[1][k] or 0
      for _, f in ipairs(gest.frames) do
        if math.abs(f[k] - first) > 0.02 then gest.used[id] = true; any = true; break end
      end
    end
    gest.play = any and #gest.frames >= 2
    gest.pos = 1
    flash(gest.play and "GESTURE play" or "GESTURE vuoto")
  else
    gest.rec, gest.play, gest.frames, gest.used = true, false, {}, {}
    gest.bpm = clock.get_tempo()            -- la riproduzione segue i cambi di tempo
    flash("GESTURE rec")
  end
end

local function gest_clear()
  gest.rec, gest.play, gest.frames, gest.used = false, false, {}, {}
  flash("GESTURE cancellato")
end

local function gest_tick()
  if gest.rec then
    if #gest.frames < 30 * 60 then
      local f = {}
      for k, id in ipairs(GEST) do f[k] = params:get(id) end
      table.insert(gest.frames, f)
    end
  elseif gest.play then
    local n = #gest.frames
    gest.pos = gest.pos + clock.get_tempo() / (gest.bpm or clock.get_tempo())
    while gest.pos >= n do gest.pos = gest.pos - (n - 1) end
    local i0 = math.floor(gest.pos)
    local f = gest.pos - i0
    local any = false
    for k, id in ipairs(GEST) do
      if gest.used[id] then
        local a, b = gest.frames[i0][k], gest.frames[i0 + 1][k]
        params:set(id, a + f * (b - a))
        any = true
      end
    end
    if not any then gest.play = false end
  end
end

-- muovere a mano un controllo registrato ne cancella il gesto
local function touched(id)
  if gest.play and gest.used[id] then gest.used[id] = nil end
end

-- ---------------------------------------------------------------- MIDI
local function cc_zone5(v)
  if v <= 25 then return 1 elseif v <= 51 then return 2 elseif v <= 76 then return 3 elseif v <= 102 then return 4 end
  return 5
end

-- la mappa CC del pedale. Con "mappa MIDI" = live i CC 64, 80 e 82 restano quelli da palco
-- (capture, bypass, tap); con "pedale" sono come sull'originale (TILT, gesture, capture)
local CC_KNOB = { [64] = "tilt", [65] = "amt1", [66] = "rate", [67] = "amt2", [68] = "time", [69] = "amt3",
  [70] = "mix", [71] = "amt4", [72] = "sens", [73] = "vol1", [74] = "drift_m", [75] = "vol2",
  [76] = "drift_d", [77] = "vol3", [78] = "output", [79] = "vol4" }
local function pedal_cc(c, v)
  local on = v >= 64
  local id = CC_KNOB[c]
  if id then
    touched(id)
    params:set(id, v / 127)
  elseif c >= 16 and c <= 19 then                 -- effetto del modulo: 5 fasce, 110-127 = modulo spento
    local m, e = c - 15, v // 22
    if e > 4 then params:set("byp" .. m, 1)
    else params:set("fx" .. m, e + 1); params:set("byp" .. m, 0) end
  elseif c >= 103 and c <= 106 then params:set("byp" .. (c - 102), on and 0 or 1)
  elseif c == 80 then if on ~= gest.rec then gest_toggle() end      -- gesture: 64-127 registra, 0-63 suona
  elseif c == 81 then gest_clear()
  elseif c == 82 then                             -- capture: 88-127 registra, 44-87 suona, 0-43 ferma e cancella
    if v >= 88 then cap_press()
    elseif v >= 44 then cap_release()
    else cap.st = "empty"; cap_send(0, 0, 0) end
  elseif c == 83 then params:set("cap_pre", on and 2 or 1)
  elseif c == 84 then params:set("fstyle", v < 44 and 1 or (v < 88 and 2 or 3))   -- low-pass, tilt, high-pass
  elseif c == 91 then params:set("bypass", on and 0 or 1)           -- 0-63 bypass, 64-127 attivo
  elseif c == 93 then if v > 0 then tap() end
  end
end

local function midi_event(data)
  local m = midi.to_msg(data)
  if m.ch == nil then return end
  local ch = params:get("midi_ch") - 1
  if ch > 0 and m.ch ~= ch then return end
  if m.type ~= "cc" then return end
  local c, v = m.cc, m.val
  local live = params:get("midi_map") == 1
  if live and c == 64 then
    if v >= 64 then if not cap.held then cap.held = true; cap_press() end
    else if cap.held then cap.held = false; cap_release() end end
  elseif live and c == 80 then params:set("bypass", v >= 64 and 1 or 0)
  elseif live and c == 82 then if v >= 64 then tap() end
  elseif c >= 20 and c <= 23 then params:set("fx" .. (c - 19), cc_zone5(v))
  elseif c >= 24 and c <= 27 then params:set("byp" .. (c - 23), v >= 64 and 1 or 0)
  elseif c == 28 then params:set("order", util.clamp(math.floor(v * 24 / 128) + 1, 1, 24))
  else pedal_cc(c, v)
  end
end

local function connect_midi()
  if mdev then mdev.event = nil end
  mdev = midi.connect(params:get("midi_port"))
  mdev.event = midi_event
end

-- ---------------------------------------------------------------- params
local function pct(p) return string.format("%d%%", math.floor(p:get() * 100 + 0.5)) end

local function add_params()
  local cs = controlspec
  params:add_separator("chroma", "CHROMA")

  params:add_group("chroma_io", "INGRESSO / USCITA", 4)
  params:add_option("input", "ingresso", { "mono L", "stereo", "L+R" }, 1)
  params:set_action("input", function(v) engine.set("inMode", v - 1) end)
  -- mix (default): catena solo-wet + vero dry/wet (MIX 100 = solo effetto, per un bus); insert: moduli in serie
  -- come sul pedale; aux: mai dry, MIX = livello del ritorno
  params:add_option("routing", "routing", { "aux (send/return)", "insert (serie)", "mix (dry/wet)" }, 3)
  params:set_action("routing", function(v) engine.set("aux", ({ 1, 0, 2 })[v]) end)
  params:add_option("out_mode", "uscita", { "stereo", "mono" }, 1)
  params:set_action("out_mode", function(v) engine.set("omono", v - 1) end)
  params:add_control("output", "output", cs.new(0, 1, "lin", 0, 0.5, ""),
    function(p) return string.format("%+.1f dB", 20 * math.log(math.max(p:get() * 2, 0.0001), 10)) end)
  params:set_action("output", function(v) engine.set("olev", v) end)

  for m = 1, 4 do
    params:add_group("chroma_m" .. m, MODS[m], 4)
    params:add_option("fx" .. m, "effetto", FX[m], 1)
    params:set_action("fx" .. m, function(v) engine.fx(m - 1, v - 1) end)
    params:add_control("amt" .. m, "amount", cs.new(0, 1, "lin", 0, 0.5, ""), pct)
    params:set_action("amt" .. m, function(v) engine.mod(m - 1, "amt", v) end)
    params:add_control("vol" .. m, "vol", cs.new(0, 1, "lin", 0, 0.5, ""),
      function(p) return string.format("%+.1f dB", 20 * math.log(math.max(p:get() * 2, 0.0001), 10)) end)
    params:set_action("vol" .. m, function(v) engine.mod(m - 1, "vol", v) end)
    params:add_binary("byp" .. m, "bypass", "toggle", 0)
    params:set_action("byp" .. m, function(v) engine.mod(m - 1, "on", 1 - v) end)
  end

  params:add_group("chroma_knobs", "CONTROLLI", 8)
  params:add_control("tilt", "tilt", cs.new(0, 1, "lin", 0, 0.5, ""),
    function(p) return string.format("%+d", math.floor((p:get() - 0.5) * 20 + 0.5)) end)
  params:set_action("tilt", function(v) engine.set("tilt", v) end)
  params:add_control("rate", "rate", cs.new(0, 1, "lin", 0, 0.5, ""),
    function(p)
      if params:get("fx2") == 5 then            -- PITCH: continuo, +-12 semitoni, niente attorno al centro
        local u = (p:get() - 0.5) * 2
        local a = math.max((math.abs(u) - 0.05) / 0.95, 0)
        return string.format("%+.1f st", (u < 0 and -12 or 12) * a)
      end
      if tempo_on() then return RDIV_N[rz] end
      return string.format("%.2f Hz", 0.05 * 2 ^ (p:get() * 8))
    end)
  params:set_action("rate", function(v)
    engine.set("rate", v)
    local z = zone(v, 8, rz)
    if z ~= rz then rz = z; send_divs() end
  end)
  params:add_control("time", "time", cs.new(0, 1, "lin", 0, 0.5, ""),
    function(p)
      local e = params:get("fx3")
      if tempo_on() and e ~= 3 and e ~= 5 then return TDIV_N[tz] end
      if e == 3 then
        local n = { "ROOM", "HALL", "CATHEDRAL", "HUGE", "HUGE" }
        return n[math.floor(p:get() * 4) + 1]
      elseif e == 5 then                        -- REVERSE: velocita' dei pezzi al contrario
        local v = p:get()
        return string.format("x%.2f", (v > 0.47 and v < 0.53) and 1 or 2 ^ ((v - 0.5) * 2))
      elseif e == 4 then
        return string.format("%d ms", math.floor(1200 * 2 ^ (p:get() * 6.3) / 48 + 0.5))
      end
      return string.format("%d ms", math.floor(1440 * 2 ^ (p:get() * 5.3) / 48 + 0.5))
    end)
  params:set_action("time", function(v)
    engine.set("time", v)
    local z = zone(v, 8, tz)
    if z ~= tz then tz = z; send_divs() end
  end)
  -- due DRIFT come sul pedale: uno per MOVEMENT, uno per DIFFUSION
  params:add_control("drift_m", "drift movement", cs.new(0, 1, "lin", 0, 0, ""), pct)
  params:set_action("drift_m", function(v) engine.set("driftm", v) end)
  params:add_control("drift_d", "drift diffusion", cs.new(0, 1, "lin", 0, 0, ""), pct)
  params:set_action("drift_d", function(v) engine.set("driftd", v) end)
  params:add_control("sens", "sensitivity", cs.new(0, 1, "lin", 0, 0.5, ""),
    function(p) return string.format("%+.1f dB", (p:get() - 0.5) * 5 * 6.02) end)
  params:set_action("sens", function(v) engine.set("sens", v) end)
  params:add_option("fstyle", "filter style", FSTYLE, 1)
  params:set_action("fstyle", function(v) engine.set("fstyle", FSTYLE_ENG[v]) end)
  params:add_control("mix", "mix", cs.new(0, 1, "lin", 0, 1, ""), pct)
  params:set_action("mix", function(v) engine.set("mix", v) end)

  params:add_group("chroma_perf", "CATENA E LIVE", 5)
  local onames = {}
  for i, pm in ipairs(PERMS) do
    local s = {}
    for j = 1, 4 do s[j] = MLET[pm[j] + 1] end
    onames[i] = table.concat(s, ">")
  end
  params:add_option("order", "ordine", onames, 1)
  params:set_action("order", function(v)
    local pm = PERMS[v]
    engine.order(pm[1], pm[2], pm[3], pm[4])
  end)
  params:add_binary("bypass", "bypass (con code)", "toggle", 0)
  params:set_action("bypass", function(v) engine.set("byp", v) end)
  params:add_option("cap_pre", "capture", { "post (uscita)", "pre (ingresso)" }, 1)
  params:set_action("cap_pre", function(v) engine.set("pre", v - 1) end)
  params:add_option("tempo_sync", "rate/time", { "liberi", "seguono il tempo" }, 1)
  params:set_action("tempo_sync", function(v)
    engine.set("tempo", v - 1)
    send_divs()
  end)
  params:add_trigger("tap", "tap tempo")
  params:set_action("tap", function() tap() end)

  params:add_group("chroma_midi", "MIDI", 3)
  local ports = {}
  for i = 1, 16 do ports[i] = i .. ": " .. ((midi.vports[i] and midi.vports[i].name) or "none") end
  params:add_option("midi_port", "porta", ports, 1)
  params:set_action("midi_port", function() connect_midi() end)
  local chs = { "omni" }
  for i = 1, 16 do chs[i + 1] = tostring(i) end
  params:add_option("midi_ch", "canale", chs, 1)
  params:add_option("midi_map", "mappa MIDI", { "live", "pedale" }, 1)
end

-- ---------------------------------------------------------------- init / cleanup
function init()
  audio.level_monitor(0)                 -- il dry passa dentro l'engine
  audio.rev_off()
  audio.comp_off()
  audio.pitch_off()

  add_params()
  params:default()
  connect_midi()
  send_divs()
  engine.set("beat", 60 / clock.get_tempo())

  -- clock di norns (interno, MIDI, Link): tempo e battere per l'LFO
  local last_src = nil
  beat_clock = clock.run(function()
    while true do
      clock.sync(1)
      -- come sul Gills: quando il tempo arriva da fuori (MIDI, Link, crow) RATE e TIME lo seguono
      local src = params:get("clock_source")
      if src ~= last_src then
        last_src = src
        if src ~= 1 and not tempo_on() then params:set("tempo_sync", 2) end
      end
      local b = 60 / clock.get_tempo()
      if math.abs(b - beat_sec) > 0.0005 then
        beat_sec = b
        engine.set("beat", b)
      end
      if tempo_on() then
        local n = math.floor(clock.get_beats() + 0.5)
        -- il punto piu' forte del TREMOLO cade sul battere
        engine.beat((n * RDIV[rz] + 0.75) % 1)
      end
    end
  end)
  clock.transport.start = function() params:set("tempo_sync", 2) end

  local p = poll.set("peak")
  if p then
    p.callback = function(v)
      peak = v
      if v > 0.98 then clip_until = now() + 0.5 end
    end
    p.time = 1 / 15
    p:start()
  end

  gest_metro = metro.init(function()
    gest_tick()
    if cap.st == "rec" and now() - cap.t0 > 30 then cap_release() end   -- capture: 30 s al massimo
  end, 1 / 30, -1)
  gest_metro:start()
  redraw_metro = metro.init(function() redraw() end, 1 / 15, -1)
  redraw_metro:start()
end

function cleanup()
  if redraw_metro then redraw_metro:stop() end
  if gest_metro then gest_metro:stop() end
  if beat_clock then clock.cancel(beat_clock) end
  clock.transport.start = nil
  if mdev then mdev.event = nil end
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
  local pg = PAGES[page]
  local id = (alt and pg.b or pg.a)[n - 1]
  if not id then return end
  touched(id)
  params:delta(id, d)
end

function key(n, z)
  if n == 1 then
    alt = z == 1
    return
  end
  -- l'azione si decide alla pressione (K1 puo' essere lasciato prima di K2/K3)
  if z == 1 then keyt[n] = { t = now(), alt = alt } end
  local k = keyt[n] or { t = now(), alt = alt }
  local held = z == 0 and (now() - k.t) or 0
  local pg = PAGES[page]
  -- K1+K3: TAP alla pressione; tenuto 1 s = tempo off (da tutte le pagine)
  if n == 3 and k.alt then
    if z == 1 then
      tap()
    elseif held >= 1 then
      table.remove(taps)
      params:set("tempo_sync", 1)
      flash("TEMPO OFF")
    end
    return
  end
  if pg.m then
    if z == 1 then
      if n == 2 then
        local m = pg.m
        local e = params:get("fx" .. m)
        e = k.alt and ((e + 3) % 5 + 1) or (e % 5 + 1)
        params:set("fx" .. m, e)
        flash(MODS[m] .. " " .. FX[m][e])
      elseif n == 3 then
        params:set("byp" .. pg.m, 1 - params:get("byp" .. pg.m))
      end
    end
    return
  end
  -- pagina PERF
  if n == 2 and k.alt then
    if z == 0 then
      if held >= 1 then gest_clear() else gest_toggle() end
    end
  elseif n == 2 then
    if z == 1 then cap_press() else cap_release() end
  elseif n == 3 and z == 1 then
    params:set("bypass", 1 - params:get("bypass"))
  end
end

-- ---------------------------------------------------------------- schermo
function redraw()
  screen.clear()
  screen.aa(0)
  screen.font_face(1)
  screen.font_size(8)
  -- riga 1: la catena nell'ordine, minuscolo = modulo in bypass
  local pm = PERMS[params:get("order")]
  local x = 0
  for i = 1, 4 do
    local m = pm[i] + 1
    local s = SHORT[m][params:get("fx" .. m)]
    if params:get("byp" .. m) == 1 then s = string.lower(s) end
    screen.level((PAGES[page].m == m) and 15 or 5)
    screen.move(x, 7)
    screen.text(s)
    x = x + 22
    if i < 4 then
      screen.level(2)
      screen.move(x - 4, 7)
      screen.text(">")
    end
  end
  screen.level(5)
  screen.move(127, 7)
  screen.text_right(({ "AUX", "INS", "MIX" })[params:get("routing")])

  -- riga 2: tempo, capture, gesture, bypass, clip
  local st = {}
  if tempo_on() then
    st[#st + 1] = string.format("%d", math.floor(clock.get_tempo() + 0.5)) ..
      clock_tag()
  end
  if cap.st == "rec" then st[#st + 1] = string.format("REC %.1f", now() - cap.t0)
  elseif cap.st == "play" then st[#st + 1] = cap.mode == 1 and "SUS" or "LOOP" end
  if gest.rec then st[#st + 1] = "G-REC" elseif gest.play then st[#st + 1] = "G-PLAY" end
  if params:get("bypass") == 1 then st[#st + 1] = "BYPASS" end
  if now() < clip_until then st[#st + 1] = "CLIP" end
  screen.level(10)
  screen.move(0, 17)
  screen.text(table.concat(st, " "))

  -- pagina
  local pg = PAGES[page]
  screen.move(0, 31)
  if now() < msg_until then
    screen.level(15)
    screen.text(msg)
  else
    screen.level(15)
    screen.font_size(8)
    if pg.m then
      local m = pg.m
      local e = params:get("fx" .. m)
      screen.text(MODS[m])
      screen.move(127, 31)
      screen.level(params:get("byp" .. m) == 1 and 4 or 15)
      screen.text_right((params:get("byp" .. m) == 1 and "bypass " or "") .. FX[m][e])
    else
      screen.text("PERF")
      screen.move(127, 31)
      screen.level(8)
      screen.text_right(params:string("cap_pre"))
    end
  end
  screen.level(3)
  screen.move(0, 35)
  screen.line(127, 35)
  screen.stroke()

  local ids = alt and pg.b or pg.a
  for i = 1, 2 do
    local y = 36 + 11 * i
    local id = ids[i]
    if id then
      screen.level(alt and 6 or 4)
      screen.move(0, y)
      screen.text("E" .. (i + 1) .. " " .. LABEL[id])
      screen.level((gest.play and gest.used[id]) and 6 or 15)
      screen.move(127, y)
      screen.text_right(params:string(id))
    end
  end
  screen.level(3)
  screen.move(0, 63)
  screen.text(page .. "/" .. #PAGES .. (alt and "  K1" or ""))
  screen.update()
end
