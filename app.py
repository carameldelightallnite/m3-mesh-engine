from flask import Flask, request, send_file, make_response
import math

app = Flask(__name__)

OUTPUT = "sphere.dae"

def buildsphere():
    segments = 16
    rings = 12
    radius = 0.1

    verts = []
    faces = []

    # generate vertices
    for i in range(rings + 1):
        phi = math.pi * i / rings
        for j in range(segments):
            theta = 2 * math.pi * j / segments
            x = radius * math.sin(phi) * math.cos(theta)
            y = radius * math.sin(phi) * math.sin(theta)
            z = radius * math.cos(phi)
            verts.append((x, y, z))

    # generate faces
    for i in range(rings):
        for j in range(segments):
            a = i * segments + j
            b = a + segments
            c = b + 1 if (j + 1) < segments else b + 1 - segments
            d = a + 1 if (j + 1) < segments else a + 1 - segments

            if i != 0:
                faces.append((a, b, d))
            if i != rings - 1:
                faces.append((d, b, c))

    # flatten arrays
    vert_array = " ".join(f"{v[0]} {v[1]} {v[2]}" for v in verts)
    index_array = " ".join(str(i) for f in faces for i in f)

    dae = f'''<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <asset>
    <unit name="meter" meter="1"/>
    <up_axis>Z_UP</up_axis>
  </asset>

  <library_geometries>
    <geometry id="sphere" name="sphere">
      <mesh>

        <source id="pos">
          <float_array id="posArr" count="{len(verts)*3}">
            {vert_array}
          </float_array>
          <technique_common>
            <accessor source="#posArr" count="{len(verts)}" stride="3">
              <param name="X" type="float"/>
              <param name="Y" type="float"/>
              <param name="Z" type="float"/>
            </accessor>
          </technique_common>
        </source>

        <vertices id="verts">
          <input semantic="POSITION" source="#pos"/>
        </vertices>

        <triangles count="{len(faces)}">
          <input semantic="VERTEX" source="#verts" offset="0"/>
          <p>{index_array}</p>
        </triangles>

      </mesh>
    </geometry>
  </library_geometries>

  <library_visual_scenes>
    <visual_scene id="Scene">
      <node id="sphereNode">
        <instance_geometry url="#sphere"/>
      </node>
    </visual_scene>
  </library_visual_scenes>

  <scene>
    <instance_visual_scene url="#Scene"/>
  </scene>
</COLLADA>'''

    with open(OUTPUT, "w") as f:
        f.write(dae)

@app.route("/")
def home():
    return "PrimMesh Server Running"

@app.route("/generate", methods=["POST"])
def generate():
    buildsphere()
    response = make_response("Download ready")
    response.headers["Content-Type"] = "text/plain"
    return response

@app.route("/download")
def download():
    return send_file(OUTPUT, as_attachment=True)

if __name__ == "__main__":
    app.run()
