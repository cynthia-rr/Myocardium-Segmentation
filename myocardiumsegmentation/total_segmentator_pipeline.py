import slicer
from constants import *

# Access TotalSegmentator Widget 
totalSegmentatorWidget = slicer.modules.totalsegmentator.widgetRepresentation()

# Run TotalSegmentator Logic with appropriate parameters
print("Starting to run TotalSegmentator heart segmentation")
totalSegmentatorWidget.self().logic.process(inputVolume=volumeNode, outputSegmentation=segmentationChambersNode, 
                                quality=SEGMENTATION_QUALITY,task=SEGMENTATION_CHAMBERS_TASK)
# Error checking if TotalSegmentator created segments, if not print error message then exit
if not segmentationChambersNode.GetSegmentation().GetSegmentIDs():
    print("Error running TotalSegmentator, no segments created")
    exit()
print("Total Segmentator heart segmentation complete")

print("Starting to run TotalSegmentator effusion segmentation")
totalSegmentatorWidget.self().logic.process(inputVolume=volumeNode, outputSegmentation=segmentationEffusionNode, 
                                quality=SEGMENTATION_QUALITY,task=SEGMENTATION_EFFUSION_TASK)
print("Total Segmentator effusion segmentation complete")

print("Starting to run TotalSegmentator coronary artery segmentation")
totalSegmentatorWidget.self().logic.process(inputVolume=volumeNode, outputSegmentation=segmentationArteryNode, 
                                quality=SEGMENTATION_QUALITY,task=SEGMENTATION_ARTERY_TASK)
print("Total Segmentator coronary artery segmentation complete")

print("Starting to run TotalSegmentator tissue segmentation")
totalSegmentatorWidget.self().logic.process(inputVolume=volumeNode, outputSegmentation=segmentationTissueNode, 
                                quality=SEGMENTATION_QUALITY,task=SEGMENTATION_TISSUE_TASK)
print("Total Segmentator tissue segmentation complete")


# save, exit
slicer.util.saveNode(segmentationChambersNode, str(PATH_FOR_SAVE / SEGMENTATION_CHAMBERS_FILENAME))
slicer.util.saveNode(segmentationEffusionNode, str(PATH_FOR_SAVE / SEGMENTATION_EFFUSION_FILENAME))
slicer.util.saveNode(segmentationArteryNode, str(PATH_FOR_SAVE / SEGMENTATION_ARTERY_FILENAME))
slicer.util.saveNode(segmentationTissueNode, str(PATH_FOR_SAVE / SEGMENTATION_TISSUE_FILENAME))

print("Saved TotalSegmentator segmentation x4, and now exit")
slicer.util.exit()

