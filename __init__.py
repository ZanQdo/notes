import bpy
import datetime

# Helper function to dynamically find the correct datablock based on the current context/window
def get_target_id(context):
    if not hasattr(context, "area") or not context.area:
        return context.scene

    area_type = context.area.type
    
    if area_type == 'NODE_EDITOR':
        if hasattr(context.space_data, "node_tree") and context.space_data.node_tree:
            return context.space_data.node_tree
        elif hasattr(context.space_data, "edit_tree") and context.space_data.edit_tree:
            return context.space_data.edit_tree
    
    elif area_type == 'DOPESHEET_EDITOR':
        if hasattr(context.space_data, "action") and context.space_data.action:
            return context.space_data.action
        elif context.active_object and getattr(context.active_object.animation_data, "action", None):
            return context.active_object.animation_data.action
            
    elif area_type == 'PROPERTIES':
        sctx = getattr(context.space_data, "context", None)
        if sctx == 'MATERIAL':
            if context.active_object and getattr(context.active_object, "active_material", None):
                return context.active_object.active_material
        elif sctx == 'OBJECT':
            return context.active_object
        elif sctx == 'DATA':
            if context.active_object and getattr(context.active_object, "data", None):
                return context.active_object.data
        elif sctx == 'SCENE':
            return context.scene
        elif sctx == 'STRIP':
            strip = getattr(context, "active_sequence_strip", None)
            if not strip and getattr(context.scene, "sequence_editor", None):
                strip = context.scene.sequence_editor.active_strip
            return strip

    # Default fallback for VIEW_3D and unhandled areas (Target the Scene)
    return context.scene


# Handler for updating the panel's category name
def update_panel_category(self, context):
    """
    Unregisters and re-registers all contextual panels to update the tab name.
    """
    for cls in PANEL_CLASSES:
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass

    prefs = context.preferences.addons[__package__].preferences
    
    for cls in PANEL_CLASSES:
        cls.bl_category = prefs.category_name
        bpy.utils.register_class(cls)
    
# Handler for updating the status bar
def update_status_bar(self, context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'STATUSBAR':
                area.tag_redraw()
    return None

# Addon Preferences
class NotesAddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

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
        update=update_status_bar
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
        size=4 
    )
    view_distance: bpy.props.FloatProperty(
        name="View Distance"
    )

# Datablock properties to store the collection of notes
class NotesDataProperties(bpy.types.PropertyGroup):
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
    context.scene.frame_set(note.frame_number)

    view3d_area = None
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            view3d_area = area
            break
    
    if not view3d_area:
        return 

    if note.view_type == 'CAMERA':
        cam_object = bpy.data.objects.get(note.camera_name)
        if cam_object and cam_object.type == 'CAMERA':
            context.scene.camera = cam_object
            view3d_area.spaces.active.region_3d.view_perspective = 'CAMERA'
    elif note.view_type == 'VIEW':
        region_3d = view3d_area.spaces.active.region_3d
        region_3d.view_perspective = 'PERSP' 
        region_3d.view_rotation = note.view_rotation
        region_3d.view_distance = note.view_distance

# Operators
class WM_OT_add_note(bpy.types.Operator):
    """Add a new note to the active datablock"""
    bl_idname = "notes.add_note"
    bl_label = "Add Note"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        target_id = get_target_id(context)
        if not target_id or not hasattr(target_id, "notes_properties"):
            self.report({'WARNING'}, "Active datablock or strip does not support notes")
            return {'CANCELLED'}

        notes_props = target_id.notes_properties
        new_note = notes_props.notes.add()
        new_note.creation_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        view3d_space = None
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                view3d_space = area.spaces.active
                break
        
        if view3d_space and view3d_space.region_3d.view_perspective == 'CAMERA':
            new_note.view_type = 'CAMERA'
            if context.scene.camera:
                new_note.camera_name = context.scene.camera.name
            else:
                new_note.camera_name = "None"
        elif view3d_space: 
            new_note.view_type = 'VIEW'
            new_note.view_rotation = view3d_space.region_3d.view_rotation
            new_note.view_distance = view3d_space.region_3d.view_distance
            new_note.camera_name = ""
        else: 
            new_note.view_type = 'CAMERA'
            if context.scene.camera:
                new_note.camera_name = context.scene.camera.name
            else:
                new_note.camera_name = "None"
                
        new_note.frame_number = context.scene.frame_current

        notes_props.active_note_index = len(notes_props.notes) - 1
        update_status_bar(self, context) 
        return {'FINISHED'}

class WM_OT_next_note(bpy.types.Operator):
    """Go to the next note and restore its context"""
    bl_idname = "notes.next_note"
    bl_label = "Next Note"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        target_id = get_target_id(context)
        if not target_id or not hasattr(target_id, "notes_properties"): return {'CANCELLED'}
        
        notes_props = target_id.notes_properties
        if notes_props.active_note_index < len(notes_props.notes) - 1:
            notes_props.active_note_index += 1
            current_note = notes_props.notes[notes_props.active_note_index]
            restore_note_context(context, current_note)
        return {'FINISHED'}

class WM_OT_previous_note(bpy.types.Operator):
    """Go to the previous note and restore its context"""
    bl_idname = "notes.previous_note"
    bl_label = "Previous Note"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        target_id = get_target_id(context)
        if not target_id or not hasattr(target_id, "notes_properties"): return {'CANCELLED'}
        
        notes_props = target_id.notes_properties
        if notes_props.active_note_index > 0:
            notes_props.active_note_index -= 1
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
        target = get_target_id(context)
        return target and hasattr(target, "notes_properties") and len(target.notes_properties.notes) > 0

    def execute(self, context):
        target_id = get_target_id(context)
        if not target_id or not hasattr(target_id, "notes_properties"): return {'CANCELLED'}
        
        notes_props = target_id.notes_properties
        index = notes_props.active_note_index
        
        notes_props.notes.remove(index)
        
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
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.spaces.active.region_3d.view_perspective = 'CAMERA'
                    break 
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
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                region_3d = area.spaces.active.region_3d
                region_3d.view_perspective = 'PERSP' 
                region_3d.view_rotation = self.rotation
                region_3d.view_distance = self.distance
                break
        return {'FINISHED'}

# Base UI Panel to handle drawing logic
class NotesPanelBase:
    bl_label = "Notes"
    bl_category = 'Notes'

    @classmethod
    def poll(cls, context):
        target = get_target_id(context)
        # Safely ensure the target object actually supports and inherited the notes_properties pointer
        return target is not None and hasattr(target, "notes_properties")

    def draw(self, context):
        layout = self.layout
        target_id = get_target_id(context)
        
        if not target_id: return
            
        # Safer fallback to prevent panel draw errors if the pointer is missing
        notes_props = getattr(target_id, "notes_properties", None)
        if not notes_props:
            return
        
        if len(notes_props.notes) > 0:
            nav_row = layout.row(align=True)
            nav_row.label(text=f"Note: {notes_props.active_note_index + 1} / {len(notes_props.notes)}")
            nav_row.operator(WM_OT_previous_note.bl_idname, text="", icon='TRIA_LEFT')
            nav_row.operator(WM_OT_next_note.bl_idname, text="", icon='TRIA_RIGHT')
            nav_row.operator(WM_OT_add_note.bl_idname, text="", icon='ADD')
            nav_row.operator(WM_OT_delete_note.bl_idname, text="", icon='TRASH')

            current_note = notes_props.notes[notes_props.active_note_index]
            
            if current_note.creation_date:
                row_date = layout.row()
                row_date.label(text=f"Date: {current_note.creation_date}", icon='TIME')

            file_version_tuple = bpy.data.version
            file_version_string = f"{file_version_tuple[0]}.{file_version_tuple[1]}.{file_version_tuple[2]}"
            
            row_version = layout.row()
            row_version.label(text=f"Saved with: {file_version_string}", icon='BLENDER')

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

            layout.label(text="Note:", icon='CURRENT_FILE')
            col = layout.column()
            
            # Version check for Blender 5.2+ to utilize the textbox feature
            if bpy.app.version >= (5, 2, 0):
                col.textbox(current_note, "note")
            else:
                col.prop(current_note, "note", text="")
        
        else:
            row = layout.row()
            row.scale_y = 1.5
            row.operator(WM_OT_add_note.bl_idname, text="Create New Note")


# Sub-Panels targeting specific editor areas
class NOTES_PT_view3d(NotesPanelBase, bpy.types.Panel):
    bl_idname = "NOTES_PT_view3d"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

class NOTES_PT_action_editor(NotesPanelBase, bpy.types.Panel):
    bl_idname = "NOTES_PT_action_editor"
    bl_space_type = 'DOPESHEET_EDITOR'
    bl_region_type = 'UI'

class NOTES_PT_node_editor(NotesPanelBase, bpy.types.Panel):
    bl_idname = "NOTES_PT_node_editor"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'

class NOTES_PT_properties_object(NotesPanelBase, bpy.types.Panel):
    bl_idname = "NOTES_PT_properties_object"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'object'

class NOTES_PT_properties_data(NotesPanelBase, bpy.types.Panel):
    bl_idname = "NOTES_PT_properties_data"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'data'

class NOTES_PT_properties_material(NotesPanelBase, bpy.types.Panel):
    bl_idname = "NOTES_PT_properties_material"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'material'

class NOTES_PT_properties_scene(NotesPanelBase, bpy.types.Panel):
    bl_idname = "NOTES_PT_properties_scene"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'scene'

class NOTES_PT_properties_strip(NotesPanelBase, bpy.types.Panel):
    bl_idname = "NOTES_PT_properties_strip"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'strip'


# Function to draw the note version in the status bar
def draw_note_status(self, context):
    layout = self.layout
    # Always target the scene for the status bar display
    target_id = context.scene

    notes_props = getattr(target_id, "notes_properties", None)
    
    if notes_props and len(notes_props.notes) > 0:
        layout.separator()

        last_note_index = len(notes_props.notes) - 1
        last_note_text = notes_props.notes[last_note_index].note
        note_info = ""
        
        target_prefix = f"[{target_id.name}] "
        
        if last_note_text:
            version_prefix = f"V{last_note_index + 1} - "
            total_max_length = 160
            note_max_length = total_max_length - len(version_prefix) - len(target_prefix)

            if note_max_length < 0: note_max_length = 0
            
            if len(last_note_text) > note_max_length:
                display_text = last_note_text.replace('\n', ' ')[:note_max_length] + "..."
            else:
                display_text = last_note_text.replace('\n', ' ')
            
            note_info = f"{target_prefix}{version_prefix}{display_text}"
        else:
            note_info = f"{target_prefix}V{last_note_index + 1}"

        layout.label(text=note_info, icon='CURRENT_FILE')


PANEL_CLASSES = [
    NOTES_PT_view3d,
    NOTES_PT_action_editor,
    NOTES_PT_node_editor,
    NOTES_PT_properties_object,
    NOTES_PT_properties_data,
    NOTES_PT_properties_material,
    NOTES_PT_properties_scene,
    NOTES_PT_properties_strip,
]

classes = (
    NotesAddonPreferences,
    NoteItem,
    NotesDataProperties,
    WM_OT_add_note,
    WM_OT_next_note,
    WM_OT_previous_note,
    WM_OT_delete_note,
    WM_OT_goto_frame,
    WM_OT_set_active_camera,
    WM_OT_restore_view,
    *PANEL_CLASSES
)

# Comprehensive list covering modern (Blender 4.x+) and legacy strip classes
STRIP_TYPES = (
    'Sequence', 'SoundStrip', 'ColorStrip', 'MovieStrip', 'ImageStrip',
    'EffectStrip', 'MetaStrip', 'SceneStrip', 'MaskStrip', 'ClipStrip', 'TextStrip',
    'AdjustmentStrip', 'CrossStrip', 'GammaCrossStrip', 'MultiplyStrip',
    'OverDropStrip', 'AlphaOverStrip', 'AlphaUnderStrip', 'WipeStrip', 'GlowStrip',
    'TransformStrip', 'SpeedControlStrip', 'MulticamStrip', 'GaussianBlurStrip',
    'ColorMixStrip', 'SoundSequence', 'ColorSequence', 'MovieSequence', 'ImageSequence',
    'EffectSequence', 'MetaSequence', 'SceneSequence', 'MaskSequence', 'ClipSequence',
    'TextSequence', 'AdjustmentSequence', 'CrossSequence', 'GammaCrossSequence',
    'MultiplySequence', 'OverDropSequence', 'AlphaOverSequence', 'AlphaUnderSequence',
    'WipeSequence', 'GlowSequence', 'TransformSequence', 'SpeedControlSequence',
    'MulticamSequence', 'GaussianBlurSequence', 'ColorMixSequence'
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        
    if __package__:
        prefs = bpy.context.preferences.addons[__package__].preferences
        for cls in PANEL_CLASSES:
            cls.bl_category = prefs.category_name

    # Register on base ID class so ALL datablocks inherit it
    bpy.types.ID.notes_properties = bpy.props.PointerProperty(type=NotesDataProperties)
    
    # Register explicitly on all specific sequence strip types
    for s_type in STRIP_TYPES:
        if hasattr(bpy.types, s_type):
            setattr(getattr(bpy.types, s_type), 'notes_properties', bpy.props.PointerProperty(type=NotesDataProperties))
            
    bpy.types.STATUSBAR_HT_header.append(draw_note_status)


def unregister():
    bpy.types.STATUSBAR_HT_header.remove(draw_note_status)
    
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass 
        
    if hasattr(bpy.types.ID, 'notes_properties'):
        del bpy.types.ID.notes_properties
        
    for s_type in STRIP_TYPES:
        if hasattr(bpy.types, s_type):
            cls = getattr(bpy.types, s_type)
            if hasattr(cls, 'notes_properties'):
                del cls.notes_properties


if __name__ == "__main__":
    register()