from flask import Flask, request, jsonify, send_from_directory
import os, uuid, math

app = Flask(__name__)
OUT = "output"
os.makedirs(OUT, exist_ok=True)

def build_shape(t, sx, sy, sz):
    hx, hy, hz = sx/2, sy/2, sz/2

    if t == 0:  # cube
        v = [
            (-hx,-hy,-hz),(hx,-hy,-hz),(hx,hy,-hz),(-hx,hy,-hz),
            (-hx,-hy,hz),(hx,-hy,hz),(hx,hy,hz),(-hx,hy,hz)
        ]
        f = [
            (0,1,2),(0,2,3),(4,5,6),(4,6,7),
            (0,1,5),(0,5,4),(2,3,7),(2,7,6),
            (1,2,6),(1,6,5),(3,0,4),(3,4,7)
        ]
        return v,f

    if t == 1:  # cylinder
        v=[]; f=[]
        seg=16
        r=max(sx,sy)/2; h=sz/2
        for i in range(seg):
            a=2*math.pi*i/seg
            x=math.cos(a)*r
            y=math.sin(a)*r
            v.append((x,y,-h))
            v.append((x,y,h))
        for i in range(seg):
            a=i*2
            b=((i+1)%seg)*2
            f.append((a,b,a+1))
            f.append((b,b+1,a+1))
        return v,f

    return build_shape(0,sx,sy,sz)

def write_dae(path, V, F):
    with open(path,"w") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>')
        f.write('<COLLADA version="1.4.1">')
        f.write('<library_geometries><geometry id="m"><mesh>')

        f.write(f'<source id="p"><float_array count="{len(V)*3}">')
        for v in V:
            f.write(f'{v[0]} {v[1]} {v[2]} ')
        f.write('</float_array></source>')

        f.write('<vertices id="v"><input semantic="POSITION" source="#p"/></vertices>')

        f.write(f'<triangles count="{len(F)}">')
        f.write('<input semantic="VERTEX" source="#v" offset="0"/><p>')
        for a,b,c in F:
            f.write(f'{a} {b} {c} ')
        f.write('</p></triangles>')

        f.write('</mesh></geometry></library_geometries>')
        f.write('<scene><instance_visual_scene url="#s"/></scene>')
        f.write('</COLLADA>')

@app.route("/convert",methods=["POST"])
def convert():
    prims=request.json.get("prims",[])
    V=[]; F=[]; off=0

    for p in prims:
        t=p["type"]
        sx,sy,sz=p["size"]
        pos=p["pos"]

        v,f=build_shape(t,sx,sy,sz)
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
