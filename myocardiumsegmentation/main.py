from constants import *
from io_utils import load_dicom_series, load_totalsegmentator_segmentations


def main():

    volume_node = load_dicom_series(PATH_TO_DICOM_FOLDER)
    segmentation_data = load_totalsegmentator_segmentations(PATH_FOR_SAVE, SEGMENTATION_CHAMBERS_FILENAME, 
                                                            SEGMENTATION_EFFUSION_FILENAME, SEGMENTATION_ARTERY_FILENAME, 
                                                            SEGMENTATION_TISSUE_FILENAME)
    segmentation_chambers_node = segmentation_data["chambers"]
    segmentation_effusion_node = segmentation_data["effusion"]
    segmentation_artery_node = segmentation_data["artery"]
    segmentation_tissue_node = segmentation_data["tissue"]

    ########################################################################
    
    segment_right_myocardium(segmentation_data)

    myocardium_layers = divide_myocardium(segmentation_data)

    segment_scar(segmentation_data, myocardium_layers)

    show_results(segmentation_data)