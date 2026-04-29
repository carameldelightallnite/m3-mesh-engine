# FULL FINAL app.py — WORKING

from flask import Flask, request, jsonify, send_from_directory
import os, uuid, math

app = Flask(__name__)
OUT = "output"
os.makedirs(OUT, exist_ok=True)

def cube(sx,sy,sz):
    hx,hy,hz = sx/2,sy/2,sz/2
    v=[(-hx,-hy,-hz),(hx,-hy,-hz),(hx,hy,-hz),(-hx,hy,-hz),
       (-hx,-hy,hz),(hx,-hy,hz),(hx,hy,hz),(-hx,hy,hz)]
    f=[(0,1,2),(0,2,3),(4,5,6),(4,6,7),
       (0,1,5),(0,5,4),(2,3,7),(2,7,6),
       (1,2,6),(1,6,5),(3,0,4),(3,4,7)]
    return v,f

def write_dae(path,v,f):
    with open(path,"w") as o:
        o.write('<?xml version="1.0" encoding="utf-8"?>')
        o.write('<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">')

        o.write('<library_geometries><geometry id="mesh"><mesh>')

        o.write(f'<source id="p"><float_array id="pa" count="{len(v)*3}">')
        for x,y,z in v: o.write(f"{x} {y} {z} ")
        o.write('</float_array>')
        o.write('<technique_common>')
        o.write(f'<accessor source="#pa" count="{len(v)}" stride="3">')
        o.write('<param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/>')
        o.write('</accessor></technique_common></source>')

        o.write(f'<source id="n"><float_array id="na" count="{len(v)*3}">')
        for x,y,z in v: o.write(f"{x} {y} {z} ")
        o.write('</float_array>')
        o.write('<technique_common>')
        o.write(f'<accessor source="#na" count="{len(v)}" stride="3">')
        o.write('<param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/>')
        o.write('</accessor></technique_common></source>')

        o.write('<vertices id="v"><input semantic="POSITION" source="#p"/></vertices>')

        o.write(f'<triangles count="{len(f)}">')
        o.write('<input semantic="VERTEX" source="#v" offset="0"/>')
        o.write('<input semantic="NORMAL" source="#n" offset="1"/>')
        o.write('<p>')
        for a,b,c in f:
            o.write(f"{a} {a} {b} {b} {c} {c} ")
        o.write('</p></triangles>')

        o.write('</mesh></geometry></library_geometries>')

        # MATERIAL FIX
        o.write('<library_materials><material id="Material"><instance_effect url="#Material-effect"/></material></library_materials>')
        o.write('<library_effects><effect id="Material-effect"><profile_COMMON><technique sid="common"><lambert><diffuse><color>0.8 0.8 0.8 1</color></diffuse></lambert></technique></profile_COMMON></effect></library_effects>')

        o.write('<library_visual_scenes><visual_scene id="Scene"><node>')
        o.write('<instance_geometry url="#mesh">')
        o.write('<bind_material><technique_common>')
        o.write('<instance_material symbol="Material" target="#Material"/>')
        o.write('</technique_common></bind_material>')
        o.write('</instance_geometry>')
        o.write('</node></visual_scene></library_visual_scenes>')

        o.write('<scene><instance_visual_scene url="#Scene"/></scene>')
        o.write('</COLLADA>')

@app.route("/convert",methods=["POST"])
def convert():
    data=request.json.get("prims",[])
    V=[];F=[];off=0

    for p in data:
        sx,sy,sz=p["size"]
        pos=p["pos"]

        v,f=cube(sx,sy,sz)

        v=[(x+pos[0],y+pos[1],z+pos[2]) for x,y,z in v]

        V.extend(v)
        for a,b,c in f:
            F.append((a+off,b+off,c+off))
        off+=len(v)

    name=str(uuid.uuid4())+".dae"
    write_dae(os.path.join(OUT,name),V,F)

    return jsonify({"file":name})

@app.route("/output/<f>")
def out(f): return send_from_directory(OUT,f)

app.run(host="0.0.0.0",port=10000)
