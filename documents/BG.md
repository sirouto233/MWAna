## 🔬 Background

### 🏷️ **Digital ELISA (dELISA)**

Digital ELISA is an ultrasensitive protein detection technique. By partitioning the bulk signal-generating reaction mixture into hundreds of thousands to millions of small-volume compartments, it allows each compartment to produce a readable signal from an individual target molecule. The target molecule concentration can then be inferred by digitally counting positive signals. Digital ELISA can achieve detection limits in the fg/mL range, 100–1000 times lower than those of conventional immunoassays. This ultrahigh sensitivity extends detection to more low-abundance protein biomarkers, such as the neurological biomarker pTau, giving the technique considerable potential for clinical applications.

### 📌 **Microwell-Based dELISA and Its Data Format**

Microwell-based dELISA uses a physical microwell array chip for partitioning and encapsulation. Its excellent stability and reproducibility have made it the most commercially established form of dELISA.

After the immunoreaction, bead loading, oil sealing, and chromogenic reaction steps, the microwell array region of the chip is required to be imaged and analyzed. Since not every microwell is occupied by a bead, two types of information are generally needed:

**1. The valid microwell regions occupied by beads.** A **well occupied by a bead** is referred to below as a **bead-on well**, and an empty microwell as a **bead-off well**.

**2. The mean fluorescence intensity within each corresponding region.**

In a common configuration, where the beads are not separately labeled by fluorescent dye, these two types of information are extracted from **bright-field** and **fluorescent** images, respectively. The resulting raw data therefore consist of paired bright-field and fluorescent images of the microwell array, with one-to-one correspondence.

### 🥅 **Data Analysis Challenges and Solutions**

The main challenge in analyzing microwell-based dELISA data is **identifying bead-on wells in bright-field images**. The presence of a dark spot inside a microwell is the primary feature distinguishing a bead-on well from a bead-off well. However, automated scanning inevitably introduces **intensity differences between images**, while **uneven illumination** can also occur within the same image. **These issues have a greater impact at high bead loading rates**, making accurate classification and precise segmentation difficult with simple pattern recognition algorithms and classification models, such as ImageJ's Trainable Weka Segmentation plugin.

<img src="./information/on_off_well_const.png" width="60%" alt="Bead-on and bead-off microwells and neighborhood context">

To address these challenges, this study adopts the following strategies to build an accurate automated analysis workflow.

1. **Partition the image into standardized microwell units** for training and classification, reducing interference from regions between microwells during feature recognition. Each generated microwell mask also has the same area, enabling more accurate mean fluorescence intensity measurements for individual units.

2. **Use a 3×3 microwell array—the central target microwell and eight surrounding reference microwells—as the classification unit**, together with a model that incorporates spatial attention (Swin-Transformer). This allows the model to learn feature contrasts between well to be identified and their neighbors, reducing the influence of regional brightness differences caused by uneven illumination.
