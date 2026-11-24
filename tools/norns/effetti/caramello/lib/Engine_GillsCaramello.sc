// Engine_GillsCaramello: pitch correction for norns, from glassy-clean to hyperpop hard-tune.
// Port of the Ksoloti Gills "autotune" patch.
//   - pitch tracking: Pitch (autocorrelation, parabolic period refinement)
//   - pitch shifting: pitch-synchronous grains (TD-PSOLA) with GrainBuf, formant control
//     analysis marks = positive zero crossings of the band-limited fundamental (one per period,
//     locked to the waveform); a grain reads the newest mark that never runs ahead of the
//     input ("live"), or one about 16 ms older ("studio"); older marks come from a 64-slot history
//   - scale / MIDI targets with hysteresis, retune speed, amount, freeze
//   - voices: main, two detuned doubles, octave sparkle, up to three harmonies
//   - fx: gate, drive + tone, air, crush, reverb, mix, output, bypass
// Input modes: 1 = mono L, 2 = L+R, 3 = two singers (L -> L, R -> R, one harmony each).
// Only core SuperCollider UGens are used.

Engine_GillsCaramello : CroneEngine {
	var <grp, <wetBus, <kbA, <kbB, <pkBus, <chains, <fx, <mode, <state, <arrays;

	*new { arg context, doneCallback;
		^super.new(context, doneCallback);
	}

	alloc {
		var s = context.server;

		// ---------------------------------------------------------------- one singer
		SynthDef(\car_chain, {
			var nb = 65536;
			var sr = SampleRate.ir;
			var inL = In.ar(\in0.kr(0));
			var inR = In.ar(\in1.kr(1));
			var src = Select.ar(\inMode.kr(0), [inL, (inL + inR) * 0.5, inR]);
			var x = HPF.ar(src, 60);
			// input ring: DelTapWr outputs the index it writes, so every grain read depends on it
			// and scsynth always runs the write first within a block
			var buf = LocalBuf(nb, 1);
			var wp = DelTapWr.ar(buf, x);
			var pt = Pitch.kr(x, initFreq: 220, minFreq: 70, maxFreq: 1100, execFreq: 200,
				maxBinsPerOctave: 32, median: 3, ampThreshold: 0.004, peakThreshold: 0.5, downSample: 1, clar: 0);
			var f0 = pt[0].clip(70, 1100);
			var env = Amplitude.kr(x, 0.001, 0.05);
			var loud = env > \gate.kr(0.002);
			var voiced = pt[1] * loud;
			var nIn = f0.cpsmidi;
			var vw = LagUD.kr(voiced, 0.03, 0.09);
			var key = \key.kr(0);
			var mask = \mask.kr(#[1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1]);
			var prevT = LocalIn.kr(1);
			var base = nIn.round;
			var best = base;
			var bd = 1000;
			var aPrev, keep, tScale, mn, useMidi, tMidi, tSel, frz, tFrz, t, cc, rt, tau, cS, corr, sem, outN;
			var fphi, pcT, ivA, ivB, ivC, hn, hiv, nhM, useChord, iv, nh, dual, sg, det, sp, lv, tot, norm;
			var offs, phis, pans, dlys, vo, rT, ta, fund, mark, markPos, lagNow, slot, mbuf, live, ncore, voices;
			var side, wid, st, mo, sig, gG;

			// nearest allowed note (13 candidates around the sung note)
			(-6..6).do { |k|
				var m = base + k;
				var a = Select.kr((m - key) % 12, mask);
				var d = (m - nIn).abs + ((1 - a) * 1000);
				var c = d < bd;
				best = Select.kr(c, [best, m]);
				bd = bd.min(d);
			};
			// hysteresis: keep the previous target while it is close enough
			aPrev = Select.kr((prevT - key) % 12, mask);
			keep = aPrev * (((prevT - nIn).abs) < (bd + 0.18)) * (prevT > 0);
			tScale = Select.kr(keep, [best, prevT]);
			// MIDI note: the held note in the octave nearest to the voice
			mn = \midiNote.kr(-1);
			useMidi = mn >= 0;
			tMidi = mn + (((nIn - mn) / 12).round * 12);
			tSel = Select.kr(useMidi, [tScale, tMidi]);
			tSel = Select.kr(voiced, [Select.kr(prevT > 0, [tSel, prevT]), tSel]);
			frz = \freeze.kr(0);
			tFrz = Latch.kr(tSel, frz);
			t = Select.kr(frz, [tSel, tFrz]);
			LocalOut.kr(t);

			// correction with retune speed (0 = instant robot)
			cc = t - nIn;
			rt = \retune.kr(0);
			tau = (1 + (1.8 * (2 ** (rt * 9.5)))) * (6.9 / 3000);
			tau = tau * (rt > 0.01);
			cS = Lag.kr(Gate.kr(cc, voiced), tau);
			corr = Select.kr(frz, [cS * \amount.kr(1), cS]);
			sem = (vw * corr) + \pitch.kr(0) + \fine.kr(0) + (\vib.kr(0) * 0.6 * SinOsc.kr(4.8 + (\vib.kr(0) * 1.5)) * vw);
			outN = nIn + sem;
			fphi = 2 ** (\formant.kr(0) / 12);

			// harmonies: scale-aware intervals from Lua (one table per voice, by pitch class of the target)
			pcT = (t - key) % 12;
			ivA = Select.kr(pcT, \iv0.kr(0 ! 12));
			ivB = Select.kr(pcT, \iv1.kr(0 ! 12));
			ivC = Select.kr(pcT, \iv2.kr(0 ! 12));
			// MIDI chord: the other held notes, each in the octave nearest to the target
			hn = [\hn1.kr(-1), \hn2.kr(-1), \hn3.kr(-1)];
			hiv = hn.collect { |h| (h + (((t - h) / 12).round * 12)) - t };
			nhM = (hn[0] >= 0) + (hn[1] >= 0) + (hn[2] >= 0);
			useChord = useMidi * (nhM > 0);
			iv = [Select.kr(useChord, [ivA, hiv[0]]), Select.kr(useChord, [ivB, hiv[1]]), Select.kr(useChord, [ivC, hiv[2]])];
			dual = \dual.kr(0);
			nh = Select.kr(useChord, [\nh.kr(1), nhM]);
			nh = nh.min(Select.kr(dual, [3, 1])) * (1 - \hoff.kr(0));

			// voice set: 0 main, 1-2 doubles, 3 sparkle octave, 4-6 harmonies
			sg = \sugar.kr(0);
			det = (6 + (14 * sg)) / 100;
			sp = ((sg - 0.4) / 0.6).max(0);
			lv = [1, 0.55 * sg, (0.55 * sg) * (1 - dual), 0.45 * sp,
				(nh > 0) * \harm.kr(0) * 0.75, (nh > 1) * \harm.kr(0) * 0.75, (nh > 2) * \harm.kr(0) * 0.75];
			tot = lv.sum { |l| l.squared };
			norm = 1 / (1 + (0.5 * (tot - 1)));
			offs = [0, det, det.neg, 12, iv[0], iv[1], iv[2]];
			phis = [1, 1.04, 0.97, 1.26, 1, 1, 1] * fphi;
			pans = [0, -0.9, 0.9, 0, -0.55, 0.55, 0];
			dlys = [0, 552, 864, 0, 96, 144, 192];
			vo = voiced * (vw > 0.5);
			rT = 2 ** ((\pitch.kr(0) + \fine.kr(0)) / 12);
			ta = sr / f0;
			// analysis marks, one per input period and locked to the waveform: positive zero crossings
			// of the fundamental (band-limited around f0), with a hold-off of 0.7 periods
			fund = LPF.ar(LPF.ar(HPF.ar(x, f0 * 0.5), f0 * 1.1), f0 * 1.1);
			mark = Trig1.ar((fund > 0) * (Delay1.ar(fund) <= 0), 0.7 / f0);
			markPos = Latch.ar(wp, mark);
			lagNow = (wp - markPos).wrap(0, nb);
			// the last 64 mark positions, for the voices that read older periods
			slot = Stepper.ar(mark, 0, 0, 63, 1);
			mbuf = LocalBuf(64, 1).clear;
			BufWr.ar(markPos, mbuf, slot);
			live = \live.kr(1);
			ncore = \ncore.kr(0);

			voices = 7.collect { |v|
				var fo = Select.kr(vo, [f0 * rT * (2 ** (offs[v] / 12)), (outN + offs[v]).midicps]).clip(30, 4000);
				var ts = sr / fo;
				var phv = Select.kr(ncore, [phis[v], phis[v] * ta / ts]).clip(0.25, 4);
				var h = (ta / phv).max(0.65 * ts).min(2 * ta).max(16);
				var g = ((lv[v] * ts) / h).min(2 * lv[v]) * norm;
				// the grain is centred on a mark, h samples after its start: the mark must lag the
				// input by at least need, or the grain would read samples not written yet
				var need = (dlys[v] + 9 + (h * ((phv - 1).abs)) + ((1 - live) * 768)) - h;
				var k = ((need - lagNow) / ta).ceil.max(0);
				var lagE = lagNow + (k * ta);
				// exact older marks from the history (k and k+1 back); estimate if a slot is stale
				var lag1 = (wp - BufRd.ar(1, mbuf, (slot - k) % 64, 1, 1)).wrap(0, nb);
				var lag2 = (wp - BufRd.ar(1, mbuf, ((slot - k) - 1) % 64, 1, 1)).wrap(0, nb);
				var ok1 = (((lag1 - lagE).abs) < (0.5 * ta)) * (k > 0);
				var ok2 = ((lag2 - (lagE + ta)).abs) < (0.5 * ta);
				var lagH = Select.ar(lag1 < need, [lag1, Select.ar(ok2, [lagE + ta, lag2])]);
				var lagC = Select.ar(ok1, [lagE, lagH]);
				var pos = (((wp - lagC) - (h * phv)) / nb).wrap(0, 1);
				var trig = Impulse.ar(fo) * (lv[v] > 0.0005);
				GrainBuf.ar(1, trig, (2 * h) / sr, buf, phv, pos, 2, 0, -1, 48) * g
			};

			// one singer: panned stack; two singers: everything to this singer's side
			side = \side.kr(0);
			wid = \width.kr(0.8);
			st = Mix.fill(7, { |v| Pan2.ar(voices[v], if((v == 1) || (v == 2), { pans[v] * wid }, { pans[v] })) });
			mo = Mix(voices);
			sig = Select.ar(side.abs > 0, [st, Pan2.ar(mo, side)]);
			gG = LagUD.kr(loud, 0.002, 0.07);
			Out.ar(\out.kr(0), sig * gG);
			Out.kr(\kb.kr(0), [nIn, t, outN, voiced]);
		}).add;

		// ---------------------------------------------------------------- effects and mix (stereo / two singers)
		[\car_fx, \car_fx2].do { |name, split|
			SynthDef(name, {
				var sr = SampleRate.ir;
				var inL = In.ar(\in0.kr(0));
				var inR = In.ar(\in1.kr(1));
				var m = (inL + inR) * 0.5;
				var mode = \inMode.kr(0);
				var dryL = Select.ar(mode, [inL, m, inL]);
				var dryR = Select.ar(mode, [inL, m, inR]);
				var y = In.ar(\wet.kr(0), 2);
				var drv = \drive.kr(0);
				var tone = \tone.kr(0.5);
				var sug = \sugar.kr(0);
				var crush = \crush.kr(0);
				var space = \space.kr(0);
				var size = \size.kr(0.4);
				var dg, clipL, mk, yd, lo, tilt, gLo, gHi, air, crN, crQ, yc, pre, rv, mixv, dgn, wgn, ol, l, r, byG, mo, om;

				// drive with tone tilt
				dg = 1 + (drv * drv * 40);
				clipL = Select.kr(drv > 0.55, [1, 1 - ((drv - 0.55) * 1.2)]);
				mk = 1 / (1 + (3.6 * drv) + (4.5 * drv * drv));
				yd = ((y * dg).tanh.clip2(clipL) / clipL) * mk;
				lo = OnePole.ar(yd, exp(-2pi * 1500 / sr));
				tilt = (tone - 0.5) * 2;
				gLo = 2 ** (tilt.neg * 1.5);
				gHi = 2 ** (tilt * 1.5);
				y = Select.ar(drv > 0.002, [y, (lo * gLo) + ((yd - lo) * gHi)]);
				// air
				air = OnePole.ar(y, exp(-2pi * 7000 / sr));
				y = y + ((y - air) * sug * 0.85);
				// crush: sample-rate and bit reduction
				crN = 1 + (crush * crush * 11).floor;
				crQ = 2 ** (15 - (crush * 11));
				yc = (Latch.ar(y, Impulse.ar(sr / crN)) * crQ).round / crQ;
				y = Select.ar(crush > 0.002, [y, yc]);
				// reverb: one stereo room, or one room per singer
				pre = DelayN.ar(y, 0.02, 0.01);
				rv = if(split == 1, {
					[FreeVerb.ar(pre[0], 1, size, 0.5), FreeVerb.ar(pre[1], 1, size, 0.5)]
				}, {
					FreeVerb2.ar(pre[0], pre[1], 1, size, 0.5)
				});
				y = y + (rv * space * 1.2);
				// mix, output, bypass
				mixv = Lag.kr(\mix.kr(1), 0.05);
				dgn = 1 - (mixv * mixv);
				wgn = 1 - ((1 - mixv) * (1 - mixv));
				ol = Lag.kr(\olev.kr(0.5) * 2, 0.05);
				l = ((dryL * dgn) + (y[0] * wgn)) * ol;
				r = ((dryR * dgn) + (y[1] * wgn)) * ol;
				byG = Lag.kr(1 - \bypass.kr(0), 0.03);
				l = dryL + ((l - dryL) * byG);
				r = dryR + ((r - dryR) * byG);
				// mono output: two singers are summed, one singer is averaged
				mo = (l + r) * if(split == 1, 1, 0.5);
				om = \omono.kr(0);
				l = Select.ar(om, [l, mo]);
				r = Select.ar(om, [r, mo]);
				l = l.clip2(1.5);
				r = r.clip2(1.5);
				l = Select.ar(l.abs > 0.8, [l, l.sign * (0.8 + (0.2 * ((l.abs - 0.8) * 5).tanh))]);
				r = Select.ar(r.abs > 0.8, [r, r.sign * (0.8 + (0.2 * ((r.abs - 0.8) * 5).tanh))]);
				Out.ar(\out.kr(0), [l, r]);
				Out.kr(\pkb.kr(0), Amplitude.kr(inL.abs.max(inR.abs), 0.001, 0.3));
			}).add;
		};

		s.sync;

		grp = Group.new(context.xg);
		wetBus = Bus.audio(s, 2);
		kbA = Bus.control(s, 4);
		kbB = Bus.control(s, 4);
		pkBus = Bus.control(s, 1);
		state = Dictionary.new;
		arrays = Dictionary.new;
		chains = [];
		mode = 1;
		this.build;

		// ---------------------------------------------------------------- commands
		this.addCommand(\mode, "i", { arg msg;
			mode = msg[1].asInteger.clip(1, 3);
			this.build;
		});
		this.addCommand(\set, "sf", { arg msg;
			var k = msg[1].asSymbol;
			var v = msg[2];
			state[k] = v;
			chains.do({ arg c; c.set(k, v) });
			fx.set(k, v);
		});
		[\mask, \iv0, \iv1, \iv2].do { |name|
			this.addCommand(name, "iiiiiiiiiiii", { arg msg;
				var a = msg[1..12];
				arrays[name] = a;
				chains.do({ arg c; c.setn(name, a) });
			});
		};

		// ---------------------------------------------------------------- polls (tuner on the OLED)
		[\noteA, \tgtA, \outA, \vcdA].do { |name, i|
			this.addPoll(name, { kbA.getnSynchronous(4)[i] });
		};
		[\noteB, \tgtB, \outB, \vcdB].do { |name, i|
			this.addPoll(name, { kbB.getnSynchronous(4)[i] });
		};
		this.addPoll(\peak, { pkBus.getSynchronous });
	}

	// (re)create the singers and the effect synth for the current input mode
	build {
		var dual = mode == 3;
		var common = [\in0, context.in_b[0].index, \in1, context.in_b[1].index, \out, wetBus.index, \dual, if(dual, 1, 0)];
		var keep = state.getPairs;
		chains.do({ arg c; c.free; });
		if(fx.notNil, { fx.free; });
		chains = if(dual, {
			[
				Synth.new(\car_chain, common ++ [\inMode, 0, \side, -1, \kb, kbA.index] ++ keep, grp, \addToHead),
				Synth.new(\car_chain, common ++ [\inMode, 2, \side, 1, \kb, kbB.index] ++ keep, grp, \addToHead)
			]
		}, {
			[Synth.new(\car_chain, common ++ [\inMode, if(mode == 2, 1, 0), \side, 0, \kb, kbA.index] ++ keep, grp, \addToHead)]
		});
		arrays.keysValuesDo({ arg k, a; chains.do({ arg c; c.setn(k, a) }) });
		fx = Synth.new(if(dual, \car_fx2, \car_fx),
			[\in0, context.in_b[0].index, \in1, context.in_b[1].index, \inMode, if(dual, 2, if(mode == 2, 1, 0)),
				\wet, wetBus.index, \out, context.out_b.index, \pkb, pkBus.index] ++ keep,
			grp, \addToTail);
	}

	free {
		chains.do({ arg c; c.free; });
		if(fx.notNil, { fx.free; });
		grp.free;
		wetBus.free;
		kbA.free;
		kbB.free;
		pkBus.free;
	}
}
