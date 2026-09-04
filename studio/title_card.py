"""Render an original transparent title overlay using the local Pillow runtime."""
import json,sys
from PIL import Image,ImageDraw,ImageFont
p=json.loads(sys.argv[1]);im=Image.new('RGBA',(p['width'],p['height']),(0,0,0,0));d=ImageDraw.Draw(im)
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',round(p['width']*.015))
d.text((round(p['width']*.05),round(p['height']*.075)),' '.join(p['title'].upper()),font=font,fill=p['color'])
im.save(p['output'])
