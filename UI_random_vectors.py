import bpy
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import FloatProperty, StringProperty, EnumProperty, PointerProperty
from bpy.utils import register_class, unregister_class
import random

##############################################################################################################################################
# -- скопированное

import bpy
import bmesh
from bmesh.types import BMEdge, BMFace, BMLoop, BMesh, BMLayerItem, BMVert
from bpy.types import Mesh, Object, Collection
from bpy import context
#from face_loop import get_last_collection_index, get_last_strokemesh_index, get_last_z_coord, is_quad

from typing import List, Set, Tuple
from mathutils import Vector, geometry, Matrix
import math
import random

#############################################################################################################################################################
# -- скопированное

##################################
# функции создания нового пустого объекта с пустым мешем без вертекс групп

def mesh_new(name: str) -> Mesh:
    '''
    Если мэш с именем таким уже есть - сделать пустым, если нет - создать новый пустой
    '''
    
    if name in bpy.data.meshes:
        mesh = bpy.data.meshes[name]
        mesh.clear_geometry()
    else:
        mesh = bpy.data.meshes.new(name)
    
    print("Mesh created")
    return mesh

def obj_new(name : str, mesh: Mesh) -> Object:
     '''
     Если объект с именем таким уже есть - перепривязать переданный меш, если нет - создать новый объект      
     '''
     
     if name in bpy.data.objects:
         object = bpy.data.objects[name]
         assert object.type == 'MESH'
         object.data = mesh
         # это достоверный способ?
         # TODO!!!!!!!!!!
         object.vertex_groups.clear()
     else:
         object = bpy.data.objects.new(name, mesh)
     print("Object created")
     #print("Object groups when created:")
     #print(len(object.vertex_groups))
     return object
    
def ob_to_col(obj: Object, col: Collection) -> None:
    '''
    Отвязывает объект от всех Colltction и от всех Scene Collection
    и привязывает к нужной нам
    '''
    
    for c in bpy.data.collections:
        if obj.name in c.objects:
            c.objects.unlink(obj)
    for sc in bpy.data.scenes:
        if obj.name in sc.collection.objects:
            sc.collection.objects.unlink(obj)
    col.objects.link(obj)
    
    print("Object assigned to Collection")  

# достать из Object его mesh почему-то достаточно obj.data. Почему?
# если ошибаюсь, то нужно все же возвращать mesh, obj
def make_new_obj_with_empty_mesh_with_unique_name_in_scene(mesh_name: str, col_name_with_idx: str) -> Object:
    '''
    Функция, которая создает правильный объект с данным именем, удаляя из сцены дубли
    '''
    mesh = mesh_new(mesh_name)
    #print(type(mesh))
    #assert type(mesh) == Mesh
     
    obj = obj_new(mesh_name, mesh)
     
    # привязка объекта к сцене
    col_name = col_name_with_idx #"TestCol"
    #assert col_name in bpy.data.collections

    ### проверка существования папки и ее создание, если ее нет
    if col_name not in bpy.data.collections:
        # New Collection
        test_coll = bpy.data.collections.new(col_name)

        # Add collection to scene collection
        bpy.context.scene.collection.children.link(test_coll)
    ###

    col = bpy.data.collections[col_name] #коллекция это папка!
     
    ob_to_col(obj, col)
    
    print("Empty obj-mesh-etc created")
    return obj

def get_last_strokemesh_index(mesh_name: str, last_col_name: str):
    '''
    Функция ищет в папке last_col_name объек с именем "<mesh_name>_<index>"
    и вовзращает самый большой index
    Если вернула -1, значит, папка пустая, объекты отсутствуют
    '''
    max_index = -1
    for strokemesh in bpy.data.collections[last_col_name].objects:
        current_index = int(strokemesh.name.split('_')[-1]) # номер идет последним
        if (current_index > max_index):
                max_index = current_index
    return max_index

def make_vectormesh():
    # -- создание vectormesh и построение точек
    VECTORMESH_NAME_BASE = "VectorMesh_"
    VECTORMESH_COL_NAME = "VectorMeshes"
    #index = get_last_strokemesh_index(VECTORMESH_NAME_BASE, VECTORMESH_COL_NAME)
    #index += 1
    index = 0

    # создаем объект, меш, привязываем к коллекции, все пустое.
    # это - будущий накопитель для кривых-петель-штрихов.
    vectormesh_obj = make_new_obj_with_empty_mesh_with_unique_name_in_scene(VECTORMESH_NAME_BASE + str(index), VECTORMESH_COL_NAME)
    index += 1
    vector_mesh = vectormesh_obj.data
    # создает bmesh для него чтобы можно было добавлять точки.
    vector_bm = bmesh.new()
    vector_bm.from_mesh(vector_mesh)

    return vector_bm, vectormesh_obj

def create_and_add_vector_to_vectormesh(vectormesh: BMesh, v1: Vector, v2: Vector):
    '''
    функция по двум данным точкам создает вершины, соединенные ребром, в меше vectormesh
    '''
    idx_start_verts = len(vectormesh.verts)
    idx_start_edge = len(vectormesh.edges)

    z_coord = 0
    new_vert_1 = vectormesh.verts.new(Vector((v1.x, v1.y, z_coord)))
    new_vert_2 = vectormesh.verts.new(Vector((v2.x, v2.y, z_coord)))
    #new_vert_1 = vectormesh.verts.new(Vector((1, 0, z_coord)))
    #new_vert_2 = vectormesh.verts.new(Vector((0, 0, z_coord)))
    vectormesh.edges.new((new_vert_1, new_vert_2))
    
    # обновление данных меша, так просят делать в документации
    vectormesh.verts.ensure_lookup_table()
    vectormesh.edges.ensure_lookup_table()

    for i in range(idx_start_verts, idx_start_verts + 2):
        vectormesh.verts[i].index = i    
    vectormesh.edges[idx_start_edge].index = i
    return

def make_vector_in_point(point: Vector, length: float):

    angle_gr = random.uniform(-90, 90) # RANDOM [-90, 90]
    angle = math.radians(angle_gr)

    cos = math.cos(angle)
    sin = math.sin(angle)
    vector_1 = Vector((length * cos, length * sin))
    vector_2 = -vector_1
    #vector_1 = Vector((0, length / 2))
    #vector_2 = Vector((0, length / 2))
    #rotation_1 = Matrix.Rotation(angle, 2, 'X')
    #rotation_2 = Matrix.Rotation(angle + math.radians(180), 2, 'X')
    #vector_1.rotate(rotation_1)
    #vector_2.rotate(rotation_2)

    # эта версия создает p и q на равном расстоянии от point, она становится центром вектора pq
    p = point + vector_1
    q = point + vector_2

    return p, q

#############################################################################################################################################################

def get_uv_boundary_coords(uv_bm: BMesh):
    '''
    Функция для поиска крайних координат в uv развертке.
    Функция просматривает все краевые точки меша, записывает их uv координаты в список.
    Затем список сортируется по х и по у отдельно.
    Функция возвращает минимальные и максимальные х, у
    '''
    uv_layer = uv_bm.loops.layers.uv.verify()
    
    boundary_verts_uv = []
    for vert in uv_bm.verts:
        for loop in vert.link_loops:
            if loop.edge.is_boundary:
                boundary_verts_uv.append(loop[uv_layer].uv)

    sort_x = sorted(boundary_verts_uv, key = lambda x: x[0])
    sort_y = sorted(boundary_verts_uv, key = lambda x: x[1])
    return sort_x[0][0], sort_x[-1][0], sort_y[0][1], sort_y[-1][1]

def make_grid_for_random_vectors(bm: BMesh, uv_obj: Object, uv_bm: BMesh, step: float, distortion: float,
                                 min_x, max_x, min_y, max_y):
    z = 1

    distortion_radius = distortion / 2

    points = []
    x = min_x
    while (x < max_x):
        y = min_y
        while(y < max_y):
            current_distortion_x = random.uniform(-distortion_radius, distortion_radius)
            current_distortion_y = random.uniform(-distortion_radius, distortion_radius)
            x_dstr = x + current_distortion_x
            y_dstr = y + current_distortion_y
            point = Vector((x_dstr, y_dstr))
            origin = Vector((x_dstr, y_dstr, z))
            end = Vector((x_dstr, y_dstr, 0))
            direction = end - origin

            # перевод в локальные координаты. скорее всего это не нужно, т к должны совпадать uv оригинального объекта и сам uv obj (искусственная развертка)
            #mw = uv_obj.matrix_world
            #mwi = mw.inverted()
            #origin = mwi @ origin
            #dest = mwi @ end
            #direction = (dest - origin).normalized()
            
            result, location, normal, index = uv_obj.ray_cast(origin=origin, direction=direction)
            if (result): # точка находится над гранями развертки!
               points.append(point)
            #points.append(point)
            y += step
        x += step 
    return points

def generate_random_vectors_on_mash_with_face_area_proportionality_grid_based(bm: BMesh, vector_bm: BMesh,
                                                                              uv_obj: Object, uv_bm: BMesh,
                                                                              len_coeff: float = 0.001, min_a_coeff: float = 0.02,
                                                                              distortion_coeff: float = None):
    
    # max_size_of_UV * min_a_coeff = min_a

    min_x, max_x, min_y, max_y = get_uv_boundary_coords(uv_bm)
    max_uv_size_x = max_x - min_x
    max_uv_size_y = max_y - min_y
    if (max_uv_size_x > max_uv_size_y):
        min_a = max_uv_size_x * min_a_coeff
    else:
        min_a = max_uv_size_y * min_a_coeff

    # можно сделать distortion ручным
    if (distortion_coeff == None):
        distortion = min_a * 0.75
    else:
        distortion = min_a * distortion_coeff

    vecotr_length = len_coeff

    points = make_grid_for_random_vectors(bm, uv_obj, uv_bm, min_a, distortion, min_x, max_x, min_y, max_y)

    print("made grid points!")

    for point in points:
        p, q = make_vector_in_point(point, vecotr_length)
        create_and_add_vector_to_vectormesh(vector_bm, p, q)

def main_random_vectors():
     #--- EDIT MODE!
    mesh_obj = bpy.context.active_object
    bm = bmesh.from_edit_mesh(mesh_obj.data)

     # постройка векторов
    vector_bm, vector_obj = make_vectormesh()
   # len_coeff = 1
   # min_a = 0.4
   # generate_random_vectors_on_mash_with_face_area_proportionality(bm, vector_bm, len_coeff, min_a)
   # generate_random_vectors_on_mash_with_face_area_proportionality(bm, vector_bm, len_coeff)

    uv_object_name = "uv_0"
    uv_obj: Object = bpy.data.objects[uv_object_name]
    uv_mesh = bpy.data.meshes[uv_object_name]
    uv_bm = bmesh.new()
    uv_bm.from_mesh(uv_mesh)

    generate_random_vectors_on_mash_with_face_area_proportionality_grid_based(bm, vector_bm, uv_obj, uv_bm)

    # чистка
    vector_bm.to_mesh(vector_obj.data)
    vector_obj.data.update()
    vector_bm.free()
    bmesh.update_edit_mesh(mesh_obj.data)
    bm.free()
    uv_bm.free()

    #############################################################################################################################################################

def convert_mesh_to_curve_and_make_poly(strokes_obj: Object, mesh_obj: Object):
    '''
    Конвертирование в кривую и установка типа "poly curve"
    '''
    # !!!!!!!! контекстозависимая часть!!
    # TODO: пока не нашла, как сделать независимой (bmesh, mesh, object, object.data не имеют функции convert)
    # но в идеале - довести до независомого! МБ оформление в оператор как-то поможет.

    #--- OBJECT MODE
    strokes_obj.select_set(True)
    mesh_obj.select_set(False)
    bpy.context.view_layer.objects.active = strokes_obj

    bpy.ops.object.convert(target='CURVE')
    
    #--- EDIT MODE
    bpy.ops.object.editmode_toggle()
    bpy.ops.curve.spline_type_set(type='POLY')

    #############################################################################################################################################################
        #############################################################################################################################################################
            #############################################################################################################################################################

'''
Кнопки:
    - выбор объекта uv_obj -> OBJECT
    - размер сетки step (min_a в алгоритме) -> FLOAT (default =)
    - длина векторов vector_size (len_coeff в алгоритме) -> FLOAT (default = 0.02)
    (они должни быть близки к 0, но можно для визуализации делать их длиннее)
    - отклонение от узлов сетки distortion -> FLOAT (default = 0, soft_max = vector_size) 
    - кнопка оператора
'''

class OBJECT_PT_RandomVectorsPanel(Panel):
    bl_label = "Random Vectors for strokes"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Curves for Strokes"
    
    def draw(self, context):
        layout = self.layout
        props = context.object.random_vectors
        
        col = layout.column()
        col.prop(props, "UV_object")
        
        col = layout.column()
        #spl = col.split()
        box = col.box()
        box.prop(props, "min_a")
        
        box.prop(props, "len_coeff")
        
        box.prop(props, "distortion")
        
        col = layout.column()
        col.operator('object.random_vectors')        
    

# параметры для панели и для оператора (которые в функцию передаются)
class RandomVectorsProps(PropertyGroup):
    
    def get_items(self, context):
        object_names = [object.name for object in bpy.data.objects]
        obj_names_enums = [("empty", "", "")]
        obj_names_enums_ = [(name, name, "") for name in object_names]
      #  obj_names_enums = []#[("empty", "", "")]
       # obj_name_enums.extend([(name, name, "") for name in object_names])
       # obj_names_enums.append(("empty", "", ""))
        obj_names_enums.extend(obj_names_enums_)
        return obj_names_enums
    
   # UV_object : StringPropetry(
    UV_object : EnumProperty(
        name="UV_object",
 # TODO make empty default value
 #       default = (None, None, ""),
        description="Отдельный объект, являющийся UV-разверткой объекта, к которому применяют оператор",
        items=get_items
    )
    min_a : FloatProperty(
        name = "Dencity %",
        default = 0.02, # 2% от размера UV развертки
        min = 0.005, # 0,5% от размера UV развертки
        max = 0.1,
        subtype = 'FACTOR'
    )
    len_coeff : FloatProperty(
        name = "Vector length",
        default = 0.001,
        min = 0.001,
        soft_max = 1,
        subtype = 'FACTOR'
        
    )
    distortion : FloatProperty(
        name = "Distortion %",
        default = 0,
        min = 0,
        max = 1,
        subtype = 'FACTOR'
        
    )

# оператор, т. е. вызов функции. Здесь вся логика
class RandomVectors(Operator):
    '''
    Для выбранного объекта (в EDIT MODE) и назначенной вручную
    искусственной развертки этого объекта
    создает множество векторов над uv разверткой типа poly curve
    
    (для последующего подключения geomentry nodes
    с генерацией штрихов вдоль направляющих кривых)
    '''
    
    bl_idname = 'object.random_vectors'
    bl_label = 'Create random vectors'
    
    # params
    UV_object = None
    a_min = None
    len_coeff = None
    distortion = None
    
    def get_params(self, context):
        props = context.object.random_vectors
        self.UV_object = props.UV_object
        self.a_min = props.min_a
        self.len_coeff = props.len_coeff
        self.distortion = props.distortion
        
    # собственно функция!
    def create_random_vectors(self):        
         #--- EDIT MODE!
        mesh_obj = bpy.context.active_object
        bm = bmesh.from_edit_mesh(mesh_obj.data)

        # постройка векторов
        vector_bm, vector_obj = make_vectormesh()

        uv_object_name = self.UV_object # TODO: работает?
        uv_obj: Object = bpy.data.objects[uv_object_name]
        uv_mesh = uv_obj.data
        uv_bm = bmesh.new()
        uv_bm.from_mesh(uv_mesh)

        generate_random_vectors_on_mash_with_face_area_proportionality_grid_based(bm, vector_bm, uv_obj, uv_bm,
                                                                                  self.len_coeff, self.a_min, self.distortion)

        # превратить в кривые
        #--- EDIT MODE TO OBJECT MODE
        #bpy.ops.object.editmode_toggle()
        #bpy.context.view_layer.update()
        #convert_mesh_to_curve_and_make_poly(vector_obj, mesh_obj)
        #--- OBJECT MODE TO EDIT MODE inside prev function is done already
        
        # чистка
        vector_bm.to_mesh(vector_obj.data)
        vector_obj.data.update()
        vector_bm.free()
        bmesh.update_edit_mesh(mesh_obj.data)
        bm.free()
        uv_bm.free()
        return
    
    def execute(self, context):
        #raise NotImplementedError
        self.get_params(context)
        
        # вызываем все нужные функции
        self.create_random_vectors()
        
        return {'FINISHED'}





classes = [
    RandomVectorsProps,
    RandomVectors,
    OBJECT_PT_RandomVectorsPanel
]

def register():
    for cl in classes:
        register_class(cl)
        
def unregister():
    for cl in reversed(classes):
        unregister_class(cl)
        
if __name__ == '__main__':
    # регистрируем классы
    # точнее, регистрируем наш оператор, теперь его можно вызывать у объектов всех
    register()
    
    # создаем свойство свое, оно будет у всех объектов (индивидуально) и в нем хранятся параметры
    # для генерации случайных векторов
    bpy.types.Object.random_vectors = PointerProperty(type = RandomVectorsProps)
    
    # вызов вручную в скрипте: (потом будет кнопка, а в коде вызывать его не нужно)
    bpy.ops.object.random_vectors()