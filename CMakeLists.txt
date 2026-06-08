cmake_minimum_required(VERSION 3.20.6...3.22.6 FATAL_ERROR)

project(MyocardiumSegmentation)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/MyocardiumSegmentation")
set(EXTENSION_CONTRIBUTORS "Cynthia Rong (Lawson Research)")
set(EXTENSION_DESCRIPTION "Segmenting the left and right myocardium, as well as the scar tissue.")
set(EXTENSION_ICONURL "https://www.example.com/Slicer/Extensions/MyocardiumSegmentation.png")
set(EXTENSION_SCREENSHOTURLS "https://www.example.com/Slicer/Extensions/MyocardiumSegmentation/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(MyocardiumSegmentation)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
