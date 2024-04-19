
# alt+S to save changes in blender to have them there!
# to have changes from vs code in blender: click red button in text editor and resolve conflict

import bpy
import bmesh
from bmesh.types import BMEdge, BMFace, BMLoop, BMesh, BMLayerItem, BMVert
from bpy import context

from bpy.types import Mesh, Object, Collection

from mathutils import Vector
from typing import List, Set, Tuple

import random

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
def loop_go_with_recording_visited_not_quads_nocross(starting_loop: BMLoop, is_second_go: bool, visited_faces_id: Set[int], faces_first_go_id: Set[int] = []) -> (List[BMFace], List[BMLoop], bool, List[BMFace]):
    '''
    Функция обхода face loop (можно переделать в edge ring), начиная с первого ребра для edge ring
    Работает только для квадов, попав на не квад - останавливается
    Возвращает список всех граней, вошедших в face loop при обходе в данном направлении
    is_second_go нужен, чтобы при обходе в обратную сторону не добавлять первую грань еще раз в список
    bool в возврате - это флаг того, цикличная дання петля или нет (то есть вернемся ли мы при обходе петли в ту грань, с которой обход начался)
    visited_faces_id - уже известные до вызова этой функции грани, посещенные на других обходах
    faces_first_go_id - посещенные на обходе в другую сторону грани, которые еще не занесли в глобальные посещенные грани visited_faces_id
    '''
    visited_not_quads = []
    faces_in_loop = []
    faces_in_loop_id = set() # нужно для отслеживание самопересечений во время ЭТОГО обхода
    loops = []
    loop = starting_loop
    
    if (not is_quad(loop.face)):
        if (not is_second_go):
            visited_not_quads.append(loop.face)
        return [], [], False, visited_not_quads
    # если это первый проход:
    if (not is_second_go):
        # если стартовая грань уже посещена - закончить обход
        if (loop.face.index in visited_faces_id) or (loop.face.index in faces_first_go_id):
            return [], [], False, visited_not_quads
        faces_in_loop.append(loop.face)
        faces_in_loop_id.add(loop.face.index)
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
        # (посещена при обходе других петель / при обходе в другую сторону / при обходе в эту же строну)
        if (radial_loop.face.index in visited_faces_id) or (radial_loop.face.index in faces_first_go_id) or (radial_loop.face.index in faces_in_loop_id):
            return faces_in_loop, loops, False, visited_not_quads
        # следующая грань не посещена, добавляем ее в инфу
        faces_in_loop.append(radial_loop.face)
        faces_in_loop_id.add(radial_loop.face.index)
        if (is_second_go):
            loops.append(radial_loop)
        else:
            loops.append(radial_loop.link_loop_next.link_loop_next)
    next_loop = radial_loop.link_loop_next.link_loop_next
    
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
        if (not is_next_face_quad):
            visited_not_quads.append(radial_loop.face)
            return faces_in_loop, loops, False, visited_not_quads
        else:
             # если следующая грань уже посещена - закончить обход
             # (посещена при обходе других петель / при обходе в другую сторону / при обходе в эту же строну)
            if (radial_loop.face.index in visited_faces_id) or (radial_loop.face.index in faces_first_go_id) or (radial_loop.face.index in faces_in_loop_id):
                return faces_in_loop, loops, False, visited_not_quads
            faces_in_loop.append(radial_loop.face)
            faces_in_loop_id.add(radial_loop.face.index)
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
    faces_in_loop_two_direction, loops_two_direction, was_cycled_loop, visited_not_quads_two = loop_go_with_recording_visited_not_quads_nocross(loop, True, visited_faces_id, set([face.index for face in faces_in_loop_one_direction]))
    faces_in_loop.extend(faces_in_loop_two_direction)
    loops.extend(loops_two_direction)
    visited_not_quads.extend(visited_not_quads_two)
    return (faces_in_loop, loops, change_direction_face, visited_not_quads)

# Версия функции collect_face_loop_with_recording_visited_not_quads_nocross
# принимает на вход конкретную лупу, т. к. в той версии при получении ребра можно было оказаться не на той грани, на которой задумано
# останавливает сбор если встречает посещенную грань
# может вернуть недействительный change_direction_face, если обход вызван из обойденной грани
# 
def collect_face_loop_with_recording_visited_not_quads_nocross_concrete_loop(loop_start: BMLoop, visited_faces_id: Set[int]) -> (List[BMFace], List[BMLoop], int, List[BMFace]):
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
    loop = loop_start

    faces_in_loop_one_direction, loops_one_direction, was_cycled_loop, visited_not_quads_one = loop_go_with_recording_visited_not_quads_nocross(loop, False, visited_faces_id)
    faces_in_loop.extend(faces_in_loop_one_direction)
    loops.extend(loops_one_direction)
    visited_not_quads.extend(visited_not_quads_one)
    change_direction_face = len(faces_in_loop) - 1
    if (was_cycled_loop):
        return (faces_in_loop, loops, -1, visited_not_quads)
    #обход в другую сторону, если не было цикла
    loop = loop_start.link_loop_next.link_loop_next
    faces_in_loop_two_direction, loops_two_direction, was_cycled_loop, visited_not_quads_two = loop_go_with_recording_visited_not_quads_nocross(loop, True, visited_faces_id, set([face.index for face in faces_in_loop_one_direction]))
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
        #edge = loop.link_loop_next.edge
        #faces_in_loop_inner, edge_ring_inner, idx_change_dir_inner, visited_not_quads_inner = collect_face_loop_with_recording_visited_not_quads_nocross(edge, visited_faces_id)
        loop_start = loop.link_loop_next
        faces_in_loop_inner, edge_ring_inner, idx_change_dir_inner, visited_not_quads_inner = collect_face_loop_with_recording_visited_not_quads_nocross_concrete_loop(loop_start, visited_faces_id)
       
        for face in faces_in_loop_inner:
            visited_faces_id.add(face.index)
        for notquad in visited_not_quads_inner:
            visited_faces_id.add(notquad.index)
        result.append((faces_in_loop_inner, edge_ring_inner, idx_change_dir_inner))
    
    return result

# версия loops_for_loop_by_edge, в которой обход петли останавливается при встрече с обойденной петлей
# и всегда вызывает обход не по ребру, а по конкретной лупе!
# важно для авто-обхода
def loops_for_loop_by_edge_nocross_concrete_loop(start_loop: BMLoop, visited_faces_id: Set[int]) -> List[Tuple[List[BMFace], List[BMLoop], int]]:
    '''
    идти вдоль лупы, содержащей данную start_edge и собирает все принадлежащие ей
    перпендикулярные лупы
    изменяет множество visited_faces_id
    TODO: сразу же обрабатывать лупу или возвращать всё накопленное?
    '''
    
#    loop = start_edge.link_loops[0]
    result = []

    # прошли по стартовой петле
    faces_in_loop, edge_ring, idx_change_dir, visited_not_quads = collect_face_loop_with_recording_visited_not_quads_nocross_concrete_loop(start_loop, visited_faces_id)
    
    # запись не квадов в посещенные
    #for notquad in visited_not_quads:
    #    visited_faces_id.add(notquad.index)
    
    # обходим перпендикулярные
    for loop in edge_ring:

        # выбор перпендикулярного ребра
        #edge = loop.link_loop_next.edge
        #faces_in_loop_inner, edge_ring_inner, idx_change_dir_inner, visited_not_quads_inner = collect_face_loop_with_recording_visited_not_quads_nocross(edge, visited_faces_id)
        loop_start = loop.link_loop_next
        faces_in_loop_inner, edge_ring_inner, idx_change_dir_inner, visited_not_quads_inner = collect_face_loop_with_recording_visited_not_quads_nocross_concrete_loop(loop_start, visited_faces_id)
       
        for face in faces_in_loop_inner:
            visited_faces_id.add(face.index)
        # запись не квадов в посещенные
        #for notquad in visited_not_quads_inner:
        #    visited_faces_id.add(notquad.index)

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

    ### симметричный обход, кольцо из 1 грани => без луп (невозможно определить направление)
    if (len(loops) == 0):
        print("process uv: no loops for edges. Suppose to be symmetrical call")
        # обновление индексов вершин и ребер [так сказано в документации]
        bm.verts.ensure_lookup_table()
        for i in range(idx_start_vert, idx_start_vert + len(vertices)):
            bm.verts[i].index = i
        return
    ###

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

def strokes_nocross(name: str, index: int, z_coord: int, start_loop: BMLoop, bm: BMesh, visited_faces_id: set, Z_STEP: float, COL_NAME: str):
    '''
    Фнукция вызывает один сбор перпендикулярных ребер + построение отдельного strokemesh по собранным петлям
    Также производит очистку памяти и обновление strokemesh на экране
    !! Изменяет значение z_coord и index
    Возвращает индексы всех посещенных граней-квад

    name - базовое имя всех strokemesh
    index - номер меша
    z_coord - сдвиг по z для направляющих в strokemesh
    startloop - с какой лупы начинается обход
    bm - модель, для которой строится strokemesh
    '''
    # создаем объект, меш, привязываем к коллекции, все пустое.
    # это - будущий накопитель для кривых-петель-штрихов.
    strokes_obj = make_new_obj_with_empty_mesh_with_unique_name_in_scene(name + str(index), COL_NAME)
    index += 1
    strokes_mesh = strokes_obj.data
    # создает bmesh для него чтобы можно было добавлять точки.
    strokes_bm = bmesh.new()
    strokes_bm.from_mesh(strokes_mesh)

    # запуск от заданного ребра
    # TODO: здесь лупа для обхода выбирается случайно из 2 луп данного ребра!
    result = loops_for_loop_by_edge_nocross_concrete_loop(start_loop, visited_faces_id)
    for idx, item in enumerate(result):
        (faces_in_loop, loops, change_direction_face) = item
        process_faces_from_loop_with_island_connectivity_em(faces_in_loop, change_direction_face, Z_STEP*z_coord, bm, strokes_bm, loops)
        z_coord += 1
    #for id in visited_faces_id:
    #    bm.faces[id].select = True

    # TODO: это для дебага в основном
    for id in visited_faces_id:
        bm.faces[id].select = True

    # очистка памяти и обновление StrokeMesh на экране
    # обновление point cloud на экране
    strokes_bm.to_mesh(strokes_mesh)
    strokes_obj.data.update()
    strokes_bm.free()

    return visited_faces_id, index, z_coord

def choose_loop(not_visited_face_id: List[int], bm: BMesh):
    '''
    Функция выбора следующей стартовой лупы для автозаполнения
    Выбор из непосещенных граней
    Выбирается случайная грань и ее первая лупа в списке
    TODO: выбор ориентации по какому-то признаку
    '''

    #random_face_id = random.choice(not_visited_face_id)
    random_face_id = list(not_visited_face_id)[0]
    # TODO выбор ориентации по какому-то признаку?
    loop = bm.faces[random_face_id].loops[0]
    #edge = bm.faces[random_face_id].edges[0]
    return loop


def auto_strokes_nocross(bm: BMesh, start_loop: BMLoop, Z_STEP: float, COL_NAME: str, MESH_NAME_BASE: str, MESH_NAME_IDX_START: int, Z_COORD_START: int):
    '''
    Функция для построения направляющих по всему мешу
    Начинает с конкретного ребра, далее выбирает случайное ребро среди ребер непосещенных граней
    Запускает сбор перпендикулярных петель, пока не обойдет все вершины (учитываются только квады)
    В базовом случае предлагается в качестве start_loop передавать сюда start_edge.link_loops[0]
    Но может понадобиться более точнее управление
    '''
    
    # все грани меша = непосещенные
    not_visited_face_id = set() #set([face.index for face in bm.faces])
    # выкинуть не квады
    for face in bm.faces:
        if is_quad(face):
            not_visited_face_id.add(face.index)

    #count_not_visited_start = len(not_visited_face_id)

    index = MESH_NAME_IDX_START
    z_coord = Z_COORD_START
    name = MESH_NAME_BASE
    visited_faces_id = set()


   # print("index = " + str(index) + " not_visited: " + str(len(not_visited_face_id)) + "/" + str(count_not_visited_start) + " visited: " + str(len(visited_faces_id)))
   # print("not_visited_id: " + str(not_visited_face_id))


    (visited_faces_id, index, z_coord) = strokes_nocross(name, index, z_coord, start_loop, bm, visited_faces_id, Z_STEP, COL_NAME)
    not_visited_face_id = not_visited_face_id.difference(visited_faces_id)

   # print("index = " + str(index) + " not_visited: " + str(len(not_visited_face_id)) + "/" + str(count_not_visited_start) + " visited: " + str(len(visited_faces_id)))
   # print("not_visited_id: " + str(not_visited_face_id))


    # пока непосещенные не пусты:
    while len(not_visited_face_id) > 0:
    # выбрать из непосещенных граней одну, взять конкретную лупу / попросить ввести (?)
        loop_next = choose_loop(not_visited_face_id, bm)
    # запустить обход из нее
    # построить в отдельный strokemesh нужные вершины и цепь
        (visited_faces_id, index, z_coord) = strokes_nocross(name, index, z_coord, loop_next, bm, visited_faces_id, Z_STEP, COL_NAME)
    # обновить множество непосещенных граней
        not_visited_face_id = not_visited_face_id.difference(visited_faces_id)


    #    print("index = " + str(index) + " not_visited: " + str(len(not_visited_face_id)) + "/" + str(count_not_visited_start) + " visited: " + str(len(visited_faces_id)))
    #   print("not_visited_id: " + str(not_visited_face_id))

    # TODO
    # все stroke_obj надо будет потом превратить в кривые, но это либо уже после всего обхода,
    # либо на пошаговом вводе можно будет сделать эту операцию после каждого обхода           
    # -- на данный момент вовне есть функция обхода всех StrokeMesh_i по именам, конвертирующая их в кривые :)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 

    return index, name

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

def convert_to_curve_all_strokemesh(name: str, count: int, mesh_obj: Object):
    '''
    Функция, которая обходит все "StrokeMesh_i" str(name+count) и конвертирует в кривые
    '''
    #--- EDIT MODE TO OBJECT MODE
    bpy.ops.object.editmode_toggle()
    bpy.context.view_layer.update()
    
    current_obj = mesh_obj

    for index in range(0, count):
        # получить stroke obj по имени
        stroke_obj_next = bpy.data.objects[name + str(index)]
        # Конвертирование накопителя строк в кривую
        convert_mesh_to_curve_and_make_poly(stroke_obj_next, current_obj)
        # переключение на OBJECT MODE
        bpy.ops.object.editmode_toggle()
        bpy.context.view_layer.update()
        current_obj = stroke_obj_next

# вызов автозаполнения nocross c конвертацией в кривые
def test_auto_strokes_nocross(Z_STEP: float, COL_NAME: str, MESH_NAME_BASE: str, MESH_NAME_IDX_START: int, Z_COORD_START: int):
    #--- EDIT MODE!
    mesh_obj = bpy.context.active_object
    bm = bmesh.from_edit_mesh(mesh_obj.data)

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

    # автозаполнение базовое
    count, name = auto_strokes_nocross(bm, starting_edge.link_loops[0], Z_STEP, COL_NAME, MESH_NAME_BASE, MESH_NAME_IDX_START, Z_COORD_START) 

     # обновление объекта на экране
    bmesh.update_edit_mesh(mesh_obj.data)
    # очистка памяти от bm
    bm.free()

    convert_to_curve_all_strokemesh(name, count, mesh_obj)  

# вызов обхода одной петли без сбора перпендикуляров, nocross
def test_collect_loop_nocross(MESH_NAME_WITH_IDX: str, Z_STEP: float, COL_NAME: str, Z_COORD_START: int):
     #--- EDIT MODE!
    mesh_obj = bpy.context.active_object
    bm = bmesh.from_edit_mesh(mesh_obj.data)
    
    # создаем объект, меш, привязываем к коллекции, все пустое.
    # это - будущий накопитель для кривых-петель-штрихов.
    name = MESH_NAME_WITH_IDX
    strokes_obj = make_new_obj_with_empty_mesh_with_unique_name_in_scene(name, COL_NAME)
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
####################################
    # просто обход 1 лупы без сбора перпендикулярных

#    (faces_in_loop, loops, change_direction_face) = collect_face_loop(starting_edge)
#    process_faces_from_loop_with_island_connectivity_em(faces_in_loop, change_direction_face, 0, bm, strokes_bm, loops)

#    (faces_in_loop, loops, change_direction_face) = collect_face_loop(next_edge)
#    process_faces_from_loop_with_island_connectivity_em(faces_in_loop, change_direction_face, 0.1, bm, strokes_bm, loops)

#######################################

    # обход 1 лупы со сбором перпендикулярных
    visited_faces_id = set()

    # обычный обход
    #result = loops_for_loop_by_edge(starting_edge, visited_faces_id)
    # обход с остановкой на посещенных гранях
    (faces_in_loop, edge_ring, idx_change_dir, visited_not_quads) = collect_face_loop_with_recording_visited_not_quads_nocross(starting_edge, visited_faces_id)
    process_faces_from_loop_with_island_connectivity_em(faces_in_loop, idx_change_dir, Z_STEP * Z_COORD_START, bm, strokes_bm, edge_ring)
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

# вызов одного обхода со сбором перпендикуляров, без автозаполнения
def test_loops_for_loop_nocross(MESH_NAME_WITH_IDX: str, Z_STEP: float, COL_NAME: str, Z_COORD_START: int):
    
    #--- EDIT MODE!
    mesh_obj = bpy.context.active_object
    bm = bmesh.from_edit_mesh(mesh_obj.data)
    
    # создаем объект, меш, привязываем к коллекции, все пустое.
    # это - будущий накопитель для кривых-петель-штрихов.
    name = MESH_NAME_WITH_IDX
    strokes_obj = make_new_obj_with_empty_mesh_with_unique_name_in_scene(name, COL_NAME)
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
####################################
    # просто обход 1 лупы без сбора перпендикулярных

#    (faces_in_loop, loops, change_direction_face) = collect_face_loop(starting_edge)
#    process_faces_from_loop_with_island_connectivity_em(faces_in_loop, change_direction_face, 0, bm, strokes_bm, loops)

#    (faces_in_loop, loops, change_direction_face) = collect_face_loop(next_edge)
#    process_faces_from_loop_with_island_connectivity_em(faces_in_loop, change_direction_face, 0.1, bm, strokes_bm, loops)

#######################################

    # обход 1 лупы со сбором перпендикулярных
    visited_faces_id = set()

    # обычный обход
    #result = loops_for_loop_by_edge(starting_edge, visited_faces_id)
    # обход с остановкой на посещенных гранях
    result = loops_for_loop_by_edge_nocross(starting_edge, visited_faces_id)
    for idx, item in enumerate(result):
        (faces_in_loop, loops, change_direction_face) = item
        process_faces_from_loop_with_island_connectivity_em(faces_in_loop, change_direction_face, Z_STEP*Z_COORD_START, bm, strokes_bm, loops)
        Z_COORD_START += 1
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

def get_last_collection_index(col_name: str):
    '''
    Функция проверяет наличие папки с именем "<col_name>_<index>"
    и вовзращает самый большой index
    Если вернула -1, значит, папки отсутствуют
    '''
    max_index = -1
    for col in bpy.data.collections:
        if (col_name in col.name):
            current_index = int(col.name.split('_')[-1]) # номер идет последним
            if (current_index > max_index):
                max_index = current_index
    return max_index

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

def get_last_z_coord(last_mesh_name: str):
    '''
    Функция ищет в строкмеше last_mesh_name точку с максимальной координатой по z
    и вовзращает этот максимальный z
    Ожидается, что в last_mesh_name действительно будет самая высокая точка среди всех
    строкмешей.
    Чтобы вычислить следующую высоту, к данной высоте надо будет прибавить Z_STEP
    TODO: ввести Z_STEP. стоит сделать умножение или сложение??
    '''
    object: Object = bpy.data.objects[last_mesh_name]

    # если строкмеши не были конвертированы в кривые:
    if (object.type == "MESH"):
        stroke_bm = bmesh.new()
        stroke_bm.from_mesh(object.data)

        z_coords = [v.co[2] for v in stroke_bm.verts] # (z_coord) list
        z_coords.sort() # сортировка по координате
        return z_coords[-1] # возвращаем максимальную высоту по z
    # если строкмеши конвертированы в кривые
    curve = object.data
    max_z = -1

    # обычный способ найти максимальную по высоте точку: перебор всех сплайнов
    for spline in curve.splines:
        #current_z = spline.bezier_points[0].co[2]
        current_z = spline.points[0].co[2]
        if (current_z > max_z):
            max_z = current_z
    # можно сделать способ, полагающийся на то, что сплайны создаются так что у каждого следующего координата z больше предыдущего,
    # поэтому помжно просто взять самый первый сплайн и всё

    #v_id_and_z_coords = [(v.index, v.co[2]) for v in stroke_bm.verts] # (v_idx, z_coord) list of tuples
    #v_id_and_z_coords.sort(key=lambda a: a[1]) # сортировка по координате
    #return v_id_and_z_coords[-1][1] # возвращаем максимальную высоту

    #z_coords = [v.co[2] for v in stroke_bm.verts] # (z_coord) list
    #z_coords.sort() # сортировка по координате
    #return z_coords[-1] # возвращаем максимальную высоту по z

    return max_z

def test_getting_last_indexes():
    col_name = "TestCol_"
    last_col_id = get_last_collection_index(col_name)
    if (last_col_id == -1):
        print("No collections exist")
        return

    mesh_name = "StrokesMesh_"
    last_mesh_id = get_last_strokemesh_index(mesh_name, col_name + str(last_col_id))
    if (last_mesh_id == -1):
        print("No strokemeshes exist")
        return
    
    last_z = get_last_z_coord(mesh_name + str(last_mesh_id))

    print("last col: " + str(last_col_id) + " last mesh: " + str(last_mesh_id) + " last z: " + str(last_z))

# эта функция нужна для вызова автозаполнения на двух отдельных половинах симметричной модели
# в качестве стартового ребра нужно на обеих половинах выбрать симметричное ребро!!!
# при вызове не второй половине нужно расскоментировать строчку с нужной start_loop
# автозаполнение с симметрией
# !!! этот метод НЕ РАБОТАЕТ и не будет работать. 1) здесь контроль направления только при первом вызове 2) контролировать направление просто НЕЛЬЗЯ
# из-за его локальности и непредсказуемости (link_loop[0])
def test_auto_stroke_nocross_for_symmetry(Z_STEP: float, COL_NAME: str, MESH_NAME_BASE: str, MESH_NAME_IDX_START: int, Z_COORD_START: int):
    #--- EDIT MODE!
    mesh_obj = bpy.context.active_object
    bm = bmesh.from_edit_mesh(mesh_obj.data)

    # определяемся, с чего начинать. Если есть выбранная - с выбранной, иначе - с некой 0-ой
    selected_edges = [edge for edge in bm.edges if edge.select]
    
    if not selected_edges:
        starting_edge = bm.edges[0]
#        next_edge = bm.edges[10]
    else:
        starting_edge = selected_edges[0]
#        next_edge = selected_edges[1]
        
    # предположим, что выбрано ребро на квадратной грани, а то в итоге пустая лупа будет!  

    # выбор направления обхода: РАСКОММЕНТИРОВАТЬ НУЖНОЕ
    # --- при обходе первой половины
    start_loop = starting_edge.link_loops[0]
    # --- при обходе второй половины
    #start_loop = starting_edge.link_loops[0].link_loop_next.link_loop_next

    # автозаполнение базовое
    count, name = auto_strokes_nocross(bm, start_loop, Z_STEP, COL_NAME, MESH_NAME_BASE, MESH_NAME_IDX_START, Z_COORD_START) 

     # обновление объекта на экране
    bmesh.update_edit_mesh(mesh_obj.data)
    # очистка памяти от bm
    bm.free()

#    convert_to_curve_all_strokemesh(name, count, mesh_obj)

# симметрия со словарем по координате=ключу - НЕ РАБОЧИЙ МЕТОД
def make_symmetry_dictionary(bm: BMesh):
    symm_dict = {} # face_id1 : face_id2, face_id2 : face_id1
    
    #median_visited_set = set()
    
    median_dict = {} # median : face_id
    index_dict = {} # face_id: median

    idx = 1
    for face in bm.faces:
        median: Vector = face.calc_center_median()
        median.freeze()
        median_symm = Vector((-median.x, median.y, median.z))
        median_symm.freeze()
        #median_tuple = (median.x, median.y, median.z)
        #median_tuple = (round(median.x, 5), round(median.y, 5), round(median.z, 5))
        #median_tuple_symm = (-median.x, median.y, median.z)
        #median_tuple_symm = (round(-median.x, 5), round(median.y, 5), round(median.z, 5))

        #assert(median_tuple == (-median_tuple_symm[0], median_tuple_symm[1], median_tuple_symm[2]))
        assert(median == Vector((-median_symm.x, median_symm.y, median_symm.z)))
        #if (median_tuple_symm in symm_dict):
        #    symm_dict[median_tuple_symm] = m
        
        # просто помещаем вообще все медианы в словарь
        #assert(not(median_tuple in median_dict))
        #median_dict[median_tuple] = face.index
        median_dict[median] = face.index
        #index_dict[face.index] = median_tuple
        index_dict[face.index] = median
        # симметричная медиана уже есть в словаре
        #if (median_tuple_symm in median_dict):
        #    id1 = face.index
        #    id2 = median_dict[median_tuple_symm]
        #    symm_dict[id1] = id2
        #    symm_dict[id2] = id1
        if (median_symm in median_dict):
            id1 = face.index
            id2 = median_dict[median_symm]
            symm_dict[id1] = id2
            symm_dict[id2] = id1
        idx += 1
    #print("faces: " + str(idx -1 ))
    #for key in median_dict.keys():
    #    symm_key = (-key[0], key[1], key[2])
    #    id1 = median_dict[key]
    #    id2 = median_dict[symm_key]
    #    assert(median_dict[symm_key] in symm_dict)
    #    assert(median_dict[key] in symm_dict)
    for val in median_dict.values():
        if (val not in symm_dict):
            print(str(val) + " median: " + str(index_dict[val]))
    print("-----")
    for face in bm.faces:
        if (face.index not in symm_dict):
            print(str(face.index) + " median: " + str(face.calc_center_median()))
            bm.faces[face.index].select = True
    print("-----")
    return symm_dict

# преобразование вектора в строку для сортировки
def compare_vectors(tuple: Tuple[int, Vector]):
    return str(tuple[1].x) + str(tuple[1].y) + str(tuple[1].z)

# симметрия с сортировкой строк - НЕ РАБОЧИЙ МЕТОД
def make_symmetry_dictionary_2(bm: BMesh):
    symm_dict = {} # face_id1 : face_id2, face_id2 : face_id1
    
    #median_visited_set = set()
    
#    median_dict = {} # median : face_id
#    index_dict = {} # face_id: median

    id_median_list = []

    for face in bm.faces:
        median: Vector = face.calc_center_median()
        id_median_list.append((face.index, median))
    
    id_median_list_sorted = sorted(id_median_list, key=compare_vectors)

    median_127 = 0
    median_396 = 0
    median_414 = 0

    # теория: все точки в одной половине - одного знака, все точки в друго - другого знака (по х)
    # то есть ровно половина списка с отриц. х, ровно половина - с положительным
    id_half: int = len(bm.faces) // 2
    for idx in range(0, id_half):
        idx1 = id_median_list_sorted[idx][0]
        median1 = id_median_list_sorted[idx][1]
        idx2 = id_median_list_sorted[id_half + idx][0]
        median2 = id_median_list_sorted[id_half + idx][1]
        symm_dict[idx1] = idx2
        symm_dict[idx2] = idx1

        if (idx1 == 127):
            median_127 = median1
        if (idx1 == 396):
            median_396 = median1
        if (idx1 == 414):
            median_414 = median1
        if (idx2 == 127):
            median_127 = median2
        if (idx2 == 396):
            median_396 = median2
        if (idx2 == 414):
            median_414 = median2


    #for val in median_dict.values():
     #   if (val not in symm_dict):
     #       print(str(val) + " median: " + str(index_dict[val]))
    #print("-----")
    for face in bm.faces:
        if (face.index not in symm_dict):
            print(str(face.index) + " median: " + str(face.calc_center_median()))
            bm.faces[face.index].select = True
    print("-----")
    return symm_dict

#from math import sqrt 
import math
from decimal import Decimal
# расстояние между Decimal векторами, без квадратного корня
def distance_v(v1: Tuple[Decimal], v2: Tuple[Decimal]):
    x_comp: Decimal = (v1[0] - v2[0])*(v1[0] - v2[0])
    y_comp: Decimal = (v1[1] - v2[1])*(v1[1] - v2[1])
    z_comp: Decimal = (v1[2] - v2[2])*(v1[2] - v2[2])
    if not ((x_comp > Decimal(0))):
        print("problem")
    assert(x_comp > Decimal(0))
    assert(y_comp > Decimal(0))
    assert(z_comp > Decimal(0))
    return Decimal(x_comp + y_comp + z_comp)

# подсчет центра грани без деления, в decimal
def count_median(face: BMFace):
    x: Decimal = Decimal()
    y: Decimal = Decimal()
    z: Decimal = Decimal()
    for v in face.verts:
        x += Decimal(str(v.co.x))
        y += Decimal(str(v.co.y))
        z += Decimal(str(v.co.z))
    # нужно ли тут деление???
    count = len(face.verts)
    #return (Decimal(x/count), Decimal(y/count), Decimal(z/count))
    return (x, y, z)

# симметрия с Decimal вычислениями - НЕ РАБОЧИЙ МЕТОД
def make_symmetry_dictionary_3(bm: BMesh):
    symm_dict = {} # face_id1 : face_id2, face_id2 : face_id1

    #id_median_list = []
    id_median_x_positive = []
    id_median_x_negative = []
                                                                                 
    for face in bm.faces:
        #median: Vector = face.calc_center_median()
        median: Tuple[Decimal, Decimal, Decimal] = count_median(face)
        if (median[0] > 0):
            id_median_x_positive.append((face.index, median))
        else:
            id_median_x_negative.append((face.index, median))
    # надеюсь, что не будет проблем с близостью к нулю....
    assert(len(id_median_x_negative) == len(id_median_x_positive))

    for tuple1 in id_median_x_negative:
        (index1, median1) = tuple1
        #median_symm_expected1: Vector = Vector((-median1.x, median1.y, median1.z))
        median_symm_expected1: Tuple[Decimal, Decimal, Decimal] = (-median1[0], median1[1], median1[2])
        min_dist: Decimal = Decimal('Infinity')
        min_index = -1
        for tuple2 in id_median_x_positive:
            (index2, median2) = tuple2
            dist: Decimal = distance_v(median_symm_expected1, median2)
            if dist < min_dist:
                min_dist = dist
                min_index = index2
        assert(min_index >= 0)
        symm_dict[index1] = min_index
        symm_dict[min_index] = index1
    return symm_dict

# симметрия по близости ожидаемого центра грани и действительного центра грани
# ОГРАНИЧЕНИЯ:
# 1) O(n^2) от количества граней. Задумывается на модели ~10к граней
# 2) Не работает на слишком маленьких гранях
# 3) Только для моделей, симметричных по oX и расположенно центром в 0 по X
# 4) Только для ЗЕРКАЛЬНЫХ моделей: разрез по OX = линия, а не кольцо граней
# 5) Возможно, будет плохо работать на моделях с утолщением, рожками и других, где есть узкие расстояния между гранями
def make_symmetry_dictionary_by_median_similarity(bm: BMesh):
    '''
    Функция устанавливает соответствие между индексами симметричных граней
    Возвращает словарь (индекс грани : индекс симметричной грани)
    Ключей столько же, сколько граней ! не половина
    См. ограничения функции!!
    '''
    symm_dict = {} # face_id1 : face_id2, face_id2 : face_id1

    id_median_x_positive = []
    id_median_x_negative = []
                                                                                 
    for face in bm.faces:
        median: Vector = face.calc_center_median()
        if (median.x > 0):
            id_median_x_positive.append((face.index, median))
        else:
            id_median_x_negative.append((face.index, median))
    # надеюсь, что не будет проблем с близостью к нулю....
    assert(len(id_median_x_negative) == len(id_median_x_positive))

    for tuple1 in id_median_x_negative:
        (index1, median1) = tuple1
        median_symm_expected1: Vector = Vector((-median1.x, median1.y, median1.z))

        min_index = -1
        for tuple2 in id_median_x_positive:
            (index2, median2) = tuple2
            # ПАРАМЕТР ТОЧНОСТИ
            rel_tol = 1e-4
            x_close = math.isclose(median_symm_expected1.x, median2.x, rel_tol=rel_tol)
            y_close = math.isclose(median_symm_expected1.y, median2.y, rel_tol=rel_tol)
            z_close = math.isclose(median_symm_expected1.z, median2.z, rel_tol=rel_tol)
            if x_close and y_close and z_close:
                min_index = index2
                break
        #if (min_index < 0):
        #    print("problem")
        assert(min_index >= 0)
        symm_dict[index1] = min_index
        symm_dict[min_index] = index1
    return symm_dict

# симметрия по ray_cast - НЕ РАБОЧИЙ МЕТОД
# непонятно, как пускать луч, если в качестве результата только 1 пересечение
def make_symmetry_dictionary_by_x(bm: BMesh, mesh_obj: Object):
    symm_dict = {} # face_id1 : face_id2, face_id2 : face_id1

    #id_median_list = []
    id_median_x_positive = []
    id_median_x_negative = []
                                                                                 
    for face in bm.faces:
        median: Vector = face.calc_center_median()
        if (median.x > 0):
            id_median_x_positive.append((face.index, median))
        else:
            id_median_x_negative.append((face.index, median))
    # надеюсь, что не будет проблем с близостью к нулю....
    assert(len(id_median_x_negative) == len(id_median_x_positive))

    # настраиваемый параметр TODO который надо подбирать для модели
    y_distance = -10
    ray_dictance = 20
    for (index1, median1) in id_median_positive:
        median_expected = Vector((-median1.x, median1.y, median1.z))
        ray_cast_position = Vector((median_expected.x, y_distance, median_expected.z))
        result = mesh_obj.ray_cast(ray_cast_position, median_expected, ray_dictance)


def make_symmetrical_face_list(faces_in_ring: List[BMFace], bm: BMesh, symm_dict: dict):
    '''
    Эта функция получает на вход список граней и возвращает список симметричных им граней
    TODO Можно переделать на чисто списки id для эффективности?
    '''
    symm_face_ring = []
    for face in faces_in_ring:
        symm_face_id = symm_dict[face.index]
        symm_face_ring.append(bm.faces[symm_face_id])
    return symm_face_ring

def make_symmetrical_loop_list(symm_face_ring: List[BMFace], idx_change_dir: int, len_ring: int):
     # определить лупу можно по двум последовательным граням
    # а если грань в списке всего одна? тогда будет строиться точка. Для функции process_uv_... этого вполне хватит, пустой список.
    # loop нужны для проверки связности двух квад в uv развертке, а если у нас всего она квада, то это и не нужно.
    '''
    Эта функция получает на вход список луп и возвращает список симметричных луп
    Лупы получаются при обходе данного списка граней в данном порядке
    с помощью прыжков по общим ребрам и radial переходов
    loop (start) -> radial.next.next --- переход как в функции collect_..._nocross
    Для определения луп используется список симметричных граней
    Функция жестко зависит от устройства функции add_vertices_made_in_line_with_island_connectivity
    и от collect_..._nocross, изменение логики в этих функциях приведет к поломке данной функции!
    '''
    symm_loop_ring = []
    start_loop = get_start_loop_from_face_ring(symm_face_ring)
    if start_loop is None:
        return symm_loop_ring
    
    # зацикленное кольцо
    if (idx_change_dir == -1):
        loop = start_loop
        for i in range(0, len_ring):
            symm_loop_ring.append(loop)
            next_loop = loop.link_loop_radial_next.link_loop_next.link_loop_next
            loop = next_loop
        assert(len(symm_loop_ring) == len_ring)
        return symm_loop_ring


    # ход в одну сторону
    loop = start_loop
    for i in range(0, idx_change_dir + 1):
        symm_loop_ring.append(loop)
        next_loop = loop.link_loop_radial_next.link_loop_next.link_loop_next
        loop = next_loop
    
    # ход в обратную сторону
    loop = start_loop.link_loop_next.link_loop_next
    for i in range(idx_change_dir + 1, len_ring):
        symm_loop_ring.append(loop.link_loop_radial_next)
        next_loop = loop.link_loop_radial_next.link_loop_next.link_loop_next
        loop = next_loop
    
    assert(len(symm_loop_ring) == len_ring)
    return symm_loop_ring

def get_start_loop_from_face_ring(symm_face_ring: List[BMFace]):
    # определить лупу можно по двум последовательным граням
    # а если грань в списке всего одна? тогда будет строиться точка. Для функции process_uv_... этого вполне хватит, пустой список.
    # loop нужны для проверки связности двух квад в uv развертке, а если у нас всего она квада, то это и не нужно.
    '''
    Данная функция определяет стартовую лупу, позволяющую обойти данный список граней в данном порядке
    с помощью прыжков по общим ребрам и radial переходов
    loop (start) -> radial.next.next --- переход как в функции collect_..._nocross
    Функция жестко зависит от устройства функции add_vertices_made_in_line_with_island_connectivity
    и от collect_..._nocross, изменение логики в этих функциях приведет к поломке данной функции!
    '''
    if (len(symm_face_ring) < 2):
        return None
    face1 = symm_face_ring[0]
    face2 = symm_face_ring[1]
    start_edge: BMEdge | None = None
    for edge in face1.edges:
        if edge in face2.edges:
            start_edge = edge
            break
    start_loop = start_edge.link_loops[0]
    if (start_loop.face == face2):
        start_loop = start_edge.link_loops[1]
    assert(start_loop.face == face1)
    return start_loop

# вызывать для второй половины
def stroke_nocross_for_symmetry(list_orto_rings: List[Tuple[List[BMFace], List[BMLoop], int]], symm_dict: dict, bm: BMesh):
    symm_list_orto_rings: List[Tuple[List[BMFace], List[BMLoop], int]] = []
    for idx, item in enumerate(list_orto_rings):
        (faces_in_loop, loops, change_direction_face) = item
        symm_face_ring = make_symmetrical_face_list(faces_in_loop, bm, symm_dict)
        symm_loop_ring = make_symmetrical_loop_list(symm_face_ring, change_direction_face, len(loops))
        symm_list_orto_rings.append([symm_face_ring, symm_loop_ring, change_direction_face])
    return symm_list_orto_rings

def test_make_symmetry_dictionary():
    #--- EDIT MODE!
    mesh_obj = bpy.context.active_object
    bm = bmesh.from_edit_mesh(mesh_obj.data)

    selected_faces = [face for face in bm.faces if face.select]
    
    if not selected_faces:
        face = bm.faces[0]
    else:
        face = selected_faces[0]
    #count = len(bm.faces)
    symm_dict = make_symmetry_dictionary_by_median_similarity(bm)
    symm_face_id = symm_dict[face.index]
    bm.faces[symm_face_id].select = True

    # обновление объекта на экране
    bmesh.update_edit_mesh(mesh_obj.data)
    bm.free

def test_stroke_nocross_for_symmetry(MESH_NAME_BASE: str, MESH_INDEX: int, Z_STEP: float, COL_NAME: str, Z_COORD_START: int):
    # построение словаря
    # один вызов сбора перпендикуляров ИЗ ИЗОЛИРОВАННОЙ ОБЛАСТИ + вызов симметричного построения

    #--- EDIT MODE!
    mesh_obj = bpy.context.active_object
    bm = bmesh.from_edit_mesh(mesh_obj.data)
    
    # создаем объект, меш, привязываем к коллекции, все пустое.
    # это - будущий накопитель для кривых-петель-штрихов.
    name = MESH_NAME_BASE + str(MESH_INDEX)
    strokes_obj = make_new_obj_with_empty_mesh_with_unique_name_in_scene(name, COL_NAME)
    strokes_mesh = strokes_obj.data
    MESH_INDEX += 1
    # создает bmesh для него чтобы можно было добавлять точки.
    strokes_bm = bmesh.new()
    strokes_bm.from_mesh(strokes_mesh)

    selected_edges = [edge for edge in bm.edges if edge.select]
    
    if not selected_edges:
        starting_edge = bm.edges[0]
    else:
        starting_edge = selected_edges[0]
        
    visited_faces_id = set()

    # словарь симметрий
    symm_dict = make_symmetry_dictionary_by_median_similarity(bm)

    # обход с остановкой на посещенных гранях
    result = loops_for_loop_by_edge_nocross(starting_edge, visited_faces_id)
    for idx, item in enumerate(result):
        (faces_in_loop, loops, change_direction_face) = item
        process_faces_from_loop_with_island_connectivity_em(faces_in_loop, change_direction_face, Z_STEP*Z_COORD_START, bm, strokes_bm, loops)
        Z_COORD_START += 1
    for id in visited_faces_id:
        bm.faces[id].select = True

    # создаем объект, меш, привязываем к коллекции, все пустое.
    # это - будущий накопитель для кривых-петель-штрихов.
    name_symm = MESH_NAME_BASE + str(MESH_INDEX)
    strokes_obj_symm = make_new_obj_with_empty_mesh_with_unique_name_in_scene(name_symm, COL_NAME)
    strokes_mesh_symm = strokes_obj_symm.data
    MESH_INDEX += 1
    # создает bmesh для него чтобы можно было добавлять точки.
    strokes_bm_symm = bmesh.new()
    strokes_bm_symm.from_mesh(strokes_mesh_symm)

    # симметрия!
    symm_orto_rings = stroke_nocross_for_symmetry(result, symm_dict, bm)
    for idx, item in enumerate(symm_orto_rings):
        (faces_in_loop, loops, change_direction_face) = item
        # TODO: пока что запись в тот же строкмеш что при первом обходе. Нужно создавать отдельный!
        process_faces_from_loop_with_island_connectivity_em(faces_in_loop, change_direction_face, Z_STEP*Z_COORD_START, bm, strokes_bm_symm, loops)
        Z_COORD_START += 1
    for id in visited_faces_id:
        bm.faces[id].select = True

#    output_not_visited_faces(bm, visited_faces_id)

    # обновление объекта на экране
    bmesh.update_edit_mesh(mesh_obj.data)
    # обновление point cloud на экране
    strokes_bm.to_mesh(strokes_mesh)
    strokes_obj.data.update()

    strokes_bm_symm.to_mesh(strokes_mesh_symm)
    strokes_obj_symm.data.update()

    # очистка памяти от bm
    bm.free()
    strokes_bm.free()
    strokes_bm_symm.free()

    #--- EDIT MODE
  #  bpy.ops.object.editmode_toggle()
  #  bpy.context.view_layer.update()
    
    # Конвертирование накопителя строк в кривую
  #  convert_mesh_to_curve_and_make_poly(strokes_obj, mesh_obj)    
    return



def main():
    ######## главные параметры для создания строкмешей!
    COLLECTION_NAME_BASE = "TestCol_"
    STROKEMESH_NAME_BASE = "StrokesMesh_"
    Z_STEP = 0.1

    last_col_idx = get_last_collection_index(COLLECTION_NAME_BASE)
    if (last_col_idx == -1):
        last_strokemesh_idx = -1
        last_z_coord = -1
        new_z_coord = 0
    else:
        last_strokemesh_idx = get_last_strokemesh_index(STROKEMESH_NAME_BASE, COLLECTION_NAME_BASE + str(last_col_idx))
        if (last_strokemesh_idx == -1):
            last_z_coord = -1 # либо 0, все равно
            new_z_coord = 0
        else:
            last_z_coord = get_last_z_coord(STROKEMESH_NAME_BASE + str(last_strokemesh_idx))
            # TODO: сомневаюсь в делении и округление, протестить
            # да вроде все корректно
            new_z_coord = round(last_z_coord / Z_STEP) + 1

    new_col_name = COLLECTION_NAME_BASE + str(last_col_idx + 1)
    new_strokemesh_idx_start = last_strokemesh_idx + 1

    ####### вызовы ########

    # одна петля без перпендикуляров
   # test_collect_loop_nocross(STROKEMESH_NAME_BASE + str(new_strokemesh_idx_start), Z_STEP, new_col_name, new_z_coord)
    # перпендикуляры
   # test_loops_for_loop_nocross(STROKEMESH_NAME_BASE + str(new_strokemesh_idx_start), Z_STEP, new_col_name, new_z_coord)
    # автозаполнение
    #test_auto_strokes_nocross(Z_STEP, new_col_name, STROKEMESH_NAME_BASE, new_strokemesh_idx_start, new_z_coord)

    # автозаполнение с симметрией
    # !!! этот метод НЕ РАБОТАЕТ
    #test_auto_stroke_nocross_for_symmetry(Z_STEP, new_col_name, STROKEMESH_NAME_BASE, new_strokemesh_idx_start, new_z_coord)

    # вычисление последних параметров создания мешей
    #test_getting_last_indexes()

    # пока что НЕ РАБОТАЕТ т к не работает closest_....
    #test_get_symmetrical_face()

    # построение словаря симметричных граней
    #test_make_symmetry_dictionary()

    # перпендикуляры с симметрией (вызывать от изолированной области)
    test_stroke_nocross_for_symmetry(STROKEMESH_NAME_BASE, new_strokemesh_idx_start, Z_STEP, new_col_name, new_z_coord)

if __name__ == "__main__":
    main()
    
# для дебага из vscode....
# может ломать результат в blender    
#main()
