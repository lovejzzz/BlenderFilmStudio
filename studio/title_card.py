"""Render an original transparent title overlay using the local Pillow runtime."""
import json,sys
from PIL import Image,ImageDraw,ImageFont
p=json.loads(sys.argv[1]);im=Image.new('RGBA',(p['width'],p['height']),(0,0,0,0));d=ImageDraw.Draw(im)
latin=all(ord(c)<128 for c in p['title']);text=' '.join(p['title'].upper()) if latin else p['title']
font_path='/System/Library/Fonts/Supplemental/Arial.ttf' if latin else '/System/Library/Fonts/STHeiti Medium.ttc'
size=round(p['width']*.015);font=ImageFont.truetype(font_path,size);bounds=d.textbbox((0,0),text,font=font)
if bounds[2]-bounds[0]>p['width']*.9:
    size=max(8,int(size*p['width']*.9/(bounds[2]-bounds[0])));font=ImageFont.truetype(font_path,size)
d.text((round(p['width']*.05),round(p['height']*.075)),text,font=font,fill=p['color'])
im.save(p['output'])
