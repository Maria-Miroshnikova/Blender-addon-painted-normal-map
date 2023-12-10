
# alt+S to save changes in blender to have them there!
# to have changes from vs code in blender: click red button in text editor and resolve conflict

import bpy
import bmesh
from bmesh.types import BMEdge, BMFace, BMLoop, BMesh
from bpy import context

from bpy.types import Mesh, Object, Collection, VertexGroup, Curve

from mathutils import Vector
from typing import List, Tuple, Set




##############################################
# функции обхода loop
# не работают на объектах, где лупа не зациклена и не обрамлена не квадами

def is_quad(face: BMFace) -> bool:
    '''
    Функция проверяет, является ли данная грань четырехугольной
    '''
    return (len(face.loops) == 4)

def collect_face_loop(starting_edge: BMEdge) -> (List[BMFace], int):
    '''
    Функция обхода face loop (можно переделать в edge ring), начиная с первого ребра для edge ring
    Работает только для квадов, попав на не квад/конец меша - меняет направление, попав снова - останавливается
    Сначала идет только в одном направлении, затем в другую
    Возвращает список всех граней, вошедших в face loop, и номер грани, с которой начался обход в другую сторону 
    Если петля зациклена, возвращает -1 (надо соединить последнюю вершину с первой при создании кривой)
    '''
    faces_in_loop = []
    #обход в одну сторону
    loop = starting_edge.link_loops[0]

  #  print(loop)
  #  print(loop.link_loop_next.link_loop_next)
  #  print(loop.link_loop_radial_next)
  #  print(loop.link_loop_radial_next.link_loop_next.link_loop_next)


    faces_in_loop_one_direction, was_cycled_loop = loop_go(loop, False)
    faces_in_loop.extend(faces_in_loop_one_direction)
    change_direction_face = len(faces_in_loop) - 1
    if (was_cycled_loop):
        return (faces_in_loop, -1)
    #обход в другую сторону, если не было цикла
    loop = starting_edge.link_loops[0].link_loop_next.link_loop_next
    faces_in_loop_two_direction, was_cycled_loop = loop_go(loop, True)
    faces_in_loop.extend(faces_in_loop_two_direction)
    return (faces_in_loop, change_direction_face)

def loop_go(starting_loop: BMLoop, is_second_go: bool) -> (List[BMFace], bool):
    '''
    Функция обхода face loop (можно переделать в edge ring), начиная с первого ребра для edge ring
    Работает только для квадов, попав на не квад - останавливается
    Возвращает список всех граней, вошедших в face loop при обходе в данном направлении
    is_second_go нужен, чтобы при обходе в обратную сторону не добавлять первую грань еще раз в список
    '''
    faces_in_loop = []
    loop = starting_loop
    #loop.edge.select = True
    
    # ??????????????????????????? мб проблема с направлениями, мб надо судя именно face подавать чтобы было точнее, а не ребро!
    if (not is_quad(loop.face)):
        return [], False
    #
    if (not is_second_go):
        faces_in_loop.append(loop.face)
    
    radial_loop = loop.link_loop_radial_next
    # проверяем, что mesh оборвался (плоская поверхность)
    if (radial_loop.face == loop.face):
        return faces_in_loop, False
    # проверяем, следующая грань это квада? 
    is_next_face_quad = is_quad(radial_loop.face)
    if (not is_next_face_quad):
        # уперлись в не квадратную грань, конец обхода
        return faces_in_loop, False
    else:
        faces_in_loop.append(radial_loop.face)
    next_loop = radial_loop.link_loop_next.link_loop_next
    next_loop.edge.select = True
    
    # цикл прыжков для сбора всей лупы пока не упремся в не кваду или не вернемся в начальную (замкнутая лупа)
    # или не закончится плоский меш
    
    loop = next_loop
    while next_loop.edge != starting_loop.edge:
        radial_loop = loop.link_loop_radial_next
        next_loop = radial_loop.link_loop_next.link_loop_next
        # циклический меш
        if (next_loop.edge == starting_loop.edge):
            break

        # проверяем, что mesh оборвался (плоская поверхность)
        if (radial_loop.face == loop.face):
            return faces_in_loop, False
        # проверяем, следующая грань это квада? 
        is_next_face_quad = is_quad(radial_loop.face)
        # next_face_orto_loop.face.select = is_quad(next_face_orto_loop.face)
        if (not is_next_face_quad):
            return faces_in_loop, False
        else:
            faces_in_loop.append(radial_loop.face)

        next_loop.edge.select = True
        loop = next_loop
    return faces_in_loop, True
   
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
    
def vertices_to_pydata(mesh: Mesh, v: List[Vector]) -> None:
    '''
    Привязка конкретных точек [(x, y, z), (...), ...] к мешу
    '''
    #!!!!!!! посмотреть видос про меш и понять, как добавить в меш новые вершины. мб надо все же bmesh.
    #mesh.vertices.
    mesh.from_pydata(v, [], [])    

# достать из Object его mesh почему-то достаточно obj.data. Почему?
# если ошибаюсь, то нужно все же возвращать mesh, obj
def make_mesh_obj_etc_for_pointcloud(mesh_name: str) -> Object:
    '''
    Функция, которая создает правильный объект с данным именем, удаляя из сцены дубли
    '''
    mesh = mesh_new(mesh_name)
    #print(type(mesh))
    #assert type(mesh) == Mesh
     
    obj = obj_new(mesh_name, mesh)
     
    # привязка объекта к сцене
    col_name = "TestCol"
    #assert col_name in bpy.data.collections
    col = bpy.data.collections[col_name] #коллекция это папка!
     
    ob_to_col(obj, col)
    
    print("Empty obj-mesh-etc created")
    return obj

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

################################

################################

def add_verts_to_point_cloud(bm: BMesh, vertices: List[Vector]) -> None:
    '''
    функция добавляет точки в bm
    '''
    idx_start = len(bm.verts)
    for v in vertices:
        bm.verts.new(v)
    bm.verts.ensure_lookup_table()

    for i in range(idx_start, idx_start + len(vertices)):
        bm.verts[i].index = i

# вместо этой уже есть хорошая group_new       
#def vgroup_new(group_name: str, obj: Object) -> VertexGroup:
#    v_group = group_new(obj, group_name)
#    return v_group

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
    add_verts_to_point_cloud(bm, vertices)
    
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

# make edges between vertices

# TODO: необходимо новый штрих, имеющий точки, уже входящие в меш, СДВИГАТЬ, чтобы это был отдельный объект!!
# достаточно делать это по z, когда работаем уже в uv координатах над плоскостью.
# сделать этот сдвиг всех добавляемых точек на delta z потом!
# TODO: второй вариант: оформлять каждый штрих в отдельный объект с точками в тех же местах (возможно ли? дорого по памяти?)
def add_vertices_made_in_line(bm: BMesh, vertices: List[Vector], idx_change_dir: int) -> None:
    '''
    функция добавляет точки И ребра между ними в bm
    !!! ожидается cписок ПОСЛЕДОВАТЕЛЬНЫХ вершин от 0 до idx_change_dir включительно, далее от 0-ой до конца!
    !!! это обусловлено тем, что vertices получены при обходе петли начиная с некоторой грани в одну сторону, а затем от нее же в другую,
    !!! при этом стартовая грань будет 0-ой в списке.
    !!! Если idx = -1, то кривая должна быть зациклена, т. е. последняя вершина в списке соединена с 0-ой.
    TODO: потенциально можно в функции сбора граней сделать сортировку граней. Это упростит понимание и поддержку данной функции
    но создает необходимость поддерживать лишнюю память для временного несортированного списка граней.
    '''
    if (len(vertices) == 0):
        print("Attempt to make stroke-mesh from empty vertices list.")
        return
    idx_start_vert = len(bm.verts)
    idx_start_edge = len(bm.edges)
    bm_verts_new = []
    # добавление вершин
    for v in vertices:
        new_vert = bm.verts.new(v)
        bm_verts_new.append(new_vert)

    # создание зацикленной кривой
    if (idx_change_dir == -1):
        for i in range(0, len(bm_verts_new) - 1):
            bm.edges.new((bm_verts_new[i], bm_verts_new[i + 1]))
        bm.edges.new((bm_verts_new[0], bm_verts_new[-1]))
    else:
        # добавление последовательных ребер в первом направлении
        for i in range(0, idx_change_dir):
            bm.edges.new((bm_verts_new[i], bm_verts_new[i + 1]))
        # добавление последовательных ребер в обратном направлении
        v_start = bm_verts_new[0] # вершина с грани, с которой начинался обход петли
        for i in range(idx_change_dir + 1, len(bm_verts_new)):
            bm.edges.new((v_start, bm_verts_new[i]))
            v_start = bm_verts_new[i]

    # обновление индексов вершин и ребер [так сказано в документации]
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    for i in range(idx_start_vert, idx_start_vert + len(vertices)):
        bm.verts[i].index = i
    for i in range(idx_start_edge, idx_start_edge + len(vertices) - 1):
        bm.edges[i].index = i



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
    pointcloud_obj = make_mesh_obj_etc_for_pointcloud(name)

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

#TODO: add_vertices_made_in_line со сдвигом по z
def get_uv_of_mesh_face_center(face: BMFace, uv_layer) -> Vector:
    '''
    функция для данной грани(не в UV) ищет координаты ее центра уже в UV
    возвращает 2D вектор
    Соотносится с ой UVMap, которая получается с помощью GeoNodes (развертка).
    TODO: будет ли соотноситься с холстом, который создается GeoNodes curve painter?
    '''
    loops = face.loops
    sum_1 = sum_2 = 0
    print("Layer: ", uv_layer.uv.items())
    for loop in loops:
        print("loop: s", loop)
        # !!!!TODO: не работает, если сделать Unwrap на объекте, почему-то пропадают items в uv слоя....
        uv_data = uv_layer.uv[loop.index]
        print(type(uv_data))
        uv = uv_data.vector
        print(type(uv), uv[0], uv[1])
        sum_1 += uv[0]
        sum_2 += uv[1]
    return Vector([sum_1 / len(loops), sum_2 / len(loops)])

def get_uv_vertices(faces: List[BMFace], mesh: Mesh) -> List[Vector]:
    '''
    функция отображает каждую грань в UV и находит там её центр
    возвращает координаты всех центров в UV
    TODO: уязвимое место, перестает работать если сделать Unwrap
    '''

    # TODO: в каких случаях его может не быть?
    # !!!!TODO: не работает, если сделать Unwrap на объекте, почему-то пропадают items в uv слоя....
    # !!!!TODO: вообще-то uv хранится и в слоях bmesh, там надо будет что-то типа как с группами точек делать.
    # !!! мб это как раз лечится тем, чтобы работать с bmesh?
    uv_layer = mesh.uv_layers.active

  #  print("Mesh uv layers: ", mesh.uv_layers)
  #  print("Mesh uv layers: ", mesh.uv_layers.active)

    vertices = []
    for face in faces:
        vertices.append(get_uv_of_mesh_face_center(face, uv_layer))
    return vertices

# exploring uv
#def main_uv():
def main():
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


    # создаем объект, меш, привязываем к коллекции, все пустое.
    # это - будущее облако точек.
    name = "UVProjection"
    pointcloud_obj = make_mesh_obj_etc_for_pointcloud(name)

    pointcloud_mesh = pointcloud_obj.data
    # создает bmesh для него чтобы можно было добавлять точки.
    pointcloud_bm = bmesh.new()
    pointcloud_bm.from_mesh(pointcloud_mesh)

    vertices = get_uv_vertices(bm.faces, mesh)
    add_verts_to_point_cloud(pointcloud_bm, [Vector([v[0], v[1], 0]) for v in vertices])
    # обновление point cloud на экране
    pointcloud_bm.to_mesh(pointcloud_mesh)
    pointcloud_obj.data.update()
    pointcloud_bm.free()  

##################################################

def main_():
    
    mesh_obj = bpy.context.active_object
    
    bm = bmesh.from_edit_mesh(mesh_obj.data)
    
    # создаем объект, меш, привязываем к коллекции, все пустое.
    # это - будущее облако точек.
    name = "StrokesMesh"
    pointcloud_obj = make_mesh_obj_etc_for_pointcloud(name)

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
    
    #for v in pointcloud_bm.verts:
    #    print(v)
    #for e in pointcloud_bm.edges:
    #    print(e)
        
    (faces_in_loop, change_direction_face) = collect_face_loop(starting_edge)
    #print(change_direction_face)
    #print(faces_in_loop)

    for face in faces_in_loop:
        face.select = True
    vertices = []
    for face in faces_in_loop:
        vertices.append(face.calc_center_median())
    add_vertices_made_in_line(pointcloud_bm, vertices, change_direction_face)

 #   for v in pointcloud_bm.verts:
 #       print(v)
 #   for e in pointcloud_bm.edges:
 #       print(e)

    (faces_in_loop, change_direction_face) = collect_face_loop(bm.edges[10])
    for face in faces_in_loop:
        face.select = True
    vertices = []
    for face in faces_in_loop:
        vertices.append(face.calc_center_median())
    add_vertices_made_in_line(pointcloud_bm, vertices, change_direction_face)

    # обновление объекта на экране
    bmesh.update_edit_mesh(mesh_obj.data)
    # обновление point cloud на экране
    pointcloud_bm.to_mesh(pointcloud_mesh)
    pointcloud_obj.data.update()

    ##########
    
    ########

    # очистка памяти от bm
    bm.free()
    pointcloud_bm.free()
    
    # Конвертирование в кривую и установка типа "poly curve"
    # !!!!!!!! контекстозависимая часть!!
    # TODO: пока не нашла, как сделать независимой (bmesh, mesh, object, object.data не имеют функции convert)
    # но в идеале - довести до независомого! МБ оформление в оператор как-то поможет.
    bpy.ops.object.editmode_toggle()
    bpy.context.view_layer.update()
    pointcloud_obj.select_set(True)
    bpy.context.view_layer.objects.active = pointcloud_obj

    bpy.ops.object.convert(target='CURVE')
    bpy.ops.object.editmode_toggle()
    bpy.ops.curve.spline_type_set(type='POLY')

if __name__ == "__main__":
    main()
    
# для дебага из vscode....
# может ломать результат в blender    
main()