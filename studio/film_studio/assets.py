"""Procedural, metric asset library shared by all personal studio projects."""

from __future__ import annotations

import math
import random
from pathlib import Path
import bpy
from mathutils import Vector


def material(name, color, metal=0, rough=.45, texture=0, emission=0, transmission=0):
    m=bpy.data.materials.get('PF_'+name)
    if m:return m
    m=bpy.data.materials.new('PF_'+name);m.use_nodes=True
    n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    bs.inputs['Transmission Weight'].default_value=transmission
    if emission:
        bs.inputs['Emission Color'].default_value=(*color,1);bs.inputs['Emission Strength'].default_value=emission
    if texture:
        tc=n.new('ShaderNodeTexCoord');sc=n.new('ShaderNodeVectorMath');sc.operation='MULTIPLY';sc.inputs[1].default_value=(1,1,1)
        l.new(tc.outputs['Generated'],sc.inputs[0]);no=n.new('ShaderNodeTexNoise');no.inputs['Scale'].default_value=texture;no.inputs['Detail'].default_value=3;l.new(sc.outputs[0],no.inputs['Vector'])
        bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.16;bump.inputs['Distance'].default_value=.0003;l.new(no.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],bs.inputs['Normal'])
        ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(*(c*.72 for c in color),1);ramp.color_ramp.elements[1].color=(*(min(1,c*1.2) for c in color),1)
        l.new(no.outputs['Fac'],ramp.inputs[0]);l.new(ramp.outputs[0],bs.inputs['Base Color'])
        if name in {'walnut','oak'}:
            sc.inputs[1].default_value=(1,28,16);no.inputs['Scale'].default_value=3.8;no.inputs['Roughness'].default_value=.75
            bump.inputs['Distance'].default_value=.0006
    return m


def palette():
    return {
      'walnut':material('walnut',(.115,.042,.018),rough=.32,texture=4),
      'oak':material('oak',(.36,.22,.11),rough=.46,texture=5),
      'brass':material('brass',(.48,.275,.075),metal=.86,rough=.27,texture=240),
      'silver':material('silver',(.48,.53,.56),metal=.91,rough=.29,texture=310),
      'chrome':material('chrome',(.7,.76,.8),metal=1,rough=.12),
      'black':material('black',(.013,.019,.022),metal=.22,rough=.32,texture=160),
      'rubber':material('rubber',(.008,.009,.009),rough=.69,texture=130),
      'tape':material('tape',(.075,.029,.011),rough=.43,texture=180),
      'ivory':material('ivory',(.75,.68,.51),rough=.4,texture=120),
      'paper':material('paper',(.55,.5,.38),rough=.8,texture=140),
      'plaster':material('plaster',(.57,.5,.39),rough=.81,texture=95),
      'teal':material('teal',(.023,.063,.061),rough=.73,texture=75),
      'stone':material('stone',(.38,.34,.28),rough=.65,texture=100),
      'ebony':material('ebony',(.017,.019,.018),rough=.31,texture=160),
      'amber':material('amber',(.96,.36,.065),rough=.3,emission=2.0),
      'red':material('red',(.48,.015,.008),rough=.32,emission=.7),
      'glass':material('glass',(.92,.98,1),rough=.06,transmission=1),
      'green':material('green',(.044,.105,.026),rough=.43),
      'clay':material('clay',(.28,.09,.038),rough=.8,texture=120),
    }


def tag(obj, root, mat=None):
    obj.parent=root
    obj['pf_asset']=root.name
    if mat:obj.data.materials.append(mat)
    return obj


def empty(name,parent=None,loc=(0,0,0)):
    o=bpy.data.objects.new(name,None);bpy.context.scene.collection.objects.link(o);o.location=loc;o.parent=parent
    return o


def box(name,loc,dims,mat,root,bevel=.003):
    x,y,z=(v/2 for v in dims)
    verts=[(-x,-y,-z),(-x,-y,z),(-x,y,-z),(-x,y,z),(x,-y,-z),(x,-y,z),(x,y,-z),(x,y,z)]
    faces=[(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(o);o.location=loc;tag(o,root,mat)
    if bevel:
        b=o.modifiers.new('Machined edge','BEVEL');b.width=min(bevel,min(dims)*.25);b.segments=3
        n=o.modifiers.new('Face normals','WEIGHTED_NORMAL');n.keep_sharp=True
    return o


def cylinder(name,loc,radius,depth,mat,root,rotation=(0,0,0),vertices=64):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=loc)
    o=bpy.context.object;o.name=name;o.rotation_euler=rotation;tag(o,root,mat)
    b=o.modifiers.new('Edge glint','BEVEL');b.width=min(.0015,depth*.15);b.segments=2
    o.modifiers.new('Face normals','WEIGHTED_NORMAL')
    return o


def sphere(name,loc,radius,mat,root,scale=(1,1,1)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=radius,location=loc)
    o=bpy.context.object;o.name=name;o.scale=scale;tag(o,root,mat)
    for p in o.data.polygons:p.use_smooth=True
    return o


def torus(name,loc,radius,minor,mat,root,rotation=(0,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=radius,minor_radius=minor,major_segments=72,minor_segments=12,location=loc,rotation=rotation)
    o=bpy.context.object;o.name=name;tag(o,root,mat)
    for p in o.data.polygons:p.use_smooth=True
    return o


def curve(name,points,radius,mat,root):
    c=bpy.data.curves.new(name,'CURVE');c.dimensions='3D';c.resolution_u=12;c.bevel_depth=radius;c.bevel_resolution=3
    s=c.splines.new('POLY');s.points.add(len(points)-1)
    for p,v in zip(s.points,points):p.co=(*v,1)
    o=bpy.data.objects.new(name,c);bpy.context.scene.collection.objects.link(o);tag(o,root,mat);return o


def text(name,body,loc,size,mat,root,rotation=(math.pi/2,0,0),align='CENTER'):
    c=bpy.data.curves.new(name,'FONT');c.body=body;c.size=size;c.align_x=align;c.extrude=.00008;c.space_character=1.18
    font=Path('/System/Library/Fonts/Supplemental/Arial.ttf')
    if font.exists():
        c.font=bpy.data.fonts.get('Arial') or bpy.data.fonts.load(str(font))
    o=bpy.data.objects.new(name,c);bpy.context.scene.collection.objects.link(o);o.location=loc;o.rotation_euler=rotation;tag(o,root,mat);return o


def lathe(name,profile,mat,root,loc=(0,0,0),segments=80):
    verts=[];faces=[]
    for r,z in profile:
        verts.extend((r*math.cos(2*math.pi*i/segments),r*math.sin(2*math.pi*i/segments),z) for i in range(segments))
    for j in range(len(profile)-1):
        for i in range(segments):
            a=j*segments+i;b=j*segments+(i+1)%segments;faces.append((a,b,b+segments,a+segments))
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(o);o.location=loc;tag(o,root,mat)
    for p in me.polygons:p.use_smooth=True
    return o


def key_rotation(obj,axis,keys):
    for frame,value in keys:
        obj.rotation_euler[axis]=value;obj.keyframe_insert('rotation_euler',index=axis,frame=frame)
    try:
        for fc in obj.animation_data.action.fcurves:
            for k in fc.keyframe_points:k.interpolation='LINEAR'
    except AttributeError:pass


def reel_transport(root,p,m,end):
    box('Walnut cabinet',(0,.035,.44),(1.06,.31,.88),m['walnut'],root,.023)
    box('Anodized face',(0,-.135,.44),(.99,.025,.82),m['silver'],root,.009)
    box('Lower fascia',(0,-.154,.13),(.97,.012,.19),m['black'],root,.004)
    # Dark hairline panel joints and fitted case hardware.
    for x in [-.47,.47]:
        for z in [.08,.82]:
            cylinder('Case screw',(x,-.154,z),.006,.004,m['chrome'],root,(math.pi/2,0,0),24)
            box('Screw slot',(x,-.157,z),(.007,.001,.001),m['black'],root,0)
    for x in [-.27,.27]:
        reel=empty('Transport reel',root,(x,-.205,.64))
        cylinder('Tape pack',(0,0,0),.187,.026,m['tape'],reel,(math.pi/2,0,0),96)
        # Concentric tape edges catch small specular highlights.
        for k in range(7):torus('Tape winding',(0,-.015,0),.078+k*.017,.0008,m['tape'],reel,(math.pi/2,0,0))
        torus('Reel rim',(0,-.023,0),.207,.005,m['silver'],reel,(math.pi/2,0,0))
        torus('Inner machined ring',(0,-.026,0),.075,.009,m['silver'],reel,(math.pi/2,0,0))
        cylinder('Reel hub',(0,-.027,0),.038,.021,m['black'],reel,(math.pi/2,0,0))
        cylinder('Reel lock',(0,-.043,0),.019,.013,m['chrome'],reel,(math.pi/2,0,0))
        for a in [0,2*math.pi/3,4*math.pi/3]:
            spoke=box('Reel spoke',(.138*math.sin(a),-.024,.138*math.cos(a)),(.036,.012,.127),m['silver'],reel,.009);spoke.rotation_euler[1]=a
            cylinder('Hub fastener',(.053*math.sin(a),-.039,.053*math.cos(a)),.004,.005,m['black'],reel,(math.pi/2,0,0),24)
        key_rotation(reel,1,[(1,0),(36,0),(end-48,18*math.pi),(end,18.25*math.pi)])
    # The transport path remains taut across the guides and head.
    curve('Magnetic tape',[(-.435,-.21,.53),(-.34,-.21,.35),(-.16,-.21,.30),(.16,-.21,.30),(.34,-.21,.35),(.435,-.21,.53)],.0032,m['tape'],root)
    for x,z in [(-.34,.35),(.34,.35),(-.16,.30),(.16,.30)]:
        cylinder('Guide roller',(x,-.21,z),.026,.033,m['chrome'],root,(math.pi/2,0,0))
        cylinder('Guide screw',(x,-.229,z),.009,.006,m['black'],root,(math.pi/2,0,0))
    box('Head block',(0,-.191,.322),(.195,.07,.073),m['black'],root,.008)
    box('Head polished cover',(0,-.23,.336),(.135,.006,.035),m['chrome'],root,.003)
    for x in [-.235,.235]:
        box('Meter bezel',(x,-.173,.21),(.2,.025,.104),m['black'],root,.008)
        box('Meter scale',(x,-.188,.213),(.176,.008,.081),m['ivory'],root,.003)
        for k in range(9):
            xx=x-.073+k*.018;tick=box('VU scale tick',(xx,-.195,.231),(.001,.001,.012 if k%2==0 else .007),m['red'] if k>6 else m['black'],root,0)
        text('Meter legend','VU',(x,-.195,.186),.014,m['black'],root)
        needle=empty('VU needle pivot',root,(x,-.198,.174));box('Needle',(0,0,.031),(.0015,.0015,.061),m['black'],needle,0)
        keys=[(f,.65*math.sin(f*.17+(0 if x<0 else .8))+.2*math.sin(f*.41)) for f in range(36,end-32,6)]
        key_rotation(needle,1,[(1,-.75),(35,-.75)]+keys+[(end,-.75)])
    for i in range(6):
        x=-.145+i*.058;box('Transport button',(x,-.175,.07),(.045,.043,.032),m['silver'] if i!=4 else m['red'],root,.004)
    for x in [-.4,.4]:
        cylinder('Level knob',(x,-.19,.13),.035,.045,m['black'],root,(math.pi/2,0,0))
        cylinder('Knob cap',(x,-.216,.13),.027,.003,m['silver'],root,(math.pi/2,0,0))
        box('Knob index',(x,-.22,.147),(.0015,.001,.008),m['black'],root,0)
    text('Brand','C Y G N U S',(0,-.153,.842),.024,m['black'],root)
    text('Model','STEREO  /  FIELD RECORDER',(0,-.162,.406),.012,m['black'],root)
    text('Transport labels','REW     STOP     PLAY     REC',(0,-.166,.027),.009,m['ivory'],root)
    for x in [-.42,.42]:
        box('Rubber foot',(x,0,-.013),(.10,.19,.032),m['rubber'],root,.006)
    for side in [-1,1]:
        for k in range(12):box('Vent',(side*.531,.014+k*.014,.60),(.002,.006,.15),m['black'],root,.001)
    curve('Power cable',[(.45,.18,.1),(.58,.28,.02),(.76,.40,.012),(1.03,.43,.01),(1.2,.4,-.3)],.008,m['rubber'],root)


def table(root,p,m,end):
    dims=p.get('dimensions',[2.8,1.5,.08]);mat=m[p.get('material','walnut')]
    box('Solid tabletop',(0,0,0),dims,mat,root,.016)
    for x in [-dims[0]*.40,dims[0]*.40]:
        for y in [-dims[1]*.37,dims[1]*.37]:box('Table leg',(x,y,-.41),(.07,.07,.77),m['black'],root,.006)
    for i in range(3):box('Drawer',(0,-dims[1]/2+.065,-.13-i*.13),(.50,.09,.105),mat,root,.004)


def room(root,p,m,end):
    width,depth,height=p.get('dimensions',[8,7,4.5]);wall=m[p.get('material','teal')]
    box('Floor',(0,0,-.055),(width,depth,.1),m['oak'] if p.get('material')=='teal' else m['stone'],root,.002)
    box('Back wall',(0,depth/2,height/2),(width,.15,height),wall,root,.01)
    box('Side wall',(-width/2,0,height/2),(.15,depth,height),wall,root,.01)
    box('Skirting',(0,depth/2-.1,.10),(width,.03,.20),m['black'],root,.004)
    for x in range(-3,4):box('Wall panel stile',(x*.85,depth/2-.085,height/2),(.025,.025,height-.3),wall,root,.002)
    for i in range(22):box('Floor plank seam',(-width/2+i*width/22,0,-.0005),(.002,depth,.001),m['black'],root,0)


def window(root,p,m,end):
    w,h=p.get('dimensions',[2.3,.1,2.0])[0::2]
    for x in [-w/2,w/2]:box('Window jamb',(x,0,h/2),(.06,.12,h+.12),m['black'],root,.003)
    for z in [0,h]:box('Window crossbar',(0,0,z),(w+.06,.12,.055),m['black'],root,.003)
    box('Window mullion',(0,0,h/2),(.035,.08,h),m['black'],root,.002)
    for i in range(14):
        slat=box('Venetian slat',(0,-.06,.08+i*h/14),(w,.13,.012),m['walnut'],root,.002);slat.rotation_euler[0]=-.35
    for x in [-w*.3,w*.3]:curve('Blind cord',[(x,-.055,.02),(x,-.055,h)],.002,m['ivory'],root)


def desk_lamp(root,p,m,end):
    cylinder('Lamp base',(0,0,.025),.16,.05,m['black'],root)
    torus('Base brass trim',(0,0,.049),.15,.003,m['brass'],root)
    curve('Lamp arm',[(0,0,.05),(0,0,.35),(.08,0,.60),(.22,0,.67)],.018,m['brass'],root)
    shade=lathe('Enamel shade',[(.20,0),(.195,.02),(.12,.12),(.08,.17),(.02,.17)],m['black'],root,(.22,0,.55))
    inner=lathe('Shade reflector',[(.188,.007),(.115,.108),(.075,.155)],m['ivory'],root,(.22,0,.55))
    sphere('Warm bulb',(.22,0,.605),.039,m['amber'],root)
    torus('Shade rolled rim',(.22,0,.555),.195,.004,m['brass'],root)


def papers(root,p,m,end):
    for i in range(5):
        q=box('Archival paper',(i*.004,i*.003,.001+i*.0012),(.31,.22,.0006),m['paper'],root,0);q.rotation_euler[2]=i*.014
    for i,body in enumerate(['TRANSMISSION LOG','STATION 07 / NIGHT WATCH','23:59     CARRIER DETECTED','________________________________','FREQUENCY       104.7 kHz']):
        text('Log line',body,(-.133,.072-i*.029,.008),.012 if i else .02,m['black'],root,(0,0,0),'LEFT')
    pen=cylinder('Pencil',(.05,-.10,.013),.005,.25,m['black'],root,(0,math.pi/2,.32));cylinder('Pencil ferrule',(.169,-.06,.013),.0055,.025,m['brass'],root,(0,math.pi/2,.32))


def city(root,p,m,end):
    rng=random.Random(p.get('seed',17))
    for i in range(20):
        x=rng.uniform(-4,4);z=rng.uniform(.4,3)
        box('Distant building',(x,1.5,z/2),(.25,1,z),m['black'],root,0)
        for j in range(5):
            col=(1,.42,.10) if rng.random()<.5 else (.08,.33,.8)
            em=material('city_'+str(i%4)+str(j%2),col,emission=3)
            box('Distant window',(x,1,z*.2+j*.30),(.025,.01,.065),em,root,0)


def plinth(root,p,m,end):
    box('Display slab',(0,0,0),p.get('dimensions',[2.5,.65,.09]),m[p.get('material','ebony')],root,.01)
    for x in [-.85,.85]:box('Slab foot',(x,0,-.10),(.28,.35,.16),m['brass'],root,.007)


def plant(root,p,m,end):
    lathe('Terracotta pot',[(.08,0),(.12,.25),(.14,.26),(.14,.29),(.122,.29),(.11,.04),(.08,0)],m['clay'],root)
    cylinder('Soil',(0,0,.255),.12,.01,m['tape'],root)
    rng=random.Random(12)
    for i in range(12):
        a=i*2.399;h=rng.uniform(.5,1.1);tip=(.3*math.cos(a),.3*math.sin(a),h)
        curve('Plant stem',[(0,0,.25),(.1*math.cos(a),.1*math.sin(a),h*.7),tip],.003,m['green'],root)
        leaf=sphere('Leaf',tip,.12,m['green'],root,(.40,1.5,.055));leaf.rotation_euler=(.25,a*.2,a)


def arch(root,p,m,end):
    radius=1.4
    for i in range(31):
        a=math.pi*i/30;pos=(radius*math.cos(a),0,1.65+radius*math.sin(a))
        o=box('Arch voussoir',pos,(.15,.32,.18),m['plaster'],root,.002);o.rotation_euler[1]=math.pi/2-a
    for x in [-radius,radius]:box('Arch pier',(x,0,.825),(.18,.32,1.65),m['plaster'],root,.006)


def curtain(root,p,m,end):
    verts=[];faces=[];n=80
    for z in [0,2.8]:
        for i in range(n):
            x=i*1.5/(n-1);verts.append((x,.05*math.sin(i*.7),z))
    for i in range(n-1):faces.append((i,i+1,n+i+1,n+i))
    me=bpy.data.meshes.new('Curtain');me.from_pydata(verts,[],faces);o=bpy.data.objects.new('Linen curtain',me);bpy.context.scene.collection.objects.link(o);tag(o,root,m['ivory'])
    s=o.modifiers.new('Fabric thickness','SOLIDIFY');s.thickness=.002


def build_asset(asset,m,end):
    root=empty(asset['id']);root['pf_role']=asset['factory']
    root.location=asset['position'];root.rotation_euler=[math.radians(x) for x in asset['rotation']];root.scale=(asset['scale'],)*3
    funcs={'reel_transport':reel_transport,'table':table,'room':room,'window':window,'desk_lamp':desk_lamp,'papers':papers,'city':city,'plinth':plinth,'plant':plant,'arch':arch,'curtain':curtain}
    if asset['factory']=='text':
        p=asset['params'];text('Typography',p.get('text',''),(0,0,0),p.get('size',.04),m[p.get('material','ivory')],root)
    elif asset['factory']=='kinetic_run':
        from .physics import kinetic_run
        kinetic_run(root,asset['params'],m,end)
    else:funcs[asset['factory']](root,asset['params'],m,end)
    return root
