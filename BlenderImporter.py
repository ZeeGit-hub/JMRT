bl_info = {
    "name": "Journey Level Importer",
    "blender": (2, 80, 0),
    "category": "Import-Export",
    "description": "Import DecorationMeshInstances.lua from Journey",
}
from lupa import LuaRuntime
from lupa import lua54
import os
import bpy
import xml.etree.ElementTree as ET
import struct
from bpy_extras.io_utils import ImportHelper
from mathutils import Vector, Matrix

xml_cache = {}
def cache_xml():
    i = 0
    
    for root, _, files in os.walk("C:\\Directory to xmls\\here"):
        for file in files:
            if file.endswith('.xml'):
                filename_without_ext = os.path.splitext(file)[0]
                full_path = os.path.join(root, file)
                xml_cache[filename_without_ext] = full_path
                i = i+1
    print(f'Cached {i} xml files.')

def find_xml_from_meshname(meshname):
    for filename, full_path in xml_cache.items():
        if meshname in filename:
            return full_path

def traverse_lua_table(lua_table,depth=0):
    indent = "  " * depth
    for key, value in lua_table.items():
        if isinstance(value, (lua_table.__class__,)):
            d = dict(value)
            
            if isinstance(d["Transformation"], (lua_table.__class__,)):
                numbers = []
                for i,r in dict(d["Transformation"]).items():
                    for j,c in dict(r).items():
                        numbers.append(c)
                mat_ = [
                    #  X            Y           Z
                    [numbers[0], numbers[4], numbers[8], numbers[12]],   #Game X
                    [numbers[1], numbers[5], numbers[9], numbers[13]],   #Game Y
                    [numbers[2], numbers[6], numbers[10], numbers[14]],  #Game Z
                    [numbers[3], numbers[7], numbers[11], numbers[15]]
                ]

                mat = [
                    [numbers[2], numbers[6], numbers[10], numbers[14]], #Blender X
                    [numbers[0], numbers[4], numbers[8], numbers[12]],  #Blender Y
                    [numbers[1], numbers[5], numbers[9], numbers[13]],  #Blender Z
                    [numbers[3], numbers[7], numbers[11], numbers[15]]
                ]

            
                
            meshname = d["Mesh"]
            matrix = Matrix(mat)
            print(matrix)
            #matrix = Matrix.Rotation(radians(90), 4, 'X') @ matrix


            xmlname = find_xml_from_meshname(meshname)
            spawn_xml_model(xmlname,meshname,matrix)



def spawn_xml_model(xml_file,meshname,transformation_matrix):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    vertices = []
    faces = []

    for datablock in root.findall(".//DATABLOCK"):
        stream = datablock.find("DATABLOCKSTREAM")
        data = datablock.find("DATABLOCKDATA")

        if stream is not None and data is not None:
            render_type = stream.get("renderType")
            if render_type == "Vertex":
                vertex_data = bytes.fromhex(data.text.strip())
                for i in range(0, len(vertex_data), 12):
                    x, y, z = struct.unpack('>fff', vertex_data[i:i+12])
                    vertices.append(Vector((x, y, z)))

    for index_source in root.findall(".//RENDERINDEXSOURCE"):
        if index_source.get("primitive") == "triangles":
            index_data = index_source.find("INDEXSOURCEDATA")
            data_type = index_source.get("format")
            if index_data is not None:
                if data_type == "ushort":
                    indices = [int(x) for x in index_data.text.split()]
                    for i in range(0, len(indices), 3):
                        faces.append((indices[i], indices[i+1], indices[i+2]))
                if data_type == "uchar":
                    indices = bytes.fromhex(index_data.text.strip())
                    #print(indices)
                    for i in range(0, len(indices), 3):
                        
                        i1, i2, i3 = struct.unpack('>BBB', indices[i:i+3])
                        faces.append((i1, i2, i3))


    if not vertices or not faces:
        print(f"Invalid xml data for model:{meshname}! V:{vertices.__len__()} F:{faces.__len__()}")
        return
    
    mesh = bpy.data.meshes.new(name=meshname)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    
    obj = bpy.data.objects.new(meshname, mesh)
    bpy.context.collection.objects.link(obj)
    obj.matrix_world = transformation_matrix

class ImportLUA(bpy.types.Operator, ImportHelper):
    bl_idname = "import.lua"
    bl_label = "Import DMI.lua"

    filename_ext = ".lua"

    def execute(self, context):
        
        lua = LuaRuntime(unpack_returned_tuples=True)
        cache_xml()

        os.chdir("C:Directory to DMI\\here")
        lua = LuaRuntime(unpack_returned_tuples=True)
        #luapath = os.fsencode("C:\\Users\\14862\\Desktop\\pssgresearch\\DecorationMeshInstances.lua")
        lua.execute('dofile("DecorationMeshInstances.lua")')
        dmi_table = lua.globals().DecorationMeshInstances
        return {'FINISHED'}
        traverse_lua_table(dmi_table)
        return {'FINISHED'}

def menu_func_import(self, context):
    self.layout.operator(ImportLUA.bl_idname, text="XML Importer")

def register():
    bpy.utils.register_class(ImportLUA)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.utils.unregister_class(ImportLUA)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()
    lua = LuaRuntime(unpack_returned_tuples=True)
    cache_xml()

    os.chdir("C:Directory to DMI\\here")
    lua = LuaRuntime(unpack_returned_tuples=True)
    #luapath = os.fsencode("C:\\Users\\14862\\Desktop\\pssgresearch\\DecorationMeshInstances.lua")
    lua.execute('dofile("DecorationMeshInstances.lua")')
    dmi_table = lua.globals().DecorationMeshInstances
    traverse_lua_table(dmi_table)