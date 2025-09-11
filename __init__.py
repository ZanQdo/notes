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
    camera_name: bpy.props.StringProperty(
        name="Camera Name",
        description="Active camera when the note was created"
    )
    frame_number: bpy.props.IntProperty(
        name="Frame Number",
        description="Current frame when the note was created"
    )
    view_type: bpy.props.StringProperty(
        name="View Type",
        description="The type of view stored (CAMERA or VIEW)"
    )
    view_rotation: bpy.props.FloatVectorProperty(
        name="View Rotation",
        size=4 # Quaternion
    )
    view_distance: bpy.props.FloatProperty(
        name="View Distance"
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

# Helper function to restore context from a note
def restore_note_context(context, note):
    """
    Sets the scene frame, camera, and view based on the provided note's properties.
    """
    # Set the frame
    context.scene.frame_set(note.frame_number)

    # Find a 3D viewport to modify
    view3d_area = None
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            view3d_area = area
            break
    
    if not view3d_area:
        return # Cannot proceed without a 3D view

    # Restore camera or custom view
    if note.view_type == 'CAMERA':
        cam_object = bpy.data.objects.get(note.camera_name)
        if cam_object and cam_object.type == 'CAMERA':
            context.scene.camera = cam_object
            view3d_area.spaces.active.region_3d.view_perspective = 'CAMERA'
    elif note.view_type == 'VIEW':
        region_3d = view3d_area.spaces.active.region_3d
        # We must set perspective to something other than CAMERA before changing rotation/distance
        region_3d.view_perspective = 'PERSP' 
        region_3d.view_rotation = note.view_rotation
        region_3d.view_distance = note.view_distance

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
        
        # Find the active 3D viewport
        view3d_space = None
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                view3d_space = area.spaces.active
                break
        
        # Capture view information
        if view3d_space and view3d_space.region_3d.view_perspective == 'CAMERA':
            new_note.view_type = 'CAMERA'
            if context.scene.camera:
                new_note.camera_name = context.scene.camera.name
            else:
                new_note.camera_name = "None"
        elif view3d_space: # It's a custom view (Ortho/Persp)
            new_note.view_type = 'VIEW'
            new_note.view_rotation = view3d_space.region_3d.view_rotation
            new_note.view_distance = view3d_space.region_3d.view_distance
            new_note.camera_name = "" # Clear camera name for custom views
        else: # Fallback if no 3D view is found
            new_note.view_type = 'CAMERA'
            if context.scene.camera:
                new_note.camera_name = context.scene.camera.name
            else:
                new_note.camera_name = "None"
                
        new_note.frame_number = context.scene.frame_current

        notes_props.active_note_index = len(notes_props.notes) - 1
        update_status_bar(self, context) # Manually update for new total
        return {'FINISHED'}

class WM_OT_next_note(bpy.types.Operator):
    """Go to the next note and restore its context"""
    bl_idname = "notes.next_note"
    bl_label = "Next Note"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        notes_props = context.scene.notes_properties
        if notes_props.active_note_index < len(notes_props.notes) - 1:
            notes_props.active_note_index += 1
            # Restore context for the new active note
            current_note = notes_props.notes[notes_props.active_note_index]
            restore_note_context(context, current_note)
        return {'FINISHED'}

class WM_OT_previous_note(bpy.types.Operator):
    """Go to the previous note and restore its context"""
    bl_idname = "notes.previous_note"
    bl_label = "Previous Note"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        notes_props = context.scene.notes_properties
        if notes_props.active_note_index > 0:
            notes_props.active_note_index -= 1
            # Restore context for the new active note
            current_note = notes_props.notes[notes_props.active_note_index]
            restore_note_context(context, current_note)
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

class WM_OT_goto_frame(bpy.types.Operator):
    """Go to the frame this note was created on"""
    bl_idname = "notes.goto_frame"
    bl_label = "Go to Frame"
    bl_options = {'REGISTER', 'UNDO'}

    frame: bpy.props.IntProperty()

    def execute(self, context):
        context.scene.frame_set(self.frame)
        return {'FINISHED'}

class WM_OT_set_active_camera(bpy.types.Operator):
    """Set the active scene camera to the one stored in the note and enter its view"""
    bl_idname = "notes.set_camera"
    bl_label = "Set Active Camera"
    bl_options = {'REGISTER', 'UNDO'}

    camera_name: bpy.props.StringProperty()

    def execute(self, context):
        cam_object = bpy.data.objects.get(self.camera_name)
        if cam_object and cam_object.type == 'CAMERA':
            context.scene.camera = cam_object
            
            # Find a 3D view area and switch to camera view
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.spaces.active.region_3d.view_perspective = 'CAMERA'
                    break # Exit the loop once a 3D view is found and updated
                    
            return {'FINISHED'}
        else:
            self.report({'WARNING'}, f"Camera '{self.camera_name}' not found.")
            return {'CANCELLED'}

class WM_OT_restore_view(bpy.types.Operator):
    """Restore the 3D viewport to the state stored in the note"""
    bl_idname = "notes.restore_view"
    bl_label = "Restore Viewport"
    bl_options = {'REGISTER', 'UNDO'}

    rotation: bpy.props.FloatVectorProperty(size=4)
    distance: bpy.props.FloatProperty()

    def execute(self, context):
        # Find a 3D view area and update its state
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                region_3d = area.spaces.active.region_3d
                region_3d.view_perspective = 'PERSP' # Ensure not in camera view
                region_3d.view_rotation = self.rotation
                region_3d.view_distance = self.distance
                break
        return {'FINISHED'}

# The UI Panel
class NOTES_PT_main_panel(bpy.types.Panel):
    """Panel in the 3D View for notes"""
    bl_label = "Notes"
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
            nav_row.label(text=f"Note: {notes_props.active_note_index + 1} / {len(notes_props.notes)}")
            nav_row.operator(WM_OT_previous_note.bl_idname, text="", icon='TRIA_LEFT')
            nav_row.operator(WM_OT_next_note.bl_idname, text="", icon='TRIA_RIGHT')
            nav_row.operator(WM_OT_add_note.bl_idname, text="", icon='ADD')
            nav_row.operator(WM_OT_delete_note.bl_idname, text="", icon='TRASH')

            # Date and Blender Version Info with Icons
            current_note = notes_props.notes[notes_props.active_note_index]
            
            # Display date with clock icon in its own row
            if current_note.creation_date:
                row_date = layout.row()
                row_date.label(text=f"Date: {current_note.creation_date}", icon='TIME')

            # Get the Blender version the file was saved with and display it in a new row
            file_version_tuple = bpy.data.version
            file_version_string = f"{file_version_tuple[0]}.{file_version_tuple[1]}.{file_version_tuple[2]}"
            
            row_version = layout.row()
            row_version.label(text=f"Saved with: {file_version_string}", icon='BLENDER')

            # Display Camera or View information
            if current_note.view_type == 'CAMERA':
                if current_note.camera_name and current_note.camera_name != "None":
                    row_cam = layout.row(align=True)
                    row_cam.label(text=f"Camera: {current_note.camera_name}", icon='CAMERA_DATA')
                    
                    if current_note.camera_name in bpy.data.objects:
                        op = row_cam.operator(WM_OT_set_active_camera.bl_idname, text="", icon='VIEW_CAMERA')
                        op.camera_name = current_note.camera_name
                    else:
                        row_cam.label(text="", icon='ERROR')
            elif current_note.view_type == 'VIEW':
                row_view = layout.row(align=True)
                row_view.label(text="Custom View Saved", icon='VIEW3D')
                op = row_view.operator(WM_OT_restore_view.bl_idname, text="", icon='RESTRICT_VIEW_OFF')
                op.rotation = current_note.view_rotation
                op.distance = current_note.view_distance

            row_frame = layout.row(align=True)
            row_frame.label(text=f"Frame: {current_note.frame_number}", icon='SEQUENCE')
            op = row_frame.operator(WM_OT_goto_frame.bl_idname, text="", icon='PLAY')
            op.frame = current_note.frame_number

            # Note Text Area with Label and Icon
            layout.label(text="Note:", icon='TEXT')
            box = layout.box()
            box.prop(current_note, "note", text="")
        
        else:
             # "Add Note" button when no notes exist
            row = layout.row()
            row.scale_y = 1.5
            row.operator(WM_OT_add_note.bl_idname, text="Create New Note")

# The Help & Links sub-panel
class NOTES_PT_HelpLinksPanel(bpy.types.Panel):
    bl_label = ""
    bl_parent_id = "NOTES_PT_main_panel"
    bl_idname = "NOTES_PT_help_links"
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
            version_prefix = f"V{last_note_index + 1} - "
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
            note_info = f"V{last_note_index + 1}"

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
    WM_OT_goto_frame,
    WM_OT_set_active_camera,
    WM_OT_restore_view,
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
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass # Ignore errors for classes that are already unregistered
        
    # Delete the scene property after unregistering classes
    # Add a check to prevent errors if it doesn't exist
    if hasattr(bpy.types.Scene, 'notes_properties'):
        del bpy.types.Scene.notes_properties


if __name__ == "__main__":
    register()

