# M3 PRIM → MESH SERVER (FINAL)

from flask import Flask, request
import uuid
import os
import math

app = Flask(__name__)

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def build_cube(size):
    x,y,z = size
    verts = [
        (-x/2,-y/2,-z/2),(x/2,-y/2,-z/2),(x/2,y/2,-z/2),(-x/2,y/2,-z/2),
        (-x/2,-y/2,z/2),(x/2,-y/2,z/2),(x/2,y/2,z/2),(-x/2,y/2,z/2)
    ]

    faces = [
        (0,1,2),(0,2,3),
        (4,5,6),(4,6,7),
        (0,1,5),(0,5,4),
        (2,3,7),(2,7,6),
        (1,2,6),(1,6,5),
        (0,3,7),(0,7,4)
    ]

    return verts, faces


def collada(vertices, faces):
    v_str = " ".join([f"{v[0]} {v[1]} {v[2]}" for v in vertices])
    i_str = " ".join([f"{a} {b} {c}" for (a,b,c) in faces])

    return f'''<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
<asset>
<contributor><authoring_tool>M3</authoring_tool></contributor>
<unit name="meter" meter="1"/>
<up_axis>Z_UP</up_axis>
</asset>

<library_geometries>
<geometry id="mesh" name="mesh">
<mesh>

<source id="pos">
<float_array id="pos-array" count="{len(vertices)*3}">
{v_str}
</float_array>
<technique_common>
<accessor source="#pos-array" count="{len(vertices)}" stride="3">
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
<p>{i_str}</p>
</triangles>

</mesh>
</geometry>
</library_geometries>

<library_visual_scenes>
<visual_scene id="Scene">
<node id="node">
<instance_geometry url="#mesh"/>
</node>
</visual_scene>
</library_visual_scenes>

<scene>
<instance_visual_scene url="#Scene"/>
</scene>

</COLLADA>'''


@app.route("/generate", methods=["POST"])
def generate():
    raw = request.form.get("data")
    parts = raw.split(",")

    vertices = []
    faces = []
    offset = 0

    for p in parts:
        shape, pos, rot, size = p.split("|")
        size = eval(size)

        v,f = build_cube(size)

        v = [(vx+offset,vy,vz) for (vx,vy,vz) in v]
        f = [(a+offset,b+offset,c+offset) for (a,b,c) in f]

        vertices.extend(v)
        faces.extend(f)
        offset += len(v)

    dae = collada(vertices, faces)

    filename = str(uuid.uuid4()) + ".dae"
    path = os.path.join(OUTPUT_DIR, filename)

    with open(path, "w") as f:
        f.write(dae)

    return f"http://127.0.0.1:5000/download/{filename}"


@app.route("/download/<name>")
def download(name):
    return open(os.path.join(OUTPUT_DIR, name)).read(), 200, {
        "Content-Type": "application/xml"
    }


if __name__ == "__main__":
    app.run(port=5000)
