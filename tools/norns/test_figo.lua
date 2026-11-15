-- FIGO, tested without a norns: a fake norns (clock, params, screen, audio) and a small model of softcut (the six
-- voices, their loops, rates, slews and jumps; the tape remembers WHEN each cell was recorded), so the test knows,
-- at every millisecond, which moment of the input the listener hears.
--     texlua tools/norns/test_figo.lua        (Lua 5.3, as on norns; texlua comes with TeX Live)
local HERE = arg[0]:match("^(.*)/[^/]*$") or "."
local SCRIPT = HERE .. "/figo/figo.lua"

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
local DT = 0.001                         -- one step of the model: 1 ms
local BUFN = 2 ^ 24 / 48000              -- softcut's buffer, seconds

local function fresh_world(bpm, seed)
  math.randomseed(seed or 1)
  W = {
    t = 0, bpm = bpm or 120, beat0 = 0, t_beat0 = 0,
    co = {}, next_id = 1,
    timed = {},                          -- {t=, fn=} callbacks (the phase poll)
    v = {}, buf = {{}, {}},
    monitor = {}, phase_cb = nil, poll = false,
    log = {},                            -- per ms: {t, a_src, a_lv, b_src, b_lv}
    jitter = 0.002,
  }
  for i = 1, 6 do
    W.v[i] = {enabled = 0, buffer = (i % 2) + 1, play = 0, rec = 0, rate = 1, rate_t = 1, rslew = 0.001, rslew_v = 0,
              ls = (i - 1) * 2, le = (i - 1) * 2 + 1, loop = 1, phase = 0, level = 0, level_t = 0, lslew = 0.001,
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
local function rset(i, x)
  local v = V(i)
  v.rate_t = x
  if v.rslew <= 0.0011 then v.rate = x; v.rslew_v = 0 else v.rslew_v = math.abs(x - v.rate) / v.rslew end
end
softcut = {
  buffer_clear = function() W.buf = {{}, {}} end,
  enable = function(i, x) V(i).enabled = x end,
  buffer = function(i, b) V(i).buffer = b end,
  pan = function(i, x) V(i).pan = x end,
  loop = function(i, x) V(i).loop = x end,
  loop_start = function(i, x) V(i).ls = x; SLICES[#SLICES + 1] = {i, "s", x} end,
  loop_end = function(i, x) V(i).le = x; SLICES[#SLICES + 1] = {i, "e", x} end,
  position = function(i, x) V(i).phase = x end,
  rate = rset,
  fade_time = function() end,
  level_slew_time = function(i, x) V(i).lslew = x end,
  rate_slew_time = function(i, x) V(i).rslew = x end,
  rec = function(i, x) V(i).rec = x end,
  rec_level = function(i, x) V(i).rec_level = x end,
  pre_level = function(i, x) V(i).pre = x end,
  level = function(i, x) V(i).level_t = x end,
  level_input_cut = function(ch, i, x) V(i).inp[ch] = x end,
  play = function(i, x) V(i).play = x end,
  voice_sync = function(dst, src, off) V(dst).phase = V(src).phase + off end,
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

-- one millisecond of audio
local function step()
  W.t = W.t + DT
  for i = 1, 6 do
    local v = V(i)
    if v.enabled == 1 and (v.play == 1 or v.rec == 1) then
      if v.rate ~= v.rate_t then
        local d = v.rslew_v * DT
        if v.rslew_v <= 0 or math.abs(v.rate_t - v.rate) <= d then v.rate = v.rate_t
        elseif v.rate_t > v.rate then v.rate = v.rate + d else v.rate = v.rate - d end
      end
      if v.level ~= v.level_t then
        local d = DT / math.max(v.lslew, 0.001)
        if math.abs(v.level_t - v.level) <= d then v.level = v.level_t
        elseif v.level_t > v.level then v.level = v.level + d else v.level = v.level - d end
      end
      if v.rec == 1 and v.rec_level > 0 then
        local src = (v.inp[1] > 0 and v.inp[2] > 0) and "LR" or ((v.inp[1] > 0) and "L" or "R")
        W.buf[v.buffer][cell(v.phase)] = {W.t, src}
      end
      local p = v.phase + v.rate * DT
      if v.loop == 1 and (p > v.le or p < v.ls) then
        p = (v.rate >= 0) and v.ls or v.le
      end
      v.phase = p
    end
  end
  -- the phase poll: voice 1, quantized, delivered 2 ms later
  if W.poll and W.phase_cb then
    local v = V(1)
    local q = math.floor(v.phase / v.quant) * v.quant
    if q ~= v.last_q then
      v.last_q = q
      W.timed[#W.timed + 1] = {t = W.t + 0.002, fn = function() W.phase_cb(1, q) end}
    end
  end
  local function src(i)
    local c = W.buf[V(i).buffer][cell(V(i).phase)]
    return c and c[1] or nil, c and c[2] or nil
  end
  local a, aw = src(3)
  local b = src(5)
  W.log[#W.log + 1] = {W.t, a, V(3).level, b, V(5).level, V(3).rate, aw}
end

local function run_until(t_end, every)
  while W.t < t_end do
    step()
    local i = 1
    while i <= #W.timed do
      if W.timed[i].t <= W.t then local e = table.remove(W.timed, i); e.fn() else i = i + 1 end
    end
    for id, c in pairs(W.co) do
      if c.wake and c.wake <= W.t then c.wake = nil; resume(id) end
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
  FIGO_pick, FIGO_pick_b = nil, nil
  dofile(SCRIPT)
  init()
  for k, x in pairs(sets or {}) do params:set(k, x) end
  EVENTS, BEV = {}, {}
  local last, lastb = nil, nil
  return function()                       -- per ms: note the events as they start and end (by coroutine)
    local S = FIGO
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

local function trailing_ok(rows, lat, tol)
  local bad, worst = 0, 0
  for _, r in ipairs(rows) do
    if not r[2] then bad = bad + 1
    else
      local e = math.abs((r[1] - r[2]) - lat)
      if e > tol then bad = bad + 1 end
      if e > worst then worst = e end
    end
  end
  return bad == 0, worst, bad
end

------------------------------------------------------------------------------------------------------------------

print("FIGO at 0: the dry passes, a few ms late, nothing else")
do
  local per = boot(120, 1, {figo = 0, memoria = 0})
  run_until(40, per)
  local ok, worst, bad = trailing_ok(window(0.5, 40), 0.008, 0.0035)
  check(ok, string.format("A plays the input %d ms behind, always (worst %.1f ms off, %d ms wrong)", 8, worst * 1000, bad))
  check(#EVENTS == 0, "no events at FIGO 0 (" .. #EVENTS .. ")")
  check(W.monitor[#W.monitor] == 0, "the norns monitor is off: the dry comes from softcut")
  local lv = true
  for _, r in ipairs(window(0.5, 40)) do if math.abs(r[3] - 1) > 1e-6 or r[5] > 0 then lv = false end end
  check(lv, "A at level 1, B silent")
  local st = true
  for _, r in ipairs(window(0.5, 40)) do if r[7] ~= "L" then st = false end end
  check(st, "the left voice plays the left input")
  cleanup()
  check(math.abs(W.monitor[#W.monitor] - 1) < 1e-9, "cleanup gives the monitor back as LEVELS says (0 dB)")
end

local function run_mode(f, c, seed, secs)
  local per = boot(120, seed, {figo = f, carattere = c, memoria = 0})
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
  local across = 0
  for _, e in ipairs(EVENTS) do
    if e.t1 then
      local b0 = math.floor(e.beat + 0.5)
      local b1 = beats_at(e.t1)
      if math.floor(b0 / 16) ~= math.floor((b1 - 0.02) / 16) then across = across + 1 end
    end
  end
  check(across == 0, "no event crosses the end of a 16-beat phrase (" .. across .. ")")
  -- after each event the dry is back: 30 ms after its end, until the next one
  local bad = 0
  for i, e in ipairs(EVENTS) do
    if e.t1 then
      local nxt = EVENTS[i + 1] and EVENTS[i + 1].t0 or e.t1 + 0.3
      local t1 = math.min(e.t1 + 0.3, nxt - 0.005)
      if t1 > e.t1 + 0.03 then
        local ok = trailing_ok(window(e.t1 + 0.03, t1), 0.008, 0.0035)
        if not ok then bad = bad + 1 end
      end
    end
  end
  check(bad == 0, "after every event A is back behind the head (" .. bad .. " not)")
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
  -- the repeats: every one long enough to repeat twice plays one slice only, from its beat on
  local nrep, badrep = 0, {}
  for _, e in ipairs(EVENTS) do
    if (e.name == "R8" or e.name == "R4") and e.t1 then
      local s = (e.name == "R8") and 0.25 or 0.5
      if e.t1 - e.t0 >= 2 * s + 0.05 then
        local lo, hi, n = 1e9, -1e9, 0
        for _, r in ipairs(window(e.t0 + s + 0.02, e.t1 - 0.02)) do
          if r[2] then lo = math.min(lo, r[2]); hi = math.max(hi, r[2]); n = n + 1 end
        end
        nrep = nrep + 1
        if n < 50 or hi - lo > s + 0.012 or lo < e.t0 - 0.03 then
          badrep[#badrep + 1] = string.format("%s span %.3f", e.name, hi - lo)
        end
      end
    end
  end
  seen.R = nrep > 0
  check(nrep > 3 and #badrep == 0, "every repeat loops one slice from its beat on (" .. nrep .. " checked; " .. table.concat(badrep, ", ") .. ")")
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

print("FIGO 100, all glitch: the glitch ones come, no tape stop")
do
  local count = run_mode(100, 100, 3, 200)
  local names = {}
  for k, n in pairs(count) do names[#names + 1] = k .. "=" .. n end
  table.sort(names)
  print("  events: " .. table.concat(names, " "))
  check((count.SHUF or 0) > 0 and (count.R16 or 0) + (count.R32 or 0) > 0 and (count.GATE or 0) > 0, "shuffle, short repeats and the gate come")
  check(not count.STOP, "no tape stop at glitch 100%")
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

print("MEMORIA: old bars come back under the dry, in time; the echo repeats and fades")
do
  local per = boot(120, 21, {figo = 0, memoria = 100, carattere = 20})
  run_until(120, per)
  local bar = 2.0
  local okmem, n_mem, n_eco = 0, 0, 0
  for _, r in ipairs(window(10, 120)) do
    if r[4] and r[5] > 0.2 then
      local back = (r[1] - r[4]) - 0.008
      local k = back / bar
      if math.abs(k - math.floor(k + 0.5)) < 0.01 and math.floor(k + 0.5) >= 1 then okmem = okmem + 1 end
      n_mem = n_mem + 1
    end
  end
  check(n_mem > 1000, "B sounds for a while with MEMORIA 100 (" .. n_mem .. " ms)")
  check(okmem > 0.5 * n_mem, string.format("B plays whole bars back, in time (%d of %d ms)", okmem, n_mem))
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
  -- nothing on A: FIGO is at 0
  check(#EVENTS == 0, "MEMORIA alone leaves A alone")
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
  check(trailing_ok(window(15.1, 15.6), 0.008, 0.0035), "the dry is back on the next beat")
  -- HOLD with FIGO: the held beat varies by itself
  params:set("figo", 100)
  key(2, 1); key(2, 0)
  run_until(30, per)
  check(FIGO.hold, "holding again")
  local slices = 0
  for _, s in ipairs(SLICES) do if s[1] == 3 and s[2] == "e" then slices = slices + 1 end end
  check(slices > 6, "with FIGO the held beat changes by itself (" .. slices .. " loop changes)")
  check(#EVENTS == 0, "no events while holding")
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
  check(trailing_ok(window(24, 60), 0.008, 0.0035), "only the dry while PULITO")
  local bsil = true
  for _, r in ipairs(window(23.5, 60)) do if r[5] > 0.01 then bsil = false end end
  check(bsil, "the memory is quiet too")
  key(3, 1); key(3, 0)
  run_until(120, per)
  check(FIGO.on and #EVENTS > nrel + 5, "K3 again: the events are back")
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
  params:set("latenza", 15)
  params:set("figo", 0)
  params:set("memoria", 0)
  run_until(140, per)
  check(trailing_ok(window(136, 140), 0.015, 0.0035), "a new latency: the dry 15 ms behind")
  params:set("latenza", 8)
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
  check(trailing_ok(window(334, 336), 0.008, 0.0035), "after the tape wrapped, the dry is still right behind the head")
  -- every screen drawn so far without an error; once more in each state
  DRAWN = {}
  redraw()
  FIGO.on = false; redraw(); FIGO.on = true
  FIGO.hold = true; redraw(); FIGO.hold = false
  local joined = table.concat(DRAWN, "|")
  check(joined:find("FIGO") and joined:find("PULITO") and joined:find("HOLD") and joined:find("BPM"), "the screen: FIGO, the states, the tempo")
end

print(string.format("figo: %d checks, %d failures", CHECKS, #FAILS))
os.exit(#FAILS == 0 and 0 or 1)
