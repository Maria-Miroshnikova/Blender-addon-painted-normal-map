import bpy
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import FloatProperty, StringProperty, EnumProperty, PointerProperty
from bpy.utils import register_class, unregister_class
import random


'''
Кнопки:
    - выбор объекта uv_obj -> OBJECT
    - размер сетки step (min_a в алгоритме) -> FLOAT (default =)
    - длина векторов vector_size (len_coeff в алгоритме) -> FLOAT (default = 0.02)
    (они должни быть близки к 0, но можно для визуализации делать их длиннее)
    - отклонение от узлов сетки distortion -> FLOAT (default = 0, soft_max = vector_size) 
    - кнопка оператора
'''

class OBJECT_PT_RandomVectorsPanel(Panel):
    bl_label = "Random Vectors for strokes"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Curves for Strokes"
    
    def draw(self, context):
        layout = self.layout
        props = context.object.random_vectors
        
        col = layout.column()
        col.prop(props, "UV_object")
        
   #     object_names = [object.name for object in bpy.data.objects]
#        obj_names_enums = [(name, name, "") for name in object_names]
#        uv_object = bpy.props.EnumProperty(
#            name="UV_object",
#            description="Отдельный объект, являющийся UV-разверткой объекта, к которому применяют оператор",
 #           items=obj_names_enums
#        )
 #       col.prop(uv_object, "UV_object")
        
        col = layout.column()
        #spl = col.split()
        box = col.box()
        box.prop(props, "min_a")
        
        box.prop(props, "len_coeff")
        
        box.prop(props, "distortion")
        
        col = layout.column()
        col.operator('object.random_vectors')        
    

# параметры для панели и для оператора (которые в функцию передаются)
class RandomVectorsProps(PropertyGroup):
    
    def get_items(self, context):
        object_names = [object.name for object in bpy.data.objects]
        obj_names_enums = [("empty", "", "")]
        obj_names_enums_ = [(name, name, "") for name in object_names]
      #  obj_names_enums = []#[("empty", "", "")]
       # obj_name_enums.extend([(name, name, "") for name in object_names])
       # obj_names_enums.append(("empty", "", ""))
        obj_names_enums.extend(obj_names_enums_)
        return obj_names_enums
    
   # UV_object : StringPropetry(
    UV_object : EnumProperty(
        name="UV_object",
 # TODO make empty default value
 #       default = (None, None, ""),
        description="Отдельный объект, являющийся UV-разверткой объекта, к которому применяют оператор",
        items=get_items
    )
    min_a : FloatProperty(
        name = "Dencity",
        default = 0.02,
        min = 0.0001,
        soft_max = 1,
        subtype = 'FACTOR'
    )
    len_coeff : FloatProperty(
        name = "Vector length",
        default = 0.001,
        min = 0.0001,
        soft_max = 1,
        subtype = 'FACTOR'
        
    )
    distortion : FloatProperty(
        name = "Distortion",
        default = 0,
        min = 0.0001,
        soft_max = 1,
        subtype = 'FACTOR'
        
    )

# оператор, т. е. вызов функции. Здесь вся логика
class RandomVectors(Operator):
    '''
    Для выбранного объекта (в EDIT MODE) и назначенной вручную
    искусственной развертки этого объекта
    создает множество векторов над uv разверткой типа poly curve
    
    (для последующего подключения geomentry nodes
    с генерацией штрихов вдоль направляющих кривых)
    '''
    
    bl_idname = 'object.random_vectors'
    bl_label = 'Create random vectors'
    
    # params
    UV_object = None
    a_min = None
    len_coeff = None
    distortion = None
    
    def get_params(self, context):
        props = context.object.random_vectors
        self.UV_object = props.UV_object
        self.a_min = props.min_a
        self.len_coeff = props.len_coeff
        self.distortion = props.distortion
        
    # собственно функция!
    def create_random_vectors(self):
        return
    
    def execute(self, context):
        #raise NotImplementedError
        self.get_params(context)
        
        # вызываем все нужные функции
        self.create_random_vectors()
        
        return {'FINISHED'}





classes = [
    RandomVectorsProps,
    RandomVectors,
    OBJECT_PT_RandomVectorsPanel
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
    bpy.types.Object.random_vectors = PointerProperty(type = RandomVectorsProps)
    
    # вызов вручную в скрипте: (потом будет кнопка, а в коде вызывать его не нужно)
   # bpy.ops.object.random_vectors()