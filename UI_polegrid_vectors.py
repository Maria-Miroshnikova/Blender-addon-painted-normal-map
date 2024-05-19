import bpy
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import FloatProperty, StringProperty, EnumProperty, PointerProperty, BoolProperty, FloatVectorProperty
from bpy.utils import register_class, unregister_class
import random

##############################################################################################################################################
# -- скопированное

import bmesh
from bmesh.types import BMEdge, BMFace, BMLoop, BMesh, BMLayerItem, BMVert


##############################################################################################################################################
##############################################################################################################################################
##############################################################################################################################################

'''
Кнопки:
    - выбор объекта uv_obj -> OBJECT
    - размер сетки step (min_a в алгоритме) -> FLOAT (default =)
    - длина векторов vector_size (len_coeff в алгоритме) -> FLOAT (default = 0.02)
    (они должни быть близки к 0, но можно для визуализации делать их длиннее)
    - отклонение от узлов сетки distortion -> FLOAT (default = 0, soft_max = vector_size) 
    - кнопка оператора
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
        
        box.prop(props, "use_symmetry_polegrid")
        box.prop(props, "use_edge_borders")
        # TODO: сделать их доступными только если полгрид уже существует
        box_operators = box.column()
        box_operators_col_1 = box_operators.column()
        box_operators_col_1.operator('object.show_polegrid')
        box_operators_col_2 = box_operators.column()
        box_operators_col_2.operator('object.add_edge_border_to_current_polegrid')
   #     box_operators.enabled = props.use_edge_borders # TODO OOOOOO
        box_operators_col_2.enabled = props.use_edge_borders

        col.operator('object.polegrid')
        ###############################

        col = layout.column()
        col.label(text="2. Base vectors orientation")
        box = col.box()
        box.prop(props, "use_symmetry_collect_rings")
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

        col.operator('object.filter_vectors')     
    

# параметры для панели и для оператора (которые в функцию передаются)
class PoleGridVectorsProps(PropertyGroup):
    
    use_symmetry_polegrid : BoolProperty(
        name = "Symmetrical",
        default = False
    )
    use_edge_borders : BoolProperty(
        name = "Use borders",
        default = False
    )
    use_symmetry_collect_rings : BoolProperty(
        name = "Symmetrical",
        default = False
    )
    filter_input : EnumProperty(
        name = "Input for filter",
        items=[("0", "Base vectors", ""), ("1", "Saved filtered vectors", "")],
       # default = ("0", "Base vectors", "")
    )
    filter_type : EnumProperty(
        name = "Filter type",
        items=[("0", "Median", ""), ("1", "Smooth", ""), ("2", "Median+Smooth", "")],
      #  default = ("2", "Median+Smooth", "")
    )
    filter_params : FloatVectorProperty(
        name = "Filter radius priority"
        #default = []
    )

# оператор, т. е. вызов функции. Здесь вся логика
class PoleGridCreator(Operator):
    '''
    Для выбранного объекта (в EDIT MODE) создает сетку полюсов и сохраняет в файл.
    Попутно делает разметку зон и сбор колец для концентрических областей.
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
        if (self.use_edge_borders):
            # извлечь их из слоя??
            # добавить их в полгрид еще перед началом обхода
            return
        # настройки для симметрии в самой функции сделать

        # сохранение в файл        
        return
    
    def execute(self, context):
        raise NotImplementedError
        self.get_params(context)
        
        # вызываем все нужные функции
        self.create_random_vectors()
        
        return {'FINISHED'}
    
class ShowPoleGridHandler(Operator):
    '''
    Выберает все ребра, относящиеся к polegrid
    '''
    
    bl_idname = 'object.show_polegrid'
    bl_label = 'Show polegrid'
    
    def read_and_select_polegrid(self, context):
        # считать из файла
        polegrid = []

         #--- EDIT MODE!
        mesh_obj = bpy.context.active_object
        bm = bmesh.from_edit_mesh(mesh_obj.data)
        # выбираем / не выбираем
        for edge in bm.edges:
            edge.select = False
        for edge_id in polegrid:
            bm.edges[edge_id].select = True
    
    def execute(self, context):
        raise NotImplementedError
        self.get_params(context)
        
        # вызываем все нужные функции
        self.create_random_vectors()
        
        return {'FINISHED'}
    
class AddEdgeBorderToGridPoleHandler(Operator):
    '''
    Вручную добавляет к уже построенной gridpole ребра из edge border текущей
    '''
    bl_idname = 'object.add_edge_border_to_current_polegrid'
    bl_label = 'Add edge border to existing polegrid'
    
    def read_and_update_polegrid(self, context):
        # считать из файла
        polegrid = []

         #--- EDIT MODE!
        mesh_obj = bpy.context.active_object
        bm = bmesh.from_edit_mesh(mesh_obj.data)
        # выбираем / не выбираем
        for edge in bm.edges:
            edge.select = False
        for edge_id in polegrid:
            bm.edges[edge_id].select = True
    
    def execute(self, context):
        raise NotImplementedError
        self.get_params(context)
        
        # вызываем все нужные функции
        self.create_random_vectors()
        
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
    
    def get_params(self, context):
        props = context.object.polegrid_vector_props 
        self.use_symmetry = props.use_symmetry_collect_rings
        
    # собственно функция!
    def collect_rings(self):       
        return
    
    def execute(self, context):
        raise NotImplementedError
        self.get_params(context)
        
        # вызываем все нужные функции
        self.create_random_vectors()
        
        return {'FINISHED'}
    
class VectorFilter(Operator):
    '''
    Для выбранного объекта (в EDIT MODE) строит вектора и фильтрует.
    Базовые вектора: достает gridpole и collect rings result из файла и при обходе колец строит просто face loop curves.
    Может применять к базовым векторами фильтры на выбор.
    Может сохранять результат фильтрации и применять следующие фильтры уже к нему.
    '''
    
    bl_idname = 'object.filter_vectors'
    bl_label = 'Filter vectors'
    
    # params
    filter_input = None
    filter_type = None
    filter_params = None
    
    def get_params(self, context):
        props = context.object.polegrid_vector_props 
        self.filter_input = props.filter_input
        self.filter_type = props.filter_type
        self.filter_params = props.filter_params
            
    # собственно функция!
    def filter_vectors(self):       
        return
    
    def execute(self, context):
        raise NotImplementedError
        self.get_params(context)
        
        # вызываем все нужные функции
        self.create_random_vectors()
        
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