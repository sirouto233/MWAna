<p align="center">
  <img src="./assets/1_bg.png" alt="MWAna logo" width="180">
</p>

<h1 align="center">MWAna</h1>

<p align="center">
  <strong>Automated Image Analysis tool for Microwell-Based dELISA</strong>
  <br>
  用于微坑法数字酶联免疫吸附测定（digital ELISA, dELISA）成像数据的自动化分析工具
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&amp;logo=python&amp;logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/PyTorch-2.7.1-EE4C2C?style=flat-square&amp;logo=pytorch&amp;logoColor=white" alt="PyTorch 2.7.1">
  <img src="https://img.shields.io/badge/torchvision-0.22.1-EE4C2C?style=flat-square" alt="torchvision 0.22.1">
  <img src="https://img.shields.io/badge/timm-1.0.24-5C5C9E?style=flat-square" alt="timm 1.0.24">
  <img src="https://img.shields.io/badge/OpenCV-4.13.0-5C3EE8?style=flat-square&amp;logo=opencv&amp;logoColor=white" alt="OpenCV 4.13.0">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Windows-11-0078D4?style=flat-square" alt="Windows 11">
  <img src="https://img.shields.io/badge/CUDA-11.8-76B900?style=flat-square&amp;logo=nvidia&amp;logoColor=white" alt="CUDA 11.8">
  <img src="https://img.shields.io/badge/Model-Swin--Tiny-7B2CBF?style=flat-square" alt="Model: Swin-Tiny">
  <a href="./LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-22A06B?style=flat-square" alt="MIT License">
  </a>
  <a href="https://github.com/sirouto233/MWAna/releases/latest">
  <img src="https://img.shields.io/github/v/release/sirouto233/MWAna?style=flat-square&amp;label=Release&amp;color=7B2CBF&amp;logo=github&amp;logoColor=white" alt="Latest Release">
  </a>
</p>

<p align="center">
  <a href="./README.md"><strong>English</strong></a>
  &nbsp; | &nbsp;
  <strong>简体中文</strong>
</p>

<p align="center">
  <a href="https://github.com/sirouto233/MWAna/releases/latest">⬇️ 下载发布版</a>
  &nbsp; · &nbsp;
  <a href="./README_zh-CN.md#-背景">🔬 背景</a>
  &nbsp; · &nbsp;
  <a href="./README_zh-CN.md#-快速使用">🚀 快速使用</a>
  &nbsp; · &nbsp;
  <a href="./README_zh-CN.md#-安装与启动">⚙️ 安装与启动</a>
  &nbsp; · &nbsp;
  <a href="./README_zh-CN.md#-工作流程">📦 工作流程</a>
  &nbsp; · &nbsp;
  <a href="./README_zh-CN.md#-使用指南">📱 使用指南</a>
  &nbsp; · &nbsp;
  <a href="./README_zh-CN.md#-项目特色">🎆 项目特色</a>
  &nbsp; · &nbsp;
  <a href="./README_zh-CN.md#-开源协议与模型来源">⚖️ 开源协议与模型来源</a>
</p>

<hr style="height:3px;background-color:#66717C;border:none;"> 


## 🔬 背景

### ☝️ 简要介绍
用于dELISA检测微坑成像的自动化数据分析程序，包含**全流程图像分析与数据提取**（明场-荧光图像分类、光场平衡、微坑提取、含珠微坑识别、荧光信号统计），同时整合**模型训练模块**（图形化打标界面、分类模型训练）。

本工具基于 **_格物致和（iomics）Inspire DX 单分子免疫分析仪_** 产生的图像数据和文件结构开发，理论上可以适配任何微坑法dELISA平台的数据分析需求。

更详细的背景介绍请您参考：
[项目背景](./documents/BG_zh-CN.md) 。

<br/>

## 🚀 快速使用

*直接使用打包的.exe程序，便于快速部署应用。 程序可直接应用于**格物致和Inspire DX 单分子免疫分析仪**图像数据的分析。

*经过测试的运行环境：Windows 11, Python 3.12 (x64), NVIDIA RTX3070, CUDA 11.8。无独显设备也可以通过CPU模式使用（不推荐）。

_**1.获取发布版程序**_

前往 [Releases](https://github.com/sirouto233/MWAna/releases/latest)，
在 **Assets** 中下载最新版 `MWAna.zip`，解压后进入包含`_internal`文件夹，启动程序`launcher.exe`，预测模型`MWAna_3×3_SwinT-V6.pth`，以及预训练权重`swin_tiny_patch4_window7_224.pth`的根目录。
<br/>

_**2.启动图形界面**_

运行`launcher.exe`，选取运行语言后，进入图形界面。
<br/>

_**3.选择工作模式，源数据文件夹以及分类模型**_

参考图形界面提示进行对应选择，具体各模式对应数据形式和文件夹结构请参考后文 [使用指南](./README_zh-CN.md#-使用指南) 。

[例] **全流程执行**：勾选上方所有处理步骤，选择明场与荧光图共存的父级文件夹（可命名为`origin`），选择模型`MWAna_3×3_SwinT-V6.pth`，点击运行，即可执行全流程分析，得到结果数据。

分析结束后，会在`origin`同级文件夹下产生以下文件夹：明场原图`bri`、荧光原图`flu`、明场处理图`bri_sol`、提取的微坑区域mask`bri_mask`、预测的含珠微坑mask`bri_bead`，分析结果`Analysis_Results`。

分析结果文件夹中主要包含：各图对应的阈值分析统计图文件夹，以及分析结果统计文件`fluorescence_stats.xlsx`，其中包含各图的【总含珠微坑数】、【阳性微坑数】、【原AMB值】，以及经过自动离群值剔除的【AMB_filtered】与剔除的图像信息。

**一般情况下可以采用【AMB_filtered】值作为该组的分析结果。**

<img src="\information\interference_gui_zh.png" width="50%">
<br/>

_**4.模型训练相关**_

*若觉得含珠微坑预测效果准确率不高，可使用本地仪器采集的明场图像进行打标与训练。

(1) 在图形界面切换为`打标与训练`，选择一张**本地经过光场平衡后的微坑明场图像**(`bri_sol`内)，以及**对应的微坑区域mask图**(`bri_mask`内)，点击`启动打标工具`即可于图形交互界面进行打标。

<打标界面操作> 点击一个微坑，即会显示其产生的3×3微坑阵列判别单元，此时用键盘上的`1`与`0`键进行打标，`1`表示含珠微坑，`0`表示空坑。完成打标后，点击`q`键进行保存与退出。非追加模式下，会在明场图片同级文件夹创建`dataset`文件夹存放训练集以及标签文件`label.csv`。

(2) 打标完成后，**标签文件**选择生成数据集文件夹内的`label.csv`文件，**预训练权重**选择`swin_tiny_patch4_window7_224.pth`，确定保存模型路径、训练轮数与批次大小后，点击`开始训练`即可进行模型训练。

<p align="center">
<img src="\information\labeling_training_gui_zh.png" width="49%">
<img src="\information\labeling_gui.png" width="44.7%">
<p>

_**5.测试数据集**_

- 项目提供 `test/` 示例图片数据集，包含示例文件夹结构，以及由 **Inspire DX** 采集的明场和荧光图像数据。您可通过该数据集熟悉目录组织方式，并测试自动批处理与打标程序效果。请前往 [Releases](https://github.com/sirouto233/MWAna/releases) 下载。
- 项目提供 `train_set/` 示例训练集，包含示例训练集结构，以及由打标工具产生的图片元素和label.csv文件。您可通过该数据集熟悉训练集目录结构，并测试训练效果。请前往 [Releases](https://github.com/sirouto233/MWAna/releases) 下载。

<br/>

## ⚙ 安装与启动

*推荐使用代码包，便于进行各模块参数调整，兼容更多图像数据，以及改进项目与集成设计。

经过测试的运行环境：Windows 11, Python 3.12 (x64), NVIDIA RTX3070, CUDA 11.8。

_**1.通过Git获取本项目**_
```powershell
git clone https://github.com/sirouto233/MWAna.git
cd MWAna
```
**_2.推荐在虚拟环境中运行项目，在项目文件夹创建环境：_**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```
**_3.默认使用NVIDIA GPU进行推理，使用 CUDA 11.8 版 PyTorch：_**

```powershell
python -m pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cu118
```

<若使用 CPU，将上面的命令替换为：>

```powershell
python -m pip install torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cpu
```

**_4.安装依赖：_**

```powershell
python -m pip install -r requirements-runtime.txt
python -m pip check
```
- `requirements.txt`：完整的 包含CUDA 11.8 的依赖清单。
- `requirements-runtime.txt`：配合上述分步安装使用的运行依赖。
- `requirements-build.txt`：可选的 PyInstaller 打包依赖。

**_5.项目启动：_**

```powershell
python launcher.py
```
启动后选择运行语言。也可以直接运行 `main_gui_zh.py` 或 `main_gui_en.py`进入GUI界面。


<br/>

## 📦 工作流程
### 🚨 功能介绍
**MWAna** 基于**_格物致和（iomics）Inspire DX 单分子免疫分析仪_** 产生的图像数据和文件结构开发。项目围绕微坑法dELISA的图像分析需求，将**图像分类**、**明场光场平衡**、**微坑识别**、磁珠二分类和荧光信号统计整合为自动化批处理流程。软件提供中英文图形界面，并包含训练集打标与模型训练工具，支持从样本标注、模型训练到批量数据分析的完整使用过程。

###  📜 分析流程与功能实现
| 分析流程      | 实现效果  | 对应代码                    | 关键设计                                          |
|-----------|-------|-------------------------|-----------------------------------------------|
| 1. 图像整理 | 按文件名区分明场和荧光，<br/>保存进对应子文件夹中 | `image_classifier`      | 基于文件名后缀的分类 |
| 2. 光场平衡 | 减轻图片光场不均匀的问题，<br/>增强含珠微坑与空坑的对比度 | `light_balance`         | 高斯平滑、Gamma校正、CLAHE增强 |
| 3. 微坑识别 | 利用明场图定位微坑位置，<br/>生成全部微坑区域的mask | `microwell_detection`   | Hough圆检测 |
| 4. 含珠微坑判定 | 将微坑mask作用于明场图像，<br/>提取出每个微坑的元素，<br/>进行含珠微坑识别，<br/>生成全部含珠微坑的mask | `bead_prediction`       | 3×3微坑领域拼接、**Swin-Transformer Tiny** 具有空间注意力的分类模型 |
| 5. 平均荧光统计 | 将含珠微坑mask作用于荧光图像，<br/>计算每个含珠微坑的平均荧光强度 | `fluorescence_analysis` | 逐元素灰度均值计算 |
| 6. AMB值计算 | 进行自动阈值划分，阳性信号判定，<br/>离群值剔除，给出综合AMB计算值<br/>（阳性微坑数/含珠微坑数） | `fluorescence_analysis` | KDE自动阈值划分、MAD离群值筛查 |

具体代码信息请您参考：[代码结构与模块说明](./documents/Code_Review_zh-CN.md) 。

<br/>

## 📱 使用指南

### _📑 图像数据名称与文件夹结构（重要）_

#### 1. 预测流程的规范数据格式及文件夹结构。

```
EXP（单次实验母文件夹）
├── origin (明场-荧光-混合文件夹)
│   └── 1 (原始数据文件夹)
│       ├── pic-01-0-1.tif (pic-01-0的明场图)
│       ├── pic-01-0-2.tif (pic-01-0的荧光图)
│       ├── pic-02-0-1.tif (pic-02-0的明场图)
│       ├── pic-02-0-2.tif (pic-02-0的荧光图)
│       └── ...
├── bri (明场图文件夹)
│   └── 1
│       ├── pic-01-0-1.tif (pic-01-0的明场图)
│       ├── pic-02-0-1.tif (pic-02-0的明场图)
│       └── ...
├── flu (荧光图文件夹)
│   └── 1
│       ├── pic-01-0-2.tif (pic-01-0的荧光图)
│       ├── pic-02-0-2.tif (pic-02-0的荧光图)
│       └── ...
├── bri_sol (预处理后明场图文件夹)
│   └── 1
│       ├── pic-01-0-1_sol.tif (pic-01-0的预处理后明场图)
│       ├── pic-02-0-1_sol.tif (pic-02-0的预处理后明场图)
│       └── ...
├── bri_mask (微坑mask文件夹)
│   └── 1
│       ├── pic-01-0-1_mask.tif (pic-01-0的微坑区域mask二值图)
│       ├── pic-02-0-1_mask.tif (pic-02-0的微坑区域mask二值图)
│       └── ...
├── bri_bead (预测的含珠微坑mask文件夹)
│   └── 1
│       ├── pic-01-0-1_bead.tif (pic-01-0的含珠微坑区域mask二值图)
│       ├── pic-02-0-1_bead.tif (pic-02-0的含珠微坑区域mask二值图)
│       └── ...
└── Analysis_Results (分析结果文件夹)
    ├── 1
    │   ├── scatter_pic-01-0-2.tif (pic-01-0的平均荧光散点图与阈值划分)
    │   ├── scatter_pic-02-0-2.tif (pic-02-0的平均荧光散点图与阈值划分)
    │   └── ...
    └── fluorescence_stats.xlsx（主要分析结果统计表）
```
- 需保持`origin`、`bri`等主要文件夹下具有一个子文件夹结构，因为**包含图像数据的子文件夹的名称**（如`1`）是分析结果中该组数据的名称标签。
- 不同起点开始的自动处理流程会向后生成全部图像文件内容和文件夹结构。

#### 2. 训练流程的规范数据格式及文件夹结构。

```
dataset（训练集文件夹）
├── label.csv（自动生成的标签信息表）
├── （以下为训练集元素示例，图片后缀信息均为打标程序自动生成）
├── pic-01-0-1_sol_comp112_bead_3x3 (pic-01-0-1_sol来源的，112位置的3×3微坑阵列元素)
├── pic-02-0-1_sol_comp5154_empty_3x3 (pic-01-0-1_sol来源的，5154位置的3×3微坑阵列元素)
└── ...
```
- 一般情况下均由打标工具自动生成

### _🏃 GUI使用_

#### _批量分析_

1. 选择待处理文件夹，勾选需要运行的步骤：
     + 勾选图像整理即启用全流程模式，直接选择`origin`即可
     + 如果已经分类，直接选择 `bri` 和 `flu`
     + 使用经过光场平衡预处理的图像，选择 `bri_sol` 和 `flu`
     + 已有微坑区域mask文件夹`bri_mask`，可跳过mask识别，但保持选择 `bri_sol` 和 `flu`
     + 已有含珠微坑mask文件夹`bri_bead`，选择`bri_bead` 和 `flu`
2. 选择AI预测模型文件。
3. 等待自动处理，在日志区查看进度、每张图的含珠微坑数和耗时。
5. 在输出文件夹查看 mask、散点图和 AMB 分析报告。

<img src="\information\interference_gui_zh.png" width="60%">
<br/>

跳过某一步时，需要保留该步骤之前生成的结果。`bri_sol`、`bri_mask` 和 `bri_bead` 与 `bri` 放在同一层。

重新运行会覆盖同名输出。建议将不同实验分别放在独立目录中。

#### _打标与训练_

1. 在打标页面选择一张 `bri_sol` 中的明场图，以及 `bri_mask` 中对应的 mask。点击 `启动打标工具`后，进入交互式GUI。
2. 左键点击单个微坑，即可其查看 3×3 邻域，按 **0** 标为空坑、按 **1** 标为含珠坑，按 **q** 退出当前预览；在主窗口按 **q** 结束并保存。图块和标签 CSV 默认保存到图像旁的 `dataset` 目录，也可以选择已有 CSV 继续添加。
3. 在训练页面选择标签 CSV、预训练权重及输出模型路径，设置轮数和 batch size 后开始训练。默认使用 80% 数据训练、20% 验证，优化器为 AdamW，学习率为 `1e-4`，损失函数为交叉熵；默认训练 30 轮、batch size 为 16。训练日志显示损失和验证准确率，模型按现有的准确率或损失改善规则保存，并在连续无改善时提前结束。

<p align="center">
<img src="\information\labeling_training_gui_zh.png" width="49%">
<img src="\information\labeling_gui.png" width="44.7%">
<p>

开始前确认 CSV 中的图像路径有效，删除重复或冲突标签，并创建模型输出文件夹。


#### _异常图像处理与离群值筛除_

残余水相弥散等情况可能使个别图像的阳性比例明显偏高。程序会在同组图像中，根据 AMB 的中位数和离散程度筛查高值，并去除有效微坑数异常低的结果，保证分析的准确性。

筛查使用中位数绝对偏差（MAD）描述同组 AMB 的波动，并结合各图的有效微坑数计算评分。默认至少有 **5 张有效图像**才进行筛查，评分超过 **3.5** 的高值图像从筛后汇总中排除；低值图像保留。报告同时给出：

- **原始 AMB**：使用全部有效图像计算。
- **筛除后 AMB**：去除高值离群图像后重新计算。
- **剔除清单**：列出图像路径、原 AMB、评分和原因，便于回看原图。

筛查只影响汇总时纳入哪些图像，不会删除原图，也不会修改单张图的荧光阈值。所以**不同样本或浓度请分开放，避免被当作同一组比较**。

筛查时剔除的图像会单独列出，方便后续进行检查。

### _🔎 其他注意事项_

- 理论上，本项目也适用于其他微坑法 dELISA 平台的图像数据分析，只要保证明场与荧光图像一一对应、同一微坑位于相同像素位置，并按上述内容整理文件夹结构即可。图像像素尺寸、分辨率或放大倍数改变时，则需要相应调整`microwell_detection`中的Hough 圆检测参数。


- 不同采集条件下的参数设置
  
   Hough 圆检测依赖微坑在图像中的实际大小和间距。更换仪器、物镜或采集分辨率后，应根据新的微坑外观调整搜索半径、中心间距及 mask 大小，使检测区域与微坑对应。优先检查 `microwell_detection.py` 中的参数：

| 参数 | 默认值 | 调整依据 |
| --- | --- | --- |
| `minRadius` / `maxRadius` | 6 / 10 | 微坑在图像中的像素半径 |
| `minDist` | 20 | 相邻微坑中心的像素距离 |
| `param1` / `param2` | 30 / 14 | 检测灵敏度、对比度和噪声 |
| mask 半径 | 8 | 希望保留的微坑区域 |

- 如果荧光配对数量少于预期，检查文件后缀、相对子目录和对应的 `_bead.tif` 是否齐全；如果微坑漏检，先检查 Hough 参数和生成的 mask。


- 项目提供 `test/` 示例图片数据集，包含示例文件夹结构，以及由 **Inspire DX** 采集的明场和荧光图像数据。您可通过该数据集熟悉目录组织方式，并测试自动批处理与打标程序效果。请前往 [Releases](https://github.com/sirouto233/MWAna/releases) 下载。
- 项目提供 `train_set/` 示例训练集，包含示例训练集结构，以及由打标工具产生的图片元素和label.csv文件。您可通过该数据集熟悉训练集目录结构，并测试训练效果。请前往 [Releases](https://github.com/sirouto233/MWAna/releases) 下载。

<br/>

## 🎆 项目特色

### 以 3×3 微坑矩阵作为判定单元

由于图像不同区域可能存在光场不均匀，不能仅依赖单个微坑的亮暗特征作为判定其中是否含有微珠的独立依据。因此，本项目采用 **3×3 微坑矩阵** 作为判定单元：待判断微坑在阵列中心，并将其周围 8 个位置的微坑图像组合到邻域中，共同用于判断中心微坑的含珠情况。

<img src="\information\on_off_well_const_zh.png" width="60%">

这一方法为中心微坑提供了同一区域内的亮度和形态参照。模型在识别磁珠造成的局部灰度与纹理变化时，可以同时比较周围微坑的外观，从而减轻区域光场不均对含珠判断的干扰。前序光场平衡负责改善整幅图像的照明分布，邻域比较则进一步提供局部参照。

训练集打标和批量预测均采用这种邻域图像表示。每个微坑阵列只对应一个标签，即中央微坑为空坑或含磁珠微坑；周围微坑参与提供比较信息，不需要预先知道它们的类别。程序按位置选择邻域图像并拼接，在图像边缘或邻坑缺失时使用附近区域或镜像进行补位。

### Swin-Transformer Tiny

本项目使用 **Swin-Transformer V1** 深度学习架构进行二分类模型训练，使用预训练权重为 `swin_tiny_patch4_window7_224`。选择这一模型的主要考虑是其空间自注意力机制：它能够学习不同图像位置之间的关系，联合利用中心微坑的细节与周围参考微坑的信息。

Swin-Tiny 先在局部窗口内提取特征，再通过移位窗口建立相邻区域之间的联系，并逐层形成更大范围的图像表示。对于 3×3 微坑矩阵，这种结构有助于将中心坑的局部外观与邻域比较信息结合起来，最终输出中心微坑属于“空坑”或“含珠坑”的概率。

输入微坑阵列元素统一缩放至 **224×224**，施加中央区域权重较高的固定径向亮度（暗角滤镜）加权，再复制为三通道并按 ImageNet 均值和标准差归一化。该亮度加权属于图像预处理，空间注意力则由模型在训练中学习。预测时，含珠类别概率大于 **0.5** 的微坑被保留为有效单元。

<br/>

## ⚖ 开源协议与模型来源

本项目以 **MIT 协议**开源，见 [LICENSE](LICENSE)。

本项目使用模型架构与预训练权重通过 [timm](https://github.com/huggingface/pytorch-image-models) 获取，

模型论文：Liu et al., [Swin Transformer: Hierarchical Vision Transformer using Shifted Windows](https://doi.org/10.1109/ICCV48922.2021.00986), 2021 IEEE/CVF International Conference on Computer Vision (ICCV), Montreal, QC, Canada, 2021, pp. 9992-10002, doi: 10.1109/ICCV48922.2021.00986.
