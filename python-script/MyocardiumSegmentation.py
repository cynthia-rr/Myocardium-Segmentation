import slicer
import DICOMLib
from GlobalConstants import *
import numpy as np
import SimpleITK as sitk
import sitkUtils
import vtk
import scipy

# TODO: unsure about this saving file stuff

# Make the Myocardium (left, right) and Scar (left, right) segments visible, hide the rest
# and show the centred 3D view of the segments
def setMyocardiumScarsVisible(segmentationDisplayNode: slicer.vtkMRMLSegmentationDisplayNode, 
                              segmentation: slicer.vtkMRMLSegmentationNode, 
                              visibleSegmentIDs: list[str]) -> None:
    for segmentID in segmentation.GetSegmentIDs():
        segmentationDisplayNode.SetSegmentVisibility(segmentID, False)
    for segmentID in visibleSegmentIDs:
        segmentationDisplayNode.SetSegmentVisibility(segmentID, True)

    # Show the segmentations in 3D, and center the 3D view
    segmentationChambersNode.CreateClosedSurfaceRepresentation()
    segmentationDisplayNode.SetVisibility3D(True)
    slicer.app.layoutManager().threeDWidget(0).threeDView().resetFocalPoint()

# Use union to copy the left/right myocardium segment into the left/right scar segment, 
# then take the intersection with the scar segment to get the scar within the myocardium
def segmentScarInMyocardium(outputSegmentID: str, entireScarSegmentID: str, partialMyocardiumSegmentID:str) -> None:
    segmentEditorWidget.setActiveEffectByName("Logical operators")
    segmentEditorNode.SetSelectedSegmentID(outputSegmentID) # change selected segment
    effect = segmentEditorWidget.activeEffect()
    effect.setParameter("Operation", "UNION")
    effect.setParameter("ModifierSegmentID", partialMyocardiumSegmentID) 
    effect.self().onApply() # copy the myocardium segment into the output segment
    effect.setParameter("Operation", "INTERSECT")
    effect.setParameter("ModifierSegmentID", entireScarSegmentID)
    effect.self().onApply() # scar segment = myocardium *intersection* scar segment


# Importing labelmap into segment, and returning the ID
def importLabelmap(labelmap: slicer.vtkMRMLLabelMapVolumeNode) -> str:
    oldIDs = set(segmentation.GetSegmentIDs())
    print(oldIDs)
    slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(labelmap, segmentationChambersNode)
    newIDs = set(segmentation.GetSegmentIDs())
    print(newIDs)
    return list(oldIDs - newIDs)[0]

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

    # Convert from labelmaps to SimpleITK images
    myocardiumImage = sitkUtils.PullVolumeFromSlicer(myocardiumLabelmap)
    ventricleImage = sitkUtils.PullVolumeFromSlicer(ventricleLabelmap)
    
    myocardiumArray = sitk.GetArrayFromImage(myocardiumImage) # TODO: replace the smoothing if needed
    #myocardiumArray = scipy.ndimage.binary_fill_holes(myocardiumArray) # Fill holes in myocardium to make it a solid mask, so that distance maps are accurate
    ventricleArray = sitk.GetArrayFromImage(ventricleImage)

    # Calculate distance to myocardium (outer) boundary (epicardium)
    epicardiumDistance = sitk.SignedMaurerDistanceMap(sitk.GetImageFromArray(myocardiumArray.astype(np.uint8)), 
                                                      insideIsPositive=True, squaredDistance=False, useImageSpacing=True)
    
    epicardiumDistanceArray = sitk.GetArrayFromImage(epicardiumDistance) # TODO: does this need to be abs?
    #epicardiumDistanceArray = np.maximum(epicardiumDistanceArray, 0) # TODO: remove if not needed

    # Calculate distance to ventricle (endocardium)
    endocardiumDistance = sitk.SignedMaurerDistanceMap(sitk.GetImageFromArray(ventricleArray.astype(np.uint8)), 
                                                       insideIsPositive=True, squaredDistance=False, useImageSpacing=True)
    endocardiumDistanceArray = sitk.GetArrayFromImage(endocardiumDistance) # TODO: does this need to be abs?
    #endocardiumDistanceArray = np.maximum(endocardiumDistanceArray, 0) # TODO: remove if unneeded

    # Compute wall thickness # TODO: check this math
    denominator = epicardiumDistanceArray - endocardiumDistanceArray + 1e-6
    wallDepth = epicardiumDistanceArray / denominator    

    # Restrict to myocardium only
    myocardiumMask = myocardiumArray.astype(bool)

    # Create masks for the 3 segments
    innerMask = (myocardiumMask & (wallDepth >= 0) & (wallDepth < 1/3))
    middleMask = (myocardiumMask & (wallDepth >= 1/3) & (wallDepth < 2/3))
    outerMask = (myocardiumMask & (wallDepth >= 2/3) & (wallDepth <= 1))

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

    # Import labelmaps into segmentation
    # slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(innerLabelmap, segmentationChambersNode, "InnerLayerLabelmap")
    # slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(middleLabelmap, segmentationChambersNode, "MiddleLayerLabelmap")
    # slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(outerLabelmap, segmentationChambersNode, "OuterLayerLabelmap")

    arr = slicer.util.arrayFromVolume(innerLabelmap)

    print("Unique values:", np.unique(arr))
    print("Nonzero voxels:", np.count_nonzero(arr))

    # Rename imported segments # TODO: idk fixx this, is the label map empty?
    innerID = importLabelmap(innerLabelmap)
    middleID = importLabelmap(middleLabelmap)
    outerID = importLabelmap(outerLabelmap)

    segmentation.GetSegment(innerID).SetName("left myocardium inner")
    segmentation.GetSegment(middleID).SetName("left myocardium middle")
    segmentation.GetSegment(outerID).SetName("left myocardium outer")

    segmentation.GetSegment(innerID).SetColor(1.0, 0.0, 0.0)
    segmentation.GetSegment(middleID).SetColor(1.0, 0.0, 0.0)
    segmentation.GetSegment(outerID).SetColor(1.0, 0.0, 0.0)

    # Remove temporary labelmaps
    slicer.mrmlScene.RemoveNode(innerLabelmap)
    slicer.mrmlScene.RemoveNode(middleLabelmap)
    slicer.mrmlScene.RemoveNode(outerLabelmap)
    slicer.mrmlScene.RemoveNode(myocardiumLabelmap)
    slicer.mrmlScene.RemoveNode(ventricleLabelmap)

    return innerID, middleID, outerID # Return segment IDs




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
volumeDisplayNode = volumeNode.GetDisplayNode()
volumeDisplayNode.SetWindow(DISPLAY_WINDOW)
volumeDisplayNode.SetLevel(DISPLAY_LEVEL)

# Load the saved segmentations
segmentationChambersNode = slicer.util.loadSegmentation(PATH_FOR_SAVE / SEGMENTATION_CHAMBERS_FILENAME)
segmentationChambersNode.SetName("Myocardium-Segmentation")
segmentationEffusionNode = slicer.util.loadSegmentation(PATH_FOR_SAVE / SEGMENTATION_EFFUSION_FILENAME)
segmentationEffusionNode.SetName("Effusion-Segmentation")
# TODO: error checking for alignment of segmentation on top of the volume node?



# Create new segmentations for the right myocardium, left scar, right scar, setting their ID, name and colour
segmentation = segmentationChambersNode.GetSegmentation()
rightMyocardiumSegmentID = segmentation.AddEmptySegment("heart_myocardium_right", "right myocardium", [0.5, 0.0, 0.0])
scarSegmentID = segmentation.AddEmptySegment("heart_scar", "scar", [1.0, 1.0, 0.0]) # Colour scars yellow
leftScarSegmentID = segmentation.AddEmptySegment("heart_scar_left", "left scar", [1.0, 1.0, 0.0])
rightScarSegmentID = segmentation.AddEmptySegment("heart_scar_right", "right scar", [1.0, 1.0, 0.0])
borderSegmentID = segmentation.AddEmptySegment("heart_border", "border", [0.0, 0.5, 1.0])

# Error checking if segments were created successfully, if not print error message then exit
if not rightMyocardiumSegmentID or not scarSegmentID or not leftScarSegmentID or not rightScarSegmentID:
    print("Error creating segments")
    exit()

# Set the name of the old myocardium segment to be left myocardium, and save right ventricle segment ID for later use
# Working off assumption of consistent naming from TotalSegmentator, but should add error checking
pleuralEffusionSegmentID = segmentation.GetSegmentIdBySegmentName("") # TODO: add the name of the pleural effusion segmentation
leftMyocardiumSegmentID = segmentation.GetSegmentIdBySegmentName("myocardium") 
# TODO: change this to be adaptive so it doesn't break if the naming changes
segmentation.GetSegment(leftMyocardiumSegmentID).SetName("left myocardium") 
rightVentricleSegmentID = segmentation.GetSegmentIdBySegmentName("right ventricle of heart")

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
# Set the selected segment to the right ventricle
segmentEditorNode.SetSelectedSegmentID(rightVentricleSegmentID)

# Keep only the largest island, remove small blobs
effect = segmentEditorWidget.activeEffect()
effect.setParameter("Operation", "KEEP_LARGEST_ISLAND")
effect.self().onApply()


# Set Editor Widget to the Logical Operators effect 
segmentEditorWidget.setActiveEffectByName("Logical operators")
# Set the Segment Editor Node to right myocardium segment
segmentEditorNode.SetSelectedSegmentID(rightMyocardiumSegmentID) 

# Use Union to copy the right ventricle into the right myocardium segment
effect = segmentEditorWidget.activeEffect()
effect.setParameter("Operation", "UNION")
effect.setParameter("ModifierSegmentID", rightVentricleSegmentID) 
effect.self().onApply()


# Set Editor Widget to the Margin effect 
# # TODO: union also with a hollow shell of the right ventricle, 
# so that there are no gaping holes in the myocardium (and can do division by 3 layers)
segmentEditorWidget.setActiveEffectByName("Margin")
# Set the Segment Editor Node to right myocardium segment
segmentEditorNode.SetSelectedSegmentID(rightMyocardiumSegmentID)
# Set the Segment Editor node settings
# (editable area, editable intensity range, overwrite)
segmentEditorNode.SetSourceVolumeIntensityMask(True)
segmentEditorNode.SetSourceVolumeIntensityMaskRange(MIN_MYOCARDIUM_THRESHOLD_VALUE, MAX_MYOCARDIUM_THRESHOLD_VALUE)
segmentEditorNode.SetOverwriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteNone)

# use Segment Editor effects to grow the right segment by 7.0mm, with relevant parameters
effect = segmentEditorWidget.activeEffect()
effect.setParameter("MarginSizeMm", "7.0") # TODO: how to determine width of right myocardium
effect.self().onApply()

# subtract the right ventricle from the right myocardium segment to get the final right myocardium segmentation
segmentEditorWidget.setActiveEffectByName("Logical operators")
segmentEditorNode.SetSelectedSegmentID(rightMyocardiumSegmentID) ####### TODO: should prob make this cleaner
segmentEditorNode.SetSourceVolumeIntensityMask(False)

effect = segmentEditorWidget.activeEffect()
effect.setParameter("Operation", "SUBTRACT") #TODO: change this to hollow?
effect.setParameter("ModifierSegmentID", rightVentricleSegmentID) 
effect.self().onApply()


# Smooth the right myocardium segment slightly # TODO: remove this if it is unhelpful
# TODO: repeat for the left side, if it is helpful
segmentEditorWidget.setActiveEffectByName("Smoothing")
segmentEditorNode.SetSelectedSegmentID(rightMyocardiumSegmentID)
segmentEditorNode.SetSourceVolumeIntensityMask(True)
segmentEditorNode.SetSourceVolumeIntensityMaskRange(MIN_THRESHOLD_VALUE, MIN_MYOCARDIUM_THRESHOLD_VALUE)
segmentEditorNode.SetOverwriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteNone)

 # TODO: there is a problem here with the smoothing, with the healthy version (the threshold values?)
effect = segmentEditorWidget.activeEffect()
effect.setParameter("SmoothingMethod", "CLOSING")
effect.setParameter("KernelSizeMm", "3.0") # TODO: make this 50% of the entire myocardium thickcness?
effect.self().onApply()

segmentEditorNode.SetSourceVolumeIntensityMask(False) # Median smoothing anywhere
effect.setParameter("SmoothingMethod", "MEDIAN")
effect.setParameter("KernelSizeMm", "3.0")
effect.self().onApply()


print("Finished segmenting right myocardium")


# Grow the left myocardium segment so it covers more of the left muscle
# Set Editor Widget to the Margin effect 
segmentEditorWidget.setActiveEffectByName("Margin")
# Set the Segment Editor Node to right myocardium segment
segmentEditorNode.SetSelectedSegmentID(leftMyocardiumSegmentID) 
# Set the Segment Editor node settings
# (editable area, editable intensity range, overwrite)
segmentEditorNode.SetSourceVolumeIntensityMask(True)
segmentEditorNode.SetSourceVolumeIntensityMaskRange(MIN_MYOCARDIUM_THRESHOLD_VALUE, MAX_MYOCARDIUM_THRESHOLD_VALUE)
segmentEditorNode.SetOverwriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteNone)
segmentEditorNode.SetMaskMode(3) # Set to editable area is outside all segments

# use Segment Editor effects to grow the left myocardium segment # TODO: grow size?
effect = segmentEditorWidget.activeEffect()
effect.setParameter("MarginSizeMm", "5.5")
effect.self().onApply()


# Smooth the left myocardium segment slightly # TODO: remove this if it is unhelpful
segmentEditorWidget.setActiveEffectByName("Smoothing")
segmentEditorNode.SetSelectedSegmentID(leftMyocardiumSegmentID)
segmentEditorNode.SetSourceVolumeIntensityMask(True)
segmentEditorNode.SetSourceVolumeIntensityMaskRange(MIN_THRESHOLD_VALUE, MIN_MYOCARDIUM_THRESHOLD_VALUE)
segmentEditorNode.SetOverwriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteNone)

effect = segmentEditorWidget.activeEffect()
effect.setParameter("SmoothingMethod", "CLOSING")
effect.setParameter("KernelSizeMm", "3.0") # TODO: adjust size
effect.self().onApply()

segmentEditorNode.SetSourceVolumeIntensityMask(False) # Median smoothing anywhere
effect.setParameter("SmoothingMethod", "MEDIAN")
effect.setParameter("KernelSizeMm", "3.0") # TODO: adjust size
effect.self().onApply()


#### Segmenting the scar tissue ####

# Segment the General scar tissue using threshold
segmentEditorWidget.setActiveEffectByName("Threshold") # TODO: make a helper function for this mask parameter setting given the node
segmentEditorNode.SetSourceVolumeIntensityMask(False)
segmentEditorNode.SetMaskMode(0) # Set to editable area anywhere
segmentEditorNode.SetSelectedSegmentID(scarSegmentID) # change selected segment to the General Scar segment
segmentEditorNode.SetOverwriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteNone) # allow overlap with other segments

effect = segmentEditorWidget.activeEffect()
effect.setParameter("MinimumThreshold", str(MIN_SCAR_THRESHOLD_VALUE))
effect.setParameter("MaximumThreshold", str(MAX_SCAR_THRESHOLD_VALUE))
effect.self().onApply()

# Ensure that the dark border around the left/right myocardium is not mistakenly included in the General scar
# Copy the Pleural Effusion into the Border segment # TODO: make a helper for this
segmentEditorWidget.setActiveEffectByName("Logical operators")
# Set the Segment Editor Node to right myocardium segment
segmentEditorNode.SetSelectedSegmentID(pleuralEffusionSegmentID) 

# Use Union to copy the pleural effusion  into the heart border segment
effect = segmentEditorWidget.activeEffect()
effect.setParameter("Operation", "UNION")
effect.setParameter("ModifierSegmentID", borderSegmentID) 
effect.self().onApply()


# Use the Hollow tool to draw the border of the heart tissue using the Pleural Effusion segment
segmentEditorWidget.setActiveEffectByName("Hollow")
segmentEditorNode.SetSourceVolumeIntensityMask(False)
segmentEditorNode.SetMaskMode(0) # Set to editable area anywhere
segmentEditorNode.SetSelectedSegmentID(borderSegmentID) # change selected segment to the General Scar segment
segmentEditorNode.SetOverwriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteNone) # allow overlap with other segments

effect = segmentEditorWidget.activeEffect()
effect.setParameter("ShellThicknessMm", "2.7")
effect.setParameter("ShellMode", "INSIDE_SURFACE")
effect.setParameter("ApplyToAllVisibleSegments", "0")
effect.self().onApply()


# Subtract the Border from the Scar segment (Scar = Scar - Border)



# set the left/right scar segments by taking the intersection of the general scar and left/right myocardium segments
segmentScarInMyocardium(leftScarSegmentID, scarSegmentID, leftMyocardiumSegmentID)
segmentScarInMyocardium(rightScarSegmentID, scarSegmentID, rightMyocardiumSegmentID)


# Smooth the right scar segment slightly # TODO: remove this if it is unhelpful
# TODO: make a smoothing function, with segmentID, mask thresholds, and type of smoothing as parameters, to avoid repeating code
segmentEditorWidget.setActiveEffectByName("Smoothing")
segmentEditorNode.SetSelectedSegmentID(rightScarSegmentID)
segmentEditorNode.SetSourceVolumeIntensityMask(True)
segmentEditorNode.SetSourceVolumeIntensityMaskRange(MIN_THRESHOLD_VALUE, MAX_SCAR_THRESHOLD_VALUE)
segmentEditorNode.SetOverwriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteNone)

effect = segmentEditorWidget.activeEffect()
effect.setParameter("SmoothingMethod", "CLOSING")
effect.setParameter("KernelSizeMm", "2.0")
effect.self().onApply()

# TODO: fix the magic numbers
segmentEditorNode.SetSourceVolumeIntensityMaskRange(-90, MAX_THRESHOLD_VALUE)
effect.setParameter("SmoothingMethod", "OPENING")
effect.setParameter("KernelSizeMm", "1.2")
effect.self().onApply()

# Smooth the LEFT scar segment slightly 
segmentEditorWidget.setActiveEffectByName("Smoothing")
segmentEditorNode.SetSelectedSegmentID(leftScarSegmentID)
segmentEditorNode.SetSourceVolumeIntensityMask(True)
segmentEditorNode.SetSourceVolumeIntensityMaskRange(MIN_THRESHOLD_VALUE, MAX_SCAR_THRESHOLD_VALUE)
segmentEditorNode.SetOverwriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteNone)

effect = segmentEditorWidget.activeEffect()
effect.setParameter("SmoothingMethod", "CLOSING")
effect.setParameter("KernelSizeMm", "2.0")
effect.self().onApply()

# TODO: fix the magic numbers
segmentEditorNode.SetSourceVolumeIntensityMaskRange(-90, 3071)
effect.setParameter("SmoothingMethod", "OPENING")
effect.setParameter("KernelSizeMm", "1.2")
effect.self().onApply()


print("Finished segmenting scar tissue")






# TODO: make myocaridum a closed wall?

# TODO: divide myocaridum into 3 layers
leftVentricleSegmentID = segmentation.GetSegmentIdBySegmentName("left ventricle of heart") 
# TODO: change this to be adaptive so it doesn't break if the naming changes
leftMyocardiumInnerSegmentID, leftMyocardiumMiddleSegmentID, leftMyocardiumOuterSegmentID = divideMyocardium(
    segmentation, volumeNode, segmentationChambersNode, leftMyocardiumSegmentID, leftVentricleSegmentID)



# Change visibility so that only left myocardium, right myocardium, left scar and right scar are visible
# setMyocardiumScarsVisible(segmentationChambersNode.GetDisplayNode(), segmentation, [leftMyocardiumSegmentID, 
#                           rightMyocardiumSegmentID, leftScarSegmentID, rightScarSegmentID, 
#                           leftMyocardiumInnerSegmentID, leftMyocardiumMiddleSegmentID, leftMyocardiumOuterSegmentID])

setMyocardiumScarsVisible(segmentationChambersNode.GetDisplayNode(), segmentation, [leftMyocardiumSegmentID, 
                          rightMyocardiumSegmentID, leftScarSegmentID, rightScarSegmentID])






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
