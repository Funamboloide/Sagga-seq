-- FIGO, tested without a norns: a fake norns (clock, params, screen, audio) and a model of softcut as its source
-- does it (softcut-lib, the one norns builds): six voices done in order in each block, a head that writes 8 samples
-- behind its position and a read that looks 2 samples past it, a crossfade of FADE at every jump and loop wrap (the
-- old head keeps playing where it was while it fades out; a jump asked during a fade waits for its end, at the place
-- asked then, and setting a loop point forgets it), rate and level slews of one pole (-60 dB at the slew time). The
-- test knows at every millisecond which moment of the input each voice plays, and whether that is on the tape yet.
--     texlua tools/norns/test_figo.lua        (Lua 5.3, as on norns; texlua comes with TeX Live)
local HERE = arg[0]:match("^(.*)/[^/]*$") or "."
local SCRIPT = arg[1] or (HERE .. "/figo/figo.lua")

local FAILS, CHECKS = {}, 0
local function check(cond, what)
  CHECKS = CHECKS + 1
  if not cond then
    FAILS[#FAILS + 1] = what
    print("  FAIL: " .. what)
  end
end

------------------------------------------------------------------------------------------------------------------
-- the world: virtual time, the scheduler, the tape

local W
local DT = 0.001                         -- one step of the model: 1 ms (a block of 48 samples)
local SR = 48000
local WOFF = 8 / SR                      -- softcut writes 8 samples behind its position
local LOOK = 2 / SR                      -- and the read at a position uses the samples up to 2 past it
local TAPE = 300                         -- FIGO's tape: 1 .. 301 s

local function fresh_world(bpm, seed)
  math.randomseed(seed or 1)
  W = {
    t = 0, bpm = bpm or 120, beat0 = 0, t_beat0 = 0,
    co = {}, next_id = 1,
    timed = {},                          -- {t=, fn=} callbacks (the phase poll)
    poll_delay = 0.002,                  -- the phase poll gets to Lua this late (FIGO guesses 5 ms)
    v = {}, buf = {{}, {}},
    monitor = {}, phase_cb = nil, poll = false,
    log = {},                            -- per ms, see step()
    jitter = 0.002,
    bad = 0, bad_first = nil, bad_what = nil,   -- ms where a voice you hear plays tape not recorded yet
    rec0 = nil,
  }
  for i = 1, 6 do
    W.v[i] = {enabled = 0, buffer = (i % 2) + 1, play = 0, rec = 0, rate = 1, rate_t = 1, rslew = 0,
              ls = (i - 1) * 2, le = (i - 1) * 2 + 1, loop = 1, phase = 0, level = 0, level_t = 0, lslew = 0.001,
              fade = 0.01, old = nil, prog = 1, queued = nil,
              rec_level = 0, pre = 0, quant = 1, last_q = nil, inp = {0, 0}, pan = 0}
  end
end

local function beats_at(t)
  return W.beat0 + (t - W.t_beat0) * W.bpm / 60
end

local function set_bpm(bpm)
  W.beat0 = beats_at(W.t)
  W.t_beat0 = W.t
  W.bpm = bpm
end

local function time_of_beat(b)
  return W.t_beat0 + (b - W.beat0) * 60 / W.bpm
end

-- the clock, as norns does it: a coroutine yields ('sync', q) or ('sleep', s)
clock = {transport = {}}
local function schedule(id, mode, x)
  local wake
  if mode == "sync" then
    local cb = beats_at(W.t)
    local nb = math.ceil((cb + 1e-7) / x) * x
    wake = time_of_beat(nb)
  else
    wake = W.t + x
  end
  W.co[id].wake = wake + math.random() * W.jitter
  W.co[id].mode = mode
end
local function resume(id)
  local c = W.co[id]
  if not c then return end
  local ok, mode, x = coroutine.resume(c.co)
  if not ok then error(mode .. "\n" .. debug.traceback(c.co)) end
  if coroutine.status(c.co) == "dead" then
    W.co[id] = nil
  else
    schedule(id, mode, x)
  end
end
clock.run = function(f, ...)
  local id = W.next_id
  W.next_id = id + 1
  local args = {...}
  W.co[id] = {co = coroutine.create(function() f(table.unpack(args)) end), wake = nil}
  resume(id)
  return id
end
clock.cancel = function(id) W.co[id] = nil end
-- SAGGA's START, as norns does it (matron's clock_midi and clock_scheduler): at the next tick the count of beats goes
-- back to 0, every clock.sync waiting resumes, and clock.transport.start is called
local function midi_start()
  W.beat0 = 0
  W.t_beat0 = W.t
  for _, c in pairs(W.co) do if c.mode == "sync" and c.wake then c.wake = W.t end end
  if clock.transport.start then clock.transport.start() end
end
clock.sleep = function(s) return coroutine.yield("sleep", s) end
clock.sync = function(q) return coroutine.yield("sync", q) end
clock.get_beats = function() return beats_at(W.t) end
clock.get_tempo = function() return W.bpm end
clock.get_beat_sec = function() return 60 / W.bpm end

util = {
  time = function() return W.t end,
  dbamp = function(db) return 10 ^ (db / 20) end,
  clamp = function(x, a, b) return math.min(b, math.max(a, x)) end,
}

controlspec = {new = function(min, max, warp, step, default, units)
  return {min = min, max = max, step = step, default = default}
end}

-- params: what FIGO uses
local P
local function fresh_params()
  P = {list = {}, by = {}}
  local function add(p) P.list[#P.list + 1] = p; P.by[p.id] = p end
  params = {
    add_separator = function(self, id) end,
    add_control = function(self, id, name, spec) add({id = id, kind = "control", spec = spec, v = spec.default}) end,
    add_option = function(self, id, name, opts, def) add({id = id, kind = "option", n = #opts, v = def}) end,
    add_trigger = function(self, id) add({id = id, kind = "trigger", v = 0}) end,
    set_action = function(self, id, fn) P.by[id].action = fn end,
    get = function(self, id) return P.by[id].v end,
    set = function(self, id, v)
      local p = P.by[id]
      if p.kind == "control" then v = math.min(p.spec.max, math.max(p.spec.min, v)) end
      if p.kind == "option" then v = math.min(p.n, math.max(1, v)) end
      p.v = v
      if p.action then p.action(v) end
    end,
    read = function(self) end,
    write = function(self) end,
    delta = function(self, id, d)
      local p = P.by[id]
      local step = (p.spec and p.spec.step and p.spec.step > 0) and p.spec.step or 1
      self:set(id, p.v + d * step)
    end,
  }
  add({id = "monitor_level", kind = "control", spec = {min = -60, max = 6, step = 0}, v = 0})
end

local DRAWN = {}
screen = setmetatable({}, {__index = function(_, k)
  return function(...) if k == "text" or k == "text_right" then DRAWN[#DRAWN + 1] = select(1, ...) end end
end})
audio = {
  level_monitor = function(x) W.monitor[#W.monitor + 1] = x end,
  level_adc_cut = function() end, level_eng_cut = function() end, level_tape_cut = function() end,
}

-- softcut, modelled
local SLICES = {}                        -- every loop region set on a voice (for the bounds check)
local function V(i) return W.v[i] end
local function cut(v, pos)               -- softcut's cutToPos: a crossfade from here to pos, or wait for the one on
  if v.old then v.queued = pos; return end
  v.old = {phase = v.phase}
  v.prog = 0
  v.phase = pos
end
softcut = {
  buffer_clear = function() W.buf = {{}, {}} end,
  enable = function(i, x) V(i).enabled = x end,
  buffer = function(i, b) V(i).buffer = b end,
  pan = function(i, x) V(i).pan = x end,
  loop = function(i, x) V(i).loop = x end,
  loop_start = function(i, x) V(i).ls = x; V(i).queued = nil; SLICES[#SLICES + 1] = {i, "s", x} end,
  loop_end = function(i, x) V(i).le = x; V(i).queued = nil; SLICES[#SLICES + 1] = {i, "e", x} end,
  position = function(i, x) cut(V(i), x) end,
  rate = function(i, x) V(i).rate_t = x end,
  fade_time = function(i, x) V(i).fade = x end,
  level_slew_time = function(i, x) V(i).lslew = x end,
  rate_slew_time = function(i, x) V(i).rslew = x end,
  rec = function(i, x) V(i).rec = x; if x == 1 and not W.rec0 then W.rec0 = W.t end end,
  rec_level = function(i, x) V(i).rec_level = x end,
  pre_level = function(i, x) V(i).pre = x end,
  level = function(i, x) V(i).level_t = x end,
  level_input_cut = function(ch, i, x) V(i).inp[ch] = x end,
  play = function(i, x) V(i).play = x end,
  voice_sync = function(dst, src, off) cut(V(dst), V(src).phase + off) end,
  phase_quant = function(i, q) V(i).quant = q end,
  event_phase = function(fn) W.phase_cb = fn end,
  poll_start_phase = function() W.poll = true end,
  poll_stop_phase = function() W.poll = false end,
}
for _, k in ipairs({"pre_filter_dry", "pre_filter_lp", "pre_filter_fc_mod", "post_filter_dry", "post_filter_lp",
                    "post_filter_hp", "post_filter_bp", "post_filter_br", "post_filter_fc", "post_filter_rq"}) do
  softcut[k] = function() end
end

local function cell(x) return math.floor(x / DT + 0.5) end

-- one pole, as softcut's LogRamp: -60 dB at time t
local function slew(x, target, t)
  if t <= 0 then return target end
  local y = target + (x - target) * math.exp(-6.9 * DT / t)
  if math.abs(y - target) < 1e-5 then y = target end
  return y
end

-- how long ago the record head of buffer b wrote position p (nil: not in this pass of the tape, or never)
local function age_at(b, p)
  for i = 1, 2 do
    local r = V(i)
    if r.rec == 1 and r.rec_level > 0 and r.buffer == b then
      local d = ((r.phase - WOFF) - p) % TAPE
      if d > 200 or d > W.t - (W.rec0 or W.t) then return nil end
      return d
    end
  end
  return nil
end
local function readable(b, p) return age_at(b, p + LOOK) ~= nil end

-- one millisecond of audio: the voices in order, like softcut's blocks
local function step()
  W.t = W.t + DT
  for i = 1, 6 do
    local v = V(i)
    if v.enabled == 1 and (v.play == 1 or v.rec == 1) then
      v.rate = slew(v.rate, v.rate_t, v.rslew)
      v.level = slew(v.level, v.level_t, v.lslew)
      if v.rec == 1 and v.rec_level > 0 then
        local src = (v.inp[1] > 0 and v.inp[2] > 0) and "LR" or ((v.inp[1] > 0) and "L" or "R")
        W.buf[v.buffer][cell(v.phase - WOFF)] = {W.t, src}
        if v.old then W.buf[v.buffer][cell(v.old.phase - WOFF)] = {W.t, src} end
      end
      if v.old then                        -- the old head goes on where it was, fading out
        v.old.phase = v.old.phase + v.rate * DT
        v.prog = v.prog + math.abs(v.rate) * DT / math.max(v.fade, 1e-4)
        if v.prog >= 1 then v.old = nil; v.prog = 1 end
      end
      v.phase = v.phase + v.rate * DT
      if v.loop == 1 and (v.phase > v.le or v.phase < v.ls) then
        -- softcut wraps to the sample; a step here is 48 of them: what went past the end goes on from the start
        -- (not when the head was outside the loop already, or while it fades: then softcut goes to the start)
        local fwd = v.rate >= 0
        local over = 0
        if not v.old then
          if fwd and v.phase > v.le then over = v.phase - v.le elseif not fwd and v.phase < v.ls then over = v.ls - v.phase end
          if over > math.abs(v.rate) * DT + 1e-9 then over = 0 end
        end
        cut(v, fwd and (v.ls + over) or (v.le - over))
      end
      if not v.old and v.queued then
        local q = v.queued
        v.queued = nil
        cut(v, q)
      end
    end
  end
  -- the phase poll: voice 1, quantized, delivered 2 ms later
  if W.poll and W.phase_cb then
    local v = V(1)
    local q = math.floor(v.phase / v.quant) * v.quant
    if q ~= v.last_q then
      v.last_q = q
      W.timed[#W.timed + 1] = {t = W.t + W.poll_delay, fn = function() W.phase_cb(1, q) end}
    end
  end
  -- what you hear must be on the tape: every head of A and B that sounds
  for i = 3, 6 do
    local v = V(i)
    if v.enabled == 1 and v.play == 1 and v.level > 0.01 then
      local wa = v.old and math.sin(v.prog * math.pi / 2) or 1
      if v.level * wa > 0.01 and not readable(v.buffer, v.phase) then
        W.bad = W.bad + 1; W.bad_first = W.bad_first or W.t; W.bad_what = W.bad_what or ("voice " .. i)
      end
      if v.old and v.level * math.sin((1 - v.prog) * math.pi / 2) > 0.01 and not readable(v.buffer, v.old.phase) then
        W.bad = W.bad + 1; W.bad_first = W.bad_first or W.t; W.bad_what = W.bad_what or ("voice " .. i .. ", fading")
      end
    end
  end
  local va, vb = V(3), V(5)
  local aa, ab = age_at(va.buffer, va.phase), age_at(vb.buffer, vb.phase)
  local c = W.buf[va.buffer][cell(va.phase - DT)]       -- (the channel: from a cell surely written)
  -- t, A plays the input of (time), A level, B input time, B level, A rate, A's channel, A age, B age
  W.log[#W.log + 1] = {W.t, aa and W.t - aa or nil, va.level, ab and W.t - ab or nil, vb.level, va.rate,
                       c and c[2] or nil, aa, ab}
end

local function run_until(t_end, every)
  while W.t < t_end do
    step()
    local i = 1
    while i <= #W.timed do
      if W.timed[i].t <= W.t then local e = table.remove(W.timed, i); e.fn() else i = i + 1 end
    end
    local due = {}                       -- (the due ones first: a coroutine may start others, and a table
    for id, c in pairs(W.co) do          -- must not grow while pairs walks it)
      if c.wake and c.wake <= W.t then due[#due + 1] = id end
    end
    table.sort(due)
    for _, id in ipairs(due) do
      local c = W.co[id]
      if c and c.wake and c.wake <= W.t then c.wake = nil; resume(id) end
    end
    if every then every() end
  end
end

-- start FIGO in a fresh world
local EVENTS, BEV
local function boot(bpm, seed, sets)
  fresh_world(bpm, seed)
  fresh_params()
  SLICES = {}
  FIGO = nil
  init, enc, key, redraw, cleanup = nil, nil, nil, nil, nil
  FIGO_pick, FIGO_pick_b, FIGO_pick_mem, FIGO_shuf_rev_ok = nil, nil, nil, nil
  dofile(SCRIPT)
  init()
  for k, x in pairs(sets or {}) do params:set(k, x) end
  EVENTS, BEV = {}, {}
  local last, lastb = nil, nil
  return function()                       -- per ms: note the events as they start and end (by coroutine)
    local S = FIGO
    if (S.ev_id and not S.ev) or (S.evb_id and not S.evb) then W.stale = (W.stale or 0) + 1 end
    local cur = S.ev and (S.ev_id or "REL") or nil
    if cur ~= last then
      if last and #EVENTS > 0 and not EVENTS[#EVENTS].t1 then EVENTS[#EVENTS].t1 = W.t end
      if cur then EVENTS[#EVENTS + 1] = {name = S.ev, label = S.last_ev, t0 = W.t, beat = beats_at(W.t), pb = S.beat} end
      last = cur
    end
    if cur and EVENTS[#EVENTS] then EVENTS[#EVENTS].label = S.last_ev end
    local curb = S.evb_id
    if curb ~= lastb then
      if lastb and #BEV > 0 and not BEV[#BEV].t1 then BEV[#BEV].t1 = W.t end
      if curb then BEV[#BEV + 1] = {t0 = W.t} end
      lastb = curb
    end
    if curb and BEV[#BEV] then BEV[#BEV].label = S.last_b end
  end
end

-- the log between two times
local function window(t0, t1)
  local out = {}
  for _, r in ipairs(W.log) do
    if r[1] >= t0 and r[1] <= t1 then out[#out + 1] = r end
  end
  return out
end

-- the dry, `lat` behind the head: what A plays is that old (the head writes 8 samples behind its position)
local function dry_age(lat) return lat - WOFF end
local function trailing_ok(rows, age, tol)
  tol = tol or 0.0001
  local bad, worst = 0, 0
  for _, r in ipairs(rows) do
    if not r[8] then bad = bad + 1
    else
      local e = math.abs(r[8] - age)
      if e > tol then bad = bad + 1 end
      if e > worst then worst = e end
    end
  end
  return bad == 0, worst, bad
end

local function tape_ok(what)
  check(W.bad == 0, string.format("%s: nothing you hear plays tape not recorded yet (%d ms, first at %.3f s, %s)",
    what, W.bad, W.bad_first or 0, W.bad_what or "-"))
  check(not W.stale, string.format("%s: no event's id left behind when it ended (%d ms)", what, W.stale or 0))
end

-- the part of x past the nearest multiple of m (-m/2 .. m/2)
local function off_grid(x, m)
  local k = math.floor(x / m + 0.5)
  return x - k * m, k
end

local DRY = dry_age(0.0005)

-- after each event the dry is back: 30 ms after its end, until the next one (or 300 ms)
local function dry_back_after_events()
  local bad = 0
  for i, e in ipairs(EVENTS) do
    if e.t1 then
      local nxt = EVENTS[i + 1] and EVENTS[i + 1].t0 or e.t1 + 0.3
      local t1 = math.min(e.t1 + 0.3, nxt - 0.005)
      if t1 > e.t1 + 0.03 and not trailing_ok(window(e.t1 + 0.03, t1), DRY) then bad = bad + 1 end
    end
  end
  return bad
end

------------------------------------------------------------------------------------------------------------------

print("the model of softcut: a jump during a crossfade waits, a loop point forgets it; the slews of one pole")
do
  fresh_world(120, 1)
  local v = V(3)
  v.enabled, v.play, v.fade, v.loop, v.ls, v.le, v.phase = 1, 1, 0.006, 1, 0, 100, 10
  softcut.position(3, 20)
  softcut.position(3, 30)
  check(v.phase == 20 and v.queued == 30, "the second jump waits for the first crossfade")
  for _ = 1, 7 do step() end
  check(v.phase >= 30 - 1e-9 and v.phase <= 30.002, string.format("then it is made, at the place asked (%.4f)", v.phase))
  softcut.position(3, 40)
  softcut.loop_start(3, 0)
  for _ = 1, 7 do step() end
  check(v.phase < 31, "a loop point set during the crossfade forgets the jump that waited")
  v.rslew, v.rate_t = 0.5, 2
  for _ = 1, 72 do step() end                  -- one time constant (0.5 / 6.9)
  check(math.abs(v.rate - (2 - math.exp(-1))) < 0.02, string.format("rate after one time constant: %.3f", v.rate))
end

print("FIGO at 0: the dry passes, half a millisecond late, nothing else")
do
  local per = boot(120, 1, {figo = 0, memoria = 0})
  run_until(40, per)
  local ok, worst, bad = trailing_ok(window(0.5, 40), DRY)
  check(ok, string.format("A plays the input %.2f ms after the head wrote it, always (worst %.3f ms off, %d ms wrong)",
    DRY * 1000, worst * 1000, bad))
  check(#EVENTS == 0, "no events at FIGO 0 (" .. #EVENTS .. ")")
  check(W.monitor[#W.monitor] == 0, "the norns monitor is off: the dry comes from softcut")
  local lv = true
  for _, r in ipairs(window(0.5, 40)) do if math.abs(r[3] - 1) > 1e-4 or r[5] > 0.001 then lv = false end end
  check(lv, "A at level 1, B silent")
  local st = true
  for _, r in ipairs(window(0.5, 40)) do if r[7] ~= "L" then st = false end end
  check(st, "the left voice plays the left input")
  tape_ok("FIGO 0")
  cleanup()
  check(math.abs(W.monitor[#W.monitor] - 1) < 1e-9, "cleanup gives the monitor back as LEVELS says (0 dB)")
end

local function run_mode(f, c, seed, secs, sets)
  local s = {figo = f, carattere = c, memoria = 0}
  for k, x in pairs(sets or {}) do s[k] = x end
  local per = boot(120, seed, s)
  run_until(secs, per)
  local count = {}
  for _, e in ipairs(EVENTS) do count[e.name] = (count[e.name] or 0) + 1 end
  return count
end

print("FIGO 100, all dub: dub events only, never two at once, never across a phrase, the dry back after each")
do
  local per = boot(120, 7, {figo = 100, carattere = 0, memoria = 0})
  run_until(200, per)
  local count, overlap = {}, false
  for i, e in ipairs(EVENTS) do
    count[e.name] = (count[e.name] or 0) + 1
    if i > 1 and EVENTS[i - 1].t1 and EVENTS[i - 1].t1 > e.t0 + 1e-6 then overlap = true end
  end
  local names = {}
  for k, n in pairs(count) do names[#names + 1] = k .. "=" .. n end
  table.sort(names)
  print("  events: " .. table.concat(names, " "))
  check(#EVENTS > 40, "plenty of events at 100 (" .. #EVENTS .. ")")
  check(not count.R32 and not count.SHUF, "the glitch ones stay out at dub 100%")
  check((count.REV or 0) > 0 and (count.R4 or 0) + (count.R8 or 0) > 0 and (count.HALF or 0) > 0, "reverse, repeats and half speed all come")
  check(not overlap, "never two events on A at once")
  tape_ok("dub")
  local across, early = 0, 0
  for _, e in ipairs(EVENTS) do
    if e.t1 then
      local b0 = math.floor(e.beat + 0.5)
      local b1 = beats_at(e.t1)
      if math.floor(b0 / 16) ~= math.floor((b1 - 0.02) / 16) then across = across + 1 end
      local lead = (b0 - e.beat) * 0.5          -- s before its beat (120 bpm)
      if math.abs(lead - 0.0075) > 0.0035 then early = early + 1 end
    end
  end
  check(across == 0, "no event crosses the end of a 16-beat phrase (" .. across .. ")")
  check(early == 0, "every event starts 7.5 ms before its beat: on the tape, 8 ms behind the head as before (" .. early .. " not)")
  local bad = dry_back_after_events()
  check(bad == 0, "after every event A is back behind the head, half a ms (" .. bad .. " not)")
  -- what each kind does to time
  local function slope(rows)
    local n, sx, sy, sxx, sxy = 0, 0, 0, 0, 0
    for _, r in ipairs(rows) do
      if r[2] then n = n + 1; sx = sx + r[1]; sy = sy + r[2]; sxx = sxx + r[1] ^ 2; sxy = sxy + r[1] * r[2] end
    end
    if n < 10 then return nil end
    return (n * sxy - sx * sy) / (n * sxx - sx * sx)
  end
  local seen = {}
  for _, e in ipairs(EVENTS) do
    if e.t1 and not seen[e.name] then
      local rows = window(e.t0 + 0.02, e.t1 - 0.02)
      if e.name == "REV" then
        local s = slope(rows)
        check(s and s < -0.3, string.format("REVERSE plays the input backwards (slope %.2f)", s or 0))
        seen.REV = true
      elseif e.name == "HALF" then
        local s = slope(rows)
        check(s and math.abs(s - 0.5) < 0.05, string.format("OTTAVA - plays at half speed (slope %.2f)", s or 0))
        seen.HALF = true
      end
    end
  end
  -- the repeats: every one long enough to repeat twice plays one slice only, from its beat on, in time
  local nrep, badrep = 0, {}
  for _, e in ipairs(EVENTS) do
    if (e.name == "R8" or e.name == "R4") and e.t1 then
      local s = (e.name == "R8") and 0.25 or 0.5
      if e.t1 - e.t0 >= 2 * s + 0.05 then
        local lo, hi, n, grid = 1e9, -1e9, 0, 0
        for _, r in ipairs(window(e.t0 + s + 0.03, e.t1 - 0.02)) do
          if r[2] then
            lo = math.min(lo, r[2]); hi = math.max(hi, r[2]); n = n + 1
            if math.abs(off_grid(r[8] - DRY, s)) > 0.0004 then grid = grid + 1 end
          end
        end
        nrep = nrep + 1
        if n < 50 or hi - lo > s + 0.012 or lo < e.t0 - 0.03 or grid > 0 then
          badrep[#badrep + 1] = string.format("%s span %.3f, %d ms off the grid", e.name, hi - lo, grid)
        end
      end
    end
  end
  seen.R = nrep > 0
  check(nrep > 3 and #badrep == 0, "every repeat loops one slice from its beat on, whole slices later than the dry (" .. nrep .. " checked; " .. table.concat(badrep, ", ") .. ")")
  check(seen.REV and seen.HALF and seen.R, "the shapes were all checked")
  -- the tape stop: slower and slower, quiet at the end
  for _, e in ipairs(EVENTS) do
    if e.name == "STOP" and e.t1 then
      local rows = window(e.t1 - 0.06, e.t1 - 0.01)
      local r = rows[#rows]
      check(r and r[6] < 0.35 and r[3] < 0.3, string.format("TAPE STOP: at its end the rate is %.2f and the level %.2f", r and r[6] or -1, r and r[3] or -1))
      break
    end
  end
end

print("FIGO 100, all glitch: the glitch ones come, no tape stop; the roll that rises never passes the head")
do
  local count = run_mode(100, 100, 3, 200)
  local names = {}
  for k, n in pairs(count) do names[#names + 1] = k .. "=" .. n end
  table.sort(names)
  print("  events: " .. table.concat(names, " "))
  check((count.SHUF or 0) > 0 and (count.R16 or 0) + (count.R32 or 0) > 0 and (count.GATE or 0) > 0, "shuffle, short repeats and the gate come")
  check(not count.STOP, "no tape stop at glitch 100%")
  check((count.ROLL or 0) > 0, "rolls come (" .. (count.ROLL or 0) .. ")")
  local rose = false
  for _, e in ipairs(EVENTS) do
    if e.name == "ROLL" and e.t1 then
      for _, r in ipairs(window(e.t0, e.t1)) do if r[6] > 1.3 then rose = true end end
    end
  end
  check(rose, "the roll's pitch rises at glitch 100%")
  tape_ok("glitch")
  -- shuffle plays only the last bar before it
  local okshuf, n = true, 0
  for _, e in ipairs(EVENTS) do
    if e.name == "SHUF" and e.t1 then
      n = n + 1
      for _, r in ipairs(window(e.t0 + 0.02, e.t1 - 0.02)) do
        if r[2] and (r[2] < e.t0 - 2.0 - 0.03 or r[2] > e.t0 + 0.01) then okshuf = false end
      end
    end
  end
  check(n > 0 and okshuf, "SHUFFLE plays sixteenths of the bar before it, nothing else (" .. n .. " checked)")
  -- the glitch again at a fast tempo and a slow one, and with the phase poll late (FIGO's guess ahead of the head,
  -- then behind it): the head is never passed
  for _, x in ipairs({{174, 0.002}, {90, 0.002}, {128, 0.0}, {128, 0.009}}) do
    local per = boot(x[1], 5, {figo = 100, carattere = 90, memoria = 60})
    W.poll_delay = x[2]
    run_until(150, per)
    tape_ok(string.format("%d bpm, the poll %d ms late", x[1], x[2] * 1000))
    local bad = dry_back_after_events()
    check(bad == 0, string.format("%d bpm, the poll %d ms late: the dry back after every event (%d not)", x[1], x[2] * 1000, bad))
  end
end

print("how often: more FIGO, more events; most at the end of the phrase, fewest on the ones")
do
  local counts = {}
  for _, f in ipairs({10, 30, 60, 100}) do
    local c = run_mode(f, 50, 11, 240)
    local n = 0
    for _, x in pairs(c) do n = n + x end
    counts[#counts + 1] = n
  end
  print("  events in 4 minutes at FIGO 10/30/60/100: " .. table.concat(counts, " / "))
  check(counts[1] < counts[2] and counts[2] < counts[3] and counts[3] < counts[4], "the count grows with FIGO")
  check(counts[1] <= 8, "at 10 almost nothing")
  -- where they start: the pick, many times
  local at = {}
  for b = 0, 15 do at[b] = 0 end
  math.randomseed(5)
  for _ = 1, 20000 do
    for b = 0, 15 do
      if FIGO_pick(b, 16, 0.5, 0.5) then at[b] = at[b] + 1 end
    end
  end
  check(at[15] > 3 * at[0] and at[14] > at[13] and at[3] > at[0], string.format("phrase end %d, beat 15 vs the one %d vs %d", at[14], at[15], at[0]))
  -- the length never runs past the phrase
  local past = 0
  for _ = 1, 20000 do
    local b = math.random(0, 15)
    local k, L = FIGO_pick(b, 16, 1, math.random(), math.random)
    if k and b + L > 16 then past = past + 1 end
  end
  check(past == 0, "no pick runs past the phrase")
end

print("the picks that keep the heads apart: MEMORIA at double only if it stays behind the head, SHUFFLE backwards only")
print("from what is on the tape")
do
  boot(120, 1, {})
  math.randomseed(3)
  local doubles, bad = 0, 0
  for _ = 1, 20000 do
    local L = ({2, 4, 8})[math.random(1, 3)]
    local beat = 0.2 + math.random() * 0.8
    local c = 0.8 + math.random() * 0.2
    local n, rate = FIGO_pick_mem(L, c, beat)
    if rate == 2 then
      doubles = doubles + 1
      -- B starts n bars behind the head (a few ms closer in aux) and gains a second a second for L beats
      if n * 4 * beat - L * beat < 0.05 then bad = bad + 1 end
    end
  end
  check(doubles > 500 and bad == 0, string.format("MEMORIA: %d at double, %d would get past the head", doubles, bad))
  local SAFE, revs, bad2 = 0.012, 0, 0
  for _ = 1, 50000 do
    local beat = 0.2 + math.random() * 0.8
    local sx, bar = beat / 4, 4 * beat
    local rt = (math.random() < 0.5) and 0 or math.random() * 0.04
    local lat = 0.0003 + math.random() * 0.005
    local e = (math.random() * 2 - 1) * SAFE      -- the phase poll's error
    local i, j = math.random(0, 7), math.random(0, 15)
    if FIGO_shuf_rev_ok(j, i, sx, bar, SAFE + rt - lat + 0.001) then
      revs = revs + 1
      -- where a backwards sixteenth starts (its end), from the head at the event's start: the bar before the dry
      -- at the mixer (rt - lat ahead of the head, give or take e); the head has moved i sixteenths by then
      if -bar + (j + 1) * sx + e + rt - lat > i * sx - 10 / 48000 then bad2 = bad2 + 1 end
    end
  end
  check(revs > 20000 and bad2 == 0, string.format("SHUFFLE: %d backwards allowed, %d of them not on the tape", revs, bad2))
end

print("MEMORIA: old bars come back under the dry, in time; the echo repeats and fades")
do
  local per = boot(120, 21, {figo = 0, memoria = 100, carattere = 20})
  run_until(120, per)
  local bar = 2.0
  local okmem, n_mem = 0, 0
  for _, e in ipairs(BEV) do
    if e.label and e.label:find("MEMORIA") and e.t1 then
      for _, r in ipairs(window(e.t0 + 0.05, e.t1)) do
        if r[9] and r[5] > 0.2 then
          local d, k = off_grid(r[9] - DRY, bar)
          if math.abs(d) < 0.004 and k >= 1 then okmem = okmem + 1 end
          n_mem = n_mem + 1
        end
      end
    end
  end
  check(n_mem > 1000, "B sounds for a while with MEMORIA 100 (" .. n_mem .. " ms)")
  check(okmem == n_mem, string.format("B plays whole bars back, in time with the dry (%d of %d ms)", okmem, n_mem))
  -- the echo: the half beat (dotted eighth with dub) after its start, over and over, quieter each time
  local neco, badeco = 0, 0
  for _, e in ipairs(BEV) do
    if e.label == "ECO" and e.t1 then
      neco = neco + 1
      local h = 0.375
      local lv0, lvlast = nil, nil
      for _, r in ipairs(window(e.t0 + h + 0.01, e.t1)) do
        if r[5] > 0.02 then
          if not r[4] or r[4] < e.t0 - 0.03 or r[4] > e.t0 + h + 0.01 then badeco = badeco + 1 end
          lv0 = lv0 or r[5]
          lvlast = r[5]
        end
      end
      if not lv0 or lvlast >= lv0 then badeco = badeco + 1 end
    end
  end
  check(neco > 0 and badeco == 0, "ECO repeats the slice after its start and fades (" .. neco .. " echoes, " .. badeco .. " wrong)")
  local heard, off = 0, 0
  for _, e in ipairs(BEV) do
    if e.label == "ECO" and e.t1 then
      for _, r in ipairs(window(e.t0 + 0.39, e.t1)) do
        if r[5] > 0.02 and r[9] then
          heard = heard + 1
          local d, k = off_grid(r[9] - DRY, 0.375)
          if math.abs(d) > 0.0004 or k < 1 then off = off + 1 end
        end
      end
    end
  end
  check(heard > 500 and off == 0, string.format("ECO: whole echoes after the dry, to the sample (%d ms, %d off)", heard, off))
  -- nothing on A: FIGO is at 0
  check(#EVENTS == 0, "MEMORIA alone leaves A alone")
  tape_ok("memoria")
end

print("HOLD (K2): the last beat loops on the next beat, then the dry again")
do
  local per = boot(120, 4, {figo = 0, memoria = 0})
  run_until(10.1, per)
  key(2, 1); key(2, 0)
  run_until(10.6, per)
  check(FIGO.hold == true, "holding from the next beat")
  local lo, hi = 1e9, -1e9
  for _, r in ipairs(window(10.6, 14)) do if r[2] then lo = math.min(lo, r[2]); hi = math.max(hi, r[2]) end end
  check(hi - lo <= 0.5 + 0.012 and lo >= 10.5 - 0.5 - 0.03 and hi <= 10.5 + 0.01, string.format("the beat before 10.5 s loops (%.3f .. %.3f)", lo, hi))
  key(2, 1); key(2, 0)
  run_until(15.6, per)
  check(FIGO.hold == false, "HOLD off")
  check(trailing_ok(window(15.1, 15.6), DRY), "the dry is back on the next beat")
  -- HOLD with FIGO: the held beat varies by itself
  params:set("figo", 100)
  key(2, 1); key(2, 0)
  run_until(30, per)
  check(FIGO.hold, "holding again")
  local slices = 0
  for _, s in ipairs(SLICES) do if s[1] == 3 and s[2] == "e" then slices = slices + 1 end end
  check(slices > 6, "with FIGO the held beat changes by itself (" .. slices .. " loop changes)")
  check(#EVENTS == 0, "no events while holding")
  tape_ok("hold")
end

print("PULITO (K3): out with a tape stop on the next beat, then nothing; K3 again: back")
do
  local per = boot(120, 9, {figo = 100, carattere = 0, memoria = 60})
  run_until(20, per)
  key(3, 1); key(3, 0)
  local n0 = #EVENTS
  run_until(23, per)
  check(FIGO.on == false and EVENTS[#EVENTS] and EVENTS[#EVENTS].label == "TAPE STOP", "the way out is a tape stop (dub)")
  local nrel = #EVENTS
  run_until(60, per)
  check(#EVENTS == nrel, "no events while PULITO")
  check(trailing_ok(window(24, 60), DRY), "only the dry while PULITO")
  local bsil = true
  for _, r in ipairs(window(23.5, 60)) do if r[5] > 0.01 then bsil = false end end
  check(bsil, "the memory is quiet too")
  key(3, 1); key(3, 0)
  run_until(120, per)
  check(FIGO.on and #EVENTS > nrel + 5, "K3 again: the events are back")
  tape_ok("pulito")
end

print("the knobs, the menus, a tempo change, mono, the long run past the end of the tape")
do
  local per = boot(120, 2, {figo = 40, carattere = 50, memoria = 40})
  enc(2, 5); enc(3, -10); enc(1, 3)
  check(params:get("figo") == 45 and params:get("carattere") == 40 and params:get("memoria") == 43, "E2 FIGO, E3 CARATTERE, E1 MEMORIA")
  params:set("ingresso", 2)
  check(W.v[2].inp[1] == 1 and W.v[2].inp[2] == 0, "mono: the right voice records the left input")
  params:set("ingresso", 1)
  check(W.v[2].inp[1] == 0 and W.v[2].inp[2] == 1, "stereo again")
  run_until(30, per)
  set_bpm(128)
  run_until(60, per)
  params:set("frase", 1)
  run_until(90, per)
  params:set("frase", 3)
  run_until(120, per)
  params:set("latenza_ms", 15)
  params:set("figo", 0)
  params:set("memoria", 0)
  run_until(140, per)
  check(trailing_ok(window(136, 140), dry_age(0.015)), "a new latency: the dry 15 ms behind")
  params:set("latenza_ms", 0.5)
  params:set("figo", 70)
  params:set("memoria", 50)
  -- past the end of the 300 s tape
  run_until(330, per)
  local bad = 0
  for _, s in ipairs(SLICES) do
    if s[3] < 1 - 1e-9 or s[3] > 301 + 1e-9 then bad = bad + 1 end
  end
  check(bad == 0, "every loop point inside the tape (" .. bad .. " out)")
  local pairs_ok = true
  for i = 3, 6 do if W.v[i].ls >= W.v[i].le then pairs_ok = false end end
  check(pairs_ok, "loop start before loop end on every voice")
  params:set("figo", 0)
  params:set("memoria", 0)
  run_until(336, per)
  check(trailing_ok(window(334, 336), DRY), "after the tape wrapped, the dry is still right behind the head")
  tape_ok("the long run")
  -- every screen drawn so far without an error; once more in each state
  DRAWN = {}
  redraw()
  FIGO.on = false; redraw(); FIGO.on = true
  FIGO.hold = true; redraw(); FIGO.hold = false
  local joined = table.concat(DRAWN, "|")
  check(joined:find("FIGO") and joined:find("PULITO") and joined:find("HOLD") and joined:find("BPM"), "the screen: FIGO, the states, the tempo")
end

print("START from SAGGA in the middle of an event: norns' beats go back to 0, FIGO goes on (insert and aux)")
do
  for _, routing in ipairs({1, 2}) do
    local per = boot(120, 7, {figo = 100, carattere = 50, memoria = 60, routing = routing})
    run_until(40, per)
    local guard = 0
    while not (FIGO.ev and FIGO.ev_id) and guard < 20000 do run_until(W.t + 0.001, per); guard = guard + 1 end
    local t_start, was = W.t, FIGO.ev
    run_until(W.t + 0.05, per)                       -- (well inside it)
    t_start = W.t
    midi_start()
    run_until(t_start + 20, per)
    local long, after = 0, 0
    for _, e in ipairs(EVENTS) do
      if (e.t1 or W.t) > t_start - 1.5 then
        if (e.t1 or W.t) - e.t0 > 2 * 0.5 + 0.1 then long = long + 1 end
        if e.t0 > t_start + 0.5 then after = after + 1 end
      end
    end
    check(long == 0 and after > 5, string.format("routing %d, START during %s: no event outlasts its 2 beats (%d), new ones come (%d)",
      routing, tostring(was), long, after))
    -- and they are on the new count's beats: each starts its lead before one (7.5 ms; aux 18.5)
    local lead, off = (routing == 2) and 0.0185 or 0.0075, 0
    for _, e in ipairs(EVENTS) do
      if e.t0 > t_start + 0.5 then
        local b = beats_at(e.t0)
        local before = (math.ceil(b) - b) * 0.5
        if math.abs(before - lead) > 0.0035 then off = off + 1 end
      end
    end
    check(off == 0, string.format("routing %d: after START every event %.1f ms before a beat of the new count (%d not)",
      routing, lead * 1000, off))
    tape_ok("START, routing " .. routing)
  end
end

------------------------------------------------------------------------------------------------------------------
-- aux: FIGO on a bus. The mixer's dry gets to norns RT after it plays (half the way), what norns plays gets back
-- the rest of RT later; FIGO is told RT (anticipo). What A plays, heard at the mixer, should land on the grid of the
-- dry there: (how old it is on the tape) + 1 sample (softcut's write) + RT = whole slices

local RT = 0.011
local function at_mixer(age) return age + 1 / SR + RT end

print("aux: FIGO 0 is silence on the return; the dry never comes out of A")
do
  local per = boot(120, 1, {figo = 0, memoria = 0, routing = 2})
  run_until(40, per)
  local loud = 0
  for _, r in ipairs(window(0.3, 40)) do if r[3] > 0.001 or r[5] > 0.001 then loud = loud + 1 end end
  check(loud == 0, "A and B quiet the whole time (" .. loud .. " ms not)")
  check(W.monitor[#W.monitor] == 0, "the norns monitor off: the dry is on the mixer")
  DRAWN = {}
  redraw()
  check(table.concat(DRAWN, "|"):find("AUX"), "the screen says AUX")
end

print("aux, FIGO 100 dub: the repeats land on the grid at the mixer; nothing plays the dry; no gate, no empty repeats")
do
  local per = boot(120, 7, {figo = 100, carattere = 0, memoria = 0, routing = 2})
  run_until(200, per)
  local count = {}
  for _, e in ipairs(EVENTS) do count[e.name] = (count[e.name] or 0) + 1 end
  local names = {}
  for k, n in pairs(count) do names[#names + 1] = k .. "=" .. n end
  table.sort(names)
  print("  events: " .. table.concat(names, " "))
  check(#EVENTS > 30, "plenty of events (" .. #EVENTS .. ")")
  check(not count.GATE, "no GATE on a bus")
  tape_ok("aux dub")
  -- A heard only inside events, and never a copy of the dry (at speed, a few ms after the mixer: a flam)
  local outside, dry = 0, 0
  local function in_event(t)
    for _, e in ipairs(EVENTS) do if e.t1 and t >= e.t0 and t <= e.t1 + 0.012 then return true end end
    return false
  end
  for _, r in ipairs(W.log) do
    if r[3] > 0.02 then
      if not in_event(r[1]) then outside = outside + 1 end
      if r[8] and math.abs(r[6] - 1) < 0.01 and at_mixer(r[8]) < 0.03 then dry = dry + 1 end
    end
  end
  check(outside == 0, "A is heard only during an event (" .. outside .. " ms not)")
  check(dry == 0, "A never plays a copy of what the mixer has just played (" .. dry .. " ms)")
  -- the repeats: at the mixer, whole slices after the dry played them
  local nrep, heard, off, worst = 0, 0, 0, 0
  for _, e in ipairs(EVENTS) do
    if (e.name == "R4" or e.name == "R8") and e.t1 then
      nrep = nrep + 1
      local s = (e.name == "R8") and 0.25 or 0.5
      for _, r in ipairs(window(e.t0 + 0.006, e.t1)) do      -- (the event before may be fading out still)
        if r[3] > 0.02 and r[8] then
          heard = heard + 1
          local d, k = off_grid(at_mixer(r[8]), s)
          if math.abs(d) > 0.0006 or k < 1 then off = off + 1 end
          worst = math.max(worst, math.abs(d))
        end
      end
    end
  end
  check(nrep > 3 and heard > 1000, string.format("repeats heard (%d events, %d ms)", nrep, heard))
  check(off == 0, string.format("every ms of them whole slices after the dry, at the mixer (%d off, worst %.2f ms)", off, worst * 1000))
  -- the first slice is not played (it is the dry): A comes in a slice after the event starts
  local early = 0
  for _, e in ipairs(EVENTS) do
    if (e.name == "R4" or e.name == "R8") and e.t1 then
      local s = (e.name == "R8") and 0.25 or 0.5
      for _, r in ipairs(window(e.t0 + 0.006, e.t0 + s - 0.006)) do if r[3] > 0.02 then early = early + 1 end end
    end
  end
  check(early == 0, "nothing in the first slice (" .. early .. " ms)")
  local empty = 0
  for _ = 1, 5000 do
    local b = math.random(0, 15)
    local k, L = FIGO_pick(b, 16, 1, math.random(), math.random)
    if k and (k == "GATE" or (k:sub(1, 1) == "R" and k ~= "REV" and k ~= "ROLL" and L < 2 * ({R4 = 1, R8 = 0.5, R16 = 0.25, R32 = 0.125})[k])) then
      empty = empty + 1
    end
  end
  check(empty == 0, "the pick: no gate, no repeat as long as its slice (" .. empty .. ")")
end

print("aux, FIGO 100 glitch: rolls and short repeats on the grid, shuffles, the rising roll; nothing unrecorded")
do
  local per = boot(120, 3, {figo = 100, carattere = 100, memoria = 0, routing = 2})
  run_until(200, per)
  local count = {}
  for _, e in ipairs(EVENTS) do count[e.name] = (count[e.name] or 0) + 1 end
  local names = {}
  for k, n in pairs(count) do names[#names + 1] = k .. "=" .. n end
  table.sort(names)
  print("  events: " .. table.concat(names, " "))
  check((count.ROLL or 0) > 0 and (count.SHUF or 0) > 0 and (count.R16 or 0) + (count.R32 or 0) > 0, "rolls, shuffles, short repeats")
  tape_ok("aux glitch")
  local heard, off, worst = 0, 0, 0
  for _, e in ipairs(EVENTS) do
    local s = ({R16 = 0.125, R32 = 0.0625, ROLL = 0.0625})[e.name]
    if s and e.t1 then
      for _, r in ipairs(window(e.t0 + 0.006, e.t1)) do
        if r[3] > 0.02 and r[8] and (e.name ~= "ROLL" or r[6] < 1.001) then
          heard = heard + 1
          local d = off_grid(at_mixer(r[8]), s)
          local tol = (e.name == "ROLL") and 0.0035 or 0.0006
          if math.abs(d) > tol then off = off + 1 end
          worst = math.max(worst, math.abs(d))
        end
      end
    end
  end
  check(heard > 500 and off == 0, string.format("short repeats and rolls on the grid at the mixer (%d ms, %d off, worst %.2f ms)", heard, off, worst * 1000))
  for _, x in ipairs({{174, 0.002, 11}, {128, 0.0, 11}, {128, 0.009, 11}, {174, 0.002, 35}, {90, 0.002, 0}}) do
    local per2 = boot(x[1], 5, {figo = 100, carattere = 70, memoria = 60, routing = 2, anticipo = x[3]})
    W.poll_delay = x[2]
    run_until(150, per2)
    tape_ok(string.format("aux %d bpm, the poll %d ms late, anticipo %d ms", x[1], x[2] * 1000, x[3]))
  end
end

print("aux: MEMORIA in time at the mixer, HOLD heard and in time, the switch back to insert brings the dry")
do
  local per = boot(120, 21, {figo = 0, memoria = 100, carattere = 20, routing = 2})
  run_until(120, per)
  local okmem, n_mem = 0, 0
  for _, e in ipairs(BEV) do
    if e.label and e.label:find("MEMORIA") and e.t1 then
      for _, r in ipairs(window(e.t0 + 0.05, e.t1)) do
        if r[9] and r[5] > 0.2 then
          local d, k = off_grid(at_mixer(r[9]), 2.0)
          if math.abs(d) < 0.004 and k >= 1 then okmem = okmem + 1 end
          n_mem = n_mem + 1
        end
      end
    end
  end
  check(n_mem > 1000 and okmem == n_mem, string.format("B: whole bars after the dry at the mixer (%d of %d ms)", okmem, n_mem))
  tape_ok("aux memoria")
  local neco, heard, off = 0, 0, 0
  for _, e in ipairs(BEV) do
    if e.label == "ECO" and e.t1 then
      neco = neco + 1
      for _, r in ipairs(window(e.t0 + 0.39, e.t1)) do
        if r[5] > 0.02 and r[9] then
          heard = heard + 1
          local d, k = off_grid(at_mixer(r[9]), 0.375)
          if math.abs(d) > 0.0006 or k < 1 then off = off + 1 end
        end
      end
    end
  end
  check(neco > 0 and heard > 500 and off == 0, string.format("ECO: whole echoes after the dry at the mixer (%d echoes, %d ms, %d off)", neco, heard, off))
  params:set("memoria", 0)
  run_until(130.1, per)
  key(2, 1); key(2, 0)
  run_until(131, per)
  local held, off = 0, 0
  run_until(134, per)
  for _, r in ipairs(window(131, 134)) do
    if r[3] > 0.02 and r[8] then
      held = held + 1
      if math.abs(off_grid(at_mixer(r[8]), 0.5)) > 0.0035 then off = off + 1 end
    end
  end
  check(FIGO.hold and held > 2000 and off == 0, string.format("HOLD: the beat heard, a beat later at the mixer (%d ms, %d off)", held, off))
  key(2, 1); key(2, 0)
  run_until(136, per)
  local quiet = true
  for _, r in ipairs(window(135.5, 136)) do if r[3] > 0.001 then quiet = false end end
  check(not FIGO.hold and quiet, "HOLD off: quiet again")
  params:set("routing", 1)
  run_until(140, per)
  check(trailing_ok(window(138, 140), DRY) and math.abs(W.log[#W.log][3] - 1) < 1e-3, "routing insert: the dry is back")
  params:set("figo", 100)
  run_until(150, per)
  params:set("routing", 2)
  run_until(160, per)
  tape_ok("the switches")
  local loud = 0
  for _, r in ipairs(window(150.2, 160)) do
    if r[3] > 0.02 and r[8] and math.abs(r[6] - 1) < 0.01 and at_mixer(r[8]) < 0.03 then loud = loud + 1 end
  end
  check(loud == 0, "aux again: no copy of the dry (" .. loud .. " ms)")
end

print(string.format("figo: %d checks, %d failures", CHECKS, #FAILS))
os.exit(#FAILS == 0 and 0 or 1)
