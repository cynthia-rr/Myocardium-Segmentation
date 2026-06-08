from pathlib import Path
import slicer
import DICOMLib

#### Initialisation and setup ####

def load_dicom_series(dicom_folder: Path) -> slicer.vtkMRMLScalarVolumeNode:
    """
    Load a DICOM series into the MRML scene given its path, and return the volume node. 
    """
    # Error checking the path to input folder
    if not dicom_folder.exists() or not dicom_folder.is_dir():
        raise FileNotFoundError(f"Error: DICOM folder path '{dicom_folder}' does not exist or is not a directory.")

    # Load DICOM folder, get Volume node 
    with DICOMLib.DICOMUtils.TemporaryDICOMDatabase() as db:
        try:
            DICOMLib.DICOMUtils.importDicom(dicom_folder, db) # Imports DICOM files into temp db
        except Exception as e:
            print(f"Error importing DICOM files: {e}") # TODO: raise an error here
            exit()
        patient_uids = db.patients() # Get list of patient UIDs in database
        if not patient_uids:
            raise RuntimeError("No patients found in the DICOM database.")
        
        loadNodeIDs = DICOMLib.DICOMUtils.loadPatientByUID(patient_uids[0]) # Load the first patient into the MRML scene
        if not loadNodeIDs:
            raise RuntimeError("Unable to load the DICOM series into the scene.")

        # Get loaded Volume Node
        volume_node = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
        if volume_node is None:
            raise RuntimeError("Could not load volume node.")
        return volume_node

def load_segmentation(segmentation_path: Path, name: str) -> slicer.vtkMRMLSegmentationNode:
    """
    Load a segmentation, set the name and return the segmentation node.
    """
    # Load the segmentation from the given path
    segmentation_node = slicer.util.loadSegmentation(segmentation_path)
    if segmentation_node is None:
        raise RuntimeError("Unable to load the segmentation.")
    # Set the name of the segmentation node
    segmentation_node.setName(name)
    return segmentation_node

# TODO: create a new class, return that class instead of a dictionary?
def load_totalsegmentator_segmentations(save_folder: Path, chambers_filename: str, effusion_filename: str, 
                                        artery_filename: str, tissue_filename: str) -> dict[str, slicer.ctkMRMLSegmentationNode]:
     """
     Load the segmentation nodes from TotalSegmentator with the filename, return a dictionary from name to segmentation node.
     """

     return { # TODO: chambers file name constant
         "chambers": load_segmentation(save_folder / chambers_filename, "Myocardium-Segmentation"),
        "effusion": load_segmentation(save_folder / effusion_filename, "Effusion-Segmentation"),
        "artery": load_segmentation(save_folder / artery_filename, "Artery-Segmentation"),
        "tissue": load_segmentation(save_folder / tissue_filename, "Tissue-Segmentation")
        }

def export_segment_to_labelmap(segmentation_node: slicer.vtkMRMLSegmentationNode, segment_id: str, 
                               volume_node: slicer.vtkMRMLScalarVolumeNode, labelmap_name: str) -> slicer.vtkMRMLLabelMapVolumeNode:
    """
    Export the segment to a labelmap using the segment id and labelmap name given, return a labelmap.
    """

    labelmap_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", labelmap_name)
    slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(segmentation_node, [segment_id], labelmap_node, volume_node)
    return labelmap_node

def import_labelmap_to_segmentation(labelmap_node: slicer.vtkMRMLLabelmapVolumeNode, segmentation_node: slicer.vtkMRMLSegmentatioNode) -> str:
    """
    Import a labelmap into a segment, and return the new segment ID.
    """

    segmentation = segmentation_node.GetSegmentation()
    
    existing_ids = set(segmentation.GetSegmentIDs())
    slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(labelmap_node, segmentation_node)
    updated_ids = set(segmentation.GetSegmentIDs())

    new_ids = updated_ids - existing_ids

    if len(new_ids) != 1:
        raise RuntimeError("Expected exactly one imported segment.")

    return new_ids[0]

def remove_nodes(*nodes) -> None:
    """
    Remove temporary MRML nodes.
    """
    for node in nodes:
        if node is not None:
            slicer.mrmlScene.RemoveNode(node)



##############################################################################################################




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
leftScarInnerSegmentID = segmentation.AddEmptySegment("heart_scar_left_inner", "left scar inner", COLOUR_LIGHT_ORANGE)
leftScarMiddleSegmentID = segmentation.AddEmptySegment("heart_scar_left_middle", "left scar middle", COLOUR_ORANGE)
leftScarOuterSegmentID = segmentation.AddEmptySegment("heart_scar_left_outer", "left scar outer", COLOUR_DARK_ORANGE)

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



# Create SegmentEditor Node from module # TODO: fix the order of editor node vs widget
segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode", "SegmentEditorNode")
segmentEditorWidget = slicer.qMRMLSegmentEditorWidget()
segmentEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode) # Set the Segment Editor node
# Create Segment Editor widget's MRML scene, segmentation node and volume node
segmentEditorWidget.setMRMLScene(slicer.mrmlScene)
segmentEditorWidget.setSegmentationNode(segmentationChambersNode)
segmentEditorWidget.setSourceVolumeNode(volumeNode)

