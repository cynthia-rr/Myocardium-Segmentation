# Constants for segmentation parameters and settings
from pathlib import Path

PATH_TO_NIFTI = Path.home() / "Downloads/datasets/Totalsegmentator_dataset_v201/s0738/ct.nii.gz"
PATH_TO_DICOM_FOLDER = Path.home() / "Downloads/datasets/CRA-03"
PATH_FOR_SAVE = Path.home() / "Documents/sjhc/extension-repo/python-script/segmentations"

SEGMENTATION_CHAMBERS_FILENAME = "chambers-segmentation.seg.nrrd"
SEGMENTATION_EFFUSION_FILENAME = "effusion-segmentation.seg.nrrd"

DISPLAY_WINDOW = 800
DISPLAY_LEVEL = 200

MIN_THRESHOLD_VALUE = -1024
MAX_THRESHOLD_VALUE = 3071
MIN_MYOCARDIUM_THRESHOLD_VALUE = -120
MAX_MYOCARDIUM_THRESHOLD_VALUE = 300
MIN_SCAR_THRESHOLD_VALUE = -200
MAX_SCAR_THRESHOLD_VALUE = -60

SEGMENTATION_QUALITY = "normal"
SEGMENTATION_CHAMBERS_TASK = "heartchambers_highres"
SEGMENTATION_EFFUSION_TASK = "pleural_pericard_effusion"
