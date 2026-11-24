// Engine_GillsChroma: four effect modules in series, five effects each, in any order.
// Port of the Ksoloti Gills "chroma console" patch.
//   CHARACTER : DRIVE SWEETEN FUZZ HOWL SWELL
//   MOVEMENT  : DOUBLER VIBRATO PHASER TREMOLO PITCH
//   DIFFUSION : CASCADE REELS SPACE COLLAGE REVERSE
//   TEXTURE   : FILTER SQUASH CASSETTE BROKEN INTERFERENCE
// Each effect is its own SynthDef working in place on a stereo chain bus; the order of the
// four module nodes is the order of the chain. Switching an effect cross-fades the old node
// out and the new one in. CAPTURE (30 s looper / sustainer) before or after the chain,
// bypass with trails, aux (send/return) or insert routing, LFO locked to the beat.
// Only core SuperCollider UGens are used.

Engine_GillsChroma : CroneEngine {
	var <preG, <modG, <postG, <cb, <db, <rb, <pb, <gIB, <capB, <lfoB, <gB, <drB, <pkB;
	var <capL, <capR, <inSyn, <lfoSyn, <outSyn, <capSyn, <mods, <fx, <ord, <state, <modState, <names;

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
		var capFrames = (48000 * 30) + 1024;

		// ------------------------------------------------------------ module wrapper
		// in place on the chain bus: out = x + (fx(x) * vol - x) * g, g = on/off and switch fade
		var mk = { arg name, m, func;
			SynthDef(name, {
				var bus = \bus.kr(0);
				var x = In.ar(bus, 2);
				var env = EnvGen.kr(Env.asr(0.02, 1, 0.02), \gate.kr(1), doneAction: 2);
				var g = env * Lag.kr(\on.kr(1), 0.02);
				var y = func.value(x);
				var v = if(m == 2, { 1 }, { \vol.kr(0.5) * 2 });
				ReplaceOut.ar(bus, x + (((y * v) - x) * g));
				Out.kr(\gbus.kr(0), g);
			}).add;
		};
		// shared pieces
		var pre = { 2 ** ((\sens.kr(0.5) - 0.5) * 5) };
		var tiltEQ = { arg y, fc;
			var t = (\tilt.kr(0.5) - 0.5) * 2;
			var lo = OnePole.ar(y, exp((-2pi * fc) / SampleRate.ir));
			(lo * (2 ** (t.neg * 1.5))) + ((y - lo) * (2 ** (t * 1.5)))
		};
		var lp1 = { arg fc; var w = (2pi * fc) / SampleRate.ir; 1 - (w / (1 + w)) };   // OnePole coef
		// tape pieces after Airwindows (Chris Johnson, MIT licence), as on the Gills:
		// awFlut: wobbles whose speed is drawn again at random (0.24..0.98 of hz) at every cycle
		// and glides there, the depth following the speed squared (Flutter / ToTape); one per hz
		// given, +-2 at most, rms as a plain sine of depth 1 (uses the synth's control LocalIn)
		var awFlut = { arg hz;
			var rIn = LocalIn.kr(hz.size).asArray;
			var ph = hz.collect { arg h, i; Phasor.ar(0, (rIn[i] * h) / SampleRate.ir, 0, 1) };
			var r = hz.collect { arg h, i; Lag.kr(TRand.kr(0.24, 0.98, HPZ1.kr(A2K.kr(ph[i])) < 0), 1.1 / h) };
			LocalOut.kr(r);
			hz.collect { arg h, i; ((r[i] * r[i]) * 2) * (ph[i] * 2pi).sin }
		};
		// awSoft: the "soften" of ToTape, highs pulled down by 1 - cos(|highs| pi/2) (coef: OnePole)
		var awSoft = { arg x, coef, amt;
			var lo = OnePole.ar(x, coef);
			var hi = x - lo;
			lo + (hi * (1 - ((1 - (hi.abs * 0.5pi).min(0.5pi).cos) * amt)))
		};
		// awSat: sin() up to +-pi/2, flat beyond (Tape / ToTape)
		var awSat = { arg x; x.clip2(0.5pi).sin };
		var envF = { arg x; Amplitude.ar(((x[0].abs) + (x[1].abs)) * 0.5, 0.0024, 0.08) };
		var timeS = { Lag.kr(\time.kr(0.5), 0.01) };
		var rateS = { Lag.kr(\rate.kr(0.5), 0.006) };
		// routing: 0 insert (modules in series, as on the pedal), 1 aux (wet-only chain, never any dry),
		// 2 mix (default: the wet-only chain plus a real dry/wet at the end). Inside the modules 1 and 2 are the same
		var aux = { \aux.kr(2).min(1) };
		// two DRIFT controls, as on the pedal: one for Movement, one for Diffusion
		var driftM = { \driftm.kr(0) };
		var driftD = { \driftd.kr(0) };
		var lfo = { In.ar(\lfobus.kr(0)) };                 // movement LFO phase 0..1
		var dr = { In.kr(\drbus.kr(0)) };                    // slow random drift, already x DRIFT
		var tempo = { \tempo.kr(0) };
		var beatS = { \beat.kr(0.5) * SampleRate.ir };       // one quarter note in samples
		var dtime = {                                       // diffusion delay, samples
			Select.kr(tempo.value, [1440 * (2 ** (timeS.value * 5.3)), beatS.value * \tdiv.kr(1)]).min(120000)
		};

		names = [
			[\chr_drive, \chr_sweeten, \chr_fuzz, \chr_howl, \chr_swell],
			[\chr_doubler, \chr_vibrato, \chr_phaser, \chr_tremolo, \chr_pitch],
			[\chr_cascade, \chr_reels, \chr_space, \chr_collage, \chr_reverse],
			[\chr_filter, \chr_squash, \chr_cassette, \chr_broken, \chr_interf]
		];

		// ============================================================ CHARACTER
		mk.(\chr_drive, 0, { arg x;
			// half of the TILT comes before the saturation, so it also changes what distorts
			var camt = \amt.kr(0.5);
			var xp = x * pre.value;
			var hp = OnePole.ar(xp, 0.991);
			var t = (\tilt.kr(0.5) - 0.5) * 2;
			var d0 = xp - hp;
			var lo = OnePole.ar(d0, lp1.(700));
			var d = (lo * (2 ** (t.neg * 0.75))) + ((d0 - lo) * (2 ** (t * 0.75)));
			var y = (((d * (1 + ((camt * camt) * 40))) + 0.15).tanh - 0.149) * (0.8 / (1 + (camt * 4.5)));
			tiltEQ.(OnePole.ar(y, 0.45), 700)
		});
		mk.(\chr_sweeten, 0, { arg x;
			var camt = \amt.kr(0.5);
			var xp = x * pre.value;
			var e = envF.(x);
			var thr = 0.3 - (camt * 0.24);
			var g = ((thr + ((e - thr) * 0.33)) / e.max(0.0001)).min(1);
			var cmp = OnePole.ar(g, 0.998);
			tiltEQ.((xp * cmp * (1 + (camt * 1.5))).tanh * (0.75 + (camt * 0.1)), 700)
		});
		mk.(\chr_fuzz, 0, { arg x;
			var camt = \amt.kr(0.5);
			var xp = x * pre.value;
			var hp = OnePole.ar(xp, 0.991);
			var bias = (\tilt.kr(0.5) - 0.5) * 0.6;
			var y = ((((xp - hp) * (20 + ((camt * camt) * 300))) + bias).tanh - bias.tanh) * 0.17;
			tiltEQ.(OnePole.ar(y, 0.62), 700)
		});
		mk.(\chr_howl, 0, { arg x;
			// envelope-triggered resonant sweep: the louder the attack, the higher it howls
			var camt = \amt.kr(0.5);
			var xp = x * pre.value;
			var e = envF.(x);
			var dec = 1 / (1.2 * (2 ** (\tilt.kr(0.5).neg * 5.5)));
			var hw = Slew.ar((e * 4).min(1), 100000, dec);
			var fc = (180 * (2 ** ((A2K.kr(hw) * 7) * (0.6 + camt)))).clip(20, 20000);
			var f = (xp * (30 + (camt * 200))).tanh * 0.5;
			tiltEQ.(RLPF.ar(f, fc, 1 / (3 + (camt * 9))) * 0.19, 700)
		});
		mk.(\chr_swell, 0, { arg x;
			// auto-swell: every new attack fades in from silence (the gain first goes down in 5 ms,
			// so a note played over a ringing one does not click)
			var camt = \amt.kr(0.5);
			var xp = x * pre.value;
			var a = ((x[0].abs) + (x[1].abs)) * 0.5;
			var e = Amplitude.ar(a, 0.0024, 0.08);
			var es = Amplitude.ar(a, 0.032, 0.24);
			var thr = 0.0015 * (2 ** ((1 - \sens.kr(0.5)) * 6));
			var att = 0.02 * (2 ** (camt * 7));
			var onset = Trig1.ar(e > ((es * 1.7) + thr), 0.1);
			var g = EnvGen.ar(Env([1, 0, 1], [0.005, att]), onset) * Slew.ar(es > (thr * 0.5), 100000, 0.5 / att);
			tiltEQ.(xp * (g * g), 700)
		});

		// ============================================================ MOVEMENT
		mk.(\chr_doubler, 1, { arg x;
			// RATE: from tight doubling (8 ms) to slapback (128 ms); the right side 1.37 times later
			var mamt = \amt.kr(0.5);
			// DRIFT: each tap jumps to a new place every 0.15 .. 0.6 s and glides there in about 80 ms:
			// random momentary pitch shifts
			var base = 0.008 * (2 ** (rateS.value * 4));
			var m = (SinOsc.ar(0.27) * 24) / SampleRate.ir;
			var jump = TDuty.kr(Dwhite(0.15, 0.6));
			var off = [0, 1].collect { OnePole.ar(K2A.ar(TRand.kr(-1, 1, jump) * (driftM.value * 160)), 0.99974) / SampleRate.ir };
			var a = DelayC.ar(x[1], 0.2, base + m + off[0]);
			var b = DelayC.ar(x[0], 0.2, ((base * 1.37) - (m * 0.8)) + off[1]);
			var kd = (1 - aux.value) * (1 - (0.3 * mamt));
			[(x[0] * kd) + (a * mamt), (x[1] * kd) + (b * mamt)]
		});
		mk.(\chr_vibrato, 1, { arg x;
			// DRIFT bends the sine toward a wandering random wave (a new target every LFO cycle)
			// and moves the right side up to a quarter of a cycle away: stereo spread
			var mamt = \amt.kr(0.5);
			var drf = driftM.value;
			var ph = lfo.value;
			var wrap = HPZ1.ar(ph) < 0;
			var hz = Select.kr(tempo.value, [0.05 * (2 ** (rateS.value * 8)), \rdiv.kr(1) / \beat.kr(0.5)]);
			var coef = (1 - ((4 * hz) / SampleRate.ir)).clip(0, 0.99999);
			[0, 1].collect { arg c;
				var w0 = ((ph + (c * drf * 0.25)) * 2pi).sin;
				var rnd = OnePole.ar(TRand.ar(-1, 1, wrap), coef);
				var w = w0 + (drf * (rnd - w0));
				DelayC.ar(x[c], 0.02, (2 + ((mamt * 6) * (0.5 + (0.5 * w)))) / 1000)
			}
		});
		mk.(\chr_phaser, 1, { arg x;
			// 2 to 12 first-order all-pass stages swept by the LFO (right channel 90 degrees later);
			// DRIFT bends the sweep toward a wandering random wave
			var mamt = \amt.kr(0.5);
			var drf = driftM.value;
			var ph = A2K.kr(lfo.value);
			var wrapK = HPZ1.kr(ph) < 0;
			var hz = Select.kr(tempo.value, [0.05 * (2 ** (rateS.value * 8)), \rdiv.kr(1) / \beat.kr(0.5)]);
			var coefK = (1 - ((4 * hz * BlockSize.ir) / SampleRate.ir)).clip(0, 0.99999);
			var nst = ((mamt * 5) + 0.5).floor;          // 0..5 -> 2..12 stages
			var y = [0, 1].collect { arg c;
				var w0 = ((ph + (c * 0.25)) * 2pi).sin;
				var rnd = OnePole.kr(TRand.kr(-1, 1, wrapK), coefK);
				var sv = 0.5 + (0.5 * (w0 + ((drf * 0.7) * (rnd - w0))));
				var f = 200 * (2 ** (sv * 4));
				var g = (pi * f / SampleRate.ir).tan;
				var a = (1 - g) / (1 + g);
				var v = x[c];
				var taps = [];
				12.do { arg k;
					v = FOS.ar(v, a.neg, 1, a);
					if(k.odd, { taps = taps.add(v) });
				};
				Select.ar(nst, taps)
			};
			[0, 1].collect { arg c;
				Select.ar(aux.value, [((x[c] + y[c]) * 0.5) * 1.3, y[c] * 0.65])
			}
		});
		mk.(\chr_tremolo, 1, { arg x;
			// AMOUNT: from a soft shimmer (sine) to a square chop; DRIFT bends the wave toward a
			// wandering random one, so the dips differ
			var mamt = \amt.kr(0.5);
			var drf = driftM.value;
			var k = 1 + (12 * mamt * mamt);
			var ph = lfo.value;
			var hz = Select.kr(tempo.value, [0.05 * (2 ** (rateS.value * 8)), \rdiv.kr(1) / \beat.kr(0.5)]);
			var rnd = OnePole.ar(TRand.ar(-1, 1, HPZ1.ar(ph) < 0), (1 - ((4 * hz) / SampleRate.ir)).clip(0, 0.99999));
			var w0 = (ph * 2pi).sin;
			var w = w0 + ((drf * 0.7) * (rnd - w0));
			var s = 0.5 + (0.5 * ((k * w).tanh / k.tanh));
			x * (1 - ((mamt * s) * (1 + (mamt * 0.3)))).max(0)
		});
		mk.(\chr_pitch, 1, { arg x;
			// RATE is continuous, an octave down to an octave up, no shift in a small zone around the
			// centre; AMOUNT is dry / wet (all wet at full); DRIFT is lo-fi: the shifted voice is held
			// for 1..8 samples (48 kHz down to 6 kHz) and its pitch wanders
			var mamt = \amt.kr(0.5);
			var pu = (rateS.value - 0.5) * 2;
			var semi = (pu.sign * 12) * ((pu.abs - 0.05) / 0.95).max(0);
			var pr = 2 ** ((semi + (dr.value * 0.5)) / 12);
			var sh = PitchShift.ar(x, 0.0427, pr, 0, 0);
			var n = 1 + ((driftM.value * 7) + 0.5).floor;
			var wet = Select.ar(n > 1, [sh, Latch.ar(sh, Impulse.ar(SampleRate.ir / n))]);
			(x * ((1 - aux.value) * (1 - (mamt * mamt)))) + (wet * (1 - ((1 - mamt) * (1 - mamt))))
		});

		// ============================================================ DIFFUSION
		// delay lines with feedback: the loop goes through LocalIn (one block), so the feedback
		// tap reads one block earlier than the output tap and the echoes stay exactly d apart
		[[\chr_cascade, 0], [\chr_reels, 1]].do { arg pair;
			var name = pair[0], e = pair[1];
			mk.(name, 2, { arg x;
				var damt = \amt.kr(0.5);
				var wetv = \vol.kr(0.5) * 2;
				var dt = dtime.value;
				var bs = BlockSize.ir;
				var dfD = Lag.ar(K2A.ar(dt), 0.48);
				var mod = if(e == 1, {
					// tape wow and flutter (awFlut); CASCADE: a slow even sway with DRIFT
					var wf = awFlut.([1.0, 11.0]);
					(wf[0] * (10 + (driftD.value * 100))) + (wf[1] * (2 + (driftD.value * 8)))
				}, {
					SinOsc.ar(0.42) * (driftD.value * 100)
				});
				var d = dfD + mod + 2;
				var fb = damt * if(e == 0, 1.12, 1.04);
				var cLp = if(e == 0, {
					// CASCADE: DRIFT also wears the repeats down
					lp1.((6500 * (2 ** (((dt / SampleRate.ir).neg * 1.6) - (driftD.value * 1.2)))).clip(900, 6500))
				}, {
					lp1.(5200 - (driftD.value * 2500))
				});
				var cHp = lp1.(if(e == 0, 60, 140));
				var fbIn = LocalIn.ar(2);
				var bufs = [LocalBuf(131072, 1), LocalBuf(131072, 1)];
				var phs = [0, 1].collect { arg c; DelTapWr.ar(bufs[c], x[c] + fbIn[c]) };
				var filt = { arg r; var l = OnePole.ar(r, cLp); l - OnePole.ar(l, cHp) };
				var vOut = [0, 1].collect { arg c; filt.(DelTapRd.ar(bufs[c], phs[c], d / SampleRate.ir, 2)) };
				var vFb = [0, 1].collect { arg c; filt.(DelTapRd.ar(bufs[c], phs[c], (d - bs) / SampleRate.ir, 2)) };
				var w = if(e == 1, {
					// every pass through the tape squashes the loud highs and rounds the peaks
					awSat.(awSoft.(vFb * 1.3, lp1.(2800), 1)) * 0.77
				}, {
					vFb.tanh + (WhiteNoise.ar(0.0006 ! 2) * (1 + driftD.value))
				});
				LocalOut.ar(w * fb);
				(x * (1 - aux.value)) + (vOut * (wetv * if(e == 0, 0.6, 0.75)))
			});
		};
		mk.(\chr_space, 2, { arg x;
			// plate (see above); TIME morphs room -> hall -> cathedral -> huge, the room
			// glides instead of jumping, DRIFT adds chorus to the tail
			var damt = \amt.kr(0.5);
			var wetv = \vol.kr(0.5) * 2;
			var pos = (timeS.value * 4).clip(0, 4);
			var k = pos.floor.min(3);
			var f = pos - k;
			var tab = { arg t; Select.kr(k, t) + (f * (Select.kr(k + 1, t) - Select.kr(k, t))) };
			var sz = Lag.kr(tab.([0.4, 0.65, 1.0, 1.3, 1.6]), 0.12);
			var pd = Lag.kr(tab.([96, 384, 960, 1920, 3360]), 0.12);
			var amp = (tab.([0.3, 0.8, 1.4, 2.0, 3.0]) + (driftD.value * 1.5)).min(4.5);
			var trim = tab.([0.98, 1.07, 1.16, 1.25, 1.06]);           // same loudness as the earlier SPACE
			var pl = plate.(x, sz, tab.([0.5, 1.5, 3.0, 6.0, 15.0]), tab.([0.75, 0.6, 0.5, 0.42, 0.38]),
				tab.([0.6, 0.62, 0.66, 0.7, 0.72]), amp, pd, LocalIn.ar(2));
			// AMOUNT is dry / wet: all wet at full
			var kd = (1 - aux.value) * (1 - (damt * damt));
			LocalOut.ar(pl.clip2(4));
			(x * kd) + ((pl * 2) * (((1 - ((1 - damt) * (1 - damt))) * wetv) * trim))
		});
		mk.(\chr_collage, 2, { arg x;
			// two overlapping grains replay chunks of the line and are written back, so the loop keeps
			// editing itself. The chunks sit 1..3 grain lengths back: when TIME moves they slide and the
			// pitch bends. DRIFT: some grains at double or half speed, and a slow wobble
			var damt = \amt.kr(0.5);
			var wetv = \vol.kr(0.5) * 2;
			var drf = driftD.value;
			var bs = BlockSize.ir;
			var gT = Select.kr(tempo.value, [1200 * (2 ** (timeS.value * 6.3)), beatS.value * \tdiv.kr(1) * 0.5]).min(60000);
			var gL = Lag.ar(K2A.ar(gT), 0.72);                 // glides as on the Gills (time constant 0.1 s)
			var gp = Phasor.ar(0, 1 / gL, 0, 1);
			var pb = (gp + 0.5).wrap(0, 1);
			var ta = HPZ1.ar(gp) < 0;
			var tb = HPZ1.ar(pb) < 0;
			var spOf = { arg r; (r < (drf * 0.5)) - ((r >= (drf * 0.5)) * (r < (drf * 0.75)) * 0.5) };
			var spA = Latch.ar(spOf.(TRand.ar(0, 1, ta)), ta);
			var spB = Latch.ar(spOf.(TRand.ar(0, 1, tb)), tb);
			var wow = 8 + ((1 + SinOsc.ar(0.42)) * (drf * 60));
			var oa = ((gL * ((1 + TIRand.ar(0, 2, ta)) - (spA * gp))) + wow).clip(bs + 8, 126000);
			var ob = ((gL * ((1 + TIRand.ar(0, 2, tb)) - (spB * pb))) + wow).clip(bs + 8, 126000);
			var wa = 1 - ((gp * 2) - 1).abs;
			var wb = 1 - wa;
			var fbIn = LocalIn.ar(2);
			var bufs = [LocalBuf(131072, 1), LocalBuf(131072, 1)];
			var phs = [0, 1].collect { arg c; DelTapWr.ar(bufs[c], x[c] + fbIn[c]) };
			var rd = { arg c, dly; DelTapRd.ar(bufs[c], phs[c], dly / SampleRate.ir, 2) };
			var vOut = [0, 1].collect { arg c; (rd.(c, oa) * wa) + (rd.(c, ob) * wb) };
			var vFb = [0, 1].collect { arg c; (rd.(c, oa - bs) * wa) + (rd.(c, ob - bs) * wb) };
			LocalOut.ar((vFb * (damt * 0.95)).tanh);
			(x * (1 - aux.value)) + (vOut * (wetv * 0.75))
		});
		mk.(\chr_reverse, 2, { arg x;
			// backwards chunks; TIME is their speed (and pitch): half, normal at the centre, double. The
			// chunk is one beat with the tempo, half a second without. AMOUNT is dry / wet (all wet at
			// full), DRIFT wobbles the pitch
			var damt = \amt.kr(0.5);
			var wetv = \vol.kr(0.5) * 2;
			var ts = timeS.value;
			var rsp = Select.kr((ts > 0.47) * (ts < 0.53), [2 ** ((ts - 0.5) * 2), 1]);
			var rvC = Select.kr(tempo.value, [24000, beatS.value]).min(120000 / (1 + rsp));
			var pa = Phasor.ar(0, 1 / rvC, 0, 1);
			var pb = (pa + 0.5).wrap(0, 1);
			var wa = 1 - ((pa * 2) - 1).abs;
			var wb = 1 - wa;
			var span = K2A.ar(rvC * (1 + rsp));
			var wow = 4 + ((1 + SinOsc.ar(0.6)) * (driftD.value * 100));
			var bufs = [LocalBuf(131072, 1), LocalBuf(131072, 1)];
			var phs = [0, 1].collect { arg c; DelTapWr.ar(bufs[c], x[c]) };
			var v = [0, 1].collect { arg c;
				(DelTapRd.ar(bufs[c], phs[c], (wow + (pa * span)) / SampleRate.ir, 2) * wa) +
				(DelTapRd.ar(bufs[c], phs[c], (wow + (pb * span)) / SampleRate.ir, 2) * wb)
			};
			(x * ((1 - aux.value) * (1 - (damt * damt)))) + (v * (((1 - ((1 - damt) * (1 - damt))) * wetv) * 1.3))
		});

		// ============================================================ TEXTURE
		mk.(\chr_filter, 3, { arg x;
			// FILTER STYLE: 0 tilt, 1 low-pass, 2 high-pass. Tilt: left of the centre cuts the highs,
			// right cuts the lows, nothing happens at the centre. Low-pass and high-pass do nothing at AMOUNT 0
			// and filter more as it is turned up (the pedal in the tutorial closes the low-pass until almost silent)
			var tamt = \amt.kr(0.5);
			var t = (tamt - 0.5) * 2;
			var lo = OnePole.ar(x, lp1.(800));
			var tl = (lo * Select.kr(t > 0, [1, 2 ** (t.neg * 4)])) + ((x - lo) * Select.kr(t < 0, [1, 2 ** (t * 4)]));
			var lpf = RLPF.ar(x, (20300 * (2 ** (tamt.neg * 9))).clip(40, 20000), 1 / 0.9);
			var hpf = RHPF.ar(x, (20 * (2 ** (tamt * 8.6))).min(20000), 1 / 0.8);
			Select.ar(\fstyle.kr(0), [tl, lpf, hpf])
		});
		mk.(\chr_squash, 3, { arg x;
			var tamt = \amt.kr(0.5);
			var e = Amplitude.ar(((x[0].abs) + (x[1].abs)) * 0.5, 0.001, 0.12);
			var thr = 0.3 * (2 ** (tamt.neg * 6));
			var g = OnePole.ar(((thr + ((e - thr) * 0.12)) / e.max(0.0001)).min(1), 0.99);
			var drv = 1 + ((tamt - 0.85).max(0) * 30);
			(x * (g * (1 + (tamt * 5)) * drv * 0.8)).tanh * 1.1
		});
		mk.(\chr_cassette, 3, { arg x;
			// wow and flutter, tape compression, head bump, soft highs, tape clip, hiss,
			// dropouts at high settings
			var tamt = \amt.kr(0.5);
			var wf = awFlut.([0.9, 14.5]);
			var d = (96 + (tamt * ((40 * (1 + wf[0])) + (6 * wf[1])))) / SampleRate.ir;
			var e = Amplitude.ar(((x[0].abs) + (x[1].abs)) * 0.5, 0.0048, 0.16);
			var cg = 1 / (1 + ((e * tamt) * 3));
			var dropRate = 0.73 * (tamt >= 0.85);
			var gate = OnePole.ar(1 - (Decay.ar(Dust.ar(dropRate), 0.29).min(1) * 0.85), 0.99);
			var v = DelayC.ar(x, 0.01, d) * cg;
			var hb = (BPF.ar(v, 70, 1) * (0.45 * tamt)).clip2(1);      // head bump, holds itself back
			var n = WhiteNoise.ar((0.012 * tamt) ! 2);
			v = v + (hb * (1 - ((hb * hb) / 3)));
			v = awSat.(awSoft.(v * (1 + (tamt * 4)), lp1.(3500), tamt)) / (1 + (tamt * 1.5));
			v = RLPF.ar(v, (16000 * (2 ** (tamt.neg * 2.4))).min(20000), 1 / 0.75);
			(v + (n - OnePole.ar(n, 0.7))) * (gate * 1.15)
		});
		mk.(\chr_broken, 3, { arg x;
			// a broken machine: random pitch drops that slowly recover, with wobble
			var tamt = \amt.kr(0.5);
			var t = TDuty.kr(Dwhite(0.5, 0.5 + (2.5 * (1.2 - tamt))));
			var bkT = Decay.kr(t * (tamt * (200 + TRand.kr(0, 500, t))), 2.07);
			var bk = Lag.kr(bkT, 0.24);
			var wf = awFlut.([(5 + (tamt * 9)) * 1.64]);                // uneven wobble
			var d = ((64 + bk + ((tamt * 18) * wf[0])).min(1900)) / SampleRate.ir;
			var am = 1 - ((tamt * 0.35) * (0.5 + (0.5 * SinOsc.ar(2.4))));
			DelayC.ar(x, 0.042, d) * am
		});
		mk.(\chr_interf, 3, { arg x;
			// crackle -> static bursts -> digital glitches as the amount rises
			var tamt = \amt.kr(0.5);
			var z = tamt * 3;
			var zone = z.floor.min(2);
			var lvl = 0.25 + (0.75 * (z - zone));
			var crk = Decay.ar(Dust.ar((10 + (120 * lvl)) * (48000 / 65536)) * WhiteNoise.ar(0.35 * lvl), 0.0003);
			var stT = TDuty.ar(Dwhite(2000 / 48000, 22000 / 48000));
			var stA = TRand.ar(0, 1, stT) * (TRand.ar(0, 1, stT) < 0.5);
			var st = WhiteNoise.ar(0.06) * (lvl * stA * (zone >= 1));
			var bp = BPF.ar(st, 1200 + (2500 * tamt), 1 / 1.5) * 3;
			var v = x + crk + bp;
			var gt = Dust.ar(((1 + (6 * lvl)) * (48000 / 65536)) * (zone >= 2));
			var gon = Trig1.ar(gt, TRand.ar(600, 4600, gt) / SampleRate.ir);
			var held = Latch.ar((v * 24).round / 24, Impulse.ar(SampleRate.ir / 4));
			Select.ar(gon > 0, [v, held])
		});

		// ============================================================ input, LFO, output, capture
		SynthDef(\chr_in, {
			var inL = In.ar(\in0.kr(0));
			var inR = In.ar(\in1.kr(1));
			var mode = \inMode.kr(0);                      // 0 mono L, 1 stereo, 2 L+R
			var m = (inL + inR) * 0.5;
			var l = Select.ar(mode, [inL, inL, m]);
			var r = Select.ar(mode, [inL, inR, m]);
			// bypass with trails: the chain input closes in 10 ms, tails keep ringing
			var gg = Slew.ar(K2A.ar(1 - \byp.kr(0)), 100, 100);
			var cap = InFeedback.ar(\capbus.kr(0), 2) * \pre.kr(0);
			var d = ([l, r] * gg) + cap;
			Out.ar(\cbus.kr(0), d);
			Out.ar(\dbus.kr(0), d);
			Out.ar(\rbus.kr(0), [l, r]);
			Out.ar(\gibus.kr(0), gg);
			Out.kr(\pkbus.kr(0), Peak.kr(l.abs.max(r.abs), Impulse.kr(15)));
		}).add;

		SynthDef(\chr_lfo, {
			// movement LFO: free (RATE) or note divisions of the tempo; locked to the beat with
			// a gentle phase correction (the loudest point of the tremolo lands on the beat)
			var tempo = \tempo.kr(0);
			var rS = Lag.kr(\rate.kr(0.5), 0.006);
			var drv = Lag.kr(LFDNoise0.kr(10), 0.08) * \driftm.kr(0);
			var hzT = \rdiv.kr(1) / \beat.kr(0.5);
			// DRIFT makes the free speed wander; on the tempo the speed stays put
			var hz = Select.kr(tempo, [(0.05 * (2 ** (rS * 8))) * (1 + (drv * 0.25)), hzT]);
			var corr = LocalIn.kr(1);
			var ph = Phasor.ar(0, (hz + corr) * SampleDur.ir, 0, 1);
			var bt = \t_beat.tr(0);
			var err = (((\bphase.kr(0) - Latch.kr(A2K.kr(ph), bt)) + 0.5).wrap(0, 1)) - 0.5;
			var lim = hzT * 0.5;
			var c2 = Latch.kr((err * (err.abs > 0.01)) / (2 * \beat.kr(0.5)), bt).clip(lim.neg, lim) * tempo;
			LocalOut.kr(c2);
			Out.ar(\lfobus.kr(0), ph);
			Out.kr(\drbus.kr(0), drv);
		}).add;

		SynthDef(\chr_out, {
			var wet = In.ar(\cbus.kr(0), 2);
			var dry = In.ar(\dbus.kr(0), 2);
			var raw = In.ar(\rbus.kr(0), 2);
			var gI = In.ar(\gibus.kr(0));
			var cap = InFeedback.ar(\capbus.kr(0), 2);
			var pre = \pre.kr(0);
			var auxR = \aux.kr(2);
			var aux = auxR.min(1);
			var dm = (auxR - 1).max(0);              // 1 in mix: MIX brings in the clean input, whatever the bypass does
			var mixS = Lag.kr(\mix.kr(1), 0.02);
			var ol = Lag.kr(\olev.kr(0.5), 0.02) * 2;
			var dg = (2 * (1 - mixS)).min(1);
			var wg = (2 * mixS).min(1);
			// aux: with every module bypassed the chain would just pass the dry: fade it out
			var mg = In.kr(\gbus.kr(0), 4).clip(0, 1);
			var w = Lag.kr(1 - ((1 - mg[0]) * (1 - mg[1]) * (1 - mg[2]) * (1 - mg[3])), 0.01);
			var outA = ((cap * (pre * dg)) + (raw * (dg * dm)) + (wet * (wg * w))) * ol;
			var outI = (((dry * dg) + (wet * wg)) * ol) + (raw * (1 - gI));
			var o = Select.ar(aux, [outI, outA]);
			var mo, l, r;
			Out.ar(\postbus.kr(0), o);
			o = o + (cap * (1 - pre));
			mo = (o[0] + o[1]) * 0.5;
			l = Select.ar(\omono.kr(0), [o[0], mo]).clip2(1.5);
			r = Select.ar(\omono.kr(0), [o[1], mo]).clip2(1.5);
			l = Select.ar(l.abs > 0.8, [l, l.sign * (0.8 + (0.2 * ((l.abs - 0.8) * 5).tanh))]);
			r = Select.ar(r.abs > 0.8, [r, r.sign * (0.8 + (0.2 * ((r.abs - 0.8) * 5).tanh))]);
			Out.ar(\out.kr(0), [l, r]);
		}).add;

		SynthDef(\chr_cap, {
			// CAPTURE: hold to record (pre = chain input, post = output), release to play;
			// shorter than 1 s = sustainer (two random grains = pad), longer = loop with seam blend
			var sr = SampleRate.ir;
			var bL = \bufL.kr(0), bR = \bufR.kr(0);
			var src = Select.ar(\pre.kr(0), [In.ar(\postbus.kr(0), 2), In.ar(\dbus.kr(0), 2)]);
			var rec = \rec.kr(0);
			var rise = Trig1.ar(K2A.ar(rec), 0.002);         // longer than a block: RecordBuf sees it
			var fall = Trig1.ar(K2A.ar(1 - rec), 0.002);
			var run = (K2A.ar(rec) + Trig1.ar(fall, 0.01)) > 0;   // keeps writing 10 ms for the seam
			var maxLen = BufFrames.kr(bL) - 1000;
			var len = Latch.ar(Sweep.ar(rise, sr), fall).clip(1, maxLen);
			var tail = (len * 0.25).min(480);
			var play = \play.kr(0);
			var go = Trig1.ar(K2A.ar(play), 0.002);
			var p = Phasor.ar(go, 1, 0, len);
			// seam blend from the second pass on (the tail after the loop end is written meanwhile)
			var first = Trig1.ar(go, (len + tail) / sr);
			var seam = (p < tail) * (first <= 0);
			var lp = [bL, bR].collect { arg b;
				var a = BufRd.ar(1, b, p, 1, 2);
				var t = BufRd.ar(1, b, len + p, 1, 2);
				Select.ar(seam, [a, (a * (p / tail)) + (t * (1 - (p / tail)))])
			};
			var gl = (len * 0.85).min(19200);
			var span = (len - gl).max(0);
			var gt = Impulse.ar((2 * sr) / gl);
			var gpos = TRand.ar(0, span, gt) / BufFrames.kr(bL);
			var su = [bL, bR].collect { arg b; GrainBuf.ar(1, gt, gl / sr, b, 1, gpos, 2, 0, -1, 8) };
			var cg = Lag.kr(play, 0.03);
			var out = Select.ar(\mode.kr(0), [lp, su]) * cg;
			RecordBuf.ar(src[0], bL, 0, 1, 0, run, 0, rise);
			RecordBuf.ar(src[1], bR, 0, 1, 0, run, 0, rise);
			Out.ar(\capbus.kr(0), out);
		}).add;

		s.sync;

		// ------------------------------------------------------------ buses, buffers, nodes
		cb = Bus.audio(s, 2);
		db = Bus.audio(s, 2);
		rb = Bus.audio(s, 2);
		pb = Bus.audio(s, 2);
		gIB = Bus.audio(s, 1);
		capB = Bus.audio(s, 2);
		lfoB = Bus.audio(s, 1);
		gB = Bus.control(s, 4);
		drB = Bus.control(s, 1);
		pkB = Bus.control(s, 1);
		capL = Buffer.alloc(s, capFrames, 1);
		capR = Buffer.alloc(s, capFrames, 1);
		s.sync;

		preG = Group.new(context.xg, \addToHead);
		modG = Group.new(preG, \addAfter);
		postG = Group.new(modG, \addAfter);
		state = Dictionary.new;
		modState = Array.fill(4, { Dictionary.new });
		fx = [0, 0, 0, 0];
		ord = [0, 1, 2, 3];

		inSyn = Synth.new(\chr_in, [\in0, context.in_b[0].index, \in1, context.in_b[1].index,
			\cbus, cb.index, \dbus, db.index, \rbus, rb.index, \gibus, gIB.index,
			\capbus, capB.index, \pkbus, pkB.index], preG, \addToTail);
		lfoSyn = Synth.new(\chr_lfo, [\lfobus, lfoB.index, \drbus, drB.index], preG, \addToHead);
		mods = 4.collect { arg m;
			Synth.new(names[m][0], this.modArgs(m), modG, \addToTail)
		};
		outSyn = Synth.new(\chr_out, [\cbus, cb.index, \dbus, db.index, \rbus, rb.index, \gibus, gIB.index,
			\capbus, capB.index, \gbus, gB.index, \postbus, pb.index, \out, context.out_b.index], postG, \addToHead);
		capSyn = Synth.new(\chr_cap, [\bufL, capL.bufnum, \bufR, capR.bufnum, \postbus, pb.index,
			\dbus, db.index, \capbus, capB.index], postG, \addToTail);

		// ------------------------------------------------------------ commands
		// global values (sent to every node that has a control with that name)
		this.addCommand(\set, "sf", { arg msg;
			var k = msg[1].asSymbol, v = msg[2];
			state[k] = v;
			preG.set(k, v);
			modG.set(k, v);
			postG.set(k, v);
		});
		// per-module values: amt, vol, on
		this.addCommand(\mod, "isf", { arg msg;
			var m = msg[1].asInteger.clip(0, 3), k = msg[2].asSymbol, v = msg[3];
			modState[m][k] = v;
			mods[m].set(k, v);
		});
		// effect of a module (0..4): cross-fade from the old node to a new one in the same place
		this.addCommand(\fx, "ii", { arg msg;
			var m = msg[1].asInteger.clip(0, 3), e = msg[2].asInteger.clip(0, 4);
			var old = mods[m];
			if(e != fx[m], {
				fx[m] = e;
				mods[m] = Synth.new(names[m][e], this.modArgs(m), old, \addAfter);
				old.set(\gate, 0);
			});
		});
		// order of the chain: four module numbers (0 CHARACTER, 1 MOVEMENT, 2 DIFFUSION, 3 TEXTURE)
		this.addCommand(\order, "iiii", { arg msg;
			var o = msg[1..4].collect({ arg v; v.asInteger.clip(0, 3) });
			if(o.asSet.size == 4, {
				ord = o;
				mods[o[0]].moveToHead(modG);
				(1..3).do({ arg i; mods[o[i]].moveAfter(mods[o[i - 1]]) });
			});
		});
		// beat from the norns clock: expected LFO phase on this beat
		this.addCommand(\beat, "f", { arg msg;
			lfoSyn.set(\t_beat, 1, \bphase, msg[1]);
		});
		// capture: rec (1 = recording), play (1 = playing), mode (0 loop, 1 sustainer)
		this.addCommand(\cap, "iii", { arg msg;
			capSyn.set(\rec, msg[1], \play, msg[2], \mode, msg[3]);
		});

		this.addPoll(\peak, { pkB.getSynchronous });
	}

	modArgs { arg m;
		var a = [\bus, cb.index, \gbus, gB.index + m, \lfobus, lfoB.index, \drbus, drB.index];
		state.keysValuesDo({ arg k, v; a = a ++ [k, v] });
		modState[m].keysValuesDo({ arg k, v; a = a ++ [k, v] });
		^a
	}

	free {
		[inSyn, lfoSyn, outSyn, capSyn].do({ arg n; if(n.notNil, { n.free }) });
		mods.do({ arg n; n.free });
		[preG, modG, postG].do({ arg g; if(g.notNil, { g.free }) });
		[cb, db, rb, pb, gIB, capB, lfoB, gB, drB, pkB, capL, capR].do({ arg b; if(b.notNil, { b.free }) });
	}
}
