from flask import Flask, request, send_file, make_response
import math

app = Flask(__name__)

OUTPUT = "sphere.dae"

def buildsphere():
    # Proven safe defaults for SL
    segments = 24   # longitude
    rings = 16      # latitude (excluding poles)
    radius = 0.1

    verts = []
    faces = []

    # --- vertices ---
    # top pole
    verts.append((0.0, 0.0, radius))

    # rings (exclude poles)
    for i in range(1, rings):
        phi = math.pi * i / rings  # 0..pi
        for j in range(segments):
            theta = 2 * math.pi * j / segments
            x = radius * math.sin(phi) * math.cos(theta)
            y = radius * math.sin(phi) * math.sin(theta)
            z = radius * math.cos(phi)
            verts.append((x, y, z))

    # bottom pole
    verts.append((0.0, 0.0, -radius))

    top_index = 0
    bottom_index = len(verts) - 1

    # --- faces (top cap) ---
    for j in range(segments):
        a = 1 + j
        b = 1 + (j + 1) % segments
        faces.append((top_index, a, b))

    # --- faces (middle) ---
    for i in range(1, rings - 1):
        for j in range(segments):
            current = 1 + (i - 1) * segments + j
            next = current + segments

            right = 1 + (i - 1) * segments + (j + 1) % segments
            next_right = right + segments

            faces.append((current, next, right))
            faces.append((right, next, next_right))

    # --- faces (bottom cap) ---
    start_last_ring = 1 + (rings - 2) * segments
    for j in range(segments):
        a = start_last_ring + j
        b = start_last_ring + (j + 1) % segments
        faces.append((a, bottom_index, b))

    # --- flatten ---
    vert_array = " ".join(f"{x} {y} {z}" for (x, y, z) in verts)
    index_array = " ".join(str(i) for tri in faces for i in tri)

    dae = f"""<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <asset>
    <unit name="meter" meter="1"/>
    <up_axis>Z_UP</up_axis>
  </asset>

  <library_geometries>
    <geometry id="sphere" name="sphere">
      <mesh>

        <source id="sphere-pos">
          <float_array id="sphere-arr" count="{len(verts)*3}">
            {vert_array}
          </float_array>
          <technique_common>
            <accessor source="#sphere-arr" count="{len(verts)}" stride="3">
              <param name="X" type="float"/>
              <param name="Y" type="float"/>
              <param name="Z" type="float"/>
            </accessor>
          </technique_common>
        </source>

        <vertices id="sphere-verts">
          <input semantic="POSITION" source="#sphere-pos"/>
        </vertices>

        <triangles count="{len(faces)}">
          <input semantic="VERTEX" source="#sphere-verts" offset="0"/>
          <p>{index_array}</p>
        </triangles>

      </mesh>
    </geometry>
  </library_geometries>

  <library_visual_scenes>
    <visual_scene id="Scene" name="Scene">
      <node id="sphere-node" name="sphere">
        <instance_geometry url="#sphere"/>
      </node>
    </visual_scene>
  </library_visual_scenes>

  <scene>
    <instance_visual_scene url="#Scene"/>
  </scene>
</COLLADA>
"""

    with open(OUTPUT, "w") as f:
        f.write(dae)

@app.route("/")
def home():
    return "PrimMesh Server Running"

@app.route("/generate", methods=["POST"])
def generate():
    buildsphere()
    resp = make_response("Download ready")
    resp.headers["Content-Type"] = "text/plain"
    return resp

@app.route("/download")
def download():
    return send_file(OUTPUT, as_attachment=True)

if __name__ == "__main__":
    app.run()
