import os
import slicer

MIN_SLICER_VERSION = "5.10.0"
MIN_MYOCARDIUM_THRESHOLD_VALUE = -300
MAX_MYOCARDIUM_THRESHOLD_VALUE = 300
MIN_SCAR_THRESHOLD_VALUE = -1225
MAX_SCAR_THRESHOLD_VALUE = 50

# load image
path = os.path.expanduser("~/Downloads/datasets/Totalsegmentator_dataset_v201/s0738/ct.nii.gz")

# get node
volumeNode = slicer.util.loadVolume(path)

# create segmentation node
segmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "Myocardium-Segmentation")
segmentationNode.CreateDefaultDisplayNodes()  # only needed for display, not necessary for processing

# access module logic
widget = slicer.modules.totalsegmentator.widgetRepresentation()
logic = widget.self().logic


# run segmentation with parameters
print("starting to run totalSegmentator now")
logic.process(inputVolume=volumeNode, 
            outputSegmentation=segmentationNode, 
            quality="normal",
            task="heartchambers_highres")
print("done segmentation! YAY!")


# create new segmentations for the right myocardium, left scar, right scar
segmentation = segmentationNode.GetSegmentation()
rightMyocardiumSegmentID = segmentation.AddEmptySegment("heart_myocardium_right")
scarSegmentID = segmentation.AddEmptySegment("heart_scar")
leftScarSegmentID = segmentation.AddEmptySegment("heart_scar_left")
rightScarSegmentID = segmentation.AddEmptySegment("heart_scar_right")

print("created new segments for right myocardium, left scar and right scar")

#print(dir(slicer.vtkSlicerSegmentationsModuleLogic))

# copy right ventricle into right myocardium segment
# TODO: should use the union effect instead of deepcopy
rightMyocardiumSegment = segmentation.GetSegment(rightMyocardiumSegmentID)
rightMyocardiumSegment.DeepCopy(segmentation.GetSegment("heart_ventricle_right"))


# set the new names of the segments
segmentation.GetSegment(rightMyocardiumSegmentID).SetName("right myocardium")
segmentation.GetSegment(scarSegmentID).SetName("scar")
segmentation.GetSegment(leftScarSegmentID).SetName("left scar")
segmentation.GetSegment(rightScarSegmentID).SetName("right scar")
segmentation.GetSegment("heart_myocardium").SetName("left myocardium")
# TODO: update the heart_myocardium id and name to left myocardium to match the right side

print("done copying right ventricle into right myocardium segment")

# select the right myocardium segment
segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")

# create Segment Editor widget 
segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
segmentEditorWidget.setMRMLScene(slicer.mrmlScene)

# finish configuring the Segment Editor widget
segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)
segmentEditorWidget.setSegmentationNode(segmentationNode)
segmentEditorWidget.setSourceVolumeNode(volumeNode)
segmentEditorWidget.setActiveEffectByName("Margin")

# set Segment Editor Node to correct segment
segmentEditorNode.SetSelectedSegmentID(rightMyocardiumSegmentID)

## CHECKING TO SEE IF THE CORRECT SEGMENT IS SELECTED
#print("currently editing: ", segmentEditorNode.GetSelectedSegmentID())

# update the settings of the Segment Editor node 
# (editable area, editable intensity range, overwrite)
segmentEditorNode.SetSourceVolumeIntensityMask(True)
segmentEditorNode.SetSourceVolumeIntensityMaskRange(MIN_MYOCARDIUM_THRESHOLD_VALUE, MAX_MYOCARDIUM_THRESHOLD_VALUE)
segmentEditorNode.SetOverwriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteNone)

# use Segment Editor effects to grow the segment by 3.0mm, with relevant parameters
effect = segmentEditorWidget.activeEffect()
effect.setParameter("MarginSizeMm", "3.0")
effect.self().onApply()

# subtract the right ventricle from the right myocardium segment to get the final right myocardium segmentation
segmentEditorWidget.setActiveEffectByName("Logical operators")
effect = segmentEditorWidget.activeEffect()

segmentEditorNode.SetSelectedSegmentID(rightMyocardiumSegmentID) ####### TODO: should prob make this cleaner

effect.setParameter("Operation", "SUBTRACT")
effect.setParameter("ModifierSegmentID", "heart_ventricle_right") # TODO: make this a variable or constant?
effect.self().onApply()



# TODO: INSTEAD of fiddling with the settings, instead call threshold on everything, 
# then call intersection for left and right scar
# segment the General scar tissue using threshold
segmentEditorWidget.setActiveEffectByName("Threshold")
effect = segmentEditorWidget.activeEffect()
segmentEditorNode.SetSelectedSegmentID(scarSegmentID) # change selected segment to the General Scar segment
segmentEditorNode.SetSourceVolumeIntensityMask(True)
segmentEditorNode.SetSourceVolumeIntensityMaskRange(MIN_SCAR_THRESHOLD_VALUE, MAX_SCAR_THRESHOLD_VALUE)
segmentEditorNode.SetOverwriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteNone) # allow overlap with other segments

effect.self().onApply()

# set the left scar segment by taking the intersection of the scar and left myocardium segments
segmentEditorWidget.setActiveEffectByName("Logical operators")
effect = segmentEditorWidget.activeEffect()
segmentEditorNode.SetSelectedSegmentID(leftScarSegmentID) # change selected segment to the left
effect.setParameter("Operation", "UNION")
effect.setParameter("ModifierSegmentID", "heart_myocardium")
effect.self().onApply()
effect.setParameter("Operation", "INTERSECT")
effect.setParameter("ModifierSegmentID", "heart_scar")
effect.self().onApply()

# set the right scar segment by taking the intersection of the scar and right myocardium segments
segmentEditorNode.SetSelectedSegmentID(rightScarSegmentID) # change selected segment to the right
effect.setParameter("Operation", "UNION")
effect.setParameter("ModifierSegmentID", "heart_myocardium_right")
effect.self().onApply()
effect.setParameter("Operation", "INTERSECT")
effect.setParameter("ModifierSegmentID", "heart_scar")
effect.self().onApply()


# save, exit
# slicer.util.exit()




"""
# printing segment names
print("ID (internal), Name (display)")
for segmentId in segmentation.GetSegmentIDs():
    segment = segmentation.GetSegment(segmentId)
    print(segmentId, " --> ", segment.GetName())
"""

