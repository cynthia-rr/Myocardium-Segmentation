# main.py

from InitialSegmentation import run_initial
from MyocardiumSegmentation import run_myocardium   

run_initial()
run_myocardium()

slicer.util.exit()
