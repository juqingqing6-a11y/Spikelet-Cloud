import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.append("Please fill in the directory path where the project is located on your PC.")  

from ultralytics import YOLO

analyse_path = "Please fill in the path you need to analyse"
project_path = "Please fill in the path where you want to save the outputs"
folder_name = "Please define the name of the output folder"


if __name__ == '__main__':
    model = YOLO('RGD-YOLO.pt')
    model.predict(source=analyse_path,
                    imgsz=640,
                    project=project_path,
                    name=folder_name,
                    save=True,
                    show_labels=False,
                    show_conf=False,
                    line_width=2,
                    save_crop=False,)