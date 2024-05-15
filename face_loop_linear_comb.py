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
    !!! При этом остальные грани становятся невыбранными в edit_mode !!!

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

def get_grid_by_poles_with_outlines_handling_and_concentric_priority(bm: BMesh):
    '''
    Функция, которая сначала вызывает сбор краев и поиск концентрических колец по краям,
    размечает концентрические грани, записывает нужные края в число ребер сетки, а затем вызывает сбор сетки по полюсам.
    '''

    # подготовка для разметки граней модели
    face_zones_layer_name = "zones_layer"
    zones_dict = {} # словарь index_zone: priority
    max_index_negative = 0
#    max_index_positive = 0
#    default_priority_positive = 1
    default_priority_negative = 2
    prepare_zone_layer(bm, face_zones_layer_name)

    grid_edges: Set[BMEdge] = set()
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
        # TODO: это верно или нет?????????????????????????????
        # на краях были лупы, поэтому края не нужно обрабатывать отдельно
        for loop in outline:
            grid_edges.add(loop)

    #for index in zones_dict.keys():
    #    show_select_all_faces_from_zone_layer(bm, face_zones_layer_name, index)

    # строим сетку        
    poles_verts, not_visited_pole_edges = get_grid_by_poles_with_preprocessed_grid_edges(bm, grid_edges, face_zones_layer_name)

    #for edge in grid_edges:
    #    edge.select = True

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
def go_all_grid_nonconcentric_areas(bm: BMesh, grid_edges: List[BMEdge], visited_faces_id: Set[int], layer_name: str, zone_priority_dict: dict, faces_to_vector_dict: dict, count_basic_vector_params):
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
                count_basic_vector_params(faces, loops, faces_to_vector_dict, bm)

                # запись в общий результат обхода (для файла)
                list_of_results.append(result)

    print("count of positive zones = " + str(max_index_positive))
    return list_of_results

##############################################################################################################################################
# -- функции построения векторов по обойденным петлям граней

def count_UV_coords_for_two_basic_verts_in_face(loop_start: BMLoop, loop_end: BMLoop, bm: BMesh):
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
    
    min_h = count_minimum_h_from_mass_center(center_co, loop_start.face, uv_layer)
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
    p = center_co + len_coeff * min_h * axis_vector_1
    q = center_co + len_coeff * min_h * axis_vector_2

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

def  count_UV_coords_for_two_basic_verts_all_faces(faces: List[BMFace], loops: List[BMLoop], faces_to_vector_dict: dict, bm: BMesh):
    for loop in loops:
                p, q = count_UV_coords_for_two_basic_verts_in_face(loop, loop.link_loop_next.link_loop_next, bm)
                faces_to_vector_dict[loop.face.index] = (p, q, loop.index)

def make_basic_vectors_for_all_grid(bm: BMesh, grid_edges: List[BMEdge], visited_faces_id, layer_name: str, zones_dict: dict,
                                    concentric_result: List[Tuple[List[BMFace], List[BMLoop], int]]):
    '''
    Функция вызывает обход не концентрических областей и подсчет углов базовых векторов с OX для граней колец,
    а также то же самое в ранее обойденных концентрических областях
    '''

    faces_to_vector_dict = {} # словарь face_id : (p, q, main loop), где p и q - точки на третях средней линии грани -- тестовое
    
    # сбор колец неконцентрических областей и подсчет углов одновременно
    list_of_results = go_all_grid_nonconcentric_areas(bm, grid_edges, visited_faces_id, layer_name, zones_dict, faces_to_vector_dict, count_UV_coords_for_two_basic_verts_all_faces)

    # подсчет углов концентрических областей
    for result in concentric_result:
        for edge_ring in result:
            faces, loops, idx_change_dir, not_quads = edge_ring
            count_UV_coords_for_two_basic_verts_all_faces(faces, loops, faces_to_vector_dict, bm)
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
    queue = []
    queue_faces = set()
    visited_faces = set()
    queue.append((face, depth))
    queue_faces.add(face.index)
    
    main_p, main_q, loop = face_to_vector_dict[face.index]
    main_vector: Vector = main_p - main_q
    
    # 0 - 1 четверть, 1 - 2 четвреть, ...
    #count_angles_in_quarts = [0, 0, 0, 0] # число векторов в координатных четвертях
    quarts_dict = {} # quart: [angles in quart]
    quart_id = []
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
        if (current_depth != 0):
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
    if (face.index == 3) or (face.index == 1):
        print(quarts_dict)
        print("face index: ")
        print(face.index)
        print("result: ")
        print(result)
        print('------------')
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
        #angle, basic_vector = filter_face_with_vectors(bm, bm.faces[key], face_to_vector_dict, filter_params, layer_name, zone_to_priority_dict)
        angle, basic_vector = filter_face_median_smart(bm, bm.faces[key], face_to_vector_dict, filter_params, layer_name, zone_to_priority_dict)

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

def write_result_collecting_rings(list_of_results, concentric_results, file_name: str):
    
   # for result in list_of_results:
   #     for ring in result:
   #         if len(ring) != 3:
   #             print("start face for ring: " + str(ring[0].index))
    # TODO: можно было бы просто не записывать в concentric_loop четвертую компоненту, тогда не нужен этот обход для форматирования
    for result in concentric_results:
        result_no_four_element = []
        for edge_ring in result:
            faces, loops, idx_change_dir, not_quads = edge_ring
            result_no_four_element.append((faces, loops, idx_change_dir))
        list_of_results.append(result_no_four_element)

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

def make_vectormesh():
    # -- создание vectormesh и построение точек
    # TODO настроить параметры и т д
    index = 0
    vectormesh_name = "VectorMesh_"
    vectormesh_col_name = "VectorMeshes"
    # создаем объект, меш, привязываем к коллекции, все пустое.
    # это - будущий накопитель для кривых-петель-штрихов.
    vectormesh_obj = make_new_obj_with_empty_mesh_with_unique_name_in_scene(vectormesh_name + str(index), vectormesh_col_name)
    index += 1
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

def main_old_complex():
    #--- EDIT MODE!
    mesh_obj = bpy.context.active_object
    bm = bmesh.from_edit_mesh(mesh_obj.data)

    # --- получение полюсной сетки
    #poles, edges, not_visited = get_grid_by_poles(bm)
    #for edge in edges:
    #    edge.select = True

   # --- получение краевых границ
   # outlines = get_edges_for_all_outlines(bm)
   # for floop in flowloops:
   #     for edge in floop:
   #         edge.select = True

    # --- поиск максимальных концентрических колец
    #visited_faces_id = set()
    #for outline in outlines:
    #    result, visited_faces_id, maximum_ring_outline = find_maximum_concentric_faceloop_around_outline_dense(bm, outline, visited_faces_id)
    #    for ring_data in result:
    #        faces_in_loop, loops, idx_change_dir, visited_not_quads = ring_data
    #        for face in faces_in_loop:
    #            face.select = True

    #for edge in bm.edges:
    #    if edge.select:
    #        print(edge.index)

    #bm.verts[4218].select = True

   # for face in bm.faces:
   #     if face.select:
   #         print(face.index)
   # return
    
    face_zones_layer_name = "zones_layer"
    grid_edges, visited_faces_id, zones_dict, concentric_result = get_grid_by_poles_with_outlines_handling_and_concentric_priority(bm)
    for edge in grid_edges:
        edge.select = True
    
    #faces_to_angle = make_basic_vectors_for_all_grid(bm, grid_edges, visited_faces_id, face_zones_layer_name, zones_dict, concentric_result)
    faces_to_vector_dict, list_of_results = make_basic_vectors_for_all_grid(bm, grid_edges, visited_faces_id, face_zones_layer_name, zones_dict, concentric_result)
    
    len_coeff = 0.8
    filter_params = [1000, 0.1, 0.02, 0.02, 0.01]
    #faces_to_vector_dict_new = faces_to_vector_dict
    faces_to_vector_dict_new = filter_vectors_for_mesh(bm, faces_to_vector_dict, len_coeff, face_zones_layer_name, zones_dict, filter_params)
    
    # -- создание vectormesh и построение точек
    # TODO настроить параметры и т д
    index = 0
    vectormesh_name = "VectorMesh_"
    vectormesh_col_name = "VectorMeshes"
    # создаем объект, меш, привязываем к коллекции, все пустое.
    # это - будущий накопитель для кривых-петель-штрихов.
    vectormesh_obj = make_new_obj_with_empty_mesh_with_unique_name_in_scene(vectormesh_name + str(index), vectormesh_col_name)
    index += 1
    vector_mesh = vectormesh_obj.data
    # создает bmesh для него чтобы можно было добавлять точки.
    vector_bm = bmesh.new()
    vector_bm.from_mesh(vector_mesh)

    make_vectors_from_dict(faces_to_vector_dict_new, vector_bm)

    # очистка памяти и обновление VectorMesh на экране
    vector_bm.to_mesh(vector_mesh)
    vectormesh_obj.data.update()
    vector_bm.free()

    # -- остальной код

    # обновление объекта на экране
    bmesh.update_edit_mesh(mesh_obj.data)
    # очистка памяти от bm
    bm.free()

def isclose(angle1, angle2, rel_tol):
    diff = abs(angle1 - angle2)
    return diff < rel_tol

####################################################################################################################################################################

def loop_magnitude(loop: BMLoop, uv_layer):
    v1 = loop[uv_layer].uv
    v2 = loop.link_loop_next[uv_layer].uv
    return (v2 - v1).magnitude

def make_points_in_grid_points(min_coeff, next_coeff, min_loop, uv_layer):
    # считаем координаты в UV вершин грани
    min_edge_v_1 = min_loop[uv_layer].uv
    min_edge_v_2 = min_loop.link_loop_next[uv_layer].uv

    min_edge_v_3 = min_loop.link_loop_next.link_loop_next[uv_layer].uv
    min_edge_v_4 = min_loop.link_loop_prev[uv_layer].uv

    points = []
    for i in range (1, min_coeff + 1):
        i_part_of_min_edge = (min_edge_v_1) + (i / (min_coeff + 1)) * (min_edge_v_2 - min_edge_v_1)
        i_part_of_min_edge_opposite = (min_edge_v_4) + (i / (min_coeff + 1)) * (min_edge_v_3 - min_edge_v_4)

        for j in range (1, next_coeff + 1):
            v_ij = i_part_of_min_edge + (j / (next_coeff + 1)) * (i_part_of_min_edge_opposite - i_part_of_min_edge)
            points.append(v_ij)
    return points

def make_points_in_grid_points_for_cells(min_coeff, next_coeff, min_loop, uv_layer):
    # считаем координаты в UV вершин грани
    min_edge_v_1 = min_loop[uv_layer].uv
    min_edge_v_2 = min_loop.link_loop_next[uv_layer].uv

    min_edge_v_3 = min_loop.link_loop_next.link_loop_next[uv_layer].uv
    min_edge_v_4 = min_loop.link_loop_prev[uv_layer].uv

    points = []
    for i in range (0, min_coeff + 1):
        i_part_of_min_edge = (min_edge_v_1) + (i / (min_coeff)) * (min_edge_v_2 - min_edge_v_1)
        i_part_of_min_edge_opposite = (min_edge_v_4) + (i / (min_coeff)) * (min_edge_v_3 - min_edge_v_4)

       # middle_line_i = i+i_part_of_min_edge + i_part_of_min_edge_opposite
        row = []
        for j in range (0, next_coeff + 1):
            v_ij = i_part_of_min_edge + (j / (next_coeff)) * (i_part_of_min_edge_opposite - i_part_of_min_edge)
            #points.append(v_ij)
            row.append(v_ij)
        points.append(row)
    return points

def make_points_in_grid_cells(min_coeff, next_coeff, min_loop, uv_layer):
    # находим координаты узлов сетки
    points_grid = make_points_in_grid_points_for_cells(min_coeff, next_coeff, min_loop, uv_layer)

    points = []
    for i in range(0, min_coeff):
        for j in range(0, next_coeff):
            center = (points_grid[i][j] + points_grid[i + 1][j + 1] + points_grid[i][j + 1] + points_grid[i + 1][j]) / 4
            points.append(center)
    return points


def make_points_proportionally_to_face(face: BMFace, bm: BMesh, min_a: float, face_to_points_dict: dict):
    '''
    Функция для данной грани и минимального размера клетки min_a вычисляет координаты точек внутри грани для построения векторов в них.
    Находится минимум сколько раз min_a помещается в минимальном ребре грани (min_coeff) и в минимальном из боковых ребер грани (next_coeff), затем
    проводится min_coeff средних линий и next_coeff боковых средних линий. В узлах сетки средних линий и есть искомые точки.

    координаты точек записываются в словарь face_id: List[Vectors]

    !!! грань должна быть 4-угольной
    
    '''
    # quart expected
    uv_layer = bm.loops.layers.uv.verify()

    # выбираем минимальное ребро
    #min_edge = None
    min_edge_len = float('inf')
    min_loop = None
    for loop in face.loops:
        e_length = loop_magnitude(loop, uv_layer)
        if e_length < min_edge_len:
            min_edge_len = e_length
            #min_edge = edge
            min_loop = loop
    # выбираем минимальное из боковых ребер
    #next_min_edge = min_loop.link_loop_next.edge
    next_loop = min_loop.link_loop_next
    next_min_len = loop_magnitude(next_loop, uv_layer)
    prev_min_len = loop_magnitude(min_loop.link_loop_prev, uv_layer)
    if (prev_min_len < next_min_len):
        next_min_len = prev_min_len
        #next_min_edge = min_loop.link_loop_prev.edge
        next_loop = min_loop.link_loop_prev

    min_coeff = math.floor(min_edge_len / min_a)
    next_coeff = math.floor(next_min_len / min_a)

    points = make_points_in_grid_cells(min_coeff, next_coeff, min_loop, uv_layer)

   # face_to_points_dict[face.index] = points
    return len(points), points

def make_point_on_face(face: BMFace, bm: BMesh, min_a: float, face_to_points_dict: dict):
    # quart expected
    uv_layer = bm.loops.layers.uv.verify()

    center = Vector((0, 0))
    for loop in face.loops:
        center += loop[uv_layer].uv
    
    center /= 4

    face_to_points_dict[face.index] = [center]
    return

import random

def make_vector_in_point(point: Vector, length: float):

    angle = random.uniform(-90, 90) # RANDOM [-90, 90]

    vector_1 = Vector((0, length / 2))
    vector_2 = Vector((0, length / 2))
    rotation_1 = Matrix.Rotation(angle, 2, 'X')
  #  if angle == 0:
  #      rotation_2 = Matrix.rotate(math.radians(180), 2, 'X')
    rotation_2 = Matrix.Rotation(angle + math.radians(180), 2, 'X')
    vector_1.rotate(rotation_1)
    vector_2.rotate(rotation_2)

    p = point + vector_1
    q = point + vector_2

    return p, q

def generate_random_vectors_on_mash_with_face_area_proportionality(bm: BMesh, vector_bm: BMesh, len_coeff: float, min_a = None):
    '''
    min_a - насколько много точек генерировать в гранях
    len_coeff - насколько длинными делать векторы в этих точках. Минимальная длина будет min_a, модификатор * len_coeff из промежутка (0, +00)
    
    '''
    
    # если минимальный размер не задали, найдем минимальное ребро и возьмем его длину
    if (min_a == None):
        uv_layer = bm.loops.layers.uv.verify()

        min_a = float('inf')
        #for edge in bm.edges:
        #    e_len = edge.calc_length()
        #    if e_len < min_a:
        #        min_a = e_len
        # TODO мб можно все же не копаться на уровне loop а узнать коэффициент масштабирования при переходе к UV?
        # -- скорее всего нет, т. к. разные ребро по-разному сжимаются
        for face in bm.faces:
            for loop in face.loops:
                e_len = loop_magnitude(loop, uv_layer)
                if e_len < min_a:
                    min_a = e_len

    face_to_points_dict = {}

    i = 0
    count = 0
    for face in bm.faces:
        if (is_quad(face)):
            count_local, points = make_points_proportionally_to_face(face, bm, min_a, face_to_points_dict)
            count += count_local

            for point in points:
                p, q = make_vector_in_point(point, len_coeff * min_a)
                create_and_add_vector_to_vectormesh(vector_bm, p, q)

            #make_point_on_face(face, bm, min_a, face_to_points_dict)
            if (i % 10 == 0):
                print("made " + str(i) + "/" + str(len(bm.faces)) + ", points created: " + str(count))
            i += 1
    print("Done with calculation 1")
    return
    print("------------------------------")
    i = 0
    for id in face_to_points_dict.keys():
        points = face_to_points_dict[id]
        for point in points:
            p, q = make_vector_in_point(point, len_coeff * min_a)
            create_and_add_vector_to_vectormesh(vector_bm, p, q)
        if (i % 40 == 0):
                print("create " + str(i) + "/" + str(count))
        i += len(points)
    print("Done with creation 2")
    return

def main_random_vectors():
     #--- EDIT MODE!
    mesh_obj = bpy.context.active_object
    bm = bmesh.from_edit_mesh(mesh_obj.data)

     # постройка векторов
    vector_bm, vector_obj = make_vectormesh()
    len_coeff = 1
   # min_a = 0.4
   # generate_random_vectors_on_mash_with_face_area_proportionality(bm, vector_bm, len_coeff, min_a)
    generate_random_vectors_on_mash_with_face_area_proportionality(bm, vector_bm, len_coeff)


    # чистка
    vector_bm.to_mesh(vector_obj.data)
    vector_obj.data.update()
    vector_bm.free()
    bmesh.update_edit_mesh(mesh_obj.data)
    bm.free()

def main():             
  #  main_make_pole_grid_and_basic_vectors()
  #  main_filter_vectors_from_file()
  main_random_vectors()

def main_with_params():
    ######## главные параметры для создания строкмешей!
    COLLECTION_NAME_BASE = "TestCol_"
    STROKEMESH_NAME_BASE = "StrokesMesh_"
    Z_STEP = 0.1
    LAYER_NAME_EDGE_IS_BORDER = "is_border_edge"
    STROKEMESH_LAYERS_FILE_NAME = "strokemesh_layers.json"

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

    #------- 



   # test_learn_something()

if __name__ == "__main__":
    main()