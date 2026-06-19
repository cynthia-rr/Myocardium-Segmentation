import slicer

from myocardiumsegmentation.io_utils import load_dicom_series, load_segmentation
# from totalsegmentator_pipeline import run_totalsegmentator_pipeline
from myocardiumsegmentation.cardiac_analysis import divide_myocardium, segment_scar, segment_scar_sections

from myocardiumsegmentation.visualization import set_segments_visibility
from division_io_constants import *

def division():
    # Load input data
    volume_node = load_dicom_series(PATH_TO_PERF_DICOM_FOLDER)

    # Run TotalSegmentator
    # segmentation_name_to_node = run_totalsegmentator_pipeline(volume_node)
    # extract the segmentation nodes from the dictionary
    # segmentation_chambers_node = segmentation_name_to_node["Chambers-Segmentation"]
    # segmentation_effusion_node = segmentation_name_to_node["Effusion-Segmentation"]
    # segmentation_artery_node = segmentation_name_to_node["Artery-Segmentation"]
    # segmentation_tissue_node = segmentation_name_to_node["Tissue-Segmentation"]

    # Load already made segmentations
    segmentation_node = load_segmentation(PATH_FOR_SAVE/SEGMENTATION_FILENAME, "MySegmentation")
    
    print("loaded segmentations")

    segmentation = segmentation_node.GetSegmentation()

    # TODO: clean this up
    # Get key segment IDs (from TotalSegmentator output)
    left_myocardium_id = segmentation.GetSegmentIdBySegmentName("myocardium")
    left_ventricle_id = segmentation.GetSegmentIdBySegmentName("left ventricle of heart")

    # dark_region_id = segmentation.AddEmptySegment("dark_region", "dark region", COLOUR_BLUE)
    # light_region_id = segmentation.AddEmptySegment("light_region", "light region", COLOUR_RED)

    # dark_myo_id = segmentation.AddEmptySegment("dark_myocardium", "dark myocardium", COLOUR_DARK_ORANGE)
    # light_myo_id = segmentation.AddEmptySegment("light_myocardium", "light myocardium", COLOUR_LIGHT_ORANGE)


    # Create Segment Editor
    segment_editor_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode", "SegmentEditorNode")
    segment_editor_widget = slicer.qMRMLSegmentEditorWidget()
    segment_editor_widget.setMRMLSegmentEditorNode(segment_editor_node)
    segment_editor_widget.setMRMLScene(slicer.mrmlScene)
    segment_editor_widget.setSegmentationNode(segmentation_node)
    segment_editor_widget.setSourceVolumeNode(volume_node)

    left_inner_id, left_middle_id, left_outer_id = divide_myocardium(volume_node, segmentation_node, 
                                                                     left_myocardium_id, left_ventricle_id)

    # TODO: clean this up
    segmentation.GetSegment(left_inner_id).SetName("left myocardium inner")
    segmentation.GetSegment(left_middle_id).SetName("left myocardium middle")
    segmentation.GetSegment(left_outer_id).SetName("left myocardium outer")
    segmentation.GetSegment(left_inner_id).SetColor(COLOUR_PINK)
    segmentation.GetSegment(left_middle_id).SetColor(COLOUR_GREEN)
    segmentation.GetSegment(left_outer_id).SetColor(COLOUR_LIGHT_BLUE)


    # # Segment general dark/ light regions
    # print("Segmenting dark/ light regions...")

    # segment_scar(segmentation, segmentation_effusion_node, segment_editor_widget,
    #              segment_editor_node, scar_id, pleural_id, border_id)

    # # map from region segment id to scar segment id
    # region_map = {left_myocardium_id: left_scar_id, right_myocardium_id: right_scar_id, left_inner_id: inner_scar_id,
    #               left_middle_id: middle_scar_id, left_outer_id: outer_scar_id}
    # # Segment scar regions, left scar, right scar, left inner, middle, outer scar
    # segment_scar_sections(segment_editor_widget, segment_editor_node, scar_id, region_map)

    # Set visibility of segments
    set_segments_visibility(segmentation_node, segmentation, [left_inner_id, left_middle_id, left_outer_id], volume_node)


    print("Done segmentation!")


if __name__ == "__main__":

    division()