import slicer

from io_utils import load_dicom_series, load_segmentation
from totalsegmentator_pipeline import run_totalsegmentator_pipeline
from cardiac_analysis import segment_right_myocardium, improve_left_myocardium, segment_scar, segment_right_left_scar, divide_myocardium
from visualization import set_segments_visibility
from constants import *

def main():
    # Load input data
    volume_node = load_dicom_series(PATH_TO_DICOM_FOLDER)

    # Run TotalSegmentator
    # run_totalsegmentator_pipeline(volume_node)


    # TODO: include the others
    segmentation_chambers_node = load_segmentation(PATH_FOR_SAVE/SEGMENTATION_CHAMBERS_FILENAME, "Chambers-Segmentation")
    segmentation_effusion_node = load_segmentation(PATH_FOR_SAVE/SEGMENTATION_EFFUSION_FILENAME, "Effusion-Segmentation")
    # segmentation_artery_node = load_segmentation(PATH_FOR_SAVE/SEGMENTATION_ARTERY_FILENAME, "Artery-Segmentation")
    # segmentation_tissue_node = load_segmentation(PATH_FOR_SAVE/SEGMENTATION_TISSUE_FILENAME, "Tissue-Segmentation")
    
    print("loaded segmentations")

    segmentation = segmentation_chambers_node.GetSegmentation()

    # Get key segment IDs (from TotalSegmentator output)
    left_myocardium_id = segmentation.GetSegmentIdBySegmentName("myocardium")
    right_ventricle_id = segmentation.GetSegmentIdBySegmentName("right ventricle of heart")
    left_ventricle_id = segmentation.GetSegmentIdBySegmentName("left ventricle of heart")
    
    right_myocardium_id = segmentation.AddEmptySegment("heart_myocardium_right", "right myocardium", COLOUR_PINK)
    right_scar_id = segmentation.AddEmptySegment("heart_scar_right", "right scar", COLOUR_YELLOW)
    left_scar_id = segmentation.AddEmptySegment("heart_scar_left", "left scar", COLOUR_YELLOW)


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
    
    # Segment general scar areas
    print("Segmenting scar...")

    pleural_id = segmentation.GetSegmentIdBySegmentName("lung_pleural")

    scar_id = segmentation.AddEmptySegment("heart_scar", "scar", COLOUR_YELLOW)
    border_id = segmentation.AddEmptySegment("heart_border", "border", COLOUR_BLUE)

    segment_scar(segmentation, segmentation_effusion_node, segment_editor_widget,
                 segment_editor_node, scar_id, pleural_id, border_id)

    # Segment scar regions, left scar, right scar, left inner, middle, outer scar
    region_map = {
        left_myocardium_id: "heart_scar_left", # TODO: add the inner, middle and outer scar once it works
        right_myocardium_id: "heart_scar_right",
    }

    segment_right_left_scar(segment_editor_widget, segment_editor_node, scar_id, region_map)

    # Segment left myocardium into 3 layers, inner, middle, outer
    inner_id, middle_id, outer_id = divide_myocardium(segmentation, volume_node, segmentation_chambers_node,
                                                      left_myocardium_id, left_ventricle_id)

    # Set visibility of segments
    set_segments_visibility(segmentation_chambers_node, segmentation, 
                            [inner_id, middle_id, outer_id, right_myocardium_id], volume_node)
    segmentation_effusion_node.GetDisplayNode().SetAllSegmentsVisibility(False)
    # segmentation_artery_node.GetDisplayNode().SetAllSegmentsVisibility(False)

    print("Done segmentation!")


if __name__ == "__main__":
    main()