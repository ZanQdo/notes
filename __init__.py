import bpy

# Handler for updating the panel's category name
def update_panel_category(self, context):
    """
    This function is called when the 'category_name' property is updated
    in the addon preferences. It unregisters the panel, updates its
    bl_category attribute, and then re-registers it.
    """
    try:
        bpy.utils.unregister_class(NOTES_PT_main_panel)
    except RuntimeError:
        pass

    prefs = context.preferences.addons[__name__].preferences
    NOTES_PT_main_panel.bl_category = prefs.category_name
    
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


# Property group for a single note item
class NoteItem(bpy.types.PropertyGroup):
    note: bpy.props.StringProperty(
        name="Note",
        description="A single note entry",
        default="",
    )

# Scene properties to store the collection of notes
class NotesSceneProperties(bpy.types.PropertyGroup):
    notes: bpy.props.CollectionProperty(type=NoteItem)
    active_note_index: bpy.props.IntProperty(
        name="Active Note Index",
        description="Index of the currently displayed note",
        default=0,
        min=0
    )

# Operators for note management
class WM_OT_add_note(bpy.types.Operator):
    """Add a new note"""
    bl_idname = "notes.add_note"
    bl_label = "Add Note"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        notes_props = context.scene.notes_properties
        new_note = notes_props.notes.add()
        notes_props.active_note_index = len(notes_props.notes) - 1
        return {'FINISHED'}

class WM_OT_next_note(bpy.types.Operator):
    """Go to the next note"""
    bl_idname = "notes.next_note"
    bl_label = "Next Note"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        notes_props = context.scene.notes_properties
        if notes_props.active_note_index < len(notes_props.notes) - 1:
            notes_props.active_note_index += 1
        return {'FINISHED'}

class WM_OT_previous_note(bpy.types.Operator):
    """Go to the previous note"""
    bl_idname = "notes.previous_note"
    bl_label = "Previous Note"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        notes_props = context.scene.notes_properties
        if notes_props.active_note_index > 0:
            notes_props.active_note_index -= 1
        return {'FINISHED'}


# The UI Panel
class NOTES_PT_main_panel(bpy.types.Panel):
    """Creates a Panel in the 3D View for notes"""
    bl_label = "Notes and Info"
    bl_idname = "NOTES_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Notes'

    def draw(self, context):
        layout = self.layout
        notes_props = context.scene.notes_properties
        
        # Check if there are any notes
        if len(notes_props.notes) > 0:
            # Navigation Row
            nav_row = layout.row(align=True)
            nav_row.label(text=f"Version: {notes_props.active_note_index + 1} / {len(notes_props.notes)}")
            
            op_row = nav_row.row(align=True)
            op_row.operator(WM_OT_previous_note.bl_idname, text="-")
            op_row.operator(WM_OT_next_note.bl_idname, text="+")
            
            layout.separator()

            # Note Text Area
            current_note = notes_props.notes[notes_props.active_note_index]
            box = layout.box()
            box.prop(current_note, "note", text="")
        else:
            layout.label(text="No notes yet. Create one!")
            
        layout.separator()
        
        # "Add Note" button
        layout.operator(WM_OT_add_note.bl_idname, text="Create New Note")


# Registration
classes = (
    NotesAddonPreferences,
    NoteItem,
    NotesSceneProperties,
    WM_OT_add_note,
    WM_OT_next_note,
    WM_OT_previous_note,
    NOTES_PT_main_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        
    prefs = bpy.context.preferences.addons[__name__].preferences
    NOTES_PT_main_panel.bl_category = prefs.category_name

    bpy.types.Scene.notes_properties = bpy.props.PointerProperty(type=NotesSceneProperties)

def unregister():
    del bpy.types.Scene.notes_properties

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()

