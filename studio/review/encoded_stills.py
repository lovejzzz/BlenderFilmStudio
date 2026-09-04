"""Extract indexed encoded-film checks without touching movie or render sources."""
import argparse,subprocess,json,hashlib
from pathlib import Path
from PIL import Image,ImageDraw
p=argparse.ArgumentParser();p.add_argument('movie');p.add_argument('output');p.add_argument('--frames',required=True);a=p.parse_args();movie=Path(a.movie);out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
frames=[int(v) for v in a.frames.split(',')];expression='+'.join(f'eq(n,{n-1})' for n in frames)
subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-nostdin','-n','-i',str(movie),'-vf',f"select='{expression}'", '-fps_mode','vfr',str(out/'encoded-%03d.png')],check=True,timeout=120)
images=sorted(out.glob('encoded-*.png'));assert len(images)==len(frames)
for start in range(0,len(images),12):
 sheet=Image.new('RGB',(1440,4*218),(14,15,18));draw=ImageDraw.Draw(sheet)
 for j,(frame,path) in enumerate(list(zip(frames,images))[start:start+12]):
  with Image.open(path) as im:
   im=im.convert('RGB');im.thumbnail((480,205));x=j%3*480;y=j//3*218;sheet.paste(im,(x,y));draw.text((x+4,y+204),f'Encoded frame {frame} | {(frame-1)/24:.3f}s',fill='white')
 sheet.save(out/f'encoded-sheet-{start//12+1:02}.jpg',quality=94)
(out/'manifest.json').write_text(json.dumps({'movie':str(movie),'movieSha256':hashlib.sha256(movie.read_bytes()).hexdigest(),'frames':frames},indent=2))
