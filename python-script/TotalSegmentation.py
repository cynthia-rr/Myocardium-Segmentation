import slicer
import DICOMLib
from GlobalConstants import *

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

# Create segmentation node
segmentationNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "Myocardium-Segmentation")
#segmentationNode.CreateDefaultDisplayNodes()  # only needed for display, not necessary for processing

# Access TotalSegmentator Widget 
totalSegmentatorWidget = slicer.modules.totalsegmentator.widgetRepresentation()

# Run TotalSegmentator Logic with appropriate parameters
print("Starting to run TotalSegmentator")
totalSegmentatorWidget.self().logic.process(inputVolume=volumeNode, outputSegmentation=segmentationNode, 
                                quality=SEGMENTATION_QUALITY,task=SEGMENTATION_TASK)
# Error checking if TotalSegmentator created segments, if not print error message then exit
if not segmentationNode.GetSegmentation().GetSegmentIDs():
    print("Error running TotalSegmentator, no segments created")
    exit()
print("Total Segmentator segmentation complete")


# save, exit
slicer.util.saveNode(segmentationNode, str(PATH_FOR_SAVE / "segmentation.seg.nrrd"))
print("Saved TotalSegmentator segmentation, and now exit")
# slicer.util.exit()


"""segLogic = slicer.modules.segmentations.logic()
segLogic.ExportSegmentsClosedSurfaceRepresentationToFiles("segmentations", segmentationNode)
"""

