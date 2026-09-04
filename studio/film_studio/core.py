"""Pure, bounded document operations. No Blender, network or code execution."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re

VERSION = "personal-film/1"
FACTORIES = {"reel_transport", "table", "room", "window", "desk_lamp", "papers", "text", "city", "kinetic_run", "plinth", "plant", "arch", "curtain"}
OPERATIONS = {"camera_distance", "camera_orbit", "lens", "focus", "cut_offset", "warmth", "exposure", "reject"}


class StudioError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def exact(value, keys, name):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise StudioError(f"{name}: expected fields {sorted(keys)}")


def number(v, lo, hi, name):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not lo <= v <= hi:
        raise StudioError(f"{name}: expected finite number in [{lo}, {hi}]")


def vector(v, n, lo, hi, name):
    if not isinstance(v, list) or len(v) != n:
        raise StudioError(f"{name}: expected {n} values")
    for x in v:
        number(x, lo, hi, name)


def identifier(v):
    if not isinstance(v, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", v):
        raise StudioError("Invalid stable identifier")


def validate(doc):
    exact(doc, {"schema", "id", "title", "revision", "fps", "simulation_end", "world", "assets", "lights", "shots", "sound"}, "project")
    if doc["schema"] != VERSION:
        raise StudioError("Unsupported project version")
    identifier(doc["id"])
    if not isinstance(doc["title"], str) or len(doc["title"]) > 100:
        raise StudioError("Invalid title")
    number(doc["revision"], 1, 100000, "revision")
    number(doc["fps"], 24, 24, "fps")
    number(doc["simulation_end"], 96, 1200, "simulation_end")
    exact(doc["world"], {"color", "strength", "exposure", "warmth"}, "world")
    vector(doc["world"]["color"], 3, 0, 1, "world color")
    number(doc["world"]["strength"], 0, 2, "world strength")
    number(doc["world"]["exposure"], -4, 4, "exposure")
    number(doc["world"]["warmth"], -1, 1, "warmth")
    if type(doc["revision"]) is not int or type(doc["simulation_end"]) is not int:raise StudioError("Revision and simulation frames must be integers")
    ids=set()
    if not isinstance(doc["assets"], list) or not 1 <= len(doc["assets"]) <= 80:
        raise StudioError("Expected 1-80 assets")
    for a in doc["assets"]:
        exact(a, {"id", "factory", "position", "rotation", "scale", "params"}, "asset")
        identifier(a["id"])
        if a["id"] in ids or a["factory"] not in FACTORIES:
            raise StudioError("Duplicate asset or unsupported factory")
        ids.add(a["id"])
        vector(a["position"], 3, -50, 50, "position")
        vector(a["rotation"], 3, -360, 360, "rotation")
        number(a["scale"], .05, 20, "scale")
        if not isinstance(a["params"], dict):
            raise StudioError("Invalid asset parameters")
        allowed={"material", "dimensions", "text", "size", "color", "count", "spacing", "release", "speed", "amplitude", "seed", "opening"}
        if set(a["params"]) - allowed:
            raise StudioError("Unknown or executable asset parameter")
        for k,v in a["params"].items():
            if k == "opening": vector(v,4,-30,30,k)
            elif k == "dimensions": vector(v,3,.001,30,k)
            elif k == "color": vector(v,3,0,1,k)
            elif k in {"text","material"}:
                if not isinstance(v,str) or len(v)>500:raise StudioError("Invalid text parameter")
            else:number(v,0,1200,k)
        if 'count' in a['params'] and (type(a['params']['count']) is not int or not 2<=a['params']['count']<=24):raise StudioError('Count must be 2-24')
        if a['factory']=='kinetic_run':
            if a['scale']!=1 or a['rotation']!=[0,0,0]:raise StudioError('Kinetic assets require unit scale and zero rotation')
            if 'size' in a['params']:number(a['params']['size'],.05,.25,'ball radius')
            if 'spacing' in a['params']:number(a['params']['spacing'],.08,.3,'spacing')
        if 'opening' in a['params']:
            cx,w,sill,h=a['params']['opening'];dims=a['params'].get('dimensions',[8,7,4.5])
            if w<=0 or sill<=0 or h<=0 or abs(cx)+w/2>=dims[0]/2 or sill+h>=dims[2]:raise StudioError('Opening must fit inside wall')
    if sum(a['factory']=='kinetic_run' for a in doc['assets'])>1:raise StudioError('One kinetic assembly per project')
    if not isinstance(doc["lights"],list) or not 1 <= len(doc["lights"]) <= 16:
        raise StudioError("Expected 1-16 lights")
    for l in doc["lights"]:
        exact(l,{"id","type","position","target","color","power","size","role"},"light")
        identifier(l["id"])
        if l["id"] in ids or l["type"] not in {"AREA","POINT","SPOT"} or l["role"] not in {"key","fill","rim","practical"}:
            raise StudioError("Invalid light")
        ids.add(l["id"])
        vector(l["position"],3,-50,50,"light position");vector(l["target"],3,-50,50,"light target")
        vector(l["color"],3,0,1,"light color");number(l["power"],0,5000,"light power");number(l["size"],.01,10,"light size")
    if not isinstance(doc["shots"],list) or not 1<=len(doc["shots"])<=12:
        raise StudioError("Expected 1-12 shots")
    shot_ids=set()
    for s in doc["shots"]:
        exact(s,{"id","label","target","aim_offset","anchor","offset","duration","lens","distance","azimuth","elevation","travel","fstop","focus_offset"},"shot")
        identifier(s["id"])
        if s["id"] in shot_ids or s["target"] not in {a["id"] for a in doc["assets"]}:
            raise StudioError("Invalid shot target or duplicate ID")
        shot_ids.add(s["id"])
        if s["anchor"] not in {"start","contact","peak","settled"}:
            raise StudioError("Unknown event anchor")
        if not isinstance(s["label"],str) or len(s["label"])>100:raise StudioError("Invalid shot label")
        vector(s["aim_offset"],3,-10,10,"aim offset")
        for k,lo,hi in [("offset",-240,1000),("duration",24,240),("lens",18,135),("distance",.1,30),("azimuth",-360,360),("elevation",-40,85),("travel",-.6,.6),("fstop",1.4,32),("focus_offset",-3,3)]:
            number(s[k],lo,hi,k)
        if not isinstance(s["duration"],int) or not isinstance(s["offset"],int):raise StudioError("Frame fields must be integers")
    if sum(s["duration"] for s in doc["shots"])>1200:raise StudioError("Movie exceeds 50-second product budget")
    exact(doc["sound"],{"style","gain"},"sound")
    if doc["sound"]["style"] not in {"tape","kinetic","none"}:raise StudioError("Unsupported sound style")
    number(doc["sound"]["gain"],0,1,"sound gain")
    return doc


def apply_patch(doc, proposal):
    validate(doc)
    exact(proposal,{"revision","operation","shot","value","reason"},"director proposal")
    if proposal["revision"] != doc["revision"]:raise StudioError("Stale revision: review the current project first")
    op=proposal["operation"]
    if op not in OPERATIONS:raise StudioError("Unsupported operation")
    if not isinstance(proposal["reason"],str) or len(proposal["reason"])>500:raise StudioError("Invalid reason")
    if op=="reject":raise StudioError(proposal["reason"])
    new=copy.deepcopy(doc);s=next((s for s in new["shots"] if s["id"]==proposal["shot"]),None)
    v=proposal["value"];number(v,-1000,1000,"proposal value")
    if op in {"warmth","exposure"}:
        if proposal["shot"]!="ALL":raise StudioError("Look changes must disclose all shots")
        new["world"][op]=v
    else:
        if s is None:raise StudioError("Unknown shot")
        key={"camera_distance":"distance","camera_orbit":"azimuth","lens":"lens","focus":"focus_offset","cut_offset":"offset"}[op]
        s[key]=int(v) if op=="cut_offset" and v==int(v) else v
    new["revision"]+=1;validate(new)
    return new


def protected_world(doc):
    return digest({"assets":doc["assets"],"simulation_end":doc["simulation_end"],"fps":doc["fps"]})


def quick_proposal(doc, text, shot_id):
    """Small disclosed convenience grammar; general language uses the AI adapter."""
    s=next((s for s in doc["shots"] if s["id"]==shot_id),None)
    if not s:raise StudioError("Select a shot")
    text=text.lower().strip();op=None;v=0;target=shot_id
    if text in {"closer","closer camera","push in","近一点","靠近一点"}:op="camera_distance";v=s["distance"]*.85
    elif text in {"wider","pull back","远一点"}:op="camera_distance";v=s["distance"]*1.15
    elif text in {"warmer","暖一点"}:op="warmth";v=min(1,doc["world"]["warmth"]+.2);target="ALL"
    elif text in {"cooler","冷一点"}:op="warmth";v=max(-1,doc["world"]["warmth"]-.2);target="ALL"
    elif text in {"later cut","晚半秒"}:op="cut_offset";v=s["offset"]+12
    if op is None:raise StudioError("Use AI Director for free-form notes, or quick notes: closer / wider / warmer / cooler / later cut")
    return {"revision":doc["revision"],"operation":op,"shot":target,"value":v,"reason":text}
