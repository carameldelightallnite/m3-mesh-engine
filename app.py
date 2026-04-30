from flask import Flask, request, send_file
import os

app = Flask(__name__)

OUTPUT = "finalobject.dae"

def builddae():
    content = """<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <asset>
    <unit name="meter" meter="1"/>
    <up_axis>Z_UP</up_axis>
  </asset>

  <library_geometries>
    <geometry id="cube" name="cube">
      <mesh>
        <source id="cubePos">
          <float_array id="cubeArr" count="24">
          -0.1 -0.1 -0.1  0.1 -0.1 -0.1  0.1 0.1 -0.1  -0.1 0.1 -0.1
          -0.1 -0.1 0.1   0.1 -0.1 0.1   0.1 0.1 0.1   -0.1 0.1 0.1
          </float_array>
          <technique_common>
            <accessor source="#cubeArr" count="8" stride="3">
              <param name="X" type="float"/>
              <param name="Y" type="float"/>
              <param name="Z" type="float"/>
            </accessor>
          </technique_common>
        </source>

        <vertices id="cubeVerts">
          <input semantic="POSITION" source="#cubePos"/>
        </vertices>

        <triangles count="12">
          <input semantic="VERTEX" source="#cubeVerts" offset="0"/>
          <p>
          0 1 2 0 2 3
          4 5 6 4 6 7
          0 4 7 0 7 3
          1 5 6 1 6 2
          3 2 6 3 6 7
          0 1 5 0 5 4
          </p>
        </triangles>
      </mesh>
    </geometry>
  </library_geometries>

  <library_visual_scenes>
    <visual_scene id="Scene">
      <node id="cubeNode">
        <instance_geometry url="#cube"/>
      </node>
    </visual_scene>
  </library_visual_scenes>

  <scene>
    <instance_visual_scene url="#Scene"/>
  </scene>
</COLLADA>
"""
    with open(OUTPUT, "w") as f:
        f.write(content)

@app.route("/")
def home():
    return "PrimMesh Server Running"

@app.route("/generate", methods=["POST"])
def generate():
    builddae()
    return send_file(OUTPUT, as_attachment=True)

if __name__ == "__main__":
    app.run()
