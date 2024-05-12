
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
from old_versions import *
   
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
# функции для обхода лупы (сбор перпендикулярных ей) в двух ориентациях. Не нужна, т к есть функция обхода лупы по ребру, которое однозначно
# определяет направление

# если определять начало через ребро а не через кваду, то ориентация будет однозначной.
# мб эта функция потом понадобится для автозаполнения, но начнем не с нее.
# каждый face может принадлежать 2 лупам, но каждое ребро принадлежит только 1 кольцу
# стоит ли передавать множество не самих bmface а только их id? TODO
# set будет передаваться по ссылке или нет? TODO
def loops_for_loop(start_quad: BMFace, is_horisontal: bool, visited_faces: Set[BMFace], obj: Object, mesh: Mesh) -> None:
    '''
    идти вдоль лупы, содержащей данную quad вдоль заданного направления и собирать все принадлежащие ей
    перпендикулярные лупы
    '''
    
    # уже знаем, что грань квадратная
    # или нам это не надо,тк заложено в функцию обхода лупы? TODO!
    edge = start_quad.edges[0]
    loop = edge.link_loops[0]
    if (is_horisontal):
        edge = loop.link_loop_next.edge
        #loop = edge.link_loops[0]
    #else:
        #loop = start_quad.loops[1]

    faces_in_loop, edge_ring = collect_face_loop(edge)
    for idx, e in enumerate(edge_ring):
        loop = e.link_loops[0]
        # не будет ли тут путаницы?
        start_edge = loop.link_loop_next.edge
        faces_in_loop_inner, edge_ring_inner = collect_face_loop(start_edge)
        make_point_cloud(mesh, obj, faces_in_loop_inner, idx)

def loops_for_loop_both_orientations(start_quad: BMFace, visited_faces: Set[BMFace], obj: Object, mesh: Mesh):
    loops_for_loop(start_quad, True, visited_faces, obj, mesh)
    loops_for_loop(start_quad, False, visited_faces, obj, mesh)
    pass

#################################


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

#########################################
# --- --- edit face layers

# константы для слоя обозначения принадлежности грани строкмешу, которому соответствует данный слой
BELONGS_TO_STROKEMESH = 1
NOT_BELONG_TO_STROKEMESH = -1

# НЕ ИСПОЛЬЗУЕТСЯ (не работает удаление слоев). Вместо этого - работа с файлом, см. 4 функции ниже
def write_faces_to_layer(bm: BMesh, layer_name: str, faces_id: List[int]):
    '''
    layer_name = имя слоя = имя strokemesh, в котором создается вершина в uv для данной грани face_id
    функция должна вызываться каждый раз, когда грани используются для построения точек в uv развертке в строкмеше
    '''
    if layer_name not in bm.faces.layers.int:
        strokemesh_layer = bm.faces.layers.int.new(layer_name)
    else:
        strokemesh_layer =  bm.faces.layers.int[layer_name]

    for f in faces_id:
        bm.faces[f][strokemesh_layer] = BELONGS_TO_STROKEMESH

# НЕ ИСПОЛЬЗУЕТСЯ. Вместо этого - работа с файлом, см. 4 функции ниже
# почему-то эта функция уничтожает вершины когда удаляет слой
# не могу выяснить, как удалять слой без удаления вершин, поэтому
def recalculate_strokemesh_layers(bm: BMesh, strokemesh_name_base: str):
    '''
    Функция пересчитывает слои граней, связанные со строкмешами
    - Удаляем слои граней, соответствующие несуществующим сейчас строкмешам
    - Устанавливает видимость строкмешей
    - Возвращает множество id граней, которые используются в видимых строкмешах

    Функция нужна, чтобы можно было вызывать постройку строкмешей для граней, которые уже используются в других мешах,
    но все их меши невидимы.

    !!! Не вызывать функцию до того, как будет настроено создание слоев строкмешей для граней
    '''
    strokemesh_dict = {} # strokemesh_name : visibility
    #visible_names = set()
    
    # определяем, какие сейчас существуют строкмеши и их видимость
    for o in context.view_layer.objects:
        if strokemesh_name_base not in o.name:
                continue
        # видимые
        #if o.hide_viewport or o.visible_get():
            #visible_names.add(o.name)
        strokemesh_dict[o.name] = (o.hide_viewport or o.visible_get())
    
    # определяем, какие существуют слои строкмешевые и ссылки на них
    layer_dict = {} # слои, соответствующие существующим строкмешам
    not_existing_strokemesh_layers = set()
    #for strokemesh in strokemesh_dict.keys:
    #    if strokemesh not in bm.faces.layers.int:
    #        la
    for layer in bm.faces.layers.int:
        if strokemesh_name_base not in layer.name:
            continue
        # слой есть, а strokemesh нет (слой надо очистить)
        if layer.name not in strokemesh_dict:
            not_existing_strokemesh_layers.add(layer)
        # слой есть и строкмеш есть
        else:
            layer_dict[layer.name] = layer
        # слоя нет, а строкмеш есть - невозможно! Как только создается строкмеш, создается и слой
        # TODO функция должна запускаться только после того, как введем создание слоев при создании строкмешей
    
    # удаляем слои от несуществующих strokemesh
    # больше никакой очистки/переписывания не нужно!
    for layer in not_existing_strokemesh_layers:
        print("remove layer: " + str(layer.name))
        bm.faces.layers.int.remove(layer)

    used_faces_id = set()
    # переписываем слои для каждой грани и запоминаем занятые грани
    for face in bm.faces:
        for layer_name in layer_dict.values():
            layer = layer_dict[layer_name]
            # если грань используется в слое и слой видимый
            if (face[layer] == BELONGS_TO_STROKEMESH) and (strokemesh_dict[layer_name]):
                used_faces_id.add(face.index)

    return used_faces_id

###########################################

# медленные версии функций посроения вектора в грани под углом, лишние действия

def count_UV_verts_in_face_with_angle_around_OX_slow(bm: BMesh, face: BMFace, ring_edge_loop: BMLoop, angle: float, len_coeff: float):
    '''
    Функция вычисляет координаты двух точек, лежащих на линии, проходящей через центр масс и повернутой относительно OX на угол angle (в радианах!)
    rign_edge_loop - (уже не актуально, т. к. угол относительно OX. можно либо ее, либо face)
    длина построенного вектора = len_coeff * (длина самой короткой высоты от центра масс к сторонам грани)
    '''

    uv_layer = bm.loops.layers.uv.verify()
    
    loop_start = ring_edge_loop
    # названия последовательных вершин:
    # v_1 = loop_start.vert
    # v_2 = loop_start.link_loop_next.vert
    # u_1 = loop_start.link_loop_next.link_loop_next.vert
    # u_2 = loop_start.link_loop_prev.vert
    
    # перевод координат в UV

    v_1_uv_co = loop_start[uv_layer].uv
    v_2_uv_co = loop_start.link_loop_next[uv_layer].uv
    u_1_uv_co = loop_start.link_loop_next.link_loop_next[uv_layer].uv
    u_2_uv_co = loop_start.link_loop_prev[uv_layer].uv
    
    v_center: Vector = (v_1_uv_co + v_2_uv_co) / 2
    u_center: Vector = (u_1_uv_co + u_2_uv_co) / 2
    
    # точка/вектор O
    center_co: Vector = (v_center + u_center) / 2
    
    min_h = count_minimum_h_from_mass_center_slow(center_co, v_1_uv_co, v_2_uv_co, u_1_uv_co, u_2_uv_co)
    
    axis_vector = Vector((1, 0))
    rotation_matrix_1 = Matrix.Rotation(angle, 2, axis_vector)
    rotation_matrix_2 = Matrix.Rotation(angle + math.radians(180.0), 2, axis_vector)

    p = center_co + len_coeff * min_h * rotation_matrix_1 * axis_vector
    q = center_co + len_coeff * min_h * rotation_matrix_2 * axis_vector

    return p, q

def count_minimum_h_from_mass_center_slow(center_co: Vector, v_1_uv_co: Vector, v_2_uv_co: Vector, u_1_uv_co: Vector, u_2_uv_co: Vector):
    '''
    v1, v2, u1, u2 - последовательные вершины грани, координаты в uv развертке
    center_co - центр масс грани, координаты в uv_развертке
    функция строит высоты из центра масс к каждой стороне и наход самую короткую высоту
    возвращает длину минимальной высоты
    '''
    # точки пересечения высот из О со сторонами
    h_v1_v2, other = geometry.intersect_point_line(center_co, v_1_uv_co, v_2_uv_co)
    h_v2_u1, other = geometry.intersect_point_line(center_co, u_1_uv_co, v_2_uv_co)
    h_u1_u2, other = geometry.intersect_point_line(center_co, u_1_uv_co, u_2_uv_co)
    h_u2_v1, other = geometry.intersect_point_line(center_co, v_1_uv_co, u_2_uv_co)
    
    # векторы высот из О к сторонами
    h_vectors = []
    h_vectors.append(center_co - h_v1_v2)
    h_vectors.append(center_co - h_u1_u2)
    h_vectors.append(center_co - h_v2_u1)
    h_vectors.append(center_co - h_u2_v1)
   # h_v1_v2_vec = center_co - h_v1_v2
   # h_u1_u2_vec = center_co - h_u1_u2
   # h_v2_u1_vec = center_co - h_v2_u1
   # h_u2_h1_vec = center_co - h_u2_v1

    # поиск минимальной высоты и ее вектора
    min_h = float('inf')
    #min_h_vec = None
    for h_vector in h_vectors:
        if h_vector.magnitude < min_h:
            min_h = h_vector.magnitude
            #min_h_vec = h_vector

    return min_h

#################################################################################################################################################
# - фильтр, опирающийся на угол относительно ОХ

def filter_angles_for_mesh(bm: BMesh, face_to_angle_dict: dict, len_coeff: float, layer_name: str, zone_to_priority_dict: dict, filter_params: List[int]):
    '''
    Функция фильтрует каждую грань меша, получая усредненный угол (на основе значений базовых углов данной грани и смежных граней)
    Затем ищет точки для вектора под таким углом для этой грани
    Записывает вектора в словарь face_id: (p, q)
    '''
    # TODO: добавить параметры фильтра
    # TODO: настроить приоритеты в меше самом!

    face_to_vector_dict: dict = {}

    for key in face_to_angle_dict.keys():
        # считываем базовые угол, посчитанный заранее
        basic_angle, loop_start = face_to_angle_dict[key]

        # подсчет нового угла с помощью фильтра для грани с id = key
        # TODO filter_params вместо []
        
        angle = filter_face_angle(bm, bm.faces[key], face_to_angle_dict, filter_params, layer_name, zone_to_priority_dict)
        #angle, ring_edge_loop = face_to_angle_dict[key]
        #angle = -math.radians(45.0)

        # поиск точек для вектора под новым углом
        p, q = count_UV_verts_in_face_with_angle_around_OX(bm, loop_start, angle, len_coeff)
        
        # запись в словарь face_id : (p, q)
        face_to_vector_dict[key] = (p, q)

    return face_to_vector_dict

def filter_face_angle(bm: BMesh, face: BMFace, face_to_angle_dict: dict, filter_params: List[int], layer_name: str, zone_to_priority_dict: dict):
    
    # BFS с глубиной обхода = len(filter_params)

    # для конкретной грани - достать ее зону из слоя, достать из словаря приоритет этой зоны
    # считать общую сумму приоритетов зон и приоритетов фильтра
    
    face_zones_layer =  bm.faces.layers.int[layer_name]

    filter_priority_summ = 0
    zone_priority_summ = 0
    angle_summ = 0
    summ = 0

    depth = 0
    max_depth = len(filter_params) - 1
    queue = []
    queue_faces = set()
    visited_faces = set()
    queue.append((face, depth))
    queue_faces.add(face.index)
    while(len(queue) > 0):
        current_face, current_depth = queue.pop()
        visited_faces.add(current_face.index)
        queue_faces.remove(current_face.index)
        
        # подсчет вклада этой грани в угол
        filter_priority = filter_params[current_depth]
        
        zone_index = bm.faces[current_face.index][face_zones_layer]
        zone_priority = zone_to_priority_dict[zone_index]

        angle, ring_edge_loop = face_to_angle_dict[current_face.index]

        #zone_priority_summ += zone_priority
        #filter_priority_summ += filter_priority
        summ += filter_priority * zone_priority
        angle_summ += filter_priority * zone_priority * angle

        # добавление смежных граней в очередь, если только мы не на максимальной глубине
        if (current_depth == max_depth):
            continue
        # крестовой фильтр (не оч)
        # TODO неправильная проверка in queue!!!!!!! не учитывается глубина
        #for loop in current_face.loops:
        #    if loop.edge.is_boundary:
        #        continue
        #    radial_loop: BMLoop = loop.link_loop_radial_next
        #    adj_face = radial_loop.face
        #    if adj_face in queue:
        #        continue
        #    if adj_face.index in visited_faces:
        #        continue
        #    queue.append((adj_face, current_depth + 1))

        # ~квадратный фильтр ()
        for vert in current_face.verts:
            for f in vert.link_faces:
                if f.index in queue_faces:
                    continue
                if f.index in visited_faces:
                    continue
                queue.append((f, current_depth + 1))
                queue_faces.add(f.index)
        
   # angle_summ /= zone_priority_summ * filter_priority_summ
    angle_summ /= summ

    return angle_summ

def make_basic_vectors_angles_for_all_grid(bm: BMesh, grid_edges: List[BMEdge], visited_faces_id, layer_name: str, zones_dict: dict,
                                    concentric_result: List[Tuple[List[BMFace], List[BMLoop], int]]):
    '''
    Функция вызывает обход не концентрических областей и подсчет углов базовых векторов с OX для граней колец,
    а также то же самое в ранее обойденных концентрических областях
    '''

    #faces_to_vector_dict = {} # словарь face_id : vector (p - q), где p и q - точки на третях средней линии грани -- тестовое
    faces_to_angles_dict = {} # словарь face_id : angle, в радианах, - угол между главной средней линией грани и осью OX, в uv координатах.
    
    # сбор колец неконцентрических областей и подсчет углов одновременно
    go_all_grid_nonconcentric_areas(bm, grid_edges, visited_faces_id, layer_name, zones_dict, faces_to_angles_dict, count_basic_vector_angle_for_ring)

    # подсчет углов концентрических областей
    for result in concentric_result:
        for edge_ring in result:
            faces, loops, idx_change_dir, not_quads = edge_ring
            count_basic_vector_angle_for_ring(faces, loops, faces_to_angles_dict, bm)
    return faces_to_angles_dict

def count_basic_vector_angle_for_ring(faces: List[BMFace], ring_loops: List[BMLoop], face_to_angle_dict: dict, bm: BMesh):
    '''
    Функция строит базовую кривую вдоль кольца.
    Для каждой грани она вычислят координаты в UV для двух точек отрезка кривой, расположенного внутри грани
    перпендикулярно ребрам кольца посередине грани.
    Это и есть вектор базовый.
    Для каждой грани запоминается ее вектор.
    
    '''
    for i in range(0, len(ring_loops)):
        loop_start = ring_loops[i]
        
        # -- поиск точек для векторов базовых -- для тестов
        #p, q = count_UV_coords_for_two_basic_verts_in_face(loop_start, loop_end, bm)

        # -- вычисление угла базового и сразу построение без фильтра -- для тестов
        #angle = count_angle_of_main_middle_line_around_OX_in_UV_radians(loop_start, bm)
        #len_coeff = 0.8
        #p, q = count_UV_verts_in_face_with_angle_around_OX(bm, loop_start.face, loop_start, angle, len_coeff)

        # -- вычисление угла базового
        angle = count_angle_of_main_middle_line_around_OX_in_UV_radians(loop_start, bm)
        
        # записать в словарь: (точка, точка) -- для тестов
        #face_to_vector_dict[loop_start.face.index] = (p, q)

        # запись в словарь: (базовый угол, ребро кольца)
        face_to_angle_dict[loop_start.face.index] = (angle, loop_start)
        
    #for face in faces:
    #    assert(face.index in face_to_vector_dict)
    return

def count_UV_verts_in_face_with_angle_around_OX(bm: BMesh, ring_edge_loop: BMLoop, angle: float, len_coeff: float):
    '''
    Функция вычисляет координаты двух точек, лежащих на линии, проходящей через центр масс и повернутой относительно OX на угол angle (в радианах!)
    rign_edge_loop - (уже не актуально, т. к. угол относительно OX. можно либо ее, либо face)
    длина построенного вектора = len_coeff * (длина самой короткой высоты от центра масс к сторонам грани)
    '''
    uv_layer = bm.loops.layers.uv.verify()
    
    # КОРОЧЕ до вершин придется достучаться через лупы соответствующие, потому что слой у них
    # поэтому нужно для каждой точки найти соответствующую ей лупу и у нее уже просить координаты точки в uv
    loop_start = ring_edge_loop

    center_co = Vector((0.0, 0.0))

    for loop in loop_start.face.loops:
        # сумма векторов всех точек грани в uv координатах
        center_co += loop[uv_layer].uv
    
    center_co /= 4
    
    min_h = count_minimum_h_from_mass_center(center_co, loop_start.face, uv_layer)
    #min_h = 0.1 # сначала чисто угол протестируем
    
    axis_vector_1 = Vector((1, 0))
    axis_vector_2 = Vector((1, 0))

    # Угол будет вверх от ОХ если угол будет БОЛЬШЕ 0. Меньше - в нижнюю полуплоскость повернемся.
    if angle < 0:
        angle = -angle
    rotation_matrix_1 = Matrix.Rotation(angle, 2, 'X')
    rotation_matrix_2 = Matrix.Rotation(angle + math.radians(180.0), 2, 'X')

    axis_vector_1.rotate(rotation_matrix_1) 
    axis_vector_2.rotate(rotation_matrix_2)
    p = center_co + len_coeff * min_h * axis_vector_1
    q = center_co + len_coeff * min_h * axis_vector_2

    return p, q

def count_angle_of_main_middle_line_around_OX_in_UV_radians(loop_start: BMLoop, bm: BMesh):
    '''
    Функция ищет угол в радианах между ОХ и главной средней линией грани
    главная средняя грань = пересекает кольцо ребер
    Если угол будет > 180 то вычтет 180
    '''
    uv_layer = bm.loops.layers.uv.verify()
    
    # КОРОЧЕ до вершин придется достучаться через лупы соответствующие, потому что слой у них
    # поэтому нужно для каждой точки найти соответствующую ей лупу и у нее уже просить координаты точки в uv

    center_co = Vector((0.0, 0.0))

    for loop in loop_start.face.loops:
        # сумма векторов всех точек грани в uv координатах
        center_co += loop[uv_layer].uv
    
    center_co /= 4
    
    middle_of_main_edge = (loop_start.link_loop_next[uv_layer].uv + loop_start[uv_layer].uv) / 2
    
    main_middle_line_vector = center_co - middle_of_main_edge

    OX = Vector((1, 0))

    # TODO: правильно ли работает это???
    angle = OX.angle_signed(main_middle_line_vector)

    # вектор главной средней линии направлен в нижнюю полуплоскость:
    if angle > 0:
  #      angle = -angle
  #      angle += math.radians(180.0)
        angle -= math.radians(180.0)
    #if angle > math.radians(180.0):
    #    angle -= math.radians(180.0)

    return angle