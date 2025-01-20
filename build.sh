# !/bin/bash


# Windows
docker run -v "$(pwd):/src/" cdrx/pyinstaller-windows "pyinstaller --onefile main.py -n libretranslateGUI"



# Linux
docker run -v "$(pwd):/src/" cdrx/pyinstaller-linux "pyinstaller --onefile main.py -n libretranslateGUI"






