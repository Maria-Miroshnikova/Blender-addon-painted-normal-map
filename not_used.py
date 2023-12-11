
# alt+S to save changes in blender to have them there!
# to have changes from vs code in blender: click red button in text editor and resolve conflict

import bpy
import bmesh
from bmesh.types import BMEdge, BMFace, BMLoop, BMesh, BMLayerItem
from bpy import context

from bpy.types import Mesh, Object, Collection, VertexGroup, Curve

from mathutils import Vector
from typing import List, Tuple, Set
from face_loop import *
   
##################################
# функции создания нового пустого объекта с пустым мешем без вертекс групп
    
def vertices_to_pydata(mesh: Mesh, v: List[Vector]) -> None:
    '''
    Привязка конкретных точек [(x, y, z), (...), ...] к мешу
    '''
    #!!!!!!! посмотреть видос про меш и понять, как добавить в меш новые вершины. мб надо все же bmesh.
    #mesh.vertices.
    mesh.from_pydata(v, [], [])    

#########################################

def group_new(obj: Object, group_name: str) -> VertexGroup:
    '''
    Функция создает группу с заданным именем.
    Если группа вертексов уже есть у объекта, очистить, иначе создать новую
    '''
    # теперь я не уверена что это надо делать ТАК !!!!!!!!!!!!!!!!!!!!!!
    # TODO
    if group_name in obj.vertex_groups:
        v_group = obj.vertex_groups[group_name]
        v_group.clear()
    else:
        v_group = obj.vertex_groups.new(name=group_name)
    return v_group  

def grouping_vertices(obj: Object, iteration: int, verts_id_start: int, verts_id_end: int) -> str:
    '''
    УСТАРЕЛА
    Функция создает новую группу для точек, задает ей имя с итерацией,
    добавляет все точки заданного объекта с индексами от start до end включительно
    в эту группу
    Возвращает имя группы
    '''
    group_name = "curve_" + str(iteration)
    v_group = group_new(obj, group_name)
    #print("Obj groups:")
    #print(len(obj.vertex_groups))


    v_group.add(range(verts_id_start, verts_id_end + 1), 1.0, 'ADD')
    return group_name

def add_verts_to_point_cloud_old(bm: BMesh, faces: List[BMFace]) -> List[Vector]:
    '''
    УСТАРЕЛА
    '''
    vertices = []
    # сбор центров
    for face in faces:
        vertices.append(face.calc_center_median())
    for v in vertices:
        bm.verts.new(v)
    bm.verts.ensure_lookup_table()
    return vertices

#def make_point_cloud(mesh: Mesh, obj: Object, faces: List[BMFace], iteration: int) -> None:
def make_point_cloud(bm: BMesh, obj: Object, faces: List[BMFace], iteration: int) -> None:
    '''
    УСТАРЕЛА
    Функция получает на вход набор граней из одной face loop,
    чтобы превратить их в набор точек с общей vertex group и добавить их
    в облако точек (obj, mesh)
    iteration нужна чтобы создавать группу с итерацией в названии
    
    !!! эта функция опирается на то, что все точки добавляются в меш с индексом от
    (последний индекс добавлениия -> длина добавления) и точки в этом диапазоне индексов все
    нужно добавить в одну группу
    '''
    # не факт что id совпадут
    verts_id_start = len(bm.verts)
    
    print("--- bmesh verts before adding:")
    for idx, v in enumerate(bm.verts):
        print(idx, v)
    #добавление вершин в pointcloud и ????? обновление меша?
    vertices = add_verts_to_point_cloud_old(bmesh, faces)
    print("bmesh verts after adding:")
    for idx, v in enumerate(bm.verts):
        print(idx, v)

    #не факт, что id совпадут
    verts_id_end = verts_id_start + len(vertices) - 1
    
    # добавление в меш
    #vertices_to_pydata(mesh, vertices)

    #layers = bm.verts.layers.deform
    #print("lets print layers")
    #for l in layers:
 #       print(l)
   
   
    # вызов функции создания группы и добавления в группу
   # group_name = grouping_vertices(obj, iteration, verts_id_start, verts_id_end)
    
   # check_vertexgroup_verts(obj, group_name)

################################

def grouping_layers(bm: BMesh, id_start: int, id_end: int, group_id: int) -> None :
    '''
    функция достает нужный слой bm и в этот слой каждой точке записывает vertex_group с дефолтным весом 1
    '''
    weight_default = 1
    layer = bm.verts.layers.deform.verify() # достаем название слоя, где перечислены v_groups для каждой вершины.
    # verify такой слой создает, если его нету, или дает известный.
    for i in range(id_start, id_end + 1):
        # если v[layer] это словарь, то вот как добавить группу в этот словарь!
        #print("add vert ", i, " to group ", group_id)
        bm.verts[i][layer][group_id] = weight_default
        

def add_verts_and_group(bm: BMesh, obj: Object, vertices: List[Vector], iter: int) -> None:
    '''
    функция добавляет набор точек в bm (pointcloud) и добавляет в слой этого bm
    созданный здесь же vertex group
    все данные хранятся в bm и не будут видны пока не сделаем bm.to_mesh и obj.data.update снаружи!
    '''

    #добавить точки в bm
    id_start = len(bm.verts)
    id_end = id_start + len(vertices) - 1
    add_verts_to_bmesh(bm, vertices)
    
    #создать vertex group
    group_name = "curve_"+str(iter)
    v_group = group_new(obj, group_name)
    #group_id = obj.vertex_groups[group_name].index
    group_id = v_group.index

    #добавить группу в слой bm и точки в группу
    grouping_layers(bm, id_start, id_end, group_id)
    #check_vertexgroup_verts(obj, group_name)

def check_vertexgroup_verts(obj: Object, group_name: str):
    #как досать вершины и их номер группы?
    #
    # vertex.groups - список объектов типа VertexGroupELements, которые означают что-то типа вес+группа (id), где эта вершина состоит
    # obj.vertex_groups - словарь (НАЗВАНИЕ: данные) групп, в которых состоят вершины объекта
    # obj.vertex_groups[group_name] - данные конкретной группы, index - ее id
    # в этом коде мы собираем список вершин объекта, у которых среди id групп, в которых они состоят, есть id нужной нам группы
    # решение:
    #print([vert for vert in obj.data.vertices if obj.vertex_groups[group_name].index in [i.group for i in vert.groups]])
    vertexes_from_group = [vert for vert in obj.data.vertices if obj.vertex_groups[group_name].index in [i.group for i in vert.groups]]
    v_ids = [v.index for v in vertexes_from_group]
    print("Group [", group_name, "] = ", len(v_ids))
    print(v_ids)    

#def check_groups(obj: Object):
#    names = ["curve_1", "curve_2"]
#    for name in names:
#        check_vertexgroup_verts(obj, name)

################################

#exploring face loops and vertex groups
def main_loops():
    '''
    Эта функция вызываеися из edit mode, Edge (2)
    Необходимо чтобы было выбрано ребро, иначе будет выбрано случайное
    НО если это случайное ребро будет принадлежать не кваде, то ничего не произойдет!
    
    Функция вызывает обход face loop с выбранным ребром, создает облако точек с центрами в
    пройденных гранях, помещает это облако точек в отдельный объект и все точки помещает в одну группу
    '''
    
    mesh_obj = bpy.context.active_object
    
    bm = bmesh.from_edit_mesh(mesh_obj.data)
    
    # создаем объект, меш, привязываем к коллекции, все пустое.
    # это - будущее облако точек.
    name = "PointCloud"
    pointcloud_obj = make_new_obj_with_empty_mesh_with_unique_name_in_scene(name)

    pointcloud_mesh = pointcloud_obj.data
    # создает bmesh для него чтобы можно было добавлять точки.
    pointcloud_bm = bmesh.new()
    pointcloud_bm.from_mesh(pointcloud_mesh)

    # определяемся, с чего начинать. Если есть выбранная - с выбранной, иначе - с некой 0-ой
    # TODO: переделать на face?
    selected_edges = [edge for edge in bm.edges if edge.select]
    
    if not selected_edges:
        starting_edge = bm.edges[0]
    else:
        starting_edge = selected_edges[0]
        
    # предположим, что выбрано ребро на квадратной грани, а то в итоге пустая лупа будет!        
        
    #faces_in_loop = go_through_loop(starting_edge)
    faces_in_loop = collect_face_loop(starting_edge)
    print(faces_in_loop)
    for face in faces_in_loop:
        face.select = True
    #make_point_cloud(pointcloud_bm, pointcloud_obj, faces_in_loop, 1)
    vertices = []
    for face in faces_in_loop:
        vertices.append(face.calc_center_median())
    add_verts_and_group(pointcloud_bm, pointcloud_obj, vertices, 1)

    faces_in_loop = collect_face_loop(bm.edges[10])
    print(faces_in_loop)
    for face in faces_in_loop:
        face.select = True
    #make_point_cloud(pointcloud_mesh, pointcloud_obj, faces_in_loop, 2)
    vertices = []
    for face in faces_in_loop:
        vertices.append(face.calc_center_median())
    add_verts_and_group(pointcloud_bm, pointcloud_obj, vertices, 2)

    # обновление объекта на экране
    bmesh.update_edit_mesh(mesh_obj.data)
    # обновление point cloud на экране
    pointcloud_bm.to_mesh(pointcloud_mesh)
    pointcloud_obj.data.update()

    check_vertexgroup_verts(pointcloud_obj, 'curve_1')
    check_vertexgroup_verts(pointcloud_obj, 'curve_2')


    ##########
    
    ########

    # очистка памяти от bm
    bm.free()
    pointcloud_bm.free()

####################################

def curve_new(name: str) -> Curve:
    '''
    Если кривая с именем таким уже есть - сделать пустым, если нет - создать новый пустой
    '''
    if name in bpy.data.curves:
        curve = bpy.data.curves[name]
        curve.splines.clear()
    else:
        curve = bpy.data.curves.new(name, 'CURVE')
    
    print("Curve created")
    return curve

def obj_curve_new(name : str, curve: Curve) -> Object:
     '''
     Если объект с именем таким уже есть - перепривязать переданный кривую, если нет - создать новый объект      
     '''
     
     if name in bpy.data.objects:
         object = bpy.data.objects[name]
         assert object.type == 'CURVE'
         object.data = curve
     else:
         object = bpy.data.objects.new(name, curve)
     print("Object created")
     return object


def add_point_to_spline(spline, coords):
    spline.bezier_points.add(1)
    point = spline.bezier_points[-1]
    point.co = coords

# exploring curves
def main_curves():
    name = "test_curve"
    curve = curve_new(name)
    obj = obj_curve_new(name, curve)
    
    # привязка объекта к сцене
    col_name = "TestCol"
    #assert col_name in bpy.data.collections
    col = bpy.data.collections[col_name] #коллекция это папка!
    ob_to_col(obj, col)
    
    curve.splines.new('BEZIER')
    spline = curve.splines.active
    add_point_to_spline(spline, (0, 2.0, 0))
    add_point_to_spline(spline, (1, 3.0, 0))
    
  #  print(type(curve))
    
    
    #curve.vertex_add((0, -1.0, 0))
    
    #bm = bmesh.from_edit_mesh(mesh_obj.data)
    
    

    # очистка памяти от bm
    #bm.free()

#####################################

def get_uv_of_mesh_face_center_obj(face: BMFace, uv_layer) -> Vector:
    '''
    УСТАРЕЛА: использует Mesh для доступа к uv, что возможно только в object mode

    функция для данной грани(не в UV) ищет координаты ее центра уже в UV
    возвращает 2D вектор
    Соотносится с ой UVMap, которая получается с помощью GeoNodes (развертка).
    TODO: будет ли соотноситься с холстом, который создается GeoNodes curve painter?
    '''
    loops = face.loops
    sum_1 = sum_2 = 0
    for loop in loops:
        uv_data = uv_layer.uv[loop.index]
        print(type(uv_data))
        uv = uv_data.vector
        print(type(uv), uv[0], uv[1])
        sum_1 += uv[0]
        sum_2 += uv[1]
    return Vector([sum_1 / len(loops), sum_2 / len(loops)])

def get_uv_vertices_from_faces_obj(faces: List[BMFace], mesh: Mesh) -> List[Vector]:
    '''
    УСТАРЕЛА: использует Mesh для доступа к uv, что возможно только в object mode

    функция отображает каждую грань в UV и находит там её центр
    возвращает координаты всех центров в UV

    Периодически не работает из-за смены режима / Unwrap / других непонятностей...
    '''
    uv_layer = mesh.uv_layers.active

    vertices = []
    for face in faces:
        vertices.append(get_uv_of_mesh_face_center_obj(face, uv_layer))
    return vertices

# функция, которую предполагается вызывать для результатов, полученных из функции collect_face_loop
def process_faces_from_loop_obj(faces: List[BMFace], idx_change_dir: int, delta_z: float, mesh_to_project: Mesh, strokes_bm: BMesh):
    '''
    УСТАРЕЛА: использует Mesh для доступа к uv, что возможно только в object mode

    Эта функция принимает на вход список граней (объекта mesh_to_project), входящих в петлю,
    находит их центры в UV координатах,
    создает из них цепь и добавляет в объект-накопитель-штрихов strokemesh_bm
    '''
    uv_centers_of_loop_faces = get_uv_vertices_from_faces_obj(faces, mesh_to_project)
    add_vertices_made_in_line_with_delta_z(strokes_bm, uv_centers_of_loop_faces, idx_change_dir, delta_z)

# exploring uv
def main_uv():

    # Знакомство с uv в Mesh
    # !!! TODO: все написанные тут функции используют микс Mesh и BMesh, хотя можно свести только ко второму

    obj = bpy.context.active_object

    mesh = obj.data
    uv_layer = mesh.uv_layers.active
    
    #uv_data = uv_layer.data
    ud_data_uv = uv_layer.uv
    #print(uv_data)
    print(ud_data_uv)
    
    uv_coords = []
    
    items_uv_uv = ud_data_uv.items()
  #  print(items_uv_uv[1][-1])
   # print(type(items_uv_uv[1][-1]))
  #  print(items_uv_uv)

    for item in items_uv_uv:
        uv_coords.append(item[-1].vector)
    


    print(uv_coords[0:2])
    
    faces = []
    bm = bmesh.new()
    bm.from_mesh(mesh)

    # Ниже - визуализация uv_центров для теста

    # создаем объект, меш, привязываем к коллекции, все пустое.
    # это - будущее облако точек.
    name = "UVProjection"
    pointcloud_obj = make_new_obj_with_empty_mesh_with_unique_name_in_scene(name)

    pointcloud_mesh = pointcloud_obj.data
    # создает bmesh для него чтобы можно было добавлять точки.
    pointcloud_bm = bmesh.new()
    pointcloud_bm.from_mesh(pointcloud_mesh)

    vertices = get_uv_vertices_from_faces_obj(bm.faces, mesh)
    add_verts_to_bmesh(pointcloud_bm, [Vector([v[0], v[1], 0]) for v in vertices])
    # обновление point cloud на экране
    pointcloud_bm.to_mesh(pointcloud_mesh)
    pointcloud_obj.data.update()
    pointcloud_bm.free()  
    
def main_fixing_uv_bugs():
    # в edit mode layer становится пустым...
    mesh_obj = bpy.context.active_object
    mesh = mesh_obj.data
    
    bpy.ops.object.editmode_toggle()
    
    bm = bmesh.from_edit_mesh(mesh)
    
    faces = bm.faces
    
    uv_centers = get_uv_vertices_from_faces_em(faces, bm)
    print("centers uv: ", uv_centers)
    
    bm.free()
    bpy.ops.object.editmode_toggle()
    
    # Ниже - визуализация uv_центров для теста

    # создаем объект, меш, привязываем к коллекции, все пустое.
    # это - будущее облако точек.
    name = "UVProjection"
    pointcloud_obj = make_new_obj_with_empty_mesh_with_unique_name_in_scene(name)

    pointcloud_mesh = pointcloud_obj.data
    # создает bmesh для него чтобы можно было добавлять точки.
    pointcloud_bm = bmesh.new()
    pointcloud_bm.from_mesh(pointcloud_mesh)

    add_verts_to_bmesh(pointcloud_bm, [Vector([v[0], v[1], 0]) for v in uv_centers])
    # обновление point cloud на экране
    pointcloud_bm.to_mesh(pointcloud_mesh)
    pointcloud_obj.data.update()
    pointcloud_bm.free()  
    

if __name__ == "__main__":
    main_fixing_uv_bugs
    
# для дебага из vscode....
# может ломать результат в blender    
#main()