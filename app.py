from flask import Flask, request, send_from_directory
import os, uuid, math

app = Flask(__name__)
OUT = "output"
os.makedirs(OUT, exist_ok=True)

# -------------------------------
# BASIC SHAPES
# -------------------------------

def cube(sx, sy, sz):
    hx, hy, hz = sx/2, sy/2, sz/2
    v = [
        (-hx,-hy,-hz),(hx,-hy,-hz),(hx,hy,-hz),(-hx,hy,-hz),
        (-hx,-hy,hz),(hx,-hy,hz),(hx,hy,hz),(-hx,hy,hz)
    ]
    f = [
        (0,1,2),(0,2,3),
        (4,5,6),(4,6,7),
        (0,1,5),(0,5,4),
        (2,3,7),(2,7,6),
        (1,2,6),(1,6,5),
        (3,0,4),(3,4,7)
    ]
    return v,f

def cylinder(sx, sy, sz, seg=24):
    r = sx/2
    h = sz/2
    v=[]; f=[]
    for i in range(seg):
        a=2*math.pi*i/seg
        x=math.cos(a)*r
        y=math.sin(a)*r
        v.append((x,y,-h))
        v.append((x,y,h))
    for i in range(0,seg*2,2):
        n=(i+2)%(seg*2)
        f.append((i,n,n+1))
        f.append((i,n+1,i+1))
    return v,f

def sphere(sx, sy, sz, rings=10, seg=20):
    r=sx/2
    v=[]; f=[]
    for i in range(rings+1):
        phi=math.pi*i/rings
        for j in range(seg):
            theta=2*math.pi*j/seg
            x=r*math.sin(phi)*math.cos(theta)
            y=r*math.sin(phi)*math.sin(theta)
            z=r*math.cos(phi)
            v.append((x,y,z))
    for i in range(rings):
        for j in range(seg):
            nj=(j+1)%seg
            a=i*seg+j
            b=i*seg+nj
            c=(i+1)*seg+j
            d=(i+1)*seg+nj
            f.append((a,b,d))
            f.append((a,d,c))
    return v,f

# -------------------------------
# SHAPE DETECTION (SIMPLE)
# -------------------------------

def detect_shape(sx, sy, sz):
    if sz < sx*0.25:
        return "cube"
    if abs(sx - sy) < 0.05:
        return "cylinder"
    return "sphere"

# -------------------------------
# WRITE DAE FILE
# -------------------------------

def write_dae(path, verts, faces):
    with open(path,"w") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>')
        f.write('<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">')
        f.write('<library_geometries><geometry id="mesh"><mesh>')
        
        f.write(f'<source id="pos"><float_array count="{len(verts)*3}">')
        for v in verts:
            f.write(f'{v[0]} {v[1]} {v[2]} ')
        f.write('</float_array></source>')
        
        f.write('<vertices id="verts"><input semantic="POSITION" source="#pos"/></vertices>')
        
        f.write(f'<triangles count="{len(faces)}">')
        f.write('<input semantic="VERTEX" source="#verts" offset="0"/><p>')
        for tri in faces:
            f.write(f'{tri[0]} {tri[1]} {tri[2]} ')
        f.write('</p></triangles>')
        
        f.write('</mesh></geometry></library_geometries></COLLADA>')

# -------------------------------
# API ROUTES
# -------------------------------

@app.route("/")
def home():
    return "M3 Mesh Engine Running"

@app.route("/convert", methods=["POST"])
def convert():
    data = request.json or {}

    try:
        sx,sy,sz = data["prims"][0]["size"]
    except:
        sx,sy,sz = 1,1,0.2

    shape = detect_shape(sx,sy,sz)

    if shape == "cube":
        v,f = cube(sx,sy,sz)
    elif shape == "cylinder":
        v,f = cylinder(sx,sy,sz)
    else:
        v,f = sphere(sx,sy,sz)

    name = str(uuid.uuid4()) + ".dae"
    path = os.path.join(OUT,name)

    write_dae(path, v, f)

    return name

@app.route("/output/<filename>")
def output_file(filename):
    return send_from_directory(OUT, filename)

# -------------------------------
# RENDER FIX (CRITICAL)
# -------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)