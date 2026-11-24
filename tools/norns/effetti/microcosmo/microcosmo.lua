-- microcosmo
-- 11 effetti x 4 varianti
-- (stile Hologram Microcosm)
--
-- E1 preset  K1+E1 pagina
-- E2 E3 valori, K1: sotto
-- K2 HOLD (non col looper)
-- K3 LOOP rec>play>dub
--    (tenuto 1 s: UNDO)
-- K1+K2 TAP (tenuto: BYPASS)
-- K1+K3 LOOP stop/play
--    (tenuto 1 s: ERASE)
-- REVERSE FX: pag. OPZIONI, CC85
--
-- v0.2 dal patch Ksoloti Gills

engine.name = "GillsMicrocosmo"

-- i preset nell'ordine del pedale; AID = numero dell'effetto nell'engine per ogni posto
local ALGOS = { "MOSAIC", "SEQ", "GLIDE", "BLOCKS", "INTERRUPT", "ARP", "HAZE", "TUNNEL", "STRUM", "PATTERN", "WARP" }
local AID = { 0, 1, 2, 6, 7, 8, 3, 4, 5, 9, 10 }
local BANKS = { "MICRO LOOP", "MICRO LOOP", "MICRO LOOP", "GLITCH", "GLITCH", "GLITCH",
  "GRANULES", "GRANULES", "GRANULES", "MULTIDELAY", "MULTIDELAY" }
local SHAPES = { "SQUARE", "RAMP", "TRIANGLE", "SAW" }
local SUBS = { "1/4", "1/2", "TAP", "2x", "4x", "8x" }
local SUBM = { 0.25, 0.5, 1, 2, 4, 8 }
local LSP = { 0.25, 0.5, 1, 2, 4 }
local RMODES = { "A ROOM", "B DARK", "C HALL", "D AMBIENT" }
local LSTATE = { [0] = "----", "REC", "PLAY", "DUB", "STOP" }

local PAGES = {
  { name = "SOUND", a = { "activity", "repeats" }, b = { "mod_depth", "mod_rate" } },
  { name = "COLORE", a = { "shape", "filter" }, b = { "resonance", "reverb_mode" } },
  { name = "MIX", a = { "mix", "space" }, b = { "fx_volume", "looper_only" } },
  { name = "TIME / LOOP", a = { "time", "loop_level" }, b = { "loop_speed", "loop_fade" } },
  { name = "OPZIONI", a = { "fx_reverse", "loop_pre" }, b = { "time_mode", "hold_mode" } },
  { name = "LOOPER", a = { "reverse", "loop_shape" }, b = { "loop_quant", "loop_burst" } },
}
local LABEL = { activity = "ACTIVITY", repeats = "REPEATS", mod_depth = "MOD DEPTH", mod_rate = "MOD RATE",
  shape = "SHAPE", filter = "FILTER", resonance = "RESONANCE", reverb_mode = "REVERB", mix = "MIX",
  space = "SPACE", fx_volume = "FX VOLUME", time = "TIME", loop_level = "LOOP LEVEL", loop_speed = "LOOP SPEED",
  loop_fade = "LOOP FADE", reverse = "LOOP REV", loop_pre = "LOOPER", time_mode = "TIME MODE", hold_mode = "HOLD",
  fx_reverse = "REVERSE FX", looper_only = "LOOPER ONLY", loop_shape = "FADE", loop_quant = "QUANTIZE",
  loop_burst = "BURST" }

local page, alt = 1, false
local mdev
local peak, clip_until = 0, 0
local msg, msg_until = "", 0
local lstate, llen = 0, 0
local subZone, lsZone, rvZone = 3, 3, 1
local tempo_knob = false              -- in TEMPO: il pot TIME comanda finche' non arriva TAP o START
local qcnt = 0
local keyt = {}
local hold_cc = false
local cc_burst = false                -- CC81 premuto ha aperto una ripresa BURST
local beat_clock, redraw_metro
local polls = {}

local function now() return util.time() end
local function flash(s) msg, msg_until = s, now() + 1.5 end

local function zone(v, n, cur)
  local w = 1 / n
  local lo, hi = (cur - 1) * w - 0.02, cur * w + 0.02
  if v >= lo and v <= hi then return cur end
  return util.clamp(math.floor(v * n) + 1, 1, n)
end

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

local function knob_bpm() return 40 * 2 ^ (params:get("time") * 2.585) end
local function tempo_mode() return params:get("time_mode") == 2 end
local function bpm_now()
  if tempo_mode() and tempo_knob then return knob_bpm() end
  return clock.get_tempo()
end

-- QUANTIZE: una semiminima in campioni (0 = spento)
local function send_qlen()
  local q = params:get("loop_quant") == 2 and math.floor(2880000 / bpm_now() + 0.5) or 0
  engine.set("qlen", q)
end

-- lunghezza della battuta per l'engine (campioni), come nel Gills
local function send_beat()
  local m = tempo_mode() and 1 or SUBM[subZone]
  local bl = util.clamp(2880000 / (bpm_now() * m), 1440, 192000)
  engine.set("beat", bl)
  send_qlen()
end

local function loop_speed()
  if not tempo_mode() then return LSP[lsZone] end
  local v = params:get("loop_speed")
  if v > 0.46 and v < 0.54 then return 1 end
  local x = v < 0.5 and (v / 0.46) - 1 or (v - 0.54) / 0.46
  local sp = 2 ^ (math.abs(x) * 2)
  return x < 0 and 1 / sp or sp
end

local function send_lspd() engine.set("lspd", loop_speed()) end

-- ---------------------------------------------------------------- azioni live
local function tap()
  local t = now()
  keyt.taps = keyt.taps or {}
  local taps = keyt.taps
  if #taps > 0 and t - taps[#taps] > 2.5 then for i = #taps, 1, -1 do taps[i] = nil end end
  table.insert(taps, t)
  while #taps > 4 do table.remove(taps, 1) end
  if #taps >= 2 then
    local sum = 0
    for i = 2, #taps do sum = sum + (taps[i] - taps[i - 1]) end
    local bpm = util.clamp(60 / (sum / (#taps - 1)), 20, 300)
    if params:get("clock_source") == 1 then params:set("clock_tempo", math.floor(bpm + 0.5)) end
  end
  tempo_knob = false
  engine.tap()
  send_beat()
end

local function loop_active() return lstate >= 1 and lstate <= 3 end

-- HOLD non funziona mentre il looper registra o suona (come sul pedale)
local function set_hold(on)
  if on and loop_active() then flash("HOLD: NO COL LOOPER"); on = false end
  params:set("hold", on and 1 or 0)
end

local function loop_cmd(c)
  -- far partire il looper (rec, o play da STOP) spegne HOLD
  if (c == 1 and (lstate == 0 or lstate == 4)) or (c == 2 and lstate == 4) then
    if params:get("hold") == 1 then params:set("hold", 0) end
  end
  engine.loop(c)
  local names = { "", "", "LOOP ERASE", "UNDO" }
  if names[c] ~= "" then flash(names[c]) end
end

-- BURST: loop a strato unico, registra finche' tieni premuto e suona quando lasci;
-- se c'e' gia' un loop, premere lo cancella e ne registra subito uno nuovo
local function burst_take() return params:get("loop_burst") == 2 end
local function burst_start()
  if lstate ~= 0 then engine.loop(3) end
  loop_cmd(1)
end

-- ---------------------------------------------------------------- MIDI
-- la mappa CC del pedale (accanto ai CC "live" 64 e 80-86, che restano)
local CC_KNOB = { [6] = "activity", [8] = "filter", [9] = "mix", [11] = "repeats", [12] = "space",
  [13] = "loop_level", [14] = "mod_rate", [15] = "resonance", [16] = "fx_volume", [17] = "loop_speed",
  [18] = "loop_speed", [19] = "mod_depth", [21] = "loop_fade" }
local function pedal_cc(c, v)
  local on = v >= 64
  if CC_KNOB[c] then params:set(CC_KNOB[c], v / 127)
  elseif c == 5 then                                   -- suddivisione 0-5
    params:set("time_mode", 1)
    params:set("time", (math.min(v, 5) + 0.5) / 6)
  elseif c == 7 then params:set("shape", (v >> 5) + 1)  -- quattro fasce
  elseif c == 10 then                                  -- TIME: il tempo, 40..240 BPM
    if params:get("clock_source") == 1 then
      params:set("clock_tempo", math.floor(40 * 2 ^ (v / 127 * 2.585) + 0.5))
    end
    tempo_knob = false
    send_beat()
  elseif c == 20 then params:set("reverb_mode", (v >> 5) + 1)
  elseif c == 23 then params:set("reverse", on and 1 or 0)
  elseif c == 24 then params:set("loop_pre", on and 2 or 1)
  elseif c == 25 then params:set("looper_only", on and 2 or 1)
  elseif c == 26 then params:set("loop_burst", on and 2 or 1)
  elseif c == 27 then params:set("loop_quant", on and 2 or 1)
  elseif c == 28 then                                  -- record: una ripresa nuova
    if lstate ~= 1 then
      if lstate ~= 0 then engine.loop(3) end
      loop_cmd(1)
    end
  elseif c == 29 then if lstate == 1 or lstate == 3 or lstate == 4 then loop_cmd(1) end   -- play
  elseif c == 30 then if lstate == 1 or lstate == 2 or lstate == 4 then loop_cmd(1) end   -- overdub (da play)
  elseif c == 31 then if lstate >= 1 and lstate <= 3 then loop_cmd(2) end                 -- stop
  elseif c == 34 then loop_cmd(3)
  elseif c == 35 then loop_cmd(4)
  elseif c == 47 then params:set("fx_reverse", on and 1 or 0)
  elseif c == 48 then set_hold(on)
  elseif c == 93 then if v > 0 then tap() end
  elseif c == 102 then params:set("bypass", on and 0 or 1)   -- 0-63 bypass, 64-127 attivo
  end
end

local function midi_event(data)
  local m = midi.to_msg(data)
  if m.ch == nil then return end
  local ch = params:get("midi_ch") - 1
  if ch > 0 and m.ch ~= ch then return end
  if m.type == "cc" then
    local on = m.val >= 64
    if m.cc == 64 then
      if on ~= hold_cc then hold_cc = on; set_hold(on) end
    elseif m.cc == 80 then params:set("bypass", on and 1 or 0)
    elseif m.cc == 85 then params:set("fx_reverse", on and 1 or 0)
    elseif m.cc == 81 and not on then
      if cc_burst then cc_burst = false; loop_cmd(1) end
    elseif m.cc >= 81 and m.cc <= 86 then
      if on then
        if m.cc == 81 then
          cc_burst = burst_take()
          if cc_burst then burst_start() else loop_cmd(1) end
        elseif m.cc == 86 then loop_cmd(4)
        elseif m.cc == 82 then tap()
        elseif m.cc == 83 then loop_cmd(2)
        elseif m.cc == 84 then loop_cmd(3)
        end
      end
    else
      pedal_cc(m.cc, m.val)
    end
  elseif m.type == "program_change" then
    -- come nella tabella del pedale: 1-4 ARP A-D, 5-8 INTERRUPT, 9-12 BLOCKS, 13-16 GLIDE, 17-20 SEQ,
    -- 21-24 MOSAIC, 25-28 HAZE, 29-32 TUNNEL, 33-36 STRUM, 37-40 PATTERN, 41-44 WARP
    -- (45-60 sono i preset utente del pedale: qui niente)
    local pc = m.val - 1
    if pc >= 0 and pc < 44 then
      local g = pc // 4
      params:set("preset", (g < 6 and 5 - g or g) * 4 + pc % 4 + 1)
    end
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
  local function ctl(id, name, def, fmt, action)
    params:add_control(id, name, cs.new(0, 1, "lin", 0, def, ""), fmt or pct)
    params:set_action(id, action)
  end
  params:add_separator("microcosmo", "MICROCOSMO")
  local pnames = {}
  for a = 1, 11 do for v = 1, 4 do pnames[#pnames + 1] = ALGOS[a] .. " " .. string.char(64 + v) end end
  params:add_option("preset", "preset", pnames, 1)
  params:set_action("preset", function(i)
    engine.preset(AID[(i - 1) // 4 + 1], (i - 1) % 4)
  end)

  params:add_group("mc_sound", "SUONO", 11)
  ctl("activity", "activity", 0.5, nil, function(v) engine.set("act", v) end)
  ctl("repeats", "repeats", 0.5, nil, function(v) engine.set("rep", v) end)
  -- SHAPE: le quattro forme del pedale (l'engine riceve il centro della zona)
  params:add_option("shape", "shape", SHAPES, 1)
  params:set_action("shape", function(v) engine.set("shp", (v - 0.5) / 4) end)
  ctl("mod_depth", "mod depth", 0, nil, function(v) engine.set("moddep", v) end)
  ctl("mod_rate", "mod rate", 0, function(p) return string.format("%.2f Hz", 0.05 * 2 ^ (p:get() * 7)) end,
    function(v) engine.set("modrate", v) end)
  ctl("filter", "filter", 1, function(p)
    local v = p:get()
    if v > 0.94 then return "OPEN" elseif v < 0.03 then return "OFF" end
    local f = 20 * 2 ^ (v * 10)
    return f < 1000 and string.format("%d Hz", math.floor(f)) or string.format("%.1f k", f / 1000)
  end, function(v) engine.set("flt", v) end)
  ctl("resonance", "resonance", 0, nil, function(v) engine.set("res", v) end)
  params:add_option("reverb_mode", "reverb", RMODES, 1)
  params:set_action("reverb_mode", function(v) engine.set("rmode", v - 1) end)
  ctl("space", "space", 0, nil, function(v) engine.set("spc", v) end)
  -- l'eco dentro SPACE segue il tempo, resta come a 120 BPM, oppure e' spento (solo riverbero)
  params:add_option("space_echo", "space echo", { "a tempo", "libero", "spento" }, 1)
  params:set_action("space_echo", function(v) engine.set("secho", v - 1) end)
  ctl("mix", "mix", 1, nil, function(v) engine.set("mix", v) end)

  params:add_group("mc_time", "TEMPO E LOOPER", 15)
  params:add_binary("fx_reverse", "reverse effetto", "toggle", 0)
  params:set_action("fx_reverse", function(v) engine.set("frev", v) end)
  ctl("fx_volume", "fx volume", 0.5, function(p)
    return string.format("%+.1f dB", 20 * math.log(math.max(p:get() * 2, 0.0001), 10))
  end, function(v) engine.set("fxv", v) end)
  params:add_option("time_mode", "time mode", { "SUBDIV", "TEMPO" }, 1)
  params:set_action("time_mode", function() send_beat(); send_lspd() end)
  ctl("time", "time", 0.42, function(p)
    if tempo_mode() then return string.format("%.1f BPM", knob_bpm()) end
    return SUBS[subZone]
  end, function(v)
    subZone = zone(v, 6, subZone)
    send_beat()
  end)
  ctl("loop_level", "loop level", 0.714, nil, function(v) engine.set("llev", v) end)
  ctl("loop_speed", "loop speed", 0.5, function() return string.format("%.2fx", loop_speed()) end, function(v)
    lsZone = zone(v, 5, lsZone)
    send_lspd()
  end)
  ctl("loop_fade", "loop fade", 0.25, function(p)
    local t = 0.005 * 2 ^ (p:get() * 11)
    return t < 1 and string.format("%d ms", math.floor(t * 1000 + 0.5)) or string.format("%.1f s", t)
  end, function(v) engine.set("lfade", 0.005 * 2 ^ (v * 11)) end)
  params:add_binary("reverse", "loop reverse", "toggle", 0)
  params:set_action("reverse", function(v) engine.set("lrev", v) end)
  params:add_option("loop_pre", "looper", { "POST fx", "PRE fx" }, 1)
  params:set_action("loop_pre", function(v) engine.set("pre", v - 1) end)
  params:add_binary("hold", "hold", "toggle", 0)
  params:set_action("hold", function(v) engine.set("hold", v) end)
  params:add_option("hold_mode", "hold", { "toggle", "momentaneo" }, 1)
  params:add_option("loop_shape", "loop fade", { "in+out", "solo in", "solo out" }, 1)
  params:set_action("loop_shape", function(v) engine.set("lshape", v - 1) end)
  params:add_option("loop_quant", "quantize", { "off", "semiminima" }, 1)
  params:set_action("loop_quant", function() send_qlen() end)
  params:add_option("loop_burst", "burst", { "off", "on" }, 1)
  params:add_option("looper_only", "looper only", { "off", "on" }, 1)
  params:set_action("looper_only", function(v) engine.set("lonly", v - 1) end)

  params:add_group("mc_io", "INGRESSO / USCITA", 4)
  params:add_option("input", "ingresso", { "mono L", "stereo", "L+R" }, 1)
  params:set_action("input", function(v) engine.set("inMode", v - 1) end)
  params:add_option("routing", "routing", { "aux (send/return)", "insert (dry/wet)" }, 2)
  params:set_action("routing", function(v) engine.set("aux", v == 1 and 1 or 0) end)
  params:add_option("out_mode", "uscita", { "stereo", "mono" }, 1)
  params:set_action("out_mode", function(v) engine.set("omono", v - 1) end)
  params:add_binary("bypass", "bypass (con code)", "toggle", 0)
  params:set_action("bypass", function(v) engine.set("kill", v) end)

  params:add_group("mc_midi", "MIDI", 2)
  local ports = {}
  for i = 1, 16 do ports[i] = i .. ": " .. ((midi.vports[i] and midi.vports[i].name) or "none") end
  params:add_option("midi_port", "porta", ports, 1)
  params:set_action("midi_port", function() connect_midi() end)
  local chs = { "omni" }
  for i = 1, 16 do chs[i + 1] = tostring(i) end
  params:add_option("midi_ch", "canale", chs, 1)
end

-- ---------------------------------------------------------------- init / cleanup
function init()
  audio.level_monitor(0)                 -- il dry lo gestisce l'engine: MIX e' un dry/wet (in aux non c'e')
  audio.rev_off()
  audio.comp_off()
  audio.pitch_off()

  add_params()
  params:default()
  connect_midi()
  send_beat()
  send_lspd()

  -- clock di norns: tempo e griglia (in SUBDIV 1/4 e 1/2 la griglia si riallinea ogni 4 e 2 battute)
  beat_clock = clock.run(function()
    local last = 0
    while true do
      clock.sync(1)
      local b = clock.get_tempo()
      if math.abs(b - last) > 0.05 then last = b; send_beat() end
      if not (tempo_mode() and tempo_knob) then
        local per = (not tempo_mode() and subZone == 1) and 4 or ((not tempo_mode() and subZone == 2) and 2 or 1)
        -- con Link la battuta e' quella della sessione (quantum): i battere coincidono con gli altri peer
        local n = params:get("clock_source") == 3 and math.floor(clock.get_beats() + 0.5) or qcnt
        if n % per == 0 then engine.sync() end
        qcnt = qcnt + 1
      end
    end
  end)
  clock.transport.start = function()
    qcnt = 0
    tempo_knob = false
    send_beat()
  end

  for name, f in pairs({
    peak = function(v) peak = v; if v > 0.98 then clip_until = now() + 0.5 end end,
    lstate = function(v)
      lstate = math.floor(v + 0.5)
      if loop_active() and params:get("hold") == 1 then params:set("hold", 0) end
    end,
    llen = function(v) llen = v end,
  }) do
    local p = poll.set(name)
    if p then
      p.callback = f
      p.time = 1 / 15
      p:start()
      polls[name] = p
    end
  end

  redraw_metro = metro.init(function() redraw() end, 1 / 15, -1)
  redraw_metro:start()
end

function cleanup()
  if redraw_metro then redraw_metro:stop() end
  if beat_clock then clock.cancel(beat_clock) end
  clock.transport.start = nil
  for _, p in pairs(polls) do p:stop() end
  if mdev then mdev.event = nil end
  audio.level_monitor(util.dbamp(params:get("monitor_level")))
  if params:get("reverb") == 2 then audio.rev_on() end
  if params:get("compressor") == 2 then audio.comp_on() end
  audio.pitch_on()
end

-- ---------------------------------------------------------------- controlli
function enc(n, d)
  if n == 1 then
    if alt then page = util.clamp(page + d, 1, #PAGES)
    else params:delta("preset", d) end
    return
  end
  local pg = PAGES[page]
  local id = (alt and pg.b or pg.a)[n - 1]
  if not id then return end
  if id == "time" and tempo_mode() then tempo_knob = true end
  params:delta(id, d)
  if id == "time" then send_beat() end
end

-- azioni "tenuto 1 s" mentre il tasto e' ancora premuto
local function hold_check(n, id, f)
  clock.run(function()
    clock.sleep(1)
    if keyt[n] and keyt[n].id == id then
      keyt[n].long = true
      f()
    end
  end)
end

function key(n, z)
  if n == 1 then
    alt = z == 1
    return
  end
  if z == 1 then
    local k = { t = now(), alt = alt, id = math.random(1, 1000000000), long = false }
    keyt[n] = k
    if n == 2 and not alt then
      if params:get("hold_mode") == 2 then set_hold(true)
      else set_hold(params:get("hold") == 0) end
    elseif n == 2 and alt then
      tap()
      hold_check(2, k.id, function()
        local taps = keyt.taps
        if taps then table.remove(taps) end
        params:set("bypass", 1 - params:get("bypass"))
        flash(params:get("bypass") == 1 and "BYPASS" or "bypass off")
      end)
    elseif n == 3 and not alt then
      k.burst = burst_take()
      if k.burst then burst_start()
      else
        loop_cmd(1)
        hold_check(3, k.id, function() loop_cmd(4) end)
      end
    elseif n == 3 and alt then
      loop_cmd(2)
      hold_check(3, k.id, function() loop_cmd(3) end)
    end
  else
    local k = keyt[n]
    keyt[n] = nil
    if n == 2 and k and not k.alt and params:get("hold_mode") == 2 then set_hold(false) end
    if n == 3 and k and k.burst then loop_cmd(1) end
  end
end

-- ---------------------------------------------------------------- schermo
function redraw()
  screen.clear()
  screen.aa(0)
  screen.font_face(1)
  screen.font_size(8)
  local pi = params:get("preset")
  local a = (pi - 1) // 4 + 1
  screen.level(15)
  screen.move(0, 7)
  screen.text(params:string("preset"))
  local top = BANKS[a]
  if params:get("bypass") == 1 then top = "BYPASS"
  elseif params:get("looper_only") == 2 then top = "LOOP ONLY"
  elseif params:get("fx_reverse") == 1 then top = "REVERSE" end
  screen.level(top ~= BANKS[a] and 15 or 5)
  screen.move(127, 7)
  screen.text_right(top)

  -- tempo
  screen.level(8)
  screen.move(0, 17)
  local src = " " .. clock_tag() .. " "
  local tm = tempo_mode() and (tempo_knob and "TEMPO pot" or "TEMPO") or ("SUB " .. SUBS[subZone])
  screen.text(string.format("%.1f", bpm_now()) .. src .. tm)
  if now() < clip_until then
    screen.level(15)
    screen.move(127, 17)
    screen.text_right("CLIP")
  end

  -- pagina e valori
  local pg = PAGES[page]
  screen.move(0, 28)
  if now() < msg_until then
    screen.level(15)
    screen.text(msg)
  else
    screen.level(4)
    screen.text(page .. "/" .. #PAGES .. " " .. pg.name .. (alt and "   K1" or ""))
  end
  local ids = alt and pg.b or pg.a
  for i = 1, 2 do
    local id = ids[i]
    local y = 28 + 10 * i
    if id then
      screen.level(alt and 6 or 4)
      screen.move(0, y)
      screen.text("E" .. (i + 1) .. " " .. LABEL[id])
      screen.level(15)
      screen.move(127, y)
      screen.text_right(params:string(id))
    end
  end

  -- looper
  screen.level(3)
  screen.move(0, 52)
  screen.line(127, 52)
  screen.stroke()
  screen.level(lstate == 1 and 15 or 10)
  screen.move(0, 62)
  local s = (params:get("routing") == 1 and "AUX " or "INS ") .. (params:get("loop_pre") == 2 and "PRE " or "PST ")
    .. (LSTATE[lstate] or "----")
  if lstate > 0 then s = s .. string.format(" %.1fs", llen) end
  screen.text(s)
  screen.move(127, 62)
  screen.text_right((params:get("hold") == 1 and "H" or "-") .. (params:get("reverse") == 1 and "R" or "-"))
  screen.update()
end
