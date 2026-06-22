import slicer
from io_constants import *
from total_segmentation_constants import *

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


def run_totalsegmentator_pipeline(volume_node: slicer.vtkMRMLScalarVolumeNode) -> dict[str, slicer.vtkMRMLSegmentationNode]:
    """
    Run the TotalSegmentator extension, to segment the chambers, effusion, coronary arteries and 
    different types of tissues.
    Return the segmentation nodes in a dictionary that maps the name to the node.
    """
    # Access widget 
    widget = slicer.modules.totalsegmentator.widgetRepresentation()

    # Create the segmentation nodes
    segmentation_chambers_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", SEGMENTATION_CHAMBERS_NODE_NAME)
    segmentation_effusion_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", SEGMENTATION_EFFUSION_NODE_NAME)
    # segmentation_artery_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", SEGMENTATION_ARTERY_NODE_NAME)
    # segmentation_tissue_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", SEGMENTATION_TISSUE_NODE_NAME)

    # Add segmentation nodes to the dictionary
    name_to_node = {SEGMENTATION_CHAMBERS_NODE_NAME: segmentation_chambers_node, 
                    SEGMENTATION_EFFUSION_NODE_NAME: segmentation_effusion_node, 
                    # SEGMENTATION_ARTERY_NODE_NAME: segmentation_artery_node, 
                    # SEGMENTATION_TISSUE_NODE_NAME: segmentation_tissue_node
                    }
    

    # Define pipeline steps
    tasks = [(SEGMENTATION_CHAMBERS_TASK, segmentation_chambers_node, "heart"),
             (SEGMENTATION_EFFUSION_TASK, segmentation_effusion_node, "effusion"),
             (SEGMENTATION_ARTERY_TASK, segmentation_artery_node, "artery"),
             (SEGMENTATION_TISSUE_TASK, segmentation_tissue_node, "tissue")]

    # Run all segmentations
    for task, output_node, label in tasks:
        run_totalsegmentator_task(widget, volume_node, output_node, task, label)


    # Save outputs
    outputs = [(segmentation_chambers_node, SEGMENTATION_CHAMBERS_FILENAME),
               (segmentation_effusion_node, SEGMENTATION_EFFUSION_FILENAME),
            #    (segmentation_artery_node, SEGMENTATION_ARTERY_FILENAME),
            #    (segmentation_tissue_node, SEGMENTATION_TISSUE_FILENAME)
            ]

    for node, filename in outputs:
        slicer.util.saveNode(node, str(PATH_FOR_SAVE/filename))

    print("Saved TotalSegmentator outputs")

    return name_to_node
    # slicer.util.exit()

