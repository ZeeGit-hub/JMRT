import xml.etree.ElementTree as ET
import os
import sys
import struct


def parse(xml_file, out_dir=None):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    vertex_count = 0
    tri_count = 0

    vertices = []
    faces = []
    unk_half4s = []

    for datablock in root.findall(".//DATABLOCK"):
        stream = datablock.find("DATABLOCKSTREAM")
        data = datablock.find("DATABLOCKDATA")
        elem_count = datablock.get("elementCount")

        if stream is not None and data is not None:
            render_type = stream.get("renderType")
            if render_type == "Vertex":
                vertex_count = int(elem_count)
                vertex_data = bytes.fromhex(data.text.strip())
                vertices.append(vertex_data)
            if render_type == "ST":
                read_half(stream, data, unk_half4s)

    for index_source in root.findall(".//RENDERINDEXSOURCE"):
        if index_source.get("primitive") == "triangles":
            cnt = int(index_source.get("count"))
            if cnt != 0:
                tri_count = int(int(index_source.get("count")) / 3)
        read_triangles(index_source, faces)

    outfile = os.path.splitext(xml_file)[0]
    if out_dir is not None:
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        outfile = os.path.join(out_dir, os.path.basename(outfile))

    write_data(outfile, vertices, faces, unk_half4s, vertex_count, tri_count)
    print(f"Successfully parsed {xml_file}")


def read_half(stream, data, halfs):
    data_type = stream.get("dataType")
    if data_type not in ["half4", "half2"]:
        raise Exception(f"Unknown HALF data type: {data_type}")

    res = bytes.fromhex(data.text.strip())
    if stream.get("dataType") == "half4":
        res = [x for i, x in enumerate(res) if i % 8 < 4]
        res = bytes(res)
    halfs.append(res)


def read_triangles(index_source, faces):
    data_type = index_source.get("format")
    index_data = index_source.find("INDEXSOURCEDATA")
    if index_data is not None:
        if data_type == "ushort":
            face_data = struct.pack(
                ">" + "H" * len(index_data.text.split()),
                *map(int, index_data.text.split()),
            )
            faces.append(face_data)
        elif data_type == "uchar":
            face_data = bytes.fromhex(index_data.text.strip())
            faces.append(face_data)
        else:
            raise Exception(f"Unknown TRI data type: {data_type}")


def write_data(
    outfile: str,
    vertices: list[bytes],
    faces: list[bytes],
    halfs: list[bytes],
    vertex_count: int,
    tri_count: int,
):
    offsets = []
    with open(f"{outfile}.bin", "wb") as f:
        offset = 0
        for vertex in vertices:
            f.write(vertex)
            offset += len(vertex)

        f.write(b"\xFF" * 12)
        offset += 12
        offsets.append(offset)

        for face in faces:
            f.write(face)
            offset += len(face)

        f.write(b"\xFF" * 12)
        offset += 12
        offsets.append(offset)

        for half in halfs:
            f.write(half)

    with open(f"{outfile}.offsets", "w") as f:
        f.write("OFFSETS:\n")
        f.write(f"Faces: {offsets[0]} | 0x{offsets[0]:X}\n")
        f.write(f"UV:    {offsets[1]} | 0x{offsets[1]:X}\n")
        f.write("\nCOUNTS:\n")
        f.write(f"Vertices / UV: {vertex_count}\n")
        f.write(f"Triangles:     {tri_count}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: parse.py <filename> or parse.py <in-dir> <out-dir>")
        sys.exit(1)
    elif len(sys.argv) == 2:
        parse(sys.argv[1])
    elif len(sys.argv) == 3:
        in_dir = sys.argv[1]
        out_dir = sys.argv[2]
        for (path, dirs, files) in os.walk(in_dir):
            for file in files:
                if file.endswith(".xml"):
                    parse(
                        os.path.join(path, file),
                        os.path.join(out_dir, os.path.relpath(path, in_dir)),
                    )
