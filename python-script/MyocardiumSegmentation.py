import slicer
import DICOMLib

import SimpleITK as sitk
import sitkUtils
import numpy as np
import scipy.ndimage
import qt

from GlobalConstants import *

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
    spacingXYZ = myocardiumImage.GetSpacing() # TODO: spacing?
    spacing = spacingXYZ[::-1]

    print("done converting to numpy")
    # Find bounding box of myocardium by finding the coordinates that are non-zero
    coords = np.argwhere(myocardiumArray)

    if len(coords) == 0:
        raise RuntimeError("Myocardium segmentation is empty")

    zmin, ymin, xmin = coords.min(axis=0)
    zmax, ymax, xmax = coords.max(axis=0)

    # Add padding so the EDT can see the boundaries properly
    pad = 50 # TODO: magic number

    zmin = max(0, zmin - pad)
    ymin = max(0, ymin - pad)
    xmin = max(0, xmin - pad)

    zmax = min(myocardiumArray.shape[0], zmax + pad)
    ymax = min(myocardiumArray.shape[1], ymax + pad)
    xmax = min(myocardiumArray.shape[2], xmax + pad)

    # Crop arrays
    myocardiumCrop = myocardiumArray[zmin:zmax, ymin:ymax, xmin:xmax]
    ventricleCrop = ventricleArray[zmin:zmax, ymin:ymax, xmin:xmax]

    print("cropped shape")

    # Calculate distance to endocardium and epicardium
    distanceEndocardium = scipy.ndimage.distance_transform_edt(~ventricleCrop, sampling=spacing)
    distanceEpicardium = scipy.ndimage.distance_transform_edt(myocardiumCrop, sampling=spacing)
    
    print("done calculating distance")

    # Restrict to myocardium only
    distanceEndocardium = np.abs(distanceEndocardium)
    distanceEpicardium = np.maximum(distanceEpicardium, 0)

    # Calculate wall depth
    wallDepth = distanceEndocardium / (distanceEndocardium + distanceEpicardium + 1e-6) # to prevent division by 0
    wallDepth = np.nan_to_num(wallDepth, nan=0.0, posinf=1.0, neginf=0.0)
    wallDepth = np.clip(wallDepth, 0.0, 1.0)
    
    print("calculate wall depth")

    # Calculate percentile for inner layer, middle layer
    innerLimit = np.percentile(wallDepth[myocardiumCrop], INNER_MYOCARDIUM_LIMIT)
    middleLimit = np.percentile(wallDepth[myocardiumCrop], MIDDLE_MYOCARDIUM_LIMIT)

    # Create masks for the 3 segments 
    innerMask = (myocardiumCrop & (wallDepth < innerLimit)) 
    middleMask = (myocardiumCrop & (wallDepth >= innerLimit) & (wallDepth < middleLimit))
    outerMask = (myocardiumCrop & (wallDepth >= middleLimit))
    # innerMask = scipy.ndimage.binary_closing(innerMask, iterations=1)

    print("myocardium:", myocardiumCrop.sum()) # TODO: so i think the problem is in the myocariudm crop
    print("inner:", innerMask.sum())
    print("middle:", middleMask.sum())
    print("outer:", outerMask.sum())
    print("union:", (innerMask | middleMask | outerMask).sum())

    # Convert masks to images
    innerImage = sitk.GetImageFromArray(innerMask.astype(np.uint8))
    middleImage = sitk.GetImageFromArray(middleMask.astype(np.uint8))
    outerImage = sitk.GetImageFromArray(outerMask.astype(np.uint8))

    # Copy geometry
    referenceCrop = sitk.RegionOfInterest(myocardiumImage,
                                          size=[int(xmax-xmin), int(ymax-ymin), int(zmax-zmin)],
                                          index=[int(xmin), int(ymin), int(zmin)])

    innerImage.CopyInformation(referenceCrop)
    middleImage.CopyInformation(referenceCrop)
    outerImage.CopyInformation(referenceCrop)


    # Push to Slicer
    innerLabelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "InnerLayerLabelmap")
    middleLabelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "MiddleLayerLabelmap")
    outerLabelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "OuterLayerLabelmap")


    sitkUtils.PushVolumeToSlicer(innerImage, innerLabelmap)
    sitkUtils.PushVolumeToSlicer(middleImage, middleLabelmap)
    sitkUtils.PushVolumeToSlicer(outerImage, outerLabelmap)

    print("push to slicer")
    # Rename imported segments 
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
    # slicer.mrmlScene.RemoveNode(innerLabelmap)
    # slicer.mrmlScene.RemoveNode(middleLabelmap)
    # slicer.mrmlScene.RemoveNode(outerLabelmap)
    # slicer.mrmlScene.RemoveNode(myocardiumLabelmap)
    # slicer.mrmlScene.RemoveNode(ventricleLabelmap)

    return innerID, middleID, outerID # Return segment IDs

"""
def divideMyocardium2(segmentation: slicer.vtkMRMLSegmentationNode, volumeNode: slicer.vtkMRMLScalarVolumeNode,
                      segmentationChambersNode: slicer.vtkMRMLSegmentationNode, myocardiumSegmentID: str,
                      ventricleSegmentID: str) -> tuple[str, str, str]:

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
    # Convert the spacing to the right format
    spacingXYZ = myocardiumImage.GetSpacing()
    spacing = tuple(float(x) for x in spacingXYZ[::-1])

    print("done converting to numpy")

    # Crop to myocardium ROI to save processing power

    coords = np.argwhere(myocardiumArray)

    if len(coords) == 0:
        raise RuntimeError("Myocardium segmentation is empty")

    zmin, ymin, xmin = coords.min(axis=0)
    zmax, ymax, xmax = coords.max(axis=0)

    pad = 50 # TODO magic number

    zmin = max(0, zmin - pad)
    ymin = max(0, ymin - pad)
    xmin = max(0, xmin - pad)

    zmax = min(myocardiumArray.shape[0], zmax + pad)
    ymax = min(myocardiumArray.shape[1], ymax + pad)
    xmax = min(myocardiumArray.shape[2], xmax + pad)

    myocardiumCrop = myocardiumArray[zmin:zmax, ymin:ymax, xmin:xmax]
    ventricleCrop = ventricleArray[zmin:zmax, ymin:ymax, xmin:xmax]

    # Make distance transforms
    distanceEndocardium = scipy.ndimage.distance_transform_edt(~ventricleCrop, sampling=spacing)
    distanceEpicardium = scipy.ndimage.distance_transform_edt(~myocardiumCrop, sampling=spacing)

    # Wall depth calculation
    wallDepthCrop = distanceEndocardium / (distanceEndocardium + distanceEpicardium + 1e-6)
    wallDepthCrop = scipy.ndimage.gaussian_filter(wallDepthCrop)
    wallDepthCrop = np.nan_to_num(wallDepthCrop, nan=0.0, posinf=0.0, neginf=0.0)
    wallDepthCrop = np.clip(wallDepthCrop, 0.0, 1.0)

    # Calculate inner, middle, outer layer bounds
    innerLimit = np.percentile(wallDepthCrop[myocardiumCrop], INNER_MYOCARDIUM_LIMIT)
    middleLimit = np.percentile(wallDepthCrop[myocardiumCrop], MIDDLE_MYOCARDIUM_LIMIT)

    # Create cropped masks
    innerCrop = (myocardiumCrop & (wallDepthCrop < innerLimit))
    middleCrop = (myocardiumCrop & (wallDepthCrop >= innerLimit) & (wallDepthCrop < middleLimit))
    outerCrop = myocardiumCrop & ~(innerCrop | middleCrop)

    # Smooth the masks # TODO : delete
    # innerCrop = scipy.ndimage.binary_opening(innerCrop)
    # innerCrop = scipy.ndimage.binary_closing(innerCrop)
    # middleCrop = scipy.ndimage.binary_opening(middleCrop)
    # outerCrop = scipy.ndimage.binary_opening(outerCrop)

    innerCrop = innerCrop & myocardiumCrop
    middleCrop = middleCrop & myocardiumCrop
    outerCrop = outerCrop & myocardiumCrop

    combined = innerCrop | middleCrop | outerCrop
    print("myocardium voxels:", myocardiumCrop.sum())
    print("combined voxels:", combined.sum())
    print("missing voxels:", (myocardiumCrop & ~combined).sum())
    print("extra voxels:", (combined & ~myocardiumCrop).sum())

    # Expand masks back to original volume size
    innerMask = np.zeros_like(myocardiumArray, dtype=bool)
    middleMask = np.zeros_like(myocardiumArray, dtype=bool)
    outerMask = np.zeros_like(myocardiumArray, dtype=bool)

    innerMask[zmin:zmax, ymin:ymax, xmin:xmax] = innerCrop
    middleMask[zmin:zmax, ymin:ymax, xmin:xmax] = middleCrop
    outerMask[zmin:zmax, ymin:ymax, xmin:xmax] = outerCrop

    print("created layer masks")

    # Convert masks back to images
    innerImage = sitk.GetImageFromArray(innerMask.astype(np.uint8))
    middleImage = sitk.GetImageFromArray(middleMask.astype(np.uint8))
    outerImage = sitk.GetImageFromArray(outerMask.astype(np.uint8))

    innerImage.CopyInformation(myocardiumImage)
    middleImage.CopyInformation(myocardiumImage)
    outerImage.CopyInformation(myocardiumImage)

    # Push back to Slicer
    innerLabelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "InnerLayerLabelmap")
    middleLabelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "MiddleLayerLabelmap")
    outerLabelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "OuterLayerLabelmap")

    sitkUtils.PushVolumeToSlicer(innerImage, innerLabelmap)
    sitkUtils.PushVolumeToSlicer(middleImage, middleLabelmap)
    sitkUtils.PushVolumeToSlicer(outerImage, outerLabelmap)

    print("push to slicer")

    # Import into segmentation

    innerID = importLabelmap(innerLabelmap)
    middleID = importLabelmap(middleLabelmap)
    outerID = importLabelmap(outerLabelmap)

    segmentation.GetSegment(innerID).SetName("left myocardium inner")
    segmentation.GetSegment(middleID).SetName("left myocardium middle")
    segmentation.GetSegment(outerID).SetName("left myocardium outer")

    segmentation.GetSegment(innerID).SetColor(COLOUR_PURPLE)
    segmentation.GetSegment(middleID).SetColor(COLOUR_GREEN)
    segmentation.GetSegment(outerID).SetColor(COLOUR_LIGHT_BLUE)

    # Cleanup
    # slicer.mrmlScene.RemoveNode(innerLabelmap)
    # slicer.mrmlScene.RemoveNode(middleLabelmap)
    # slicer.mrmlScene.RemoveNode(outerLabelmap)

    # slicer.mrmlScene.RemoveNode(myocardiumLabelmap)
    # slicer.mrmlScene.RemoveNode(ventricleLabelmap)

    return innerID, middleID, outerID"""

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


#### Initialisation and setup ####

"""# Load NIFTI file, get Volume node
volumeNode = slicer.util.loadVolume(PATH_TO_NIFTI)
print("Loaded dataset from: ", PATH_TO_NIFTI)"""

# Error checking the path to input folder
if not PATH_TO_DICOM_FOLDER.exists() or not PATH_TO_DICOM_FOLDER.is_dir():
    print(f"Error: DICOM folder path '{PATH_TO_DICOM_FOLDER}' does not exist or is not a directory.")
    exit()  

# Load DICOM folder, get Volume node 
# TODO: create helper function to do this
with DICOMLib.DICOMUtils.TemporaryDICOMDatabase() as db:
    try:
        DICOMLib.DICOMUtils.importDicom(PATH_TO_DICOM_FOLDER, db) # Imports DICOM files into temp db
    except Exception as e:
        print(f"Error importing DICOM files: {e}")
        exit()
    patientUIDs = db.patients() # Get list of patient UIDs in database
    loadNodeIDs = DICOMLib.DICOMUtils.loadPatientByUID(patientUIDs[0]) # Load the first patient into the MRML scene
    if not loadNodeIDs:
        print("Error loading DICOM files into scene.")
        exit()

# Get loaded Volume Node
volumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")

print("Loaded dataset from: ", PATH_TO_DICOM_FOLDER)

# Adjust volume display settings including window and level 
# # TODO: move this to the end with the other visibility things?
volumeDisplayNode = volumeNode.GetDisplayNode()
volumeDisplayNode.SetWindow(DISPLAY_WINDOW)
volumeDisplayNode.SetLevel(DISPLAY_LEVEL)

# Load the saved segmentations
segmentationChambersNode = slicer.util.loadSegmentation(PATH_FOR_SAVE / SEGMENTATION_CHAMBERS_FILENAME)
segmentationChambersNode.SetName("Myocardium-Segmentation")
segmentationEffusionNode = slicer.util.loadSegmentation(PATH_FOR_SAVE / SEGMENTATION_EFFUSION_FILENAME)
segmentationEffusionNode.SetName("Effusion-Segmentation")
segmentationArteryNode = slicer.util.loadSegmentation(PATH_FOR_SAVE / SEGMENTATION_ARTERY_FILENAME)
segmentationArteryNode.SetName("Artery-Segmentation")
segmentationTissueNode = slicer.util.loadSegmentation(PATH_FOR_SAVE / SEGMENTATION_TISSUE_FILENAME)
segmentationTissueNode.SetName("Tissue-Segmentation")
# TODO: error checking for alignment of segmentation on top of the volume node?

# Create new segmentations for the right myocardium, left scar, right scar, setting their ID, name and colour
segmentation = segmentationChambersNode.GetSegmentation()
rightMyocardiumSegmentID = segmentation.AddEmptySegment("heart_myocardium_right", "right myocardium", COLOUR_PINK)
leftScarInnerSegmentID = segmentation.AddEmptySegment("heart_scar_left_inner", "left scar inner", COLOUR_ORANGE)
leftScarMiddleSegmentID = segmentation.AddEmptySegment("heart_scar_left_middle", "left scar middle", COLOUR_ORANGE)
leftScarOuterSegmentID = segmentation.AddEmptySegment("heart_scar_left_outer", "left scar outer", COLOUR_ORANGE)

scarSegmentID = segmentation.AddEmptySegment("heart_scar", "scar", COLOUR_YELLOW) # Colour scars yellow
leftScarSegmentID = segmentation.AddEmptySegment("heart_left_scar", "left scar", COLOUR_YELLOW)
rightScarSegmentID = segmentation.AddEmptySegment("heart_right_scar", "right scar", COLOUR_YELLOW)
borderSegmentID = segmentation.AddEmptySegment("heart_border", "border", COLOUR_BLUE) 
# TODO: change borderSegmentID into a temp segment id?, delete when done with it

# Error checking if segments were created successfully, if not print error message then exit
if not rightMyocardiumSegmentID or not scarSegmentID or not leftScarSegmentID or not rightScarSegmentID:
    print("Error creating segments")
    exit()

# Set the name of the old myocardium segment to be left myocardium, and save right ventricle segment ID for later use
# Working off assumption of consistent naming from TotalSegmentator, but should add error checking
pleuralEffusionSegmentID = segmentationEffusionNode.GetSegmentation().GetSegmentIdBySegmentName("lung_pleural") 
leftMyocardiumSegmentID = segmentation.GetSegmentIdBySegmentName("myocardium") 
# TODO: change this to be adaptive so it doesn't break if the naming changes
segmentation.GetSegment(leftMyocardiumSegmentID).SetName("left myocardium") 
leftVentricleSegmentID = segmentation.GetSegmentIdBySegmentName("left ventricle of heart") 
rightVentricleSegmentID = segmentation.GetSegmentIdBySegmentName("right ventricle of heart")
leftVentricleSegmentID = segmentation.GetSegmentIdBySegmentName("left ventricle of heart")

print("Created new segments for right myocardium, left scar and right scar")

# Create SegmentEditor Node from module # TODO: fix the order of editor node vs widget
segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode", "SegmentEditorNode")
segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode) # Set the Segment Editor node
# Create Segment Editor widget's MRML scene, segmentation node and volume node
segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
segmentEditorWidget.setSegmentationNode(segmentationChambersNode)
segmentEditorWidget.setSourceVolumeNode(volumeNode)


#### Segmenting the right myocardium ####
# Set Editor Widget to the Islands effect
segmentEditorWidget.setActiveEffectByName("Islands")
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


print("Finished segmenting right myocardium")

### Improving the segmentation of the left myocardium ####

# Grow the left myocardium segment so it covers more of the left muscle
# Set Editor Widget to the Margin effect 
segmentEditorWidget.setActiveEffectByName("Margin")
setSegmentEditorNode(segmentEditorNode, leftMyocardiumSegmentID, True, EDITABLE_OUTSIDE_ALL_SEGMENTS,
                     MIN_MYOCARDIUM_THRESHOLD_VALUE, MAX_MYOCARDIUM_THRESHOLD_VALUE)

# use Segment Editor effects to grow the left myocardium segment 
effect = segmentEditorWidget.activeEffect()
effect.setParameter("MarginSizeMm", LEFT_MYOCARDIUM_DEPTH)
# effect.self().onApply() # TODO: remove left growing?

print("Grew left myocardium")

# Smooth the left myocardium segment slightly 
segmentEditorWidget.setActiveEffectByName("Smoothing")
setSegmentEditorNode(segmentEditorNode, leftMyocardiumSegmentID, False, EDITABLE_ANYWHERE)

effect = segmentEditorWidget.activeEffect()
effect.setParameter("SmoothingMethod", "CLOSING")
effect.setParameter("KernelSizeMm", 1) # TODO: adjust size
effect.self().onApply()

effect.setParameter("SmoothingMethod", "MEDIAN")
effect.setParameter("KernelSizeMm", 1) # TODO: adjust size
effect.self().onApply()

print("done smoothing left myocardium")

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
    segmentation, volumeNode, segmentationChambersNode, leftMyocardiumSegmentID, leftVentricleSegmentID)

print("after dividing")

#### Segmenting the scar tissue ####

# Segment the General scar tissue using threshold
segmentEditorWidget.setActiveEffectByName("Threshold") # TODO: make a helper function for this mask parameter setting given the node
setSegmentEditorNode(segmentEditorNode, scarSegmentID, False, EDITABLE_ANYWHERE)

effect = segmentEditorWidget.activeEffect()
effect.setParameter("MinimumThreshold", str(MIN_SCAR_THRESHOLD_VALUE))
effect.setParameter("MaximumThreshold", str(MAX_SCAR_THRESHOLD_VALUE))
effect.self().onApply()

print("after threshold")

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
# unionSegments(segmentEditorWidget, segmentEditorNode, leftMyocardiumInnerSegmentID, leftScarInnerSegmentID)
# intersectSegments(scarSegmentID, leftScarInnerSegmentID)
# unionSegments(segmentEditorWidget, segmentEditorNode, leftMyocardiumMiddleSegmentID, leftScarMiddleSegmentID)
# intersectSegments(scarSegmentID, leftScarMiddleSegmentID)
# unionSegments(segmentEditorWidget, segmentEditorNode, leftMyocardiumOuterSegmentID, leftScarOuterSegmentID)
# intersectSegments(scarSegmentID, leftScarOuterSegmentID)



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

print("Finished segmenting scar tissue")

# TODO: make visible
# Change visibility so that only left myocardium, right myocardium, left scar and right scar are visible
# setSegmentsVisibility(segmentationChambersNode, segmentation, [leftMyocardiumInnerSegmentID, leftMyocardiumMiddleSegmentID, 
#                                                             leftMyocardiumOuterSegmentID, rightMyocardiumSegmentID, 
#                                                             leftScarSegmentID, rightScarSegmentID])
setSegmentsVisibility(segmentationChambersNode, segmentation, [leftMyocardiumInnerSegmentID, leftMyocardiumMiddleSegmentID, 
                                                            leftMyocardiumOuterSegmentID, rightMyocardiumSegmentID, 
                                                            leftScarSegmentID, rightScarSegmentID])

segmentationEffusionNode.GetDisplayNode().SetAllSegmentsVisibility(False)
segmentationArteryNode.GetDisplayNode().SetAllSegmentsVisibility(False)
segmentationTissueNode.GetDisplayNode().SetAllSegmentsVisibility(False)

print("Done segmentation!")



"""
# printing segment names
print("ID (internal), Name (display)")
for segmentId in segmentation.GetSegmentIDs():
    segment = segmentation.GetSegment(segmentId)
    print(segmentId, " --> ", segment.GetName())
"""
"""
# save, exit
segLogic = slicer.modules.segmentations.logic()
segLogic.ExportSegmentsClosedSurfaceRepresentationToFiles("segmentations", segmentationChambersNode)
print("Saved segmentation to: ", PATH_FOR_SAVE)
# slicer.util.exit()
"""
