"""Independent final-media inspection; writes only a new review root."""
import argparse,hashlib,json,math,subprocess,statistics,re
from pathlib import Path
from PIL import Image,ImageStat,ImageChops,ImageDraw
p=argparse.ArgumentParser();p.add_argument('work');p.add_argument('output');a=p.parse_args();work=Path(a.work);out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
frames=work/'output/frames';plan=json.loads((frames/'render-plan.json').read_text());delivery=json.loads((work/'output/delivery/delivery.json').read_text());movie=Path(delivery['movie']);checks={};metrics=[];previous=None;prevshot=None
checks['movie_hash']=sha(movie)==delivery['sha256'];checks['exact_png_count']=len(list(frames.glob('frame-*.png')))==len(plan['frames'])
checks['snapshot_hash']=sha(work/'project.blend')==plan['blendSha256'];checks['all_frame_hashes']=True;checks['all_dimensions']=True;checks['no_blank_frames']=True;checks['chronological_source']=True
last=0
for rec in plan['frames']:
 f=frames/f"frame-{rec['index']:05d}.png";r=json.loads(f.with_suffix('.json').read_text());checks['all_frame_hashes'] &= sha(f)==r['sha256'] and rec==r['frame']
 with Image.open(f) as im:
  checks['all_dimensions'] &= im.size==(1920,818);small=im.convert('RGB').resize((96,41));stats=ImageStat.Stat(small);mean=statistics.mean(stats.mean);std=statistics.mean(stats.stddev)
  checks['no_blank_frames'] &= mean>1 and std>1
  change=statistics.mean(ImageStat.Stat(ImageChops.difference(small,previous)).mean) if previous is not None and prevshot==rec['shot'] else None
  metrics.append({'index':rec['index'],'shot':rec['shot'],'source':rec['sourceFrame'],'mean':mean,'std':std,'withinShotMeanAbsoluteChange':change});previous=small;prevshot=rec['shot']
 checks['chronological_source'] &= rec['sourceFrame']>last;last=rec['sourceFrame']
probe=json.loads(subprocess.check_output(['/opt/homebrew/bin/ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(movie)],text=True));v=next(s for s in probe['streams'] if s['codec_type']=='video');au=next(s for s in probe['streams'] if s['codec_type']=='audio')
checks['encoded_frames']=int(v['nb_read_frames'])==len(plan['frames']);checks['encoded_size_fps']=(v['width'],v['height'],v['avg_frame_rate'])==(1920,818,'24/1');checks['audio_stereo_48k']=au['channels']==2 and au['sample_rate']=='48000';checks['duration']=abs(float(probe['format']['duration'])-len(plan['frames'])/24)<.1
loudness=subprocess.run(['/opt/homebrew/bin/ffmpeg','-hide_banner','-i',str(movie),'-af','ebur128=peak=true','-f','null','-'],capture_output=True,text=True,timeout=120)
(out/'loudness.txt').write_text(loudness.stderr)
summary=loudness.stderr.rsplit('Summary:',1)[-1]
integrated=re.search(r'I:\s+(-?[\d.]+) LUFS',summary)
peak=re.search(r'Peak:\s+(-?[\d.]+) dBFS',summary)
audio_metrics={'integratedLUFS':float(integrated.group(1)) if integrated else None,'truePeakDbFS':float(peak.group(1)) if peak else None}
checks['complete_av_decode']=loudness.returncode==0
checks['encoded_loudness']=audio_metrics['integratedLUFS'] is not None and -22<=audio_metrics['integratedLUFS']<=-18
checks['encoded_true_peak']=audio_metrics['truePeakDbFS'] is not None and audio_metrics['truePeakDbFS']<=-1
# All-frame thumbnails plus time-indexed editorial stills for direct visual review.
for begin in range(0,len(metrics),24):
 sheet=Image.new('RGB',(1440,4*120),(12,15,17));draw=ImageDraw.Draw(sheet)
 for i,rec in enumerate(plan['frames'][begin:begin+24]):
  im=Image.open(frames/f"frame-{rec['index']:05d}.png").convert('RGB');im.thumbnail((240,103));x=(i%6)*240;y=(i//6)*120;sheet.paste(im,(x,y));draw.text((x+3,y+104),f"{rec['index']:03} | {rec['shot']} | src {rec['sourceFrame']}",fill='white')
 sheet.save(out/f"all-frames-{begin//24+1:02}.jpg",quality=93)
result={'checks':checks,'passed':all(checks.values()),'frameCount':len(metrics),'minRawMean':min(m['mean'] for m in metrics),'maxRawMean':max(m['mean'] for m in metrics),'frameMetrics':metrics,'ffprobe':probe,'audioMetrics':audio_metrics,'movieSha256':sha(movie),'visualReview':'PENDING_DIRECT_INSPECTION','listeningReview':'NOT_INFERRED_FROM_METRICS'}
(out/'audit.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['frameMetrics','ffprobe']},indent=2))
