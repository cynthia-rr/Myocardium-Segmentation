import slicer

import SimpleITK as sitk
import sitkUtils
import numpy as np
import scipy.ndimage

from constants import *
from segmentation_utils import *
#from io_utils import *

def segment_right_myocardium(editor_widget: slicer.qMRMLSegmentEditorWidget, editor_node: slicer.vtkMRMLSegmentEditorNode,
                             right_ventricle_segment_id: str, right_myocardium_segment_id: str) -> None:
    # TODO: write docstring?
    keep_largest_island(editor_widget, editor_node, right_ventricle_segment_id)
    union_segments(editor_widget, editor_node, right_ventricle_segment_id, right_myocardium_segment_id)
    hollow_segment(editor_widget, editor_node, right_myocardium_segment_id, 1.0, EDITABLE_ANYWHERE) # TODO: make 1.0 a constant
    grow_segment(editor_widget, editor_node, right_myocardium_segment_id, RIGHT_MYOCARDIUM_DEPTH, #TODO: remove the editable outside segments?
                 EDITABLE_OUTSIDE_ALL_SEGMENTS, MIN_MYOCARDIUM_THRESHOLD_VALUE, MAX_MYOCARDIUM_THRESHOLD_VALUE)
    smooth_segment(editor_widget, editor_node, right_myocardium_segment_id, RIGHT_MYOCARDIUM_DEPTH/2)


def improve_left_myocardium(segmentation: slicer.vtkMRMLSegmentationNode, editor_widget: slicer.qMRMLSegmentEditorWidget, 
                            editor_node: slicer.vtkMRMLSegmentEditorNode, left_ventricle_segment_id: str, 
                            left_myocardium_segment_id: str) -> None:
    # TODO: write docstring
    grow_segment(editor_widget, editor_node, left_myocardium_segment_id, LEFT_MYOCARDIUM_DEPTH, EDITABLE_OUTSIDE_ALL_SEGMENTS,
                     MIN_MYOCARDIUM_THRESHOLD_VALUE, MAX_MYOCARDIUM_THRESHOLD_VALUE)
    smooth_segment(editor_widget, editor_node, left_myocardium_segment_id, LEFT_MYOCARDIUM_DEPTH/2)
    create_closed_loop(segmentation, editor_widget, editor_node, left_myocardium_segment_id, left_ventricle_segment_id)

# Dividing left myocardium into inner, middle and outer layers # TODO: remove the segmentaiton?
def divide_myocardium(segmentation: slicer.vtkMRMLSegmentationNode, volume_node: slicer.vtkMRMLScalarVolumeNode,
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

    # Calculate wall depth
    wall_depth = distance_endocardium / (distance_endocardium + distance_epicardium + 1e-6) # to prevent division by 0
    wall_depth = scipy.ndimage.gaussian_filter(wall_depth, sigma=1.0) # TODO: magic numbers

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
    inner_id = import_labelmap_to_segmentation(inner_labelmap)
    middle_id = import_labelmap_to_segmentation(middle_labelmap)
    outer_id = import_labelmap_to_segmentation(outer_labelmap)

    segmentation.GetSegment(inner_id).SetName("left myocardium inner")
    segmentation.GetSegment(middle_id).SetName("left myocardium middle")
    segmentation.GetSegment(outer_id).SetName("left myocardium outer")

    segmentation.GetSegment(inner_id).SetColor(COLOUR_PURPLE)
    segmentation.GetSegment(middle_id).SetColor(COLOUR_GREEN)
    segmentation.GetSegment(outer_id).SetColor(COLOUR_LIGHT_BLUE)

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






##################################################################################################
"""
# Helper functions for segment manipulation
# Set the segment editor node settings, including selected segment, maskon/off, mask mode, thresholds
def setSegmentEditorNode(segmentEditorNode: slicer.vtkMRMLSegmentEditorNode, selectedSegmentID: str, 
                         maskOn: bool, maskMode: int, minBound:int = 0, maxBound: int = 0) -> None:

    segmentEditorNode.SetSelectedSegmentID(selectedSegmentID)
    segmentEditorNode.SetOverwriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteNone)
    segmentEditorNode.SetMaskMode(maskMode)
    segmentEditorNode.SetSourceVolumeIntensityMask(maskOn)
    if maskOn:
        segmentEditorNode.SetSourceVolumeIntensityMaskRange(minBound, maxBound)

def unionSegments(segmentEditorWidget: slicer.qMRMLSegmentEditorWidget, segmentEditorNode: slicer.vtkMRMLSegmentEditorNode,
                sourceSegmentID: str, destinationSegmentID: str) -> None:
    # Set Editor Widget to the Logical Operators effect 
    segmentEditorWidget.setActiveEffectByName("Logical operators")
    # Set the Segment Editor Node to right myocardium segment
    segmentEditorNode.SetSelectedSegmentID(destinationSegmentID) 
    segmentEditorNode.SetOverwriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteNone)
    segmentEditorNode.SetMaskMode(EDITABLE_ANYWHERE) # Set to editable area anywhere
    segmentEditorNode.SetSourceVolumeIntensityMask(False)
    
    # Use Union to copy the source segment into the destination segment
    effect = segmentEditorWidget.activeEffect()
    effect.setParameter("Operation", "UNION")
    effect.setParameter("ModifierSegmentID", sourceSegmentID) 
    effect.self().onApply()

# Use union to copy the left/right myocardium segment into the left/right scar segment, 
# then take the intersection with the scar segment to get the scar within the myocardium
def intersectSegments(sourceSegmentID: str, destinationSegmentID: str) -> None:
    segmentEditorWidget.setActiveEffectByName("Logical operators")
    segmentEditorNode.SetSelectedSegmentID(destinationSegmentID) # change selected segment
    segmentEditorNode.SetOverwriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteNone)
    segmentEditorNode.SetMaskMode(EDITABLE_ANYWHERE) # Set to editable area anywhere
    segmentEditorNode.SetSourceVolumeIntensityMask(False)

    effect = segmentEditorWidget.activeEffect()
    effect.setParameter("Operation", "INTERSECT")
    effect.setParameter("ModifierSegmentID", sourceSegmentID) 
    effect.self().onApply() 

# Importing labelmap into segment, and returning the ID
def importLabelmap(labelmap: slicer.vtkMRMLLabelMapVolumeNode) -> str:
    oldIDs = set(segmentation.GetSegmentIDs())
    slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(labelmap, segmentationChambersNode) 
    # TODO ^ replace segmentation chambers node
    newIDs = set(segmentation.GetSegmentIDs())
    return list(newIDs - oldIDs)[0]

# Dividing left myocardium into inner, middle and outer layers # TODO: remove the segmentaiton?
def divideMyocardium(segmentation: slicer.vtkMRMLSegmentationNode, volumeNode: slicer.vtkMRMLScalarVolumeNode,
                    segmentationChambersNode: slicer.vtkMRMLSegmentationNode, 
                    myocardiumSegmentID: str, ventricleSegmentID:str) -> tuple[str, str, str]:
    
    # Export myocardium to myocardiumlabel map
    myocardiumLabelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "MyocardiumLabelMap")
    slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(segmentationChambersNode, [str(myocardiumSegmentID)],
                                                                      myocardiumLabelmap, volumeNode)
    
    # Export left ventricle segment to ventricle label map
    ventricleLabelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "VentricleLabelMap")
    slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(segmentationChambersNode, [str(ventricleSegmentID)], 
                                                                      ventricleLabelmap, volumeNode)

    # Convert from label map to numpy
    myocardiumImage = sitkUtils.PullVolumeFromSlicer(myocardiumLabelmap)
    ventricleImage = sitkUtils.PullVolumeFromSlicer(ventricleLabelmap)
    
    myocardiumArray = sitk.GetArrayFromImage(myocardiumImage).astype(bool)
    ventricleArray = sitk.GetArrayFromImage(ventricleImage).astype(bool)
    spacingXYZ = myocardiumImage.GetSpacing()
    spacing = spacingXYZ[::-1]

    # Make endocardial and epicardial surfaces 
    endocardiumSurface = (scipy.ndimage.binary_dilation(ventricleArray) & myocardiumArray)
    epicardiumSurface = (~scipy.ndimage.binary_erosion(myocardiumArray) & myocardiumArray)


    # Calculate distance to endocardium and epicardium
    distanceEndocardium = scipy.ndimage.distance_transform_edt(~ventricleArray, sampling=spacing)
    distanceEpicardium = scipy.ndimage.distance_transform_edt(myocardiumArray, sampling=spacing)
    

    # Restrict to myocardium only
    distanceEndocardium = np.abs(distanceEndocardium)
    distanceEpicardium = np.maximum(distanceEpicardium, 0)

    # Calculate wall depth
    wallDepth = distanceEndocardium / (distanceEndocardium + distanceEpicardium + 1e-6) # to prevent division by 0
    wallDepth = scipy.ndimage.gaussian_filter(wallDepth, sigma=1.0)

    # Calculate percentile for inner layer, middle layer
    innerLimit = np.percentile(wallDepth[myocardiumArray], INNER_MYOCARDIUM_LIMIT)
    middleLimit = np.percentile(wallDepth[myocardiumArray], MIDDLE_MYOCARDIUM_LIMIT)

    # Create masks for the 3 segments 
    innerMask = (myocardiumArray & (wallDepth < innerLimit)) 
    middleMask = (myocardiumArray & (wallDepth >= innerLimit) & (wallDepth < middleLimit))
    outerMask = (myocardiumArray & (wallDepth >= middleLimit))
    innerMask = scipy.ndimage.binary_closing(innerMask, iterations=1)

    # Convert masks to images
    innerImage = sitk.GetImageFromArray(innerMask.astype(np.uint8))
    middleImage = sitk.GetImageFromArray(middleMask.astype(np.uint8))
    outerImage = sitk.GetImageFromArray(outerMask.astype(np.uint8))

    # Copy geometry
    innerImage.CopyInformation(myocardiumImage)
    middleImage.CopyInformation(myocardiumImage)
    outerImage.CopyInformation(myocardiumImage)

    # Push to Slicer
    innerLabelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "InnerLayerLabelmap")
    middleLabelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "MiddleLayerLabelmap")
    outerLabelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "OuterLayerLabelmap")

    sitkUtils.PushVolumeToSlicer(innerImage, innerLabelmap)
    sitkUtils.PushVolumeToSlicer(middleImage, middleLabelmap)
    sitkUtils.PushVolumeToSlicer(outerImage, outerLabelmap)

    # Rename imported segments # TODO: idk fixx this, is the label map empty?
    innerID = importLabelmap(innerLabelmap)
    middleID = importLabelmap(middleLabelmap)
    outerID = importLabelmap(outerLabelmap)

    segmentation.GetSegment(innerID).SetName("left myocardium inner")
    segmentation.GetSegment(middleID).SetName("left myocardium middle")
    segmentation.GetSegment(outerID).SetName("left myocardium outer")

    segmentation.GetSegment(innerID).SetColor(COLOUR_PURPLE)
    segmentation.GetSegment(middleID).SetColor(COLOUR_GREEN)
    segmentation.GetSegment(outerID).SetColor(COLOUR_LIGHT_BLUE)

    # Remove temporary labelmaps
    slicer.mrmlScene.RemoveNode(innerLabelmap)
    slicer.mrmlScene.RemoveNode(middleLabelmap)
    slicer.mrmlScene.RemoveNode(outerLabelmap)
    slicer.mrmlScene.RemoveNode(myocardiumLabelmap)
    slicer.mrmlScene.RemoveNode(ventricleLabelmap)

    return innerID, middleID, outerID # Return segment IDs

# Make the Myocardium (left, right) and Scar (left, right) segments visible, hide the rest
# and show the centred 3D view of the segments
def setSegmentsVisibility(segmentationNode: slicer.vtkMRMLSegmentationNode, 
                              segmentation: slicer.vtkMRMLSegmentationNode, 
                              visibleSegmentIDs: list[str]) -> None:
    for segmentID in segmentation.GetSegmentIDs():
        segmentationNode.GetDisplayNode().SetSegmentVisibility(segmentID, False)
    for segmentID in visibleSegmentIDs:
        segmentationNode.GetDisplayNode().SetSegmentVisibility(segmentID, True)

    # Show the segmentations in 3D, and center the 3D view
    segmentationNode.CreateClosedSurfaceRepresentation() 
    segmentationNode.GetDisplayNode().SetVisibility3D(True)
    slicer.app.layoutManager().threeDWidget(0).threeDView().resetFocalPoint()

"""
#### Segmenting the right myocardium ####
# Set Editor Widget to the Islands effect
"""segmentEditorWidget.setActiveEffectByName("Islands")
setSegmentEditorNode(segmentEditorNode, rightVentricleSegmentID, False, EDITABLE_ANYWHERE)

# Keep only the largest island, remove small blobs
effect = segmentEditorWidget.activeEffect()
effect.setParameter("Operation", "KEEP_LARGEST_ISLAND")
effect.self().onApply()

unionSegments(segmentEditorWidget, segmentEditorNode, rightVentricleSegmentID, rightMyocardiumSegmentID)

# Start from the right ventricle segment, and hollow it to get the smallest border possible
segmentEditorWidget.setActiveEffectByName("Hollow") # TODO: put the hollow at the end, union with hollow AFTER growing
setSegmentEditorNode(segmentEditorNode, rightMyocardiumSegmentID, False, EDITABLE_ANYWHERE)

effect = segmentEditorWidget.activeEffect()
effect.setParameter("ApplyToAllVisibleSegments", 0)
effect.setParameter("ShellMode", "OUTSIDE_SURFACE")
effect.setParameter("ShellThicknessMm", "1.0")
effect.self().onApply()

# Set Editor Widget to the Margin effect 
segmentEditorWidget.setActiveEffectByName("Margin")
setSegmentEditorNode(segmentEditorNode, rightMyocardiumSegmentID, True, EDITABLE_ANYWHERE, 
                     MIN_MYOCARDIUM_THRESHOLD_VALUE, MAX_MYOCARDIUM_THRESHOLD_VALUE)

# use Segment Editor effects to grow the right segment by ??mm, with relevant parameters
effect = segmentEditorWidget.activeEffect()
effect.setParameter("MarginSizeMm", RIGHT_MYOCARDIUM_DEPTH) 
effect.self().onApply()

# Smooth the right myocardium segment slightly 
segmentEditorWidget.setActiveEffectByName("Smoothing")
setSegmentEditorNode(segmentEditorNode, rightMyocardiumSegmentID, False, EDITABLE_ANYWHERE)

effect = segmentEditorWidget.activeEffect()
effect.setParameter("SmoothingMethod", "CLOSING")
effect.setParameter("KernelSizeMm", (RIGHT_MYOCARDIUM_DEPTH/2)) # TODO: make this mm = 50% of the entire myocardium thickcness?
effect.self().onApply()

effect.setParameter("SmoothingMethod", "MEDIAN")
effect.setParameter("KernelSizeMm", (RIGHT_MYOCARDIUM_DEPTH/2))
effect.self().onApply()


print("Finished segmenting right myocardium")"""

### Improving the segmentation of the left myocardium ####
"""
# Grow the left myocardium segment so it covers more of the left muscle
# Set Editor Widget to the Margin effect 
segmentEditorWidget.setActiveEffectByName("Margin")
setSegmentEditorNode(segmentEditorNode, leftMyocardiumSegmentID, True, EDITABLE_OUTSIDE_ALL_SEGMENTS,
                     MIN_MYOCARDIUM_THRESHOLD_VALUE, MAX_MYOCARDIUM_THRESHOLD_VALUE)

# use Segment Editor effects to grow the left myocardium segment 
effect = segmentEditorWidget.activeEffect()
effect.setParameter("MarginSizeMm", LEFT_MYOCARDIUM_DEPTH)
effect.self().onApply()

# Smooth the left myocardium segment slightly 
segmentEditorWidget.setActiveEffectByName("Smoothing")
setSegmentEditorNode(segmentEditorNode, leftMyocardiumSegmentID, False, EDITABLE_ANYWHERE)

effect = segmentEditorWidget.activeEffect()
effect.setParameter("SmoothingMethod", "CLOSING")
effect.setParameter("KernelSizeMm", LEFT_MYOCARDIUM_DEPTH/2) # TODO: adjust size
effect.self().onApply()

effect.setParameter("SmoothingMethod", "MEDIAN")
effect.setParameter("KernelSizeMm", LEFT_MYOCARDIUM_DEPTH/2) # TODO: adjust size
effect.self().onApply()

# Use Hollow effect on left ventricle, then union to left myocardium to make it a closed loop
# Create temporary segment for the hollowed left ventricle
tempSegmentID = segmentation.AddEmptySegment("hollow-left-ventricle", "hollow", COLOUR_GREEN)

# Copy in left ventricle
unionSegments(segmentEditorWidget, segmentEditorNode, leftVentricleSegmentID, tempSegmentID)

segmentEditorWidget.setActiveEffectByName("Hollow")
setSegmentEditorNode(segmentEditorNode, tempSegmentID, False, EDITABLE_ANYWHERE)

effect = segmentEditorWidget.activeEffect()
effect.setParameter("ApplyToAllVisibleSegments", 0)
effect.setParameter("ShellMode", "INSIDE_SURFACE")
effect.setParameter("ShellThicknessMm", "1.0")
effect.self().onApply()

# Union left myocardium with the shell of the left ventricle to make a closed loop
unionSegments(segmentEditorWidget, segmentEditorNode, tempSegmentID, leftMyocardiumSegmentID)

# TODO: divide myocaridum into 3 layers
# TODO: change this to be adaptive so it doesn't break if the naming changes
leftMyocardiumInnerSegmentID, leftMyocardiumMiddleSegmentID, leftMyocardiumOuterSegmentID = divideMyocardium(
    segmentation, volumeNode, segmentationChambersNode, leftMyocardiumSegmentID, leftVentricleSegmentID)"""

#### Segmenting the scar tissue ####

"""# Segment the General scar tissue using threshold
segmentEditorWidget.setActiveEffectByName("Threshold") # TODO: make a helper function for this mask parameter setting given the node
setSegmentEditorNode(segmentEditorNode, scarSegmentID, False, EDITABLE_ANYWHERE)

effect = segmentEditorWidget.activeEffect()
effect.setParameter("MinimumThreshold", str(MIN_SCAR_THRESHOLD_VALUE))
effect.setParameter("MaximumThreshold", str(MAX_SCAR_THRESHOLD_VALUE))
effect.self().onApply()

# Ensure that the dark border around the left/right myocardium is not mistakenly included in the General scar
# Copy the Pleural Effusion segment from the Pleural/Pericardial Effusion segmentation to the Myocardium-Segmentation
segmentation.CopySegmentFromSegmentation(segmentationEffusionNode.GetSegmentation(), pleuralEffusionSegmentID)
# Copy the Pleural Effusion into the Border segment 
unionSegments(segmentEditorWidget, segmentEditorNode, pleuralEffusionSegmentID, borderSegmentID)

# Use the Hollow tool to draw the border of the heart tissue using the Pleural Effusion segment
segmentEditorWidget.setActiveEffectByName("Hollow")
setSegmentEditorNode(segmentEditorNode, borderSegmentID, False, EDITABLE_ANYWHERE)

effect = segmentEditorWidget.activeEffect()
effect.setParameter("ShellThicknessMm", "4.0") # TODO: magic number
effect.setParameter("ShellMode", "INSIDE_SURFACE")
effect.setParameter("ApplyToAllVisibleSegments", "0")
effect.self().onApply()


# Subtract the Border from the Scar segment (Scar = Scar - Border)
# TODO
# Set Editor Widget to the Logical Operators effect 
segmentEditorWidget.setActiveEffectByName("Logical operators")
setSegmentEditorNode(segmentEditorNode, scarSegmentID, False, EDITABLE_ANYWHERE)

# Use Subtract to take out the border from the scar segment
effect = segmentEditorWidget.activeEffect()
effect.setParameter("Operation", "SUBTRACT")
effect.setParameter("ModifierSegmentID", borderSegmentID) 
effect.self().onApply()


# Copy the left/right myocardium into the left/right scar segments
# Set the left/right scar segments by taking the intersection of the general scar and left/right myocardium segments
unionSegments(segmentEditorWidget, segmentEditorNode, leftMyocardiumSegmentID, leftScarSegmentID)
intersectSegments(scarSegmentID, leftScarSegmentID)
unionSegments(segmentEditorWidget, segmentEditorNode, rightMyocardiumSegmentID, rightScarSegmentID)
intersectSegments(scarSegmentID, rightScarSegmentID)

# Fill in the left scar inner, middle, outer segments appropriately
unionSegments(segmentEditorWidget, segmentEditorNode, leftMyocardiumInnerSegmentID, leftScarInnerSegmentID)
intersectSegments(scarSegmentID, leftScarInnerSegmentID)
unionSegments(segmentEditorWidget, segmentEditorNode, leftMyocardiumMiddleSegmentID, leftScarMiddleSegmentID)
intersectSegments(scarSegmentID, leftScarMiddleSegmentID)
unionSegments(segmentEditorWidget, segmentEditorNode, leftMyocardiumOuterSegmentID, leftScarOuterSegmentID)
intersectSegments(scarSegmentID, leftScarOuterSegmentID)



# Smooth the right scar segment slightly # TODO: remove this if it is unhelpful
# TODO: make a smoothing function, with segmentID, mask thresholds, and type of smoothing as parameters, to avoid repeating code
segmentEditorWidget.setActiveEffectByName("Smoothing")
setSegmentEditorNode(segmentEditorNode, rightScarSegmentID, True, EDITABLE_ANYWHERE, 
                     MIN_THRESHOLD_VALUE, MAX_SCAR_THRESHOLD_VALUE)

effect = segmentEditorWidget.activeEffect()
effect.setParameter("SmoothingMethod", "CLOSING")
effect.setParameter("KernelSizeMm", "2.0")
effect.self().onApply()

# TODO: fix the magic numbers
effect.setParameter("SmoothingMethod", "OPENING")
effect.setParameter("KernelSizeMm", "1.2")
effect.self().onApply()

# Smooth the LEFT scar segment slightly 
segmentEditorWidget.setActiveEffectByName("Smoothing")
setSegmentEditorNode(segmentEditorNode, leftScarSegmentID, True, EDITABLE_ANYWHERE, 
                     MIN_THRESHOLD_VALUE, MAX_SCAR_THRESHOLD_VALUE)

effect = segmentEditorWidget.activeEffect()
effect.setParameter("SmoothingMethod", "CLOSING")
effect.setParameter("KernelSizeMm", "2.0")
effect.self().onApply()

# TODO: fix the magic numbers
effect.setParameter("SmoothingMethod", "OPENING")
effect.setParameter("KernelSizeMm", "1.2")
effect.self().onApply()

print("Finished segmenting scar tissue")"""


# Change visibility so that only left myocardium, right myocardium, left scar and right scar are visible
"""setSegmentsVisibility(segmentationChambersNode, segmentation, [leftMyocardiumInnerSegmentID, leftMyocardiumMiddleSegmentID, 
                    leftMyocardiumOuterSegmentID, rightMyocardiumSegmentID, leftScarInnerSegmentID, 
                    leftScarMiddleSegmentID, leftScarOuterSegmentID,rightScarSegmentID])
segmentationEffusionNode.GetDisplayNode().SetAllSegmentsVisibility(False)
segmentationArteryNode.GetDisplayNode().SetAllSegmentsVisibility(False)

print("Done segmentation!")"""

