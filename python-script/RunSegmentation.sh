
#!/bin/bashh

/Applications/Imaging/Slicer.app/Contents/MacOS/Slicer \
--python-script InitialSegmentation.py

echo "Finished initial segmentation, now running myocardium segmentation script"
/Applications/Imaging/Slicer.app/Contents/MacOS/Slicer \
--python-script MyocardiumSegmentation.py
