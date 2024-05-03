import bpy
import bmesh
from bmesh.types import BMEdge, BMFace, BMLoop, BMesh, BMLayerItem, BMVert
from bpy import context
#from face_loop import get_last_collection_index, get_last_strokemesh_index, get_last_z_coord, is_quad

from typing import List, Set, Tuple

# !!! edge flowloop = петля ребер, добавила flow- чтобы не путать петли ребер и механизм BMloop

#####################################################################################################################################
# --- скопировано вместо импорта.
# TODO: починить импорт в блендере

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

#def get_poles_sort_poles_by_edge_count(bm: BMesh):
#    for 

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

    # подготовка для разметки граней модели
    face_zones_layer_name = "zones_layer"
    zones_dict = {} # словарь index_zone: priority
    max_index_negative = 0
    max_index_positive = 0
    default_priority_positive = 1
    default_priority_negative = 2
    prepare_zone_layer(bm, face_zones_layer_name)

    grid_edges: Set[BMEdge] = set()
    # поиск краев
    outlines = get_edges_for_all_outlines(bm)
    # поиск максимальных концентрических колец по краям меша
    visited_faces_id = set()
    for outline in outlines:
        result, visited_faces_id, maximum_ring_outline = find_maximum_concentric_faceloop_around_outline_dense(bm, outline, visited_faces_id)

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

    for edge in grid_edges:
        edge.select = True

def main():
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
    get_grid_by_poles_with_outlines_handling_and_concentric_priority(bm)

    # обновление объекта на экране
    bmesh.update_edit_mesh(mesh_obj.data)
    # очистка памяти от bm
    bm.free()

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