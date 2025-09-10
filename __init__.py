import bpy

# Scene properties to store the notes
class NotesSceneProperties(bpy.types.PropertyGroup):
    main_notes: bpy.props.StringProperty(
        name="Notes",
        description="A space to write down your notes",
        default="",
    )

# The UI Panel
class NOTES_PT_main_panel(bpy.types.Panel):
    """Creates a Panel in the 3D View for notes"""
    bl_label = "Notes and Info"
    bl_idname = "NOTES_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
URO'
    bl_category = 'Notes Tab'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        notes_props = scene.notes_properties

        layout.label(text="Project Notes:")
        layout.prop(notes_props, "main_notes", text="")

# Registration
classes = (
    NotesSceneProperties,
    NOTES_PT_main_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.notes_properties = bpy.props.PointerProperty(type=NotesSceneProperties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.notes_properties

if __name__ == "__main__":
    register()

