// Engine_GillsMicrocosmo: granular / micro-loop / glitch / multidelay engine for norns.
// Port of the Ksoloti Gills "microcosm" patch (11 effects x 4 variations).
//   - a 10.9 s history of the input (plus HOLD and the HAZE feedback) is always being written
//   - short "voices" replay pieces of it (rate, envelope SHAPE, loops, filter sweeps, bitcrush);
//     the scheduler that decides when and what to play runs here in sclang, one pass every
//     64 samples, and every new voice is sent as a timestamped bundle: the rhythm is sample exact
//   - PATTERN and WARP: six-tap delay with feedback, tap filters and pitch
//   - LP filter, MIX, FX VOLUME, SPACE (plate after Mutable Instruments Rings, 4 modes),
//     60 s looper with overdub, undo,
//     reverse, speed, fade, pre/post; aux (send/return) or insert; bypass with trails
// Only core SuperCollider UGens are used.

Engine_GillsMicrocosmo : CroneEngine {
	classvar maxVoices = 8, bs = 64, nb = 524288, lat = 0.03;
	// HAZE: gain per SHAPE (square, ramp, triangle, saw), the same loudness at each, as on the Gills
	classvar hzK = #[0.535, 0.76, 0.71, 0.74];
	var <grpH, <grpV, <grpP, <histL, <histR, <dlyL, <dlyR, <lbL, <lbR, <ldL, <ldR;
	var <hwB, <hwK, <wetB, <xB, <dryB, <rawB, <gIB, <inB2, <loopB, <postB, <lfoK, <envK, <pkK;
	var <histS, <delS, <outS, <loopS, <task, <onsetFunc;
	// scheduler state
	var <algo, <vari, <act, <rep, <shp, <shI, <beat, <modDep, <voices, <now, <curOff, <hwEst, <envS, <envFol;
	var stepCnt, stepIdx, barIdx, chainG, chainIdx, burstLeft, burstCnt, burstOn, burstStep, intLeft, intCnt, intSrc;
	var duckT, hazeAcc, hazeLag, glPh, tunPh, slotWait, perm, gate, anchor, onPos, onCount, onHead, onNew, onPend, syncReq;
	var subN, lastDelay, holdOn, errCount;
	// REVERSE of the effect, LOOPER ONLY
	var <fxRev, <lonly;
	// looper state: 0 empty, 1 rec, 2 play, 3 dub, 4 stop; quantize (samples per quarter, 0 = off)
	var <lst, lrecT, llen, ldub, lrev, lspd, lfade, qlen, <lqPend, lqGen;

	*new { arg context, doneCallback;
		^super.new(context, doneCallback);
	}

	alloc {
		var s = context.server;

		// ------------------------------------------------------------ SPACE plate reverb
		// Griesinger/Dattorro "figure eight" as laid out in the Mutable Instruments Rings reverb
		// (MIT licence, (c) 2014 Emilie Gillet): predelay, four input diffusers, then two
		// branches (low-pass, two allpasses, long modulated line) that feed each other.
		// Same structure and numbers as the Gills patch. sz room size 0.3..1.6, t60 decay in s,
		// klp loop brightness 0..1, kap diffusion, amp modulation depth, pdS predelay in samples.
		// The loop goes through LocalIn (one block), so the long lines read one block earlier
		// and the loop keeps its exact length. fb: the two loop channels of the synth's LocalIn;
		// the caller writes the returned pair back (LocalOut, clipped at 4) and plays it doubled.
		var plate = { arg in, sz, t60, klp, kap, amp, pdS, fb;
			var sr = SampleRate.ir, bsz = BlockSize.ir;
			var len = { arg n; ((n * sz) - 1) / sr };
			// AllpassN feedback = sign * exp(log(0.001) * delay / decay): decay for a coefficient g * kap
			var ap = { arg x, n, g, mx; AllpassN.ar(x, mx, len.(n), (len.(n) * (0.001.log / kap.log)) * g) };
			var krt = 2 ** ((-9.966 * ((10180 * sz) / 48000)) / t60);
			var t1 = LFTri.kr(0.5), t2 = LFTri.kr(0.3, 1.48);
			var l1 = 0.5 + ((0.5 * t1) * (1.5 - ((0.5 * t1) * t1)));
			var l2 = 0.5 + ((0.5 * t2) * (1.5 - ((0.5 * t2) * t2)));
			var x = DelayL.ar((in[0] + in[1]) * 0.2, 0.1, pdS.clip(1, 4800) / sr);
			var d1 = DelayL.ar(fb[0], 0.25, ((((4460 * sz) - 1) + ((40 * amp) * l1)) - bsz) / sr);
			var d2 = DelayL.ar(fb[1], 0.25, ((((6261 * sz) - 1) + ((50 * amp) * l2)) - bsz) / sr);
			var a, c;
			x = ap.(ap.(ap.(ap.(x, 150, 1, 0.02), 214, 1, 0.02), 319, 1, 0.02), 527, 1, 0.02);
			a = OnePole.ar(x + (d2 * krt), 1 - klp);
			a = ap.(ap.(a, 2182, -1, 0.1), 2690, 1, 0.1);
			c = OnePole.ar(x + (d1 * krt), 1 - klp);
			c = ap.(ap.(c, 2525, 1, 0.1), 2197, -1, 0.1);
			[a, c]
		};

		// ------------------------------------------------------------ history writer, onsets, LFO
		SynthDef(\mcm_hist, {
			var inL = In.ar(\in0.kr(0));
			var inR = In.ar(\in1.kr(1));
			var mode = \inMode.kr(0);                          // 0 mono L, 1 stereo, 2 L+R
			var m = (inL + inR) * 0.5;
			var l = Select.ar(mode, [inL, inL, m]);
			var r = Select.ar(mode, [inL, inR, m]);
			// bypass with trails: the effect input closes in 10 ms
			var gI = Slew.ar(K2A.ar(1 - \kill.kr(0)), 100, 100);
			var d = [l, r] * gI;
			var lp = InFeedback.ar(\loopbus.kr(0), 2);
			var dp = d + (lp * \pre.kr(0));                    // looper pre-FX: it goes through the effect
			var hw = Phasor.ar(0, 1, 0, BufFrames.ir(\bufL.kr(0)));
			var hm = Slew.kr(\hold.kr(0), 50, 50);              // 20 ms to hold
			var hl = \holdlen.kr(96000);
			var held = [\bufL.kr(0), \bufR.kr(0)].collect { arg b; BufRd.ar(1, b, (hw - hl).wrap(0, BufFrames.ir(b)), 1, 1) };
			var fb = InFeedback.ar(\wetbus.kr(0), 2) * \hazefb.kr(0);
			var soft = { arg x; var a = x.abs; Select.ar(a > 0.75, [x, x.sign * (0.75 + ((a - 0.75) / (1 + ((a - 0.75) * 2))))]) };
			var w = Select.ar(hm > 0, [dp + soft.(fb), dp + ((held - dp) * hm)]);
			var a = ((w[0].abs) + (w[1].abs)) * 0.5;
			var envF = Amplitude.ar(a, 0.00096, 0.012);
			var envSl = Amplitude.ar(a, 0.06, 0.24);
			var envFo = Amplitude.ar(a, 0.0048, 0.16);
			var onset = Trig1.ar(envF > ((envSl * 1.8) + 0.006), 0.06);
			var lfoPh = Phasor.kr(0, (0.05 * (2 ** (\modrate.kr(0) * 7))) / ControlRate.ir, 0, 1);
			// WARP D crossfade: its own phase at a quarter of the LFO speed (no jump when the LFO wraps)
			var wrpPh = Phasor.kr(0, (0.0125 * (2 ** (\modrate.kr(0) * 7))) / ControlRate.ir, 0, 1);
			BufWr.ar(w[0], \bufL.kr(0), hw);
			BufWr.ar(w[1], \bufR.kr(0), hw);
			SendReply.ar(onset, '/mcm_onset', (hw - 96).wrap(0, BufFrames.ir(\bufL.kr(0))));
			Out.ar(\hwbus.kr(0), hw);
			Out.kr(\hwk.kr(0), A2K.kr(hw));
			Out.ar(\xbus.kr(0), w);                             // what the multidelay hears
			Out.ar(\drybus.kr(0), dp);
			Out.ar(\inbus2.kr(0), d);                           // looper pre-FX source (without the loop)
			Out.ar(\rawbus.kr(0), [l, r]);
			Out.ar(\gibus.kr(0), gI);
			Out.kr(\envk.kr(0), [A2K.kr(envSl), A2K.kr(envFo)]);
			Out.kr(\lfok.kr(0), [(lfoPh * 2pi).sin * \moddep.kr(0), wrpPh]);   // MOD DEPTH x LFO, slow phase
			Out.kr(\pkk.kr(0), Peak.kr(l.abs.max(r.abs), Impulse.kr(15)));
		}).add;

		// ------------------------------------------------------------ one voice
		SynthDef(\mcm_voice, {
			var sr = SampleRate.ir;
			var bL = \bufL.kr(0), bR = \bufR.kr(0);
			var n = BufFrames.ir(bL);
			var hwS = Latch.ar(In.ar(\hwbus.kr(0)), Impulse.ar(0));
			var life = \life.ir(4800);
			var lifeS = life / sr;
			var rate0 = \rate.kr(1);
			var lfo = In.kr(\lfok.kr(0), 2);
			var rate = Lag.kr(rate0, 0.01) * (1 + (0.03 * lfo[0]));
			var seg = \seg.kr(0);
			var isLoop = seg > 0;
			var absP = \abs.ir(-1);
			var st0 = Select.ar(absP >= 0, [hwS - \back.ir(0), K2A.ar(absP)]);
			// never read ahead of the write head (faster than real time voices start further back)
			var need = Select.kr(isLoop, [((rate0 - 1).max(0) * life) + 96, 2]);
			var bk0 = (hwS - st0).wrap(0, n).max(need);
			// REVERSE one-shot (rv): the same stretch is read from its far end; a forward grain whose end
			// is not recorded yet moves back in time by its own length (the rate arrives already negated)
			var rv = \rv.ir(0);
			var span = rate0.abs * life;
			var bkR = Select.ar(rate0 < 0, [bk0 + span, (bk0 - span).max(96)]);
			var bk = Select.ar(rv, [bk0, bkR]).clip(2, n - 8192);
			var start = Latch.ar(hwS - bk, Impulse.ar(0));
			var off = Phasor.ar(0, rate, 0, seg.max(1));
			var lin = Sweep.ar(0, rate * sr);
			var pos = start + Select.ar(isLoop, [lin, off]);
			var xf = (seg / 8).min(240).max(1);
			// loops: forwards the seam is at the end of the segment, backwards at its start
			var bwd = rate < 0;
			var t = Select.ar(bwd, [((off - (seg - xf)) / xf).clip(0, 1), ((xf - off) / xf).clip(0, 1)]) * isLoop;
			var wraps = PulseCount.ar(HPZ1.ar(off).abs > (seg * 0.25));
			var rd = { arg p; [bL, bR].collect { arg b; BufRd.ar(1, b, p.wrap(0, n), 1, 2) } };
			var a = rd.(pos);
			var b = rd.(pos + (seg * ((2 * bwd) - 1)));
			var sig = a + ((b - a) * t);
			// envelope, one value per block as on the Gills. sh 0..3 = the contour (square, ramp, triangle,
			// saw) of every grain or of every turn of a micro loop
			var el = Sweep.kr(0, 1);
			var sh = \sh.ir(0);
			var shc = sh.clip(0, 3);
			var cw = \cw.ir(0);
			var contour = \contour.ir(0) * isLoop;
			var lx = (el / lifeS).clip(0, 1);
			var lp = Select.kr(rv, [lx, 1 - lx]);              // reversed one-shot: window and sweep reversed
			var ip = Select.kr(contour, [lp, (A2K.kr(off) / seg.max(1)).clip(0, 1)]);
			var sm = { arg x; (x * x) * (3 - (2 * x)) };
			// TUNNEL (cw 2): how a drone fades over its life (quick start, then a curve between a square
			// and a fourth power), the same as on the Gills
			var tunDec = {
				var a = 0.04368;
				var y = 1 - ((lx - a) / (1 - a)).clip(0, 1);
				var y2 = y * y;
				var e = Select.kr(lx < a, [y2 * (0.72 + (0.28 * y2)), sm.((lx / a).clip(0, 1))]);
				(e * sm.(((1 - lx) * 10).clip(0, 1))) * ((lx > 0) * (lx < 1))
			};
			// the pedal's contours. a, r: attack and release fades as fractions (mf = longest). bell: HAZE
			// grains (cw 1) take a Hann bell for the triangle, the smoothest cloud (after the grain windows
			// of Mutable Instruments Clouds, MIT licence, (c) 2014 Emilie Gillet)
			var shW = { arg ph, mf, bell;
				var triW = 1 - ((2 * ph) - 1).abs;
				var hannW = (ph * pi).sin.squared;
				var e = Select.kr(shc, [1, ph, Select.kr(bell, [triW, hannW]), 1 - ph]);
				var a = Select.kr(shc, [mf, 0, 0, mf.min(0.015)]);
				var r = Select.kr(shc, [mf, mf.min(0.03), 0, 0]);
				var fa = Select.kr(a > 0, [1, sm.((ph / a.max(0.00001)).clip(0, 1))]);
				var fr = Select.kr(r > 0, [1, sm.(((1 - ph) / r.max(0.00001)).clip(0, 1))]);
				((e * fa) * fr) * ((ph > 0) * (ph < 1))
			};
			var bell = cw > 0;
			var eP = Select.kr(contour, [shW.(lp, Select.kr(bell, [0.1, 0.02]), bell), shW.(ip, 0.03 * (sh > 0), 0)]);
			var fio = ((el * (sr / 384)).min(1) * (((lifeS - el) * (sr / 384)).clip(0, 1)));
			var eN = eP * Select.kr(contour, [1, fio]);
			// ramp, triangle and saw also move a gentle low-pass with the contour (SHAPE works on "the volume
			// or filter characteristics"): open at the top of the contour, dark where it is low
			var kT = Select.kr(sh > 0, [1, 0.04 + (0.96 * eN.cubed)]);
			// cw 2 (TUNNEL): the drone also fades over its life
			var env = eN * Select.kr(cw > 1.5, [1, tunDec.value]);
			var kg = EnvGen.kr(Env.asr(0.001, 1, 0.004), \gate.kr(1), doneAction: 2);
			var gg = \gain.ir(1) * (\decay.ir(1) ** A2K.kr(wraps)) * kg * env;
			// filter sweep from f0 to f1 over the life (1 low-pass, 2 band-pass), bitcrush
			var fc = (\f0.kr(1000) * (2 ** (lp * \flog.kr(0)))).clip(20, 20000);
			var rq = 1 / \q.ir(1);
			var ft = \ft.ir(0);
			var cd = \cd.ir(0);
			var cq = \cq.ir(32);
			var pan = \pan.ir(0);
			var gl = Select.kr(pan > 0, [1, 1 - (pan * 0.8)]);
			var gr = Select.kr(pan < 0, [1, 1 + (pan * 0.8)]);
			sig = Select.ar(ft, [sig, RLPF.ar(sig, fc, rq), BPF.ar(sig, fc, rq) * 1.6]);
			sig = Select.ar(cd > 0, [sig, Latch.ar((sig * cq).round / cq, Impulse.ar(sr / cd.max(1)))]);
			sig = Select.ar(sh > 0, [sig, OnePole.ar(sig, 1 - kT)]);
			Line.kr(0, 1, lifeS, doneAction: 2);
			Out.ar(\out.kr(0), [sig[0] * (gg * gl), sig[1] * (gg * gr)]);
		}).add;

		// ------------------------------------------------------------ PATTERN / WARP multidelay
		SynthDef(\mcm_delay, {
			var sr = SampleRate.ir;
			var x = In.ar(\xbus.kr(0), 2);
			var act = \active.kr(0);
			var bufs = [\dbufL.kr(0), \dbufR.kr(0)];
			var fbIn = LocalIn.ar(2);
			var ph = [0, 1].collect { arg c; DelTapWr.ar(bufs[c], x[c] + (fbIn[c] * act)) };
			var bsz = BlockSize.ir;
			var lfo = In.kr(\lfok.kr(0), 2);
			var mod = 120 * lfo[0];
			var init = \t_init.tr(0);
			var snap = Trig1.kr(init, 0.4);                     // after a preset change the taps jump
			var dip = Lag.kr(1 - Trig1.kr(init, 0.01), 0.004);
			var tT = \tt.kr(#[12000, 24000, 36000, 48000, 60000, 72000]);
			var tG = \tg.kr(#[0, 0, 0, 0, 0, 0]);
			var tPr = \tpr.kr(#[1, 1, 1, 1, 1, 1]);
			var nTap = \ntap.kr(1);
			var fmode = \fmode.kr(0);                           // 0 none, 1 low-pass (WARP A), 2 band-pass (WARP B)
			var warp3 = \warp3.kr(0);
			var envN = (In.kr(\envk.kr(0), 2)[1] * 6).min(1);
			// REVERSE: the taps read backwards (pitch ratio -1) in chunks as long as the tap delay;
			// the switch happens inside a 12 ms dip of the taps
			var rvIn = \frev.kr(0);
			var rvs = DelayN.kr(rvIn, 0.01, 0.006);
			var dipR = Lag.kr(1 - Trig1.kr(Changed.kr(rvIn), 0.012), 0.003);
			var rdT = { arg c, d; DelTapRd.ar(bufs[c], ph[c], d.max(1) / sr, 2) };
			// one tap: plain, or a two-head pitch shifter on the delay line (WARP C/D, REVERSE), then the tap filter
			var tapOut = { arg kv, pr0, d, tt;
				var pr = pr0 * (1 - (2 * rvs));
				var win = Select.kr(rvs, [2048, (2 * tt).clip(4800, 96000)]);
				var inc = (pr - 1).abs / win;
				var p1 = Phasor.ar(0, inc, 0, 1);
				var p2 = (p1 + 0.5).wrap(0, 1);
				var up = pr > 1;
				var da = Select.ar(up, [win * p1, win * (1 - p1)]);
				var db = Select.ar(up, [win * p2, win * (1 - p2)]);
				var wa = 1 - ((p1 * 2) - 1).abs;
				var xw = 0.5 + (0.5 * (((lfo[1] + (kv * 0.16)) * 2pi).sin));
				var f1 = (300 * (2 ** (1.2 + (4.1 * envN) + (0.3 * kv)))).min(20000);
				var f2 = (300 * (2 ** ((kv * 0.9) + 1))).min(20000);
				[0, 1].collect { arg c;
					var plain = rdT.(c, d);
					var sh = (rdT.(c, d + da) * wa) + (rdT.(c, d + db) * (1 - wa));
					// (pr - 1).abs > 0: "!=" on a UGen is an identity test in sclang, not a signal
					var pt = Select.ar((pr - 1).abs > 0.0001, [plain, Select.ar(warp3 * (1 - rvs), [sh, plain + (xw * (sh - plain))])]);
					Select.ar(fmode, [pt, RLPF.ar(pt, f1, 0.5), BPF.ar(pt, f2, 1 / 6) * 4.5])
				}
			};
			var dly = 6.collect { arg k;
				Select.ar(snap > 0, [Lag.ar(K2A.ar(tT[k]), 0.36), K2A.ar(tT[k])]) + (if(k.odd, 1, -1) * mod)
			};
			var taps = 6.collect { arg k;
				var o = tapOut.(k, tPr[k], dly[k], tT[k]);
				var g = tG[k] * (k < nTap);
				var pl = if(k.odd, 1, 0.52), pr2 = if(k.odd, 0.52, 1);   // pan +0.6 / -0.6: first tap on the right, as on the pedal
				[o[0] * (g * pl), o[1] * (g * pr2)]
			};
			var sl = taps.collect({ arg t; t[0] }).sum;
			var srr = taps.collect({ arg t; t[1] }).sum;
			// feedback: PATTERN reads the pattern length, WARP the last tap; the loop goes through
			// LocalIn (one block), so both are read one block earlier
			var fbT = \fbt.kr(24000);
			var fbD = Select.ar(snap > 0, [Lag.ar(K2A.ar(fbT), 0.36), K2A.ar(fbT)]) + (Select.kr(nTap % 2, [-1, 1]) * mod);
			var fP = [0, 1].collect { arg c; rdT.(c, fbD - bsz) };
			var last = (nTap - 1).clip(0, 5);
			var fW = tapOut.(last, Select.kr(last, tPr), Select.ar(last, dly) - bsz, Select.kr(last, tT));
			var fl = Select.ar(\iswarp.kr(0), [fP, fW]);
			var lp = OnePole.ar(fl, 0.45);
			var dc = OnePole.ar(lp, 0.997);
			var qq = (lp - dc) * \dfb.kr(0);
			var qs = qq.collect { arg v; var a = v.abs; Select.ar(a > 0.75, [v, v.sign * (0.75 + ((a - 0.75) / (1 + ((a - 0.75) * 2))))]) };
			LocalOut.ar(qs);
			Out.ar(\out.kr(0), [sl, srr] * (Lag.kr(act, 0.007) * dip * dipR));
		}).add;

		// ------------------------------------------------------------ filter, mix, SPACE, output
		SynthDef(\mcm_out, {
			var sr = SampleRate.ir;
			var wet = In.ar(\wetbus.kr(0), 2);
			var dry = In.ar(\drybus.kr(0), 2);
			var raw = In.ar(\rawbus.kr(0), 2);
			var gI = In.ar(\gibus.kr(0));
			var lp = InFeedback.ar(\loopbus.kr(0), 2);
			var pre = \pre.kr(0);
			// LOOPER ONLY: the effects are muted and the input itself goes through the pitch modulation
			// (MOD DEPTH / RATE, +-3 % like the voices), the filter, MIX and SPACE
			var mdA = 0.03 / (2pi * (0.05 * (2 ** (\modrate.kr(0) * 7))));
			var pass = DelayC.ar(dry, 0.5, (mdA * (\moddep.kr(0) + In.kr(\lfok.kr(0), 2)[0])).clip(0, 0.45));
			var wetIn = Select.ar(\lonly.kr(0), [wet, pass]);
			var fCut = Lag.kr(\flt.kr(1), 0.03);
			var fRes = Lag.kr(\res.kr(0), 0.03);
			var fc = (20 * (2 ** (fCut * 10))).clip(20, 20000);
			var byp = ((fCut - 0.94) / 0.05).clip(0, 1);
			var gate = (fCut / 0.03).min(1);
			var comp = 1 / (1 + (fRes * 1.5));
			var lpf = RLPF.ar(wetIn, fc, 2 * (1 - (0.93 * fRes))) * comp;
			var fw = lpf + ((wetIn - lpf) * byp);
			var mixS = Lag.kr(\mix.kr(0.5), 0.02);
			var fxv = Lag.kr(\fxv.kr(0.5), 0.02);
			var spc = Lag.kr(\spc.kr(0), 0.02);
			var lonly = \lonly.kr(0);
			var dg = (2 * (1 - mixS)).min(1);
			var wk = (2 * mixS).min(1);
			var wg = wk * ((2 * fxv) * gate);
			// INTERRUPT: the glitches replace the dry signal; MIX 100% = no dry at all
			var duck = Lag.kr(\duck.kr(0), 0.33);
			var d = Select.kr(\interrupt.kr(0) * (1 - lonly), [dg, dg * (1 - (duck * wk))]);
			var ol = (dry * d) + (fw * wg);
			var xl = raw * (gI * d);
			var sw = (2 * spc).min(1), sd = (2 * (1 - spc)).min(1);
			// SPACE: plate, shortest to longest: A bright room, B dark medium, C large hall, D ambient;
			// a mode change fades the wet in over 50 ms, as on the Gills.
			// Echo beside the plate (the manual: SPACE "mixes in reverberation and delay"), as on the
			// Gills: a ping-pong pair whose times are two subdivisions of the tempo per mode (secho
			// 1 = free, as at 120 BPM), folded by octaves into 30 ms .. 1.3 s; the repeats darken in
			// the loop and are also sent into the plate. A 3/32 + 1/16, B 1/8 + 3/16, C 3/16 + 1/4,
			// D 3/8 + 1/2. A new tempo bends the repeats, as tape.
			var md = \rmode.kr(0);
			var tabs = { arg t; Select.kr(md, t) };
			var fade = Sweep.kr(Changed.kr(md), 20).clip(0, 1);
			// secho: 0 the echo follows the tempo, 1 free (as at 120 BPM), 2 off (the plate alone, as loud)
			var se = \secho.kr(0);
			var eOn = se < 1.5;
			var trim = Select.kr(eOn, [tabs.([0.838, 1.648, 1.37, 1.38]), tabs.([0.763, 1.436, 1.131, 1.064])]);
			var bt = Select.kr(se > 0.5, [\beat.kr(24000), 24000]);
			var tl0 = bt * tabs.([0.1875, 0.5, 0.75, 1.5]);
			var tr0 = bt * tabs.([0.25, 0.75, 1.0, 2.0]);
			var dn = 2 ** ((tr0 / 62400).log2.ceil.max(0)).neg;      // halvings: the right time fits 1.3 s
			var up = 2 ** ((1440 / (tl0 * dn)).log2.ceil.max(0));    // doublings: the left time is 30 ms or more
			var eTl = Lag.kr((tl0 * dn) * up, 0.29);
			var eTr = Lag.kr((tr0 * dn) * up, 0.29);
			var eK = tabs.([6000, 2200, 4000, 3000].collect { arg f; var w = (2pi * f) / 48000; 1 - (w / (1 + w)) });   // loop low-pass
			var fb = LocalIn.ar(4);                                   // plate loop (2), echo lines (2)
			var soft = { arg x; Select.ar(x.abs > 0.75, [x, x.sign * (0.75 + ((x.abs - 0.75) / (1 + ((x.abs - 0.75) * 2))))]) };
			var rl = DelayL.ar(fb[2], 1.3, (eTl - BlockSize.ir) / sr);
			var rr = DelayL.ar(fb[3], 1.3, (eTr - BlockSize.ir) / sr);
			var efb = tabs.([0.15, 0.3, 0.4, 0.55]);
			var wL = soft.(ol[0] + (OnePole.ar(rr, eK) * efb));       // ping-pong: each side repeats the other
			var wR = soft.(ol[1] + (OnePole.ar(rl, eK) * efb));
			var snd = tabs.([0.3, 0.4, 0.5, 0.6]) * eOn;
			var pl = plate.(ol + ([rl, rr] * snd), tabs.([0.55, 0.85, 1.15, 1.6]), tabs.([0.8, 1.8, 4.2, 12.0]),
				tabs.([0.8, 0.3, 0.55, 0.45]), tabs.([0.6, 0.625, 0.68, 0.72]), tabs.([0.5, 1.0, 1.6, 3.0]),
				tabs.([96, 576, 1200, 2880]), [fb[0], fb[1]]);
			var out, mo2, l, r;
			LocalOut.ar(pl.clip2(4) ++ [wL, wR]);
			out = (ol * sd) + (((pl * 2) + ([rl, rr] * (tabs.([0.308, 0.448, 0.54, 0.871]) * eOn))) * ((sw * fade) * trim));
			Out.ar(\postbus.kr(0), out);                         // looper post-FX source
			// insert (default): MIX is a dry/wet and in bypass the dry stays where MIX puts it (unity up to half
			// way, nothing at full: a bus stays silent). aux: no direct dry on the return, ever
			out = Select.ar(\aux.kr(0), [out + (raw * ((1 - gI) * dg)), out - (xl * sd)]);
			out = out + (lp * (1 - pre));
			mo2 = (out[0] + out[1]) * 0.5;
			l = Select.ar(\omono.kr(0), [out[0], mo2]);
			r = Select.ar(\omono.kr(0), [out[1], mo2]);
			l = Select.ar(l.abs > 0.75, [l, l.sign * (0.75 + ((l.abs - 0.75) / (1 + ((l.abs - 0.75) * 2))))]).clip2(1);
			r = Select.ar(r.abs > 0.75, [r, r.sign * (0.75 + ((r.abs - 0.75) / (1 + ((r.abs - 0.75) * 2))))]).clip2(1);
			Out.ar(\out.kr(0), [l, r]);
		}).add;

		// ------------------------------------------------------------ looper
		SynthDef(\mcm_loop, {
			var sr = SampleRate.ir;
			var bL = \lbL.kr(0), bR = \lbR.kr(0), dL = \ldL.kr(0), dR = \ldR.kr(0);
			var src = Select.ar(\pre.kr(0), [In.ar(\postbus.kr(0), 2), In.ar(\inbus2.kr(0), 2)]);
			var rec = \rec.kr(0);
			var rise = Trig1.ar(K2A.ar(rec), 0.002);
			var fall = Trig1.ar(K2A.ar(1 - rec), 0.002);
			var el = Sweep.ar(rise, sr);                              // samples since the start of the take
			// QUANTIZE: qlen = length chosen at the close (0 = as played); longer than played = keep
			// recording and start the loop by itself when the take reaches it (qarm)
			var qT = \qlen.kr(0);
			var lenM = Latch.ar(el, fall);
			var len = Select.ar(qT > 0, [lenM, K2A.ar(qT)]).clip(2, BufFrames.kr(bL) - 1024);
			var run = (K2A.ar(rec) + Trig1.ar(fall, 0.01) + ((qT > 0) * (el < (qT + 544)))) > 0;   // + seam
			var tail = (len * 0.25).min(480);
			var goA = Trig1.ar((el >= qT) * (qT > 0) * \qarm.kr(0), 0.01);
			var go = T2A.ar(\t_go.tr(0)) + goA;
			var started = SetResetFF.ar(go, rise);
			var rv = \rev.kr(0);
			var spd = \spd.kr(1) * (1 - (2 * rv));
			var p = Phasor.ar(go, spd, 0, len, rv * (len - 1));
			var first = Trig1.ar(go, ((len + tail) / sr) / \spd.kr(1));
			var seam = (p < tail) * (first <= 0);
			var dubOn = \dubon.kr(0);
			var lay = [[bL, dL], [bR, dR]].collect { arg bb, c;
				var a = BufRd.ar(1, bb[0], p, 1, 2);
				var tl = BufRd.ar(1, bb[0], len + p, 1, 2);
				var base = Select.ar(seam, [a, (a * (p / tail)) + (tl * (1 - (p / tail)))]);
				var du = BufRd.ar(1, bb[1], p, 1, 1);
				// overdub: add the input to the dub layer where the playhead is (also clears it after UNDO)
				BufWr.ar((du * dubOn) + (src[c] * \dub.kr(0)), bb[1], p.floor);
				base + (du * dubOn)
			};
			// fade shape: 0 in + out, 1 fade in only (stop in 5 ms), 2 fade out only (start in 5 ms)
			var fadeT = \fade.kr(0.01);
			var shp = \lshape.kr(0);
			var lg = Slew.ar(K2A.ar(\lgt.kr(0)) * started, Select.kr(shp > 1.5, [1 / fadeT, 200]),
				Select.kr((shp > 0.5) * (shp < 1.5), [1 / fadeT, 200]));
			var lev = Lag.kr(\llev.kr(0), 0.02) * 1.4;
			RecordBuf.ar(src[0], bL, 0, 1, 0, run, 0, rise);
			RecordBuf.ar(src[1], bR, 0, 1, 0, run, 0, rise);
			Out.ar(\loopbus.kr(0), lay * (lg * lev) * (\play.kr(0) > 0));
		}).add;

		s.sync;

		// ------------------------------------------------------------ buffers, buses, nodes
		histL = Buffer.alloc(s, nb, 1);
		histR = Buffer.alloc(s, nb, 1);
		dlyL = Buffer.alloc(s, nb, 1);
		dlyR = Buffer.alloc(s, nb, 1);
		lbL = Buffer.alloc(s, (48000 * 61), 1);
		lbR = Buffer.alloc(s, (48000 * 61), 1);
		ldL = Buffer.alloc(s, (48000 * 61), 1);
		ldR = Buffer.alloc(s, (48000 * 61), 1);
		hwB = Bus.audio(s, 1);
		wetB = Bus.audio(s, 2);
		xB = Bus.audio(s, 2);
		dryB = Bus.audio(s, 2);
		rawB = Bus.audio(s, 2);
		gIB = Bus.audio(s, 1);
		inB2 = Bus.audio(s, 2);
		loopB = Bus.audio(s, 2);
		postB = Bus.audio(s, 2);
		hwK = Bus.control(s, 1);
		lfoK = Bus.control(s, 2);
		envK = Bus.control(s, 2);
		pkK = Bus.control(s, 1);
		s.sync;

		grpH = Group.new(context.xg, \addToHead);
		grpV = Group.new(grpH, \addAfter);
		grpP = Group.new(grpV, \addAfter);
		histS = Synth.new(\mcm_hist, [\in0, context.in_b[0].index, \in1, context.in_b[1].index,
			\bufL, histL.bufnum, \bufR, histR.bufnum, \loopbus, loopB.index, \wetbus, wetB.index,
			\hwbus, hwB.index, \hwk, hwK.index, \xbus, xB.index, \drybus, dryB.index, \inbus2, inB2.index,
			\rawbus, rawB.index, \gibus, gIB.index, \envk, envK.index, \lfok, lfoK.index, \pkk, pkK.index], grpH);
		delS = Synth.new(\mcm_delay, [\xbus, xB.index, \dbufL, dlyL.bufnum, \dbufR, dlyR.bufnum,
			\lfok, lfoK.index, \envk, envK.index, \out, wetB.index], grpP, \addToHead);
		outS = Synth.new(\mcm_out, [\wetbus, wetB.index, \drybus, dryB.index, \rawbus, rawB.index,
			\gibus, gIB.index, \loopbus, loopB.index, \postbus, postB.index, \lfok, lfoK.index,
			\out, context.out_b.index], delS, \addAfter);
		loopS = Synth.new(\mcm_loop, [\lbL, lbL.bufnum, \lbR, lbR.bufnum, \ldL, ldL.bufnum, \ldR, ldR.bufnum,
			\postbus, postB.index, \inbus2, inB2.index, \loopbus, loopB.index], grpP, \addToTail);

		// ------------------------------------------------------------ scheduler
		algo = 0; vari = 0; act = 0.5; rep = 0.5; shp = 10; shI = 0; beat = 24000; modDep = 0;
		voices = List.new;
		now = 0; curOff = 0; hwEst = 0; envS = 0; envFol = 0;
		onPos = Array.fill(8, 0); onCount = 0; onHead = 0; onNew = 0; onPend = 0;
		syncReq = false; subN = 0; lastDelay = nil; holdOn = false; errCount = 0;
		lst = 0; lrecT = 0; llen = 0; ldub = false; lrev = 0; lspd = 1; lfade = 0.01;
		fxRev = false; lonly = false; qlen = 0; lqPend = false; lqGen = 0;
		this.resetSched;
		onsetFunc = OSCFunc({ arg msg;
			onPos[onHead] = msg[3];
			onHead = (onHead + 1) % 8;
			onCount = (onCount + 1).min(8);
			onPend = 1;
		}, '/mcm_onset', s.addr);
		task = Routine({
			var tick = (bs * 4) / 48000;
			loop {
				var hwNow = hwK.getSynchronous;
				var ev = envK.getnSynchronous(2);
				now = thisThread.seconds;
				envS = ev[0];
				envFol = ev[1];
				this.prune;
				4.do({ arg i;
					curOff = (i * bs) / 48000;
					hwEst = (hwNow + ((lat + curOff) * 48000)) % nb;
					onNew = onPend;
					onPend = 0;
					subN = subN + 1;
					// a runtime error must not stop the scheduler: report it (a few times) and go on
					if(lonly.not, {
						try { this.sched } { arg err;
							errCount = errCount + 1;
							if(errCount < 4, { ("Microcosmo scheduler: " ++ err.errorString).postln });
						};
					});
					syncReq = false;
				});
				if((algo >= 9) and: { lonly.not }, { this.delaySetup(false) });
				if((lst == 1) and: { (now - lrecT) > 59.9 }, { this.loopClose(true) });   // 60 s at most
				tick.wait;
			}
		}).play(SystemClock);

		// ------------------------------------------------------------ commands
		this.addCommand(\preset, "ii", { arg msg;
			var a = msg[1].asInteger.clip(0, 10), v = msg[2].asInteger.clip(0, 3);
			if((a != algo) or: { v != vari }, {
				algo = a; vari = v;
				this.killAll;
				this.resetSched;
				histS.set(\hazefb, 0);
				outS.set(\interrupt, if(algo == 7, 1, 0), \duck, 0);
				if((algo >= 9) and: { lonly.not }, { this.delaySetup(true) }, { delS.set(\active, 0) });
			});
		});
		this.addCommand(\set, "sf", { arg msg;
			var k = msg[1].asSymbol, v = msg[2];
			switch(k,
				\act, { act = v.clip(0, 1) },
				\rep, { rep = v.clip(0, 1) },
				// SHAPE, as on the pedal: 0 square, 1 ramp, 2 triangle, 3 saw (shp = 10 + shI asks a new
				// voice for that contour; 0..1 would be a fixed window)
				\shp, { shI = (v.clip(0, 1) * 4).floor.asInteger.min(3); shp = 10 + shI },
				\beat, { beat = v.clip(1440, 192000); outS.set(\beat, beat) },
				\moddep, { modDep = v; histS.set(\moddep, v); outS.set(\moddep, v) },
				\hold, {
					// HOLD does not work while the looper records or plays (as on the pedal)
					if((v > 0.5) and: { (lst >= 1) and: { lst <= 3 } }, { v = 0 });
					if((v > 0.5) and: { holdOn.not }, { histS.set(\holdlen, (beat * 4).clip(24000, 384000)) });
					holdOn = v > 0.5;
					histS.set(\hold, v);
				},
				\lspd, { lspd = v.clip(0.25, 4); loopS.set(\spd, lspd); if((lspd != 1) and: { lst == 3 }, { this.loopDub(false) }) },
				\lrev, { lrev = v; loopS.set(\rev, v) },
				\lfade, { lfade = v.clip(0.005, 10.5); if(lst != 1, { loopS.set(\fade, lfade) }) },
				\qlen, { qlen = v.max(0) },
				\frev, { this.setRev(v > 0.5) },
				\lonly, {
					lonly = v > 0.5;
					outS.set(\lonly, if(lonly, 1, 0));
					if(lonly, { this.killAll; delS.set(\active, 0) }, { if(algo >= 9, { this.delaySetup(true) }) });
				},
				{ grpH.set(k, v); grpP.set(k, v) }
			);
		});
		// looper: 1 rec > play > dub, 2 stop / play, 3 erase, 4 undo
		this.addCommand(\loop, "i", { arg msg;
			switch(msg[1].asInteger,
				1, { this.loopRec },
				2, { this.loopStop },
				3, { this.loopErase },
				4, { this.loopUndo }
			);
		});
		// tap: restart the step counters on the tap; sync: beat from the norns clock
		this.addCommand(\tap, "", { stepCnt = 0 });
		this.addCommand(\sync, "", { syncReq = true });

		this.addPoll(\peak, { pkK.getSynchronous });
		this.addPoll(\lstate, { lst });
		this.addPoll(\llen, { if(lst == 1, { now - lrecT }, { llen }) });
	}

	// ================================================================ voices
	prune {
		voices = voices.reject({ arg v; v[\end] < now });
	}
	slotVoice { arg k;
		^voices.detect({ arg v; (v[\slot] == k) and: { v[\killed].not } })
	}
	kill { arg v;
		if(v.notNil and: { v[\killed].not }, {
			v[\killed] = true;
			v[\end] = now + curOff + lat + 0.01;
			context.server.makeBundle(lat + curOff, { v[\syn].set(\gate, 0) });
		});
	}
	killAll {
		voices.do({ arg v; this.kill(v) });
	}
	// back: frames behind the write head (or abs: absolute position in the history)
	// shape 10 + n: contour n (0 square, 1 ramp, 2 triangle, 3 saw; the make-up for the last three is added here);
	// cw = 1: HAZE grain, cw = 2: loop that also fades over its life (TUNNEL)
	spawn { arg back = 0, rate = 1, life = 4800, gain = 1, pan = 0, shape = 0.5, abs = -1,
		seg = 0, contour = 0, ft = 0, f0 = 1000, f1 = 1000, q = 1, cd = 0, bits = 16, decay = 1, slot = -1, cw = 0;
		var v, args, rv = 0, dir = 1, bkE, sh;
		life = life.asInteger;
		sh = (shape - 9.5).floor.asInteger.clip(0, 3);
		if(sh > 0, { gain = gain * 1.25 });
		// REVERSE: loops run backwards; one-shots read their stretch from the far end (the voice moves it
		// back in time if that end is not recorded yet), keeping clear of the oldest history
		if(fxRev, {
			dir = -1;
			if(seg <= 0, {
				rv = 1;
				if(rate > 0, {
					bkE = if(abs >= 0, { (hwEst - abs) % nb }, { back });
					bkE = (bkE - (rate * life)).max(96);
					life = life.min(((nb - 8192 - bkE) / (rate + 1)).floor).asInteger;
				});
			});
		});
		if((voices.size >= maxVoices) or: { life < 64 }, { ^nil });
		args = [\bufL, histL.bufnum, \bufR, histR.bufnum, \hwbus, hwB.index, \lfok, lfoK.index, \out, wetB.index,
			\back, back, \abs, abs, \rate, rate * dir, \rv, rv, \life, life, \gain, gain, \pan, pan.clip(-1, 1), \sh, sh,
			\seg, seg, \contour, contour, \ft, ft, \f0, f0, \flog, (f1 / f0).log2, \q, q, \cd, cd,
			\cq, 2 ** (bits - 1), \decay, decay, \cw, cw];
		v = (syn: nil, end: now + curOff + lat + (life / 48000) + 0.02, slot: slot, killed: false,
			loop: seg > 0, dir: dir, rate: rate * dir);
		context.server.makeBundle(lat + curOff, { v[\syn] = Synth.new(\mcm_voice, args, grpV, \addToTail) });
		voices.add(v);
		^v
	}
	// persistent looping voice: segment of len frames ending gap frames before the write head
	spawnLoop { arg len, gap, rate, life, gain, pan, shape, contour, decay = 1, slot = -1, abs = -1, ft = 0, f0 = 1000, q = 1, cw = 0;
		len = len.max(256).asInteger;
		^this.spawn(len + gap, rate, life, gain, pan, shape, abs, len, contour, ft, f0, f0, q, 0, 16, decay, slot, cw)
	}
	// REVERSE switched: looping voices turn around where they are, one-shots finish, the delay taps flip
	setRev { arg on;
		if(on != fxRev, {
			fxRev = on;
			voices.do({ arg v;
				if(v[\loop] and: { v[\killed].not }, {
					v[\dir] = v[\dir].neg;
					v[\rate] = v[\rate].neg;
					this.setV(v, \rate, v[\rate]);
				});
			});
			context.server.makeBundle(lat, { delS.set(\frev, if(on, 1, 0)) });
		});
	}
	setV { arg v ... pairs;
		if(v.notNil and: { v[\syn].notNil }, {
			context.server.makeBundle(lat + curOff, { v[\syn].set(*pairs) });
		});
	}

	onset { arg k;
		var idx;
		if(onCount <= 0, { ^0 });
		if(k >= onCount, { k = k % onCount });
		idx = (onHead - 1 - k) % 8;
		^onPos[idx]
	}
	beatFit { arg beats;
		var b = beat;
		while({ (b * beats) > 470000 }, { b = b * 0.5 });
		^b.asInteger
	}
	resetSched {
		stepCnt = 0; stepIdx = 0; barIdx = 0; chainG = 0; chainIdx = 0;
		burstLeft = 0; burstCnt = 0; burstOn = 0; burstStep = 0; intLeft = 0; intCnt = 0; intSrc = 0;
		duckT = 0; hazeAcc = 0; hazeLag = 0; glPh = 0; tunPh = 0;
		slotWait = Array.fill(maxVoices, { arg i; i * 2400 });
		perm = Array.fill(16, { arg i; i % 8 });
		gate = Array.fill(16, 1);
		anchor = hwEst;
	}
	newPattern {
		perm = Array.fill(16, { 8.rand });
		gate = Array.fill(16, { arg i; if(i.odd, { if(1.0.rand < 0.25, 1, 0) }, { if(1.0.rand < 0.8, 1, 0) }) });
		gate[0] = 1;
	}
	sched {
		switch(algo,
			0, { this.schedMosaic },
			1, { this.schedSeq },
			2, { this.schedGlide },
			3, { this.schedHaze },
			4, { this.schedTunnel },
			5, { this.schedStrum },
			6, { this.schedBlocks },
			7, { this.schedInterrupt },
			8, { this.schedArp }
		);
	}

	// ================================================================ MICRO LOOP
	schedMosaic {
		var sp = #[[1, 2, 1, 2], [1, 0.5, 1, 0.5], [2, 2, 2, 2], [0.5, 1, 2, 4]];
		var lm = #[1, 0.5, 0.5, 1, 0.25, 0.5];
		var n = 1 + (act * 5.99).floor;
		maxVoices.do({ arg k;
			var v = this.slotVoice(k);
			var s, len, iters, life, pan;
			if(k >= n, { if(v.notNil, { this.kill(v) }) }, {
				if(v.isNil, {
					if(slotWait[k] > 0, { slotWait[k] = slotWait[k] - bs }, {
						s = sp[vari][k % 4];
						len = (this.beatFit(1) * lm[k]).clip(1200, 96000).asInteger;
						iters = 1 + (rep * rep * 15).floor;
						life = (len / s).floor * iters;
						pan = if(k.odd, 1, -1) * (0.15 + (0.12 * k));
						this.spawnLoop(len, 300, s, life, 1.1 / (1 + (0.3 * (n - 1))), pan, shp, 1, 0.55 + (0.45 * rep), k);
						slotWait[k] = 0;
					});
				});
			});
		});
	}
	schedSeq {
		var step = (this.beatFit(4).div(4)).max(600);
		var j, nbar, on, start, rate, lifeMul, pan, f, lo, hi, life, ft, f0, f1, q, cd, bits, gain, v, lay = 0, gC = 0.8;
		if(syncReq, { stepCnt = if(stepCnt > (step / 2), { step - bs }, { 0 }) });
		stepCnt = stepCnt + bs;
		if(stepCnt < step, { ^this });
		stepCnt = stepCnt - step;
		j = stepIdx % 16;
		if(j == 0, {
			nbar = 1 + (rep * 3.99).floor;
			if((rep < 0.08) or: { (barIdx % nbar) == 0 }, { anchor = (hwEst - (step * 8) - 480) % nb; this.newPattern });
			barIdx = barIdx + 1;
		});
		stepIdx = stepIdx + 1;
		on = gate[j];
		if((vari == 3) and: { on == 0 } and: { j.odd } and: { 1.0.rand < act }, { on = 1 });
		if(on == 0, { ^this });
		if((rep < 0.08) or: { ((hwEst - anchor) % nb) > 400000 }, { anchor = (hwEst - (step * 8) - 480) % nb });
		start = (anchor + (step * perm[j])) % nb;
		rate = 1; lifeMul = 0.95;
		// B bounces between normal and half speed; ACTIVITY = how often: every bar, half bar, beat, eighth, sixteenth
		if((vari == 1) and: { ((stepIdx - 1).div(#[16, 8, 4, 2, 1][(act * 4.99).floor.asInteger.clip(0, 4)]) % 2) == 1 }, { rate = 0.5 });
		// C: ACTIVITY adds layers, up to three
		if(vari == 2, { lay = (act * 2.99).floor.asInteger.clip(0, 2); lifeMul = 1 + (act * 1.5) });
		// more and longer layers: each one a little softer
		gC = #[0.80, 0.515, 0.39][lay] + ((#[0.68, 0.459, 0.357][lay] - #[0.80, 0.515, 0.39][lay]) * ((act * 2.99) - lay));
		if(vari == 3, { lifeMul = 0.85 });
		pan = (1.0.rand - 0.5) * 1.2;
		life = step * lifeMul * if(j.odd, 1, 2);
		ft = 0; f0 = 1000; f1 = 1000; q = 1; cd = 0; bits = 16; gain = 0.8;
		if((vari == 0) and: { act > 0.03 }, {
			f = 250 * (2 ** (1.0.rand * act * 5.5));
			ft = if(2.rand == 1, 1, 2); f0 = f; f1 = f; q = 1.2 + (act * 3);
		});
		if(vari == 2, {
			lo = 300 + (300 * 1.0.rand); hi = 3000 + (5000 * act);
			ft = 1; q = 1.4;
			if((j.bitAnd(4)) != 0, { f0 = lo; f1 = hi }, { f0 = hi; f1 = lo });
			gain = gC;
		});
		if(vari == 3, { cd = 2 + 4.rand; bits = 6; gain = 0.8 * 1.4 });
		v = this.spawn(0, rate, life, gain, pan, shp, start, 0, 0, ft, f0, f1, q, cd, bits);
		if(v.isNil, { ^this });
		lay.do({ arg i;                                    // the added layers: other slices, sweeping the other way
			var n = i + 1;
			var st2 = (anchor + (step * perm[(j + (5 * n)) % 16])) % nb;
			var dn = ((j + n).bitAnd(4)) != 0;
			this.spawn(0, 1, step * lifeMul * 1.2, gC, if(n == 1, { pan.neg }, { pan * 0.3 }), shp, st2, 0, 0,
				1, if(dn, { hi }, { lo }), if(dn, { lo }, { hi }), 1.4);
		});
		if((vari == 3) and: { act > 0.9 } and: { (j % 4) == 0 }, {
			this.spawn(0, 0.5, step * 2, 0.6, pan.neg, shp, start, 0, 0, 0, 1000, 1000, 1, 4, 5);
		});
		if((vari == 1) and: { act > 0.9 } and: { (j % 8) == 0 }, {      // sustain pad layer
			this.spawn(0, 0.5, step * 16, 0.28, 0, 11, (start - step) % nb, 0, 0, 1, 1800, 1800, 0.8);   // pad: swells in (ramp)
		});
	}
	schedGlide {
		var lo = #[0.5, 0.5, 1, 0.5];
		var oc = #[1, 2, 1, 2];
		var f = 0.04 * (2 ** (act * 6.5));                 // glide rate 0.04..3.6 Hz
		// SHAPE = the glide pattern: square stays on a pitch, slides to the other, stays, slides back (in the
		// tutorial the pedal slides for about as long as it stays); ramp climbs and drops back, triangle
		// climbs and comes down, saw drops and climbs back
		var c = switch(shI, 1, { 0.97 }, 3, { 0.03 }, { 0.5 });
		var tri, len;
		glPh = (glPh + (f * (bs / 48000))) % 1;
		tri = if(glPh < c, { glPh / c }, { (1 - glPh) / (1 - c) });
		if(shI == 2, { tri = (tri * tri) * (3 - (2 * tri)) });
		if(shI == 0, { tri = ((2 * tri) - 0.5).clip(0, 1) });
		len = (this.beatFit(1).div(4)).clip(2400, 24000);
		4.do({ arg k;
			// B goes from double speed down to half (manual: "between double and half speed"; the tutorial's
			// memory card: x2 -> x1/2); D has two loops each way
			var l = if((vari == 1) or: { (vari == 3) and: { (k.bitAnd(2)) != 0 } }, { 1 - tri }, { tri });
			var rate = lo[vari] * (2 ** (l * oc[vari]));
			var v = this.slotVoice(k);
			var iters, life;
			if(v.notNil, {
				if((subN % 4) == 0, { v[\rate] = rate * v[\dir]; this.setV(v, \rate, v[\rate]) });
			}, {
				if(slotWait[k] > 0, { slotWait[k] = slotWait[k] - bs }, {
					iters = 2 + (rep * rep * 14).floor;
					life = ((len * iters) / rate).min(480000);
					this.spawnLoop(len, 300, rate, life, 0.5, if(k.odd, 0.6, -0.6), 10, 0, 1, k);
					slotWait[k] = len.div(2);
				});
			});
		});
	}

	// ================================================================ GRANULES
	schedHaze {
		var gps = 3 + (act * act * 50);
		var dmin = 0.06, dmax = 0.25, spread = 0.03 + act;
		var dur, rate, ov, gain, back;
		if(vari == 0, { gps = gps * 0.6; dmin = 0.12; dmax = 0.24; spread = 0.03 + (act * 0.25) });
		if(vari == 1, { gps = gps * 1.25; dmin = 0.04; dmax = 0.30; spread = 0.05 + (act * 1.5) });
		if((subN % 8) == 0, { histS.set(\hazefb, rep * 0.78) });
		// A is "stretched, overlapping samples": the grains walk through the last moments at half speed and start over
		hazeLag = hazeLag + (bs / 2);
		if(hazeLag > (spread * 48000), { hazeLag = 0 });
		hazeAcc = hazeAcc + (gps * (bs / 48000) * (0.5 + 1.0.rand));
		while({ hazeAcc >= 1 }, {
			hazeAcc = hazeAcc - 1;
			dur = dmin + ((dmax - dmin) * 1.0.rand);
			rate = 1;
			if(vari == 0, { rate = 1 + ((1.0.rand - 0.5) * 0.012) });
			if((vari == 2) and: { 2.rand == 1 }, { rate = 2 });
			if((vari == 3) and: { 2.rand == 1 }, { rate = 0.5 });
			ov = gps * (dmin + dmax) * 0.5;
			gain = (1.45 / (1 + (ov * 0.3))) * hzK[shI];
			back = ((0.01 + (spread * 1.0.rand)) * 48000).asInteger;
			if(vari == 0, { back = 480 + hazeLag.asInteger + 288.rand });
			this.spawn(back, rate, dur * 48000, gain, (1.0.rand - 0.5) * if(vari == 1, 1.8, 1.1), shp, cw: 1);
		});
	}
	schedTunnel {
		var l0 = (this.beatFit(1) * 0.125).clip(960, 12000);   // micro loop: a 32nd note, 20..250 ms
		var envN = (envFol * 8).min(1);
		var gap = this.beatFit(2);
		var trig, k, old, decay, rate, v, f, sc;
		tunPh = (tunPh + (bs / (this.beatFit(8) * 8))) % 1;
		// modifiers on the running drones (every fourth pass)
		if((subN % 4) == 0, {
			voices.do({ arg dv;
				var sl = dv[\slot], ln;
				if(dv[\killed].not and: { sl >= 0 } and: { sl <= 3 }, {
					ln = l0;
					if(vari == 0, { ln = l0 * (1 + ((act * 0.6) * (((tunPh + (0.25 * sl)) * 2pi).sin))) });
					if(vari == 3, { ln = l0 * (1 - ((act * 0.75) * envN)) });
					if((vari == 0) or: { vari == 3 }, { this.setV(dv, \seg, ln.max(256)) });
					if(vari == 1, {
						this.setV(dv, \f0, 250 * (2 ** (((act * 4.5) * (0.5 + (0.5 * ((((tunPh * 2) + (0.3 * sl)) * 2pi).sin)))) + 0.5)), \flog, 0);
					});
				});
			});
		});
		// a new drone on every onset, or every 2 beats while there is signal
		stepCnt = stepCnt + bs;
		trig = ((onNew > 0) and: { stepCnt > (gap / 4) }) or: { (stepCnt > (gap * 2)) and: { envS > 0.004 } };
		if(trig.not, { ^this });
		stepCnt = 0;
		k = chainIdx % 4;
		chainIdx = chainIdx + 1;
		old = this.slotVoice(k);
		if(old.notNil, { this.kill(old) });
		decay = 0.6 + (rep * rep * 20);
		rate = if(vari == 1, 0.5, 1);
		if(vari == 2, {
			sc = #[220, 330, 440, 660, 880, 1320];
			f = sc[6.rand] * if(2.rand == 1, 1, 2);
			this.spawnLoop(l0, 400, rate, decay * 48000, 0.8 * (2.6 + (act * 2)), if(k.odd, 0.55, -0.55), shp, 1, 1, k, -1, 2, f, 2 + (act * 18), 2);
		}, {
			this.spawnLoop(l0, 400, rate, decay * 48000, if(vari == 3, 1.2, 0.8), if(k.odd, 0.55, -0.55), shp, 1, 1, k, -1,
				if(vari == 1, 1, 0), 600, 1.3, 2);
		});
	}
	schedStrum {
		var spb = #[1, 2, 3, 4, 6, 8];
		var step = (this.beatFit(1).div(spb[(act * 5.99).floor.asInteger])).max(960);
		var dur, k, abs, pan, rate;
		if(onNew > 0, { chainG = 1; chainIdx = 0 });
		if(syncReq, { stepCnt = if(stepCnt > (step / 2), { step - bs }, { 0 }) });
		stepCnt = stepCnt + bs;
		if(stepCnt < step, { ^this });
		stepCnt = stepCnt - step;
		if((chainG < 0.01) or: { onCount == 0 }, { ^this });
		dur = (step * if(vari == 1, 3, 1.6)).min(18000);
		k = if(vari >= 2, { chainIdx % onCount.min(4) }, { 0 });
		abs = (this.onset(k) - 144) % nb;
		pan = if(chainIdx.odd, 0.45, -0.45);
		rate = if((vari == 3) and: { chainIdx.odd }, 2, 1);
		this.spawn(0, rate, dur, 0.8 * chainG, pan, shp, abs);
		if(vari == 1, {
			this.spawn(0, 1.003, dur, 0.55 * chainG, pan.neg, shp, (abs - 432) % nb);
			this.spawn(0, 0.997, dur, 0.55 * chainG, pan * 0.3, shp, (abs - 816) % nb);
		});
		chainIdx = chainIdx + 1;
		chainG = chainG * (0.55 + (0.45 * rep));
	}

	// ================================================================ GLITCH
	schedBlocks {
		var step = (this.beatFit(1).div(4)).max(720);
		var ord = #[0, 0, 1, 0, 2, 1, 0, 3];
		var rs = #[1, 2, 0.5, 1.5, 0.75];
		var i, k, abs, back, rate, lifeMul, gain, ratchet, ft, cd;
		if((onNew > 0) and: { burstOn == 0 } and: { 1.0.rand < (0.25 + (0.75 * rep)) }, {
			burstOn = 1; burstLeft = 2 + (act * 6).floor; burstCnt = step; burstStep = 0;
		});
		if((burstOn == 0) and: { rep > 0.8 } and: { envS > 0.004 }, {
			barIdx = barIdx + bs;
			if(barIdx > (step * 8), { barIdx = 0; burstOn = 1; burstLeft = 2 + (act * 6).floor; burstCnt = step; burstStep = 0 });
		});
		if(burstOn == 0, { ^this });
		burstCnt = burstCnt + bs;
		if(burstCnt < step, { ^this });
		burstCnt = burstCnt - step;
		i = burstStep;
		burstStep = burstStep + 1;
		burstLeft = burstLeft - 1;
		if(burstLeft <= 0, { burstOn = 0 });
		k = if(act < 0.3, { ord[i % 8] }, { 4.rand });
		if(onCount == 0, { abs = -1; back = step * 2 }, { abs = (this.onset(k) - 96) % nb; back = 0 });
		rate = 1;
		if(((vari == 1) or: { vari == 3 }) and: { 1.0.rand < (0.3 + (0.7 * act)) }, { rate = rs[5.rand] });
		lifeMul = if(vari == 2, 2.5, 0.9);
		gain = if(vari == 2, { (0.75 * (1 - (0.1 * i))).max(0.1) }, { 0.8 });
		ratchet = (vari == 0) and: { (i % 4) == 3 } and: { act > 0.5 };
		ft = if(vari == 2, 1, 0);
		cd = if(vari == 3, 3, 0);
		if(ratchet, {                                       // the same slice twice in one step
			this.spawn(back, 1, step, gain, (1.0.rand - 0.5) * 1.2, shp, abs, step.div(2).max(256), 1);
		}, {
			this.spawn(back, rate, step * lifeMul, gain, (1.0.rand - 0.5) * 1.2, shp, abs, 0, 0, ft, 1400, 700, 0.8, cd, 6);
		});
	}
	schedInterrupt {
		var step = (this.beatFit(1).div(4)).max(720);
		var rs1 = #[2, 0.5, 1.5, 0.75, 1.335];
		var rs3 = #[4, 0.25, 2, -1, 0.5];
		var i, src, rate, abs, f0, cd;
		if(syncReq, { stepCnt = if(stepCnt > (step / 2), { step - bs }, { 0 }) });
		stepCnt = stepCnt + bs;
		if(stepCnt < step, { ^this });
		stepCnt = stepCnt - step;
		stepIdx = stepIdx + 1;
		if(intLeft <= 0, {
			duckT = 0;
			if(stepIdx.even and: { 1.0.rand < (rep * rep * 0.7) }, {
				intLeft = 2 * (1 + (1.0.rand * (1 + (act * 3))).floor);
				intCnt = 0;
				intSrc = (hwEst - (step * 2) - 64) % nb;
			}, {
				this.setDuck(0);
				^this
			});
		});
		duckT = 1;
		this.setDuck(1);
		intLeft = intLeft - 1;
		i = intCnt;
		intCnt = intCnt + 1;
		src = intSrc;
		if((act > 0.4) and: { 1.0.rand < (act * 0.5) }, { src = (hwEst - (step * (1 + 6.rand))) % nb });
		rate = 1;
		if(vari == 1, { rate = rs1[5.rand] });
		if(vari == 3, { rate = rs3[5.rand] });
		if((vari == 0) and: { 1.0.rand < (act * 0.3) }, { rate = -1 });
		abs = if(rate < 0, { (src + step - 64) % nb }, { src });
		cd = if(vari == 3, { 2 + 5.rand }, { 0 });
		if(vari == 2, {
			f0 = 7000 * (2 ** ((i * 0.7).neg));
			this.spawn(0, rate, step, 0.85, (1.0.rand - 0.5) * 0.8, 10, abs, 0, 0, 1, f0, f0 * 0.6, 2.5);
			this.spawn(0, rate, step, 0.45, 0.7, 10, (abs - (step * 3)) % nb, 0, 0, 1, f0 * 0.5, f0 * 0.3, 2);
		}, {
			this.spawn(0, rate, step, 0.85, (1.0.rand - 0.5) * 0.8, 10, abs, 0, 0, 0, 1000, 1000, 1, cd, 5);
		});
	}
	setDuck { arg v;
		context.server.makeBundle(lat + curOff, { outS.set(\duck, v) });
	}
	schedArp {
		var step = (this.beatFit(1).div(4)).max(720);
		var rs = #[1, 2, 1.5, 0.5, 1.335, 2, 0.75, 1];
		var n, j, k, abs, rate, pan, f, ft, cd;
		if(onNew > 0, { chainG = 1 });
		if(syncReq, { stepCnt = if(stepCnt > (step / 2), { step - bs }, { 0 }) });
		stepCnt = stepCnt + bs;
		if(stepCnt < step, { ^this });
		stepCnt = stepCnt - step;
		if((onCount == 0) or: { chainG < 0.01 }, { ^this });
		n = 2 + (act * 6.99).floor;
		j = stepIdx % n;
		stepIdx = stepIdx + 1;
		if(j == (n - 1), { chainG = chainG * (0.65 + (0.35 * rep)) });
		k = n - 1 - j;
		abs = (this.onset(k) - 96) % nb;
		rate = if(vari == 1, { rs[j % 8] }, { 1 });
		pan = ((j / (n - 1)) - 0.5) * 1.4;
		ft = 0; f = 1000; cd = 0;
		if(vari == 2, { f = 300 * (2 ** (1.0.rand * 5)); ft = if(2.rand == 1, 1, 2) });
		if(vari == 3, { cd = 2 + 4.rand });
		this.spawn(0, rate, step * 0.85, 0.8 * chainG, pan, shp, abs, 0, 0, ft, f, f, 2 + (1.0.rand * 4), cd, 6);
	}

	// ================================================================ MULTIDELAY setup
	delaySetup { arg init;
		var pat = #[[0.75, 1, 1.5, 1.75, 0.25, 1.25], [0.6667, 1.3333, 2, 1, 2.3333, 2.6667], [1.5, 0.5, 2.75, 3.25, 1, 3.75]];
		var plen = #[2, 3, 4];
		var semi = #[0, 12, 7, 12, 19, 24];
		var nTap = 1 + (act * 5.99).floor;
		var b, p, tT, tG, tPr, fmode, cfg;
		if((algo == 9) and: { vari > 0 }, {
			b = this.beatFit(plen[vari - 1]);
			p = plen[vari - 1] * b;
			tT = pat[vari - 1].collect({ arg m; m * b });
		}, {
			b = this.beatFit((0.5 * nTap) + 0.5);
			tT = Array.fill(6, { arg k; 0.5 * (k + 1) * b });
			p = tT[nTap - 1];
		});
		// SHAPE = level contour over the taps: square a plain delay (every tap a little softer, as the pedal's
		// taps are in the tutorial), ramp growing, triangle with the middle taps in front, saw fading away;
		// the loudest tap always stays at full level
		tG = Array.fill(6, { arg k;
			var q = switch(shI, 1, { 1 - ((k + 1) / nTap) }, 2, { ((((2 * k) + 1) / nTap) - 1).abs }, 3, { k / nTap }, { (0.6 * k) / nTap });
			var g = 1 - (q.max(0) * 0.85);
			if(k < nTap, { (g * 0.8) / (1 + (0.25 * (nTap - 1))) }, { 0 })
		});
		tPr = Array.fill(6, { arg k;
			if((algo == 10) and: { vari == 2 }, { 2 ** (semi[k] / 12) }, { if((algo == 10) and: { vari == 3 }, 2, 1) })
		});
		fmode = if(algo == 10, { if(vari == 0, 1, { if(vari == 1, 2, 0) }) }, { 0 });
		cfg = [tT, tG, tPr, nTap, p, rep * 0.95, fmode, if((algo == 10) and: { vari == 3 }, 1, 0), shI, if(algo == 10, 1, 0)];
		if(init or: { cfg != lastDelay }, {
			lastDelay = cfg;
			context.server.makeBundle(lat, {
				delS.setn(\tt, tT, \tg, tG, \tpr, tPr);
				delS.set(\ntap, nTap, \fbt, p, \dfb, rep * 0.95, \fmode, fmode, \warp3, cfg[7],
					\iswarp, cfg[9], \active, 1);
				if(init, { delS.set(\t_init, 1) });
			});
		});
	}

	// ================================================================ looper
	loopClose { arg play;
		var e = (now - lrecT) * 48000, t, g;
		if(lqPend, { ^this });                                   // already waiting for the quantized end
		// QUANTIZE: the length goes to the nearest quarter note; longer than played = keep recording,
		// the looper synth starts the loop by itself exactly there
		if((qlen > 0) and: { e >= 4800 }, {
			t = (e / qlen).round.max(1) * qlen;
			while({ t > (48000 * 60) }, { t = t - qlen });
			if(t > 0, {
				if(t > e, {
					lqPend = true;
					lqGen = lqGen + 1;
					g = lqGen;
					loopS.set(\rec, 0, \qlen, t, \qarm, 1, \fade, 0.005, \lgt, if(play, 1, 0), \play, 1);
					SystemClock.sched(((t - e) / 48000) + lat, {
						if(lqPend and: { g == lqGen }, {
							lqPend = false;
							llen = t / 48000;
							lst = if(play, 2, 4);
							loopS.set(\qarm, 0, \fade, lfade);
						});
						nil
					});
				}, {
					llen = t / 48000;
					lst = if(play, 2, 4);
					loopS.set(\rec, 0, \qlen, t, \qarm, 0, \fade, 0.005, \lgt, if(play, 1, 0), \play, 1, \t_go, 1);
					SystemClock.sched(0.05, { loopS.set(\fade, lfade); nil });
				});
				^this
			});
		});
		llen = now - lrecT;
		loopS.set(\rec, 0);
		if(llen < 0.1, { lst = 0; llen = 0; loopS.set(\play, 0, \lgt, 0); ^this });
		lst = if(play, 2, 4);
		// first fade-in is fast (5 ms), then the LOOP FADE time
		loopS.set(\fade, 0.005, \lgt, if(play, 1, 0), \play, 1, \t_go, 1);
		SystemClock.sched(0.05, { loopS.set(\fade, lfade); nil });
	}
	loopRec {
		switch(lst,
			0, {
				this.holdOff;
				if(qlen > 0, { stepCnt = 0 });                       // QUANTIZE: effect and loop start together
				lst = 1; lrecT = now; ldub = false;
				ldL.zero; ldR.zero;
				loopS.set(\dubon, 0, \dub, 0, \play, 0, \lgt, 0, \qlen, 0, \qarm, 0, \rec, 1);
			},
			1, { this.loopClose(true) },
			2, { if(lspd == 1, { this.loopDub(true) }) },
			3, { this.loopDub(false) },
			4, { this.holdOff; lst = 2; loopS.set(\lgt, 1, \t_go, 1) }
		);
	}
	// starting the looper ends HOLD (as on the pedal)
	holdOff {
		if(holdOn, { holdOn = false; histS.set(\hold, 0) });
	}
	loopDub { arg on;
		if(on, {
			lst = 3; ldub = true;
			loopS.set(\dubon, 1, \dub, 1);
		}, {
			if(lst == 3, { lst = 2 });
			loopS.set(\dub, 0);
		});
	}
	loopStop {
		switch(lst,
			1, { this.loopClose(false) },
			2, { lst = 4; loopS.set(\lgt, 0, \dub, 0) },
			3, { lst = 4; loopS.set(\lgt, 0, \dub, 0) },
			4, { this.holdOff; lst = 2; loopS.set(\lgt, 1, \t_go, 1) }
		);
	}
	loopErase {
		lst = 0; llen = 0; ldub = false;
		lqPend = false; lqGen = lqGen + 1;
		loopS.set(\rec, 0, \play, 0, \lgt, 0, \dub, 0, \dubon, 0, \qlen, 0, \qarm, 0);
		ldL.zero; ldR.zero;
	}
	loopUndo {
		if(ldub, {
			ldub = false;
			if(lst == 3, { lst = 2 });
			loopS.set(\dub, 0, \dubon, 0);
			ldL.zero; ldR.zero;
		});
	}

	free {
		if(task.notNil, { task.stop });
		if(onsetFunc.notNil, { onsetFunc.free });
		[histS, delS, outS, loopS].do({ arg n; if(n.notNil, { n.free }) });
		[grpH, grpV, grpP].do({ arg g; if(g.notNil, { g.free }) });
		[histL, histR, dlyL, dlyR, lbL, lbR, ldL, ldR, hwB, wetB, xB, dryB, rawB, gIB, inB2, loopB, postB,
			hwK, lfoK, envK, pkK].do({ arg b; if(b.notNil, { b.free }) });
	}
}
