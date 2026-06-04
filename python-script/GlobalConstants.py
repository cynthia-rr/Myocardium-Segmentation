# Constants for segmentation parameters and settings
from pathlib import Path

PATH_TO_NIFTI = Path.home() / "Downloads/datasets/Totalsegmentator_dataset_v201/s0738/ct.nii.gz"
PATH_TO_DICOM_FOLDER = Path.home() / "Downloads/datasets/CCTA"
PATH_FOR_SAVE = Path.home() / "Documents/sjhc/extension-repo/python-script/segmentations"

SEGMENTATION_CHAMBERS_FILENAME = "chambers-segmentation2.seg.nrrd"
SEGMENTATION_EFFUSION_FILENAME = "effusion-segmentation2.seg.nrrd"
SEGMENTATION_ARTERY_FILENAME = "artery-segmentation2.seg.nrrd"
SEGMENTATION_TISSUE_FILENAME = "tissue-segmentation2.seg.nrrd"

SEGMENTATION_QUALITY = "normal"
SEGMENTATION_CHAMBERS_TASK = "heartchambers_highres"
SEGMENTATION_EFFUSION_TASK = "pleural_pericard_effusion"
SEGMENTATION_ARTERY_TASK = "coronary_arteries"
SEGMENTATION_TISSUE_TASK = "tissue_types"

DISPLAY_WINDOW = 800
DISPLAY_LEVEL = 200

MIN_THRESHOLD_VALUE = -1024
MAX_THRESHOLD_VALUE = 3071
MIN_MYOCARDIUM_THRESHOLD_VALUE = -90 # TODO: change back to -100?
MAX_MYOCARDIUM_THRESHOLD_VALUE = 300
MIN_SCAR_THRESHOLD_VALUE = -1024
MAX_SCAR_THRESHOLD_VALUE = -50

INNER_MYOCARDIUM_LIMIT = 33
MIDDLE_MYOCARDIUM_LIMIT = 67

RIGHT_MYOCARDIUM_DEPTH = 1.0
LEFT_MYOCARDIUM_DEPTH = 1.0 
# in main script, write if left_myocardium == 0 or < min value from resolution, 
# then skip the margin step, and adjust smoothing??

COLOUR_PINK = (0.50, 0.0, 0.0)
COLOUR_YELLOW = (1.00, 1.00, 0.00)
COLOUR_GREEN = (0.60, 0.80, 0.60)
COLOUR_LIGHT_BLUE = (0.70, 0.80, 1.00)
COLOUR_BLUE = (0.0, 0.50, 1.0)
COLOUR_PURPLE = (0.90, 0.55, 0.90)



EDITABLE_ANYWHERE = 0
EDITABLE_OUTSIDE_ALL_SEGMENTS = 3