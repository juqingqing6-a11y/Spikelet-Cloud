# Rice Grain Phenotyping Analysis System

## 前端开发交接（2026-11-03）

测试环境的完整前端快照现位于 [`frontend/`](frontend/README.md)：包含 Django HTML 模板、JavaScript、CSS、字体、界面图片和使用手册，以及页面入口、接口约定和文件哈希清单。前端优化人员请从 [交接说明](frontend/README.md) 开始；这些页面需要配合现有 Django 后端联调。本仓库原有模型代码及研究说明保留在下方。

Jie Zhou<sup>1*</sup>, Min Zhang<sup>1</sup>, Ji Zhou<sup>1,2*</sup>

<sup>1</sup>State Key Laboratory of Crop Genetics & Germplasm Enhancement, College of Agriculture, Academy for Advanced Interdisciplinary Studies, Jiangsu Collaborative Innovation Center for Modern Crop Production Co-sponsored by Province and Ministry, Nanjing Agricultural University, Nanjing 210095, China;

<sup>2</sup>Cambridge Crop Research, National Institute of Agricultural Botany, Cambridge CB3 0LE, UK;

<sup>*</sup>Correspondence for the source code and cloud software: jiezhou@njau.edu.cn; Ji.Zhou@NJAU.edu.cn or JZhou@cemps.ac.cn

## Please cite the research article
1) If you wish to cite the RGPAS platform and its related machine learning or deep learning models, please refer to our manuscript entitled "From phenome to genome: A cloud-based AI platform for integrative rice grain analysis and genetic mapping to empower grain-focused crop improvement" (doi: 10.1016/j.aiia.2026.07.013). 
2) If you wish to use the WRGD set, please access the whole set at https://www.ebi.ac.uk/biostudies/studies/S-BSST2194.
3) Please be aware we accept no responsibility for any subsequent modifications, adaptations, or derivative versions made by third parties. We are also not responsible for user-uploaded datasets or models in the RGPAS platform, including their content, quality, accuracy, or use. All uploaded datasets will be removed from the server on a daily basis.

## Install Python, Anaconda and Libraries
If you wish to use the RGPAS platform from source code, you will need to set up Python on your operating system. 

1. Install Python releases:
   
   •	Read the beginner’s guide to Python if you are new to the language: 
   https://wiki.python.org/moin/BeginnersGuide
   
   •	For Windows users, Python 3 release can be downloaded via: 
   https://www.python.org/downloads/windows/
   
   •	For Mac OS users, Python 3 release can be downloaded via: 
   https://www.python.org/downloads/mac-osx/
   
   •	AirMeasurer only supports Python 3 onwards

2. Install Anaconda Python distribution:
   
   •	Read the install instruction using the URL: https://docs.continuum.io/anaconda/install
   
   •	For Windows users, a detailed step-by-step installation guide can be found via: 
   https://docs.continuum.io/anaconda/install/windows 
   
   •	For Mac OS users, a detailed step-by-step installation guide can be found via:
   https://docs.continuum.io/anaconda/install/mac-os.html
   
   •	An Anaconda Graphical installer can be found via: 
   https://www.continuum.io/downloads

   •	We recommend users install the latest Anaconda Python distribution

3. Create a environment for the deep learning to prevent conflicts.

```bash
# 1) Create and activate environment
conda create -n your_env_name python=3.9 -y
conda activate your_env_name

# 2) Install PyTorch (CUDA or CPU)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# 3) Common dependencies
pip install opencv-python scikit-image scipy numpy matplotlib tqdm jupyter

```

Their is a `requirements.txt` file is provided under the code folder, install with:

```bash
pip install -r requirements.txt
```

---
## Using trained machine learning or deep learning models published 

To run panicle detection with "RGD-YOLO":

```bash
# 1) Activate environment
conda activate your_env_name

# 2) Enter RDG-YOLO directory
cd code/RDG-YOLO

# 3) Download the model of RDG-YOLO
Please through Releases to get the model for panicle detection

# 4) Start predict
python predict.py
```

To run whole grain identification with "EfficientNet-RG":

```bash
# 1) Activate environment
conda activate your_env_name

# 2) Enter EfficientNet-RG directory
cd code/EfficientNet-RG

# 3) Download the model of EfficientNet-RG
Please through Releases to get the model for panicle detection

# 4) Start Jupyter
jupyter notebook

```

## License
Source codes, notebooks, and trained learning model are shared under **the _MIT_ license**. For any commerical use, please contact the corresponding author listed above. 

