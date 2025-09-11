import bpy
import datetime

# Handler for updating the panel's category name
def update_panel_category(self, context):
    """
    This function is called when the 'category_name' property is updated
    in the addon preferences. It unregisters the panel, updates its
    bl_category attribute, and then re-registers it.
    """
    try:
        # Unregister both panels to ensure a clean update
        bpy.utils.unregister_class(NOTES_PT_HelpLinksPanel)
        bpy.utils.unregister_class(NOTES_PT_main_panel)
    except RuntimeError:
        pass

    prefs = context.preferences.addons[__name__].preferences
    NOTES_PT_main_panel.bl_category = prefs.category_name
    
    # Re-register both panels, parent first
    bpy.utils.register_class(NOTES_PT_main_panel)
    bpy.utils.register_class(NOTES_PT_HelpLinksPanel)
    
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
    creation_date: bpy.props.StringProperty(
        name="Creation Date",
        description="Date the note was created"
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
        new_note.creation_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
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

class WM_OT_delete_note(bpy.types.Operator):
    """Delete the current note"""
    bl_idname = "notes.delete_note"
    bl_label = "Delete Note"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Only allow deleting if there are notes
        return len(context.scene.notes_properties.notes) > 0

    def execute(self, context):
        notes_props = context.scene.notes_properties
        index = notes_props.active_note_index
        
        notes_props.notes.remove(index)
        
        # Adjust the active index if it's now out of bounds
        if index >= len(notes_props.notes) and len(notes_props.notes) > 0:
            notes_props.active_note_index = len(notes_props.notes) - 1
            
        update_status_bar(self, context)
        return {'FINISHED'}

# The UI Panel
class NOTES_PT_main_panel(bpy.types.Panel):
    """Panel in the 3D View for notes"""
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
            nav_row.operator(WM_OT_previous_note.bl_idname, text="", icon='TRIA_LEFT')
            nav_row.operator(WM_OT_next_note.bl_idname, text="", icon='TRIA_RIGHT')
            nav_row.operator(WM_OT_delete_note.bl_idname, text="", icon='TRASH')

            # Date and Blender Version Info
            current_note = notes_props.notes[notes_props.active_note_index]
            date_text = f"Date: {current_note.creation_date}" if current_note.creation_date else ""
            
            # Get the Blender version the file was saved with
            file_version_tuple = bpy.data.version
            file_version_string = f"{file_version_tuple[0]}.{file_version_tuple[1]}.{file_version_tuple[2]}"
            blender_text = f"Saved with: {file_version_string}"

            info_text = f"{date_text} | {blender_text}" if date_text else blender_text
            layout.label(text=info_text)

            layout.separator()

            # Note Text Area
            box = layout.box()
            box.prop(current_note, "note", text="")
        
        layout.separator()
        
        # "Add Note" button
        layout.operator(WM_OT_add_note.bl_idname, text="Create New Note")

# The Help & Links sub-panel
class NOTES_PT_HelpLinksPanel(bpy.types.Panel):
    bl_label = ""
    bl_parent_id = "NOTES_PT_main_panel"
    bl_idname = "SNAPSHOT_PT_help_links"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text='Help & Links', icon='HEART')

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.operator('wm.url_open', text='Read the Manual', icon = 'HELP').url = 'https://superhivemarket.com/products/notes/docs'
        row = layout.row()
        row.operator('wm.url_open' ,text='Discover More!', icon = 'URL').url = 'http://blenderaddon.com'
        row = layout.row()
        row.operator('wm.url_open', text='Follow us on Twitter', icon = 'BOIDS').url = 'https://twitter.com/BlenderAddon'
        row = layout.row()
        row.operator('wm.url_open', text='Subscribe on Youtube', icon = 'PLAY').url = 'https://www.youtube.com/@blenderaddon'
        row = layout.row()
        row.operator('wm.url_open', text='Hire a Blender Expert', icon = 'BLENDER').url = 'https://www.patazanimation.com'


# Function to draw the note version in the status bar
def draw_note_status(self, context):
    layout = self.layout
    notes_props = context.scene.notes_properties
    
    if len(notes_props.notes) > 0:
        layout.separator()

        last_note_index = len(notes_props.notes) - 1
        last_note_text = notes_props.notes[last_note_index].note
        note_info = ""
        
        if last_note_text:
            version_prefix = f"Version {last_note_index + 1} - "
            total_max_length = 80
            note_max_length = total_max_length - len(version_prefix)

            # Ensure note_max_length is not negative
            if note_max_length < 0:
                note_max_length = 0
            
            # Truncate the note if it's too long to fit in the status bar
            if len(last_note_text) > note_max_length:
                # Replace newlines with spaces for single-line display
                display_text = last_note_text.replace('\n', ' ')[:note_max_length] + "..."
            else:
                display_text = last_note_text.replace('\n', ' ')
            
            note_info = f"{version_prefix}{display_text}"
        else:
            # If there's no note, just show the version number without a period
            note_info = f"Version {last_note_index + 1}"

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
    WM_OT_delete_note,
    NOTES_PT_main_panel,
    NOTES_PT_HelpLinksPanel,
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
    # Remove the draw function from the status bar
    bpy.types.STATUSBAR_HT_header.remove(draw_note_status)
    
    # Unregister all classes
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
        
    # Delete the scene property after unregistering classes
    # Add a check to prevent errors if it doesn't exist
    if hasattr(bpy.types.Scene, 'notes_properties'):
        del bpy.types.Scene.notes_properties


if __name__ == "__main__":
    register()
