import slicer

import SimpleITK as sitk
import sitkUtils
import numpy as np
import scipy.ndimage

from segmentation_constants import *
from segmentation_utils import *
from io_utils import export_segment_to_labelmap, import_labelmap_to_segmentation, remove_nodes

def segment_right_myocardium(editor_widget: slicer.qMRMLSegmentEditorWidget, editor_node: slicer.vtkMRMLSegmentEditorNode,
                             right_ventricle_segment_id: str, right_myocardium_segment_id: str) -> None:
    # TODO: write docstring?
    keep_largest_island(editor_widget, editor_node, right_ventricle_segment_id)
    union_segments(editor_widget, editor_node, right_ventricle_segment_id, right_myocardium_segment_id)
    hollow_segment(editor_widget, editor_node, right_myocardium_segment_id, 1.0, "OUTSIDE_SURFACE") # TODO: make 1.0 a constant
    if RIGHT_MYOCARDIUM_GROWTH > 0:
        grow_segment(editor_widget, editor_node, right_myocardium_segment_id, RIGHT_MYOCARDIUM_GROWTH, #TODO: remove the editable outside segments?
                    EDITABLE_OUTSIDE_ALL_SEGMENTS, MIN_MYOCARDIUM_THRESHOLD_VALUE, MAX_MYOCARDIUM_THRESHOLD_VALUE)
    smooth_segment(editor_widget, editor_node, right_myocardium_segment_id, max(RIGHT_MYOCARDIUM_GROWTH/2, 1.0))


def improve_left_myocardium(segmentation: slicer.vtkMRMLSegmentationNode, editor_widget: slicer.qMRMLSegmentEditorWidget, 
                            editor_node: slicer.vtkMRMLSegmentEditorNode, left_ventricle_segment_id: str, 
                            left_myocardium_segment_id: str) -> None:
    # TODO: write docstring
    if LEFT_MYOCARDIUM_GROWTH > 0:
        grow_segment(editor_widget, editor_node, left_myocardium_segment_id, LEFT_MYOCARDIUM_GROWTH, EDITABLE_OUTSIDE_ALL_SEGMENTS,
                        MIN_MYOCARDIUM_THRESHOLD_VALUE, MAX_MYOCARDIUM_THRESHOLD_VALUE)
    smooth_segment(editor_widget, editor_node, left_myocardium_segment_id, max(1.0, LEFT_MYOCARDIUM_GROWTH/2))
    create_closed_loop(segmentation, editor_widget, editor_node, left_myocardium_segment_id, left_ventricle_segment_id)

# Dividing left myocardium into inner, middle and outer layers # TODO: remove the segmentaiton?
def divide_myocardium(volume_node: slicer.vtkMRMLScalarVolumeNode,
                    segmentation_chambers_node: slicer.vtkMRMLSegmentationNode, 
                    myocardium_segment_id: str, ventricle_segment_id:str) -> tuple[str, str, str]:
    # TODO: write docstring
    """
    """
    # Export myocardium to myocardiumlabel map
    myocardium_labelmap = export_segment_to_labelmap(segmentation_chambers_node, myocardium_segment_id, volume_node, "MyocardiumLabelMap")
    
    # Export left ventricle segment to ventricle label map
    ventricle_labelmap = export_segment_to_labelmap(segmentation_chambers_node, ventricle_segment_id, volume_node, "VentricleLabelMap")

    # TODO: delete if unnedded
    # ventricle_labelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "VentricleLabelMap")
    # slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(segmentation_chambers_node, [str(ventricle_segment_id)], 
    #                                                                   ventricle_labelmap, volume_node)

    # Convert from label map to numpy
    myocardium_image = sitkUtils.PullVolumeFromSlicer(myocardium_labelmap)
    ventricle_image = sitkUtils.PullVolumeFromSlicer(ventricle_labelmap)
    
    myocardium_array = sitk.GetArrayFromImage(myocardium_image).astype(bool)
    ventricle_array = sitk.GetArrayFromImage(ventricle_image).astype(bool)
    spacingXYZ = myocardium_image.GetSpacing()
    spacing = spacingXYZ[::-1]

    # # Make endocardial and epicardial surfaces # TODO: delete 
    # endocardium_surface = (scipy.ndimage.binary_dilation(ventricle_array) & myocardium_array)
    # epicardium_surface = (~scipy.ndimage.binary_erosion(myocardium_array) & myocardium_array)

    # Calculate distance to endocardium and epicardium
    distance_endocardium = scipy.ndimage.distance_transform_edt(~ventricle_array, sampling=spacing)
    distance_epicardium = scipy.ndimage.distance_transform_edt(myocardium_array, sampling=spacing)
    

    # Restrict to myocardium only
    distance_endocardium = np.abs(distance_endocardium)
    distance_epicardium = np.maximum(distance_epicardium, 0)

    # Calculate wall depth, and smoothing to prevent protrusions
    wall_depth = distance_endocardium / (distance_endocardium + distance_epicardium + 1e-6) # to prevent division by 0
    wall_depth = scipy.ndimage.gaussian_filter(wall_depth, sigma=1.5) # TODO: magic numbers

    # Calculate percentile for inner layer, middle layer
    inner_limit = np.percentile(wall_depth[myocardium_array], INNER_MYOCARDIUM_LIMIT)
    middle_limit = np.percentile(wall_depth[myocardium_array], MIDDLE_MYOCARDIUM_LIMIT)

    # Create masks for the 3 segments 
    inner_mask = (myocardium_array & (wall_depth < inner_limit)) 
    inner_mask = scipy.ndimage.binary_closing(inner_mask, iterations=1) # Smoothing
    middle_mask = (myocardium_array & (wall_depth >= inner_limit) & (wall_depth < middle_limit))
    outer_mask = (myocardium_array & (wall_depth >= middle_limit))

    # Convert masks to images
    inner_image = sitk.GetImageFromArray(inner_mask.astype(np.uint8))
    middle_image = sitk.GetImageFromArray(middle_mask.astype(np.uint8))
    outer_image = sitk.GetImageFromArray(outer_mask.astype(np.uint8))

    # Copy geometry
    inner_image.CopyInformation(myocardium_image)
    middle_image.CopyInformation(myocardium_image)
    outer_image.CopyInformation(myocardium_image)

    # Push to Slicer
    inner_labelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "InnerLayerLabelmap")
    middle_labelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "MiddleLayerLabelmap")
    outer_labelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "OuterLayerLabelmap")

    sitkUtils.PushVolumeToSlicer(inner_image, inner_labelmap)
    sitkUtils.PushVolumeToSlicer(middle_image, middle_labelmap)
    sitkUtils.PushVolumeToSlicer(outer_image, outer_labelmap)

    # Rename imported segments
    inner_id = import_labelmap_to_segmentation(inner_labelmap, segmentation_chambers_node)
    middle_id = import_labelmap_to_segmentation(middle_labelmap, segmentation_chambers_node)
    outer_id = import_labelmap_to_segmentation(outer_labelmap, segmentation_chambers_node)

    segmentation_chambers_node.GetSegmentation().GetSegment(inner_id).SetName("left myocardium inner")
    segmentation_chambers_node.GetSegmentation().GetSegment(middle_id).SetName("left myocardium middle")
    segmentation_chambers_node.GetSegmentation().GetSegment(outer_id).SetName("left myocardium outer")

    # Remove temporary labelmaps
    remove_nodes(inner_labelmap, middle_labelmap, outer_labelmap, myocardium_labelmap, ventricle_labelmap)

    return inner_id, middle_id, outer_id # Return segment IDs

# TODO: make a separate segment border function

def segment_scar(segmentation: slicer.vtkMRMLSegmentationNode, segmentation_effusion_node: slicer.vtkMRMLSegmentationNode, 
                 editor_widget: slicer.qMRMLSegmentEditorWidget, editor_node: slicer.vtkMRMLSegmentEditorNode, 
                 scar_segment_id: str, pleural_segment_id: str, border_segment_id: str) -> None:
    # TODO: write the docstring
    """ 
    Segment the scar by: 
    1. 
    """
    threshold_segment(editor_widget, editor_node, scar_segment_id, MIN_SCAR_THRESHOLD_VALUE, MAX_SCAR_THRESHOLD_VALUE)

    segmentation.CopySegmentFromSegmentation(segmentation_effusion_node.GetSegmentation(), pleural_segment_id)
    # Copy the Pleural Effusion into the Border segment 
    union_segments(editor_widget, editor_node, pleural_segment_id, border_segment_id)
    hollow_segment(editor_widget, editor_node, border_segment_id, 4.0, "INSIDE_SURFACE")

    subtract_segments(editor_widget, editor_node, border_segment_id, scar_segment_id)

def segment_scar_in_region(editor_widget: slicer.qMRMLSegmentEditorWidget, editor_node: slicer.vtkMRMLSegmentEditorNode, 
                           scar_segment_id: str, region_segment_id: str, destination_segment_id: str) -> None:
    # TODO: write doc string
    """
    Set the destination segment to be the intersection of the general scar and the target region
    """
    union_segments(editor_widget, editor_node, region_segment_id, destination_segment_id)
    intersect_segments(editor_widget, editor_node, scar_segment_id, destination_segment_id)
    # TODO: and subtract for better visual?


# TODO: come up with a better name than this
# TODO: find a better way to pass in all of the segment ids, such as a dictionary?
def segment_right_left_scar(editor_widget: slicer.qMRMLSegmentEditorWidget, editor_node: slicer.qMRMLSegmentEditorWidget, 
                            scar_segment_id: str, region_to_scar_segment_id: dict[str, str]) -> None:
    # TODO: write docstring and figure out this dict thing
    """left_myocardium_segment_id: str, left_myoccardium_inner_segment_id: str,
                            left_myocardium_middle_segment_id: str, left_myocardium_outer_segment_id: str,
                            right_myocardium_segment_id: str, scar_segment_id: str, left_scar_segment_id: str, 
                            left_scar_inner_segment_id: str, left_scar_middle_segment_id: str, left_scar_outer_segment_id: str, 
                            
    """

    for region_segment_id in region_to_scar_segment_id:
        segment_scar_in_region(editor_widget, editor_node, scar_segment_id, region_segment_id, region_to_scar_segment_id[region_segment_id])
    # TODO: smooth left and right scars??
    """segmentEditorWidget.setActiveEffectByName("Smoothing")
    setSegmentEditorNode(segmentEditorNode, leftScarSegmentID, True, EDITABLE_ANYWHERE, 
                        MIN_THRESHOLD_VALUE, MAX_SCAR_THRESHOLD_VALUE)

    effect = segmentEditorWidget.activeEffect()
    effect.setParameter("SmoothingMethod", "CLOSING")
    effect.setParameter("KernelSizeMm", "2.0")
    effect.self().onApply()

    # TODO: fix the magic numbers
    effect.setParameter("SmoothingMethod", "OPENING")
    effect.setParameter("KernelSizeMm", "1.2")
    effect.self().onApply()"""

