# Constants for input, output, visuals
from pathlib import Path

PATH_TO_NIFTI = Path.home() / "Downloads/datasets/Totalsegmentator_dataset_v201/heart/s0338/ct.nii.gz"
PATH_TO_DICOM_FOLDER = Path.home() / "Downloads/datasets/CRA-03"
<<<<<<< HEAD
PATH_FOR_SAVE = Path.home() / "Documents/sjhc/saved-segmentations"
=======
PATH_FOR_SAVE = Path.home() / "Documents/sjhc/extension-repo/saved-segmentations"

SEGMENTATION_CHAMBERS_FILENAME = "chambers-segmentation.seg.nrrd"
SEGMENTATION_EFFUSION_FILENAME = "effusion-segmentation.seg.nrrd"
SEGMENTATION_ARTERY_FILENAME = "artery-segmentation.seg.nrrd"
SEGMENTATION_TISSUE_FILENAME = "tissue-segmentation.seg.nrrd"
>>>>>>> 5f56283 (moving the saved segmentations)

SEGMENTATION_CHAMBERS_FILENAME = "chambers-segmentation3.seg.nrrd"
SEGMENTATION_EFFUSION_FILENAME = "effusion-segmentation3.seg.nrrd"
SEGMENTATION_ARTERY_FILENAME = "artery-segmentation3.seg.nrrd"
SEGMENTATION_TISSUE_FILENAME = "tissue-segmentation3.seg.nrrd"

DISPLAY_WINDOW = 800
DISPLAY_LEVEL = 200

COLOUR_RED = (0.5, 0.0, 0.0)
COLOUR_PINK = (1.0, 0.8, 1.0)
COLOUR_DARK_ORANGE = (1.0, 0.65, 0.0)
COLOUR_ORANGE = (1.0, 0.7, 0.0)
COLOUR_LIGHT_ORANGE = (1.0, 0.85, 0.0)
COLOUR_YELLOW = (1.00, 1.00, 0.00)
COLOUR_GREEN = (0.60, 0.80, 0.60)
COLOUR_BLUE = (0.0, 0.50, 1.0)
COLOUR_LIGHT_BLUE = (0.70, 0.80, 1.00)
COLOUR_PURPLE = (0.90, 0.55, 0.90)