import slicer




def configure_editor(editor_node: slicer.vtkMRMLSegmentEditorNode, *, segment_id: str, 
                     overwrite_mode: slicer.vtkMRMLSegmentEditorNode.OverwriteMode = slicer.vtkMRMLSegmentEditorNode.OverwriteNone,
                     mask_mode: int, mask_enabled: bool, min_threshold: int = 0, max_threshold: int = 0) -> None:
    """
    Configure the segment editor node according to the given parameters
    """
    editor_node.SetSelectedSegmentID(segment_id)
    editor_node.SetOverwriteMode(overwrite_mode)
    editor_node.SetMaskMode(mask_mode)

    editor_node.SetSourceVolumeIntensityMask(mask_enabled)
    if mask_enabled:
        editor_node.SetSourceVolumeIntensityMaskRange(min_threshold, max_threshold)
    
    
def apply_effect()
    
    

def union_segments()
    


def intersect_segments()
    



def subtract_segments()
    

def keep_largest_island()
    



def hollow_segment()
    

def grow_segment()
    

def smooth_segment()
    



