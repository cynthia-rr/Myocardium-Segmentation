import logging
import os
# from token import LEFTSHIFTEQUAL

import vtk
from typing import Any

import slicer
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import (
    ScriptedLoadableModule,
    ScriptedLoadableModuleLogic,
    ScriptedLoadableModuleTest,
    ScriptedLoadableModuleWidget,
)
from slicer.parameterNodeWrapper import parameterNodeWrapper
from slicer.util import VTKObservationMixin
from slicer import vtkMRMLScalarVolumeNode, vtkMRMLSegmentationNode


SEGMENTATION_QUALITY = "normal"
SEGMENTATION_CHAMBERS_TASK = "heartchambers_highres"
SEGMENTATION_CHAMBERS_NODE_NAME = "Chambers-Segmentation"
COLOUR_PINK = (1.0, 0.8, 1.0)
COLOUR_GREEN = (0.6, 0.8, 0.6)
COLOUR_LIGHT_BLUE = (0.7, 0.8, 1.0)
COLOUR_PURPLE = (0.6, 0.5, 1.0)

# keep legacy defaults
EDITABLE_ANYWHERE = 0
EDITABLE_OUTSIDE_ALL_SEGMENTS = 3
DISPLAY_WINDOW = 800
DISPLAY_LEVEL = 200


#
# MyocardiumSegmentationModule
#


class MyocardiumSegmentationModule(ScriptedLoadableModule): # TODO: complete the help text, dependencies, acknowledgements
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
        self.parent.helpText = _("""Segment the right myocardium, adjust the left myocardium segmentation 
                                and divide the left myocardium into three layers. 
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


def registerSampleData(): # TODO: add sample data 
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
        sampleName="MyocardiumSegmentationSample",
        # Thumbnail should have size of approximately 260x280 pixels and stored in Resources/Icons folder.
        # It can be created by Screen Capture module, "Capture all views" option enabled, "Number of images" set to "Single".
        thumbnailFileName=os.path.join(iconsPath, "MyocardiumSegmentationModule1.png"),
        # Download URL and target file name
        uris="https://github.com/cynthia-rr/Myocardium-Segmentation/releases/download/TestData/ct-heart.nii.gz",
        # fileNames="ctheart.nii.gz",
        # Checksum to ensure file integrity. Can be computed by this command:
        #  import hashlib; print(hashlib.sha256(open(filename, "rb").read()).hexdigest())
        checksums="sha256:a2d5db462f0226955b7836fb6c4670ea0aceaee87431ffc16e980bad3736c0e3",
        # This node name will be used when the data set is loaded
        nodeNames="MyocardiumSegmentationModule1",
    )





#
# MyocardiumSegmentationModuleParameterNode
#


@parameterNodeWrapper
class MyocardiumSegmentationModuleParameterNode:
    """
    The parameters needed by module.

    inputVolume - The volume to segment the myocardium and scar from.
    segmentationNode - The segmentation node to put the final segmentation in.
    myocardiumLowerThreshold - The lower threshold of HU values for myocardium tissue.
    myocardiumUpperThreshold - The upper threshold of HU values for myocardium tissue.
    rightMyocardiumWidth - The width of the right myocardium in mm.
    leftMyocardiumGrowth - The growth of the left myocardium in mm to be thicker or thinner.
    myocardiumInnerLimit - The percentile for the inner layer of the left myocardium.
    myocardiumMiddleLimit - The percentile for the middle layer of the left myocardium.
    """

    inputVolume: vtkMRMLScalarVolumeNode
    segmentationNode: vtkMRMLSegmentationNode
    myocardiumLowerThreshold: float
    myocardiumUpperThreshold: float
    rightMyocardiumWidth: float
    leftMyocardiumGrowth: float
    myocardiumInnerLimit: float
    myocardiumMiddleLimit: float


#
# MyocardiumSegmentationModuleWidget


class MyocardiumSegmentationModuleWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)
        self.logic = None
        self._parameterNode = None
        self._parameterNodeGuiTag = None

    def setup(self) -> None:
        """Called when the user opens the module the first time."""
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        uiWidget = slicer.util.loadUI(self.resourcePath("UI/MyocardiumSegmentationModule.ui"))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class.
        self.logic = MyocardiumSegmentationModuleLogic()

        # Connections
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # Buttons
        self.ui.SegmentButton.connect("clicked(bool)", self.onSegment)
        self.ui.UpdateButton.connect("clicked(bool)", self.onUpdate)
        self.ui.InputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self._checkCanSegment) 
        self.ui.InputVolumeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self._checkCanUpdate)
        self.ui.SegmentationSelector.connect("currentNodeChanged(vtkMRMLNode*)", self._checkCanSegment)
        self.ui.SegmentationSelector.connect("currentNodeChanged(vtkMRMLNode*)", self._checkCanUpdate)

        self.initializeParameterNode()
        self._checkCanSegment()
        self._checkCanUpdate()

    def cleanup(self) -> None:
        """Called when the application closes and the module widget is destroyed."""
        self.removeObservers()

    def enter(self) -> None:
        """Called each time the user opens this module."""
        self.initializeParameterNode()

    def exit(self) -> None:
        """Called each time the user opens a different module."""
        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self._parameterNodeGuiTag = None
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanSegment)
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanUpdate)

    def onSceneStartClose(self, caller, event) -> None:
        """Called just before the scene is closed."""
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event) -> None:
        """Called just after the scene is closed."""
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self) -> None:
        """Ensure parameter node exists, observed, and has default node selections."""
        self.setParameterNode(self.logic.getParameterNode())

        if not self._parameterNode:
            return

        if not self._parameterNode.inputVolume:
            firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
            if firstVolumeNode:
                self._parameterNode.inputVolume = firstVolumeNode
                self.ui.InputVolumeSelector.setCurrentNode(firstVolumeNode)
        if not self._parameterNode.segmentationNode:
            segmentationNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLSegmentationNode")
            if segmentationNode:
                self._parameterNode.segmentationNode = segmentationNode
                self.ui.SegmentationSelector.setCurrentNode(segmentationNode)

    def setParameterNode(self, inputParameterNode: MyocardiumSegmentationModuleParameterNode | None) -> None:
        """Set and observe parameter node."""
        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanSegment)
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanUpdate)

        self._parameterNode = inputParameterNode
        if self._parameterNode:
            self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanSegment)
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanUpdate)
            self._checkCanSegment()
            self._checkCanUpdate()

    def _checkCanSegment(self, caller=None, event=None) -> None:
        """
        Check if the user is able to segment.
        """
        input_volume = self.ui.InputVolumeSelector.currentNode()
        segmentation_node = self.ui.SegmentationSelector.currentNode()

        if input_volume and segmentation_node:
            self.ui.SegmentButton.toolTip = _("Click to run initial TotalSegmentator segmentation")
            self.ui.SegmentButton.enabled = True
        else:
            self.ui.SegmentButton.toolTip = _("Select an input volume and segmentation first.")
            self.ui.SegmentButton.enabled = False

    def _checkCanUpdate(self, caller=None, event=None) -> None:
        """
        Check if the user is able to update the segmentation.
        """
        input_volume = self.ui.InputVolumeSelector.currentNode()
        segmentation_node = self.ui.SegmentationSelector.currentNode()

        if input_volume and segmentation_node:
            self.ui.UpdateButton.toolTip = _("Click to segment or re-segment the right myocardium and left myocardium layers.")
            self.ui.UpdateButton.enabled = True
        else:
            self.ui.UpdateButton.toolTip = _("Select an input volume and segmentation.")
            self.ui.UpdateButton.enabled = False

    def _get_widget_value(self, widget) -> Any:
        """Return the value of a Qt widget (handles callables like value())."""
        if widget is None:
            return None
        value_attr = getattr(widget, "value", None)
        if callable(value_attr):
            return value_attr()
        return value_attr

    def _get_range_widget_values(self, range_widget) -> tuple[int, int]:
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

    def onUpdate(self) -> None:
        """Run processing when user clicks "Update" button."""
        if not self._parameterNode:
            raise RuntimeError("Parameter node is not initialized.")

        # Update parameter node with the latest UI values.
        self._parameterNode.rightMyocardiumWidth = self._get_widget_value(self.ui.RightMyocardiumWidthSpinBox)
        self._parameterNode.leftMyocardiumGrowth = self._get_widget_value(self.ui.LeftMyocardiumGrowthSpinBox)
        inner_percentile, middle_percentile = self._get_range_widget_values(self.ui.PercentileRangeWidget) 
        # TODO: use ranges as just tuples instead of converting to 2 separate values
        min_threshold, max_threshold = self._get_range_widget_values(self.ui.ThresholdRangeWidget)
        self._parameterNode.myocardiumInnerLimit = inner_percentile
        self._parameterNode.myocardiumMiddleLimit = middle_percentile
        self._parameterNode.myocardiumLowerThreshold = min_threshold
        self._parameterNode.myocardiumUpperThreshold = max_threshold
        self._parameterNode.segmentationNode = self.ui.SegmentationSelector.currentNode()

        if inner_percentile is None or middle_percentile is None:
            raise RuntimeError("Left myocardium layer division values are unavailable.")
        if min_threshold is None or max_threshold is None:
            raise RuntimeError("Myocardium threshold range values are unavailable.")
        if not self._parameterNode.segmentationNode:
            raise RuntimeError("Segmentation is not selected.")

        with slicer.util.tryWithErrorDisplay(_("Failed to compute results."), waitCursor=True):
            self.logic.process(
                self._parameterNode.inputVolume,
                self._parameterNode.segmentationNode,
                self._parameterNode.rightMyocardiumWidth,
                self._parameterNode.leftMyocardiumGrowth,
                self._parameterNode.myocardiumInnerLimit,
                self._parameterNode.myocardiumMiddleLimit,
                self._parameterNode.myocardiumLowerThreshold,
                self._parameterNode.myocardiumUpperThreshold
                )

    def onSegment(self) -> None:
        """Run TotalSegmentator when user clicks the 'Segment' button."""
        if not self._parameterNode or not self._parameterNode.inputVolume or not self._parameterNode.segmentationNode:
            raise RuntimeError("Input volume or segmentation node is not available.")

        with slicer.util.tryWithErrorDisplay(_("Failed to run TotalSegmentator."), waitCursor=True):
            self.logic.run_total_segmentator(self._parameterNode.inputVolume, self._parameterNode.segmentationNode)
            # self._parameterNode.segmentationNode = chambers_node
            # self.ui.SegmentationSelector.setCurrentNode(chambers_node)
            self._checkCanSegment()


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

    def __init__(self, editor_widget: slicer.qMRMLSegmentEditorWidget = None,
                 editor_node: slicer.vtkMRMLSegmentEditorNode = None) -> None:
        """Called when the logic class is instantiated. Can be used for initializing member variables."""
        ScriptedLoadableModuleLogic.__init__(self)
        self.editor_widget = editor_widget
        self.editor_node = editor_node

    def getParameterNode(self):
        return MyocardiumSegmentationModuleParameterNode(super().getParameterNode())

    def run_total_segmentator(self, input_volume: vtkMRMLScalarVolumeNode, 
                              segmentation_node: vtkMRMLSegmentationNode) -> None:
        """Run TotalSegmentator."""
        if not input_volume:
            raise ValueError("Input volume is invalid")

        widget = slicer.modules.totalsegmentator.widgetRepresentation()
        if not widget or not hasattr(widget, "self"):
            raise RuntimeError("TotalSegmentator widget is not available. Ensure the TotalSegmentator extension is installed.")

        widget_self = widget.self()
        if not widget_self or not hasattr(widget_self, "logic"):
            raise RuntimeError("TotalSegmentator logic is not available.")

        # segmentation_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", SEGMENTATION_CHAMBERS_NODE_NAME)
        widget_self.logic.process(inputVolume=input_volume,
                                  outputSegmentation=segmentation_node,
                                  quality=SEGMENTATION_QUALITY,
                                  task=SEGMENTATION_CHAMBERS_TASK)

        if not segmentation_node.GetSegmentation().GetSegmentIDs():
            raise RuntimeError("TotalSegmentator chamber segmentation failed.")

        # return segmentation_node

    def process(self,
                input_volume: vtkMRMLScalarVolumeNode,
                segmentation_node: vtkMRMLSegmentationNode,
                right_myocardium_width: float,
                left_myocardium_growth: float,
                inner_myocardium_percentile: float,
                middle_myocardium_percentile: float,
                min_threshold: float,
                max_threshold: float) -> None:
        """ # TODO: fix the docstring and the parameters
        Run the left/right myocardium segmentation algorithm.
        Can be used without GUI widget.
        :param input_volume: input volume used by the segment editor
        :param segmentation_node: segmentation node containing left/right ventricles and myocardium (input)
        :param right_myocardium_width: thickness of right myocardium in mm
        :param left_myocardium_growth: how much thicker or thinner the left myocardium should be compared to the original segment
        :param inner_myocardium_percentile: percentage of left myocardium attributed to the inner layer
        :param middle_myocardium_percentile: percentage of the left myocardium attributed to the inner and middle layers
        :param min_threshold: minimum HU threshold for myocardium tissue 
        :param max_threshold: maximum HU threshold for myocardium tissue
        """

        # if not input_volume or not segmentation_chambers_node:
        if not input_volume:
            raise ValueError("Input volume is invalid")

        logging.info("Myocardium segmentation started")

        segmentation_myocardium = segmentation_node.GetSegmentation()

        # If there are old inner, middle, outer myocardium segments from previous process, remove them
        for name in {"inner left myocardium", "middle left myocardium", "outer left myocardium"}:
            temp_id = segmentation_myocardium.GetSegmentIdBySegmentName(name)
            if temp_id: # If not None, then remove
                segmentation_myocardium.RemoveSegment(temp_id)



        left_myocardium_id = segmentation_myocardium.GetSegmentIdBySegmentName("myocardium")
        if not left_myocardium_id:
            raise RuntimeError("Could not find segment named 'myocardium' in the chambers segmentation.")

        right_ventricle_id = segmentation_myocardium.GetSegmentIdBySegmentName("right ventricle of heart")
        left_ventricle_id = segmentation_myocardium.GetSegmentIdBySegmentName("left ventricle of heart")
        if not right_ventricle_id or not left_ventricle_id:
            raise RuntimeError("Could not find required ventricle segments in the chambers segmentation.")

        right_myocardium_id = segmentation_myocardium.GetSegmentIdBySegmentName("right_myocardium")
        if right_myocardium_id: # If not None, then remove the old segment before making another
            segmentation_myocardium.RemoveSegment(right_myocardium_id)
        # Create a new segment
        right_myocardium_id = segmentation_myocardium.AddEmptySegment("heart_myocardium_right", "right myocardium")
        segmentation_myocardium.GetSegment(right_myocardium_id).SetColor(COLOUR_PURPLE)

        # Create Segment Editor
        segment_editor_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode", "SegmentEditorNode")
        editor_widget = slicer.qMRMLSegmentEditorWidget()
        editor_widget.setMRMLScene(slicer.mrmlScene)
        editor_widget.setMRMLSegmentEditorNode(segment_editor_node)
        editor_widget.setSegmentationNode(segmentation_node)
        editor_widget.setSourceVolumeNode(input_volume)

        segmentation_logic = MyocardiumSegmentationModuleLogic(editor_widget, segment_editor_node)
        segmentation_logic.segment_right_myocardium(right_ventricle_id, right_myocardium_id, right_myocardium_width,
                         min_threshold, max_threshold)
        segmentation_logic.improve_left_myocardium(segmentation_myocardium, left_ventricle_id, left_myocardium_id, left_myocardium_growth,
                        min_threshold, max_threshold)
        inner_id, middle_id, outer_id = segmentation_logic.divide_myocardium(
            input_volume,
            segmentation_node,
            left_myocardium_id,
            left_ventricle_id,
            inner_myocardium_percentile,
            middle_myocardium_percentile,
        )

        segmentation_myocardium.GetSegment(inner_id).SetName("inner left myocardium")
        segmentation_myocardium.GetSegment(middle_id).SetName("middle left myocardium")
        segmentation_myocardium.GetSegment(outer_id).SetName("outer left myocardium")
        segmentation_myocardium.GetSegment(inner_id).SetColor(COLOUR_PINK)
        segmentation_myocardium.GetSegment(middle_id).SetColor(COLOUR_GREEN)
        segmentation_myocardium.GetSegment(outer_id).SetColor(COLOUR_LIGHT_BLUE)


        # segmentation_logic.set_segments_visibility(segmentation_node, 
        #                                            [inner_id, middle_id, outer_id, right_myocardium_id], 
        #                                            input_volume)

        editor_widget.setSegmentationNode(None)
        editor_widget.setSourceVolumeNode(None)
        editor_widget.setMRMLSegmentEditorNode(None)
        slicer.mrmlScene.RemoveNode(segment_editor_node)

        logging.info("Myocardium segmentation completed")

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

    def copy_segment(self, source_segment_id: str, destination_segment_id: str) -> None:
        self.configure_editor(destination_segment_id, mask_enabled=False, mask_mode=EDITABLE_ANYWHERE)
        self.apply_effect("Logical operators", {"Operation": "COPY", "ModifierSegmentID": source_segment_id})

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
        self.copy_segment(left_ventricle_segment_id, temp_segment_id)
        self.hollow_segment(temp_segment_id, thickness_mm=1.5, shell_mode="INSIDE_SURFACE")
        self.union_segments(temp_segment_id, left_myocardium_segment_id)
        segmentation.RemoveSegment(temp_segment_id)

    def segment_right_myocardium(self, right_ventricle_segment_id: str,
                                 right_myocardium_segment_id: str,
                                 width_mm: float, 
                                 min_threshold: float, 
                                 max_threshold: float) -> None:
        self.keep_largest_island(right_ventricle_segment_id)
        self.copy_segment(right_ventricle_segment_id, right_myocardium_segment_id)
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
                          inner_percentile: float, middle_percentile: float) -> tuple[str, str, str]:
        """
        Divide the left myocardium into three layers, inner, middle, outer that extend from the left ventricle 
        and end at the edge of the left myocardium. Return the segment IDs of the inner, middle and outer segments. 
        """
        import numpy as np
        import scipy.ndimage

        # Export myocardium to myocardium label mapw
        myocardium_labelmap = self.export_segment_to_labelmap(segmentation_chambers_node, myocardium_segment_id, volume_node, "MyocardiumLabelMap")
        
        # Export left ventricle segment to ventricle label map
        ventricle_labelmap = self.export_segment_to_labelmap(segmentation_chambers_node, ventricle_segment_id, volume_node, "VentricleLabelMap")

        # Create inner layer labelmap as a duplicate of the myocardium to start off 
        inner_labelmap = self.export_segment_to_labelmap(segmentation_chambers_node, myocardium_segment_id, volume_node, "InnerLayerLabelMap")
        middle_labelmap = self.export_segment_to_labelmap(segmentation_chambers_node, myocardium_segment_id, volume_node, "MiddleLayerLabelMap")
        outer_labelmap = self.export_segment_to_labelmap(segmentation_chambers_node, myocardium_segment_id, volume_node, "OuterLayerLabelMap")

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
        inner_id = self.import_labelmap_to_segmentation(inner_labelmap, segmentation_chambers_node)
        middle_id = self.import_labelmap_to_segmentation(middle_labelmap, segmentation_chambers_node)
        outer_id = self.import_labelmap_to_segmentation(outer_labelmap, segmentation_chambers_node)

        # Remove temporary labelmaps
        for node in [inner_labelmap, middle_labelmap, outer_labelmap, myocardium_labelmap, ventricle_labelmap]:
            slicer.mrmlScene.RemoveNode(node)

        return inner_id, middle_id, outer_id # Return segment IDs
    


    # TODO: figure out where to put these 3 functions
    def export_segment_to_labelmap(self, segmentation_node: slicer.vtkMRMLSegmentationNode, segment_id: str, 
                                    volume_node: slicer.vtkMRMLScalarVolumeNode, labelmap_name: str) -> slicer.vtkMRMLLabelMapVolumeNode:
        """
        Export the segment to a labelmap using the segment id and labelmap name given, return a labelmap.
        """

        labelmap_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", labelmap_name)
        slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(segmentation_node, [segment_id], 
                                                                        labelmap_node, volume_node)
        return labelmap_node

    def import_labelmap_to_segmentation(self, labelmap_node: slicer.vtkMRMLLabelMapVolumeNode, 
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
    
    def set_segments_visibility(self, 
                                segmentation_node: slicer.vtkMRMLSegmentationNode, 
                                visible_segmentids: list[str], 
                                volume_node: slicer.vtkMRMLScalarVolumeNode) -> None:
        display_node = segmentation_node.GetDisplayNode()
        segmentation = segmentation_node.GetSegmentation()
        
        for segmentID in set(segmentation.GetSegmentIDs()) - set(visible_segmentids):
            display_node.SetSegmentVisibility(segmentID, False)
        for segmentID in visible_segmentids:
            display_node.SetSegmentVisibility(segmentID, True)

        # Show the segmentations in 3D, and center the 3D view
        segmentation_node.CreateClosedSurfaceRepresentation() 
        display_node.SetVisibility3D(True)
        slicer.app.layoutManager().threeDWidget(0).threeDView().resetFocalPoint()

        volume_node.GetDisplayNode().SetWindow(DISPLAY_WINDOW)
        volume_node.GetDisplayNode().SetLevel(DISPLAY_LEVEL)



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
