import logging
import os

import vtk
import numpy as np
import scipy.ndimage # TODO: remove these imports?

import slicer
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.parameterNodeWrapper import parameterNodeWrapper

from slicer import vtkMRMLScalarVolumeNode, vtkMRMLSegmentationNode


MIN_THRESHOLD_VALUE = -1024
MAX_THRESHOLD_VALUE = 3071
MIN_MYOCARDIUM_THRESHOLD_VALUE = -90 
MAX_MYOCARDIUM_THRESHOLD_VALUE = 300
MIN_SCAR_THRESHOLD_VALUE = -1024
MAX_SCAR_THRESHOLD_VALUE = -50
INNER_MYOCARDIUM_LIMIT = 33
MIDDLE_MYOCARDIUM_LIMIT = 67
RIGHT_MYOCARDIUM_GROWTH = 1.0
# keep legacy defaults
LEFT_MYOCARDIUM_GROWTH = 1.0
EDITABLE_ANYWHERE = 0
EDITABLE_OUTSIDE_ALL_SEGMENTS = 3


#
# MyocardiumSegmentationModule
#


class MyocardiumSegmentationModule(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("Myocardium Segmentation Module") 
        self.parent.categories = [translate("qSlicerAbstractCoreModule", "Segmentation")]
        self.parent.dependencies = ["SegmentEditor", "TotalSegmentator"]  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["Cynthia Rong (Lawson Research Institute)"] 
        # TODO: update with short description of the module and a link to online module documentation
        # _() function marks text as translatable to other languages
        self.parent.helpText = _("""Segment the left and right myocardium, divide the left myocardium into three layers, 
                                 and segment potential scar tissue areas. 
                                 For more information see the  <a href="https://github.com/organization/projectname#MyocardiumSegmentationModule">module documentation</a>.""")
        # TODO: replace with organization, grant and thanks
        self.parent.acknowledgementText = _("""
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""")

        # Additional initialization step after application startup is complete
        slicer.app.connect("startupCompleted()", registerSampleData)


#
# Register sample data sets in Sample Data module
#


def registerSampleData():
    """Add data sets to Sample Data module."""
    # It is always recommended to provide sample data for users to make it easy to try the module,
    # but if no sample data is available then this method (and associated startupCompeted signal connection) can be removed.

    import SampleData

    iconsPath = os.path.join(os.path.dirname(__file__), "Resources/Icons")

    # To ensure that the source code repository remains small (can be downloaded and installed quickly)
    # it is recommended to store data sets that are larger than a few MB in a Github release.

    # MyocardiumSegmentationModule1
    SampleData.SampleDataLogic.registerCustomSampleDataSource(
        # Category and sample name displayed in Sample Data module
        category="MyocardiumSegmentationModule",
        sampleName="MyocardiumSegmentationModule1",
        # Thumbnail should have size of approximately 260x280 pixels and stored in Resources/Icons folder.
        # It can be created by Screen Capture module, "Capture all views" option enabled, "Number of images" set to "Single".
        thumbnailFileName=os.path.join(iconsPath, "MyocardiumSegmentationModule1.png"),
        # Download URL and target file name
        uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
        fileNames="MyocardiumSegmentationModule1.nrrd",
        # Checksum to ensure file integrity. Can be computed by this command:
        #  import hashlib; print(hashlib.sha256(open(filename, "rb").read()).hexdigest())
        checksums="SHA256:998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
        # This node name will be used when the data set is loaded
        nodeNames="MyocardiumSegmentationModule1",
    )

    # MyocardiumSegmentationModule2
    SampleData.SampleDataLogic.registerCustomSampleDataSource(
        # Category and sample name displayed in Sample Data module
        category="MyocardiumSegmentationModule",
        sampleName="MyocardiumSegmentationModule2",
        thumbnailFileName=os.path.join(iconsPath, "MyocardiumSegmentationModule2.png"),
        # Download URL and target file name
        uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
        fileNames="MyocardiumSegmentationModule2.nrrd",
        checksums="SHA256:1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
        # This node name will be used when the data set is loaded
        nodeNames="MyocardiumSegmentationModule2",
    )


#
# MyocardiumSegmentationModuleParameterNode
#


@parameterNodeWrapper
class MyocardiumSegmentationModuleParameterNode:
    """
    The parameters needed by module.

    inputVolume - The volume to threshold.
    imageThreshold - The value at which to threshold the input volume.
    invertThreshold - If true, will invert the threshold.
    thresholdedVolume - The output volume that will contain the thresholded volume.
    invertedVolume - The output volume that will contain the inverted thresholded volume.
    """

    inputVolume: vtkMRMLScalarVolumeNode
    chambersSegmentation: vtkMRMLSegmentationNode


#
# MyocardiumSegmentationModuleWidget
#


class MyocardiumSegmentationModuleWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None
        self._parameterNodeGuiTag = None

    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath("UI/MyocardiumSegmentationModule.ui"))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = MyocardiumSegmentationModuleLogic()

        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # Buttons
        self.ui.applyButton.connect("clicked(bool)", self.onApplyButton)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

    def cleanup(self) -> None:
        """Called when the application closes and the module widget is destroyed."""
        self.removeObservers()

    def enter(self) -> None:
        """Called each time the user opens this module."""
        # Make sure parameter node exists and observed
        self.initializeParameterNode()

    def exit(self) -> None:
        """Called each time the user opens a different module."""
        # Do not react to parameter node changes (GUI will be updated when the user enters into the module)
        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self._parameterNodeGuiTag = None
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)

    def onSceneStartClose(self, caller, event) -> None:
        """Called just before the scene is closed."""
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event) -> None:
        """Called just after the scene is closed."""
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self) -> None:
        """Ensure parameter node exists and observed."""
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())

        # Select default input nodes if nothing is selected yet to save a few clicks for the user
        if not self._parameterNode.inputVolume:
            firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
            if firstVolumeNode:
                self._parameterNode.inputVolume = firstVolumeNode
        if not self._parameterNode.chambersSegmentation:
            firstSegmentationNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLSegmentationNode")
            if firstSegmentationNode:
                self._parameterNode.chambersSegmentation = firstSegmentationNode

    def setParameterNode(self, inputParameterNode: MyocardiumSegmentationModuleParameterNode | None) -> None:
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """

        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
            self._checkCanApply()

    def _get_widget_value(self, widget):
        """Return the value of a Qt widget (handles callables like value())."""
        if widget is None:
            return None
        value_attr = getattr(widget, "value", None)
        if callable(value_attr):
            return value_attr()
        return value_attr

    def _get_range_widget_values(self, range_widget):
        """Return (min, max) from a CTK range widget supporting methods or properties."""
        if range_widget is None:
            return None, None
        minimum = getattr(range_widget, "minimumValue", None)
        maximum = getattr(range_widget, "maximumValue", None)
        if callable(minimum):
            minimum = minimum()
        if callable(maximum):
            maximum = maximum()
        return minimum, maximum

    def _checkCanApply(self, caller=None, event=None) -> None:
        if self._parameterNode and self._parameterNode.inputVolume and self._parameterNode.chambersSegmentation:
            self.ui.applyButton.toolTip = _("Segment left and right myocardium")
            self.ui.applyButton.enabled = True
        else:
            self.ui.applyButton.toolTip = _("Select input volume and chambers segmentation node")
            self.ui.applyButton.enabled = False

    def onApplyButton(self) -> None:
        """Run processing when user clicks "Apply" button."""
        right_width = self._get_widget_value(self.ui.RightMyocardiumWidthSpinBox)
        left_width = self._get_widget_value(self.ui.LeftMyocardiumWidthSpinBox)
        inner_percentile, middle_percentile = self._get_range_widget_values(self.ui.RangeWidget)
        min_threshold, max_threshold = self._get_range_widget_values(self.ui.RangeWidget_2)
        if inner_percentile is None or middle_percentile is None:
            raise RuntimeError("Left myocardium layer division values are unavailable.")
        if min_threshold is None or max_threshold is None:
            raise RuntimeError("Myocardium threshold range values are unavailable.")
        with slicer.util.tryWithErrorDisplay(_("Failed to compute results."), waitCursor=True):
            self.logic.process(
                self.ui.inputVolumeSelector.currentNode(),
                self.ui.SegmentationSelector.currentNode(),
                right_myocardium_width=right_width,
                left_myocardium_width=left_width,
                inner_myocardium_percentile=inner_percentile,
                middle_myocardium_percentile=middle_percentile,
                min_threshold=min_threshold,
                max_threshold=max_threshold,
            )


#
# MyocardiumSegmentationModuleLogic
#


class MyocardiumSegmentationModuleLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self) -> None:
        """Called when the logic class is instantiated. Can be used for initializing member variables."""
        ScriptedLoadableModuleLogic.__init__(self)

    def getParameterNode(self):
        return MyocardiumSegmentationModuleParameterNode(super().getParameterNode())

    def process(self,
                input_volume: vtkMRMLScalarVolumeNode,
                segmentation_chambers_node: vtkMRMLSegmentationNode,
                right_myocardium_width: float = RIGHT_MYOCARDIUM_GROWTH,
                left_myocardium_width: float = LEFT_MYOCARDIUM_GROWTH,
                inner_myocardium_percentile: float = INNER_MYOCARDIUM_LIMIT,
                middle_myocardium_percentile: float = MIDDLE_MYOCARDIUM_LIMIT, 
                min_threshold: float = MIN_MYOCARDIUM_THRESHOLD_VALUE, 
                max_threshold: float = MAX_MYOCARDIUM_THRESHOLD_VALUE) -> None:
        """
        Run the left/right myocardium segmentation algorithm.
        Can be used without GUI widget.
        :param inputVolume: input volume used by the segment editor
        :param chambersSegmentation: segmentation node containing left/right ventricles and myocardium
        :param showResult: whether to keep the segment editor internal node visible while running
        """

        if not input_volume or not segmentation_chambers_node:
            raise ValueError("Input volume or chambers segmentation is invalid")

        logging.info("Myocardium segmentation started")

        segmentation = segmentation_chambers_node.GetSegmentation()
        left_myocardium_id = segmentation.GetSegmentIdBySegmentName("myocardium")
        if not left_myocardium_id:
            raise RuntimeError("Could not find segment named 'myocardium' in the chambers segmentation.")
        segmentation.GetSegment(left_myocardium_id).SetName("left myocardium")

        right_ventricle_id = segmentation.GetSegmentIdBySegmentName("right ventricle of heart")
        left_ventricle_id = segmentation.GetSegmentIdBySegmentName("left ventricle of heart")
        if not right_ventricle_id or not left_ventricle_id:
            raise RuntimeError("Could not find required ventricle segments in the chambers segmentation.")

        right_myocardium_id = segmentation.AddEmptySegment("heart_myocardium_right", "right myocardium")

        # Create Segment Editor
        segment_editor_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode", "SegmentEditorNode")
        editor_widget = slicer.qMRMLSegmentEditorWidget()
        editor_widget.setMRMLScene(slicer.mrmlScene)
        editor_widget.setMRMLSegmentEditorNode(segment_editor_node)
        editor_widget.setSegmentationNode(segmentation_chambers_node)
        editor_widget.setSourceVolumeNode(input_volume)

        effects = MyocardiumSegmentationLogic(editor_widget, segment_editor_node)
        effects.segment_right_myocardium(right_ventricle_id, right_myocardium_id, right_myocardium_width,
                         min_threshold, max_threshold)
        effects.improve_left_myocardium(segmentation, left_ventricle_id, left_myocardium_id, left_myocardium_width,
                        min_threshold, max_threshold)
        effects.divide_myocardium(
            input_volume,
            segmentation_chambers_node,
            left_myocardium_id,
            left_ventricle_id,
            inner_myocardium_percentile,
            middle_myocardium_percentile,
        )

        editor_widget.setSegmentationNode(None)
        editor_widget.setSourceVolumeNode(None)
        editor_widget.setMRMLSegmentEditorNode(None)
        slicer.mrmlScene.RemoveNode(segment_editor_node)

        logging.info("Myocardium segmentation completed")



class MyocardiumSegmentationLogic:
    def __init__(self, editor_widget: slicer.qMRMLSegmentEditorWidget,
                 editor_node: slicer.vtkMRMLSegmentEditorNode):
        self.editor_widget = editor_widget
        self.editor_node = editor_node

    def configure_editor(self, segment_id: str,
                         overwrite_mode=slicer.vtkMRMLSegmentEditorNode.OverwriteNone,
                         mask_mode: int = EDITABLE_ANYWHERE, mask_enabled: bool = False,
                         min_threshold: int = 0, max_threshold: int = 0) -> None:
        self.editor_node.SetSelectedSegmentID(segment_id)
        self.editor_node.SetOverwriteMode(overwrite_mode)
        self.editor_node.SetMaskMode(mask_mode)
        self.editor_node.SetSourceVolumeIntensityMask(mask_enabled)
        if mask_enabled:
            self.editor_node.SetSourceVolumeIntensityMaskRange(min_threshold, max_threshold)

    def apply_effect(self, effect_name: str, parameters: dict) -> None:
        self.editor_widget.setActiveEffectByName(effect_name)
        effect = self.editor_widget.activeEffect()
        for key, value in parameters.items():
            effect.setParameter(key, value)
        effect.self().onApply()

    def union_segments(self, source_segment_id: str, destination_segment_id: str) -> None:
        self.configure_editor(destination_segment_id, mask_enabled=False, mask_mode=EDITABLE_ANYWHERE)
        self.apply_effect("Logical operators",
                          {"Operation": "UNION", "ModifierSegmentID": source_segment_id})

    def keep_largest_island(self, destination_segment_id: str) -> None:
        self.configure_editor(destination_segment_id, mask_enabled=False, mask_mode=EDITABLE_ANYWHERE)
        self.apply_effect("Islands", {"Operation": "KEEP_LARGEST_ISLAND"})

    def hollow_segment(self, destination_segment_id: str, thickness_mm: float, shell_mode: str) -> None:
        self.configure_editor(destination_segment_id, mask_enabled=False, mask_mode=EDITABLE_ANYWHERE)
        self.apply_effect("Hollow",
                          {"ShellThicknessMm": thickness_mm,
                           "ShellMode": shell_mode,
                           "ApplyToAllVisibleSegments": 0})

    def grow_shrink_segment(self, destination_segment_id: str, margin_mm: float, mask_mode: int,
                            min_threshold: int, max_threshold: int) -> None:
        self.configure_editor(destination_segment_id, mask_enabled=True, mask_mode=mask_mode,
                              min_threshold=min_threshold, max_threshold=max_threshold)
        self.apply_effect("Margin", {"MarginSizeMm": margin_mm})

    def smooth_segment(self, destination_segment_id: str, kernel_size_mm: float) -> None:
        self.configure_editor(destination_segment_id, mask_enabled=False, mask_mode=EDITABLE_ANYWHERE)
        self.apply_effect("Smoothing",
                          {"SmoothingMethod": "CLOSING", "KernelSizeMm": kernel_size_mm})
        self.apply_effect("Smoothing",
                          {"SmoothingMethod": "MEDIAN", "KernelSizeMm": kernel_size_mm})

    def create_closed_loop(self, segmentation: slicer.vtkMRMLSegmentationNode,
                           left_myocardium_segment_id: str,
                           left_ventricle_segment_id: str) -> None:
        temp_segment_id = segmentation.AddEmptySegment("hollow-left-ventricle", "hollow")
        self.union_segments(left_ventricle_segment_id, temp_segment_id)
        self.hollow_segment(temp_segment_id, thickness_mm=1.5, shell_mode="INSIDE_SURFACE")
        self.union_segments(temp_segment_id, left_myocardium_segment_id)
        segmentation.RemoveSegment(temp_segment_id)

    def segment_right_myocardium(self, right_ventricle_segment_id: str,
                                 right_myocardium_segment_id: str,
                                 width_mm: float, 
                                 min_threshold: float, 
                                 max_threshold: float) -> None:
        self.keep_largest_island(right_ventricle_segment_id)
        self.union_segments(right_ventricle_segment_id, right_myocardium_segment_id)
        self.hollow_segment(right_myocardium_segment_id, 1.5, "OUTSIDE_SURFACE")
        if width_mm != 0:
            self.grow_shrink_segment(right_myocardium_segment_id, width_mm,
                                     EDITABLE_OUTSIDE_ALL_SEGMENTS,
                                     min_threshold, max_threshold)
        self.smooth_segment(right_myocardium_segment_id, max(width_mm / 2, 1.0))

    def improve_left_myocardium(self, segmentation: slicer.vtkMRMLSegmentationNode,
                                left_ventricle_segment_id: str,
                                left_myocardium_segment_id: str,
                                width_mm: float,
                                min_threshold: float, 
                                max_threshold: float) -> None:
        if width_mm != 0:
            self.grow_shrink_segment(left_myocardium_segment_id, width_mm,
                                     EDITABLE_OUTSIDE_ALL_SEGMENTS,
                                     min_threshold, max_threshold)
        self.smooth_segment(left_myocardium_segment_id, max(1.5, width_mm / 2))
        self.create_closed_loop(segmentation, left_myocardium_segment_id, left_ventricle_segment_id)
    

    def divide_myocardium(self, volume_node: slicer.vtkMRMLScalarVolumeNode,
                          segmentation_chambers_node: slicer.vtkMRMLSegmentationNode,
                          myocardium_segment_id: str, ventricle_segment_id: str,
                          inner_percentile: float, middle_percentile: float) -> None:
        """
        Divide the left myocardium into three layers, inner, middle, outer that extend from the left ventricle 
        and end at the edge of the left myocardium. Return the segment IDs of the inner, middle and outer segments. 
        """
        # Export myocardium to myocardium label mapw
        myocardium_labelmap = export_segment_to_labelmap(segmentation_chambers_node, myocardium_segment_id, volume_node, "MyocardiumLabelMap")
        
        # Export left ventricle segment to ventricle label map
        ventricle_labelmap = export_segment_to_labelmap(segmentation_chambers_node, ventricle_segment_id, volume_node, "VentricleLabelMap")

        # Create inner layer labelmap as a duplicate of the myocardium to start off 
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
        inner_percentile = float(max(0.0, min(100.0, inner_percentile)))
        middle_percentile = float(max(0.0, min(100.0, middle_percentile)))
        if inner_percentile >= middle_percentile:
            inner_percentile, middle_percentile = sorted((inner_percentile, middle_percentile))
        inner_limit = np.percentile(wall_depth[myocardium_array], inner_percentile)
        middle_limit = np.percentile(wall_depth[myocardium_array], middle_percentile)

        # Create masks for the 3 segments 
        inner_mask = (myocardium_array & (wall_depth < inner_limit)) 
        inner_mask = scipy.ndimage.binary_closing(inner_mask, iterations=1) # Smoothing
        middle_mask = (myocardium_array & (wall_depth >= inner_limit) & (wall_depth < middle_limit))
        outer_mask = (myocardium_array & (wall_depth >= middle_limit))

        slicer.util.updateVolumeFromArray(inner_labelmap, inner_mask.astype(np.uint8))
        slicer.util.updateVolumeFromArray(middle_labelmap, middle_mask.astype(np.uint8))
        slicer.util.updateVolumeFromArray(outer_labelmap, outer_mask.astype(np.uint8))

        # Rename imported segments 
        inner_id = import_labelmap_to_segmentation(inner_labelmap, segmentation_chambers_node)
        middle_id = import_labelmap_to_segmentation(middle_labelmap, segmentation_chambers_node)
        outer_id = import_labelmap_to_segmentation(outer_labelmap, segmentation_chambers_node)

        # Set colors for the left myocardium layers: inner light pink, middle light green, outer light blue.
        segmentation = segmentation_chambers_node.GetSegmentation()
        for segment_id, color in (
            (inner_id, (1.0, 0.75, 0.8)),
            (middle_id, (0.75, 1.0, 0.75)),
            (outer_id, (0.7, 0.85, 1.0)),
        ):
            segment = segmentation.GetSegment(segment_id)
            if segment:
                segment.SetColor(*color)

        # Remove temporary labelmaps
        for node in [inner_labelmap, middle_labelmap, outer_labelmap, myocardium_labelmap, ventricle_labelmap]:
            slicer.mrmlScene.RemoveNode(node)

        return inner_id, middle_id, outer_id # Return segment IDs


# TODO: figure out where to put this
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
        raise RuntimeError("Expected exactly one imported segment. New ids: ", len(new_ids))

    return new_ids.pop()



#
# MyocardiumSegmentationModuleTest
#


class MyocardiumSegmentationModuleTest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        """Do whatever is needed to reset the state - typically a scene clear will be enough."""
        slicer.mrmlScene.Clear()

    def runTest(self):
        """Run as few or as many tests as needed here."""
        self.setUp()
        self.test_MyocardiumSegmentationModule1()

    def test_MyocardiumSegmentationModule1(self):
        """Ideally you should have several levels of tests.  At the lowest level
        tests should exercise the functionality of the logic with different inputs
        (both valid and invalid).  At higher levels your tests should emulate the
        way the user would interact with your code and confirm that it still works
        the way you intended.
        One of the most important features of the tests is that it should alert other
        developers when their changes will have an impact on the behavior of your
        module.  For example, if a developer removes a feature that you depend on,
        your test should break so they know that the feature is needed.
        """

        self.delayDisplay("Starting the test")

        # Get/create input data

        import SampleData

        registerSampleData()
        inputVolume = SampleData.downloadSample("MyocardiumSegmentationModule1")
        self.delayDisplay("Loaded test data set")

        inputScalarRange = inputVolume.GetImageData().GetScalarRange()
        self.assertEqual(inputScalarRange[0], 0)
        self.assertEqual(inputScalarRange[1], 695)

        outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
        threshold = 100

        # Test the module logic

        logic = MyocardiumSegmentationModuleLogic()

        # Test algorithm with non-inverted threshold
        logic.process(inputVolume, outputVolume, threshold, True)
        outputScalarRange = outputVolume.GetImageData().GetScalarRange()
        self.assertEqual(outputScalarRange[0], inputScalarRange[0])
        self.assertEqual(outputScalarRange[1], threshold)

        # Test algorithm with inverted threshold
        logic.process(inputVolume, outputVolume, threshold, False)
        outputScalarRange = outputVolume.GetImageData().GetScalarRange()
        self.assertEqual(outputScalarRange[0], inputScalarRange[0])
        self.assertEqual(outputScalarRange[1], inputScalarRange[1])

        self.delayDisplay("Test passed")
