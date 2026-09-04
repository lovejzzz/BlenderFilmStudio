"""Original deterministic stereo sound design. No downloaded music or samples."""
import math,random,wave,array,json
from pathlib import Path

def soundtrack(doc,plan,output,response_events=None):
    sr=48000;duration=len(plan['frames'])/24;n=round(duration*sr);left=[0.0]*n;right=[0.0]*n;rng=random.Random(402)
    style=doc['sound']['style'];gain=doc['sound']['gain'];cues=[]
    def place(start,dur,fn,amp=.2,pan=0):
        lo=max(0,round(start*sr));hi=min(n,round((start+dur)*sr))
        gl=math.sqrt((1-pan)/2)*amp;gr=math.sqrt((1+pan)/2)*amp
        for i in range(lo,hi):
            t=(i/sr-start);v=fn(t)
            left[i]+=v*gl;right[i]+=v*gr
    def bell(freq,decay=1.5):
        return lambda t: (math.sin(2*math.pi*freq*t)*math.exp(-t/decay)+.23*math.sin(2*math.pi*freq*2.01*t)*math.exp(-t/.25)+.12*math.sin(2*math.pi*freq*3.99*t)*math.exp(-t/.07))*(1-math.exp(-t/.002))
    def source_time(frame):
        matches=[(f['index']-1)/24 for f in plan['frames'] if f['sourceFrame']==frame]
        return matches[0] if matches else None
    if style=='tape':
        # Warm harmonic bed with original pitches, subtle wow and stereo air.
        for i,freq in enumerate([146.832,220,261.626,329.628]):
            place(.6,duration-.6,lambda t,f=freq:math.sin(2*math.pi*f*t+.045*math.sin(2*math.pi*.47*t))*(1-math.exp(-t/2))*math.exp(-t/24),.033,(-.55+i*.35))
        for t,midi in [(1.9,62),(5.8,69),(9.8,65),(13.8,64)]:
            place(t,4,bell(440*2**((midi-69)/12),2),.055,math.sin(t)*.3);cues.append({'time':t,'kind':'original melodic tone'})
        for i in range(n):
            t=i/sr;active=min(1,max(0,(t-1.42)*8))*min(1,max(0,(duration-1.35-t)/.9));hiss=rng.uniform(-1,1)*.006
            motor=(math.sin(2*math.pi*58*t)+.2*math.sin(2*math.pi*116*t))*.011*active
            left[i]+=hiss+motor;right[i]+=hiss*.75+motor
        for t in [1.45,duration-1.6]:place(t,.09,lambda x:rng.uniform(-1,1)*math.exp(-x/.013),.13,-.15)
    elif style=='kinetic':
        for i,freq in enumerate([130.813,196,293.665]):place(0,duration,lambda t,f=freq:math.sin(2*math.pi*f*t)*(1-math.exp(-t/2)),.009,-.35+i*.35)
        for i,(name,frame) in enumerate(sorted((response_events or {}).items())):
            t=source_time(frame)
            if t is None:continue
            freq=440*2**(([60,62,64,67,69,72,74,76][i%8]-69)/12)
            place(t,2.5,bell(freq,.7),.11,-.65+i*.18)
            place(t,.10,lambda x:math.sin(2*math.pi*115*x)*math.exp(-x/.019)+rng.uniform(-1,1)*math.exp(-x/.004),.08,-.65+i*.18)
            cues.append({'time':t,'sourceFrame':frame,'target':name,'kind':'impact and original resonant tone'})
        for i in range(n):left[i]+=rng.uniform(-1,1)*.0015;right[i]+=rng.uniform(-1,1)*.0015
    samples=array.array('h');peak=0;square=0
    for i in range(n):
        t=i/sr;envelope=min(1,t/.35,max(0,(duration-t)/1.3))*gain
        for v in [left[i],right[i]]:
            v=max(-.98,min(.98,v*envelope));peak=max(peak,abs(v));square+=v*v;samples.append(round(v*32767))
    with wave.open(str(output),'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(sr);w.writeframes(samples.tobytes())
    return {'sampleRate':sr,'channels':2,'seconds':duration,'peakDbFS':20*math.log10(max(1e-9,peak)),'rmsDbFS':10*math.log10(max(1e-12,square/(2*n))),'cues':cues,'provenance':'original deterministic procedural synthesis, no external samples'}
