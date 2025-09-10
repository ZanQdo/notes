import bpy

# Handler for updating the panel's category name
def update_panel_category(self, context):
    """
    This function is called when the 'category_name' property is updated
    in the addon preferences. It unregisters the panel, updates its
    bl_category attribute, and then re-registers it.
    """
    # Unregister the panel to allow for re-registration with a new category
    try:
        bpy.utils.unregister_class(NOTES_PT_main_panel)
    except RuntimeError:
        # The class may not have been registered yet, which is fine.
        pass

    # Update the bl_category on the class itself
    prefs = context.preferences.addons[__name__].preferences
    NOTES_PT_main_panel.bl_category = prefs.category_name
    
    # Re-register the panel with the updated category
    bpy.utils.register_class(NOTES_PT_main_panel)


# Addon Preferences
class NotesAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    category_name: bpy.props.StringProperty(
        name="Tab Name",
        description="Set the name for the Notes tab in the sidebar",
        default="Notes",
        update=update_panel_category
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "category_name")


# Scene properties to store the notes
class NotesSceneProperties(bpy.types.PropertyGroup):
    main_notes: bpy.props.StringProperty(
        name="Notes",
        description="A space to write down your notes",
        default="",
    )
    version_counter: bpy.props.IntProperty(
        name="Version",
        description="A counter for the project version",
        default=0,
        min=0,
    )

# Operators for version counter
class WM_OT_increase_version(bpy.types.Operator):
    """Increase the version counter"""
    bl_idname = "notes.increase_version"
    bl_label = "Increase Version"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.scene.notes_properties.version_counter += 1
        return {'FINISHED'}

class WM_OT_decrease_version(bpy.types.Operator):
    """Decrease the version counter"""
    bl_idname = "notes.decrease_version"
    bl_label = "Decrease Version"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.notes_properties
        if props.version_counter > 0:
            props.version_counter -= 1
        return {'FINISHED'}


# The UI Panel
class NOTES_PT_main_panel(bpy.types.Panel):
    """Creates a Panel in the 3D View for notes"""
    bl_label = "Notes and Info"
    bl_idname = "NOTES_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    # The bl_category will be dynamically set from preferences
    bl_category = 'Notes'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        notes_props = scene.notes_properties

        # Version Counter UI
        row = layout.row(align=True)
        row.label(text="Version:")
        row.operator(WM_OT_decrease_version.bl_idname, text="-")
        row.prop(notes_props, "version_counter", text="")
        row.operator(WM_OT_increase_version.bl_idname, text="+")

        layout.separator()

        layout.label(text="Project Notes:")
        # Use a box for a better text area look
        box = layout.box()
        box.prop(notes_props, "main_notes", text="")

# Registration
classes = (
    NotesAddonPreferences,
    NotesSceneProperties,
    WM_OT_increase_version,
    WM_OT_decrease_version,
    NOTES_PT_main_panel,
)

def register():
    # Register all classes
    for cls in classes:
        bpy.utils.register_class(cls)
        
    # Set the initial category from saved preferences on startup
    prefs = bpy.context.preferences.addons[__name__].preferences
    NOTES_PT_main_panel.bl_category = prefs.category_name

    # Add the property group to the scene
    bpy.types.Scene.notes_properties = bpy.props.PointerProperty(type=NotesSceneProperties)

def unregister():
    # Remove the property group from the scene
    del bpy.types.Scene.notes_properties

    # Unregister all classes in reverse order
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()

