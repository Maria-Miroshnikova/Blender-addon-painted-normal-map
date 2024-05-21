import bpy
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import FloatProperty, StringProperty, EnumProperty, PointerProperty, BoolProperty, FloatVectorProperty
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

# !!! edge flowloop = петля ребер, добавила flow- чтобы не путать петли ребер и механизм BMloop

#####################################################################################################################################
# --- скопировано вместо импорта.
# TODO: починить импорт в блендере

def read_symmetry_dict_from_file(filename: str):
    try:
        f = open(filename, 'r')
        f.close()
    except FileNotFoundError:
        return None

    with open(filename) as f:
        symm_dict_str = json.load(f)
        symm_dict = {}
        for key in symm_dict_str.keys():
            symm_dict[int(key)] = symm_dict_str[key]
    return symm_dict

def write_symmetry_dict_to_file(filename: str, symm_dict: dict):
    with open(filename, 'w') as f:
        f.write(json.dumps(symm_dict))
    return

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

def is_quad(face: BMFace) -> bool:
    '''
    Функция проверяет, является ли данная грань четырехугольной
    '''
    return (len(face.loops) == 4)

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

    return max_z

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

#####################################################################################################################################
# ---- переделанные функции из числа старых

# Версия функции collect_face_loop_with_recording_visited_not_quads_nocross
# принимает на вход конкретную лупу, т. к. в той версии при получении ребра можно было оказаться не на той грани, на которой задумано
# останавливает сбор если встречает посещенную грань
# может вернуть недействительный change_direction_face, если обход вызван из обойденной грани
# 
def collect_face_loop_with_recording_visited_not_quads_nocross_concrete_loop(loop_start: BMLoop, visited_faces_id: Set[int]) -> (List[BMFace], List[BMLoop], int, List[BMFace], bool):
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
        return (faces_in_loop, loops, -1, visited_not_quads, was_cycled_loop)
    #обход в другую сторону, если не было цикла
    loop = loop_start.link_loop_next.link_loop_next
    faces_in_loop_two_direction, loops_two_direction, was_cycled_loop, visited_not_quads_two = loop_go_with_recording_visited_not_quads_nocross(loop, True, visited_faces_id, set([face.index for face in faces_in_loop_one_direction]))
    faces_in_loop.extend(faces_in_loop_two_direction)
    loops.extend(loops_two_direction)
    visited_not_quads.extend(visited_not_quads_two)
    return (faces_in_loop, loops, change_direction_face, visited_not_quads, was_cycled_loop)

#####################################################################################################################################
# --- finding outlines/holes and concentric face loops around holes/outlines

def is_pole(vert: BMVert):
    '''
    Функция проверяет, является ли данная вершина полюсом
    '''
    return len(vert.link_edges) != 4

def get_edge_flowloop_on_outline_by_verts_and_bound_edges(start_vert: BMVert, visited_edges: Set[BMEdge]):
    '''
    Функция "прыгает" от одной краевой вершины к другой по краевым ребрам между вершинами.
    Не зависит от наличия/отсутствия полюсов на краю.

    TODO: гипотеза: краевые петли ребер всегда зациклены
    TODO: гипотеза: не бывает пересечений с посещенными ребрами

    возвращает списком все краевые ребра, по которым пройдет, + bool был ли цикл (скорее всего должен быть всегда true! кроме каких-то вырожденных случаев)

    ! не подходит для wire ребер (не являющися частью грани) т. к. не отлавливает самопересечения, только цикл
    '''
    flowloop_edges: List[BMEdge] = []

    current_vert = start_vert
    current_edge: BMEdge = None
    for edge in current_vert.link_edges:
        if edge.is_boundary:
            current_edge = edge
            break
    
    if (current_edge == None):
        print("No boundary edges while searshon edgeflow on boundary")
        return [], False

    if current_edge in visited_edges:
        return [], False
    flowloop_edges.append(current_edge)
    
    if current_edge.verts[0] == current_vert:
        next_vert = current_edge.verts[1]
    else:
        next_vert = current_edge.verts[0]
    
    current_vert = next_vert

    while(True):
        for edge in current_vert.link_edges:
            if edge.is_boundary and (edge not in flowloop_edges):
                current_edge = edge
                break
        if (current_edge == None):
            print("No boundary edges while searshon edgeflow on boundary")
            return
        
        if current_edge in visited_edges:
            print("Edge while searshon edgeflow on boundary was visited before")
            return flowloop_edges, False
        
        flowloop_edges.append(current_edge)
        
        if current_edge.verts[0] == current_vert:
            next_vert = current_edge.verts[1]
        else:
            next_vert = current_edge.verts[0]
        if (next_vert == start_vert):
            return flowloop_edges, True
        current_vert = next_vert

def get_edges_for_all_outlines(bm: BMesh) -> List[List[BMEdge]]:
    '''
    Функция находит все края модели и ребра на этих краях. Для каждого отдельного "края" записывает ребра в список.
    Возвращает список "краев", каждый из которых является списком ребер по этому краю.

    гипотеза: краевые петли ребер всегда зациклены
    гипотеза: не бывает пересечений с посещенными ребрами
    '''

    flowloops: List[List[BMEdge]] = []

    visited_edges: Set[BMEdge] = set() 
    visited_verts: Set[BMVert] = set()

    # прыгаем по всем краевым вершинами
    for vert in bm.verts:
        if vert.is_boundary:
            if vert in visited_verts:
                continue
            # собираем край из ребер, начиная с данной вершины
            flowloop_edges, is_cycled = get_edge_flowloop_on_outline_by_verts_and_bound_edges(vert, visited_edges)
            assert(is_cycled) # гипотеза про цикличность краев
            # на всякий запоминаем посещенные ребра в общее множество
            visited_edges = visited_edges.union(set(flowloop_edges))
            flowloops.append(flowloop_edges)

            # отдельно пробегаем собранные краевые ребра, достаем из них посещенные вершины и записываем
            # их в общее множество, чтобы не делать вызов сбора края на посещенных вершинах
            # TODO: можно было бы запоминать посещенные вершины еще в самой функции сбора края, не делая дополнительный проход
            for edge in flowloop_edges:
                for v in edge.verts:
                    visited_verts.add(v)
    return flowloops

def find_maximum_concentric_faceloop_around_outline(bm: BMesh, outline: List[BMEdge]) -> List[Tuple[List[BMFace], List[BMLoop], int, List[BMFace]]]:
    '''
    Для данного края outline функция ищет максимальный набор концентрических петель.
    Если петли найдены - возвращает результаты обхода этих петель функцией collect_face_loop_with_recording_visited_not_quads_nocross_concrete_loop
    в виде списка результатов вызова для каждого кольца.
    Последним в списке будет идти максимальное кольцо.

    TODO: должны ли сюда приходить "посещенные" и должны ли запомненные тут посещенные передаваться вовне?
    '''

    # выбор ребра на краю (любое). Это - ребро для горизонтального кольца ребер
    start_edge = outline[0]
    
    result_for_concentric_loops: List[Tuple[List[BMFace], List[BMLoop], int, List[BMFace]]] = []
    visited_faces_id = set()

    current_horiz_loop = start_edge.link_loops[0]

    current_vertic_loop = current_horiz_loop.link_loop_next # т к начальное ребро - краевое, у него всего одна лупа.
    current_face = current_horiz_loop.face
    if (not is_quad(current_face)):
        return result_for_concentric_loops

    # обход горизонтального кольца ребер
    while(True):
        faces_in_loop, loops, idx_change_dir, visited_not_quads, was_cycled = collect_face_loop_with_recording_visited_not_quads_nocross_concrete_loop(current_vertic_loop, visited_faces_id)
        if (not was_cycled): # не добавляем эту петлю к концентрическим, заканчиваем обход
            break
        
        # запоминаем результат
        faces_id = [face.index for face in faces_in_loop]
        visited_faces_id = visited_faces_id.union(faces_id)
        result_for_concentric_loops.append((faces_in_loop, loops, idx_change_dir, visited_not_quads))

        # следующее ребро в горизонтальном кольце
        next_horiz_loop = current_horiz_loop.link_loop_next.link_loop_next.link_loop_radial_next
        current_horiz_loop = next_horiz_loop
        if (current_horiz_loop.edge.is_boundary): # дошли до края
            break
        current_face = next_horiz_loop.face
        if (not is_quad(current_face)):
            break
        current_vertic_loop = current_horiz_loop.link_loop_next.link_loop_radial_next

    return result_for_concentric_loops

def get_outlins_of_ring(current_horiz_loop: BMLoop, loops: List[BMLoop]) -> (List[BMLoop], List[BMLoop]):
    '''
    !!!!!! перед применением метода пересчитать нормали!!! из-за нормалей в разных полуплоскостях (неправильно определение внутренней и внешней стороны меша)
    могут быть сбиты направления у BMloop!!!!
    
    Функция по набору loop ЦИКЛИЧНОГО вертикального кольца ищет ПОСЛЕДОВАТЕЛЬНЫЕ ребра его внешней и внутренней границы
    Чтобы определить, как из границ внутренняя/внешняя, используется current_horiz_loop

    Возвращает (множество loop внутренней границы, множество loop внешней границы)
    '''
 #   current_ring_outline_next = set([loop.link_loop_next for loop in loops]) # сбор loop на краях текущего вертикального кольца
    current_ring_outline_next = [loop.link_loop_next for loop in loops] # сбор loop на краях текущего вертикального кольца
   # for loop in current_ring_outline_next:
   #     loop.edge.select = True
   # return False
 #   current_ring_outline_prev = set([loop.link_loop_prev for loop in loops]) # сбор loop на краях текущего вертикального кольца
    current_ring_outline_prev = [loop.link_loop_prev for loop in loops] # сбор loop на краях текущего вертикального кольца
   # for loop in current_ring_outline_prev:
   #     loop.face.select = True
   # return False
    
    # определяем, которая из границ внешняя/внутренняя
    if (current_horiz_loop in current_ring_outline_next):
        # внутренняя, внешняя
        return (current_ring_outline_next, current_ring_outline_prev)
    else:
        # внутренняя, внешняя
        return (current_ring_outline_prev, current_ring_outline_next)
    
def get_adjacent_faces_id_for_loop_outline(loop_outline: List[BMLoop]):
    '''
    Функция по данной ей границе из loop находит грани, смежные с этой границей с другой стороны
    Определение стороны однозначно т к loop и radial_loop относятся только к одной грани!

    если кольцо смежно само с собой/с дырой/с внутренними кольцами, то link_loop_radial_next.face.index будет содержать как раз
    соседние грани этого же кольца / те же грани для которых вызывается radial_next / грани внутренних колец - соответственно
    '''
    faces_next_to_inner_outline_of_ring_id = [loop.link_loop_radial_next.face.index for loop in loop_outline]
    #for face_id in faces_next_to_inner_outline_of_ring_id:
    #    bm.faces[face_id].select = True
    #return False
    return faces_next_to_inner_outline_of_ring_id

def is_current_ring_dense(current_horiz_loop: BMLoop, loops: List[BMLoop], faces_in_concentric_loops_id: Set[int], bm: BMesh):
    '''
    !!!!!! перед применением метода пересчитать нормали!!! из-за нормалей в разных полуплоскостях (неправильно определение внутренней и внешней стороны меша)
    могут быть сбиты направления у BMloop!!!!
    
    Функция проверяет для данного ЦИКЛИЧНОГО кольца, что его внутренник край смежен только с гранями, посещенными во время поиска концентрических колец.

    faces_in_concentric_loops_id уже должно содержать грани данного кольца!
    все параметры названы так же, как в функции, где вызывается is_current_ring_dense
    см. их смысл в find_maximum_concentric_faceloop_around_outline_dense
    '''
    inner_outline_loops, outer_outline_loops = get_outlins_of_ring(current_horiz_loop, loops)
        
    # собираем id граней, которые смежны с внутренней границей текущего кольца
    faces_next_to_inner_outline_of_ring_id = get_adjacent_faces_id_for_loop_outline(inner_outline_loops)
        
    return faces_in_concentric_loops_id.issuperset(faces_next_to_inner_outline_of_ring_id), inner_outline_loops, outer_outline_loops

def slide_when_end_of_horiz_ring_because_of_holes_between_rings(current_horiz_loop: BMLoop):
    '''
    Функиця для данной current_horiz_loop лупы, находящейся на КРАЮ (is_boundary) дырки между концентрическими лупами
    ищет, куда сдвинуть вдоль внешней границы текущего концентрического кольца эту current_horiz_loop, чтобы продолжить обход колец

    Если сдвиг возможен - вернет новую horiz_loop
    Если это на самом деле внешняя граница не просто кольца, а всего меша, то вокруг будет дырка ВЕЗДЕ и сдвиг не возможен. Вернет стартовую лупу.
    
    ВЫЗЫВАТЬ, когда уже известно, что current_horiz_loop внешнаяя КРАЕВАЯ! и краевая для КОЛЬЦА, уже записанного в допустимые концентрические!
    '''
    start_loop = current_horiz_loop
    while(True):
        next_loop = current_horiz_loop.link_loop_next.link_loop_radial_next.link_loop_next
        #next_loop.edge.select = True
        current_horiz_loop = next_loop
        if (current_horiz_loop == start_loop):
            return start_loop
        if (not current_horiz_loop.edge.is_boundary):
            # изначальная краевая лупа оказалась не внутри новой грани, а внутри той же грани, где только что было обход кольца, и направление неверное!
            # поэтому, дойдя до некраевой лупы, нужно перепрыгнуть на сторону новой грани для обхода
            return current_horiz_loop.link_loop_radial_next

# версия find_maximum_concentric_faceloop_around_outline
def find_maximum_concentric_faceloop_around_outline_dense(bm: BMesh, outline: List[BMEdge], visited_faces_id: Set[int]) -> List[Tuple[List[BMFace], List[BMLoop], int, List[BMFace]]]:
    '''
    !!!!!! перед применением метода пересчитать нормали!!! из-за нормалей в разных полуплоскостях (неправильно определение внутренней и внешней стороны меша)
    могут быть сбиты направления у BMloop!!!!

    Для данного края outline функция ищет максимальный набор концентрических петель.
    Если петли найдены - возвращает результаты обхода этих петель функцией collect_face_loop_with_recording_visited_not_quads_nocross_concrete_loop
    в виде списка результатов вызова для каждого кольца.
    Последним в списке будет идти максимальное кольцо.
    Также возвращает край (List[BMLoop]) максимального кольца (лупы будут изнутри кольца)

    Следит за тем, что кольца были плотные (не содержали в области внутри себя грани, не принадлежащие одному из колец). Кольцо, смежное с лишними грани, не засчитывается.

    Записывает грани колец в visited_faces_id
    Не вызывает обход, если грань стартового граничного ребра уже посещена

    TODO: должны ли сюда приходить "посещенные" и должны ли запомненные тут посещенные передаваться вовне?
    '''

    # выбор ребра на краю (любое). Это - ребро для горизонтального кольца ребер
    start_edge = outline[0]
    
    result_for_concentric_loops: List[Tuple[List[BMFace], List[BMLoop], int, List[BMFace]]] = []
  #  visited_faces_id = set()

    current_horiz_loop = start_edge.link_loops[0]
    #current_horiz_loop.edge.select = True
    #return

    # проверка на посещенность грани стартовой лупы. Если мы в посещенной зоне - не делать поиск колец! Конец
    if (current_horiz_loop.face.index in visited_faces_id):
        print("outline in visited area!")
        return result_for_concentric_loops, visited_faces_id, []

    current_vertic_loop = current_horiz_loop.link_loop_next # т к начальное ребро - краевое, у него всего одна лупа.
    current_face = current_horiz_loop.face
    if (not is_quad(current_face)):
        return result_for_concentric_loops, visited_faces_id, []

    maximum_ring_outline = []
    faces_in_concentric_loops_id = set() # множество всех граней, посещенных при обходе в этой функции
    # обход горизонтального кольца ребер
    while(True):
        faces_in_loop, loops, idx_change_dir, visited_not_quads, was_cycled = collect_face_loop_with_recording_visited_not_quads_nocross_concrete_loop(current_vertic_loop, visited_faces_id)
        if (not was_cycled): # не добавляем эту петлю к концентрическим, заканчиваем обход
            break

        # проверка на плотность. Если кольцо неплотное - заканчиваем обход.
        faces_id = [face.index for face in faces_in_loop]
        faces_in_concentric_loops_id = faces_in_concentric_loops_id.union(faces_id)  # добавляем грани текущего кольца в посещенные
        
        is_dense, inner_outline, outer_outline = is_current_ring_dense(current_horiz_loop, loops, faces_in_concentric_loops_id, bm)
        if not is_dense:
            break

        # запоминаем результат
        visited_faces_id = visited_faces_id.union(faces_id)
        result_for_concentric_loops.append((faces_in_loop, loops, idx_change_dir, visited_not_quads))
        maximum_ring_outline = outer_outline

        # следующее ребро в горизонтальном кольце
        next_horiz_loop = current_horiz_loop.link_loop_next.link_loop_next.link_loop_radial_next
        current_horiz_loop = next_horiz_loop
        if (current_horiz_loop.edge.is_boundary): # дошли до края
            slide_loop = slide_when_end_of_horiz_ring_because_of_holes_between_rings(current_horiz_loop) # попробуем сдвинуться по краю (работает, если встретили дырку между концентрическими кольцами)
            if slide_loop == current_horiz_loop: # сдвиг не возможен => находится на краю меша, конец обхода
                break
            current_horiz_loop = slide_loop
        current_face = current_horiz_loop.face
        if (not is_quad(current_face)):
            break
        current_vertic_loop = current_horiz_loop.link_loop_next.link_loop_radial_next

    return result_for_concentric_loops, visited_faces_id, maximum_ring_outline


###############################################################################################################################################################
# --- creating regular grid with poles


def get_edge_flowloop(edge_start: BMEdge, pole_start: BMVert, visited_edges: Set[BMEdge], verts_in_flowloops: Set[int]):
    '''
    Функция ищет петлю ребер, проходящее через стартовое ребро с началом в вершине-полюсе, и записывает всю петлю в посещенные ребра
    Если встретит посещенное ребро, то обход прекратится
    Если встретит полюс - обход тоже прекратится (наподобие встроенного поиска петель в блендере, только на краях не будет работать так же т к края состоят из полюсов!)
    '''
    # если упремся в полюс - конец обхода -- по идее, это отлавливает попадание на край, т к на краю не может быть не полюс
    # если попадем на посещенную - конец обхода
    # если попадем на крайнюю - конец обхода -- НЕ ФАКТ!

    # запомним вершину на конце стартового ребра. Его начальная вершина по условиям - полюс.
    start_edge_verts = edge_start.verts
    if start_edge_verts[0].index == pole_start.index:
        end_vert = start_edge_verts[1]
    else:
        end_vert = start_edge_verts[0]
    
    start_loop: BMLoop = None

    # найдем стартовую лупу с началом в стартовом полюсе и стартовым ребром
    for loop in edge_start.link_loops:
        if (loop.vert.index == pole_start.index):
            start_loop = loop
            break
    if (start_loop == None):
        # теория: все равно пройдем по этому ребру в другом запуске.
        # либо: сделать другой подбор next
        return
        print("none start_loop with start_edge_id = " + str(edge_start.index))
        assert(start_loop == None)

    current_end_vert = end_vert
    current_loop = start_loop
    while (True):
        #if (current_loop.edge.index in [1926, 19893, 25268, 34671]):
        #    print("edge " + str(current_loop.edge.index) + " start pole: " + str(pole_start.index))
        if (current_loop.edge in visited_edges):
            break
        visited_edges.add(current_loop.edge)
        if (is_pole(current_end_vert)):
            break
        if (current_end_vert.index in verts_in_flowloops):
            break
        
        verts_in_flowloops.add(current_end_vert.index)
        next_loop = current_loop.link_loop_next.link_loop_radial_next.link_loop_next # следующее ребро в петле ребер
        if (next_loop == None):
            print("none start_loop with start_edge_id = " + str(edge_start.index))
            assert(next_loop == None)
        current_loop = next_loop
        current_end_vert = next_loop.link_loop_next.vert


def get_grid_by_poles(bm: BMesh):
    '''
    Функция ищет все полюса и для каждого полюса через все его ребра проводит петли ребер
    Возвращает все петли ребер, начинающиеся в полюсах
    Ребра собираются в единое множество

    Когда одна ветвь сетки упирается в уже построенную ветвь, построение ветки обрывается
    => Сетка вообще говоря не однозначна и ее вид зависит от порядка обхода полюсов.
    TODO: сделать управление этим?

    Обработка краевых полюсов:
    3-полюсы: краевые ребра добавляются в посещенные, построение сетки не запускается
    >3-полюсы: краевые ребра добавляющая в посещенные, для не краевых - запуск построения сетки

    TODO: ввести заданные вручную пределы, внутри которых строится сетка
    TODO: обрабатывать края отдельно и не запускать сетку на зонах с краями!
    '''
    
    poles_verts: List[BMVert] = []
    for v in bm.verts:
        if is_pole(v):
            poles_verts.append(v)
    
    grid_edges = set()
    verts_in_flowloops_id = set() # все вершины ребер, участвующих в сетке. Для отслеживания пересечений в сетке.
    for pole in poles_verts:
        # обработка краевых вершин
        if (pole.is_boundary):
            for edge in pole.link_edges:
                if (edge.is_boundary):
                    grid_edges.add(edge)
                else:
                    if len(pole.link_edges) > 3:
                        get_edge_flowloop(edge, pole, grid_edges, verts_in_flowloops_id)
            continue
        for edge in pole.link_edges:
            get_edge_flowloop(edge, pole, grid_edges, verts_in_flowloops_id)
            #grid_edges.extend(edge_rings)
    not_visited_pole_edges = set()
    for pole in poles_verts:
        for edge in pole.link_edges:
            # проверяем мою теорию
            #assert (edge in grid_edges)
            if (edge not in grid_edges):
                not_visited_pole_edges.add(edge)
    return poles_verts, grid_edges, not_visited_pole_edges

#######################################################################################################################################
# методы для считывания/редактирования разметки граней по зонам

# константы для слоя с разметкой граней по зонам
NOT_IN_ZONE = 0 # у концентрических зон индексы < 0, у остальных > 0

def write_faces_to_zone_layer(bm: BMesh, layer_name: str, faces_id: List[int], index: int):
    '''
    Функция записывает всем граням из заданного layer_name слоя граней значения index (номер зоны)
    Ничего не возвращает
    Если слоя нет, создает его
    '''
    if layer_name not in bm.faces.layers.int:
        face_zones_layer = bm.faces.layers.int.new(layer_name)
    else:
        face_zones_layer =  bm.faces.layers.int[layer_name]

    for id in faces_id:
        bm.faces[id][face_zones_layer] = index

def get_faces_from_zone_layer(bm: BMesh, layer_name: str, index: int):
    '''
    Функция ищет грани, у которых слой layer_name имеет значение index (грани из зоны номер index)
    Если слоя нет, возвращает пустое множество
    '''
    if layer_name not in bm.faces.layers.int:
        return set()
    else:
        face_zones_layer =  bm.faces.layers.int[layer_name]
    
    faces_from_zone_id = set()
    for f in bm.faces:
        if f[face_zones_layer] == index:
            faces_from_zone_id.add(f.index)

    return faces_from_zone_id

def delete_faces_from_zone_layer(bm: BMesh, layer_name: str, faces_to_delete: List[BMFace]):
    '''
    Функция всем данным гранями записывает в слой граней layer_name значение NOT_IN_ZONE
    '''
    if layer_name not in bm.faces.layers.int:
        return
    else:
        face_zones_layer =  bm.faces.layers.int[layer_name]
    
    for f in faces_to_delete:
        f[face_zones_layer] = NOT_IN_ZONE

def show_select_all_faces_from_zone_layer(bm: BMesh, layer_name: str, index: int):
    '''
    Функция ищет все грани, у которых в слое граней layer_name стоит значение index (номер зоны)
    и делает их выбранными в edit_mode

    !!!!! НЕ ЗАБЫТЬ СДЕЛАТЬ bm.update
    '''
    if layer_name not in bm.faces.layers.int:
        return
    else:
        face_zones_layer =  bm.faces.layers.int[layer_name]

    for f in bm.faces:
        if f[face_zones_layer] == index:
            f.select = True
        #else:
        #    f.select = False

def prepare_zone_layer(bm: BMesh, layer_name: str):
    '''
    Функция содает слой layer_name в слоях граней

    Вызывать функцию перед всеми обходами меша, иначе будут проблемы с (пересоздавшимися?) BMFace
    TODO: как правильно работать со слоями??
    '''
    if layer_name not in bm.faces.layers.int:
        face_zones_layer = bm.faces.layers.int.new(layer_name)
    else:
        face_zones_layer =  bm.faces.layers.int[layer_name]

IS_POLEGRID_EDGE = 1
IS_NOT_POLEGRID_EDGE = -1

def write_edges_to_polegrid_layer(bm: BMesh, layer_name: str, edges_id: List[int]):
    '''
    Функция записывает всем ребрам из заданного layer_name слоя ребер значения 
    Ничего не возвращает
    Если слоя нет, создает его
    '''
    if layer_name not in bm.edges.layers.int:
        polegrid_layer = bm.edges.layers.int.new(layer_name)
    else:
        polegrid_layer =  bm.edges.layers.int[layer_name]

    for id in edges_id:
        bm.edges[id][polegrid_layer] = IS_POLEGRID_EDGE

def get_edges_from_polegrid_layer(bm: BMesh, layer_name: str):
    '''
    Функция ищет ребра, у которых слой layer_name имеет значение IS_POLEGRID_EDGE
    Если слоя нет, возвращает пустое множество
    '''
    if layer_name not in bm.edges.layers.int:
        return set()
    else:
        polegrid_layer =  bm.edges.layers.int[layer_name]
    
    edges_id = set()
    for e in bm.edges:
        if e[polegrid_layer] == IS_POLEGRID_EDGE:
            edges_id.add(e.index)

    return edges_id

def delete_edges_from_polegrid_layer(bm: BMesh, layer_name: str, edges_to_delete: List[BMEdge]):
    '''
    Функция всем данным ребрам записывает в слой ребер layer_name значение IS_NOT_POLEGRID_EDGE
    '''
    if layer_name not in bm.edges.layers.int:
        return
    else:
        polegrid_layer =  bm.edges.layers.int[layer_name]
    
    for e in edges_to_delete:
        e[polegrid_layer] = IS_NOT_POLEGRID_EDGE

def show_select_all_edges_from_polegrid_layer(bm: BMesh, layer_name: str,):
    '''
    Функция ищет все ребра, у которых в слое ребер layer_name стоит значение IS_POLEGRID_EDGE
    и делает их выбранными в edit_mode

    !!!!! НЕ ЗАБЫТЬ СДЕЛАТЬ bm.update
    '''
    if layer_name not in bm.edges.layers.int:
        return
    else:
        polegrid_layer =  bm.edges.layers.int[layer_name]

    for e in bm.edges:
        if e[polegrid_layer] == IS_POLEGRID_EDGE:
           e.select = True

IS_BORDER_EDGE = 1
NOT_BORDER_EDGE = -1

def get_edges_from_edge_border_layer(bm: BMesh, layer_name: str):
    '''
    Функция ищет ребра, у которых слой ребер layer_name имеет значение IS_BORDER_EDGE
    Если слоя нет, возвращает пустое множество
    '''
    if layer_name not in bm.edges.layers.int:
        return set()
    else:
        edge_group_layer =  bm.edges.layers.int[layer_name]
    
    border_edges_id = set()
    for e in bm.edges:
        if e[edge_group_layer] == IS_BORDER_EDGE:
            border_edges_id.add(e.index)

    return border_edges_id

###########################################################################################################################

# константы для определения, какой области принадлежит полюс
CONCENTRIC_AREA = -1
NOT_CONCENTRIC_AREA = 1
OUTLINE_AREA = 10

def define_pole_area(pole: BMVert, bm: BMesh, layer_name: str):
    '''
    Функция определяет, какой области принадлежит полюс: области концентрических колец по краям меша / всему остальному пространству / границе между эти двумя областями
    ! граница между зонами = outline максимального кольца
    '''

    if layer_name not in bm.faces.layers.int:
        print("Try to get zones_layer for pole are detection, but layer does not exist!")
        return
    else:
        face_zones_layer =  bm.faces.layers.int[layer_name]

    # определение количества смежных граней из разных зон
    count_faces_in_concentric_area = 0
    count_faces_in_not_concentric_area = 0
    for face in pole.link_faces:
        if face[face_zones_layer] >= 0:
            count_faces_in_not_concentric_area += 1
        else:
            count_faces_in_concentric_area += 1

    # смежные грани только неконцентричные
    if (count_faces_in_concentric_area == 0):
        return NOT_CONCENTRIC_AREA
    # смежные грани только концентричные
    if (count_faces_in_not_concentric_area == 0):
        return CONCENTRIC_AREA
    # есть смежные грани обоих типов
    return OUTLINE_AREA

def define_edge_area(edge: BMEdge, bm: BMesh, layer_name: str):
    '''
    Функция определяет, какой области принадлежит ребро: области концентрических колец по краям меша / всему остальному пространству / границе между эти двумя областями
    ! граница между зонами = outline максимального кольца
    '''

    if layer_name not in bm.faces.layers.int:
        print("Try to get zones_layer for pole are detection, but layer does not exist!")
        return
    else:
        face_zones_layer =  bm.faces.layers.int[layer_name]

    # определение количества смежных граней из разных зон
    count_faces_in_concentric_area = 0
    count_faces_in_not_concentric_area = 0
    for face in edge.link_faces:
        if face[face_zones_layer] >= 0:
            count_faces_in_not_concentric_area += 1
        else:
            count_faces_in_concentric_area += 1

    # смежные грани только неконцентричные
    if (count_faces_in_concentric_area == 0):
        return NOT_CONCENTRIC_AREA
    # смежные грани только концентричные
    if (count_faces_in_not_concentric_area == 0):
        return CONCENTRIC_AREA
    # есть смежные грани обоих типов
    return OUTLINE_AREA

def poles_sorted_by_degree(bm: BMesh):
    '''
    Функция собирает все полюсы меша и возвращает список с ними, сортировка по возрастанию степени полюса
    '''
    poles_verts: List[BMVert] = []

    #for v in bm.verts:
    #    if is_pole(v):
    #        poles_verts.append(v)
    poles_degrees_dict = {} # словарь степень_полюса : список id таких полюсов (количество легко посчитать)
    for v in bm.verts:
        if is_pole(v):
            degree = len(v.link_edges)
            if not (degree in poles_degrees_dict):
                poles_degrees_dict[degree] = list([v.index])
            else:
                list_prev : List[int] = poles_degrees_dict[degree]
                list_prev.append(v.index)
                poles_degrees_dict[degree] = list_prev
            #poles_verts.append(v)
    print("poles statistics: ")
    for key in poles_degrees_dict:
        degree = key
        count = len(poles_degrees_dict[key])
        print(str(degree) + "-edge : " + str(count))
    # полюса обрабатываются в порядке увелечения степени, не учитывается частота
    sorted_digrees = sorted(poles_degrees_dict.keys())
    #sorted_digrees = poles_degrees_dict.keys()
    print("poriadok obhoda: " + str(sorted_digrees))
    for key in sorted_digrees:
        verts = [bm.verts[id] for id in poles_degrees_dict[key]]
        poles_verts.extend(verts)
    return poles_verts

# TODO: сделать координату на выбор пользователя??
def sort_poles_by_coordinates(poles: List[BMVert]):
    '''
    Функция сортирует список полюсов по их Z координате по убыванию (сверху вниз)
    '''
    poles_sorted = sorted(poles, key=lambda vert: vert.co.z, reverse=True)
    return poles_sorted

def get_grid_by_poles_with_preprocessed_grid_edges(bm: BMesh, grid_edges: Set[BMEdge], layer_name: str):
    '''
    Функция ищет все полюса и для каждого полюса через все его ребра проводит петли ребер
    Возвращает все петли ребер, начинающиеся в полюсах
    Ребра собираются в единое множество

    Когда одна ветвь сетки упирается в уже построенную ветвь, построение ветки обрывается
    => Сетка вообще говоря не однозначна и ее вид зависит от порядка обхода полюсов.
    TODO: сделать управление этим?

    Обработка краевых полюсов:
    3-полюсы: краевые ребра добавляются в посещенные, построение сетки не запускается
    >3-полюсы: краевые ребра добавляющая в посещенные, для не краевых - запуск построения сетки

    grid_edges - ребра в сетке, может быть заранее подготовлено. Например, ручным вводом границ обхода
    verts_in_flowloops_id - индексы всех вершин, участвующих в сетке, в т ч не полюсов, а тех, что соединяют ребра сетки.
                            должны быть подготовлены соответственно.

    TODO: ввести заданные вручную пределы, внутри которых строится сетка
    TODO: хороший способ сортировки полюсов / замена останавок на построеные всех линий + очистку лишних
    '''
    # подготовка полюсов для обхода (сбор и сортировки)
    poles_verts_sorted_by_degree = poles_sorted_by_degree(bm)
    poles_verts = sort_poles_by_coordinates(poles_verts_sorted_by_degree)

    # сбор уже поучаствовавших в концентрических границах вершин
    verts_in_flowloops_id = set()
    for edge in grid_edges:
        for vert in edge.verts:
            verts_in_flowloops_id.add(vert.index)

    for pole in poles_verts:
        #if pole.index == 7284:
        #    break
            #print('kek')
        pole_area = define_pole_area(pole, bm, layer_name)
        
        # концентрическая область - уже размечена
        if (pole_area == CONCENTRIC_AREA):
            continue
        # пограничная область - размечаем только ребрам в не концентрической области
        elif (pole_area == OUTLINE_AREA):
            for edge in pole.link_edges:
                edge_area = define_edge_area(edge, bm, layer_name)
                if (edge_area == NOT_CONCENTRIC_AREA):
                    get_edge_flowloop(edge, pole, grid_edges, verts_in_flowloops_id)
        # свободная область: размечаем по всем ребрам. Отдельная обработка краевых ребер, не попавших в концентрическую область!
        else:
            # обработка краевых полюсов на краях, где нет концентрических колец
            if (pole.is_boundary):
                for edge in pole.link_edges:
                    if (edge.is_boundary):
                        grid_edges.add(edge)
                    else:
                        if len(pole.link_edges) > 3:
                            get_edge_flowloop(edge, pole, grid_edges, verts_in_flowloops_id)
                continue
            # обработка не краевых полюсов
            for edge in pole.link_edges:
                get_edge_flowloop(edge, pole, grid_edges, verts_in_flowloops_id)
                #grid_edges.extend(edge_rings)
    
    # TODO: дебаговая часть
    not_visited_pole_edges = set()
    for pole in poles_verts:
        for edge in pole.link_edges:
            # проверяем мою теорию
            #assert (edge in grid_edges)
            if (edge not in grid_edges):
                not_visited_pole_edges.add(edge)

    return poles_verts, not_visited_pole_edges

def get_grid_by_poles_with_outlines_handling_and_concentric_priority(bm: BMesh, border_edges: List[BMEdge]):
    '''
    Функция, которая сначала вызывает сбор краев и поиск концентрических колец по краям,
    размечает концентрические грани, записывает нужные края в число ребер сетки, а затем вызывает сбор сетки по полюсам.
    '''

    # подготовка для разметки граней модели
    face_zones_layer_name = "zones_layer"
    zones_dict = {} # словарь index_zone: priority
    max_index_negative = 0
    default_priority_negative = 2
    prepare_zone_layer(bm, face_zones_layer_name)

    grid_edges: Set[BMEdge] = set(border_edges)
    # поиск краев
    outlines = get_edges_for_all_outlines(bm)
    # поиск максимальных концентрических колец по краям меша
    visited_faces_id = set()
    concentric_zones_result = []
    for outline in outlines:
        result, visited_faces_id, maximum_ring_outline = find_maximum_concentric_faceloop_around_outline_dense(bm, outline, visited_faces_id)

        # записываем результат, чтобы построить кривые в концентрических зонах в ОТДЕЛЬНОЙ функции ПОТОМ
        if (len(result) != 0):
            concentric_zones_result.append(result)

        # разметка данной концентрической зоны
        if (len(result) != 0):
            # подготовка словаря
            max_index_negative -= 1
            zones_dict[max_index_negative] = default_priority_negative
            for ring_data in result:
                faces, loops, idx_change, quads = ring_data
                faces_id = [face.index for face in faces]
                write_faces_to_zone_layer(bm, face_zones_layer_name, faces_id, max_index_negative)

        # края зоны становятся частью сетки
        for loop in maximum_ring_outline:
            #loop.edge.select = True
            grid_edges.add(loop.edge)

        # если на краю нет концентрических колец, то край будем обрабатывать внутри get_grid
        if len(maximum_ring_outline) == 0:
            continue

        # на краях были лупы, поэтому края не нужно обрабатывать отдельно
        for loop in outline:
            grid_edges.add(loop)

    # строим сетку        
    poles_verts, not_visited_pole_edges = get_grid_by_poles_with_preprocessed_grid_edges(bm, grid_edges, face_zones_layer_name)

    return grid_edges, visited_faces_id, zones_dict, concentric_zones_result

##############################################################################################################################################
# переделанные под нужды функции из old_versions

def loop_go_inside_grid(starting_loop: BMLoop, is_second_go: bool, grid_edges: Set[BMEdge]) -> (List[BMFace], List[BMLoop], bool):
    '''
    Функция обхода face loop (можно переделать в edge ring), начиная с первого ребра для edge ring
    Работает только для квадов, попав на не квад - останавливается
    Возвращает список всех граней, вошедших в face loop при обходе в данном направлении
    is_second_go нужен, чтобы при обходе в обратную сторону не добавлять первую грань еще раз в список

    останавливает обход если попадает на ребро сетки!
    стартовая лупа не проверяется на принадлежность сетке
    '''
    faces_in_loop = []
    loops = []
    loop = starting_loop
    
    if (not is_quad(loop.face)):
        return [], [], False
    
    if (not is_second_go):
        faces_in_loop.append(loop.face)
        loops.append(loop)

    if (loop.edge in grid_edges):
        return faces_in_loop, loops, False
    
    radial_loop = loop.link_loop_radial_next

    # проверяем, что mesh оборвался (плоская поверхность)
    # проверка основана на том, что у грани с обрывом на внешнем ребре только 1 link_loops
    if (radial_loop == loop):
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
    
    # цикл прыжков для сбора всей лупы пока не упремся в не кваду или не вернемся в начальную (замкнутая лупа)
    # или не закончится плоский меш
    
    loop = next_loop
    while next_loop.edge != starting_loop.edge:

        # если попали на ребро сетки - конец обхода
        if (loop.edge in grid_edges):
            return faces_in_loop, loops, False

        radial_loop = loop.link_loop_radial_next
        next_loop = radial_loop.link_loop_next.link_loop_next
        
        # циклический меш
        if (next_loop == starting_loop):
            break

        # проверяем, что mesh оборвался (плоская поверхность)
        # проверка основана на том, что у грани с обрывом на внешнем ребре только 1 link_loops
        if (radial_loop == loop):
            return faces_in_loop, loops, False
        
        # проверяем, следующая грань это квада? 
        is_next_face_quad = is_quad(radial_loop.face)
        
        if (not is_next_face_quad):
            return faces_in_loop, loops, False
        else:
            faces_in_loop.append(radial_loop.face)
            if (is_second_go):
                loops.append(radial_loop)
            else:
                loops.append(radial_loop.link_loop_next.link_loop_next)

        loop = next_loop
    return faces_in_loop, loops, True


def collect_face_loop_inside_grid(loop: BMEdge, grid_edges: List[BMEdge]) -> (List[BMFace], List[BMLoop], int):
    '''
    Функция обхода face loop (можно переделать в edge ring), начиная с первого ребра для edge ring
    Работает только для квадов, попав на не квад/конец меша - меняет направление, попав снова - останавливается
    Сначала идет только в одном направлении, затем в другую
    Возвращает список всех граней, вошедших в face loop, и номер грани, с которой начался обход в другую сторону 
    Если петля зациклена, возвращает -1 (надо соединить последнюю вершину с первой при создании кривой)

    останавливает обход если попадает на ребро сетки!
    стартовая лупа не проверяется на принадлежность сетке
    '''
    faces_in_loop = []
    loops = []
    #обход в одну сторону

    faces_in_loop_one_direction, loops_one_direction, was_cycled_loop = loop_go_inside_grid(loop, False, grid_edges)
    faces_in_loop.extend(faces_in_loop_one_direction)
    loops.extend(loops_one_direction)
    change_direction_face = len(faces_in_loop) - 1
    if (was_cycled_loop):
        return (faces_in_loop, loops, -1)
    #обход в другую сторону, если не было цикла
    # внутри того же face берем лупу на противоположной стороны, и направление обхода меняется
    # первая лупа не проверяется на совпадение с сеткой!
    loop = loop.link_loop_next.link_loop_next
    faces_in_loop_two_direction, loops_two_direction, was_cycled_loop = loop_go_inside_grid(loop, True, grid_edges)
    faces_in_loop.extend(faces_in_loop_two_direction)
    loops.extend(loops_two_direction)
    return (faces_in_loop, loops, change_direction_face)

# допустим, пользователь сам выбирает начальную петлю (ребром конечно же), вдоль которой будет происходить сбор петель
# эта версия просто идет вдоль петли и собирает для нее результаты вызова collect_face_loop от её поперечных петель
def loops_for_loop_inside_grid(start_loop: BMLoop, visited_faces_id: Set[int], grid_edges: List[BMEdge]) -> List[Tuple[List[BMFace], List[BMLoop], int]]:
    '''
    Функция идет вдоль кольца, заданного стартовой лупой, и собирает все принадлежащие ей
    перпендикулярные кольца
    изменяет множество visited_faces_id
    не выходит за пределы области вызова в сетке grid_edges
    '''
    
    result = []

    faces_in_loop, edge_ring, idx_change_dir = collect_face_loop_inside_grid(start_loop, grid_edges)
    for face in faces_in_loop:
        visited_faces_id.add(face.index)
    for loop in edge_ring:
        # выбор перпендикулярной лупы
        loop_next = loop.link_loop_next
        faces_in_loop_inner, edge_ring_inner, idx_change_dir_inner = collect_face_loop_inside_grid(loop_next, grid_edges)
        for face in faces_in_loop_inner:
            visited_faces_id.add(face.index)
        result.append((faces_in_loop_inner, edge_ring_inner, idx_change_dir_inner))
    
    return result

###################################################################################################################################################################

def choose_next_loop(bm: BMesh, not_visited_faces_id: Set[int], grid_edges: List[BMEdge]):
    '''
    Фунция выбирает из непосещенных граней какую-то (без признаков и сортировок), ищет у нее подходящее ребро (не краевое и не из сетки)
    Возвращает loop с внутренней стороны грани.
    На данный момент, будет попытка найти у грани не краевую и не сеточную лупу, но если таких нет, то функция вернут случайную лупу этой грани.
    Даже изолированная в сетке одиночная грань будет обработана!
    
    TODO: еще до этой функции сделать слияние одиночных граней?
    TODO: может тогда тут вообще не нужны никакие размышления, просто берем грань и любую ее loop??

 #   Если на выбранной грани не окажется подходящих ребер, грань удалится из непосещенных, поиск подходящей грани с подходящим ребром продолжится    
 #   Если грань и ребро не найдутся, функция вернет None, а not_visited_faces_id будет пусто
    '''
    while(len(not_visited_faces_id) != 0):
        next_face_id = not_visited_faces_id.pop()
        next_face = bm.faces[next_face_id]
        next_edge : BMEdge = None

        # ищем среди ребер ребро, которое не на ребрах сетки, а внутри области, ограниченной сеткой
        for edge in next_face.edges:
            if edge not in grid_edges:
                next_edge = edge
                # если ребро при этом не крайнее - берем
                if not (next_edge.is_boundary):
                    for loop in next_edge.link_loops:
                        if loop.face.index == next_face_id:
                            return loop
            if next_edge != None:
                return next_edge.link_loops[0] #крайнее ребро, у него всего одна лупа
            
        # если дошли сюда, то у грани все ребра сеточные, т е это изолированная грань
        # TODO: вызов попытки слияния?
        # возвращаем у нее ЛЮБУЮ лупу
        return next_face.loops[0]
    return None

def choose_loop_for_orientation_by_size_of_zone(grid_edges: List[BMEdge], start_loop: BMLoop):
    '''
    Функция делает пробный обход из грани данной стартовой лупы по вертикали и по горизонтали.
    Узнает размер области по длине собранных колец.
    Возвращает ребро более короткого кольца, чтобы перпендикуляры по нему были в длинную сторону (в т. ч. решается вопрос полосок!)

    !!! в полюсной сетке grid_edges все зоны регулярные, в том числе: все параллельные кольца одинакового размера, нет самопересечений
    '''
    faces_horizontal, loops_horizontal, idx_change_dir_horizontal = collect_face_loop_inside_grid(start_loop, grid_edges)

    # берем боковую лупу любую из двух. ее краевость/сеточность учтется в collect_face_loop!
    vertical_loop = start_loop.link_loop_next
    faces_vertical, loops_vertical, idx_change_dir_vertical = collect_face_loop_inside_grid(vertical_loop, grid_edges)

    if len(faces_horizontal) > len(faces_vertical):
        return vertical_loop
    return start_loop
    

# TODO: здесь и в постройке grid с учетом концентров - сделать словарь самоуправляющимся объектом!!!! чтобы он сам следил за индексом!!!!
def go_all_grid_nonconcentric_areas(bm: BMesh, grid_edges: List[BMEdge], visited_faces_id: Set[int], layer_name: str, zone_priority_dict: dict, faces_to_vector_dict: dict, count_basic_vector_params, len_coeff: float):
    '''
    Функция обходит все непосещенные зоны (ожидается, что все концентры будут уже посещены!! и записани в visited_faces_id)
    и собирает в них перпендикулярные кольца.
    Размечает зоны, заносит в словарь зон zones_priority_dict.
    Вызывает построение базовых векторов в обойденных зонах.

    Не посещает не-квады.
    Посещает в том числе одиночные изолированные грани.
    Правильно обходит полосы.
    Выбор грани для посещения - случайная (предопределенная).
    Выбор ориентации - так, чтобы перпендикуляры были || более длинной стороне зоны

    TODO: сделать назначение приоритетов порандомнее?? или это вообще где-нибудь снаружи
    '''
    # подготовка словаря
    max_index_positive = 0 
    default_priority_positive = 1
    
    # все грани меша = непосещенные
    not_visited_face_id = set()
    # выкинуть не квады и посещенные
    for face in bm.faces:
        if is_quad(face) and (face.index not in visited_faces_id):
            not_visited_face_id.add(face.index)
    
    list_of_results = []

    while(len(not_visited_face_id) > 0):
        # выбрать новую грань и ребро
        loop = choose_next_loop(bm, not_visited_face_id, grid_edges)
        if (loop == None): # грани кончились, поэтому лупа для обхода так и не была выбрана
            break
        
        # определить ориентацию обхода
        loop = choose_loop_for_orientation_by_size_of_zone(grid_edges, loop)
        
        # обход
        result = loops_for_loop_inside_grid(loop, visited_faces_id, grid_edges)
        not_visited_face_id = not_visited_face_id.difference(visited_faces_id)  # вычеркиваем все посещенные грани из непосещенных граней для вызова
        
        # разметка zone_layer и запись в словарь
        if (len(result) > 0):
            max_index_positive += 1
            zone_priority_dict[max_index_positive] = default_priority_positive
            for edge_ring in result:
                faces, loops, idx_change_dir = edge_ring
                faces_id = [face.index for face in faces]
                write_faces_to_zone_layer(bm, layer_name, faces_id, max_index_positive)

                # построить базовые кривые в гранях (уже в отдельной функции)
                count_basic_vector_params(faces, loops, faces_to_vector_dict, bm, len_coeff)

                # запись в общий результат обхода (для файла)
                list_of_results.append(result)

    print("count of positive zones = " + str(max_index_positive))
    return list_of_results

##############################################################################################################################################
# -- функции построения векторов по обойденным петлям граней

def count_UV_coords_for_two_basic_verts_in_face_in_thirds_proportionally_to_face_size(loop_start: BMLoop, loop_end: BMLoop, bm: BMesh):
    '''
    Функция строит векторы на главной средней линии грани на ее третях
    главная средняя грань = пересекает кольцо ребер

    (для тестов была полезна)
    '''
    uv_layer = bm.loops.layers.uv.verify()
   
    v_1 = loop_start.edge.verts[0]
    v_2 = loop_start.edge.verts[1]
    u_1 = loop_end.edge.verts[0]
    u_2 = loop_end.edge.verts[1]

    # КОРОЧЕ до вершин придется достучаться через лупы соответствующие, потому что слой у них
    # поэтому нужно для каждой точки найти соответствующую ей лупу и у нее уже просить координаты точки в uv

    for loop in loop_start.face.loops:
        if loop.vert == v_1:
            loop_v1 = loop
        elif loop.vert == v_2:
            loop_v2 = loop
        elif loop.vert == u_1:
            loop_u1 = loop
        elif loop.vert == u_2:
            loop_u2 = loop
    
    # перевод координат в UV

    v_1_uv_co = loop_v1[uv_layer].uv
    v_2_uv_co = loop_v2[uv_layer].uv
    u_1_uv_co = loop_u1[uv_layer].uv
    u_2_uv_co = loop_u2[uv_layer].uv

    # TODO: проверить округление
    #v_center: Vector = (v_1.co + v_2.co) / 2
    #u_center: Vector = (u_1.co + u_2.co) / 2
    v_center: Vector = (v_1_uv_co + v_2_uv_co) / 2
    u_center: Vector = (u_1_uv_co + u_2_uv_co) / 2

    middle_line_co: Vector = (v_center + u_center) / 2

    p: Vector = middle_line_co + (v_center - middle_line_co) / 3
    q: Vector = middle_line_co + (u_center - middle_line_co) / 3

    return p, q

def count_UV_coords_for_two_basic_verts_in_face(loop_start: BMLoop, loop_end: BMLoop, bm: BMesh, len_coeff: float):
    '''
    Функция строит векторы на главной средней линии грани
    главная средняя грань = пересекает кольцо ребер

    Длина векторов len_coeff = 0.001
    '''
    uv_layer = bm.loops.layers.uv.verify()
   
    v_1 = loop_start.edge.verts[0]
    v_2 = loop_start.edge.verts[1]
    u_1 = loop_end.edge.verts[0]
    u_2 = loop_end.edge.verts[1]

    # КОРОЧЕ до вершин придется достучаться через лупы соответствующие, потому что слой у них
    # поэтому нужно для каждой точки найти соответствующую ей лупу и у нее уже просить координаты точки в uv

    for loop in loop_start.face.loops:
        if loop.vert == v_1:
            loop_v1 = loop
        elif loop.vert == v_2:
            loop_v2 = loop
        elif loop.vert == u_1:
            loop_u1 = loop
        elif loop.vert == u_2:
            loop_u2 = loop
    
    # перевод координат в UV

    v_1_uv_co = loop_v1[uv_layer].uv
    v_2_uv_co = loop_v2[uv_layer].uv
    u_1_uv_co = loop_u1[uv_layer].uv
    u_2_uv_co = loop_u2[uv_layer].uv

    v_center: Vector = (v_1_uv_co + v_2_uv_co) / 2
    u_center: Vector = (u_1_uv_co + u_2_uv_co) / 2

    middle_line_co: Vector = (v_center + u_center) / 2
    directon: Vector = (v_center - middle_line_co)
    directon.normalize()

  #  len_coeff = 0.001

    p: Vector = middle_line_co + directon * len_coeff
    q: Vector = middle_line_co - directon * len_coeff

    return p, q

def count_minimum_h_from_mass_center(center_co: Vector, face: BMFace, uv_layer):
    '''
    center_co - центр масс грани, координаты в uv_развертке
    функция строит высоты из центра масс к каждой стороне и наход самую короткую высоту
    возвращает длину минимальной высоты
    '''
    
    h_vectors = [] # векторы высот из О к сторонами
    loops = face.loops
    min_h = float('inf')
    for i in range(-1, len(face.loops) - 1):
        v_1_uv = loops[i][uv_layer].uv
        v_2_uv = loops[i + 1][uv_layer].uv
        h_v1_v2_point, other = geometry.intersect_point_line(center_co, v_1_uv, v_2_uv) # точки пересечения высот из О со сторонами
        h_vector = center_co - h_v1_v2_point

        # поиск минимальной высоты и ее вектора
        if h_vector.magnitude < min_h:
            min_h = h_vector.magnitude

    return min_h

def count_UV_verts_in_face_with_angle_around_basic_vector(bm: BMesh, ring_edge_loop: BMLoop, angle: float, len_coeff: float, basic_vector: Vector):
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
    
    #min_h = count_minimum_h_from_mass_center(center_co, loop_start.face, uv_layer)
    #min_h = 0.1 # сначала чисто угол протестируем
    
    axis_vector_1 = Vector(basic_vector)
    axis_vector_2 = Vector(basic_vector)

    # Угол будет вверх от ОХ если угол будет БОЛЬШЕ 0. Меньше - в нижнюю полуплоскость повернемся.
    #if angle < 0:
    #    angle = -angle
    # правильные ли это матрицы??
    rotation_matrix_1 = Matrix.Rotation(angle, 2)
    angle_2 = angle + math.radians(180.0)
    if (angle == 0):
        angle_2 = math.radians(180.0)
    rotation_matrix_2 = Matrix.Rotation(angle_2, 2)

    axis_vector_1.rotate(rotation_matrix_1) 
    axis_vector_2.rotate(rotation_matrix_2)
    axis_vector_1.normalize()
    axis_vector_2.normalize()
    p = center_co + len_coeff * axis_vector_1
    q = center_co + len_coeff * axis_vector_2

    return p, q

def make_vector_in_point(point: Vector, length: float, angle: float):

    cos = math.cos(angle)
    sin = math.sin(angle)
    vector_1 = Vector((length * cos, length * sin))
    vector_2 = -vector_1

    # эта версия создает p и q на равном расстоянии от point, она становится центром вектора pq
    p = point + vector_1
    q = point + vector_2

    return p, q

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

def  count_UV_coords_for_two_basic_verts_all_faces(faces: List[BMFace], loops: List[BMLoop], faces_to_vector_dict: dict, bm: BMesh, len_coeff: float):
    for loop in loops:
                p, q = count_UV_coords_for_two_basic_verts_in_face(loop, loop.link_loop_next.link_loop_next, bm, len_coeff)
                faces_to_vector_dict[loop.face.index] = (p, q, loop.index)

def make_basic_vectors_for_all_grid(bm: BMesh, grid_edges: List[BMEdge], visited_faces_id: Set[int], layer_name: str, zones_dict: dict,
                                    concentric_result: List[Tuple[List[BMFace], List[BMLoop], int]], len_coeff: float,
                                    use_symmetry: bool, symm_file_name: str, use_left_side: bool):
    '''
    Функция вызывает обход не концентрических областей и подсчет углов базовых векторов с OX для граней колец,
    а также то же самое в ранее обойденных концентрических областях
    '''
    # если обход с симметрией, то надо обходить только одну сторону. Запишем все грани второй стороны в посещенные.
    if (use_symmetry):
        symm_dict = read_symmetry_dict_from_file(symm_file_name)
        left_faces_id = set()
        rigth_faces_id = set()
        for key in symm_dict.keys():
            if (key in left_faces_id) or (key in rigth_faces_id):
                continue

            if not (is_quad(bm.faces[key])):
                continue
            center = bm.faces[key].calc_center_median()
            if (center.x < 0):
                left_faces_id.add(key)
                rigth_faces_id.add(symm_dict[key])
            else:
                left_faces_id.add(symm_dict[key])
                rigth_faces_id.add(key)
        if (use_left_side):
            visited_faces_id = visited_faces_id.union(rigth_faces_id)
        else:
            visited_faces_id = visited_faces_id.union(left_faces_id)   

    faces_to_vector_dict = {} # словарь face_id : (p, q, main loop), где p и q - точки на третях средней линии грани -- тестовое
    
    # сбор колец неконцентрических областей и подсчет углов одновременно
    list_of_results = go_all_grid_nonconcentric_areas(bm, grid_edges, visited_faces_id, layer_name, zones_dict, faces_to_vector_dict, count_UV_coords_for_two_basic_verts_all_faces, len_coeff)
    
    # получение симметричного результата для второй половины и построение базы в нем
    if (use_symmetry):
        for result in list_of_results:
            symm_result = loops_for_loop_by_edge_nocross_for_symmetry(list_of_results, symm_dict, bm)
            # подсчет углов симметричной области
            for edge_ring in symm_result:
                faces, loops, idx_change_dir = edge_ring
                count_UV_coords_for_two_basic_verts_all_faces(faces, loops, faces_to_vector_dict, bm, len_coeff)
            list_of_results.append(symm_result) # для записи в файл


    
    # подсчет углов концентрических областей
    # тут надо будет обойти даже если симметрия, потому что концентрические зоны предыдущий алгос не затрагивает.
    for result in concentric_result:
        for edge_ring in result:
          #  faces, loops, idx_change_dir, not_quads = edge_ring
            faces, loops, idx_change_dir = edge_ring
            count_UV_coords_for_two_basic_verts_all_faces(faces, loops, faces_to_vector_dict, bm, len_coeff)
    return faces_to_vector_dict, list_of_results

def make_vectors_from_dict(faces_to_vector_dict: dict, vector_bm: BMesh):
    '''
    Функция для всех граней в словаре faces_to_vector_dict считывает точки (p,q, main_loop) вектора, посчитанного в этой грани.
    Строит этот вектор и добавляет в vector_bm 
    '''    
    for key in faces_to_vector_dict.keys():
        v1, v2, edge = faces_to_vector_dict[key]
        #v1, v2 = faces_to_vector_dict[key]
        #face = bm.faces[key]
        create_and_add_vector_to_vectormesh(vector_bm, v1, v2)
    return

def filter_face_with_vectors(bm: BMesh, face: BMFace, face_to_vector_dict: dict, filter_params: List[int], layer_name: str, zone_to_priority_dict: dict):
    '''
    Функция фильтрации конкретной грани.
    
    Форма фильтра: все смежные грани по КВАДРАТУ (то есть смежность не по ребру, а по точке)
    
    Смежные грани собираются с помощью BFS обхода
    filter_params - массив, чей i-ый элемент соответствует коэффициенту важности элементов c i+1-ой глубиной обхода
    (0-ой, то есть фильтруемый, элемент не участвует в подсчете итогового значения)

    Подсчет значения:
    для каждого вектора считается его угол относительно фильтруемого вектора. При этом направление фильтруемого вектора берется любое,
    а направление окружающих векторов задаются от ближайшей к дальней точке
    (близость считается относительно прямой, содержащей фильтруемый вектор)
    Углы окружающих векторов поворачивают фильтруемый вектор по/против часовой стрелки
    Их значения умножаются на приоритет радиусный и на приоритет зоны (у концентрической зоны приоритет больше)
    Итоговое значение = сумме всех углов окружающих векторов (умноженных на приоритеты)    
    '''

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

    # отбрасываем обход зон, если начиная с них дальше нули в радиусных параметрах
    size = len(filter_params)
    for i in range(0, size):
        if (filter_params[size-1-i] == 0):
            max_depth -= 1
    max_depth += 1

    # весь фильтр из 0
    if (max_depth == 0):
        return 0, main_vector

    queue = []
    queue_faces = set()
    visited_faces = set()
    queue.append((face, depth))
    queue_faces.add(face.index)
    
    #vectors = []
    main_p, main_q, loop = face_to_vector_dict[face.index]
    main_vector: Vector = main_p - main_q
    while(len(queue) > 0):
        current_face, current_depth = queue.pop()
        visited_faces.add(current_face.index)
        queue_faces.remove(current_face.index)
        
        # подсчет вклада этой грани в угол
        
        zone_index = bm.faces[current_face.index][face_zones_layer]
        zone_priority = zone_to_priority_dict[zone_index]

        p, q, ring_edge_loop = face_to_vector_dict[current_face.index]
        vector = p - q

        # основной вектор тоже участвует в BFS, но его мы пропускаем
        if (vector != main_vector):
            filter_priority = filter_params[current_depth - 1]

            # в одной ли полуплоскости точки вектора (хз что делать из из разных)
            # наверное, надо будет считать, какое из расстояний больше, и все равно в сторону большего направлять
            # тогда и проверять не буду!

            # найти ближнайшую из двух дочек к вектору
            p_height_point, other = geometry.intersect_point_line(p, main_p, main_q)
            q_height_point, other = geometry.intersect_point_line(q, main_p, main_q)

            p_distance = (p - p_height_point).magnitude
            q_distance = (q - q_height_point).magnitude

            # сделать вектор от ближайшей к дальней точек

            if (p_distance < q_distance):
                vector = -vector

            #if (p_distance == q_distance):
                # параллельный вектор - не учитывать при подсчете
            #    # TODO переход к сбору смежных в очередь
            #    break

            # вроде этого уже достаточно будет
            # даже сразу можно считать его вклад и не надо записывать в список
            angle = main_vector.angle_signed(vector)

            # верхняя полуплоскость
            if angle < 0:
                if angle < -math.radians(90.0):
                    # поворот в положительную сторону, по часовой
                    angle = (angle + math.radians(180.0))
                else:
                    # поворот в отрицательную сторону, против часовой
                    angle = angle
            # нижняя полуплоскость
            else:
                if angle > math.radians(90.0):
                    # поворот в отрицательную сторону, против часовой
                    angle = angle - math.radians(180.0)
                else:
                    # поворот в положительную сторону, по часовой
                    angle = angle
                
            #angle_summ += angle
            

            zone_priority_summ += zone_priority
            filter_priority_summ += filter_priority
            summ += filter_priority * zone_priority
            angle_summ += filter_priority * zone_priority * angle

        # добавление смежных граней в очередь, если только мы не на максимальной глубине
        if (current_depth == max_depth):
            continue

        # ~квадратный фильтр ()
        for vert in current_face.verts:
            for f in vert.link_faces:
                if f.index in queue_faces:
                    continue
                if f.index in visited_faces:
                    continue
                queue.append((f, current_depth + 1))
                queue_faces.add(f.index)

    return -angle_summ, main_vector

import statistics

def filter_face_median(bm: BMesh, face: BMFace, face_to_vector_dict: dict, filter_params: List[int], layer_name: str, zone_to_priority_dict: dict):
    '''
    Данный фильтр работает по тому же принципу, что и filter_face_with_vectors
    - Форма
    - BFS и параметры
    - Подсчет угла для конкретного вектора из числа окружающих

    Подсчет значения:
    Значения углов для окружающих векторов сортируются. Сначала идет сортировка количеств векторов в четвертях.
    Затем внутри медианной четверти выбирается медианное значение.
    '''
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
    
    #vectors = []
    main_p, main_q, loop = face_to_vector_dict[face.index]
    main_vector: Vector = main_p - main_q
    
    # 0 - 1 четверть, 1 - 2 четвреть, ...
    #count_angles_in_quarts = [0, 0, 0, 0] # число векторов в координатных четвертях
    quarts_dict = {} # quart: [angles in quart]
    quart_id = 0
    while(len(queue) > 0):
        current_face, current_depth = queue.pop()
        visited_faces.add(current_face.index)
        queue_faces.remove(current_face.index)
        
        # подсчет вклада этой грани в угол
        filter_priority = filter_params[current_depth]
        
        zone_index = bm.faces[current_face.index][face_zones_layer]
        zone_priority = zone_to_priority_dict[zone_index]

        p, q, ring_edge_loop = face_to_vector_dict[current_face.index]
        vector = p - q

        # основной вектор тоже участвует в BFS, но его мы пропускаем
        if (vector != main_vector):
            # в одной ли полуплоскости точки вектора (хз что делать из из разных)
            # наверное, надо будет считать, какое из расстояний больше, и все равно в сторону большего направлять
            # тогда и проверять не буду!

            # найти ближнайшую из двух дочек к вектору
            p_height_point, other = geometry.intersect_point_line(p, main_p, main_q)
            q_height_point, other = geometry.intersect_point_line(q, main_p, main_q)

            p_distance = (p - p_height_point).magnitude
            q_distance = (q - q_height_point).magnitude

            # сделать вектор от ближайшей к дальней точек

            if (p_distance < q_distance):
                vector = -vector

            #if (p_distance == q_distance):
                # параллельный вектор - не учитывать при подсчете
            #    # TODO переход к сбору смежных в очередь
            #    break

            # вроде этого уже достаточно будет
            # даже сразу можно считать его вклад и не надо записывать в список
            angle = main_vector.angle_signed(vector)

            # верхняя полуплоскость
            if angle < 0:
                if angle < -math.radians(90.0):
                    # поворот в положительную сторону, по часовой
                    angle = (angle + math.radians(180.0))
                    quart_id = 1
                else:
                    # поворот в отрицательную сторону, против часовой
                    angle = angle
                    quart_id = 0
            # нижняя полуплоскость
            else:
                if angle > math.radians(90.0):
                    # поворот в отрицательную сторону, против часовой
                    angle = angle - math.radians(180.0)
                    quart_id = 2
                else:
                    # поворот в положительную сторону, по часовой
                    angle = angle
                    quart_id = 3
                
            #angle_summ += angle
            

            #zone_priority_summ += zone_priority
            #filter_priority_summ += filter_priority
            #summ += filter_priority * zone_priority
            #angle_with_coeffs = filter_priority * zone_priority * angle
            if quart_id not in quarts_dict:
                quarts_dict[quart_id] = [(angle, filter_priority, zone_priority)]
            else:
                prev_list = quarts_dict[quart_id]
                prev_list.append((angle, filter_priority, zone_priority))
                quarts_dict[quart_id] = prev_list

        # добавление смежных граней в очередь, если только мы не на максимальной глубине
        if (current_depth == max_depth):
            continue

        # ~квадратный фильтр ()
        for vert in current_face.verts:
            for f in vert.link_faces:
                if f.index in queue_faces:
                    continue
                if f.index in visited_faces:
                    continue
                queue.append((f, current_depth + 1))
                queue_faces.add(f.index)
    
    if (len(quarts_dict.keys()) == 0):
        return 0, main_vector
    # поиск максимальной, а не медианной, четверти
    #count_angles_in_quarts: List = []
    max_quart = 0
    max_count = -1
    # TODO: сейчас приоритет на последнюю попавшуюся четверть. Стоит ли рандомизировать приоритет?
    # TODO: при всем этом подходе высокая приоритетность концентрической зоны не будет иметь значения
    for key in quarts_dict.keys():
        #count_angles_in_quarts.append(key, len(quarts_dict[key]))
        if (len(quarts_dict[key]) > max_count):
            max_count = len(quarts_dict[key])
            max_quart = key

    #count_angles_in_quarts.sort(key=lambda x: x[1])

    # поиск медианного угла в четверти
    max_quart_agles = quarts_dict[max_quart]
    # Здесь сортировать по произведению или же только по углу??
    #max_quart_agles.sort(key=lambda x: x[0]*x[1]*x[2])
    max_quart_agles.sort(key=lambda x: x[0])
    median_len = len(max_quart_agles)
    if (median_len % 2 == 0):
        i : int = median_len // 2 - 1
        angle_1, f_pr_1, z_pr_1 = max_quart_agles[i]
        i = median_len // 2
        angle_2, f_pr_2, z_pr_2 = max_quart_agles[i]
        result = (angle_1 * f_pr_1 * z_pr_1 + angle_2 * f_pr_2 * z_pr_2) / (f_pr_1 * z_pr_1 + f_pr_2 * z_pr_2)
    else:
        angle, f_pr, z_pr = max_quart_agles[median_len // 2]
        result = angle

    return -result, main_vector

def filter_face_median_smart(bm: BMesh, face: BMFace, face_to_vector_dict: dict, filter_params: List[int], layer_name: str, zone_to_priority_dict: dict):
    '''
    Данный фильтр работает по тому же принципу, что и filter_face_with_vectors
    - Форма
    - BFS и параметры
    - Подсчет угла для конкретного вектора из числа окружающих

    Подсчет значения:
    Значения углов для окружающих векторов сортируются. Сначала идет сортировка количеств векторов в четвертях.
    Затем внутри медианной четверти выбирается медианное значение.
    '''
    # BFS с глубиной обхода = len(filter_params)

    # для конкретной грани - достать ее зону из слоя, достать из словаря приоритет этой зоны
    # считать общую сумму приоритетов зон и приоритетов фильтра
    
    face_zones_layer =  bm.faces.layers.int[layer_name]

    depth = 0
    max_depth = len(filter_params) - 1

    # отбрасываем обход зон, если начиная с них дальше нули в радиусных параметрах
    size = len(filter_params)
    for i in range(0, size):
        if (filter_params[size-1-i] == 0):
            max_depth -= 1
    max_depth += 1

    queue = []
    queue_faces = set()
    visited_faces = set()
    queue.append((face, depth))
    queue_faces.add(face.index)
    
    main_p, main_q, loop = face_to_vector_dict[face.index]
    main_vector: Vector = main_p - main_q

    # весь фильтр из 0
    if (max_depth == 0):
        return 0, main_vector
    
    # 0 - 1 четверть, 1 - 2 четвреть, ...
    #count_angles_in_quarts = [0, 0, 0, 0] # число векторов в координатных четвертях
    quarts_dict = {} # quart: [angles in quart]
    quart_id = []
    while(len(queue) > 0):
        current_face, current_depth = queue.pop()
        visited_faces.add(current_face.index)
        queue_faces.remove(current_face.index)

        # основной вектор тоже участвует в BFS, но его мы пропускаем
        if (current_depth != 0):

            # подсчет вклада этой грани в угол
            filter_priority = filter_params[current_depth - 1]
        
            zone_index = bm.faces[current_face.index][face_zones_layer]
            zone_priority = zone_to_priority_dict[zone_index]

            p, q, ring_edge_loop = face_to_vector_dict[current_face.index]
            vector = p - q

            # в одной ли полуплоскости точки вектора (хз что делать из из разных)
            # наверное, надо будет считать, какое из расстояний больше, и все равно в сторону большего направлять
            # тогда и проверять не буду!

            # найти ближнайшую из двух дочек к вектору
            p_height_point, other = geometry.intersect_point_line(p, main_p, main_q)
            q_height_point, other = geometry.intersect_point_line(q, main_p, main_q)

            p_distance = (p - p_height_point).magnitude
            q_distance = (q - q_height_point).magnitude

            # сделать вектор от ближайшей к дальней точек

            if (p_distance < q_distance):
                vector = -vector

            # ОБРАБОТКА КРАЕВЫХ СЛУЧАЕВ
            # -- ПАРАМЕТР ТОЧНОСТИ
            rel_tol = 1e-4
            
            #is_p_q_close = math.isclose(p_distance, q_distance, rel_tol=rel_tol)
            #if (is_p_q_close):
            # => вектор параллелен главной прямой, либо перпендикулярен и она пересекает его посередине

            # вроде этого уже достаточно будет
            # даже сразу можно считать его вклад и не надо записывать в список
            angle = main_vector.angle_signed(vector)

            # ~ 0 градусов (параллельность)
            if isclose(angle, -math.radians(0), rel_tol=rel_tol) or isclose(angle, math.radians(0), rel_tol=rel_tol) or isclose(angle, -math.radians(180), rel_tol=rel_tol) or isclose(angle, math.radians(180), rel_tol=rel_tol):
                    #center = (p + q) / 2
                    #main_center = (main_p + main_q) / 2
                    #if math.isclose(center, main_center, rel_tol):
               # main_p_p_dist = (p - main_p).magnitude
               # main_p_q_dist = (q - main_p).magnitude
               # main_q_p_dist = (p - main_q).magnitude
               # main_q_q_dist = (q - main_q).magnitude

               # main_p_distances = main_p_p_dist + main_p_q_dist
               # main_q_distances = main_q_q_dist + main_q_p_dist

                # центр вектора находится на перпендикуляре из центра главного вектора
               # if (math.isclose(main_p_distances, main_q_distances, rel_tol=rel_tol)):
                    #quart_id = [0,1,2,3]
               # elif main_p_distances < main_q_distances: 
               #     quart_id = [0,3]
               # else:
               #     quart_id = [1,2]
                quart_id = [0,1,2,3]
                angle = 0
            # верхняя полуплоскость
            elif angle < 0:
                # ~ 90 градусов
                if isclose(angle, -math.radians(90), rel_tol=rel_tol):
                    #if (is_p_q_close): # главная прямая пересекает этот вектор посередине
                        # вектор вносит вклад во все четверти
                    #    quart_id = [0,1,2,3]
                    #else: # вектор вносит вклад в 1 и 2 четверти
                    #    quart_id = [0,1]
                    #    angle = math.radians(90)
                    quart_id = [0,1,2,3]
                    angle = math.radians(90)
                elif angle < -math.radians(90.0):
                    # поворот в положительную сторону, по часовой
                    angle = (angle + math.radians(180.0))
                    quart_id = [1]
                else:
                    # поворот в отрицательную сторону, против часовой
                    angle = angle
                    quart_id = [0]
            # нижняя полуплоскость
            else:
                # ~ 90 градусов
                if isclose(angle, math.radians(90), rel_tol=rel_tol):
                    #if (is_p_q_close): # главная прямая пересекает этот вектор посередине
                        # вектор вносит вклад во все четверти
                    #    quart_id = [0,1,2,3]
                    #else: # вектор вносит вклад в 3 и 4 четверти
                    #    quart_id = [2,3]
                    #    angle = math.radians(90)
                    quart_id = [0,1,2,3]
                    angle = math.radians(90)
                elif angle > math.radians(90.0):
                    # поворот в отрицательную сторону, против часовой
                    angle = angle - math.radians(180.0)
                    quart_id = [2]
                else:
                    # поворот в положительную сторону, по часовой
                    angle = angle
                    quart_id = [3]
            if (len(quart_id) > 1):
                # добавляем вектор в списки нескольких четвертей
                for id in quart_id:
                    # всегда положительный
                    signed_angle = angle
                    if (id == 0) or (id == 2):
                        # это отрицательный четверти
                        signed_angle = -angle
                    if id not in quarts_dict:
                        quarts_dict[id] = [(signed_angle, filter_priority, zone_priority)]
                    else:
                        prev_list = quarts_dict[id]
                        prev_list.append((signed_angle, filter_priority, zone_priority))
                        quarts_dict[id] = prev_list

            else:
                quart_id = quart_id[0]        
                if quart_id not in quarts_dict:
                    quarts_dict[quart_id] = [(angle, filter_priority, zone_priority)]
                else:
                    prev_list = quarts_dict[quart_id]
                    prev_list.append((angle, filter_priority, zone_priority))
                    quarts_dict[quart_id] = prev_list

        # добавление смежных граней в очередь, если только мы не на максимальной глубине
        if (current_depth == max_depth):
            continue

        # ~квадратный фильтр ()
        for vert in current_face.verts:
            for f in vert.link_faces:
                if f.index in queue_faces:
                    continue
                if f.index in visited_faces:
                    continue
                queue.append((f, current_depth + 1))
                queue_faces.add(f.index)
    
    if (len(quarts_dict.keys()) == 0):
        return 0, main_vector
    # поиск максимальной, а не медианной, четверти
    max_quart = 0
    max_count = -1
    for key in quarts_dict.keys():
        if (len(quarts_dict[key]) > max_count):
            max_count = len(quarts_dict[key])
            max_quart = key

    # поиск медианного угла в четверти
    max_quart_agles = quarts_dict[max_quart]
    # Здесь сортировать по произведению или же только по углу??
    max_quart_agles.sort(key=lambda x: x[0])
    median_len = len(max_quart_agles)
    if (median_len % 2 == 0):
        i : int = median_len // 2 - 1
        angle_1, f_pr_1, z_pr_1 = max_quart_agles[i]
        i = median_len // 2
        angle_2, f_pr_2, z_pr_2 = max_quart_agles[i]
        result = (angle_1 * f_pr_1 * z_pr_1 + angle_2 * f_pr_2 * z_pr_2) / (f_pr_1 * z_pr_1 + f_pr_2 * z_pr_2)
    else:
        angle, f_pr, z_pr = max_quart_agles[median_len // 2]
        result = angle
    return -result, main_vector

def filter_vectors_for_mesh(bm: BMesh, face_to_vector_dict: dict, len_coeff: float, layer_name: str, zone_to_priority_dict: dict, filter_params: List[int]):
    '''
    Функция фильтрует каждую грань меша, получая усредненный угол (на основе значений базовых углов данной грани и смежных граней)
    Затем ищет точки для вектора под таким углом для этой грани
    Записывает вектора в словарь face_id: (p, q)
    '''
    # TODO: добавить параметры фильтра
    # TODO: настроить приоритеты в меше самом!

    faces_to_vector_new_dict = {}

    for key in face_to_vector_dict.keys():
        # считываем базовые угол, посчитанный заранее
        p_basic, q_basic, loop_start_id = face_to_vector_dict[key]
        for loop in bm.faces[key].loops:
            if loop.index == loop_start_id:
                loop_start = loop

        # подсчет нового угла с помощью фильтра для грани с id = key
        
        # ВОТ ТУТ ФИЛЬТР (мб передавать его как параметр)
        angle, basic_vector = filter_face_with_vectors(bm, bm.faces[key], face_to_vector_dict, filter_params, layer_name, zone_to_priority_dict)
  #      angle, basic_vector = filter_face_median_smart(bm, bm.faces[key], face_to_vector_dict, filter_params, layer_name, zone_to_priority_dict)

        #angle, ring_edge_loop = face_to_angle_dict[key]
        #angle = -math.radians(45.0)

        # поворот базового вектора на вычисленный угол
        p, q = count_UV_verts_in_face_with_angle_around_basic_vector(bm, loop_start, angle, len_coeff, basic_vector)
        
        # запись в словарь face_id : (p, q)
        faces_to_vector_new_dict[key] = (p, q, loop_start_id)

    return faces_to_vector_new_dict

def filter_vectors_for_mesh_median_only_thin_rings(bm: BMesh, face_to_vector_dict: dict, len_coeff: float, layer_name: str, zone_to_priority_dict: dict, filter_params: List[int], list_of_results):
    '''
    Функция фильтрует каждую грань меша, получая усредненный угол (на основе значений базовых углов данной грани и смежных граней)
    Затем ищет точки для вектора под таким углом для этой грани
    Записывает вектора в словарь face_id: (p, q)
    '''
    faces_to_vector_new_dict = {}

    for result in list_of_results:
        # медианный фильтр применяем только к полосам/одиночным граням
        if (len(result) != 1):
            continue

        # разворачиваем результат обхода одиночной грани/полосы
        faces, loops, idx_change_dir = result[0]

        # фильтруем
        i = 0
        for face in faces:

            # TODO: краевые грани обрабатывать или нет?

            face_id = face.index
            loop_start = loops[i]
            p_basic, q_basic, loop_start_id = face_to_vector_dict[face_id]

             # ФИЛЬТР
            #angle, basic_vector = filter_face_median(bm, face, face_to_vector_dict, filter_params, layer_name, zone_to_priority_dict)
            angle, basic_vector = filter_face_median_smart(bm, face, face_to_vector_dict, filter_params, layer_name, zone_to_priority_dict)

            # поворот базового вектора на вычисленный угол
            p, q = count_UV_verts_in_face_with_angle_around_basic_vector(bm, loop_start, angle, len_coeff, basic_vector)
        
            faces_to_vector_new_dict[face_id] = (p, q, loop_start_id)
            
            i += 1

    # дописываем в словарь базовые вектора граней, которые не затронул медианный фильтр
    for key in face_to_vector_dict.keys():
        if key not in faces_to_vector_new_dict:
            faces_to_vector_new_dict[key] = face_to_vector_dict[key]

    return faces_to_vector_new_dict

##########################################################################################################################################################
# -- функции записи промежуточных данных в файл
import json


def write_edge_grid(edge_grid: List[BMEdge], file_name: str):
    return

def read_edge_grid(file_name: str):
    return

def write_result_collecting_rings(list_of_results, file_name: str):
    # сериализация BMloop и BMFace до индексов
    list_serialized = []
    for result in list_of_results:
        result_serialized = []
        for edge_ring in result:
            #print(len(edge_ring))
            faces, loops, idx_change_dir = edge_ring
            result_serialized.append(([face.index for face in faces], [loop.index for loop in loops], idx_change_dir))
        list_serialized.append(result_serialized)

    with open(file_name, 'w') as f:
        f.write(json.dumps(list_serialized))
    return

def write_only_concentric_result_collecting_rings(concentric_results, file_name: str):
    
    formatted_concentris_result = []
    # сериализация BMloop и BMFace до индексов
    for result in concentric_results:
        result_no_four_element = []
        for edge_ring in result:
            faces, loops, idx_change_dir, not_quads = edge_ring
            result_no_four_element.append(([face.index for face in faces], [loop.index for loop in loops], idx_change_dir))
        formatted_concentris_result.append(result_no_four_element)

    with open(file_name, 'w') as f:
        f.write(json.dumps(formatted_concentris_result))
    return

def read_result_collecting_ring(file_name: str, bm: BMesh):
    '''
    Функция считывает из файла результаты сборов перпендикулярных колец, где записаны индексы граней и луп вместо их как классов BMface, BMloop.
    Затем она находит в меше грани и лупы по индексам и составляет список результатов, в котором участвуют уже они вместо индексов.
    '''
    
    bm.faces.ensure_lookup_table()
    list_of_results: List[Tuple[List[BMFace], List[BMLoop], int]] = []
    with open(file_name) as f:
        list_serialized = json.load(f)
    for result_serialized in list_serialized:
        result = []
        for edge_ring in result_serialized:
            faces_s, loops_s, idx_change_dir = edge_ring
            
            faces = []
            for face_id in faces_s:
                faces.append(bm.faces[face_id])

            loops = []
            for i in range(0, len(faces)):
                loop_id = loops_s[i]
                for loop in faces[i].loops:
                    if loop.index == loop_id:
                        loops.append(loop)
                        break

            result.append((faces, loops, idx_change_dir))
        list_of_results.append(result)
    return list_of_results

def write_zones_dict(zones_dict: dict, file_name: str):
    with open(file_name, 'w') as f:
        f.write(json.dumps(zones_dict))
    return

def read_zones_dict(file_name: str):
    with open(file_name) as f:
        zones_dict_serialized = json.load(f)
    zones_dict = {}
    for key in zones_dict_serialized.keys():
        zones_dict[int(key)] = zones_dict_serialized[key]
    return zones_dict

# TODO: сделать такую же функцию для хранения базовых векторов
def write_face_to_vector_dict(face_to_vector_dict: dict, file_name: str):
    
    dict_serialized = {}
    for key in face_to_vector_dict.keys():
        p, q, loop = face_to_vector_dict[key]
        json_p = json.dumps(p, default=lambda o: list(o))
        json_q = json.dumps(q, default=lambda o: list(o))
        #json_loop = json.dumps(loop, default=lambda o: o.__dict__, indent=4)
        dict_serialized[key] = (json_p, json_q, loop)
    with open(file_name, 'w') as f:
        #f.write(json.dumps(face_to_vector_dict))
        f.write(json.dumps(dict_serialized))
    return

def read_face_to_vector_dict(file_name: str):
    '''
    предполагается, что в файле записан словарь face_id: (p, q, main_loop)
    '''
    with open(file_name) as f:
        #faces_to_vector_dict = json.load(f)
        dict_serialized = json.load(f)
    faces_to_vector_dict = {    }
    for key in dict_serialized.keys():
        json_p, json_q, loop = dict_serialized[key]
        #p = Vector(**json.loads(json_p))
        #q = Vector(**json.loads(json_q))
        #loop = BMLoop(**json.loads(json_loop))
        p = Vector(json.loads(json_p))
        q = Vector(json.loads(json_q))
        faces_to_vector_dict[int(key)] = (p, q, int(loop))
    return faces_to_vector_dict

def update_face_to_vector_dict_from_mesh(vector_bm: BMesh, bm: BMesh, face_to_vector_dict: dict, file_name: str):
    # посчитать центры граней в UV!
    uv_layer = bm.loops.layers.uv.verify()

    face_to_center_dict = {}
    for face in bm.faces:
        center = Vector((0, 0))
        for loop in face.loops:
            # сумма векторов всех точек грани в uv координатах
            center += loop[uv_layer].uv
    
        center /= 4
        #center = face.calc_center_median()
        face_to_center_dict[face.index] = center
    
    # посчитать центры векторов (они уже в UV)
    #face_to_edge = {}
    #face_to_vector_dict = {}
    keys_list: List[int] = face_to_vector_dict.keys()
    faces_id_set = set(keys_list)
    for edge in vector_bm.edges:
        verts = edge.verts
        edge_v_1 = verts[0].co
        edge_v_2 = verts[1].co
        v_1_uv = Vector((edge_v_1.x, edge_v_1.y))
        v_2_uv = Vector((edge_v_2.x, edge_v_2.y))
        center = (v_1_uv + v_2_uv) / 2
        # сопоставить
        for face_id in face_to_center_dict.keys():
            current_center = face_to_center_dict[face_id]
            # ПАРАМЕТР ТОЧНОСТИ
            rel_tol = 1e-4
            x_close = math.isclose(center.x, current_center.x, rel_tol=rel_tol)
            y_close = math.isclose(center.y, current_center.y, rel_tol=rel_tol)
            if x_close and y_close:
                faces_id_set.remove(face_id)
                #face_to_edge[face_id] = edge.index
                prev = face_to_vector_dict[face_id]
                face_to_vector_dict[face_id] = (v_1_uv, v_2_uv, prev[2])
                break
    
    # обновить файл (нужно ли??)
#    write_face_to_vector_dict(face_to_vector_dict, file_name)
    assert(len(faces_id_set) == 0)
    return face_to_vector_dict
##########################################################################################################################################################

def make_vectormesh(index: int):
    # -- создание vectormesh и построение точек
    # TODO настроить параметры и т д
    vectormesh_name = VECTORMESH_OBJ_NAME_BASE
    vectormesh_col_name = VECTORMESH_COL_NAME
    # создаем объект, меш, привязываем к коллекции, все пустое.
    # это - будущий накопитель для кривых-петель-штрихов.
    vectormesh_obj = make_new_obj_with_empty_mesh_with_unique_name_in_scene(vectormesh_name + str(index), vectormesh_col_name)
    vector_mesh = vectormesh_obj.data
    # создает bmesh для него чтобы можно было добавлять точки.
    vector_bm = bmesh.new()
    vector_bm.from_mesh(vector_mesh)

    return vector_bm, vectormesh_obj

def main_make_pole_grid_and_basic_vectors():
    #--- EDIT MODE!
    mesh_obj = bpy.context.active_object
    bm = bmesh.from_edit_mesh(mesh_obj.data)
    bm.faces.ensure_lookup_table()
  #  for face in bm.faces:
  #      if face.select:
  #          print(face.index)
  #  return

    # сетка полюсов, обход концентров
    face_zones_layer_name = "zones_layer"
    grid_edges, visited_faces_id, zones_dict, concentric_result = get_grid_by_poles_with_outlines_handling_and_concentric_priority(bm)
    for edge in grid_edges:
        edge.select = True
    
    # базовые векторы для всего меша
    faces_to_vector_dict, list_of_results = make_basic_vectors_for_all_grid(bm, grid_edges, visited_faces_id, face_zones_layer_name, zones_dict, concentric_result)
    
    # постройка векторов
    vector_bm, vector_obj = make_vectormesh()
    make_vectors_from_dict(faces_to_vector_dict, vector_bm)

    # запись в файл результатов обхода концентров и не концентров
    results_file_name = "rings_collecting_results.json"
    write_result_collecting_rings(list_of_results, concentric_result, results_file_name)
    # запись словаря векторов в файл
    file_name = "face_to_vector_dict.json"
    write_face_to_vector_dict(faces_to_vector_dict, file_name)
    # запись результатов обхода в файл: сетка полюсов, кольца ребер, словарь зон
    zd_file_name = "zones_dict.json"
    write_zones_dict(zones_dict, zd_file_name)

    # чистка
    vector_bm.to_mesh(vector_obj.data)
    vector_obj.data.update()
    vector_bm.free()
    bmesh.update_edit_mesh(mesh_obj.data)
    bm.free()

    return

def main_filter_vectors_from_file():
    #--- EDIT MODE!
    mesh_obj = bpy.context.active_object
    bm = bmesh.from_edit_mesh(mesh_obj.data)
    bm.faces.ensure_lookup_table()
 #   for face in bm.faces:
 #       if face.select:
 #           print(face.index)
 #           if edge.index == 1:
 #               print(face.index)
  #  return
   # loops = bm.loops
   # loops_0 = bm.loops[0]

    name = "VectorMesh_0"
    if name in bpy.data.meshes:
        vector_mesh = bpy.data.meshes[name]
    vector_bm = bmesh.new()
    vector_bm.from_mesh(vector_mesh)

    # достать словарь векторов из файла
    file_name = "face_to_vector_dict.json"
    faces_to_vector_dict = read_face_to_vector_dict(file_name)

    # апдейт с меша либо нет
    faces_to_vector_dict = update_face_to_vector_dict_from_mesh(vector_bm, bm, faces_to_vector_dict, file_name)

    # достать словарь зон из файла
    zd_file_name = "zones_dict.json"
    face_zones_layer_name = "zones_layer"
    zones_dict = read_zones_dict(zd_file_name)

    # фильтр медианный
    # -- достать результаты сбора перпендикулярных колец из файла
    results_file_name = "rings_collecting_results.json"
    list_of_results = read_result_collecting_ring(results_file_name, bm)
    # -- применить медианный фильтр
    median_filter_params = [1000, 0.1]
    len_coeff = 0.8
    faces_to_vector_dict = filter_vectors_for_mesh_median_only_thin_rings(bm, faces_to_vector_dict, len_coeff, face_zones_layer_name, zones_dict, median_filter_params, list_of_results)
    #faces_to_vector_dict = filter_vectors_for_mesh(bm, faces_to_vector_dict, len_coeff, face_zones_layer_name, zones_dict, median_filter_params)


    # фильтры векторные
    len_coeff = 0.8
    #filter_params = [1000, 0.1, 0.02, 0.02, 0.01]
    filter_params = [1000, 0.1]
  #  faces_to_vector_dict = filter_vectors_for_mesh(bm, faces_to_vector_dict, len_coeff, face_zones_layer_name, zones_dict, filter_params)
    

    # постройка
    vector_bm, vector_obj = make_vectormesh()
    make_vectors_from_dict(faces_to_vector_dict, vector_bm)

    # запись в файл
    write_face_to_vector_dict(faces_to_vector_dict, file_name)

    # чистка
    vector_bm.to_mesh(vector_obj.data)
    vector_obj.data.update()
    vector_bm.free()
    bmesh.update_edit_mesh(mesh_obj.data)
    bm.free()
    return

def isclose(angle1, angle2, rel_tol):
    diff = abs(angle1 - angle2)
    return diff < rel_tol

def get_last_strokemesh_index(last_col_name: str):
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

#############################################################################################################################################
#-- функции для симметрии

# вызывать для второй половины ИЗОЛИРОВАННОЙ
def loops_for_loop_by_edge_nocross_for_symmetry(list_orto_rings: List[Tuple[List[BMFace], List[BMLoop], int]], symm_dict: dict, bm: BMesh):
    '''
    Функция, которая выдает результат как loops_for_loop_by_edge_nocross
    Эта функция не вызывает алгоритм сбора перпендикулярных колец, а отображает готовый результат вызова для одной области
    Функция работает только с симметрией по оХ
    Не учитывает и не записывает отображенные грани в посещенные! Просто создает симметричный набор для process_uv_....
    '''
    symm_list_orto_rings: List[Tuple[List[BMFace], List[BMLoop], int]] = []
    for idx, item in enumerate(list_orto_rings):
        (faces_in_loop, loops, change_direction_face) = item
        symm_face_ring = make_symmetrical_face_list(faces_in_loop, bm, symm_dict)
        symm_loop_ring = make_symmetrical_loop_list(symm_face_ring, change_direction_face, len(loops))
        symm_list_orto_rings.append([symm_face_ring, symm_loop_ring, change_direction_face])
    return symm_list_orto_rings

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

# вызывать для второй половины ИЗОЛИРОВАННОЙ
def loops_for_loop_by_edge_nocross_for_symmetry(list_orto_rings: List[Tuple[List[BMFace], List[BMLoop], int]], symm_dict: dict, bm: BMesh):
    '''
    Функция, которая выдает результат как loops_for_loop
    Эта функция не вызывает алгоритм сбора перпендикулярных колец, а отображает готовый результат вызова для одной области
    Функция работает только с симметрией по оХ
    Не учитывает и не записывает отображенные грани в посещенные! Просто создает симметричный result
    '''
    symm_list_orto_rings: List[Tuple[List[BMFace], List[BMLoop], int]] = []
    for idx, item in enumerate(list_orto_rings):
        (faces_in_loop, loops, change_direction_face) = item
        symm_face_ring = make_symmetrical_face_list(faces_in_loop, bm, symm_dict)
        symm_loop_ring = make_symmetrical_loop_list(symm_face_ring, change_direction_face, len(loops))
        symm_list_orto_rings.append([symm_face_ring, symm_loop_ring, change_direction_face])
    return symm_list_orto_rings

##############################################################################################################################################
##############################################################################################################################################
##############################################################################################################################################

import os

def delete_not_existing_meshes_files():
    directory = os.fsencode("/")
    vectormesh_names = [object.name for object in bpy.data.collections[VECTORMESH_COL_NAME].objects]

    files_to_delte = []
    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        file_contains_some_existing_name = False
        for name in vectormesh_names:
            if filename.startswith(name): 
                # print(os.path.join(directory, filename))
                file_contains_some_existing_name = True
                break
        if (not file_contains_some_existing_name):
            files_to_delte.append(filename)
    
    for name in files_to_delte:
        os.remove(name)

'''
Кнопки:
'''

class OBJECT_PT_GridPoleVectorFilterPanel(Panel):
    bl_label = "GridPole Vectors for strokes"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Curves for Strokes"
    
    def draw(self, context):
        layout = self.layout
        props = context.object.polegrid_vector_props
        
        col = layout.column()
        col.label(text="1. Pole Grid")
        box = col.box()
        
       # box.prop(props, "use_symmetry_polegrid")
        box.prop(props, "use_edge_borders")
        # TODO: сделать их доступными только если полгрид уже существует
        box_operators = box.column()
        box_operators_col_1 = box_operators.column()
        box_operators_col_1.operator('object.show_polegrid')
        box_operators_col_2 = box_operators.column()
        box_operators_col_2.operator('object.add_edge_border_to_current_polegrid')
   #     box_operators.enabled = props.use_edge_borders # TODO OOOOOO
       # box_operators_col_2.enabled = props.use_edge_borders

        col.operator('object.polegrid')
        ###############################

        col = layout.column()
        col.label(text="2. Base vectors orientation")
        box = col.box()
        box.prop(props, "use_symmetry_collect_rings")
        col = box.column()
        col.prop(props, "side_for_symmetry")
        col.enabled = props.use_symmetry_collect_rings


        box.operator('object.collect_rings_in_gridpole')

        ##################################
        
        col = layout.column()
        col.label(text="3. Filter vectors")
        box = col.box()
        box.prop(props, "filter_input")
        box.prop(props, "filter_type")
        box = box.box()
       # box.label(text="filter params")
        box.prop(props, "filter_params")
        box.prop(props, "len_coeff")

        col.operator('object.filter_vectors')     
    

# параметры для панели и для оператора (которые в функцию передаются)

BASE_VECTORS_INPUT_NAME = "Base vectors"
BASE_VECTORS_INPUT_ID = "0"

class PoleGridVectorsProps(PropertyGroup):
    
    def get_filter_type(self, context):
        type = [("0", "Median", ""), ("1", "Smooth", ""), ("2", "Median+Smooth", "")]
        return type
    def get_filter_input(self, context):
        vectormesh_names = [object.name for object in bpy.data.collections[VECTORMESH_COL_NAME].objects]
        input = [(BASE_VECTORS_INPUT_ID, BASE_VECTORS_INPUT_NAME, "")]
        i = 1
        for name in vectormesh_names:
            input.append((name, name, ""))
            i += 1
        return input

    use_symmetry_polegrid : BoolProperty(
        name = "Symmetrical",
        default = False
    )
    use_edge_borders : BoolProperty(
        name = "Use borders",
        default = False
    )
    side_for_symmetry: EnumProperty(
        name = "Side for symmetry",
        items=[("0", "Left", ""),("1", "Right", "")],
        default = 0
    )
    use_symmetry_collect_rings : BoolProperty(
        name = "Symmetrical",
        default = False
    )
    filter_input : EnumProperty(
        name = "Input for filter",
        items=get_filter_input,
        default = 0
    )
    filter_type : EnumProperty(
        name = "Filter type",
        items=get_filter_type,
        default = 2
    )
    filter_params : FloatVectorProperty(
        name = "Filter radius priority",
        subtype="TRANSLATION"
        #default = []
    )
    len_coeff : FloatProperty(
        name = "Vector length",
        default = 0.0002,
        min = 0.0001,
        soft_max = 1,
        subtype = 'FACTOR'
        
    )
# названия файлов данных
CONCENTRIC_RESULT_FILENAME_BASE: str = "_concentric_result.json"
NON_CONCENTRIC_RESULT_FILENAME_BASE: str = "_non_concentric_result.json"
ZONE_TO_PRIORITY_DICT_BASE: str = "_zones_dicts.json"
LAYER_NAME_EDGE_IS_BORDER = "is_border_edge"
POLEGRID_LAYER_NAME = "polegrid_layer"
FACE_TO_ZONE_LAYER_NAME = "zones_layer"
BASE_VECTORS_FILENAME_BASE: str = "_base_vectors.json"
FILTERED_VECTORS_FILENAME_BASE: str = "_filtered_vectors.json"
VECTORMESH_COL_NAME: str = "VectorMeshes"
VECTORMESH_OBJ_NAME_BASE: str = "VectorMesh_"
SYMMETRY_DICT_FILE_NAME_BASE: str = "_symm_dict.json"

# оператор, т. е. вызов функции. Здесь вся логика
class PoleGridCreator(Operator):
    '''
    Для выбранного объекта (в EDIT MODE) создает сетку полюсов.
    Попутно делает разметку зон и сбор колец для концентрических областей.

    Разметка зон (zone_dict) и результат обхода концентрических зон сохраняются в соответствующие файлы данных.
    Сетка сохарняется в слой ребер.
    '''
    
    bl_idname = 'object.polegrid'
    bl_label = 'Create polegrid'
    
    # params
    use_symmetry = None
    use_edge_borders = None
    
    def get_params(self, context):
        props = context.object.polegrid_vector_props 
        self.use_symmetry = props.use_symmetry_polegrid
        self.use_edge_borders = props.use_edge_borders

    # собственно функция!
    def create_polegrid(self):

        #--- EDIT MODE!
        mesh_obj = bpy.context.active_object
        bm = bmesh.from_edit_mesh(mesh_obj.data)
        bm.faces.ensure_lookup_table()
  #  for face in bm.faces:
  #      if face.select:
  #          print(face.index)
  #  return
        edge_borders = []
        if self.use_edge_borders: # достаем из слоя ребра ручных границ
            edge_border_id = get_edges_from_edge_border_layer(bm, LAYER_NAME_EDGE_IS_BORDER)
            edge_borders = [bm.edges[id] for id in edge_border_id]

        # сетка полюсов, обход концентров
        delete_faces_from_zone_layer(bm, FACE_TO_ZONE_LAYER_NAME, bm.faces)  # очистка разметки
        grid_edges, visited_faces_id, zones_dict, concentric_result = get_grid_by_poles_with_outlines_handling_and_concentric_priority(bm, edge_borders) # новая разметка
        
        for edge in grid_edges:
            edge.select = True

        # запись в файлы данных
        file_name_concentric = mesh_obj.name + CONCENTRIC_RESULT_FILENAME_BASE
        write_only_concentric_result_collecting_rings(concentric_result, file_name_concentric)
        file_name_zone_dict = mesh_obj.name + ZONE_TO_PRIORITY_DICT_BASE
        write_zones_dict(zones_dict, file_name_zone_dict)

        # разметка слоя ребер. Очищаем слой полностью + записываем новую посчитанную сетку
        delete_edges_from_polegrid_layer(bm,POLEGRID_LAYER_NAME, bm.edges) # очищаем старый результат
        grid_edges_id = [edge.index for edge in grid_edges]
        write_edges_to_polegrid_layer(bm, POLEGRID_LAYER_NAME, grid_edges_id)

        bmesh.update_edit_mesh(mesh_obj.data)
        bm.free()

        return
    
    def execute(self, context):
       # raise NotImplementedError
        self.get_params(context)
        
        # вызываем все нужные функции
        self.create_polegrid()
        
        return {'FINISHED'}
    
class ShowPoleGridHandler(Operator):
    '''
    Выберает все ребра, относящиеся к polegrid
    '''
    
    bl_idname = 'object.show_polegrid'
    bl_label = 'Show polegrid'
    
    def read_and_select_polegrid(self, context):

         #--- EDIT MODE!
        mesh_obj = bpy.context.active_object
        bm = bmesh.from_edit_mesh(mesh_obj.data)

        for edge in bm.edges:
            edge.select = False

        show_select_all_edges_from_polegrid_layer(bm, POLEGRID_LAYER_NAME)

        bmesh.update_edit_mesh(mesh_obj.data)
        bm.free()
    
    def execute(self, context):
       # raise NotImplementedError
        
        # вызываем все нужные функции
        self.read_and_select_polegrid(context)
        
        return {'FINISHED'}
    
class AddEdgeBorderToGridPoleHandler(Operator):
    '''
    Вручную добавляет к уже построенной gridpole ребра из selected. (Записывает их в слой)
    Можно вызывать ПОСЛЕ генерации сетки.
    Если до - то не имеет смысла, перед новой генерацией слой очищается.
    '''
    bl_idname = 'object.add_edge_border_to_current_polegrid'
    bl_label = 'Add selected edges to existing polegrid'
    
    def write_selected_edges_to_polegrid_layer(self, context):
       
         #--- EDIT MODE!
        mesh_obj = bpy.context.active_object
        bm = bmesh.from_edit_mesh(mesh_obj.data)

        edges_to_add = []
        for edge in bm.edges:
            if edge.select:
                edges_to_add.append(edge.index)
                edge.select = False

        write_edges_to_polegrid_layer(bm, POLEGRID_LAYER_NAME, edges_to_add)        

        show_select_all_edges_from_polegrid_layer(bm, POLEGRID_LAYER_NAME)
    
    def execute(self, context):
       # raise NotImplementedError
        
        # вызываем все нужные функции
        self.write_selected_edges_to_polegrid_layer(context)
        
        return {'FINISHED'}

class RingsCollector(Operator):
    '''
    Для выбранного объекта (в EDIT MODE) достает gridpole из файла и обходит ее, записывает
    результаты обхода в файл.
    '''
    
    bl_idname = 'object.collect_rings_in_gridpole'
    bl_label = 'Generate base vectors'
    
    # params
    use_symmetry = None
    len_coeff = None
    side_for_symmetry = None
    
    def get_params(self, context):
        props = context.object.polegrid_vector_props 
        self.use_symmetry = props.use_symmetry_collect_rings
        self.len_coeff = props.len_coeff
        self.side_for_symmetry = props.side_for_symmetry
        
    # собственно функция!
    def collect_rings(self, context):       

        #--- EDIT MODE!
        mesh_obj = bpy.context.active_object
        bm = bmesh.from_edit_mesh(mesh_obj.data)

        # достаем сетку и обход концентров из слоя / файла
        grid_edges_id = get_edges_from_polegrid_layer(bm, POLEGRID_LAYER_NAME)
        grid_edges = [bm.edges[id] for id in grid_edges_id]

        file_name_concentric = mesh_obj.name + CONCENTRIC_RESULT_FILENAME_BASE
        concentric_result = read_result_collecting_ring(file_name_concentric, bm)
        
        file_name_zones = mesh_obj.name + ZONE_TO_PRIORITY_DICT_BASE
        zones_dict = read_zones_dict(file_name_zones)

        visited_faces_id = set()
        for result in concentric_result:
            for edge_ring in result:
                faces, loops, idx = edge_ring
                faces_id = [face.index for face in faces]
                visited_faces_id = visited_faces_id.union(faces_id)

        # базовые векторы для всего меша
        symm_file_name = mesh_obj.name + SYMMETRY_DICT_FILE_NAME_BASE
        use_left_side = False
        if (self.side_for_symmetry == "0"):
            use_left_side = True
        faces_to_vector_dict, list_of_results = make_basic_vectors_for_all_grid(bm, grid_edges, visited_faces_id, FACE_TO_ZONE_LAYER_NAME, zones_dict, concentric_result,
                                                                                self.len_coeff, self.use_symmetry, symm_file_name, use_left_side)
    
        # постройка векторов
        vectormesh_index = get_last_strokemesh_index(VECTORMESH_COL_NAME)
        vectormesh_index += 1
        vector_bm, vector_obj = make_vectormesh(vectormesh_index)
        make_vectors_from_dict(faces_to_vector_dict, vector_bm)

        # запись результатов обхода в файл: сетка полюсов, кольца ребер, словарь зон
        # -- запись в файл результатов обхода не концентров
        results_file_name = mesh_obj.name + NON_CONCENTRIC_RESULT_FILENAME_BASE
        write_result_collecting_rings(list_of_results, results_file_name)
        # -- запись словаря векторов в файл
        base_vectors_file_name = mesh_obj.name + BASE_VECTORS_FILENAME_BASE
        write_face_to_vector_dict(faces_to_vector_dict, base_vectors_file_name)
        # -- запись словаря зон в файл
        write_zones_dict(zones_dict, file_name_zones)

        # чистка
        vector_bm.to_mesh(vector_obj.data)
        vector_obj.data.update()
        vector_bm.free()
        bmesh.update_edit_mesh(mesh_obj.data)
        bm.free()

    
    def execute(self, context):
        #raise NotImplementedError
        self.get_params(context)
        
        # вызываем все нужные функции
        self.collect_rings(context)
        
        return {'FINISHED'}
    
class VectorFilter(Operator):
    '''
    Для выбранного объекта (в EDIT MODE) строит вектора и фильтрует.
    Базовые вектора: достает gridpole и collect rings result из файла и при обходе колец строит просто face loop curves.
    Может применять к базовым векторами фильтры на выбор.
    Может сохранять результат фильтрации и применять следующие фильтры уже к нему.
    '''

   # delete_not_existing_meshes_files()
    
    bl_idname = 'object.filter_vectors'
    bl_label = 'Filter vectors'
    
    # params
    filter_input = None
    filter_type = None
    filter_params = None
    len_coeff = None
    
    def get_params(self, context):
        props = context.object.polegrid_vector_props 
        self.filter_input = props.filter_input
        self.filter_type = props.filter_type
        self.filter_params = props.filter_params
        self.len_coeff = props.len_coeff

    # собственно функция!
    def filter_vectors(self): 

        #--- EDIT MODE!
        mesh_obj = bpy.context.active_object
        bm = bmesh.from_edit_mesh(mesh_obj.data)
        bm.faces.ensure_lookup_table()
 #   for face in bm.faces:
 #       if face.select:
 #           print(face.index)
 #           if edge.index == 1:
 #               print(face.index)
  #  return
   # loops = bm.loops
   # loops_0 = bm.loops[0]

        # достать словарь векторов из файла
        if (self.filter_input == BASE_VECTORS_INPUT_ID):
            vectors_file_name = mesh_obj.name + BASE_VECTORS_FILENAME_BASE
        else:
            vectormesh_name = self.filter_input
            vectors_file_name = vectormesh_name + FILTERED_VECTORS_FILENAME_BASE
        faces_to_vector_dict = read_face_to_vector_dict(vectors_file_name)
        
        # достать словарь зон из файла
        zd_file_name = mesh_obj.name + ZONE_TO_PRIORITY_DICT_BASE
        face_zones_layer_name = FACE_TO_ZONE_LAYER_NAME
        zones_dict = read_zones_dict(zd_file_name)

        filter_params: Vector = list(self.filter_params)
        # ФИЛЬТРЫ
        if (self.filter_type != "1"): # либо медианный, либо медианный + обычный
            # -- достать результаты сбора перпендикулярных колец из файла
            results_file_name = mesh_obj.name + NON_CONCENTRIC_RESULT_FILENAME_BASE
            concentric_result_file_name = mesh_obj.name + CONCENTRIC_RESULT_FILENAME_BASE
            list_of_results = read_result_collecting_ring(results_file_name, bm)
            list_of_concentris_results = read_result_collecting_ring(concentric_result_file_name, bm)
            list_of_results.extend(list_of_concentris_results)

            # -- фильтр по одиночным полосам
            faces_to_vector_dict = filter_vectors_for_mesh_median_only_thin_rings(bm, faces_to_vector_dict, self.len_coeff, face_zones_layer_name, zones_dict, filter_params, list_of_results)
            
            if (self.filter_type == "2"): # медианный + обычный
                 faces_to_vector_dict = filter_vectors_for_mesh(bm, faces_to_vector_dict, self.len_coeff, face_zones_layer_name, zones_dict, filter_params)
        else:
            faces_to_vector_dict = filter_vectors_for_mesh(bm, faces_to_vector_dict, self.len_coeff, face_zones_layer_name, zones_dict, filter_params)

        # постройка
        vector_mesh_index = get_last_strokemesh_index(VECTORMESH_COL_NAME)
        vector_mesh_index += 1
        vector_bm, vector_obj = make_vectormesh(vector_mesh_index)
        make_vectors_from_dict(faces_to_vector_dict, vector_bm)

        # запись построенных векторов в файл
        file_name_save = VECTORMESH_OBJ_NAME_BASE + str(vector_mesh_index) + FILTERED_VECTORS_FILENAME_BASE
        write_face_to_vector_dict(faces_to_vector_dict, file_name_save)

        # чистка
        vector_bm.to_mesh(vector_obj.data)
        vector_obj.data.update()
        vector_bm.free()
        bmesh.update_edit_mesh(mesh_obj.data)
        bm.free()
        return      
    
    def execute(self, context):
      #  raise NotImplementedError
        self.get_params(context)
        
        # вызываем все нужные функции
        self.filter_vectors()
        
        return {'FINISHED'}

classes = [
    PoleGridVectorsProps,
    PoleGridCreator,
    RingsCollector,
    ShowPoleGridHandler,
    AddEdgeBorderToGridPoleHandler,
    VectorFilter,
    OBJECT_PT_GridPoleVectorFilterPanel
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
    bpy.types.Object.polegrid_vector_props = PointerProperty(type = PoleGridVectorsProps)
    
    # вызов вручную в скрипте: (потом будет кнопка, а в коде вызывать его не нужно)
    #bpy.ops.object.random_vectors()