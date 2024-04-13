
# alt+S to save changes in blender to have them there!
# to have changes from vs code in blender: click red button in text editor and resolve conflict

import bpy
import bmesh
from bmesh.types import BMEdge, BMFace, BMLoop, BMesh, BMLayerItem, BMVert
from bpy import context

from bpy.types import Mesh, Object, Collection

from mathutils import Vector
from typing import List, Set, Tuple

##############################################
# функции обхода loop
# не работают на объектах, где лупа не зациклена и не обрамлена не квадами
# TODO: вообще все списки и т п переделать на индексы?

def is_quad(face: BMFace) -> bool:
    '''
    Функция проверяет, является ли данная грань четырехугольной
    '''
    return (len(face.loops) == 4)

def collect_face_loop(starting_edge: BMEdge) -> (List[BMFace], List[BMLoop], int):
    '''
    Функция обхода face loop (можно переделать в edge ring), начиная с первого ребра для edge ring
    Работает только для квадов, попав на не квад/конец меша - меняет направление, попав снова - останавливается
    Сначала идет только в одном направлении, затем в другую
    Возвращает список всех граней, вошедших в face loop, и номер грани, с которой начался обход в другую сторону 
    Если петля зациклена, возвращает -1 (надо соединить последнюю вершину с первой при создании кривой)
    '''
    faces_in_loop = []
    loops = []
    #обход в одну сторону
    loop = starting_edge.link_loops[0]

    faces_in_loop_one_direction, loops_one_direction, was_cycled_loop = loop_go(loop, False)
    faces_in_loop.extend(faces_in_loop_one_direction)
    loops.extend(loops_one_direction)
    change_direction_face = len(faces_in_loop) - 1
    if (was_cycled_loop):
        return (faces_in_loop, loops, -1)
    #обход в другую сторону, если не было цикла
    loop = starting_edge.link_loops[0].link_loop_next.link_loop_next
    faces_in_loop_two_direction, loops_two_direction, was_cycled_loop = loop_go(loop, True)
    faces_in_loop.extend(faces_in_loop_two_direction)
    loops.extend(loops_two_direction)
    return (faces_in_loop, loops, change_direction_face)

# TODO: здесь используются баговые признаки обрыва меша и цикла, см loop_go_..._quads
def loop_go(starting_loop: BMLoop, is_second_go: bool) -> (List[BMFace], List[BMLoop], bool):
    '''
    Функция обхода face loop (можно переделать в edge ring), начиная с первого ребра для edge ring
    Работает только для квадов, попав на не квад - останавливается
    Возвращает список всех граней, вошедших в face loop при обходе в данном направлении
    is_second_go нужен, чтобы при обходе в обратную сторону не добавлять первую грань еще раз в список
    '''
    faces_in_loop = []
    loops = []
    loop = starting_loop
    #loop.edge.select = True
    
    # ??????????????????????????? мб проблема с направлениями, мб надо судя именно face подавать чтобы было точнее, а не ребро!
    # вряд ли
    if (not is_quad(loop.face)):
        return [], [], False
    #
    if (not is_second_go):
        faces_in_loop.append(loop.face)
        loops.append(loop)
    
    radial_loop = loop.link_loop_radial_next
    # проверяем, что mesh оборвался (плоская поверхность)
    if (radial_loop.face == loop.face):
        return faces_in_loop, loops, False
    # проверяем, следующая грань это квада? 
    is_next_face_quad = is_quad(radial_loop.face)
    if (not is_next_face_quad):
        # уперлись в не квадратную грань, конец обхода
        return faces_in_loop, loops, False
    else:
        faces_in_loop.append(radial_loop.face)
        if (is_second_go):
            loops.append(radial_loop)
        else:
            loops.append(radial_loop.link_loop_next.link_loop_next)
    next_loop = radial_loop.link_loop_next.link_loop_next
#    next_loop.edge.select = True
    
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
            return faces_in_loop, loops, False
        # проверяем, следующая грань это квада? 
        is_next_face_quad = is_quad(radial_loop.face)
        # next_face_orto_loop.face.select = is_quad(next_face_orto_loop.face)
        if (not is_next_face_quad):
            return faces_in_loop, loops, False
        else:
            faces_in_loop.append(radial_loop.face)
            if (is_second_go):
                loops.append(radial_loop)
            else:
                loops.append(radial_loop.link_loop_next.link_loop_next)

 #       next_loop.edge.select = True
        loop = next_loop
    return faces_in_loop, loops, True

def collect_face_loop_with_recording_visited_not_quads(starting_edge: BMEdge) -> (List[BMFace], List[BMLoop], int, List[BMFace]):
    '''
    Функция обхода face loop (можно переделать в edge ring), начиная с первого ребра для edge ring
    Работает только для квадов, попав на не квад/конец меша - меняет направление, попав снова - останавливается
    Сначала идет только в одном направлении, затем в другую
    Возвращает список всех граней, вошедших в face loop, и номер грани, с которой начался обход в другую сторону 
    Если петля зациклена, возвращает -1 (надо соединить последнюю вершину с первой при создании кривой)
    '''
    visited_not_quads = []
    faces_in_loop = []
    loops = []
    #обход в одну сторону
    loop = starting_edge.link_loops[0]
    print("inside collect_loop loop: " + str(loop.index))
    print("start edge link loops: " + str([loop.index for loop in starting_edge.link_loops]))

    faces_in_loop_one_direction, loops_one_direction, was_cycled_loop, visited_not_quads_one = loop_go_with_recording_visited_not_quads(loop, False)
    faces_in_loop.extend(faces_in_loop_one_direction)
    loops.extend(loops_one_direction)
    visited_not_quads.extend(visited_not_quads_one)
    change_direction_face = len(faces_in_loop) - 1
    if (was_cycled_loop):
        return (faces_in_loop, loops, -1, visited_not_quads)
    #обход в другую сторону, если не было цикла
    loop = starting_edge.link_loops[0].link_loop_next.link_loop_next
    faces_in_loop_two_direction, loops_two_direction, was_cycled_loop, visited_not_quads_two = loop_go_with_recording_visited_not_quads(loop, True)
    faces_in_loop.extend(faces_in_loop_two_direction)
    loops.extend(loops_two_direction)
    visited_not_quads.extend(visited_not_quads_two)
    return (faces_in_loop, loops, change_direction_face, visited_not_quads)

def loop_go_with_recording_visited_not_quads(starting_loop: BMLoop, is_second_go: bool) -> (List[BMFace], List[BMLoop], bool, List[BMFace]):
    '''
    Функция обхода face loop (можно переделать в edge ring), начиная с первого ребра для edge ring
    Работает только для квадов, попав на не квад - останавливается
    Возвращает список всех граней, вошедших в face loop при обходе в данном направлении
    is_second_go нужен, чтобы при обходе в обратную сторону не добавлять первую грань еще раз в список
    '''
    visited_not_quads = []
    faces_in_loop = []
    loops = []
    loop = starting_loop
    #loop.edge.select = True
    
    # ??????????????????????????? мб проблема с направлениями, мб надо судя именно face подавать чтобы было точнее, а не ребро!
    # вряд ли
    if (not is_quad(loop.face)):
        if (not is_second_go):
            visited_not_quads.append(loop.face)
        return [], [], False, visited_not_quads
    #
    if (not is_second_go):
        faces_in_loop.append(loop.face)
        loops.append(loop)
    
    radial_loop = loop.link_loop_radial_next
    
    # проверяем, что mesh оборвался (плоская поверхность)
    #if (radial_loop.face == loop.face):
    #    return faces_in_loop, loops, False, visited_not_quads
    
    # проверяем, что mesh оборвался (плоская поверхность)
    # проверка основана на том, что у грани с обрывом на внешнем ребре только 1 link_loops
    if (radial_loop == loop):
        return faces_in_loop, loops, False, visited_not_quads
    
    # проверяем, следующая грань это квада? 
    is_next_face_quad = is_quad(radial_loop.face)
    if (not is_next_face_quad):
        visited_not_quads.append(radial_loop.face)
        # уперлись в не квадратную грань, конец обхода
        return faces_in_loop, loops, False, visited_not_quads
    else:
        faces_in_loop.append(radial_loop.face)
        if (is_second_go):
            loops.append(radial_loop)
        else:
            loops.append(radial_loop.link_loop_next.link_loop_next)
    next_loop = radial_loop.link_loop_next.link_loop_next
#    next_loop.edge.select = True
    
    # цикл прыжков для сбора всей лупы пока не упремся в не кваду или не вернемся в начальную (замкнутая лупа)
    # или не закончится плоский меш
    
    loop = next_loop
    while next_loop.edge != starting_loop.edge:
        radial_loop = loop.link_loop_radial_next
        next_loop = radial_loop.link_loop_next.link_loop_next
        
        # циклический меш
        #if (next_loop.edge == starting_loop.edge):
         #   break
        if (next_loop == starting_loop):
            break

        # проверяем, что mesh оборвался (плоская поверхность)
        # проверка основана на том, что у грани с обрывом на внешнем ребре только 1 link_loops
        if (radial_loop == loop):
            return faces_in_loop, loops, False, visited_not_quads
        
        # проверяем, следующая грань это квада? 
        is_next_face_quad = is_quad(radial_loop.face)
        # next_face_orto_loop.face.select = is_quad(next_face_orto_loop.face)
        if (not is_next_face_quad):
            visited_not_quads.append(radial_loop.face)
            return faces_in_loop, loops, False, visited_not_quads
        else:
            faces_in_loop.append(radial_loop.face)
            if (is_second_go):
                loops.append(radial_loop)
            else:
                loops.append(radial_loop.link_loop_next.link_loop_next)

 #       next_loop.edge.select = True
        loop = next_loop
    return faces_in_loop, loops, True, visited_not_quads
   
# Версия функции loop_go_with_recording_visited_not_quads
# останавливает сбор если встречает посещенную грань
# TODO: по идее, проблем с цикличьностью и проверкой на посещенность не будет, ведь сверяем посещенность по visited_faces_id, а туда посещенные вершины записываются
# во внешней функции, а не тут же
def loop_go_with_recording_visited_not_quads_nocross(starting_loop: BMLoop, is_second_go: bool, visited_faces_id: Set[int]) -> (List[BMFace], List[BMLoop], bool, List[BMFace]):
    '''
    Функция обхода face loop (можно переделать в edge ring), начиная с первого ребра для edge ring
    Работает только для квадов, попав на не квад - останавливается
    Возвращает список всех граней, вошедших в face loop при обходе в данном направлении
    is_second_go нужен, чтобы при обходе в обратную сторону не добавлять первую грань еще раз в список
    bool в возврате - это флаг того, цикличная дання петля или нет (то есть вернемся ли мы при обходе петли в ту грань, с которой обход начался)
    visited_faces_id - уже известные до вызова этой функции грани, посещенные на других обходах
    '''
    visited_not_quads = []
    faces_in_loop = []
    loops = []
    loop = starting_loop
    #loop.edge.select = True
    
    if (not is_quad(loop.face)):
        if (not is_second_go):
            visited_not_quads.append(loop.face)
        return [], [], False, visited_not_quads
    # если это первый проход:
    if (not is_second_go):
        # если стартовая грань уже посещена - закончить обход
        if (loop.face.index in visited_faces_id):
            return [], [], False, visited_not_quads
        faces_in_loop.append(loop.face)
        loops.append(loop)
    
    radial_loop = loop.link_loop_radial_next
    
    # проверяем, что mesh оборвался (плоская поверхность)
    #if (radial_loop.face == loop.face):
    #    return faces_in_loop, loops, False, visited_not_quads
    # проверяем, что mesh оборвался (плоская поверхность)
    # проверка основана на том, что у грани с обрывом на внешнем ребре только 1 link_loops
    if (radial_loop == loop):
        return faces_in_loop, loops, False, visited_not_quads

    # проверяем, следующая грань это квада? 
    is_next_face_quad = is_quad(radial_loop.face)
    if (not is_next_face_quad):
        visited_not_quads.append(radial_loop.face)
        # уперлись в не квадратную грань, конец обхода
        return faces_in_loop, loops, False, visited_not_quads
    else:
        # если следующая грань уже посещена - закончить обход
        if (radial_loop.face.index in visited_faces_id):
            return faces_in_loop, loops, False, visited_not_quads
        # следующая грань не посещена, добавляем ее в инфу
        faces_in_loop.append(radial_loop.face)
        if (is_second_go):
            loops.append(radial_loop)
        else:
            loops.append(radial_loop.link_loop_next.link_loop_next)
    next_loop = radial_loop.link_loop_next.link_loop_next
#    next_loop.edge.select = True
    
    # цикл прыжков для сбора всей лупы пока не упремся в не кваду или не вернемся в начальную (замкнутая лупа)
    # или не закончится плоский меш
    
    loop = next_loop
    while next_loop.edge != starting_loop.edge:
        radial_loop = loop.link_loop_radial_next
        next_loop = radial_loop.link_loop_next.link_loop_next
        
        # циклический меш
        #if (next_loop.edge == starting_loop.edge):
        #    break

        # проверяем, что mesh оборвался (плоская поверхность)
        #if (radial_loop.face == loop.face):
         #   return faces_in_loop, loops, False, visited_not_quads
        
        # циклический меш
        if (next_loop == starting_loop):
            break

        # проверяем, что mesh оборвался (плоская поверхность)
        # проверка основана на том, что у грани с обрывом на внешнем ребре только 1 link_loops
        if (radial_loop == loop):
            return faces_in_loop, loops, False, visited_not_quads
        
        # проверяем, следующая грань это квада? 
        is_next_face_quad = is_quad(radial_loop.face)
        # next_face_orto_loop.face.select = is_quad(next_face_orto_loop.face)
        if (not is_next_face_quad):
            visited_not_quads.append(radial_loop.face)
            return faces_in_loop, loops, False, visited_not_quads
        else:
             # если следующая грань уже посещена - закончить обход
            if (radial_loop.face.index in visited_faces_id):
                return faces_in_loop, loops, False, visited_not_quads
            faces_in_loop.append(radial_loop.face)
            if (is_second_go):
                loops.append(radial_loop)
            else:
                loops.append(radial_loop.link_loop_next.link_loop_next)

 #       next_loop.edge.select = True
        loop = next_loop
    return faces_in_loop, loops, True, visited_not_quads

# Версия функции collect_face_loop_with_recording_visited_not_quads
# останавливает сбор если встречает посещенную грань
# может вернуть недействительный change_direction_face, если обход вызван из обойденной грани
def collect_face_loop_with_recording_visited_not_quads_nocross(starting_edge: BMEdge, visited_faces_id: Set[int]) -> (List[BMFace], List[BMLoop], int, List[BMFace]):
    '''
    Функция обхода face loop (можно переделать в edge ring), начиная с первого ребра для edge ring
    Работает только для квадов, попав на не квад/конец меша - меняет направление, попав снова - останавливается
    Сначала идет только в одном направлении, затем в другую
    Возвращает список всех граней, вошедших в face loop, и номер грани, с которой начался обход в другую сторону 
    Если петля зациклена, возвращает -1 (надо соединить последнюю вершину с первой при создании кривой)
    visited_faces_id - уже известные до вызова этой функции грани, посещенные на других обходах
    '''
    visited_not_quads = []
    faces_in_loop = []
    loops = []
    #обход в одну сторону
    loop = starting_edge.link_loops[0]

    faces_in_loop_one_direction, loops_one_direction, was_cycled_loop, visited_not_quads_one = loop_go_with_recording_visited_not_quads_nocross(loop, False, visited_faces_id)
    faces_in_loop.extend(faces_in_loop_one_direction)
    loops.extend(loops_one_direction)
    visited_not_quads.extend(visited_not_quads_one)
    change_direction_face = len(faces_in_loop) - 1
    if (was_cycled_loop):
        return (faces_in_loop, loops, -1, visited_not_quads)
    #обход в другую сторону, если не было цикла
    loop = starting_edge.link_loops[0].link_loop_next.link_loop_next
    faces_in_loop_two_direction, loops_two_direction, was_cycled_loop, visited_not_quads_two = loop_go_with_recording_visited_not_quads_nocross(loop, True, visited_faces_id)
    faces_in_loop.extend(faces_in_loop_two_direction)
    loops.extend(loops_two_direction)
    visited_not_quads.extend(visited_not_quads_two)
    return (faces_in_loop, loops, change_direction_face, visited_not_quads)

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
def make_new_obj_with_empty_mesh_with_unique_name_in_scene(mesh_name: str) -> Object:
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

################################



# допустим, пользователь сам выбирает начальную петлю (ребром конечно же), вдоль которой будет происходить сбор петель
# эта версия просто идет вдоль петли и собирает для нее результаты вызова collect_face_loop от её поперечных петель
def loops_for_loop_by_edge(start_edge: BMEdge, visited_faces_id: Set[int]) -> List[Tuple[List[BMFace], List[BMLoop], int]]:
    '''
    идти вдоль лупы, содержащей данную start_edge и собирает все принадлежащие ей
    перпендикулярные лупы
    изменяет множество visited_faces_id
    TODO: сразу же обрабатывать лупу или возвращать всё накопленное?
    '''
    
#    loop = start_edge.link_loops[0]
    result = []

    faces_in_loop, edge_ring, idx_change_dir, visited_not_quads = collect_face_loop_with_recording_visited_not_quads(start_edge)
    for notquad in visited_not_quads:
        visited_faces_id.add(notquad.index)
    for loop in edge_ring:
        # выбор перпендикулярного ребра
        edge = loop.link_loop_next.edge
        print("start loop: " + str(loop.link_loop_next.index))
        faces_in_loop_inner, edge_ring_inner, idx_change_dir_inner, visited_not_quads_inner = collect_face_loop_with_recording_visited_not_quads(edge)
        for face in faces_in_loop_inner:
            visited_faces_id.add(face.index)
        for notquad in visited_not_quads_inner:
            visited_faces_id.add(notquad.index)
        result.append((faces_in_loop_inner, edge_ring_inner, idx_change_dir_inner))
    
    return result


# версия loops_for_loop_by_edge, в которой обход петли останавливается при встрече с обойденной петлей
def loops_for_loop_by_edge_nocross(start_edge: BMEdge, visited_faces_id: Set[int]) -> List[Tuple[List[BMFace], List[BMLoop], int]]:
    '''
    идти вдоль лупы, содержащей данную start_edge и собирает все принадлежащие ей
    перпендикулярные лупы
    изменяет множество visited_faces_id
    TODO: сразу же обрабатывать лупу или возвращать всё накопленное?
    '''
    
#    loop = start_edge.link_loops[0]
    result = []

    # прошли по стартовой петле
    faces_in_loop, edge_ring, idx_change_dir, visited_not_quads = collect_face_loop_with_recording_visited_not_quads_nocross(start_edge, visited_faces_id)
    for notquad in visited_not_quads:
        visited_faces_id.add(notquad.index)
    # обходим перпендикулярные
    for loop in edge_ring:
        # выбор перпендикулярного ребра
        edge = loop.link_loop_next.edge
        faces_in_loop_inner, edge_ring_inner, idx_change_dir_inner, visited_not_quads_inner = collect_face_loop_with_recording_visited_not_quads_nocross(edge, visited_faces_id)
        for face in faces_in_loop_inner:
            visited_faces_id.add(face.index)
        for notquad in visited_not_quads_inner:
            visited_faces_id.add(notquad.index)
        result.append((faces_in_loop_inner, edge_ring_inner, idx_change_dir_inner))
    
    return result

################################

def add_verts_to_bmesh(bm: BMesh, vertices: List[Vector]) -> None:
    '''
    функция добавляет точки в bm
    '''
    idx_start = len(bm.verts)
    for v in vertices:
        bm.verts.new(v)
    bm.verts.ensure_lookup_table()

    for i in range(idx_start, idx_start + len(vertices)):
        bm.verts[i].index = i
    
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

#nextnextnext.vert == nextnextradial.vert
#предполагаются что на вход даны две однонаправленные лупы из одинаковых положений в грани и обе принадлежат квадам ПОСЛЕДОВАТЕЛЬНЫМ
#TODO: функция ЖЕСТКО зависит от внутренностей функции collect_face_loop, изменение порядка обхода там приведет к поломке здесь
def is_loops_connective_in_uv(uv_layer: BMLayerItem, loop1: BMLoop, loop2: BMLoop, is_after_change_dir: bool) -> bool:
    '''
    Функция проверятет, являются ли две данные loop, принадлежащие последовательным граням 3D модели, связными в uv координатах
    '''
    if (is_after_change_dir): # после смены направления loop2 = loop1.next.next.radial
        loop1_next_next_next = loop1.link_loop_next.link_loop_next.link_loop_next
        return (loop2[uv_layer].uv == loop1_next_next_next[uv_layer].uv)
    else: # до смены направления loop2 = loop1.radial.next.next
        loop2_next_next_next = loop2.link_loop_next.link_loop_next.link_loop_next
        return (loop2_next_next_next[uv_layer].uv == loop1[uv_layer].uv)

# улучшение add_vertices_made_in_line, создает ребра только между точками, чьи грани связны в UV развертке.
# для этого принимает вместо с uv координатами точек их оригинальные loop
# TODO: не учитывает возникновение одиночных вершин на острове...
def add_vertices_made_in_line_with_island_connectivity(bm: BMesh, vertices: List[Vector], loops: List[BMLoop], idx_change_dir: int, uv_layer: BMLayerItem) -> None:
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
    count_edges = 0
    if (idx_change_dir == -1):
        for i in range(0, len(bm_verts_new) - 1):
            if (is_loops_connective_in_uv(uv_layer, loops[i], loops[i + 1], False)):
                count_edges += 1
                bm.edges.new((bm_verts_new[i], bm_verts_new[i + 1]))
        if (is_loops_connective_in_uv(uv_layer, loops[0], loops[-1], False)):
            count_edges += 1
            bm.edges.new((bm_verts_new[0], bm_verts_new[-1]))
    else: # создание не зацикленной кривой
        # добавление последовательных ребер в первом направлении
        for i in range(0, idx_change_dir):
            if (is_loops_connective_in_uv(uv_layer, loops[i], loops[i + 1], False)):
                count_edges += 1
                bm.edges.new((bm_verts_new[i], bm_verts_new[i + 1]))
        # добавление последовательных ребер в обратном направлении
        v_start = bm_verts_new[0] # вершина с грани, с которой начинался обход петли
        loop_start = loops[0]
        for i in range(idx_change_dir + 1, len(bm_verts_new)):
            if (is_loops_connective_in_uv(uv_layer, loop_start, loops[i], True)):
                count_edges += 1
                bm.edges.new((v_start, bm_verts_new[i]))
            v_start = bm_verts_new[i]
            loop_start = loops[i]

    # обновление индексов вершин и ребер [так сказано в документации]
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    for i in range(idx_start_vert, idx_start_vert + len(vertices)):
        bm.verts[i].index = i
    for i in range(idx_start_edge, idx_start_edge + count_edges):
        bm.edges[i].index = i

def add_vertices_made_in_line_with_delta_z(bm: BMesh, vertices: List[Vector], idx_change_dir: int, delta_z: float) -> None:
    '''
    Обертка над add_vertices_made_in_line
    Принимает на вход список 2D точек (!!!!) и сдвиг по z = delta_z, вставляет его в качества z-координаты всем точкам,
    превращая их в 3d точки на одной высоте

    Предназначена для добавления в объект созданной цепи точек, созданной из заданных точек (как и add_vertices_made_in_line)
    '''
    add_vertices_made_in_line(bm, [Vector([v[0], v[1], delta_z]) for v in vertices], idx_change_dir)

# улучшение функции add_vertices_made_in_line_with_delta_z, строит цепь с учетом того, связаны ли
# последовательные на 3D модели грани в UV развертке.
# TODO: не учитывает возникновение одиночных вершин на острове...
def add_vertices_made_in_line_with_delta_z_and_iscland_connectivity(bm: BMesh, vertices: List[Vector], loops: List[BMLoop], idx_change_dir: int, delta_z: float, uv_layer: BMLayerItem) -> None:
    add_vertices_made_in_line_with_island_connectivity(bm, [Vector([v[0], v[1], delta_z]) for v in vertices], loops, idx_change_dir, uv_layer)

################################

# em - edit mode
def get_uv_of_mesh_face_center_em(face: BMFace, uv_layer: BMLayerItem) -> Vector:
    '''
    функция для данной грани(не в UV) ищет координаты ее центра уже в UV
    возвращает 2D вектор
    Соотносится с ой UVMap, которая получается с помощью GeoNodes (развертка).
    TODO: будет ли соотноситься с холстом, который создается GeoNodes curve painter?
    '''
    loops = face.loops
    sum_1 = sum_2 = 0
    
    for loop in loops:
        uv = loop[uv_layer].uv
        #print(type(uv), uv[0], uv[1])
        sum_1 += uv[0]
        sum_2 += uv[1]
    return Vector([sum_1 / len(loops), sum_2 / len(loops)])

# em - edit mode
def get_uv_vertices_from_faces_em(faces: List[BMFace], bm: BMesh) -> List[Vector]:
    '''
    функция отображает каждую грань в UV и находит там её центр
    возвращает координаты всех центров в UV
    '''
    uv_layer = bm.loops.layers.uv.verify()
    
    vertices = []
    for face in faces:
        vertices.append(get_uv_of_mesh_face_center_em(face, uv_layer))
    return vertices

# em - edit mode
# функция, которую предполагается вызывать для результатов, полученных из функции collect_face_loop
def process_faces_from_loop_em(faces: List[BMFace], idx_change_dir: int, delta_z: float, mesh_to_project: BMesh, strokes_bm: BMesh):
    '''
    Эта функция принимает на вход список граней (объекта mesh_to_project), входящих в петлю,
    находит их центры в UV координатах,
    создает из них цепь и добавляет в объект-накопитель-штрихов strokemesh_bm
    '''
    # проецируем грани на UV и получаем их центры в UV координатах
    uv_centers_of_loop_faces = get_uv_vertices_from_faces_em(faces, mesh_to_project)

    print("uv centers count: ", len(uv_centers_of_loop_faces), " points: ", len(faces), " delta z: ", delta_z)

    # строим цепь из центров, соединенных ребрами
    add_vertices_made_in_line_with_delta_z(strokes_bm, uv_centers_of_loop_faces, idx_change_dir, delta_z)

# em - edit mode
# функция, которую предполагается вызывать для результатов, полученных из функции collect_face_loop
def process_faces_from_loop_with_island_connectivity_em(faces: List[BMFace], idx_change_dir: int, delta_z: float, mesh_to_project: BMesh, strokes_bm: BMesh, loops: List[BMLoop]):
    '''
    Эта функция принимает на вход список граней (объекта mesh_to_project), входящих в петлю,
    находит их центры в UV координатах,
    создает из них цепь и добавляет в объект-накопитель-штрихов strokemesh_bm
    '''
    # проецируем грани на UV и получаем их центры в UV координатах
    uv_centers_of_loop_faces = get_uv_vertices_from_faces_em(faces, mesh_to_project)
    
    uv_layer = mesh_to_project.loops.layers.uv.verify()

    print("uv centers count: ", len(uv_centers_of_loop_faces), " points: ", len(faces), " delta z: ", delta_z)

    # строим цепь из центров, соединенных ребрами
    add_vertices_made_in_line_with_delta_z_and_iscland_connectivity(strokes_bm, uv_centers_of_loop_faces, loops, idx_change_dir, delta_z, uv_layer)

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


#def main_process():


def output_not_visited_faces(bmesh, visited_faces_id):
    '''
    Функция для вывода на экран списка и количества непосещенных граней
    '''
    not_visited = []
    for face in bmesh.faces:
        if face.index not in visited_faces_id:
            not_visited.append(face.index)
    print("Visited faces: " + str(len(visited_faces_id)) + "/" + str(len(bmesh.faces)))
    print("Not visited faces: " + str(len(not_visited)) + " " + str(not_visited))


def main():
    
    #--- EDIT MODE!
    mesh_obj = bpy.context.active_object
    bm = bmesh.from_edit_mesh(mesh_obj.data)
    
    # создаем объект, меш, привязываем к коллекции, все пустое.
    # это - будущий накопитель для кривых-петель-штрихов.
    name = "StrokesMesh"
    strokes_obj = make_new_obj_with_empty_mesh_with_unique_name_in_scene(name)
    strokes_mesh = strokes_obj.data
    # создает bmesh для него чтобы можно было добавлять точки.
    strokes_bm = bmesh.new()
    strokes_bm.from_mesh(strokes_mesh)

    # определяемся, с чего начинать. Если есть выбранная - с выбранной, иначе - с некой 0-ой
    # TODO: переделать на face?
    selected_edges = [edge for edge in bm.edges if edge.select]
    
    if not selected_edges:
        starting_edge = bm.edges[0]
#        next_edge = bm.edges[10]
    else:
        starting_edge = selected_edges[0]
#        next_edge = selected_edges[1]
        
    # предположим, что выбрано ребро на квадратной грани, а то в итоге пустая лупа будет!        
        
    # просто обход 1 лупы без сбора перпендикулярных
#    (faces_in_loop, loops, change_direction_face) = collect_face_loop(starting_edge)
#    process_faces_from_loop_with_island_connectivity_em(faces_in_loop, change_direction_face, 0, bm, strokes_bm, loops)

#    (faces_in_loop, loops, change_direction_face) = collect_face_loop(next_edge)
#    process_faces_from_loop_with_island_connectivity_em(faces_in_loop, change_direction_face, 0.1, bm, strokes_bm, loops)

    # обход 1 лупы со сбором перпендикулярных
    visited_faces_id = set()

    # обычный обход
    result = loops_for_loop_by_edge(starting_edge, visited_faces_id)
    # обход с остановкой на посещенных гранях
    #result = loops_for_loop_by_edge_nocross(starting_edge, visited_faces_id)
    for idx, item in enumerate(result):
        (faces_in_loop, loops, change_direction_face) = item
        process_faces_from_loop_with_island_connectivity_em(faces_in_loop, change_direction_face, 0.1*idx, bm, strokes_bm, loops)
    for id in visited_faces_id:
        bm.faces[id].select = True

    output_not_visited_faces(bm, visited_faces_id)

    # обновление объекта на экране
    bmesh.update_edit_mesh(mesh_obj.data)
    # обновление point cloud на экране
    strokes_bm.to_mesh(strokes_mesh)
    strokes_obj.data.update()

    # очистка памяти от bm
    bm.free()
    strokes_bm.free()

    #--- EDIT MODE
  #  bpy.ops.object.editmode_toggle()
  #  bpy.context.view_layer.update()
    
    # Конвертирование накопителя строк в кривую
  #  convert_mesh_to_curve_and_make_poly(strokes_obj, mesh_obj)    

if __name__ == "__main__":
    main()
    
# для дебага из vscode....
# может ломать результат в blender    
#main()
