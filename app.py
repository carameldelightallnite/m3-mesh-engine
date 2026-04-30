from flask import Flask, request, send_file
import math
import os

app = Flask(__name__)

OUTPUT = "shape.dae"
BASE_URL = "https://m3-mesh-engine.onrender.com"

# =========================
# REAL TORUS
# =========================
def buildtorus():
    major_segments = 24
    minor_segments = 16
    major_radius = 0.25
    minor_radius = 0.08

    verts = []
    faces = []

    for i in range(major_segments):
        theta = 2 * math.pi * i / major_segments
        for j in range(minor_segments):
            phi = 2 * math.pi * j / minor_segments
            x = (major_radius + minor_radius * math.cos(phi)) * math.cos(theta)
            y = (major_radius + minor_radius * math.cos(phi)) * math.sin(theta)
            z = minor_radius * math.sin(phi)
            verts.append((x, y, z))

    for i in range(major_segments):
        for j in range(minor_segments):
            a = i * minor_segments + j
            b = ((i + 1) % major_segments) * minor_segments + j
            c = ((i + 1) % major_segments) * minor_segments + (j + 1) % minor_segments
            d = i * minor_segments + (j + 1) % minor_segments
            faces.append((a, b, d))
            faces.append((b, c, d))

    write_dae(verts, faces)

# =========================
# LOCKED SPHERE
# =========================
def buildsphere():
    segments = 24
    rings = 16
    radius = 0.1

    verts = []
    faces = []
    verts.append((0.0, 0.0, radius))

    for i in range(1, rings):
        phi = math.pi * i / rings
        for j in range(segments):
            theta = 2 * math.pi * j / segments
            x = radius * math.sin(phi) * math.cos(theta)
            y = radius * math.sin(phi) * math.sin(theta)
            z = radius * math.cos(phi)
            verts.append((x, y, z))

    verts.append((0.0, 0.0, -radius))
    top = 0
    bottom = len(verts) - 1

    for j in range(segments):
        a = 1 + j
        b = 1 + (j + 1) % segments
        faces.append((top, a, b))

    for i in range(1, rings - 1):
        for j in range(segments):
            cur = 1 + (i - 1) * segments + j
            nxt = cur + segments
            right = 1 + (i - 1) * segments + (j + 1) % segments
            nxt_right = right + segments
            faces.append((cur, nxt, right))
            faces.append((right, nxt, nxt_right))

    start = 1 + (rings - 2) * segments
    for j in range(segments):
        a = start + j
        b = start + (j + 1) % segments
        faces.append((a, bottom, b))

    write_dae(verts, faces)

# =========================
# REAL CYLINDER
# =========================
def buildcylinder():
    segments = 24
    radius = 0.1
    height = 0.2

    verts = []
    faces = []
    top_z = height / 2
    bottom_z = -height / 2

    top_center = len(verts)
    verts.append((0.0, 0.0, top_z))
    bottom_center = len(verts)
    verts.append((0.0, 0.0, bottom_z))

    top_ring = []
    bottom_ring = []

    for i in range(segments):
        theta = 2 * math.pi * i / segments
        x = radius * math.cos(theta)
        y = radius * math.sin(theta)
        top_ring.append(len(verts))
        verts.append((x, y, top_z))
        bottom_ring.append(len(verts))
        verts.append((x, y, bottom_z))

    for i in range(segments):
        faces.append((top_center, top_ring[i], top_ring[(i + 1) % segments]))
        faces.append((bottom_center, bottom_ring[(i + 1) % segments], bottom_ring[i]))

    for i in range(segments):
        t1, t2 = top_ring[i], top_ring[(i + 1) % segments]
        b1, b2 = bottom_ring[i], bottom_ring[(i + 1) % segments]
        faces.append((t1, b1, t2))
        faces.append((t2, b1, b2))

    write_dae(verts, faces)

# =========================
# DAE WRITER
# =========================
def write_dae(verts, faces):
    vert_array = " ".join(f"{x} {y} {z}" for (x, y, z) in verts)
    index_array = " ".join(str(i) for f in faces for i in f)

    dae = f"""<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <asset><unit name="meter" meter="1"/><up_axis>Z_UP</up_axis></asset>
  <library_geometries>
    <geometry id="mesh">
      <mesh>
        <source id="pos">
          <float_array id="posArr" count="{len(verts)*3}">{vert_array}</float_array>
          <technique_common>
            <accessor source="#posArr" count="{len(verts)}" stride="3">
              <param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/>
            </accessor>
          </technique_common>
        </source>
        <vertices id="verts"><input semantic="POSITION" source="#pos"/></vertices>
        <triangles count="{len(faces)}">
          <input semantic="VERTEX" source="#verts" offset="0"/>
          <p>{index_array}</p>
        </triangles>
      </mesh>
    </geometry>
  </library_geometries>
  <library_visual_scenes><visual_scene id="Scene"><node id="node"><instance_geometry url="#mesh"/></node></visual_scene></library_visual_scenes>
  <scene><instance_visual_scene url="#Scene"/></scene>
</COLLADA>"""
    with open(OUTPUT, "w") as f:
        f.write(dae)

# =========================
# API ROUTES
# =========================
@app.route("/")
def home():
    return "PrimMesh Server Running"

@app.route("/generate", methods=["POST"])
def generate():
    data = request.data.decode("utf-8")
    print("RAW DATA:", data)  # DEBUG

    if "Torus" in data:
        buildtorus()
    elif "Cylinder" in data:
        buildcylinder()
    elif "Sphere" in data:
        buildsphere()
    else:
        buildsphere()

    return f"{BASE_URL}/download"

@app.route("/download")
def download():
    return send_file(OUTPUT, as_attachment=True)

if __name__ == "__main__":
    app.run()
