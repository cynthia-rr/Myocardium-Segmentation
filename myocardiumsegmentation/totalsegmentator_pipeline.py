import slicer
from io_constants import *

def create_segmentation_node(name: str) -> slicer.vtkMRMLSegmentationNode:
    """
    Create and return a new segmentation node.
    """
    node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", name)
    return node

def run_totalsegmentator_task(widget: slicer.qMRMLSegmentEditorWidget, volume_node: slicer.vtkMRMLScalarVolumeNode, 
                         output_node: slicer.vtkMRMLSegmentationNode, task: str, label: str) -> None:
    """
    Run TotalSegmentator with the given task
    """

    print(f"Starting TotalSegmentator {label}")

    widget.self().logic.process(inputVolume=volume_node, outputSegmentation=output_node, 
                                quality=SEGMENTATION_QUALITY,task=task)

    if not output_node.GetSegmentation().GetSegmentIDs():
        raise RuntimeError(f"TotalSegmentator failed for {label}")

    print(f"TotalSegmentator {label} complete")


def run_totalsegmentator_pipeline(volume_node: slicer.vtkMRMLScalarVolumeNode) -> None:
        
    # Access widget 
    widget = slicer.modules.totalsegmentator.widgetRepresentation()

    # Create the segmentation nodes
    segmentationChambersNode = create_segmentation_node("Chambers")
    segmentationEffusionNode = create_segmentation_node("Effusion")
    segmentationArteryNode = create_segmentation_node("Artery")
    segmentationTissueNode = create_segmentation_node("Tissue")


    # Define pipeline steps
    tasks = [
        (SEGMENTATION_CHAMBERS_TASK, segmentationChambersNode, "heart"),
        (SEGMENTATION_EFFUSION_TASK, segmentationEffusionNode, "effusion"),
        (SEGMENTATION_ARTERY_TASK, segmentationArteryNode, "artery"),
        (SEGMENTATION_TISSUE_TASK, segmentationTissueNode, "tissue"),
    ]

    # Run all segmentations
    for task, output_node, label in tasks:
        run_totalsegmentator_task(widget, volume_node, output_node, task, label)


    # Save outputs
    outputs = [
        (segmentationChambersNode, SEGMENTATION_CHAMBERS_FILENAME),
        (segmentationEffusionNode, SEGMENTATION_EFFUSION_FILENAME),
        (segmentationArteryNode, SEGMENTATION_ARTERY_FILENAME),
        (segmentationTissueNode, SEGMENTATION_TISSUE_FILENAME),
    ]

    for node, filename in outputs:
        slicer.util.saveNode(node, str(PATH_FOR_SAVE / filename))

    print("Saved TotalSegmentator outputs")
    slicer.util.exit()

