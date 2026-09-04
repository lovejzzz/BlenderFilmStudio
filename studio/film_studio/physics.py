"""Native Bullet kinetic asset and independently inspectable event measurements."""

import math
import json
from pathlib import Path
import bpy
from mathutils import Vector
from .assets import box, sphere, text, tag


def rigid(obj,active=True,shape='BOX',mass=.15):
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    bpy.ops.rigidbody.object_add();r=obj.rigid_body;r.type='ACTIVE' if active else 'PASSIVE';r.collision_shape=shape
    r.mass=mass;r.friction=.48;r.restitution=.12;r.use_margin=True;r.collision_margin=.001
    r.linear_damping=.05;r.angular_damping=.1;r.use_deactivation=False
    obj.select_set(False)


def kinetic_run(root,p,m,end):
    count=int(p.get('count',8));spacing=p.get('spacing',.19);release=int(p.get('release',36))
    # All dimensions are metric initial geometry. No response or final poses.
    support=box('KINETIC_SUPPORT',(.2,0,-.045),(3.4,.72,.09),m['ebony'],root,.01);rigid(support,False)
    verts=[(-1.45,-.18,0),(-.35,-.18,0),(-.35,.18,0),(-1.45,.18,0),(-1.45,-.18,.33),(-.35,-.18,.025),(-.35,.18,.025),(-1.45,.18,.33)]
    faces=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    mesh=bpy.data.meshes.new('Passive ramp');mesh.from_pydata(verts,[],faces);mesh.update()
    ramp=bpy.data.objects.new('KINETIC_RAMP',mesh);bpy.context.scene.collection.objects.link(ramp);tag(ramp,root,m['brass']);rigid(ramp,False,'CONVEX_HULL')
    for y in [-.184,.184]:
        rail=box('Ramp edge',(-.9,y,.188),(1.14,.015,.016),m['brass'],root,.003);rail.rotation_euler[1]=math.atan(.305/1.1)
    radius=p.get('size',.16)
    ball=sphere('KINETIC_BALL',(-1.27,0,.282+radius),radius,m['chrome'],root);rigid(ball,True,'SPHERE',.45);ball['pf_solver_role']='initiator'
    ball.rigid_body.kinematic=True;ball.keyframe_insert('rigid_body.kinematic',frame=1);ball.keyframe_insert('rigid_body.kinematic',frame=release-1)
    ball.rigid_body.kinematic=False;ball.keyframe_insert('rigid_body.kinematic',frame=release)
    for i in range(count):
        o=box(f'KINETIC_TARGET_{i+1:02}',(i*spacing,0,.145),(.056,.19,.29),m['black'],root,.004)
        o.data.materials.append(m['brass']);o.modifiers['Machined edge'].affect='EDGES';o.modifiers['Machined edge'].material=1
        rigid(o,True,'BOX',.13);o['pf_solver_role']='target'
        text('Engraved sequence',f'{i+1:02}',(0,-.097,-.04),.035,m['brass'],o)
        box('Inset gold line',(0,-.096,.07),(.033,.001,.002),m['brass'],o,.0002)
    world=bpy.context.scene.rigidbody_world;world.substeps_per_frame=8;world.solver_iterations=40;world.time_scale=.7
    world.point_cache.frame_start=1;world.point_cache.frame_end=end


def bake_and_measure(scene,end):
    if not scene.rigidbody_world:return {'start':1},{}
    scene.frame_start=1;scene.frame_end=end;scene.frame_set(1);bpy.context.view_layer.update()
    pc=scene.rigidbody_world.point_cache
    with bpy.context.temp_override(scene=scene,point_cache=pc):bpy.ops.ptcache.bake(bake=True)
    targets=sorted((o for o in scene.objects if o.get('pf_solver_role')=='target'),key=lambda o:o.name)
    ball=next(o for o in scene.objects if o.get('pf_solver_role')=='initiator')
    records=[];initial=None;previous=None;contact=None;peak=(0,1);settled=None;quiet=0;responses={}
    for f in range(1,end+1):
        scene.frame_set(f);dg=bpy.context.evaluated_depsgraph_get();now={}
        for o in [ball]+targets:
            e=o.evaluated_get(dg);mat=e.matrix_world;pos=mat.translation.copy();rot=mat.to_quaternion();now[o.name]=(pos,rot)
        if initial is None:initial=now
        for o in targets:
            angle=math.degrees(initial[o.name][1].rotation_difference(now[o.name][1]).angle)
            if angle>1 and o.name not in responses:responses[o.name]=f
        first=targets[0];fp=now[first.name][0];bp=now[ball.name][0]
        radius=ball.dimensions.x/2
        if contact is None and bp.x+radius+.001 >= fp.x-.029 and abs(bp.y-fp.y)<.18 and bp.z-radius<fp.z+.146:
            contact=f
        speed=0;travel=0
        if previous:
            speed=sum(math.degrees(previous[o.name][1].rotation_difference(now[o.name][1]).angle) for o in targets)
            travel=max((previous[o.name][0]-now[o.name][0]).length for o in targets)
        if speed>peak[0]:peak=(speed,f)
        if len(responses)==len(targets) and speed<.05 and travel<.0005:
            quiet+=1
            if quiet>=12 and settled is None:settled=f-11
        else:quiet=0
        records.append({'frame':f,'positions':{k:[round(c,8) for c in v[0]] for k,v in now.items()},'rotations':{k:[round(c,8) for c in v[1]] for k,v in now.items()},'angularStepDegrees':round(speed,7)})
        previous=now
    diagnostic={'contact':contact,'responses':responses,'settled':settled,'frames':records}
    diagnostic_root=scene.get('pf_diagnostic_directory')
    if diagnostic_root:(Path(diagnostic_root)/'physics-measurements.json').write_text(json.dumps(diagnostic))
    if contact is None or len(responses)<max(2,len(targets)-1) or settled is None:
        raise RuntimeError(f'Kinetic motion incomplete: contact={contact}, responses={responses}, settled={settled}')
    events={'start':1,'contact':contact,'peak':peak[1],'settled':settled}
    return events,{'events':events,'responses':responses,'pointCacheBaked':pc.is_baked,'frames':records,'targetCount':len(targets),'motionAuthority':'BLENDER_BULLET','postReleasePoseKeys':0}
