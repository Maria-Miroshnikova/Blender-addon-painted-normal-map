
# alt+S to save changes in blender to have them there!
# to have changes from vs code in blender: click red button in text editor and resolve conflict

import bpy
import bmesh
from bmesh.types import BMEdge, BMFace, BMLoop
from bpy import context

from bpy.types import Mesh, Object, Collection, VertexGroup

from mathutils import Vector
from typing import List, Tuple




##############################################
# функции обхода loop
# не работают на объектах, где лупа не зациклена и не обрамлена не квадами

def is_quad(face: BMFace) -> bool:
    '''
    Функция проверяет, является ли данная грань четырехугольной
    '''
    return (len(face.loops) == 4)

def collect_face_loop(starting_edge: BMEdge) -> List[BMFace]:
    faces_in_loop = []
    #обход в одну сторону
    loop = starting_edge.link_loops[0]

  #  print(loop)
  #  print(loop.link_loop_next.link_loop_next)
  #  print(loop.link_loop_radial_next)
  #  print(loop.link_loop_radial_next.link_loop_next.link_loop_next)


    faces_in_loop_one_direction, was_cycled_loop = loop_go(loop, False)
    faces_in_loop.extend(faces_in_loop_one_direction)
    if (was_cycled_loop):
        return faces_in_loop
    #обход в другую сторону, если не было цикла
    loop = starting_edge.link_loops[0].link_loop_next.link_loop_next
    faces_in_loop_two_direction, was_cycled_loop = loop_go(loop, True)
    faces_in_loop.extend(faces_in_loop_two_direction)
    return faces_in_loop

def loop_go(starting_loop: BMLoop, is_second_go: bool) -> (List[BMFace], bool):
    '''
    Функция обхода face loop (можно переделать в edge ring), начиная с первого ребра для edge ring
    Работает только для квадов, попав на не квад - останавливается
    Сначала идет только в одном направлении
    Возвращает список всех граней, вошедших в face loop
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
    

def make_point_cloud(mesh: Mesh, obj: Object, faces: List[BMFace], iteration: int) -> None:
    '''
    Функция получает на вход набор граней из одной face loop,
    чтобы превратить их в набор точек с общей vertex group и добавить их
    в облако точек (obj, mesh)
    iteration нужна чтобы создавать группу с итерацией в названии
    
    !!! эта функция опирается на то, что все точки добавляются в меш с индексом от
    (последний индекс добавлениия -> длина добавления) и точки в этом диапазоне индексов все
    нужно добавить в одну группу
    '''
    vertices = []
    # сбор центров
    for face in faces:
        vertices.append(face.calc_center_median())
    #print(vertices)
    verts_id_start = len(mesh.vertices)
    # добавление в меш
    vertices_to_pydata(mesh, vertices)
    verts_id_end = verts_id_start + len(vertices) - 1
    # вызов функции создания группы и добавления в группу
    group_name = grouping_vertices(obj, iteration, verts_id_start, verts_id_end)
    
    check_vertexgroup_verts(obj, group_name)

################################


def main():
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
    obj = make_mesh_obj_etc_for_pointcloud(name)
    mesh = obj.data

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
    make_point_cloud(mesh, obj, faces_in_loop, 1)
    
    
    # обновление экрана
    bmesh.update_edit_mesh(mesh_obj.data)
    
    bm.free()
    
if __name__ == "__main__":
    main()
    
# для дебага из vscode....
# может ломать результат в blender    
main()