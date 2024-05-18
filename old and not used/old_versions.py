from face_loop import *

##################
# --- реализовано: без пересечений, границы и симметрия
# --- не реализовано: автоопределение непосещенных граней


# одна петля без перпендикуляров внутри границ
def test_collect_loop_nocross_inside_borders(MESH_NAME_WITH_IDX: str, Z_STEP: float, COL_NAME: str, Z_COORD_START: int, layer_name: str):
    # --- --- --- --- --- prepare
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

    selected_edges, border_edges_id = read_start_edge_and_ignore_selected_border_edges(bm, layer_name)
    starting_edge: BMEdge = selected_edges[0]
    starting_loop = starting_edge.link_loops[0]

    ####################################

    visited_faces_id = set()
    accessable_faces = get_faces_accessable_from_edge(starting_edge, border_edges_id)
    accessable_faces_id = [face.index for face in accessable_faces]

    # обход с остановкой на посещенных гранях
    (faces_in_loop, edge_ring, idx_change_dir, visited_not_quads) = collect_face_loop_with_recording_visited_not_quads_nocross_concrete_loop_inside_borders(starting_loop, visited_faces_id, accessable_faces_id)
    process_faces_from_loop_with_island_connectivity_em(faces_in_loop, idx_change_dir, Z_STEP * Z_COORD_START, bm, strokes_bm, edge_ring)
    for id in visited_faces_id:
        bm.faces[id].select = True

    #######################################
    # --- --- --- --- --- clean

 #   output_not_visited_faces(bm, visited_faces_id)

    # обновление объекта на экране
    bmesh.update_edit_mesh(mesh_obj.data)
    # обновление point cloud на экране
    strokes_bm.to_mesh(strokes_mesh)
    strokes_obj.data.update()

    # очистка памяти от bm
    bm.free()
    strokes_bm.free()

# вызов одного обхода со сбором перпендикуляров внутри границ, без автозаполнения
def test_loops_for_loop_nocross_inside_borders_with_optional_symmetry(MESH_NAME_BASE: str, INDEX_START: int, Z_STEP: float, COL_NAME: str, Z_COORD_START: int, layer_name: str, with_symmetry: bool):
    # --- --- --- --- --- prepare
     #--- EDIT MODE!
    mesh_obj = bpy.context.active_object
    bm = bmesh.from_edit_mesh(mesh_obj.data)

    if (with_symmetry):
        symm_dict = make_symmetry_dictionary_by_median_similarity(bm)
    else:
        symm_dict = {}

    # создаем объект, меш, привязываем к коллекции, все пустое.
    # это - будущий накопитель для кривых-петель-штрихов.
    #name = MESH_NAME_WITH_IDX
    #strokes_obj = make_new_obj_with_empty_mesh_with_unique_name_in_scene(name, COL_NAME)
    #strokes_mesh = strokes_obj.data
    # создает bmesh для него чтобы можно было добавлять точки.
    #strokes_bm = bmesh.new()
    #strokes_bm.from_mesh(strokes_mesh)

    selected_edges, border_edges_id = read_start_edge_and_ignore_selected_border_edges(bm, layer_name)
    starting_edge: BMEdge = selected_edges[0]
    starting_loop = starting_edge.link_loops[0]

    ####################################
    
    visited_faces_id = set()
    accessable_faces = get_faces_accessable_from_edge(starting_edge, border_edges_id)
    accessable_faces_id = [face.index for face in accessable_faces]

    # горизонтальное кольцо
    #result = loops_for_loop_by_edge_nocross_concrete_loop_inside_border(starting_loop, visited_faces_id, accessable_faces_id)
    # перпендикуляры
    #for idx, item in enumerate(result):
    #    (faces_in_loop, loops, change_direction_face) = item
    #    process_faces_from_loop_with_island_connectivity_em(faces_in_loop, change_direction_face, Z_STEP*Z_COORD_START, bm, strokes_bm, loops)
    #    Z_COORD_START += 1
    
    # Для дебага
    #for id in visited_faces_id:
    #    bm.faces[id].select = True

    (visited_faces_id, index, z_coord) = strokes_nocross_inside_border_with_optional_symmetry(MESH_NAME_BASE, INDEX_START, Z_COORD_START, starting_loop, bm, visited_faces_id, Z_STEP, COL_NAME, accessable_faces_id, with_symmetry, symm_dict)

    #######################################
    # --- --- --- --- --- clean

 #   output_not_visited_faces(bm, visited_faces_id)

    # обновление объекта на экране
    bmesh.update_edit_mesh(mesh_obj.data)
    
    # обновление point cloud на экране
 #   strokes_bm.to_mesh(strokes_mesh)
 #   strokes_obj.data.update()

    # очистка памяти от bm
    bm.free()
 #   strokes_bm.free()

# эта функция возвращает result (всё о кольце с перпендикулярами) специально для последующего вызова ее симметричной версии
# для себя все создает сама и убирает за собой
def strokes_nocross_inside_border_partitial(name: str, index: int, z_coord: int, start_loop: BMLoop, bm: BMesh, visited_faces_id: set, Z_STEP: float, COL_NAME: str, accessable_faces_id: Set[int]):
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
    result = loops_for_loop_by_edge_nocross_concrete_loop_inside_border(start_loop, visited_faces_id, accessable_faces_id)
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

    return visited_faces_id, index, z_coord, result

# специальная версия strokes_nocross для вызова в auto_strokes_nocross_inside_border
# не делает обход, только отображает уже обойденные в strokes_nocross_inside_border грани
# и строит точки в uv
# подготавливает для этого strokemesh
# записывает отраженные грани в visited
# не работает с границами, т к подразумевается, что ее вызывают на корректном результате обычного stroke_mesh и для симметричной половины те же доступные грани
# TODO: запись в посещенные вызывает дополнительный обход списка, а можно было вы в более низкой функции это проделывать на ходу обработки
def strokes_nocross_symmetry_with_visited_recording_partitial(name: str, index: int, z_coord: int, result: List[Tuple[List[BMesh], List[BMLoop], int]], symm_dict: dict, bm: BMesh, visited_faces_id: set, Z_STEP: float, COL_NAME: str):
    '''
    Функция принимает результат вызова обычного strokes_nocross_inside_border,
    отображает грани на симметричные с помощью словаря symm_dict,
    записывет их в посещенные (visited_faces_id) и строит точки и цепи в UV развертке на симметричных гранях

    !!! создает strokemesh отдельный
    !!! предполагается, что эту функцию вызывают в одной функции с обычным strokes_nocross_inside_border
    '''
    # создаем объект, меш, привязываем к коллекции, все пустое. ДЛЯ СИММЕТРИИ
    # это - будущий накопитель для кривых-петель-штрихов.
    strokes_obj_symm = make_new_obj_with_empty_mesh_with_unique_name_in_scene(name + str(index), COL_NAME)
    index += 1
    strokes_mesh_symm = strokes_obj_symm.data
    # создает bmesh для него чтобы можно было добавлять точки.
    strokes_bm_symm = bmesh.new()
    strokes_bm_symm.from_mesh(strokes_mesh_symm)

    # построение СИММЕТРИЧНОГО строкмеша
    list_orto_rings_symm = loops_for_loop_by_edge_nocross_for_symmetry(result, symm_dict, bm)
    for idx, item in enumerate(list_orto_rings_symm):
        (faces_in_loop, loops, change_direction_face) = item
        
        # ЗАПИСЬ В ПОСЕЩЕННЫЕ
        for face in faces_in_loop:
            if (face.index in visited_faces_id):
                print ("Symmetry call on visited faces!")
                assert(True)
            visited_faces_id.add(face.index)
        
        process_faces_from_loop_with_island_connectivity_em(faces_in_loop, change_direction_face, Z_STEP*z_coord, bm, strokes_bm_symm, loops)
        z_coord += 1

    # очистка памяти и обновление СИММЕТРИЧНОГО StrokeMesh на экране
    # обновление point cloud на экране
    strokes_bm_symm.to_mesh(strokes_mesh_symm)
    strokes_obj_symm.data.update()
    strokes_bm_symm.free()

    return visited_faces_id, index, z_coord

def strokes_nocross_inside_border_with_optional_symmetry(name: str, index: int, z_coord: int, start_loop: BMLoop, bm: BMesh, visited_faces_id: set, Z_STEP: float, COL_NAME: str, accessable_faces_id: Set[int], with_symmetry: bool, symm_dict: dict = {}):
    '''
    Версия, которая сама вызывает симметричный обход после обычного обхода, если указано with_symmetry = true
    '''
    # вызов сбора кольца с перпендикулярами
    visited_faces_id, index, z_coord, result = strokes_nocross_inside_border_partitial(name, index, z_coord, start_loop, bm, visited_faces_id, Z_STEP, COL_NAME, accessable_faces_id)

    # вызов симметричного отображения
    if (with_symmetry):
        visited_faces_id, index, z_coord = strokes_nocross_symmetry_with_visited_recording_partitial(name, index, z_coord, result, symm_dict, bm, visited_faces_id, Z_STEP, COL_NAME)

    return visited_faces_id, index, z_coord

def auto_strokes_nocross_inside_borders_with_optional_symmetry(bm: BMesh, start_loop: BMLoop, Z_STEP: float, COL_NAME: str, MESH_NAME_BASE: str, MESH_NAME_IDX_START: int,
                                        Z_COORD_START: int, layer_name: str, border_edges_id: Set[id], accessable_faces_id: Set[int],
                                        with_symmetry: bool, symm_dict: dict = {}):
    '''
    !!!!!! не выбирать граничную грань в качестве стартовой!!
    !!!!!! не выбирать грань на не кваде!!!!

    Функция для построения направляющих по всему мешу
    Начинает с конкретного ребра, далее выбирает случайное ребро среди ребер непосещенных граней
    Запускает сбор перпендикулярных петель, пока не обойдет все вершины (учитываются только квады)
    В базовом случае предлагается в качестве start_loop передавать сюда start_edge.link_loops[0]
    Но может понадобиться более точнее управление
    Каждый раз при выборе следующего ребра проверяет, чтобы ребро не было граничным, и пересчитывает допустимые грани в данной области
    TODO: ситуацию улучшило бы если б мы один раз прошлись по всем граням, запустили там поиск допустимых областей, посчитали допустимые грани в зонах
    записали зону в слой граней и не пересчитывали заново допустимые, а хранили их в списке где-нибудь
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

    (visited_faces_id, index, z_coord) = strokes_nocross_inside_border_with_optional_symmetry(name, index, z_coord, start_loop, bm, visited_faces_id, Z_STEP, COL_NAME, accessable_faces_id, with_symmetry, symm_dict)
    #(visited_faces_id, index, z_coord, result) = strokes_nocross_inside_border_partitial(name, index, z_coord, start_loop, bm, visited_faces_id, Z_STEP, COL_NAME, accessable_faces_id)
    
    not_visited_face_id = not_visited_face_id.difference(visited_faces_id)

   # print("index = " + str(index) + " not_visited: " + str(len(not_visited_face_id)) + "/" + str(count _not_visited_start) + " visited: " + str(len(visited_faces_id)))
   # print("not_visited_id: " + str(not_visited_face_id))


    # пока непосещенные не пусты:
    while len(not_visited_face_id) > 0:
    # выбрать из непосещенных граней одну, взять конкретную лупу / попросить ввести (?)
    # выбор среди не граничных луп!
        loop_next, isolated_face_idx = choose_loop_inside_border(not_visited_face_id, bm, border_edges_id)
        if (loop_next == None):
            not_visited_face_id = not_visited_face_id.difference(set({isolated_face_idx}))
            continue
        accessable_faces = get_faces_accessable_from_edge(loop_next.edge, border_edges_id)
        accessable_faces_id = [face.index for face in accessable_faces]
    # запустить обход из нее
    # построить в отдельный strokemesh нужные вершины и цепь
        (visited_faces_id, index, z_coord) = strokes_nocross_inside_border_with_optional_symmetry(name, index, z_coord, loop_next, bm, visited_faces_id, Z_STEP, COL_NAME, accessable_faces_id, with_symmetry, symm_dict)
        #(visited_faces_id, index, z_coord, result) = strokes_nocross_inside_border_partitial(name, index, z_coord, loop_next, bm, visited_faces_id, Z_STEP, COL_NAME, accessable_faces_id)
    # обновить множество непосещенных граней
        not_visited_face_id = not_visited_face_id.difference(visited_faces_id)


    #    print("index = " + str(index) + " not_visited: " + str(len(not_visited_face_id)) + "/" + str(count_not_visited_start) + " visited: " + str(len(visited_faces_id)))
    print("not_visited_id: " + str(not_visited_face_id))
          
    # -- на данный момент вовне есть функция обхода всех StrokeMesh_i по именам, конвертирующая их в кривые :)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 
    return index, name    

# вызов автозаполнения nocross c конвертацией в кривые
def test_auto_strokes_nocross_inside_borders(Z_STEP: float, COL_NAME: str, MESH_NAME_BASE: str, MESH_NAME_IDX_START: int, Z_COORD_START: int, layer_name: str, with_symmetry: bool):
    #--- EDIT MODE!
    mesh_obj = bpy.context.active_object
    bm = bmesh.from_edit_mesh(mesh_obj.data)

    if (with_symmetry):
        symm_dict = make_symmetry_dictionary_by_median_similarity(bm)
    else:
        symm_dict = {}

    selected_edges, border_edges_id = read_start_edge_and_ignore_selected_border_edges(bm, layer_name)
    starting_edge: BMEdge = selected_edges[0]
    starting_loop = starting_edge.link_loops[0]
    accessable_faces = get_faces_accessable_from_edge(starting_edge, border_edges_id)
    accessable_faces_id = [face.index for face in accessable_faces]

    # автозаполнение c границами
    count, name = auto_strokes_nocross_inside_borders_with_optional_symmetry(bm, starting_loop, Z_STEP, COL_NAME, MESH_NAME_BASE, MESH_NAME_IDX_START, Z_COORD_START, layer_name, border_edges_id, accessable_faces_id, with_symmetry, symm_dict) 

     # обновление объекта на экране
    bmesh.update_edit_mesh(mesh_obj.data)
    # очистка памяти от bm
    bm.free()

# TODO: раскомментить потом!
 #   convert_to_curve_all_strokemesh(name, MESH_NAME_IDX_START, count, mesh_obj)  

 #########################
 # методы для считывания/редактирования границ

# Этот метод НЕ РАБОЧИЙ
# т.к. в vertex grop могут оказаться две вершины одного ребра, а само ребро
# не предполагалось принадлежащим границе. Эту неоднозначность вводом в редакторе никак не решить
def get_boundries_from_vgroups(mesh_obj: Object, bm: BMesh, group_name_base: str):
    '''
    Функция возвращает множество индексов всех ребер, являющихся границей (состоящих из вершин, записанных в какую-либо vertex group)
    Можно переделать так, чтобы было известно, какой именно группе принадлежат ребра
    '''
    #boundries_list: List[set] = [] # boundry = set [edge_id from boundry]
    bound_edges = set()
    bound_verts = []
    #for v in mesh_obj.data.vertices:
        #if len(v.groups) > 0:
    #    for group in v.groups:
    #        if group_name_base in group.name:
    #            bound_verts.append(v.index)
    
    # словарь id -> name для групп с подходящим именем
    # не записываем в него группы, не относящиеся к границам
    id_name_group_dict = {}
    for group in mesh_obj.vertex_groups:
        if (group_name_base in group.name):
            id_name_group_dict[group.index] = group.name
    for vert in mesh_obj.data.vertices:
        vert_groups_id = [i.group for i in vert.groups]
        for group_id in vert_groups_id:
            if group_id in id_name_group_dict:
                bound_verts.append(vert.index)
    #vertexes_from_group = [vert for vert in mesh_obj.data.vertices if mesh_obj.vertex_groups[group_name].index in [i.group for i in vert.groups]]
    for i in range(0, len(bound_verts)):
        for j in range(i + 1, len(bound_verts)):
            edge: BMEdge | None = bm.edges.get((bm.verts[bound_verts[i]], bm.verts[bound_verts[j]]))
            if not (edge is None):
                bound_edges.add(edge.index)
    return bound_edges
#################################
# --- реализовано: без пересечений, симметрия
# --- не реализовано: границы, автоопределение непосещенных граней


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

# одноп остроение перпендикуляров с СИММЕТРИЕЙ
def test_loops_for_loop_by_edge_nocross_for_symmetry(MESH_NAME_BASE: str, MESH_INDEX: int, Z_STEP: float, COL_NAME: str, Z_COORD_START: int):
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
    symm_orto_rings = loops_for_loop_by_edge_nocross_for_symmetry(result, symm_dict, bm)
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

# версия strokes_nocross для вызова СРАЗУ на ДВУХ изолированных половинах симметричной модели последовательно
# TODO: 1) нет записи симметричных граней в посещенные
# TODO: 2) строкмеш и симметричный строкмеш строятся друг за другом. Возможно, лучше было бы в отдельных папках!
def strokes_nocross_for_symmetry(name: str, index: int, z_coord: int, start_loop: BMLoop, bm: BMesh, visited_faces_id: set, Z_STEP: float, COL_NAME: str, symm_dict: dict):
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
    
    # создаем объект, меш, привязываем к коллекции, все пустое. ДЛЯ СИММЕТРИИ
    # это - будущий накопитель для кривых-петель-штрихов.
    strokes_obj_symm = make_new_obj_with_empty_mesh_with_unique_name_in_scene(name + str(index), COL_NAME)
    index += 1
    strokes_mesh_symm = strokes_obj_symm.data
    # создает bmesh для него чтобы можно было добавлять точки.
    strokes_bm_symm = bmesh.new()
    strokes_bm_symm.from_mesh(strokes_mesh_symm)

    # построение СИММЕТРИЧНОГО строкмеша
    list_orto_rings_symm = loops_for_loop_by_edge_nocross_for_symmetry(result, symm_dict, bm)
    for idx, item in enumerate(list_orto_rings_symm):
        (faces_in_loop, loops, change_direction_face) = item
        process_faces_from_loop_with_island_connectivity_em(faces_in_loop, change_direction_face, Z_STEP*z_coord, bm, strokes_bm_symm, loops)
        z_coord += 1



    # TODO: это для дебага в основном
    for id in visited_faces_id:
        bm.faces[id].select = True

    # очистка памяти и обновление StrokeMesh на экране
    # обновление point cloud на экране
    strokes_bm.to_mesh(strokes_mesh)
    strokes_obj.data.update()
    strokes_bm.free()

    # очистка памяти и обновление СИММЕТРИЧНОГО StrokeMesh на экране
    # обновление point cloud на экране
    strokes_bm_symm.to_mesh(strokes_mesh_symm)
    strokes_obj_symm.data.update()
    strokes_bm_symm.free()

    return visited_faces_id, index, z_coord

# версия auto_strokes_nocross для вызова на изолированных половинах симметричной модели
# без запоминания посещений на симметричной половине !!!!!!
# TODO: можно было бы ускорить, если при определенный непосещенных граний избежать вычисление центров и сравнение знака по х!
def auto_strokes_nocross_for_symmetry(bm: BMesh, start_loop: BMLoop, Z_STEP: float, COL_NAME: str, MESH_NAME_BASE: str, MESH_NAME_IDX_START: int, Z_COORD_START: int):
    '''
    Функция для построения направляющих по всему мешу
    Начинает с конкретного ребра, далее выбирает случайное ребро среди ребер непосещенных граней
    Запускает сбор перпендикулярных петель, пока не обойдет все вершины (учитываются только квады)
    В базовом случае предлагается в качестве start_loop передавать сюда start_edge.link_loops[0]
    Но может понадобиться более точнее управление
    '''

    # построение словаря симметричных граней
    symm_dict = make_symmetry_dictionary_by_median_similarity(bm)

    # определение, на какой половине вызывается обход:
    is_positive_x_half = False
    if (start_loop.face.calc_center_median().x > 0):
        is_positive_x_half = True

    # все грани меша = непосещенные
    not_visited_face_id = set() #set([face.index for face in bm.faces])
    # выкинуть не квады и грани из второй половины
    for face in bm.faces:
        if is_quad(face):
            if (is_positive_x_half) and (face.calc_center_median().x > 0):
                not_visited_face_id.add(face.index)
            elif (not is_positive_x_half) and (face.calc_center_median().x < 0):
                not_visited_face_id.add(face.index)

    #count_not_visited_start = len(not_visited_face_id)

    index = MESH_NAME_IDX_START
    z_coord = Z_COORD_START
    name = MESH_NAME_BASE
    visited_faces_id = set()


   # print("index = " + str(index) + " not_visited: " + str(len(not_visited_face_id)) + "/" + str(count_not_visited_start) + " visited: " + str(len(visited_faces_id)))
   # print("not_visited_id: " + str(not_visited_face_id))


    (visited_faces_id, index, z_coord) = strokes_nocross_for_symmetry(name, index, z_coord, start_loop, bm, visited_faces_id, Z_STEP, COL_NAME, symm_dict)
    not_visited_face_id = not_visited_face_id.difference(visited_faces_id)

   # print("index = " + str(index) + " not_visited: " + str(len(not_visited_face_id)) + "/" + str(count_not_visited_start) + " visited: " + str(len(visited_faces_id)))
   # print("not_visited_id: " + str(not_visited_face_id))


    # пока непосещенные не пусты:
    while len(not_visited_face_id) > 0:
    # выбрать из непосещенных граней одну, взять конкретную лупу / попросить ввести (?)
        loop_next = choose_loop(not_visited_face_id, bm)
    # запустить обход из нее
    # построить в отдельный strokemesh нужные вершины и цепь
        (visited_faces_id, index, z_coord) = strokes_nocross_for_symmetry(name, index, z_coord, loop_next, bm, visited_faces_id, Z_STEP, COL_NAME, symm_dict)
    # обновить множество непосещенных граней
        not_visited_face_id = not_visited_face_id.difference(visited_faces_id)


    #    print("index = " + str(index) + " not_visited: " + str(len(not_visited_face_id)) + "/" + str(count_not_visited_start) + " visited: " + str(len(visited_faces_id)))
    #   print("not_visited_id: " + str(not_visited_face_id))                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                

    return index, name

# автозаполнение с СИММЕТРИЕЙ на изолированных половинах одной модели!
def test_auto_stroke_nocross_for_symmetry(Z_STEP: float, COL_NAME: str, MESH_NAME_BASE: str, MESH_NAME_IDX_START: int, Z_COORD_START: int):
    #--- EDIT MODE!
    mesh_obj = bpy.context.active_object
    bm = bmesh.from_edit_mesh(mesh_obj.data)

    # определяемся, с чего начинать. Если есть выбранная - с выбранной, иначе - с некой 0-ой
    selected_edges = [edge for edge in bm.edges if edge.select]
    
    if not selected_edges:
        starting_edge = bm.edges[0]
    else:
        starting_edge = selected_edges[0]
        
    # предположим, что выбрано ребро на квадратной грани, а то в итоге пустая лупа будет!  

    # автозаполнение базовое С СИММЕТРИЕЙ
    count, name = auto_strokes_nocross_for_symmetry(bm, starting_edge.link_loops[0], Z_STEP, COL_NAME, MESH_NAME_BASE, MESH_NAME_IDX_START, Z_COORD_START) 

     # обновление объекта на экране
    bmesh.update_edit_mesh(mesh_obj.data)
    # очистка памяти от bm
    bm.free()

    convert_to_curve_all_strokemesh(name, MESH_NAME_IDX_START, count, mesh_obj)

    #############################################################
    # --- реализовано: без пересечений
    # --- не реализовано: границы, симметрия, автоопределение непосещенных граней

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

    convert_to_curve_all_strokemesh(name, MESH_NAME_IDX_START, count, mesh_obj)  

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

  ###################################################################

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

def add_vertices_made_in_line_with_delta_z(bm: BMesh, vertices: List[Vector], idx_change_dir: int, delta_z: float) -> None:
    '''
    Обертка над add_vertices_made_in_line
    Принимает на вход список 2D точек (!!!!) и сдвиг по z = delta_z, вставляет его в качества z-координаты всем точкам,
    превращая их в 3d точки на одной высоте

    Предназначена для добавления в объект созданной цепи точек, созданной из заданных точек (как и add_vertices_made_in_line)
    '''
    add_vertices_made_in_line(bm, [Vector([v[0], v[1], delta_z]) for v in vertices], idx_change_dir)

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

############################################################################################

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

def main():
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

    ####### без пересечений ########

    # одна петля без перпендикуляров
   # test_collect_loop_nocross(STROKEMESH_NAME_BASE + str(new_strokemesh_idx_start), Z_STEP, new_col_name, new_z_coord)
    # перпендикуляры
   # test_loops_for_loop_nocross(STROKEMESH_NAME_BASE + str(new_strokemesh_idx_start), Z_STEP, new_col_name, new_z_coord)
    # автозаполнение
    #test_auto_strokes_nocross(Z_STEP, new_col_name, STROKEMESH_NAME_BASE, new_strokemesh_idx_start, new_z_coord)

    # вычисление последних параметров создания мешей
    #test_getting_last_indexes()

    ######## с симметрией

    # построение словаря симметричных граней
    #test_make_symmetry_dictionary()

    # перпендикуляры с симметрией (вызывать от изолированной области) без автозаполнения
    #test_loops_for_loop_by_edge_nocross_for_symmetry(STROKEMESH_NAME_BASE, new_strokemesh_idx_start, Z_STEP, new_col_name, new_z_coord)

    # автозаполнение с СИММЕТРИЕЙ для двух изолированных половин одной модели
    #test_auto_stroke_nocross_for_symmetry(Z_STEP, new_col_name, STROKEMESH_NAME_BASE, new_strokemesh_idx_start, new_z_coord)

    ######## внутри границ

    # одна петля без перпендикуляров внутри границ
   # test_collect_loop_nocross_inside_borders(STROKEMESH_NAME_BASE + str(new_strokemesh_idx_start), Z_STEP, new_col_name, new_z_coord, LAYER_NAME_EDGE_IS_BORDER)
    
    # перпендикуляры внутри границ
  #  test_loops_for_loop_nocross_inside_borders_with_optional_symmetry(STROKEMESH_NAME_BASE, new_strokemesh_idx_start, Z_STEP, new_col_name, new_z_coord, LAYER_NAME_EDGE_IS_BORDER, with_symmetry=True)
  
    # автозаполнение с границами
   # test_auto_strokes_nocross_inside_borders(Z_STEP, new_col_name, STROKEMESH_NAME_BASE, new_strokemesh_idx_start, new_z_coord, LAYER_NAME_EDGE_IS_BORDER, with_symmetry = True)
