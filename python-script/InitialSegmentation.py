from pathlib import Path
import slicer
import DICOMLib
from GlobalConstants import *



PATH_TO_NIFTI = Path.home() / "Downloads/datasets/Totalsegmentator_dataset_v201/s0738/ct.nii.gz"
PATH_TO_DICOM_FOLDER = Path.home() / "Downloads/datasets/CRA-03"
PATH_FOR_SAVE = "segmentations" 
# TODO: unsure about this saving file stuff

# TODO: create add effect function, set the function, set the parameters


# Make the Myocardium (left, right) and Scar (left, right) segments visible, hide the rest
# and show the centred 3D view of the segments
def setMyocardiumScarsVisible(displayNode: slicer.vtkMRMLSegmentationDisplayNode, 
                              segmentation: slicer.vtkMRMLSegmentationNode, 
                              visibleSegmentIDs: list[str]):
    for segmentID in segmentation.GetSegmentIDs():
        displayNode.SetSegmentVisibility(segmentID, False)
    for segmentID in visibleSegmentIDs:
        displayNode.SetSegmentVisibility(segmentID, True)

    # Show the segmentations in 3D, and center the 3D view
    segmentationNode.CreateClosedSurfaceRepresentation()
    displayNode.SetVisibility3D(True)
    slicer.app.layoutManager().threeDWidget(0).threeDView().resetFocalPoint()

def segmentScarInMyocardium(outputSegmentID: str, entireScarSegmentID: str, partialMyocardiumSegmentID:str):
    segmentEditorWidget.setActiveEffectByName("Logical operators")
    effect = segmentEditorWidget.activeEffect()
    segmentEditorNode.SetSelectedSegmentID(outputSegmentID) # change selected segment
    effect.setParameter("Operation", "UNION")
    effect.setParameter("ModifierSegmentID", partialMyocardiumSegmentID) 
    effect.self().onApply() # copy the myocardium segment into the output segment
    effect.setParameter("Operation", "INTERSECT")
    effect.setParameter("ModifierSegmentID", entireScarSegmentID)
    effect.self().onApply() # scar segment = myocardium *intersection* scar segment


#### Initialisation and setup ####

# Load NIFTI file, get Volume node
"""volumeNode = slicer.util.loadVolume(PATH_TO_NIFTI)
print("Loaded dataset from: ", PATH_TO_NIFTI)"""

# Load DICOM folder, get Volume node 
# TODO: create helper function to do this
DICOMUtils = DICOMLib.DICOMUtils
with DICOMUtils.TemporaryDICOMDatabase() as db:
    DICOMUtils.importDicom(PATH_TO_DICOM_FOLDER, db)
    patientUIDs = db.patients()
    loadedNodeIDs = DICOMUtils.loadPatientByUID(patientUIDs[0])

# Get loaded Volume Node
volumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
print("Loaded dataset from: ", PATH_TO_DICOM_FOLDER)

# Adjust volume display settings including window and level 
volumeDisplayNode = volumeNode.GetDisplayNode()
volumeDisplayNode.SetWindow(DISPLAY_WINDOW)
volumeDisplayNode.SetLevel(DISPLAY_LEVEL)


# Create segmentation node
segmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "Myocardium-Segmentation")
segmentationNode.CreateDefaultDisplayNodes()  # only needed for display, not necessary for processing

# Access TotalSegmentator Logic
totalSegmentatorWidget = slicer.modules.totalsegmentator.widgetRepresentation()
totalSegmentatorLogic = totalSegmentatorWidget.self().logic

# Run TotalSegmentator Logic with appropriate parameters
print("Starting to run TotalSegmentator")
totalSegmentatorLogic.process(inputVolume=volumeNode, 
                                outputSegmentation=segmentationNode, 
                                quality=SEGMENTATION_QUALITY,
                                task=SEGMENTATION_TASK)
print("Total Segmentator segmentation complete")



# Create new segmentations for the right myocardium, left scar, right scar, setting their ID, name and colour
segmentation = segmentationNode.GetSegmentation() # TODO: finetune these colours
rightMyocardiumSegmentID = segmentation.AddEmptySegment("heart_myocardium_right", "right myocardium", [0.5, 0.0, 0.0])
scarSegmentID = segmentation.AddEmptySegment("heart_scar", "scar", [1.0, 1.0, 0.0])
leftScarSegmentID = segmentation.AddEmptySegment("heart_scar_left", "left scar", [1.0, 1.0, 0.0])
rightScarSegmentID = segmentation.AddEmptySegment("heart_scar_right", "right scar", [1.0, 1.0, 0.0])
# TODO: add error checking, if empty then print error message and exit

# Set the name of the old myocardium segment to be left myocardium, and save right ventricle segment ID for later use
# Working off assumption of consistent naming from TotalSegmentator, but should add error checking
leftMyocardiumSegmentID = segmentation.GetSegmentIdBySegmentName("myocardium") 
# TODO: change this to be adaptive so it doesn't break if the naming changes
segmentation.GetSegment(leftMyocardiumSegmentID).SetName("left myocardium") 
rightVentricleSegmentID = segmentation.GetSegmentIdBySegmentName("right ventricle of heart")

print("Created new segments for right myocardium, left scar and right scar")

# Create SegmentEditor Node from module # TODO: fix the order of editor node vs widget
segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")

segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode) # Set the Segment Editor node
# Create Segment Editor widget and set the MRML scene, segmentation node and volume node

segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
segmentEditorWidget.setSegmentationNode(segmentationNode)
segmentEditorWidget.setSourceVolumeNode(volumeNode)

print("Initialisation and setup complete")


#### Segmenting the right myocardium ####

# Set Editor Widget to the Islands effect
segmentEditorWidget.setActiveEffectByName("Islands")
effect = segmentEditorWidget.activeEffect()
# Set the selected segment to the right ventricle
segmentEditorNode.SetSelectedSegmentID(rightVentricleSegmentID)
# Keep only the largest island, remove small blobs
effect.setParameter("Operation", "KEEP_LARGEST_ISLAND")
effect.self().onApply()


# Set Editor Widget to the Logical Operators effect 
segmentEditorWidget.setActiveEffectByName("Logical operators")
effect = segmentEditorWidget.activeEffect()
# Set the Segment Editor Node to right myocardium segment
segmentEditorNode.SetSelectedSegmentID(rightMyocardiumSegmentID) 

# Use Union to copy the right ventricle into the right myocardium segment
effect.setParameter("Operation", "UNION")
effect.setParameter("ModifierSegmentID", rightVentricleSegmentID) 
effect.self().onApply()


# Set Editor Widget to the Margin effect # TODO: try using hollow instead?
segmentEditorWidget.setActiveEffectByName("Margin")

# Set the Segment Editor Node to right myocardium segment
segmentEditorNode.SetSelectedSegmentID(rightMyocardiumSegmentID) # TODO: see if I can delete this? but then maybe not


# Set the Segment Editor node settings
# (editable area, editable intensity range, overwrite)
segmentEditorNode.SetSourceVolumeIntensityMask(True)
segmentEditorNode.SetSourceVolumeIntensityMaskRange(MIN_MYOCARDIUM_THRESHOLD_VALUE, MAX_MYOCARDIUM_THRESHOLD_VALUE)
segmentEditorNode.SetOverwriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteNone)

# use Segment Editor effects to grow the segment by 7.0mm, with relevant parameters
effect = segmentEditorWidget.activeEffect()
effect.setParameter("MarginSizeMm", "8.0")
effect.self().onApply()

# subtract the right ventricle from the right myocardium segment to get the final right myocardium segmentation
segmentEditorWidget.setActiveEffectByName("Logical operators")
effect = segmentEditorWidget.activeEffect()

segmentEditorNode.SetSelectedSegmentID(rightMyocardiumSegmentID) ####### TODO: should prob make this cleaner
segmentEditorNode.SetSourceVolumeIntensityMask(False)

effect.setParameter("Operation", "SUBTRACT") #TODO: change this to hollow?
effect.setParameter("ModifierSegmentID", rightVentricleSegmentID) 
effect.self().onApply()

print("Finished segmenting right myocardium")

# Grow the left myocardium segment so it covers the entire muscle
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

# use Segment Editor effects to grow the segment by 7.0mm, with relevant parameters
effect = segmentEditorWidget.activeEffect()
effect.setParameter("MarginSizeMm", "7.0")
effect.self().onApply()


#### Segmenting the scar tissue ####

# Segment the General scar tissue using threshold
segmentEditorWidget.setActiveEffectByName("Threshold")
effect = segmentEditorWidget.activeEffect()
segmentEditorNode.SetSourceVolumeIntensityMask(False)
segmentEditorNode.SetMaskMode(0) # Set to editable area anywhere
segmentEditorNode.SetSelectedSegmentID(scarSegmentID) # change selected segment to the General Scar segment
segmentEditorNode.SetOverwriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteNone) # allow overlap with other segments
effect.setParameter("MinimumThreshold", str(MIN_SCAR_THRESHOLD_VALUE))
effect.setParameter("MaximumThreshold", str(MAX_SCAR_THRESHOLD_VALUE))
effect.self().onApply()

# set the left/right scar segments by taking the intersection of the general scar and left/right myocardium segments
segmentScarInMyocardium(leftScarSegmentID, scarSegmentID, leftMyocardiumSegmentID)
segmentScarInMyocardium(rightScarSegmentID, scarSegmentID, rightMyocardiumSegmentID)

print("Finished segmenting scar tissue")

# Change visibility so that only left myocardium, right myocardium, left scar and right scar are visible
setMyocardiumScarsVisible(segmentationNode.GetDisplayNode(), segmentation, [leftMyocardiumSegmentID, 
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
# TODO: add error checking
segLogic = slicer.modules.segmentations.logic()
segLogic.ExportSegmentsClosedSurfaceRepresentationToFiles("segmentations", segmentationNode)
print("Saved segmentation to: ", PATH_FOR_SAVE)
# slicer.util.exit()
"""
