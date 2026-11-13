// SPDX-License-Identifier: GPL-3.0-only
// Engine_Strati: plays the sounds strati made from samples. A voice: 24 sines (each at its own ratio of the note,
// harmonics or a drum's modes) and 24 noise bands (WhiteNoise through BPF), each with its own envelope of 12 points;
// the last point holds while the key is down, then the release. A sound with a noise control (a pad) gets its noise
// low-passed and turned down by the mod wheel (\noise 0..1). The file format: tools/strati/strati/norns.py.
Engine_Strati : CroneEngine {
	classvar nSines = 24, nBands = 24, nPts = 12;
	var sounds, voices, order, cur = 0, amp = 0.5, follow = 0.0, poly = 6, pan = 0.0, noiseCtl = 1.0;

	*new { arg context, doneCallback;
		^super.new(context, doneCallback);
	}

	*readSound { arg path;
		var lines, nums, d, b;
		if(File.exists(path).not) { ^nil };
		lines = File.readAllString(path).split($\n);
		if(lines.size < 8 or: { lines[0] != "strati 1" }) { ^nil };
		nums = { arg s; s.split($ ).reject({ arg w; w.isEmpty }).collect({ arg w; w.asFloat }) };
		d = ();
		d[\name] = lines[1];
		b = nums.(lines[2]); d[\root] = b[0]; d[\release] = b[1];
		d[\seg] = nums.(lines[3]);
		d[\ratios] = nums.(lines[4]);
		d[\sines] = nums.(lines[5]);
		b = nums.(lines[6]); d[\bands] = b.copyRange(0, nBands - 1); d[\rq] = b[nBands];
		d[\gains] = nums.(lines[7]);
		d[\control] = nil;
		if(lines.size > 8 and: { lines[8].beginsWith("noise ") }) { d[\control] = nums.(lines[8].copyToEnd(6)) };
		if((d[\seg].size != (nPts - 1)) or: { d[\sines].size != (nSines * nPts) } or: { d[\gains].size != (nBands * nPts) }) { ^nil };
		^d
	}

	alloc {
		sounds = Array.newClear(128);
		voices = Dictionary.new;
		order = List.new;

		SynthDef(\strati, {
			arg out = 0, hz = 261.63, level = 0.5, gate = 1, rel = 0.3, nhz = 1, pos = 0, nlev = 1, ncut = 20000;
			var seg = NamedControl.kr(\seg, 0.1 ! (nPts - 1));
			var ratios = NamedControl.kr(\ratios, 1 ! nSines);
			var lv = NamedControl.kr(\sines, 0 ! (nSines * nPts));
			var bands = NamedControl.kr(\bands, 1000 ! nBands);
			var gains = NamedControl.kr(\gains, 0 ! (nBands * nPts));
			var rq = NamedControl.kr(\rq, 0.13);
			var sig = 0, nsig = 0;
			nSines.do({ arg k;
				var levels = lv.copyRange(k * nPts, (k * nPts) + nPts - 1) ++ [0];
				var env = EnvGen.kr(Env(levels, seg ++ [rel], \lin, nPts - 1), gate);
				var f = hz * ratios[k];
				sig = sig + (SinOsc.ar(f, Rand(0, 2pi)) * env * (f < 20000));
			});
			nBands.do({ arg b;
				var levels = gains.copyRange(b * nPts, (b * nPts) + nPts - 1) ++ [0];
				var env = EnvGen.kr(Env(levels, seg ++ [rel], \lin, nPts - 1), gate);
				nsig = nsig + (BPF.ar(WhiteNoise.ar, (bands[b] * nhz).clip(20, 20000), rq) * env);
			});
			sig = sig + (LPF.ar(nsig, ncut.lag(0.1).clip(20, 20000)) * nlev.lag(0.1));
			EnvGen.kr(Env.asr(0, 1, rel + 0.02), gate, doneAction: Done.freeSelf);
			Out.ar(out, Pan2.ar((sig * level).softclip, pos));
		}).add;
		context.server.sync;

		this.addCommand(\load, "is", { arg msg;
			var d = Engine_Strati.readSound(msg[2].asString);
			if(d.notNil and: { msg[1] >= 0 } and: { msg[1] < 128 }) { sounds[msg[1]] = d };
		});
		this.addCommand(\select, "i", { arg msg; cur = msg[1].clip(0, 127) });
		this.addCommand(\noteOn, "iff", { arg msg; this.noteOn(msg[1], msg[2], msg[3]) });
		this.addCommand(\noteOff, "i", { arg msg; this.noteOff(msg[1]) });
		this.addCommand(\allOff, "", { arg msg; voices.copy.keysDo({ arg id; this.noteOff(id) }) });
		this.addCommand(\amp, "f", { arg msg; amp = msg[1] });
		this.addCommand(\follow, "f", { arg msg; follow = msg[1] });
		this.addCommand(\poly, "i", { arg msg; poly = msg[1].clip(1, 16) });
		this.addCommand(\pan, "f", { arg msg; pan = msg[1] });
		this.addCommand(\noise, "f", { arg msg;
			var gc;
			noiseCtl = msg[1].clip(0, 1);
			voices.keysValuesDo({ arg id, syn;
				gc = this.noiseGainCut(sounds[cur]);
				syn.set(\nlev, gc[0], \ncut, gc[1]);
			});
		});
	}

	noiseGainCut { arg d;
		var c;
		if(d.isNil or: { d[\control].isNil }) { ^[1, 20000] };
		c = d[\control];
		^[(noiseCtl - 1 * c[0]).dbamp, c[1] * ((c[2] / c[1]) ** noiseCtl)]
	}

	noteOn { arg id, note, vel;
		var d = sounds[cur], syn, gc;
		if(d.isNil) { ^this };
		this.noteOff(id);
		while({ order.size >= poly }, { this.noteOff(order[0]) });
		gc = this.noiseGainCut(d);
		syn = Synth.new(\strati, [
			\nlev, gc[0], \ncut, gc[1],
			\out, context.out_b, \hz, note.midicps, \level, amp * vel, \rel, d[\release],
			\nhz, 2.pow((note - d[\root]) * follow / 12), \pos, pan,
			\seg, d[\seg], \ratios, d[\ratios], \sines, d[\sines], \bands, d[\bands], \gains, d[\gains], \rq, d[\rq]
		], context.xg);
		voices[id] = syn;
		order.add(id);
	}

	noteOff { arg id;
		var syn = voices[id];
		if(syn.notNil) {
			syn.set(\gate, 0);
			voices.removeAt(id);
			order.remove(id);
		};
	}

	free {
		voices.do({ arg syn; syn.set(\gate, 0) });
	}
}
