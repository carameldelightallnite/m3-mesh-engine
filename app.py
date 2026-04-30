from flask import Flask, request, send_file
import math

app = Flask(__name__)

OUTPUT = "shape.dae"
BASE_URL = "https://m3-mesh-engine.onrender.com"

# =========================
# NORMALS (KEEP)
# =========================
def compute_normals(verts, faces):
    normals = [[0.0,0.0,0.0] for _ in verts]
    for a,b,c in faces:
        v1,v2,v3 = verts[a],verts[b],verts[c]
        ux,uy,uz = v2[0]-v1[0], v2[1]-v1[1], v2[2]-v1[2]
        vx,vy,vz = v3[0]-v1[0], v3[1]-v1[1], v3[2]-v1[2]
        nx,ny,nz = uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx
        for i in (a,b,c):
            normals[i][0]+=nx; normals[i][1]+=ny; normals[i][2]+=nz

    result=[]
    for x,y,z in normals:
        l=math.sqrt(x*x+y*y+z*z) or 1
        result.append((x/l,y/l,z/l))
    return result

# =========================
# PROFILES (LIMITED)
# =========================
def get_profile_point(t, p_type="Square"):
    t %= 1.0
    s = 0.5

    if p_type == "Circle":
        return (s*math.cos(2*math.pi*t), s*math.sin(2*math.pi*t))

    if p_type == "Triangle":
        corners=[(-s,-s),(s,-s),(0,s),(-s,-s)]
        i=int(t*3); r=(t*3)-i
        return (
            corners[i][0]+(corners[i+1][0]-corners[i][0])*r,
            corners[i][1]+(corners[i+1][1]-corners[i][1])*r
        )

    # Square default
    corners=[(-s,-s),(s,-s),(s,s),(-s,s),(-s,-s)]
    i=int(t*4); r=(t*4)-i
    return (
        corners[i][0]+(corners[i+1][0]-corners[i][0])*r,
        corners[i][1]+(corners[i+1][1]-corners[i][1])*r
    )

# =========================
# SAFE BUILD ENGINE
# =========================
def build_safe(params):
    p_type = params.get("profile","Square")
    path_type = params.get("path","Linear")

    # LIMITS (ANTI-EXPLOIT)
    hollow = min(float(params.get("hollow",0.0)), 0.85)
    cut_s = max(0.0, float(params.get("cut_s",0.0)))
    cut_e = min(1.0, float(params.get("cut_e",1.0)))

    verts=[]
    f_out=[]

    steps = 24 if p_type=="Circle" else 16
    size = 1.0

    ring1=[]
    ring2=[]

    for i in range(steps):
        t = i/steps
        x,y = get_profile_point(t, p_type)

        ring1.append(len(verts))
        verts.append((x,y,-size))

        ring2.append(len(verts))
        verts.append((x,y,size))

    for i in range(steps):
        ni=(i+1)%steps
        a,b,c,d = ring1[i], ring1[ni], ring2[ni], ring2[i]
        f_out.extend([(a,b,c),(a,c,d)])

    write_safe(verts, f_out)

# =========================
# SAFE DAE (NO UV / NO MATERIAL SPLIT)
# =========================
def write_safe(verts, faces):
    normals = compute_normals(verts, faces)

    v = " ".join(f"{x} {y} {z}" for x,y,z in verts)
    n = " ".join(f"{x} {y} {z}" for x,y,z in normals)

    indices = " ".join(f"{i} {i}" for tri in faces for i in tri)

    dae=f"""<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
<asset><unit name="meter" meter="1"/><up_axis>Z_UP</up_axis></asset>

<library_geometries><geometry id="m"><mesh>

<source id="p">
<float_array id="pa" count="{len(verts)*3}">{v}</float_array>
<technique_common><accessor source="#pa" count="{len(verts)}" stride="3">
<param name="X"/><param name="Y"/><param name="Z"/>
</accessor></technique_common>
</source>

<source id="n">
<float_array id="na" count="{len(normals)*3}">{n}</float_array>
<technique_common><accessor source="#na" count="{len(normals)}" stride="3">
<param name="X"/><param name="Y"/><param name="Z"/>
</accessor></technique_common>
</source>

<vertices id="v">
<input semantic="POSITION" source="#p"/>
</vertices>

<triangles count="{len(faces)}">
<input semantic="VERTEX" source="#v" offset="0"/>
<input semantic="NORMAL" source="#n" offset="1"/>
<p>{indices}</p>
</triangles>

</mesh></geometry></library_geometries>

<library_visual_scenes><visual_scene id="S"><node>
<instance_geometry url="#m"/>
</node></visual_scene></library_visual_scenes>

<scene><instance_visual_scene url="#S"/></scene>
</COLLADA>"""

    with open(OUTPUT,"w") as f:
        f.write(dae)

# =========================
# ROUTES
# =========================
@app.route("/generate", methods=["POST"])
def generate():
    raw = request.data.decode("utf-8")
    params = dict(p.split("=") for p in raw.split("|") if "=" in p)
    build_safe(params)
    return f"{BASE_URL}/download"

@app.route("/download")
def download():
    return send_file(OUTPUT, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
