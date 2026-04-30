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
# FINAL ENGINE (UNCHANGED CORE)
# ==========================================
def build_prim(params):
    p_type = params.get("profile", "Square")
    path_type = params.get("path", "Linear")

    hollow = float(params.get("hollow", 0.0))
    cut_s = float(params.get("cut_s", 0.0))
    cut_e = float(params.get("cut_e", 1.0))

    taper = [float(x) for x in params.get("taper", "1,1").split(",")]
    shear = [float(x) for x in params.get("shear", "0,0").split(",")]

    verts, uvs, normals = [], [], []

    faces_out, faces_in, faces_caps = [], [], []

    profile_steps = 24 if p_type == "Circle" else (3 if p_type == "Triangle" else 4)
    path_steps = 32 if path_type == "Circular" else 1

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

            # 🔥 AUTO UV SCALE (proportional)
            u = (t - cut_s) / max((cut_e - cut_s), 0.0001)
            v = v_coord
            uvs.append((u, v))

        # ---------- HOLLOW ----------
        if hollow > 0:
            for t in path_t:
                px, py = get_profile_point(t, p_type)

                if path_type == "Linear":
                    z = -size if s_idx == 0 else size
                    tx, ty = (taper[0], taper[1]) if z > 0 else (1, 1)
                    sx, sy = (shear[0], shear[1]) if z > 0 else (0, 0)

                    x = px * tx * hollow + sx
                    y = py * ty * hollow + sy

                    nx, ny, nz = -px, -py, 0

                else:
                    x = (major_r + px * hollow) * cos_p
                    y = (major_r + px * hollow) * sin_p
                    z = py * hollow

                    nx = -px * cos_p
                    ny = -px * sin_p
                    nz = -py

                verts.append((x, y, z))
                normals.append((nx, ny, nz))
                uvs.append((u, v))

    # ---------- FACE BUILD ----------
    vps = n * (2 if hollow > 0 else 1)

    def quad(group, a, b, c, d):
        group.append((a, b, c))
        group.append((a, c, d))

    for s in range(path_steps):
        s1 = s * vps
        s2 = (s + 1) * vps

        for i in range(n - 1):
            quad(faces_out, s1+i, s1+i+1, s2+i+1, s2+i)

            if hollow > 0:
                quad(faces_in,
                     s1+i+n+1, s1+i+n,
                     s2+i+n, s2+i+n+1)

    # ---------- CAPS ----------
    if path_type == "Linear" and hollow == 0:
        for i in range(1, n - 1):
            faces_caps.append((0, i+1, i))

        top = path_steps * vps
        for i in range(1, n - 1):
            faces_caps.append((top, top+i, top+i+1))

    # ---------- CUT SEAL ----------
    if (cut_e - cut_s) < 1.0:
        for i in range(path_steps):
            a = i * vps
            b = a + vps
            quad(faces_caps, a, b, b+1, a+1)

        for i in range(path_steps):
            a = i * vps + (n - 1)
            b = a + vps
            quad(faces_caps, a, a+1, b+1, b)

    write_dae_split(verts, faces_out, faces_in, faces_caps, uvs, normals)


# ==========================================
# 🔥 SPLIT GEOMETRY FOR SL FACE INDEX CONTROL
# ==========================================
def write_dae_split(verts, out_f, in_f, cap_f, uvs, normals):

    def pack(faces):
        s = ""
        for f in faces:
            for i in f:
                s += f"{i} {i} {i} "
        return s

    v = " ".join(f"{x} {y} {z}" for x, y, z in verts)
    n = " ".join(f"{x} {y} {z}" for x, y, z in normals)
    uv = " ".join(f"{u} {v}" for u, v in uvs)

    def geo_block(id_name, faces):
        return f"""
<geometry id="{id_name}"><mesh>
<source id="{id_name}_pos"><float_array count="{len(verts)*3}">{v}</float_array>
<technique_common><accessor source="#{id_name}_pos" count="{len(verts)}" stride="3">
<param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/>
</accessor></technique_common></source>

<source id="{id_name}_norm"><float_array count="{len(normals)*3}">{n}</float_array>
<technique_common><accessor source="#{id_name}_norm" count="{len(normals)}" stride="3">
<param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/>
</accessor></technique_common></source>

<source id="{id_name}_uv"><float_array count="{len(uvs)*2}">{uv}</float_array>
<technique_common><accessor source="#{id_name}_uv" count="{len(uvs)}" stride="2">
<param name="S" type="float"/><param name="T" type="float"/>
</accessor></technique_common></source>

<vertices id="{id_name}_v"><input semantic="POSITION" source="#{id_name}_pos"/></vertices>

<triangles count="{len(faces)}">
<input semantic="VERTEX" source="#{id_name}_v" offset="0"/>
<input semantic="NORMAL" source="#{id_name}_norm" offset="1"/>
<input semantic="TEXCOORD" source="#{id_name}_uv" offset="2"/>
<p>{pack(faces)}</p>
</triangles>
</mesh></geometry>
"""

    dae = f"""<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">

<library_geometries>
{geo_block("outside", out_f)}
{geo_block("inside", in_f)}
{geo_block("caps", cap_f)}
</library_geometries>

<library_visual_scenes>
<visual_scene id="Scene">
<node>
<instance_geometry url="#outside"/>
<instance_geometry url="#inside"/>
<instance_geometry url="#caps"/>
</node>
</visual_scene>
</library_visual_scenes>

<scene><instance_visual_scene url="#Scene"/></scene>

</COLLADA>"""

    with open(OUTPUT, "w") as f:
        f.write(dae)


# ==========================================
# ROUTES
# ==========================================
@app.route("/generate", methods=["POST"])
def generate():
    raw = request.data.decode("utf-8")
    params = dict(p.split("=") for p in raw.split("|") if "=" in p)

    build_prim(params)
    return f"{BASE_URL}/download"


@app.route("/download")
def download():
    return send_file(OUTPUT, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
