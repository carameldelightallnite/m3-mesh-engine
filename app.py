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
        i = int(t * 3); r = (t * 3) - i
        return (corners[i][0] + (corners[i+1][0]-corners[i][0])*r, 
                corners[i][1] + (corners[i+1][1]-corners[i][1])*r)
    else:  # Square
        corners = [(-s, -s), (s, -s), (s, s), (-s, s), (-s, -s)]
        i = int(t * 4); r = (t * 4) - i
        return (corners[i][0] + (corners[i+1][0]-corners[i][0])*r, 
                corners[i][1] + (corners[i+1][1]-corners[i][1])*r)

# ==========================================
# UNIFIED ENGINE
# ==========================================
def build_prim(params):
    p_type = params.get("profile", "Square")
    path_type = params.get("path", "Linear")
    hollow = float(params.get("hollow", 0.0))
    cut_s, cut_e = float(params.get("cut_s", 0.0)), float(params.get("cut_e", 1.0))
    taper = [float(x) for x in params.get("taper", "1,1").split(",")]
    shear = [float(x) for x in params.get("shear", "0,0").split(",")]

    verts, uvs, normals = [], [], []
    f_out, f_in, f_cap = [], [], []

    p_steps = 24 if p_type == "Circle" else (3 if p_type == "Triangle" else 4)
    path_steps = 32 if path_type == "Circular" else 1
    major_r, size = 0.1, 0.1

    path_t = [cut_s]
    for i in range(1, p_steps+1):
        t = i / float(p_steps)
        if cut_s < t < cut_e: path_t.append(t)
    path_t.append(cut_e)
    n = len(path_t)

    for s_idx in range(path_steps + 1):
        v_c = s_idx / float(path_steps)
        phi = v_c * 2 * math.pi
        cp, sp = math.cos(phi), math.sin(phi)

        for t in path_t:
            px, py = get_profile_point(t, p_type)
            u_c = (t - cut_s) / (cut_e - cut_s)

            if path_type == "Linear":
                z = -size if s_idx == 0 else size
                tx, ty = (taper[0], taper[1]) if z > 0 else (1, 1)
                sx, sy = (shear[0], shear[1]) if z > 0 else (0, 0)
                verts.append((px*tx+sx, py*ty+sy, z))
                normals.append((px, py, 0))
            else:
                verts.append(((major_r+px)*cp, (major_r+px)*sp, py))
                normals.append((px*cp, px*sp, py))
            uvs.append((u_c, v_c))

        if hollow > 0:
            for t in path_t:
                px, py = get_profile_point(t, p_type)
                if path_type == "Linear":
                    z = -size if s_idx == 0 else size
                    tx, ty = (taper[0], taper[1]) if z > 0 else (1, 1)
                    sx, sy = (shear[0], shear[1]) if z > 0 else (0, 0)
                    verts.append((px*tx*hollow+sx, py*ty*hollow+sy, z))
                    normals.append((-px, -py, 0))
                else:
                    verts.append(((major_r+px*hollow)*cp, (major_r+px*hollow)*sp, py*hollow))
                    normals.append((-px*cp, -px*sp, -py))
                uvs.append(((t-cut_s)/(cut_e-cut_s), v_c))

    vps = n * (2 if hollow > 0 else 1)
    def quad(g, a, b, c, d): g.extend([(a, b, c), (a, c, d)])

    for s in range(path_steps):
        s1, s2 = s * vps, (s + 1) * vps
        for i in range(n - 1):
            quad(f_out, s1+i, s1+i+1, s2+i+1, s2+i)
            if hollow > 0: quad(f_in, s1+i+n+1, s1+i+n, s2+i+n, s2+i+n+1)

    if path_type == "Linear" and hollow == 0:
        for i in range(1, n - 1): f_cap.append((0, i+1, i))
        top = path_steps * vps
        for i in range(1, n - 1): f_cap.append((top, top+i, top+i+1))

    if (cut_e - cut_s) < 1.0:
        for i in range(path_steps):
            a, b = i * vps, (i+1) * vps
            quad(f_cap, a, b, b+1, a+1)
            a_e, b_e = a + (n-1), b + (n-1)
            quad(f_cap, a_e, a_e+1, b_e+1, b_e) if hollow > 0 else quad(f_cap, a_e, a_e+1, b_e+1, b_e) # Logic simplified for caps

    write_dae_fixed(verts, f_out, f_in, f_cap, uvs, normals)

# ==========================================
# FIXED DAE WRITER
# ==========================================
def write_dae_fixed(verts, out_f, in_f, cap_f, uvs, normals):
    def pack(faces):
        return "".join(f"{i} {i} {i} " for f in faces for i in f)

    v_str = " ".join(f"{x} {y} {z}" for x, y, z in verts)
    n_str = " ".join(f"{x} {y} {z}" for x, y, z in normals)
    uv_str = " ".join(f"{u} {v}" for u, v in uvs)

    dae = f"""<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
<library_effects>
  <effect id="m_o_f"><profile_COMMON><technique><phong/></technique></profile_COMMON></effect>
  <effect id="m_i_f"><profile_COMMON><technique><phong/></technique></profile_COMMON></effect>
  <effect id="m_c_f"><profile_COMMON><technique><phong/></technique></profile_COMMON></effect>
</library_effects>
<library_materials>
  <material id="m_o"><instance_effect url="#m_o_f"/></material>
  <material id="m_i"><instance_effect url="#m_i_f"/></material>
  <material id="m_c"><instance_effect url="#m_c_f"/></material>
</library_materials>
<library_geometries>
  <geometry id="mesh"><mesh>
    <source id="pos"><float_array id="pa" count="{len(verts)*3}">{v_str}</float_array>
      <technique_common><accessor source="#pa" count="{len(verts)}" stride="3"><param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/></accessor></technique_common></source>
    <source id="norm"><float_array id="na" count="{len(normals)*3}">{n_str}</float_array>
      <technique_common><accessor source="#na" count="{len(normals)}" stride="3"><param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/></accessor></technique_common></source>
    <source id="uv"><float_array id="ua" count="{len(uvs)*2}">{uv_str}</float_array>
      <technique_common><accessor source="#ua" count="{len(uvs)}" stride="2"><param name="S" type="float"/><param name="T" type="float"/></accessor></technique_common></source>
    <vertices id="v"><input semantic="POSITION" source="#pos"/></vertices>
    <triangles material="mat_out" count="{len(out_f)}"><input semantic="VERTEX" source="#v" offset="0"/><input semantic="NORMAL" source="#norm" offset="1"/><input semantic="TEXCOORD" source="#uv" offset="2"/><p>{pack(out_f)}</p></triangles>
    <triangles material="mat_in" count="{len(in_f)}"><input semantic="VERTEX" source="#v" offset="0"/><input semantic="NORMAL" source="#norm" offset="1"/><input semantic="TEXCOORD" source="#uv" offset="2"/><p>{pack(in_f)}</p></triangles>
    <triangles material="mat_cap" count="{len(cap_f)}"><input semantic="VERTEX" source="#v" offset="0"/><input semantic="NORMAL" source="#norm" offset="1"/><input semantic="TEXCOORD" source="#uv" offset="2"/><p>{pack(cap_f)}</p></triangles>
  </mesh></geometry>
</library_geometries>
<library_visual_scenes><visual_scene id="S"><node><instance_geometry url="#mesh"><bind_material><technique_common>
  <instance_material symbol="mat_out" target="#m_o"/><instance_material symbol="mat_in" target="#m_i"/><instance_material symbol="mat_cap" target="#m_c"/>
</technique_common></bind_material></instance_geometry></node></visual_scene></library_visual_scenes>
<scene><instance_visual_scene url="#S"/></scene>
</COLLADA>"""
    with open(OUTPUT, "w") as f: f.write(dae)

@app.route("/generate", methods=["POST"])
def generate():
    raw = request.data.decode("utf-8")
    params = dict(p.split("=") for p in raw.split("|") if "=" in p)
    build_prim(params)
    return f"{BASE_URL}/download"

@app.route("/download")
def download(): return send_file(OUTPUT, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
