# Constants for cardiac segmentation editor effects

SEGMENTATION_QUALITY = "normal"
SEGMENTATION_CHAMBERS_TASK = "heartchambers_highres"
SEGMENTATION_EFFUSION_TASK = "pleural_pericard_effusion"
SEGMENTATION_ARTERY_TASK = "coronary_arteries"
SEGMENTATION_TISSUE_TASK = "tissue_types"

MIN_THRESHOLD_VALUE = -1024
MAX_THRESHOLD_VALUE = 3071
MIN_MYOCARDIUM_THRESHOLD_VALUE = -90 # TODO: change back to -100?
MAX_MYOCARDIUM_THRESHOLD_VALUE = 300
MIN_SCAR_THRESHOLD_VALUE = -1024
MAX_SCAR_THRESHOLD_VALUE = -50

INNER_MYOCARDIUM_LIMIT = 33
MIDDLE_MYOCARDIUM_LIMIT = 67

RIGHT_MYOCARDIUM_GROWTH = 3.0
LEFT_MYOCARDIUM_GROWTH = 4.0
# in main script, write if left_myocardium == 0 or < min value from resolution, 
# then skip the margin step, and adjust smoothing??


EDITABLE_ANYWHERE = 0
EDITABLE_OUTSIDE_ALL_SEGMENTS = 3