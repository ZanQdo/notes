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
    
# Handler for updating the status bar
def update_status_bar(self, context):
    """
    Forces a redraw of the status bar area to ensure the note
    version is updated visually.
    """
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'STATUSBAR':
                area.tag_redraw()
    return None

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
        update=update_status_bar # Trigger status bar update when note text changes
    )

# Scene properties to store the collection of notes
class NotesSceneProperties(bpy.types.PropertyGroup):
    notes: bpy.props.CollectionProperty(type=NoteItem)
    active_note_index: bpy.props.IntProperty(
        name="Active Note Index",
        description="Index of the currently displayed note",
        default=0,
        min=0,
        update=update_status_bar
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
        update_status_bar(self, context) # Manually update for new total
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

# Function to draw the note version in the status bar
def draw_note_status(self, context):
    layout = self.layout
    notes_props = context.scene.notes_properties
    
    if len(notes_props.notes) > 0:
        layout.separator()

        current_note_text = notes_props.notes[notes_props.active_note_index].note
        note_info = ""
        
        if current_note_text:
            version_prefix = f"Version: {notes_props.active_note_index + 1}. "
            total_max_length = 80
            note_max_length = total_max_length - len(version_prefix)

            # Ensure note_max_length is not negative
            if note_max_length < 0:
                note_max_length = 0
            
            # Truncate the note if it's too long to fit in the status bar
            if len(current_note_text) > note_max_length:
                # Replace newlines with spaces for single-line display
                display_text = current_note_text.replace('\n', ' ')[:note_max_length] + "..."
            else:
                display_text = current_note_text.replace('\n', ' ')
            
            note_info = f"{version_prefix}{display_text}"
        else:
            # If there's no note, just show the version number without a period
            note_info = f"Version: {notes_props.active_note_index + 1}"

        # Display the actual note text in the status bar
        layout.label(text=note_info)


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
    
    # Append the draw function to the status bar
    bpy.types.STATUSBAR_HT_header.append(draw_note_status)


def unregister():
    del bpy.types.Scene.notes_properties

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
        
    # Remove the draw function from the status bar
    bpy.types.STATUSBAR_HT_header.remove(draw_note_status)


if __name__ == "__main__":
    register()

