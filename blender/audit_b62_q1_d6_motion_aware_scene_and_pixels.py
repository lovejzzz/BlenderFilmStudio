import argparse, hashlib, json, math, os, struct, sys, tempfile
from pathlib import Path
import bpy, numpy, OpenImageIO as oiio
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

FRAMES=(198,210,222,234,246,258,270,282)
CONDITIONS=(("STATIC","CAM_CLOSE_STATIC_D6"),("MOTION_AWARE","CAM_CLOSE_MOTION_D6"))
TARGET=Vector((0.0,0.67,1.72)); ROTATION=Matrix.Rotation(math.radians(-45.0),4,"Z")
ANCHORS=("B62_VISOR","B62_EYE_SLIT","B62_CHEST_LIGHT","B62_HAND_R","B62_CORE"); FACE={"B62_VISOR","B62_EYE_SLIT"}
CHARACTER={"B62_CHEST_LIGHT","B62_CHEST_PLATE","B62_EYE_SLIT","B62_FOOT_L","B62_FOOT_R","B62_FOREARM_L","B62_FOREARM_R","B62_HAND_L","B62_HAND_R","B62_HELMET","B62_NECK","B62_PELVIS","B62_SHIN_L","B62_SHIN_R","B62_SHOULDER_L","B62_SHOULDER_R","B62_THIGH_L","B62_THIGH_R","B62_TORSO","B62_UPPER_ARM_L","B62_UPPER_ARM_R","B62_VISOR"}
CORE={"B62_CORE","B62_CORE_RING_A","B62_CORE_RING_B"}

def args():
    tail=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []; p=argparse.ArgumentParser(); p.add_argument("--output",type=Path,required=True); p.add_argument("--build-report",type=Path,required=True); p.add_argument("--render-report",type=Path,required=True); p.add_argument("--derived-sha256",required=True); return p.parse_args(tail)
def req(x,m):
    if not x: raise RuntimeError(m)
def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for c in iter(lambda:f.read(1048576),b""): h.update(c)
    return h.hexdigest()
def normalize(v):
    if isinstance(v,float) and math.isfinite(v) and v.is_integer(): return int(v)
    if isinstance(v,float) and math.isfinite(v): return {"$f64be":struct.pack(">d",v).hex()}
    if isinstance(v,list): return [normalize(x) for x in v]
    if isinstance(v,dict): return {k:normalize(x) for k,x in v.items()}
    return v
def canonical(v): return json.dumps(normalize(v),ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def write(path,body):
    body=dict(body); body["reportHash"]=hashlib.sha256(canonical(body)).hexdigest(); path.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(prefix=".b62-d6-audit-",dir=path.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f: json.dump(body,f,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False); f.write("\n"); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    return body
def group(n): return "CHARACTER" if n in CHARACTER else "CORE" if n in CORE else "SCENE_OR_PROP" if n.startswith("B62_") else "OTHER"
def material_state(owner):
    owner=getattr(owner,"original",None) or owner; mats=[m for m in getattr(getattr(owner,"data",None),"materials",[]) if m]; rows=[]
    for m in mats:
        outs=[n for n in m.node_tree.nodes if n.type=="OUTPUT_MATERIAL"] if m.use_nodes and m.node_tree else []
        rows.append({"material":m.name,"surface":any(n.inputs.get("Surface") and n.inputs["Surface"].is_linked for n in outs),"volume":any(n.inputs.get("Volume") and n.inputs["Volume"].is_linked for n in outs),"outputs":len(outs)})
    passthrough=bool(rows) and all(r["outputs"] and r["volume"] and not r["surface"] for r in rows)
    return owner.name,passthrough
def trace(scene,graph,origin,heading,maximum):
    direction=heading.normalized(); cursor=origin.copy(); travelled=0.0
    for _ in range(64):
        remaining=maximum-travelled
        if remaining<=0:return None,"MISS",False
        hit,loc,_n,_f,owner,_m=scene.ray_cast(graph,cursor,direction,distance=remaining)
        if not hit or owner is None:return None,"MISS",False
        distance=float((loc-cursor).length); name,passthrough=material_state(owner)
        if passthrough: travelled+=distance+0.00001; cursor=loc+direction*0.00001; continue
        return name,group(name),False
    return None,"MISS",True
def center(obj,graph):
    ev=obj.evaluated_get(graph); return sum((ev.matrix_world@Vector(c) for c in ev.bound_box),Vector())/len(ev.bound_box)
def projection(scene,graph,camera):
    total=onscreen=0; points=[]
    for name in sorted(CHARACTER):
        ev=bpy.data.objects[name].evaluated_get(graph); mesh=ev.to_mesh(preserve_all_data_layers=False,depsgraph=graph)
        try:
            for vertex in mesh.vertices:
                total+=1; p=world_to_camera_view(scene,camera,ev.matrix_world@vertex.co)
                if p.z>0: points.append((float(p.x),float(p.y))); onscreen+=int(0<=p.x<=1 and 0<=p.y<=1)
        finally: ev.to_mesh_clear()
    req(points and total,"empty projection"); xs=[p[0] for p in points]; ys=[p[1] for p in points]; area=max(0,min(1,max(xs))-max(0,min(xs)))*max(0,min(1,max(ys))-max(0,min(ys)))
    return {"totalVertices":total,"onScreenVertices":onscreen,"onScreenVertexFraction":onscreen/total,"clampedUnionAreaFraction":area}
def geometry(scene,frame,condition,camera):
    scene.frame_set(frame); scene.camera=camera; graph=bpy.context.evaluated_depsgraph_get(); graph.update(); evaluated=camera.evaluated_get(graph); corners=evaluated.data.view_frame(scene=scene); left,right=min(c.x for c in corners),max(c.x for c in corners); bottom,top=min(c.y for c in corners),max(c.y for c in corners); z=sum(c.z for c in corners)/4; origin=evaluated.matrix_world.translation.copy(); rotation=evaluated.matrix_world.to_quaternion(); counts={}; groups={"CHARACTER":0,"CORE":0,"SCENE_OR_PROP":0,"OTHER":0,"MISS":0}
    for flat in range(32*18):
        y,x=divmod(flat,32); u,v=(x+.5)/32,(y+.5)/18; local=Vector((left+(right-left)*u,bottom+(top-bottom)*v,z)); name,g,exhausted=trace(scene,graph,origin,rotation@local,1000); req(not exhausted,"trace exhausted"); groups[g]+=1
        if name: counts[name]=counts.get(name,0)+1
    visible=[]
    for anchor in ANCHORS:
        point=center(bpy.data.objects[anchor],graph); name,_g,exhausted=trace(scene,graph,origin,point-origin,(point-origin).length+.01); req(not exhausted,"anchor exhausted")
        if name==anchor: visible.append(anchor)
    proj=projection(scene,graph,evaluated); helmet=counts.get("B62_HELMET",0)/576; character=groups["CHARACTER"]/576; feasible=FACE.issubset(visible) and helmet<=.70 and .20<=character<=.90 and .10<=proj["onScreenVertexFraction"]<=.60 and .35<=proj["clampedUnionAreaFraction"]<=.90 and len(visible)>=2
    return {"frame":frame,"condition":condition,"camera":camera.name,"objectCounts":dict(sorted(counts.items())),"groupCounts":groups,"helmetVisualBlockerShare":helmet,"characterVisualBlockerShare":character,"visibleAnchors":visible,"visibleAnchorCount":len(visible),"characterProjection":proj,"feasible":feasible}
def decode(path):
    req(oiio.VERSION_STRING=="3.1.13.1" and numpy.__version__=="2.3.4","decoder version"); image=oiio.ImageInput.open(str(path)); req(image is not None,"EXR open failed")
    try:
        matches=[]; sub=0
        while image.seek_subimage(sub,0):
            spec=image.spec(); names=list(spec.channelnames); pos={n:i for i,n in enumerate(names)}
            for n in names:
                if n.endswith(".R") and n[:-2].split(".")[-1]=="Combined":
                    wanted=[f"{n[:-2]}.{c}" for c in "RGBA"]
                    if all(c in pos for c in wanted): matches.append((sub,spec.width,spec.height,spec.nchannels,[pos[c] for c in wanted]))
            sub+=1
        req(len(matches)==1,"Combined count"); sub,w,h,n,indices=matches[0]; pixels=image.read_image(sub,0,0,n,oiio.FLOAT); values=numpy.ascontiguousarray(numpy.asarray(pixels)[...,indices],dtype=numpy.dtype("<f4")); finite=numpy.isfinite(values); minima=values.min(axis=(0,1)); maxima=values.max(axis=(0,1)); return {"width":w,"height":h,"sha256":hashlib.sha256(values.tobytes()).hexdigest(),"nonFiniteCount":int(values.size-finite.sum()),"rgbDynamicRange":float(max(maxima[:3])-min(minima[:3]))}
    finally:image.close()
def smooth_scale(frame):
    u=(frame-193)/95; return 2.0+.25*(3*u*u-2*u*u*u)
def main():
    a=args(); scene_path=Path(bpy.data.filepath).resolve(); req(scene_path.name=="B62_PHASE0_D6_MOTION_AWARE.blend" and sha(scene_path)==a.derived_sha256,"scene identity"); build=json.loads(a.build_report.read_text()); render=json.loads(a.render_report.read_text()); scene=bpy.context.scene; source=bpy.data.objects["CAM_CLOSE_REFLECTION"]; static=bpy.data.objects["CAM_CLOSE_STATIC_D6"]; motion=bpy.data.objects["CAM_CLOSE_MOTION_D6"]; req(static.data.lens==65.0 and motion.data.lens==65.0,"lens")
    bake=[]
    for frame in range(193,289):
        scene.frame_set(frame); graph=bpy.context.evaluated_depsgraph_get(); graph.update(); source_loc=source.evaluated_get(graph).matrix_world.translation; row={"frame":frame}
        for label,camera,scale in (("static",static,2.0),("motion",motion,smooth_scale(frame))):
            expected=TARGET+(ROTATION@(source_loc-TARGET))*scale; actual=camera.evaluated_get(graph).matrix_world.translation; row[f"{label}Scale"]=scale; row[f"{label}MaxLocationError"]=max(abs(actual[i]-expected[i]) for i in range(3))
        bake.append(row)
    req(max(max(r["staticMaxLocationError"],r["motionMaxLocationError"]) for r in bake)<=1e-6,"bake error")
    observations=[geometry(scene,f,c,bpy.data.objects[n]) for f in FRAMES for c,n in CONDITIONS]
    pixels=[]
    for row in render["renders"]:
        path=a.render_report.parent/row["exr"]["uri"]; decoded=decode(path); req(sha(path)==row["exr"]["sha256"] and decoded["sha256"]==row["combined"]["sha256"],"pixel mismatch"); pixels.append({"frame":row["frame"],"condition":row["condition"],"exrSha256":sha(path),"combined":decoded})
    motion_pass=all(r["feasible"] for r in observations if r["condition"]=="MOTION_AWARE"); static_passed=[r["frame"] for r in observations if r["condition"]=="STATIC" and r["feasible"]]; static_failed=[r["frame"] for r in observations if r["condition"]=="STATIC" and not r["feasible"]]
    report=write(a.output,{"schemaVersion":"bfs.b62CameraQualityMotionAwareIndependentHoldoutAudit.v0.1","experimentId":"B62-Q1-D6","status":"PASS","derivedScene":{"sha256":a.derived_sha256},"buildReportHash":build["reportHash"],"renderReportHash":render["reportHash"],"bake":bake,"geometry":observations,"pixels":pixels,"outcome":{"motionAllPass":motion_pass,"staticPassedFrames":static_passed,"staticFailedFrames":static_failed},"blender":{"version":bpy.app.version_string,"buildHash":bpy.app.build_hash.decode()},"operations":{"blenderStarts":1,"renderCalls":0,"modelCalls":0,"networkCalls":0,"dockerProcesses":0}}); print(f"BFS_B62_Q1_D6_INDEPENDENT PASS motion={motion_pass} report={report['reportHash']}")
if __name__=="__main__":main()
