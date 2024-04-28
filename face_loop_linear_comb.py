import bpy
import bmesh
from bmesh.types import BMEdge, BMFace, BMLoop, BMesh, BMLayerItem, BMVert
from bpy import context
#from face_loop import get_last_collection_index, get_last_strokemesh_index, get_last_z_coord

from typing import List, Set, Tuple

#####################################################################################################################################
# --- скопировано вместо импорта.
# TODO: починить импорт в блендере

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

#####################################################################################################################################

def is_pole(vert: BMVert):
    '''
    Функция проверяет, является ли данная вершина полюсом
    '''
    return len(vert.link_edges) != 4

def get_edge_flowloop_on_boundary_by_verts_and_bound_edges(start_vert: BMVert, visited_edges: Set[BMEdge]):
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
    verts_in_flowloops = set()
    for pole in poles_verts:
        if (pole.is_boundary):
            for edge in pole.link_edges:
                if (edge.is_boundary):
                    grid_edges.add(edge)
                else:
                    if len(pole.link_edges) > 3:
                        get_edge_flowloop(edge, pole, grid_edges, verts_in_flowloops)
            continue
        for edge in pole.link_edges:
            get_edge_flowloop(edge, pole, grid_edges, verts_in_flowloops)
            #grid_edges.extend(edge_rings)
    not_visited_pole_edges = set()
    for pole in poles_verts:
        for edge in pole.link_edges:
            # проверяем мою теорию
            #assert (edge in grid_edges)
            if (edge not in grid_edges):
                not_visited_pole_edges.add(edge)
    return poles_verts, grid_edges, not_visited_pole_edges

def get_all_edge_boudaries_flowloops(bm: BMesh) -> List[List[BMEdge]]:
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
            flowloop_edges, is_cycled = get_edge_flowloop_on_boundary_by_verts_and_bound_edges(vert, visited_edges)
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

def main():
    #--- EDIT MODE!
    mesh_obj = bpy.context.active_object
    bm = bmesh.from_edit_mesh(mesh_obj.data)

    # получение полюсной сетки
    poles, edges, not_visited = get_grid_by_poles(bm)
    for edge in edges:
        edge.select = True

   # получение краевых границ
   # flowloops = get_all_edge_boudaries_flowloops(bm)
   # for floop in flowloops:
   #     for edge in floop:
   #         edge.select = True

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