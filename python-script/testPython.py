import os
import slicer

# load image
path = os.path.expanduser("~/Downloads/datasets/Totalsegmentator_dataset_v201/s0738/ct.nii.gz")

# get node
volumeNode = slicer.util.loadVolume(path)

# create segmentation node
segmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "Totalsegmentator_Segmentation")
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
leftScarSegmentID = segmentation.AddEmptySegment("heart_scar_left")
rightScarSegmentID = segmentation.AddEmptySegment("heart_scar_right")

print("created new segments for right myocardium, left scar and right scar")

#print(dir(slicer.vtkSlicerSegmentationsModuleLogic))

# copy right ventricle into right myocardium segment
rightMyocardiumSegment = segmentation.GetSegment(rightMyocardiumSegmentID)
rightMyocardiumSegment.DeepCopy(segmentation.GetSegment("heart_ventricle_right"))


# set the new names of the segments
segmentation.GetSegment(rightMyocardiumSegmentID).SetName("right myocardium")
segmentation.GetSegment(leftScarSegmentID).SetName("left scar")
segmentation.GetSegment(rightScarSegmentID).SetName("right scar")

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

# set Segment Editor Node to correct segment
segmentEditorNode.SetSelectedSegmentID(rightMyocardiumSegmentID)

## CHECKING TO SEE IF THE CORRECT SEGMENT IS SELECTED
#print("currently editing: ", segmentEditorNode.GetSelectedSegmentID())

# update the settings of the Segment Editor node 
# (editable area, editable intensity range, overwrite)
segmentEditorNode.SetSourceVolumeIntensityMask(True)
segmentEditorNode.SetSourceVolumeIntensityMaskRange(-300, 300)
segmentEditorNode.SetOverwriteMode(slicer.vtkMRMLSegmentEditorNode.OverwriteNone)

# use Segment Editor effects to grow the segment by 3.0mm, with relevant parameters
segmentEditorWidget.setActiveEffectByName("Margin")
effect = segmentEditorWidget.activeEffect()
effect.setParameter("MarginSizeMm", "3.0")
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