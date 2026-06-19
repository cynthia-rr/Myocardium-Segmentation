import slicer

from io_utils import load_dicom_series, load_segmentation
from totalsegmentator_pipeline import run_totalsegmentator_pipeline
from cardiac_analysis import (segment_right_myocardium, improve_left_myocardium, 
                              segment_scar, segment_scar_sections, divide_myocardium)
from visualization import set_segments_visibility
from io_constants import *

def main():
    # Load input data
    # volume_node = load_dicom_series(PATH_TO_DICOM_FOLDER)
    
    # Load the NIFTI file
    volume_node = slicer.util.loadVolume(str(PATH_TO_NIFTI))

    # Run TotalSegmentator
    # segmentation_name_to_node = run_totalsegmentator_pipeline(volume_node)
    segmentation_name_to_node = run_totalsegmentator_pipeline(volume_node)

    # # extract the segmentation nodes from the dictionary # TODO: make this constant variables
    # segmentation_chambers_node = segmentation_name_to_node["Chambers-Segmentation"]
    # segmentation_effusion_node = segmentation_name_to_node["Effusion-Segmentation"]
    # segmentation_artery_node = segmentation_name_to_node["Artery-Segmentation"]
    # segmentation_tissue_node = segmentation_name_to_node["Tissue-Segmentation"]

    # # extract the segmentation nodes from the dictionary # TODO: make this constant variables
    # segmentation_chambers_node = segmentation_name_to_node["Chambers-Segmentation"]
    # segmentation_effusion_node = segmentation_name_to_node["Effusion-Segmentation"]
    # segmentation_artery_node = segmentation_name_to_node["Artery-Segmentation"]
    # segmentation_tissue_node = segmentation_name_to_node["Tissue-Segmentation"]

    # Uncomment the below 4 lines if running only Myocardium Segmentation 
    # (already ran TotalSegmentation separately and saved resultd)
    # segmentation_chambers_node = load_segmentation(PATH_FOR_SAVE/SEGMENTATION_CHAMBERS_FILENAME, "Chambers-Segmentation")
    # segmentation_effusion_node = load_segmentation(PATH_FOR_SAVE/SEGMENTATION_EFFUSION_FILENAME, "Effusion-Segmentation")
    # segmentation_artery_node = load_segmentation(PATH_FOR_SAVE/SEGMENTATION_ARTERY_FILENAME, "Artery-Segmentation")
    # segmentation_tissue_node = load_segmentation(PATH_FOR_SAVE/SEGMENTATION_TISSUE_FILENAME, "Tissue-Segmentation")
    
    print("loaded segmentations")

    segmentation = segmentation_chambers_node.GetSegmentation()

    # TODO: clean this up
    # Get key segment IDs (from TotalSegmentator output)
    left_myocardium_id = segmentation.GetSegmentIdBySegmentName("myocardium")
    segmentation.GetSegment(left_myocardium_id).SetName("left myocardium") # Rename as appropriate

    right_ventricle_id = segmentation.GetSegmentIdBySegmentName("right ventricle of heart")
    left_ventricle_id = segmentation.GetSegmentIdBySegmentName("left ventricle of heart")
    
    right_myocardium_id = segmentation.AddEmptySegment("heart_myocardium_right", "right myocardium", COLOUR_RED)
    right_scar_id = segmentation.AddEmptySegment("heart_scar_right", "right scar", COLOUR_YELLOW)
    left_scar_id = segmentation.AddEmptySegment("heart_scar_left", "left scar", COLOUR_YELLOW)

    pleural_id = segmentation_effusion_node.GetSegmentation().GetSegmentIdBySegmentName("lung_pleural")
    border_id = segmentation.AddEmptySegment("heart_border", "border", COLOUR_BLUE)
    scar_id = segmentation.AddEmptySegment("heart_scar", "scar", COLOUR_YELLOW)
    inner_scar_id = segmentation.AddEmptySegment("heart_left_inner_scar", "left inner scar", COLOUR_LIGHT_ORANGE)
    middle_scar_id = segmentation.AddEmptySegment("heart_left_middle_scar", "left middle scar", COLOUR_ORANGE)
    outer_scar_id = segmentation.AddEmptySegment("heart_left_outer_scar", "left outer scar", COLOUR_DARK_ORANGE)


    # Create Segment Editor
    segment_editor_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode", "SegmentEditorNode")
    
    segment_editor_widget = slicer.qMRMLSegmentEditorWidget()
    segment_editor_widget.setMRMLSegmentEditorNode(segment_editor_node)
    segment_editor_widget.setMRMLScene(slicer.mrmlScene)
    segment_editor_widget.setSegmentationNode(segmentation_chambers_node)
    segment_editor_widget.setSourceVolumeNode(volume_node)

    # Segment right myocardium
    print("Segmenting right myocardium...")

    segment_right_myocardium(segment_editor_widget, segment_editor_node, right_ventricle_id, right_myocardium_id)

    # Segment left myocardium
    print("Improving left myocardium...")

    improve_left_myocardium(segmentation, segment_editor_widget, segment_editor_node, 
                            left_ventricle_id,left_myocardium_id)
    
    # Segment left myocardium into 3 layers, inner, middle, outer
    left_inner_id, left_middle_id, left_outer_id = divide_myocardium(volume_node, segmentation_chambers_node, 
                                                                     left_myocardium_id, left_ventricle_id)

    # TODO: clean this up
    segmentation.GetSegment(left_inner_id).SetName("left myocardium inner")
    segmentation.GetSegment(left_middle_id).SetName("left myocardium middle")
    segmentation.GetSegment(left_outer_id).SetName("left myocardium outer")
    segmentation.GetSegment(left_inner_id).SetColor(COLOUR_PINK)
    segmentation.GetSegment(left_middle_id).SetColor(COLOUR_GREEN)
    segmentation.GetSegment(left_outer_id).SetColor(COLOUR_LIGHT_BLUE)

    # Segment general scar areas
    print("Segmenting scar...")

    segment_scar(segmentation, segmentation_effusion_node, segment_editor_widget,
                 segment_editor_node, scar_id, pleural_id, border_id)

    # map from region segment id to scar segment id
    region_map = {left_myocardium_id: left_scar_id, right_myocardium_id: right_scar_id, left_inner_id: inner_scar_id,
                  left_middle_id: middle_scar_id, left_outer_id: outer_scar_id}
    # Segment scar regions, left scar, right scar, left inner, middle, outer scar
    segment_scar_sections(segment_editor_widget, segment_editor_node, scar_id, region_map)

    # Set visibility of segments
    set_segments_visibility(segmentation_chambers_node, segmentation, [left_inner_id, left_middle_id, left_outer_id, 
        right_myocardium_id, inner_scar_id, middle_scar_id, outer_scar_id, right_scar_id], volume_node)
    segmentation_effusion_node.GetDisplayNode().SetAllSegmentsVisibility(False)
    segmentation_artery_node.GetDisplayNode().SetAllSegmentsVisibility(False)
    segmentation_tissue_node.GetDisplayNode().SetAllSegmentsVisibility(False)

    print("Done segmentation!")


if __name__ == "__main__":
    main()