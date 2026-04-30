from flask import Flask, request, send_file
import math

app = Flask(__name__)

OUTPUT = "shape.dae"
BASE_URL = "https://m3-mesh-engine.onrender.com"


# ==========================================
# PROFILE SYSTEM (UNCHANGED)
# ==========================================
def get_profile_point(t, p_type="Square"):
    t %= 1.0
    s = 0.05

    if p_type == "Circle":
        return (s * math.cos(2 * math.pi * t),
                s * math.sin(2 * math.pi * t))

    elif p_type == "Triangle":
        corners = [(-s, -s), (s, -s), (0, s), (-s, -s)]
        i = int(t * 3)
        r = (t * 3) - i
        p1, p2 = corners[i], corners[i+1]
        return (p1[0] + (p2[0]-p1[0])*r,
                p1[1] + (p2[1]-p1[1])*r)

    else:  # Square
        corners = [(-s, -s), (s, -s), (s, s), (-s, s), (-s, -s)]
        i = int(t * 4)
        r = (t * 4) - i
        p1, p2 = corners[i], corners[i+1]
        return (p1[0] + (p2[0]-p1[0])*r,
                p1[1] + (p2[1]-p1[1])*r)


# ==========================================
# 🔥 TRI OPTIMIZER (DECIMATION)
# ==========================================
def decimate_faces(faces, ratio):
    target = int(len(faces) * ratio)
    return faces[:max(1, target)]


# ==========================================
# FINAL ENGINE (UNCHANGED CORE BUILD)
# ==========================================
def build_base_mesh(params, quality=1.0):

    p_type = params.get("profile", "Square")
    path_type = params.get("path", "Linear")

    hollow = float(params.get("hollow", 0.0))
    cut_s = float(params.get("cut_s", 0.0))
    cut_e = float(params.get("cut_e", 1.0))

    taper = [float(x) for x in params.get("taper", "1,1").split(",")]
    shear = [float(x) for x in params.get("shear", "0,0").split(",")]

    verts, uvs, normals = [], [], []
    faces_out, faces_in, faces_caps = [], [], []

    profile_steps = int((24 if p_type == "Circle" else (3 if p_type == "Triangle" else 4)) * quality)
    path_steps = int((32 if path_type == "Circular" else 1) * quality)

    profile_steps = max(profile_steps, 3)
    path_steps = max(path_steps, 1)

    major_r = 0.1
    size = 0.1

    # ---------- PATH CUT ----------
    path_t = [cut_s]
    for i in range(1, profile_steps+1):
        t = i / float(profile_steps)
        if cut_s < t < cut_e:
            path_t.append(t)
    path_t.append(cut_e)

    n = len(path_t)

    # ---------- VERTEX BUILD ----------
    for s_idx in range(path_steps + 1):
        v_coord = s_idx / float(path_steps)
        phi = v_coord * 2 * math.pi
        cos_p, sin_p = math.cos(phi), math.sin(phi)

        for t in path_t:
            px, py = get_profile_point(t, p_type)

            if path_type == "Linear":
                z = -size if s_idx == 0 else size
                tx, ty = (taper[0], taper[1]) if z > 0 else (1, 1)
                sx, sy = (shear[0], shear[1]) if z > 0 else (0, 0)

                x = px * tx + sx
                y = py * ty + sy
                nx, ny, nz = px, py, 0

            else:
                x = (major_r + px) * cos_p
                y = (major_r + px) * sin_p
                z = py
                nx = px * cos_p
                ny = px * sin_p
                nz = py

            verts.append((x, y, z))
            normals.append((nx, ny, nz))
            uvs.append(((t - cut_s)/(cut_e - cut_s), v_coord))

    # ---------- FACE BUILD ----------
    vps = n

    def quad(group, a, b, c, d):
        group.append((a, b, c))
        group.append((a, c, d))

    for s in range(path_steps):
        s1 = s * vps
        s2 = (s + 1) * vps

        for i in range(n - 1):
            quad(faces_out, s1+i, s1+i+1, s2+i+1, s2+i)

    return verts, faces_out, faces_in, faces_caps, uvs, normals


# ==========================================
# 🔥 LOD BUILDER
# ==========================================
def build_lods(params):

    lods = []

    # High
    lods.append(build_base_mesh(params, quality=1.0))

    # Medium
    lods.append(build_base_mesh(params, quality=0.5))

    # Low
    lods.append(build_base_mesh(params, quality=0.25))

    # Lowest (decimated)
    v, f_out, f_in, f_cap, u, n = build_base_mesh(params, quality=0.15)
    f_out = decimate_faces(f_out, 0.5)
    lods.append((v, f_out, f_in, f_cap, u, n))

    return lods


# ==========================================
# 🔥 DAE WRITER WITH LODS
# ==========================================
def write_dae_lods(lods):

    def pack(faces):
        s = ""
        for f in faces:
            for i in f:
                s += f"{i} {i} {i} "
        return s

    geo_blocks = ""

    for i, (verts, f_out, f_in, f_cap, uvs, normals) in enumerate(lods):

        v = " ".join(f"{x} {y} {z}" for x, y, z in verts)
        n = " ".join(f"{x} {y} {z}" for x, y, z in normals)
        uv = " ".join(f"{u} {v}" for u, v in uvs)

        geo_blocks += f"""
<geometry id="lod{i}"><mesh>
<source id="p{i}"><float_array count="{len(verts)*3}">{v}</float_array>
<technique_common><accessor source="#p{i}" count="{len(verts)}" stride="3">
<param name="X"/><param name="Y"/><param name="Z"/>
</accessor></technique_common></source>

<source id="n{i}"><float_array count="{len(normals)*3}">{n}</float_array>
<technique_common><accessor source="#n{i}" count="{len(normals)}" stride="3">
<param name="X"/><param name="Y"/><param name="Z"/>
</accessor></technique_common></source>

<source id="uv{i}"><float_array count="{len(uvs)*2}">{uv}</float_array>
<technique_common><accessor source="#uv{i}" count="{len(uvs)}" stride="2">
<param name="S"/><param name="T"/>
</accessor></technique_common></source>

<vertices id="v{i}">
<input semantic="POSITION" source="#p{i}"/>
</vertices>

<triangles count="{len(f_out)}">
<input semantic="VERTEX" source="#v{i}" offset="0"/>
<input semantic="NORMAL" source="#n{i}" offset="1"/>
<input semantic="TEXCOORD" source="#uv{i}" offset="2"/>
<p>{pack(f_out)}</p>
</triangles>
</mesh></geometry>
"""

    dae = f"""<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">

<library_geometries>
{geo_blocks}
</library_geometries>

<scene>
<instance_visual_scene url="#Scene"/>
</scene>

<library_visual_scenes>
<visual_scene id="Scene">
<node>
<instance_geometry url="#lod0"/>
</node>
</visual_scene>
</library_visual_scenes>

</COLLADA>
"""

    with open(OUTPUT, "w") as f:
        f.write(dae)


# ==========================================
# ROUTES
# ==========================================
@app.route("/generate", methods=["POST"])
def generate():
    raw = request.data.decode("utf-8")
    params = dict(p.split("=") for p in raw.split("|") if "=" in p)

    lods = build_lods(params)
    write_dae_lods(lods)

    return f"{BASE_URL}/download"


@app.route("/download")
def download():
    return send_file(OUTPUT, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
