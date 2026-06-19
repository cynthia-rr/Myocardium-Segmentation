import slicer
from segmentation_constants import *

from typing import Any


def configure_editor(editor_node: slicer.vtkMRMLSegmentEditorNode, *, segment_id: str, 
                     overwrite_mode = slicer.vtkMRMLSegmentEditorNode.OverwriteNone, #TODO: type?
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
    

def apply_effect(editor_widget: slicer.qMRMLSegmentEditorWidget, effect_name: str, parameters: dict[str, Any]) -> None:
    """
    Apply a Segment Editor effect given the parameters
    """
    editor_widget.setActiveEffectByName(effect_name)
    effect = editor_widget.activeEffect()

    for key, value in parameters.items():
        effect.setParameter(key, value)
    effect.self().onApply()

    
def union_segments(editor_widget: slicer.qMRMLSegmentEditorWidget, editor_node: slicer.vtkMRMLSegmentEditorNode, 
                   source_segment_id: str, destination_segment_id: str) -> None:
    """
    Destination segment is set to the union of the source and the destination segment
    """
    configure_editor(editor_node, segment_id=destination_segment_id, mask_enabled=False, mask_mode=EDITABLE_ANYWHERE)
    apply_effect(editor_widget, "Logical operators", {"Operation":"UNION", "ModifierSegmentID":source_segment_id})
    # TODO: use constants instead of strings

# TODO: restructure this with function pointers/ a class?

def intersect_segments(editor_widget: slicer.qMRMLSegmentEditorWidget, editor_node: slicer.vtkMRMLSegmentEditorNode, 
                   source_segment_id: str, destination_segment_id: str) -> None:
    """
    Destination segment is set to the intersection of the source and the destination segment
    """
    configure_editor(editor_node, segment_id=destination_segment_id, mask_enabled=False, mask_mode=EDITABLE_ANYWHERE)
    apply_effect(editor_widget, "Logical operators", {"Operation":"INTERSECT", "ModifierSegmentID":source_segment_id})


def subtract_segments(editor_widget: slicer.qMRMLSegmentEditorWidget, editor_node: slicer.vtkMRMLSegmentEditorNode, 
                   source_segment_id: str, destination_segment_id: str) -> None:
    """
    Destination segment is set to the destination segment subtract the source segment
    """
    configure_editor(editor_node, segment_id=destination_segment_id, mask_enabled=False, mask_mode=EDITABLE_ANYWHERE)
    apply_effect(editor_widget, "Logical operators", {"Operation":"SUBTRACT", "ModifierSegmentID":source_segment_id})


def keep_largest_island(editor_widget: slicer.qMRMLSegmentEditorWidget, editor_node: slicer.vtkMRMLSegmentEditorNode, 
                        destination_segment_id: str) -> None: # TODO: do you need size?
    """
    Keep only the largest island
    """
    configure_editor(editor_node, segment_id=destination_segment_id, mask_enabled=False, mask_mode=EDITABLE_ANYWHERE)
    apply_effect(editor_widget, "Islands", {"Operation":"KEEP_LARGEST_ISLAND"})


def hollow_segment(editor_widget: slicer.qMRMLSegmentEditorWidget, editor_node: slicer.vtkMRMLSegmentEditorNode, 
                   destination_segment_id: str, thickness_mm: float, shell_mode: str) -> None: 
    
    """
    Hollow the segment with the given thickness and orientation (shell mode)
    """
    configure_editor(editor_node, segment_id=destination_segment_id, mask_enabled=False, mask_mode=EDITABLE_ANYWHERE)
    apply_effect(editor_widget, "Hollow", {"ShellThicknessMm":thickness_mm, "ShellMode":shell_mode, "ApplyToAllVisibleSegments":0})
    

def grow_shrink_segment(editor_widget: slicer.qMRMLSegmentEditorWidget, editor_node: slicer.vtkMRMLSegmentEditorNode, 
                 destination_segment_id: str, margin_mm: float, mask_mode: int, min_threshold: int, max_threshold:int) -> None:
    """
    Grow the segment by the margin size, using the given mask and threshold boundaries
    """
    
    configure_editor(editor_node, segment_id=destination_segment_id, mask_enabled=True, mask_mode=mask_mode, 
                     min_threshold=min_threshold, max_threshold=max_threshold)
    apply_effect(editor_widget, "Margin", {"MarginSizeMm": margin_mm})
    

def smooth_segment(editor_widget: slicer.qMRMLSegmentEditorWidget, editor_node: slicer.vtkMRMLSegmentEditorNode, 
                   destination_segment_id: str, kernel_size_mm: float) -> None:
    """
    Smooth the segment using Closing and Median methods, with the kernel size
    """
    configure_editor(editor_node, segment_id=destination_segment_id, mask_enabled=False, mask_mode=EDITABLE_ANYWHERE)
    apply_effect(editor_widget, "Smoothing", {"SmoothingMethod":"CLOSING", "KernelSizeMm":kernel_size_mm})
    apply_effect(editor_widget, "Smoothing", {"SmoothingMethod":"MEDIAN", "KernelSizeMm":kernel_size_mm})

def threshold_segment(editor_widget: slicer.qMRMLSegmentEditorWidget, editor_node: slicer.vtkMRMLSegmentEditorNode, 
                   destination_segment_id: str, min_threshold: int, max_threshold: int) -> None:
    """
    Apply the threshold between the min and max values to the segment
    """
    configure_editor(editor_node, segment_id=destination_segment_id, mask_enabled=False, mask_mode=EDITABLE_ANYWHERE)
    apply_effect(editor_widget, "Threshold", {"MinimumThreshold":min_threshold, "MaximumThreshold":max_threshold})


def create_closed_loop(segmentation: slicer.vtkMRMLSegmentationNode, editor_widget: slicer.qMRMLSegmentEditorWidget,
    editor_node: slicer.vtkMRMLSegmentEditorNode, left_myocardium_segment_id: str, left_ventricle_segment_id: str):
    
    temp_segment_id = segmentation.AddEmptySegment("hollow-left-ventricle", "hollow")

    try:
        union_segments(editor_widget, editor_node, left_ventricle_segment_id, temp_segment_id)
        hollow_segment(editor_widget, editor_node, temp_segment_id, thickness_mm=1.0, shell_mode="INSIDE_SURFACE")
        union_segments(editor_widget, editor_node, temp_segment_id, left_myocardium_segment_id)

    finally:
        segmentation.RemoveSegment(temp_segment_id)
