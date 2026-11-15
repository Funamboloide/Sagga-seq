-- FIGO
-- rende figo il noioso
-- v0.1 @ SAGGA
--
-- il loop entra, la macchina
-- lo varia da sola, a tempo:
-- tu giri una manopola.
--
-- E1 MEMORIA  E2 FIGO
-- E3 CARATTERE (dub..glitch)
-- K2 HOLD l'ultimo battito
-- K3 PULITO / di nuovo VIA
--
-- clock: PARAMETERS > CLOCK
-- source = midi (SAGGA)

-- Ispirato a Red Panda Tensor (una manopola dal pulito al rimescolato), Chase Bliss Habit (la memoria che
-- torna), Ableton Beat Repeat (ripetizioni con una probabilita') e alle Release FX del Pioneer RMX-1000.
-- Solo softcut: niente engine, gira anche su un Pi 3B+.
--
-- Il suono: le voci 1-2 registrano l'ingresso (L, R) di continuo in un nastro di 300 secondi. Le voci 3-4 (A)
-- sono quello che senti: di solito leggono il nastro appena dietro la testina (LAT ms, il "dry"), e un evento
-- le sposta (ripete un pezzo, lo rovescia, lo rallenta, lo rimescola) e poi le rimette dietro la testina. Le
-- voci 5-6 (B) sono la MEMORIA: una battuta di qualche battuta fa che torna sotto, filtrata, o un'eco lanciata.
-- Il monitor di norns resta a zero mentre FIGO gira: il dry passa da A.

local BUF0, BUF1 = 1, 301            -- the tape region, seconds (wraps once every five minutes)
local REC_L, REC_R, A_L, A_R, B_L, B_R = 1, 2, 3, 4, 5, 6
local FADE = 0.006                   -- crossfade of every jump and loop

local S = {
  on = true,          -- false: PULITO (A behind the head, nothing happens)
  hold = false,
  ev = nil,           -- the event on A: its name
  ev_id = nil,        -- its coroutine
  evb = nil,          -- the event on B
  evb_id = nil,
  hold_id = nil,
  rec_q = BUF0,       -- the record head, as the phase poll said
  rec_t = 0,
  t0 = 0,             -- when the tape started
  phrase_off = 0,
  beat = 0,           -- position in the phrase, 0 ..
  msg = "", msg_t = 0,
  last_ev = "",
}
FIGO = S              -- the test harness looks inside

-- what the knobs say, 0..1
local function figo() return params:get("figo") / 100 end
local function car() return params:get("carattere") / 100 end
local function mem() return params:get("memoria") / 100 end
local function lat() return params:get("latenza") / 1000 end
local function phrase_len() return ({8, 16, 32})[params:get("frase")] end
local function bs() return clock.get_beat_sec() end

local function say(m) S.msg, S.msg_t = m, util.time() end

local function wrap(x)
  local n = BUF1 - BUF0
  return BUF0 + ((x - BUF0) % n)
end

local function recorded()
  return util.time() - S.t0
end

-- where the dry is now: the record head (from the phase poll, 10 ms steps) minus the latency
local function now_pos()
  return wrap(S.rec_q + 0.005 + (util.time() - S.rec_t) - lat())
end

-- a loop [a, a + len] of the tape: inside the region (not across the wrap) and already recorded
local function slice(a, len, back)
  local need = back or 0
  if recorded() < need + len + 0.2 then return nil end
  a = wrap(a)
  if a < BUF0 + 0.05 or a + len > BUF1 - 0.05 then return nil end
  return a, a + len
end

local function both(fn, ...)
  fn(A_L, ...); fn(A_R, ...)
end

local function both_b(fn, ...)
  fn(B_L, ...); fn(B_R, ...)
end

-- A back behind the head: the dry
local function a_trail()
  both(softcut.rate_slew_time, 0)
  both(softcut.rate, 1)
  both(softcut.loop_start, BUF0)
  both(softcut.loop_end, BUF1)
  softcut.voice_sync(A_L, REC_L, -lat())
  softcut.voice_sync(A_R, REC_R, -lat())
  both(softcut.level_slew_time, 0.01)
  both(softcut.level, params:get("livello"))
end

local function a_loop(s, e, pos, rate)
  both(softcut.loop_start, s)
  both(softcut.loop_end, e)
  if pos then both(softcut.position, pos) end
  if rate then both(softcut.rate, rate) end
end

-- wait until a beat of the global clock (absolute)
local function wait_beat(b)
  while clock.get_beats() < b - 0.002 do
    clock.sync(1 / 32)
  end
end

local function cur_beat()
  return math.floor(clock.get_beats() + 0.5)
end

------------------------------------------------------------------------------------------------------------------
-- the events on A (they replace the dry for L beats)

local EV = {}

-- capture then repeat: the first slice passes as it is, then it repeats (the downbeat repeated, like Beat Repeat)
local function repeat_div(div)
  return function(b0, L)
    local s = div * bs()
    local a = now_pos()
    local ls, le = slice(a, s)
    if not ls then return false end
    a_loop(ls, le)
    wait_beat(b0 + L)
    return true
  end
end
EV.R4 = {name = "1/4", run = repeat_div(1 / 1), dub = 1.0, gl = 0.3, minL = 1}
EV.R8 = {name = "1/8", run = repeat_div(1 / 2), dub = 0.8, gl = 0.8}
EV.R16 = {name = "1/16", run = repeat_div(1 / 4), dub = 0.2, gl = 1.0, f = 1}
EV.R32 = {name = "1/32", run = repeat_div(1 / 8), dub = 0.0, gl = 0.6, f = 2}

-- the roll: 1/4, 1/8, 1/16, 1/32 as the event goes on (a build-up); with glitch the pitch rises too
EV.ROLL = {name = "ROLL", dub = 0.2, gl = 0.8, f = 1, minL = 1, run = function(b0, L)
  local a = now_pos()
  local ls = slice(a, bs())
  if not ls then return false end
  local divs = {1, 1 / 2, 1 / 4, 1 / 8}
  if car() > 0.6 and figo() > 0.5 then
    both(softcut.rate_slew_time, L * bs())
    both(softcut.rate, 1.5)
  end
  for i = 1, 4 do
    a_loop(ls, ls + divs[i] * bs())
    wait_beat(b0 + L * i / 4)
  end
  return true
end}

-- the last L beats backwards (dub: at half speed)
EV.REV = {name = "REVERSE", dub = 1.0, gl = 0.5, run = function(b0, L)
  if recorded() < L * bs() + 0.5 then return false end
  both(softcut.rate, car() < 0.35 and -0.5 or -1)
  wait_beat(b0 + L)
  return true
end}

-- an octave down: the tape at half speed (it falls behind the head, never past it)
EV.HALF = {name = "OTTAVA -", dub = 0.8, gl = 0.2, run = function(b0, L)
  both(softcut.rate, 0.5)
  wait_beat(b0 + L)
  return true
end}

-- the tape stops: the speed slides to almost nothing, the level goes with it at the end
EV.STOP = {name = "TAPE STOP", dub = 0.6, gl = 0.0, minL = 1, phrase_end = true, run = function(b0, L)
  local d = L * bs()
  both(softcut.rate_slew_time, d * 0.85)
  both(softcut.rate, 0.03)
  wait_beat(b0 + L * 0.75)
  both(softcut.level_slew_time, d * 0.22)
  both(softcut.level, 0)
  wait_beat(b0 + L)
  return true
end}

-- an octave up: the last half beat looped at double speed
EV.OCT = {name = "OTTAVA +", dub = 0.1, gl = 0.6, run = function(b0, L)
  local h = bs() / 2
  local a = now_pos()
  local ls, le = slice(a - h, h, h)
  if not ls then return false end
  a_loop(ls, le, ls, 2)
  wait_beat(b0 + L)
  return true
end}

-- the last bar in sixteenths, shuffled (Tensor's RAND all the way up)
EV.SHUF = {name = "SHUFFLE", dub = 0.0, gl = 1.0, f = 1, run = function(b0, L)
  local bar = 4 * bs()
  local sx = bs() / 4
  local a = now_pos()
  if not slice(a - bar, bar, bar) then return false end
  local steps = math.floor(L * 4 + 0.5)
  for i = 0, steps - 1 do
    local j = math.random(0, 15)
    local ls, le = slice(a - bar + j * sx, sx, bar)
    if ls then
      a_loop(ls, le, ls, (math.random() < 0.15) and -1 or 1)
    end
    wait_beat(b0 + (i + 1) / 4)
  end
  return true
end}

-- the dry chopped in sixteenths (a trance gate on the loop)
EV.GATE = {name = "GATE", dub = 0.2, gl = 0.7, run = function(b0, L)
  local lv = params:get("livello")
  both(softcut.level_slew_time, 0.004)
  local steps = math.floor(L * 4 + 0.5)
  local pat = math.random(0, 255) | 0x11        -- the first sixteenth of each beat always plays
  for i = 0, steps - 1 do
    local on = ((pat >> (i % 8)) & 1) == 1
    both(softcut.level, on and lv or 0)
    wait_beat(b0 + (i + 1) / 4)
  end
  both(softcut.level, lv)
  return true
end}

-- back a few bars: what played N bars ago, in time (Habit's memory, but in place of the dry)
EV.SKIP = {name = "INDIETRO", dub = 0.5, gl = 0.5, minL = 1, run = function(b0, L)
  local bar = 4 * bs()
  local n = ({1, 2, 4})[math.random(1, 3)]
  if recorded() < n * bar + L * bs() + 0.5 then return false end
  both(softcut.position, wrap(now_pos() - n * bar))
  S.last_ev = "INDIETRO " .. n
  wait_beat(b0 + L)
  return true
end}

local ORDER = {"R4", "R8", "R16", "R32", "ROLL", "REV", "HALF", "STOP", "OCT", "SHUF", "GATE", "SKIP"}

-- how likely an event is on each beat of a 16-beat phrase: few on the ones, more at the end of bars, most at
-- the end of the phrase (where a DJ would put a fill)
local W16 = {0.3, 0.7, 0.8, 1.3, 0.4, 0.7, 0.8, 1.5, 0.4, 0.7, 0.8, 1.3, 0.6, 0.9, 1.4, 2.6}

local function weight_of_beat(b, n)
  local k = math.floor(b * 16 / n)        -- 8 or 32 beat phrases scaled onto the 16
  return W16[k + 1]
end

function FIGO_pick(b, n, f, c, rnd)
  rnd = rnd or math.random
  local p = math.min(0.9, (f ^ 1.6) * 0.55 * weight_of_beat(b, n))
  if f <= 0 or rnd() >= p then return nil end
  local left = n - b                        -- beats to the end of the phrase
  local maxL = math.min(2, left)
  local Ls = {{0.5, 0.3}, {1, 0.5}, {2, (left == 2) and 0.9 or 0.2}}
  local tot, cand = 0, {}
  for _, x in ipairs(Ls) do
    if x[1] <= maxL then tot = tot + x[2]; cand[#cand + 1] = x end
  end
  local r, L = rnd() * tot, cand[#cand][1]
  for _, x in ipairs(cand) do
    r = r - x[2]
    if r <= 0 then L = x[1]; break end
  end
  local ends_phrase = (b + L == n)
  local ends_bar = ((b + L) % 4 == 0)
  local wsum, ws = 0, {}
  for _, k in ipairs(ORDER) do
    local e = EV[k]
    local w = e.dub * (1 - c) + e.gl * c
    if e.f then w = w * (f ^ e.f) end
    if e.minL and L < e.minL then w = 0 end
    if e.phrase_end and not ends_phrase then w = ends_bar and w * 0.3 or 0 end
    ws[#ws + 1] = {k, w}
    wsum = wsum + w
  end
  if wsum <= 0 then return nil end
  r = rnd() * wsum
  for _, x in ipairs(ws) do
    r = r - x[2]
    if r <= 0 and x[2] > 0 then return x[1], L end
  end
  return nil
end

local function start_event(key, b0, L)
  local e = EV[key]
  S.ev = key
  S.last_ev = e.name
  S.ev_id = clock.run(function()
    local ok = e.run(b0, L)
    a_trail()
    S.ev, S.ev_id = nil, nil
    if not ok then S.last_ev = "" end
  end)
end

local function stop_event()
  if S.ev_id then clock.cancel(S.ev_id) end
  S.ev, S.ev_id = nil, nil
  a_trail()
end

------------------------------------------------------------------------------------------------------------------
-- the memory on B (it plays under the dry)

local function b_filter(c)
  if c < 0.5 then
    both_b(softcut.post_filter_dry, 0)
    both_b(softcut.post_filter_lp, 1)
    both_b(softcut.post_filter_bp, 0)
    both_b(softcut.post_filter_fc, 700 + 2600 * c)
    both_b(softcut.post_filter_rq, 1.5)
  else
    both_b(softcut.post_filter_dry, 0)
    both_b(softcut.post_filter_lp, 0)
    both_b(softcut.post_filter_bp, 1)
    both_b(softcut.post_filter_fc, 1200 + 3000 * (c - 0.5) * 2)
    both_b(softcut.post_filter_rq, 1.2)
  end
end

local function b_off(t)
  both_b(softcut.level_slew_time, t or 0.3)
  both_b(softcut.level, 0)
end

-- a bar of N bars ago comes back, under, filtered, swapped left and right
local function memoria_run(b0, L)
  local bar = 4 * bs()
  local n = ({1, 2, 4, 8})[math.random(1, 4)]
  if recorded() < n * bar + L * bs() + 0.5 then return false end
  local c = car()
  b_filter(c)
  both_b(softcut.loop_start, BUF0)
  both_b(softcut.loop_end, BUF1)
  both_b(softcut.rate_slew_time, 0)
  both_b(softcut.rate, (c > 0.8 and math.random() < 0.3) and 2 or 1)
  both_b(softcut.position, wrap(now_pos() - n * bar))
  both_b(softcut.level_slew_time, bs() * 0.5)
  both_b(softcut.level, params:get("livello_mem") * (0.4 + 0.6 * mem()))
  S.last_b = "MEMORIA -" .. n
  wait_beat(b0 + L - 1)
  b_off(bs())
  wait_beat(b0 + L)
  return true
end

-- an echo thrown: the coming half beat (or dotted eighth) repeats, darker and quieter each time
local function eco_run(b0, L)
  local h = (car() < 0.5) and bs() * 0.75 or bs() * 0.5
  local a = now_pos()
  wait_beat(b0 + h / bs())
  local ls, le = slice(a, h)
  if not ls then return false end
  b_filter(0)
  local fc = 3000
  both_b(softcut.post_filter_fc, fc)
  both_b(softcut.rate_slew_time, 0)
  both_b(softcut.rate, 1)
  both_b(softcut.loop_start, ls)
  both_b(softcut.loop_end, le)
  both_b(softcut.position, ls)
  both_b(softcut.level_slew_time, 0.005)
  local lv = params:get("livello_mem") * (0.5 + 0.5 * mem())
  both_b(softcut.level, lv)
  S.last_b = "ECO"
  local reps = math.max(2, math.floor((L * bs() - h) / h))
  for i = 1, reps do
    clock.sleep(h)
    lv = lv * 0.7
    fc = fc * 0.75
    both_b(softcut.level_slew_time, h * 0.5)
    both_b(softcut.level, lv)
    both_b(softcut.post_filter_fc, fc)
  end
  b_off(h)
  return true
end

local function start_b(fn, b0, L)
  S.evb = true
  S.evb_id = clock.run(function()
    fn(b0, L)
    S.evb, S.evb_id = nil, nil
  end)
end

local function stop_b()
  if S.evb_id then clock.cancel(S.evb_id) end
  S.evb, S.evb_id = nil, nil
  b_off(0.2)
end

function FIGO_pick_b(b, n, m, c, rnd)
  rnd = rnd or math.random
  if m <= 0 or b % 4 ~= 0 then return nil end
  local last_bar = (b >= n - 4)
  local p = math.min(0.85, m * (last_bar and 0.7 or 0.45))
  if rnd() >= p then return nil end
  local eco_w = (1 - c) * (last_bar and 1.5 or 0.6) + c * 0.3
  if rnd() * (1 + eco_w) < eco_w then
    return "ECO", math.min(4, n - b)
  end
  return "MEMORIA", math.min(({2, 4, 8})[math.floor(rnd() * 3) + 1], n - b)
end

------------------------------------------------------------------------------------------------------------------
-- HOLD (K2) and PULITO (K3)

local function hold_on()
  if S.hold_id then return end
  S.hold_id = clock.run(function()
    clock.sync(1)
    if S.ev then stop_event() end
    S.hold = true
    local beat = bs()
    local a = now_pos()
    local ls, le = slice(a - beat, beat, beat)
    if not ls then S.hold = false; S.hold_id = nil; say("HOLD: troppo presto"); return end
    a_loop(ls, le, ls, 1)
    say("HOLD")
    while S.hold do
      clock.sync(1)
      if not S.hold then break end
      local f, c = figo(), car()
      if math.random() < f * 0.7 then          -- the held beat varies by itself, as much as FIGO says
        local r = math.random()
        if r < 0.45 then
          local div = ({1 / 2, 1 / 4, 1 / 8})[math.random(1, (c > 0.5) and 3 or 2)]
          a_loop(ls, ls + beat * div, nil, 1)
        elseif r < 0.7 then
          a_loop(ls, le, nil, -1)
        elseif r < 0.85 then
          a_loop(ls, le, nil, (c > 0.5) and 2 or 0.5)
        else
          a_loop(ls, le, nil, 1)
        end
      else
        a_loop(ls, le, nil, 1)
      end
    end
  end)
end

local function hold_off()
  S.hold = false
  clock.run(function()
    clock.sync(1)
    if S.hold_id then clock.cancel(S.hold_id) end
    S.hold_id = nil
    S.hold = false                         -- (the hold may have started on this same beat)
    if not S.ev then a_trail() end
    say("VIA")
  end)
end

-- the way out to clean, on the next beat: the tape stops (dub) or spins back (glitch), then the dry
local function release()
  clock.run(function()
    clock.sync(1)
    if S.ev then stop_event() end
    stop_b()
    if S.hold then
      S.hold = false
      if S.hold_id then clock.cancel(S.hold_id) end
      S.hold_id = nil
    end
    local b0 = cur_beat()
    local kind = params:get("release")
    if kind == 1 then kind = (car() < 0.5) and 2 or 3 end
    S.ev = "REL"
    if kind == 2 then
      S.last_ev = "TAPE STOP"
      EV.STOP.run(b0, 1)
    elseif kind == 3 then
      S.last_ev = "BACKSPIN"
      both(softcut.rate_slew_time, bs() * 0.15)
      both(softcut.rate, -2.5)
      wait_beat(b0 + 0.5)
    end
    a_trail()
    S.ev = nil
    say("PULITO")
  end)
end

------------------------------------------------------------------------------------------------------------------
-- the brain: one decision per beat

local function phrase_beat()
  local n = phrase_len()
  return math.floor(clock.get_beats() - S.phrase_off + 0.5) % n
end

local function brain()
  while true do
    clock.sync(1)
    local n = phrase_len()
    local b = phrase_beat()
    S.beat = b
    if S.on and not S.hold then
      if not S.ev then
        local k, L = FIGO_pick(b, n, figo(), car())
        if k then start_event(k, cur_beat(), L) end
      end
      if not S.evb then
        local k, L = FIGO_pick_b(b, n, mem(), car())
        if k == "ECO" then start_b(eco_run, cur_beat(), L)
        elseif k == "MEMORIA" then start_b(memoria_run, cur_beat(), L) end
      end
    end
  end
end

------------------------------------------------------------------------------------------------------------------

local function input_routing()
  local mono = params:get("ingresso") == 2
  softcut.level_input_cut(1, REC_L, 1)
  softcut.level_input_cut(2, REC_L, 0)
  softcut.level_input_cut(1, REC_R, mono and 1 or 0)
  softcut.level_input_cut(2, REC_R, mono and 0 or 1)
end

local function softcut_setup()
  softcut.buffer_clear()
  audio.level_adc_cut(1)
  audio.level_eng_cut(0)
  audio.level_tape_cut(0)
  for v = 1, 6 do
    softcut.enable(v, 1)
    softcut.buffer(v, (v % 2 == 1) and 1 or 2)
    softcut.pan(v, (v % 2 == 1) and -1 or 1)
    softcut.loop(v, 1)
    softcut.loop_start(v, BUF0)
    softcut.loop_end(v, BUF1)
    softcut.position(v, BUF0)
    softcut.rate(v, 1)
    softcut.fade_time(v, FADE)
    softcut.level_slew_time(v, 0.01)
    softcut.rate_slew_time(v, 0)
    softcut.rec(v, 0)
    softcut.rec_level(v, 0)
    softcut.pre_level(v, 0)
    softcut.level(v, 0)
    softcut.level_input_cut(1, v, 0)
    softcut.level_input_cut(2, v, 0)
    softcut.pre_filter_dry(v, 1)          -- the dry passes here: full band, no record filter
    softcut.pre_filter_lp(v, 0)
    softcut.pre_filter_fc_mod(v, 0)
    softcut.post_filter_dry(v, 1)
    softcut.post_filter_lp(v, 0)
    softcut.post_filter_hp(v, 0)
    softcut.post_filter_bp(v, 0)
    softcut.post_filter_br(v, 0)
    softcut.play(v, 1)
  end
  for _, v in ipairs({B_L, B_R}) do        -- the memory comes back swapped: the left of then on the right
    softcut.pan(v, (v % 2 == 1) and 0.7 or -0.7)
  end
  input_routing()
  softcut.rec_level(REC_L, 1)
  softcut.rec_level(REC_R, 1)
  softcut.rec(REC_L, 1)
  softcut.rec(REC_R, 1)
  S.t0 = util.time()
  S.rec_q, S.rec_t = BUF0, S.t0
  softcut.phase_quant(REC_L, 0.01)
  softcut.event_phase(function(v, pos)
    if v == REC_L then S.rec_q, S.rec_t = pos, util.time() end
  end)
  softcut.poll_start_phase()
end

local dirty = true

function init()
  params:add_separator("figo_sep", "FIGO")
  params:add_control("figo", "FIGO", controlspec.new(0, 100, "lin", 1, 0, "%"))
  params:add_control("carattere", "carattere (dub-glitch)", controlspec.new(0, 100, "lin", 1, 30, "%"))
  params:add_control("memoria", "memoria", controlspec.new(0, 100, "lin", 1, 0, "%"))
  params:add_option("frase", "frase", {"8 battiti", "16 battiti", "32 battiti"}, 2)
  params:add_trigger("allinea", "allinea: la frase parte ora")
  params:set_action("allinea", function() S.phrase_off = cur_beat(); say("FRASE DA QUI") end)
  params:add_option("release", "uscita (K3)", {"auto", "tape stop", "backspin", "secca"}, 1)
  params:add_option("ingresso", "ingresso", {"stereo", "mono (L)"}, 1)
  params:set_action("ingresso", function() input_routing() end)
  params:add_control("livello", "livello", controlspec.new(0, 1.5, "lin", 0.01, 1, ""))
  params:set_action("livello", function(x) if not S.ev and not S.hold then both(softcut.level, x) end end)
  params:add_control("livello_mem", "livello memoria", controlspec.new(0, 1, "lin", 0.01, 0.6, ""))
  params:add_control("latenza", "latenza", controlspec.new(4, 30, "lin", 1, 8, "ms"))
  params:set_action("latenza", function() if not S.ev and not S.hold then a_trail() end end)
  for _, id in ipairs({"figo", "carattere", "memoria"}) do
    params:set_action(id, function() dirty = true end)
  end

  softcut_setup()
  params:read()                            -- the settings of last time (written on the way out)
  audio.level_monitor(0)                   -- the dry comes from A, not from the monitor
  clock.run(function()
    clock.sleep(0.2)                       -- the head has moved past the latency: A behind it
    a_trail()
    clock.run(brain)
  end)
  clock.transport.start = function() S.phrase_off = cur_beat() end
  clock.run(function()
    while true do
      clock.sleep(1 / 15)
      redraw()
    end
  end)
end

function enc(n, d)
  if n == 1 then params:delta("memoria", d)
  elseif n == 2 then params:delta("figo", d)
  elseif n == 3 then params:delta("carattere", d) end
end

function key(n, z)
  if z == 0 then return end
  if n == 2 then
    if S.hold or S.hold_id then hold_off() else hold_on() end
  elseif n == 3 then
    if S.on then
      S.on = false
      release()
    else
      S.on = true
      say("VIA")
    end
  end
end

local function bar(x, y, w, v)
  screen.level(3)
  screen.rect(x, y, w, 3)
  screen.fill()
  screen.level(15)
  screen.rect(x, y, math.floor(w * v + 0.5), 3)
  screen.fill()
end

function redraw()
  screen.clear()
  screen.font_face(1)
  screen.font_size(8)
  screen.level(15)
  screen.move(0, 8)
  screen.text("FIGO")
  screen.move(127, 8)
  screen.text_right(string.format("%d", params:get("figo")))
  bar(0, 11, 128, figo())
  screen.level(6)
  screen.move(0, 23)
  screen.text("dub")
  screen.move(127, 23)
  screen.text_right("glitch")
  screen.level(3)
  screen.move(22, 21)
  screen.line(100, 21)
  screen.stroke()
  screen.level(15)
  screen.rect(22 + math.floor(78 * car()) - 1, 19, 3, 5)
  screen.fill()
  screen.level(8)
  screen.move(0, 33)
  screen.text(string.format("MEMORIA %d", params:get("memoria")))
  screen.move(127, 33)
  screen.text_right(string.format("%.1f BPM", clock.get_tempo()))
  -- the phrase: one box per beat
  local n = phrase_len()
  local w = math.floor(128 / n)
  for i = 0, n - 1 do
    screen.level(i == S.beat and 15 or ((i % 4 == 0) and 5 or 2))
    screen.rect(i * w, 37, w - 1, 4)
    screen.fill()
  end
  screen.move(0, 56)
  screen.font_size(16)
  local big
  if not S.on then big = "PULITO"
  elseif S.hold then big = "HOLD"
  elseif S.ev then big = S.last_ev
  else big = "" end
  screen.level(15)
  screen.text(big)
  screen.font_size(8)
  screen.move(127, 63)
  screen.level(6)
  if S.evb and S.last_b then screen.text_right(S.last_b) end
  if util.time() - S.msg_t < 1.5 then
    screen.move(0, 63)
    screen.level(10)
    screen.text(S.msg)
  end
  screen.update()
end

function cleanup()
  params:write()
  softcut.poll_stop_phase()
  audio.level_monitor(util.dbamp(params:get("monitor_level")))   -- the monitor as the LEVELS menu says
end
