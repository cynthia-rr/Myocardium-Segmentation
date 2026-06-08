import slicer

from constants import DISPLAY_LEVEL, DISPLAY_WINDOW

def set_segments_visibility(segmentation_node: slicer.vtkMRMLSegmentationNode, 
                              segmentation: slicer.vtkMRMLSegmentationNode, 
                              visible_segmentids: list[str]) -> None:
    display_node = segmentation_node.GetDisplayNode()
    
    for segmentID in segmentation.GetSegmentIDs() - visible_segmentids:
        display_node.SetSegmentVisibility(segmentID, False)
    for segmentID in visible_segmentids:
        display_node.SetSegmentVisibility(segmentID, True)

    # Show the segmentations in 3D, and center the 3D view
    segmentation_node.CreateClosedSurfaceRepresentation() 
    segmentation_node.GetDisplayNode().SetVisibility3D(True)
    slicer.app.layoutManager().threeDWidget(0).threeDView().resetFocalPoint()

    display_node.SetWindow(DISPLAY_WINDOW)
    display_node.SetLevel(DISPLAY_LEVEL)