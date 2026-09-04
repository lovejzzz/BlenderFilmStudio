import argparse,json
from pathlib import Path
from PIL import Image,ImageDraw
p=argparse.ArgumentParser();p.add_argument('frames');p.add_argument('output');a=p.parse_args();root=Path(a.frames);out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
frames=sorted(root.glob('frame-*.png'));plan=json.loads((root/'render-plan.json').read_text())
if len(frames)!=len(plan['frames']):raise SystemExit('Incomplete sequence')
for start in range(0,len(frames),16):
 canvas=Image.new('RGB',(1280,4*158),(13,17,20));d=ImageDraw.Draw(canvas)
 for j,file in enumerate(frames[start:start+16]):
  im=Image.open(file).convert('RGB');im.thumbnail((320,136));x=(j%4)*320;y=(j//4)*158;canvas.paste(im,(x,y));f=plan['frames'][start+j];d.text((x+5,y+138),f"{f['index']:03} / {f['shot']} / source {f['sourceFrame']}",fill='white')
 canvas.save(out/f'sheet-{start//16+1:02}.jpg',quality=94)
print(len(frames),'frames;',len(list(out.glob('sheet-*'))),'sheets')
