from pathlib import Path
import slicer
import DICOMLib

from io_constants import *

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
    segmentation_node.SetName(name)
    return segmentation_node

# TODO: create a new class, return that class instead of a dictionary?
def load_totalsegmentator_segmentations(save_folder: Path, chambers_filename: str, effusion_filename: str, 
                                        artery_filename: str, tissue_filename: str) -> dict[str, slicer.vtkMRMLSegmentationNode]:
     """
     Load the segmentation nodes from TotalSegmentator with the filename, return a dictionary from name to segmentation node.
     """

     return {
         CHAMBERS: load_segmentation(save_folder / chambers_filename, CHAMBERS),
        EFFUSION: load_segmentation(save_folder / effusion_filename, EFFUSION),
        ARTERY: load_segmentation(save_folder / artery_filename, ARTERY),
        TISSUE: load_segmentation(save_folder / tissue_filename, TISSUE)
        }

def export_segment_to_labelmap(segmentation_node: slicer.vtkMRMLSegmentationNode, segment_id: str, 
                               volume_node: slicer.vtkMRMLScalarVolumeNode, labelmap_name: str) -> slicer.vtkMRMLLabelMapVolumeNode:
    """
    Export the segment to a labelmap using the segment id and labelmap name given, return a labelmap.
    """

    labelmap_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", labelmap_name)
    slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(segmentation_node, [segment_id], 
                                                                      labelmap_node, volume_node)
    return labelmap_node

def import_labelmap_to_segmentation(labelmap_node: slicer.vtkMRMLLabelMapVolumeNode, 
                                    segmentation_node: slicer.vtkMRMLSegmentationNode) -> str:
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

    return new_ids.pop()

def remove_nodes(*nodes) -> None:
    """
    Remove temporary MRML nodes.
    """
    for node in nodes:
        if node is not None:
            slicer.mrmlScene.RemoveNode(node)

