cmake_minimum_required(VERSION 3.20.6...3.22.6 FATAL_ERROR)

project(MyocardiumScarSegmentation)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/MyocardiumScarSegmentation")
set(EXTENSION_CONTRIBUTORS "Cynthia Rong (Lawson Research)")
set(EXTENSION_DESCRIPTION "Segment the left and right myocardium, divide the left myocardium into three layers, and segment potential scar areas. ")
set(EXTENSION_ICONURL "https://www.example.com/Slicer/Extensions/MyocardiumScarSegmentation.png")
set(EXTENSION_SCREENSHOTURLS "https://www.example.com/Slicer/Extensions/MyocardiumScarSegmentation/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(MyocardiumSegmentationModule)
add_subdirectory(ScarSegmentation)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
