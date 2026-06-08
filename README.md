# Myocardium and Scar Tissue Segmentation Script for 3D Slicer

# Description: 
Tool for segmenting the scars in the myocardium by segmenting the left and right myocardium, dividing the left myocardium into three layers: inner, middle and outer, and segmenting the scar tissue in each of the myocardium segments. 

Axial view of myocardium segmentations (in red, pink, green, blue) and scar tissue (in yellow and shades of orange).
3D model of the segmentations (red is the right myocardium, yellow is the scarring on the right myocardium).

<img width="433" height="423" alt="axial-view" src="https://github.com/user-attachments/assets/7ba5c750-ec64-4c07-aaf5-ef38031f631d" />
<img width="417" height="423" alt="3D-view" src="https://github.com/user-attachments/assets/f09d9133-0b87-4832-9e8f-fca610fe6aa6" />


# Installation Instructions:
This tool works on Ubuntu, Mac and Windows.

Install Dependencies: 
Python >= 3.10
PyTorch >= 2.0.0

Download and install 3D Slicer from http://download.slicer.org/

Then, open Slicer and navigate to the Extensions Manager. 

Install the following extensions:
* TotalSegmentator (in the Segmentation category)
* Sandbox (in the Examples category)

Restart Slicer after installing the extensions.

Fork this repository, then open in a code editor (Visual Studio Code).

# Example Use




# Citations
3D Slicer
Total Segmentator
nnUNet

# License



