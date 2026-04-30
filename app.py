from flask import Flask, request, send_file
import math

app = Flask(__name__)

OUTPUT = "shape.dae"
BASE_URL = "https://m3-mesh-engine.onrender.com"

# ==========================================
# PROFILE SYSTEM
# ==========================================
def get_profile_point(t, p_type="Square"):
    t %= 1.0
    s = 0.05
    if p_type == "Circle":
        return (s * math.cos(2 * math.pi * t), s * math.sin(2 * math.pi * t))
    elif p_type == "Triangle":
        corners = [(-s, -s), (s, -s), (0, s), (-s, -s)]
        i = int(t * 3)
        r = (t * 3) - i
        p1, p2 = corners[i], corners[i+1]
        return (p1[0] + (p2[0]-p1[0])*r, p1[1] + (p2[1]-p1[1])*r)
    else:  # Square
        corners = [(-s, -s), (s, -s), (s, s), (-s, s), (-s, -s)]
        i = int(t * 4)
        r = (t * 4) - i
        p1, p2 = corners[i], corners[i+1]
        return (p1[0] + (p2[0]-p1[0])*r, p1[1] + (p2[1]-p1[1])*r)

# ==========================================
# CORE ENGINE (ALL FEATURES PRESERVED)
# ==========================================
def build_prim(params):
    p_type = params.get("profile", "Square")
    path_type = params.get("path", "Linear")
    hollow = float(params.get("hollow", 0.0))
    cut_s, cut_e = float(params.get("cut_s", 0.0)), float(params.get("cut_e", 1.0))
    taper = [float(x) for x in params.get("taper", "1,1").split(",")]
    shear = [float(x) for x in params.get("shear", "0,0").split(",")]

    verts = []
    f_out, f_in, f_cap = [] , [], []

    p_steps = 24 if p_type == "Circle" else (3 if p_type == "Triangle" else 4)
    path_steps = 32 if path_type == "Circular" else 1
    major_r, size = 0.1, 0.1

    path_t = [cut_s]
    for i in range(1, p_steps + 1):
        t = i / float(p_steps)
        if cut_s < t < cut_e: path_t.append(t)
    path_t.append(cut_e)
    n = len(path_t)

    # ---------- VERTEX GENERATION ----------
    for s_idx in range(path_steps + 1):
        v_coord = s_idx / float(path_steps)
        phi = v_coord * 2 * math.pi
        cp, sp = math.cos(phi), math.sin(phi)

        for t in path_t:
            px, py = get_profile_point(t, p_type)
            if path_type == "Linear":
                z = -size if s_idx == 0 else size
                tx, ty = (taper[0], taper[1]) if z > 0 else (1, 1)
                sx, sy = (shear[0], shear[1]) if z > 0 else (0, 0)
                verts.append((px*tx + sx, py*ty + sy, z))
            else:
                verts.append(((major_r + px) * cp, (major_r + px) * sp, py))

        if hollow > 0:
            for t in path_t:
                px, py = get_profile_point(t, p_type)
                if path_type == "Linear":
                    z = -size if s_idx == 0 else size
                    tx, ty = (taper[0], taper[1]) if z > 0 else (1, 1)
                    sx, sy = (shear[0], shear[1]) if z > 0 else (0, 0)
                    verts.append((px*tx*hollow + sx, py*ty*hollow + sy, z))
                else:
                    verts.append(((major_r + px*hollow) * cp, (major_r + px*hollow) * sp, py*hollow))

    # ---------- FACE GENERATION ----------
    vps = n * (2 if hollow > 0 else 1)
    def quad(group, a, b, c, d):
        group.extend([(a, b, c), (a, c, d)])

    for s in range(path_steps):
        s1, s2 = s * vps, (s + 1) * vps
        for i in range(n - 1):
            quad(f_out, s1+i, s1+i+1, s2+i+1, s2+i)
            if hollow > 0:
                quad(f_in, s1+i+n+1, s1+i+n, s2+i+n, s2+i+n+1)

    # Caps & Seals
    if path_type == "Linear" and hollow == 0:
        for i in range(1, n - 1): f_cap.append((0, i+1, i))
        top = path_steps * vps
        for i in range(1, n - 1): f_cap.append((top, top+i, top+i+1))

    if (cut_e - cut_s) < 1.0:
        for i in range(path_steps):
            a, b = i * vps, (i + 1) * vps
            quad(f_cap, a, b, b+1, a+1)
            if hollow > 0:
                a_e, b_e = a + (n-1), b + (n-1)
                quad(f_cap, a_e, a_e+1, b_e+1, b_e)

    write_dae_final(verts, f_out, f_in, f_cap)

# ==========================================
# FINAL MINIMALIST DAE WRITER
# ==========================================
def write_dae_final(verts, out_f, in_f, cap_f):
    def pack(faces):
        return " ".join(f"{a} {b} {c}" for (a, b, c) in faces)

    v_data = " ".join(f"{x} {y} {z}" for x, y, z in verts)

    dae = f"""<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <asset>
    <unit name="meter" meter="1"/>
    <up_axis>Z_UP</up_axis>
  </asset>
  <library_geometries>
    <geometry id="mesh" name="mesh">
      <mesh>
        <source id="pos">
          <float_array id="posArr" count="{len(verts)*3}">{v_data}</float_array>
          <technique_common>
            <accessor source="#posArr" count="{len(verts)}" stride="3">
              <param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/>
            </accessor>
          </technique_common>
        </source>
        <vertices id="verts"><input semantic="POSITION" source="#pos"/></vertices>
        <triangles material="mat0" count="{len(out_f)}">
          <input semantic="VERTEX" source="#verts" offset="0"/>
          <p>{pack(out_f)}</p>
        </triangles>
        <triangles material="mat1" count="{len(in_f)}">
          <input semantic="VERTEX" source="#verts" offset="0"/>
          <p>{pack(in_f)}</p>
        </triangles>
        <triangles material="mat2" count="{len(cap_f)}">
          <input semantic="VERTEX" source="#verts" offset="0"/>
          <p>{pack(cap_f)}</p>
        </triangles>
      </mesh>
    </geometry>
  </library_geometries>
  <library_visual_scenes>
    <visual_scene id="Scene">
      <node id="node"><instance_geometry url="#mesh"/></node>
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
