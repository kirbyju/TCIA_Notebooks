# TCIA_Notebooks
This is a home for notebooks which demonstrate how to access and work with TCIA datasets. 

# General Notebooks
*  [TCIA_Linux_Data_Retriever_App.ipynb](https://github.com/kirbyju/TCIA_Notebooks/blob/main/TCIA_Linux_Data_Retriever_App.ipynb) - A tutorial on how to install the [NBIA Data Retriever command-line Data Retriever utility on Linux](https://wiki.cancerimagingarchive.net/x/2QKPBQ) and use it to download TCIA datasets
*  [TCIA_REST_API_Queries.ipynb](https://github.com/kirbyju/TCIA_Notebooks/blob/main/TCIA_REST_API_Queries.ipynb) - A Python tutorial on how to use TCIA's REST API to ***query*** datasets
*  [TCIA_REST_API_Downloads.ipynb](https://github.com/kirbyju/TCIA_Notebooks/blob/main/TCIA_REST_API_Downloads.ipynb) - A Python tutorial on how to use TCIA's REST API to ***download*** datasets
*  [TCIA_Series_UID_Report.ipynb](https://github.com/kirbyju/TCIA_Notebooks/blob/main/TCIA_Series_UID_Report.ipynb) - Ingests a file containing TCIA Series Instance UIDs (e.g. TCIA manifest file or CSV of UIDs) and creates reports that summarize those scans

# AI and Visualization Notebooks
* [TCIA_Image_Visualization_with_itkWidgets.ipynb](https://github.com/kirbyju/TCIA_Notebooks/blob/main/TCIA_Image_Visualization_with_itkWidgets.ipynb) - Example of downloading TCIA DICOM images and visualizing them as interactive cinematic volume renderings or as 2D slices, using [itkWidgets](https://github.com/InsightSoftwareConsortium/itkwidgets).
* [TCIA_MONAI_Model_Zoo.ipynb](https://github.com/kirbyju/TCIA_Notebooks/blob/main/TCIA_MONAI_Model_Zoo.ipynb) - Demonstrates downloading data from TCIA, downloading a pre-trained model from [MONAI's Model Zoo](https://monai.io/model-zoo.html), applying the model to the data to segment anatomic structures in that data, and then visually comparing model results with expert segmentations.
* [TCIA_RTStruct_SEG_Visualization_with_itkWidgets.ipynb](https://github.com/kirbyju/TCIA_Notebooks/blob/main/TCIA_RTStruct_SEG_Visualization_with_itkWidgets.ipynb) - Tutorial of downloading expert annotations as DICOM SEG and RTSTRUCT objects, converting them to labelmaps for use in training and evaluating AI models, and visualizing them with their source images in 3D or as overlays on 2D slices.
* [TCIA_STL_Visualization_with_itkWidgets.ipynb](https://github.com/kirbyju/TCIA_Notebooks/blob/main/TCIA_STL_Visualization_with_itkWidgets.ipynb) - Shows how to download, convert, and visualize expert annotations and 3D printer models stored in STL format on TCIA for use in training and evaluating AI models.

# Collection-specific Notebooks
*  [ACNS0332.ipynb](https://github.com/kirbyju/TCIA_Notebooks/blob/main/ACNS0332/ACNS0332.ipynb) - A tutorial on accessing DICOM images, clinical data, and tumor annotations (3d segmentations & seed points) related to the ["Annotations for Chemotherapy and Radiation Therapy in Treating Young Patients With Newly Diagnosed, Previously Untreated, High-Risk Medulloblastoma/PNET (ACNS0332-Tumor-Annotations)"](https://doi.org/10.7937/D8A8-6252) dataset hosted on TCIA
*  [AREN0533.ipynb](https://github.com/kirbyju/TCIA_Notebooks/blob/main/AREN0533/AREN0533.ipynb) - A tutorial on accessing DICOM images, clinical data, and tumor annotations (3d segmentations & seed points) related to the ["Annotations for Combination Chemotherapy With or Without Radiation Therapy in Treating Young Patients With Newly Diagnosed Stage III or Stage IV Wilms Tumor (AREN0533-Tumor-Annotations)"](https://doi.org/10.7937/WFCC-DA41) dataset hosted on TCIA
