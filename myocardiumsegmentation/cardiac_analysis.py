import slicer
import vtk
import numpy as np
import scipy.ndimage

from segmentation_constants import *
from segmentation_utils import *
from io_utils import export_segment_to_labelmap, import_labelmap_to_segmentation, remove_nodes

def segment_right_myocardium(editor_widget: slicer.qMRMLSegmentEditorWidget, editor_node: slicer.vtkMRMLSegmentEditorNode,
                             right_ventricle_segment_id: str, right_myocardium_segment_id: str) -> None:
    """
    Segment the right myocardium by creating a hollow shell of the right ventricle segment, then growing the shell 
    according to the RIGHT_MYOCARDIUM_GROWTH amount. Return none, mutate the segment using the 
    right_myocardium_segment_id.
    """
    keep_largest_island(editor_widget, editor_node, right_ventricle_segment_id)
    union_segments(editor_widget, editor_node, right_ventricle_segment_id, right_myocardium_segment_id)
    hollow_segment(editor_widget, editor_node, right_myocardium_segment_id, 1.5, "OUTSIDE_SURFACE") 
    # TODO: make 1.5 a constant, smallest value depends on image resolution
    if RIGHT_MYOCARDIUM_GROWTH != 0:
        grow_shrink_segment(editor_widget, editor_node, right_myocardium_segment_id, RIGHT_MYOCARDIUM_GROWTH, #TODO: remove the editable outside segments?
                    EDITABLE_OUTSIDE_ALL_SEGMENTS, MIN_MYOCARDIUM_THRESHOLD_VALUE, MAX_MYOCARDIUM_THRESHOLD_VALUE)
    smooth_segment(editor_widget, editor_node, right_myocardium_segment_id, max(RIGHT_MYOCARDIUM_GROWTH/2, 1.0))

def improve_left_myocardium(segmentation: slicer.vtkMRMLSegmentationNode, editor_widget: slicer.qMRMLSegmentEditorWidget, 
                            editor_node: slicer.vtkMRMLSegmentEditorNode, left_ventricle_segment_id: str, 
                            left_myocardium_segment_id: str) -> None:
    """
    Segment the left myocardium by growing the existing left myocardium segment according to LEFT_MYOCARDIUM_GROWTH, 
    smoothing, and unioning with a hollow to make a closed loop. Return none, mutate the segment using 
    left_myocardium_segment_id. 
    """
    if LEFT_MYOCARDIUM_GROWTH != 0:
        grow_shrink_segment(editor_widget, editor_node, left_myocardium_segment_id, LEFT_MYOCARDIUM_GROWTH, EDITABLE_OUTSIDE_ALL_SEGMENTS,
                        MIN_MYOCARDIUM_THRESHOLD_VALUE, MAX_MYOCARDIUM_THRESHOLD_VALUE)
    smooth_segment(editor_widget, editor_node, left_myocardium_segment_id, max(1.0, LEFT_MYOCARDIUM_GROWTH/2))
    create_closed_loop(segmentation, editor_widget, editor_node, left_myocardium_segment_id, left_ventricle_segment_id)

def divide_myocardium(volume_node: slicer.vtkMRMLScalarVolumeNode,
                    segmentation_chambers_node: slicer.vtkMRMLSegmentationNode, 
                    myocardium_segment_id: str, ventricle_segment_id: str) -> None:
    """
    Divide the left myocardium into three layers, inner, middle, outer that extend from the left ventricle 
    and end at the edge of the left myocardium. Return the segment IDs of the inner, middle and outer segments. 
    """
    # Export myocardium to myocardium label mapw
    myocardium_labelmap = export_segment_to_labelmap(segmentation_chambers_node, myocardium_segment_id, volume_node, "MyocardiumLabelMap")
    
    # Export left ventricle segment to ventricle label map
    ventricle_labelmap = export_segment_to_labelmap(segmentation_chambers_node, ventricle_segment_id, volume_node, "VentricleLabelMap")

    # Create inner layer labelmap as a duplicate of the myocardium to start off 
    # TODO: change it so that it takes the inner, middle, outer segment id as input?
    inner_labelmap = export_segment_to_labelmap(segmentation_chambers_node, myocardium_segment_id, volume_node, "InnerLayerLabelMap")
    middle_labelmap = export_segment_to_labelmap(segmentation_chambers_node, myocardium_segment_id, volume_node, "MiddleLayerLabelMap")
    outer_labelmap = export_segment_to_labelmap(segmentation_chambers_node, myocardium_segment_id, volume_node, "OuterLayerLabelMap")

    # Convert from volume to array
    myocardium_array = slicer.util.arrayFromVolume(myocardium_labelmap).astype(bool)
    ventricle_array = slicer.util.arrayFromVolume(ventricle_labelmap).astype(bool)
    spacingXYZ = myocardium_labelmap.GetSpacing()
    spacing = spacingXYZ[::-1]

    # Calculate distance to endocardium and epicardium
    distance_endocardium = scipy.ndimage.distance_transform_edt(~ventricle_array, sampling=spacing)
    distance_epicardium = scipy.ndimage.distance_transform_edt(myocardium_array, sampling=spacing)
    
    # Restrict to myocardium only
    distance_endocardium = np.abs(distance_endocardium)
    distance_epicardium = np.maximum(distance_epicardium, 0)

    # Calculate wall depth, and smoothing to prevent protrusions
    wall_depth = distance_endocardium / (distance_endocardium + distance_epicardium + 1e-6) # to prevent division by 0
    wall_depth = scipy.ndimage.gaussian_filter(wall_depth, sigma=1.5) # TODO: magic numbers

    # Calculate percentile for inner layer, middle layer
    inner_limit = np.percentile(wall_depth[myocardium_array], INNER_MYOCARDIUM_LIMIT)
    middle_limit = np.percentile(wall_depth[myocardium_array], MIDDLE_MYOCARDIUM_LIMIT)

    # Create masks for the 3 segments 
    inner_mask = (myocardium_array & (wall_depth < inner_limit)) 
    inner_mask = scipy.ndimage.binary_closing(inner_mask, iterations=1) # Smoothing
    middle_mask = (myocardium_array & (wall_depth >= inner_limit) & (wall_depth < middle_limit))
    outer_mask = (myocardium_array & (wall_depth >= middle_limit))

    slicer.util.updateVolumeFromArray(inner_labelmap, inner_mask.astype(np.uint8))
    slicer.util.updateVolumeFromArray(middle_labelmap, middle_mask.astype(np.uint8))
    slicer.util.updateVolumeFromArray(outer_labelmap, outer_mask.astype(np.uint8))

    # TODO: is there a way to import to a specific segment? instead of making a new segment
    # Rename imported segments # TODO: how do i make these fit undet the volume_node? maybe help alignment
    inner_id = import_labelmap_to_segmentation(inner_labelmap, segmentation_chambers_node)
    middle_id = import_labelmap_to_segmentation(middle_labelmap, segmentation_chambers_node)
    outer_id = import_labelmap_to_segmentation(outer_labelmap, segmentation_chambers_node)

    # Remove temporary labelmaps
    remove_nodes(inner_labelmap, middle_labelmap, outer_labelmap, myocardium_labelmap, ventricle_labelmap)
    return inner_id, middle_id, outer_id # Return segment IDs


def segment_scar(segmentation: slicer.vtkMRMLSegmentationNode, segmentation_effusion_node: slicer.vtkMRMLSegmentationNode, 
                 editor_widget: slicer.qMRMLSegmentEditorWidget, editor_node: slicer.vtkMRMLSegmentEditorNode, 
                 scar_segment_id: str, pleural_segment_id: str, border_segment_id: str) -> None:
    """Segment the general scar area by using a threshold, and subtracting the pleural border."""
    threshold_segment(editor_widget, editor_node, scar_segment_id, MIN_SCAR_THRESHOLD_VALUE, MAX_SCAR_THRESHOLD_VALUE)
    segmentation.CopySegmentFromSegmentation(segmentation_effusion_node.GetSegmentation(), pleural_segment_id)
    # Copy the Pleural Effusion into the Border segment 
    union_segments(editor_widget, editor_node, pleural_segment_id, border_segment_id)
    hollow_segment(editor_widget, editor_node, border_segment_id, PLEURAL_BORDER_WIDTH, "INSIDE_SURFACE")
    subtract_segments(editor_widget, editor_node, border_segment_id, scar_segment_id)

def segment_scar_in_region(editor_widget: slicer.qMRMLSegmentEditorWidget, editor_node: slicer.vtkMRMLSegmentEditorNode, 
                           scar_segment_id: str, region_segment_id: str, destination_segment_id: str) -> None:
    """Set the scar destination segment to be the intersection of the general scar and the target region."""
    union_segments(editor_widget, editor_node, region_segment_id, destination_segment_id)
    intersect_segments(editor_widget, editor_node, scar_segment_id, destination_segment_id)
    # TODO: and subtract for better visual?


# TODO: come up with a better name than this
def segment_scar_sections(editor_widget: slicer.qMRMLSegmentEditorWidget, editor_node: slicer.qMRMLSegmentEditorWidget, 
                            scar_segment_id: str, region_to_scar_segment_id: dict[str, str]) -> None:
    """Segment the right scar, the left scar, the left inner, middle and outer scars by calling segment_scar_in_region
    for each (region, scar) pair. For ex. (left_myocardium_id, left_scar_id), (left_inner_myocardium_id, left_inner_scar_id)"""

    # TODO: fix magic numbers
    smooth_segment(editor_widget, editor_node, scar_segment_id, 1.2)

    for region_segment_id in region_to_scar_segment_id:
        segment_scar_in_region(editor_widget, editor_node, scar_segment_id, region_segment_id, region_to_scar_segment_id[region_segment_id])


def segment_wall_thickness(volume_node: slicer.vtkMRMLScalarVolumeNode, segmentation_node: slicer.vtkMRMLSegmentationNode, 
                           myocardium_segment_id: str, ventricle_segment_id: str):
    """Segment the left myocardium into two segments, one segment thinner than the WALL_THICKNESS_THRESHOLD_MM,
     and one thicker. Return the segment Ids. """

    # Export myocardium labelmap
    myocardium_labelmap = export_segment_to_labelmap(segmentation_node, myocardium_segment_id, volume_node, "Myocardium")
    myocardium = slicer.util.arrayFromVolume(myocardium_labelmap).astype(bool)

    spacing = np.array(myocardium_labelmap.GetSpacing())

    # Use a step no larger than half the smallest voxel
    step_mm = min(np.min(spacing) * 0.5, WALL_THICKNESS_STEP_MM)

    # Create surface of left ventricle
    segmentation_node.CreateClosedSurfaceRepresentation()
    ventricle_polydata = vtk.vtkPolyData()
    segmentation_node.GetClosedSurfaceRepresentation(ventricle_segment_id, ventricle_polydata)

    # Compute point normals (orthogonal to left ventricle surface)
    normals = vtk.vtkPolyDataNormals()
    normals.SetInputData(ventricle_polydata)
    normals.ComputePointNormalsOn()
    normals.SplittingOff()
    normals.ConsistencyOn()
    normals.AutoOrientNormalsOn()
    normals.Update()

    ventricle_polydata = normals.GetOutput()
    point_normals = ventricle_polydata.GetPointData().GetNormals()
    center = np.array(ventricle_polydata.GetCenter())

    # Map of thickness (direct access table, voxel is the index, length of ray is value)
    thickness_map = np.full(myocardium.shape, np.inf, dtype=np.float32)

    ras_to_ijk = vtk.vtkMatrix4x4()
    myocardium_labelmap.GetRASToIJKMatrix(ras_to_ijk)


    # Cast one ray per surface vertex in left ventricle
    for index in range(ventricle_polydata.GetNumberOfPoints()):

        point = np.array(ventricle_polydata.GetPoint(index))
        normal = np.array(point_normals.GetTuple(index))

        # Orient normals to outward direction (away from left ventricle)
        if np.dot(point - center, normal) < 0:
            normal = -normal

        # Start slightly inside myocardium
        length = 0.5
        voxels = []

        while True: # TODO: fix?

            world = point + length * normal
            ijk4 = ras_to_ijk.MultiplyPoint([world[0], world[1], world[2], 1.0])

            ijk_i = int(round(ijk4[0]))
            ijk_j = int(round(ijk4[1]))
            ijk_k = int(round(ijk4[2]))


            if not myocardium[ijk_k, ijk_j, ijk_i]:
                break

            voxels.append((ijk_k, ijk_j, ijk_i))
            length += step_mm

        # Update minimum thickness for every voxel
        for voxel in voxels:
            if length < thickness_map[voxel]:
                thickness_map[voxel] = length


    # Smooth to fill in the unknown voxel gaps
    unknown = myocardium & ~np.isfinite(thickness_map)
    _, indices = scipy.ndimage.distance_transform_edt(unknown, return_indices=True, return_distances=True)

    thickness_map[unknown] = thickness_map[tuple(indices[:, unknown])]

    # Create thin and thick masks
    thin = np.zeros_like(myocardium, dtype=np.uint8)
    thick = np.zeros_like(myocardium, dtype=np.uint8)

    valid = np.isfinite(thickness_map)

    thin[valid & (thickness_map < WALL_THICKNESS_THRESHOLD_MM)] = 1
    thick[valid & (thickness_map >= WALL_THICKNESS_THRESHOLD_MM)] = 1

    # Export labelmaps for thin and thick
    thin_labelmap = export_segment_to_labelmap(segmentation_node, myocardium_segment_id, volume_node, "Left Myocardium Thin")
    thick_labelmap = export_segment_to_labelmap(segmentation_node, myocardium_segment_id, volume_node, "Left Myocardium Thick")
    
    # Update thin and thick labelmaps using the masks
    slicer.util.updateVolumeFromArray(thin_labelmap, thin.astype(np.uint8))
    slicer.util.updateVolumeFromArray(thick_labelmap, thick.astype(np.uint8))
    
    # Convert thin and thick labelmaps to segments
    thin_id = import_labelmap_to_segmentation(thin_labelmap, segmentation_node)
    thick_id = import_labelmap_to_segmentation(thick_labelmap, segmentation_node)

    # Remove temporary myocardium, thin and thick labelmaps
    remove_nodes(thin_labelmap, thick_labelmap, myocardium_labelmap)

    return thin_id, thick_id

