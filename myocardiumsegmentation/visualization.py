import slicer

from io_constants import DISPLAY_LEVEL, DISPLAY_WINDOW

def set_segments_visibility(segmentation_node: slicer.vtkMRMLSegmentationNode, 
                            segmentation: slicer.vtkMRMLSegmentationNode, 
                              visible_segmentids: list[str], 
                              volume_node: slicer.vtkMRMLScalarVolumeNode) -> None:
    display_node = segmentation_node.GetDisplayNode()
    
    for segmentID in set(segmentation.GetSegmentIDs()) - set(visible_segmentids):
        display_node.SetSegmentVisibility(segmentID, False)
    for segmentID in visible_segmentids:
        display_node.SetSegmentVisibility(segmentID, True)

    # Show the segmentations in 3D, and center the 3D view
    segmentation_node.CreateClosedSurfaceRepresentation() 
    segmentation_node.GetDisplayNode().SetVisibility3D(True)
    slicer.app.layoutManager().threeDWidget(0).threeDView().resetFocalPoint()

    volume_node.GetDisplayNode().SetWindow(DISPLAY_WINDOW)
    volume_node.GetDisplayNode().SetLevel(DISPLAY_LEVEL)