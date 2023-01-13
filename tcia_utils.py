####### setup
import requests
import pandas as pd
import getpass
import json
import zipfile
import io
import os
from datetime import datetime
from datetime import timedelta
import matplotlib.pyplot as plt
import pydicom
import numpy as np 
from ipywidgets.widgets import * 
import ipywidgets as widgets

class StopExecution(Exception):
    def _render_traceback_(self):
        pass

token_exp_time = datetime.now()
nlst_token_exp_time = datetime.now()

####### setApiUrl()
# Called by other functions to select base URL
# Checks for valid security tokens where needed

def setApiUrl(endpoint, api_url):

    global searchEndpoints, advancedEndpoints

    # create valid endpoint lists 
    searchEndpoints = ["getCollectionValues", "getBodyPartValues", "getModalityValues",
                        "getPatient", "getPatientStudy", "getSeries", "getManufacturerValues",
                        "getSOPInstanceUIDs", "getSeriesMetaData", "getContentsByName",
                       "getImage", "getSingleImage"]
    advancedEndpoints = ["getModalityValuesAndCounts", "getBodyPartValuesAndCounts", 
                         "getDicomTags", "getSeriesMetadata2"]

    if not endpoint in searchEndpoints and not endpoint in advancedEndpoints:
        print("Endpoint not supported by tcia_utils: " + endpoint)
        print('Valid \"Search\" endpoints include', searchEndpoints)
        print('Valid \"Advanced\" endpoints include', advancedEndpoints)
        raise StopExecution 
    else:
        # set base URL for simple search and nlst simple search (no login required)
        if api_url == "":
            if endpoint in searchEndpoints:
                # Using "Search" API (no login required): https://wiki.cancerimagingarchive.net/x/fILTB
                base_url = "https://services.cancerimagingarchive.net/nbia-api/services/v1/"
            if endpoint in advancedEndpoints:
                # Using "Advanced" API (login required): https://wiki.cancerimagingarchive.net/x/YoATBg
                if datetime.now() < token_exp_time:
                    base_url = "https://services.cancerimagingarchive.net/nbia-api/services/"
                else:
                    print("Your security token for accessing the Advanced API is expired or does not exist. Create one using getToken().")
                    raise StopExecution       
        elif api_url == "nlst":
            if endpoint in searchEndpoints:
                # Using "Search" API with NLST server (no login required): https://wiki.cancerimagingarchive.net/x/fILTB
                base_url = "https://nlst.cancerimagingarchive.net/nbia-api/services/v1/"
            if endpoint in advancedEndpoints:
                # Using "Advanced" API docs (login required): https://wiki.cancerimagingarchive.net/x/YoATBg
                # Checking to see if a valid NLST authentication token exists
                if datetime.now() < nlst_token_exp_time:
                    base_url = "https://nlst.cancerimagingarchive.net/nbia-api/services/"
                else:
                    print("Your security token for accessing the NLST Advanced API is expired or does not exist. Create one using getToken(\"nlst\").")
                    raise StopExecution
        elif api_url == "restricted":
            if endpoint in searchEndpoints:
                # Using "Search with Authentication" API (login required): https://wiki.cancerimagingarchive.net/x/X4ATBg
                # Checking to see if a valid authentication token exists
                if datetime.now() < token_exp_time:
                    base_url = "https://services.cancerimagingarchive.net/nbia-api/services/v2/"
                else:
                    print("Your security token for accessing the Restricted API is expired or does not exist. Create one using getToken().")
                    raise StopExecution
            if endpoint in advancedEndpoints:
                print("\"" + api_url + "\" is an invalid api_url for the Advanced API endpoint: " + endpoint)
                print("Remove the api_url parameter unless you are querying the National Lung Screening Trial collection.")
                print("Use api_url = \"nlst\" to query the National Lung Screening Trial collection.")
                raise StopExecution
        else:
            if endpoint in searchEndpoints:
                print("\"" + api_url + "\" is an invalid api_url for Search API endpoint: " + endpoint)
                print("Remove the api_url parameter for regular public dataset searches.")
                print("Use api_url = \"nlst\" to access the National Lung Screening Trial collection.")
                print("Use api_url = \"restricted\" to access collections that require logging in.")
                raise StopExecution
            if endpoint in advancedEndpoints:
                print("\"" + api_url + "\" is an invalid api_url for Advanced API endpoint: " + endpoint)
                print("Remove the api_url parameter unless you are querying the National Lung Screening Trial collection.")
                print("Use api_url = \"nlst\" to query the National Lung Screening Trial collection.")
                raise StopExecution

        return base_url

####### getToken()
# Retrieves security token to access APIs that require authorization 
# Use getToken() for querying restricted collections with "Search API"
# Use getToken("nlst") for "Advanced API" queries of National Lung Screening Trial
# Sets expiration time for tokens (2 hours from creation)

def getToken(api_url = ""): 

    global token_exp_time, nlst_token_exp_time, api_call_headers, nlst_api_call_headers

    # token URLs
    token_url = "https://services.cancerimagingarchive.net/nbia-api/oauth/token?username="
    nlst_token_url = "https://nlst.cancerimagingarchive.net/nbia-api/oauth/token?username="

    # set user name and password
    print("Enter User: ")
    userName = input()
    passWord = getpass.getpass(prompt = 'Enter Password: ')

    # create API token
    if api_url == "nlst":
        # create nlst token
        url = nlst_token_url + userName + "&password=" + passWord + "&grant_type=password&client_id=nbiaRestAPIClient&client_secret=ItsBetweenUAndMe"
    else:
        # create regular token
        url = token_url + userName + "&password=" + passWord + "&grant_type=password&client_id=nbiaRestAPIClient&client_secret=ItsBetweenUAndMe"

    try:
        data = requests.get(url)
        data.raise_for_status()
        access_token = data.json()["access_token"]
        # track expiration status/time (2 hours from creation)
        current_time = datetime.now()
        if api_url == "nlst":
            nlst_token_exp_time = current_time + timedelta(hours=2)
            nlst_api_call_headers = {'Authorization': 'Bearer ' + access_token}
            print ('Success - Token saved to nlst_api_call_headers variable and expires at', nlst_token_exp_time)
        else:
            token_exp_time = current_time + timedelta(hours=2)
            api_call_headers = {'Authorization': 'Bearer ' + access_token}
            print ('Success - Token saved to api_call_headers variable and expires at', token_exp_time)
    # handle errors
    except requests.exceptions.HTTPError as errh:
        #print(errh)
        print("HTTP Error:", data.status_code, "-- Double check your user name and password.")
    except requests.exceptions.ConnectionError as errc:
        #print(errc)
        print("Connection Error:", data.status_code)
    except requests.exceptions.Timeout as errt:
        #print(errt)
        print("Timeout Error:", data.status_code)
    except requests.exceptions.RequestException as err:
        #print(err)
        print("Request Error:", data.status_code)
        
####### makeCredentialFile()
# Create a credential file to use with NBIA Data Retriever
# Documentation at https://wiki.cancerimagingarchive.net/x/2QKPBQ

def makeCredentialFile(): 

    # set user name and password
    print("Enter User: ")
    userName = input()
    passWord = getpass.getpass(prompt = 'Enter Password: ')

    # create credential file to use with NBIA Data Retriever  
    lines = ['userName=' + userName, 'passWord=' + passWord]
    with open('credentials.txt', 'w') as f:
        f.write('\n'.join(lines))
    print("Credential file for NBIA Data Retriever saved: credentials.txt")
    
####### queryData()
# Called by query functions that use requests.get()
# Provides error handling for requests.get()
# Formats output as JSON by default with options for "df" (dataframe) and "csv"

def queryData(endpoint, options, api_url, format):

    # get base URL
    base_url = setApiUrl(endpoint, api_url)
    # display full URL with endpoint & parameters
    url = base_url + endpoint
    print('Calling... ', url, 'with parameters', options)
    # get the data
    try:
        # include api_call_headers for restricted queries
        if api_url == "restricted" or (endpoint in advancedEndpoints and api_url == ""):
            data = requests.get(url, params = options, headers = api_call_headers)
        # include nlst_api_call_headers for nlst-advanced
        elif api_url == "nlst" and endpoint in advancedEndpoints:
            data = requests.get(url, params = options, headers = nlst_api_call_headers)
        else:
            data = requests.get(url, params = options)
        data.raise_for_status()

        # check for empty results and format output
        if data.text != "":
            data = data.json()
            # format the output (optional)
            if format == "df":
                df = pd.DataFrame(data)
                return df
            elif format == "csv":
                df = pd.DataFrame(data)
                df.to_csv(endpoint + ".csv")
                print("CSV saved to: " + endpoint + ".csv")
                return df
            else:
                return data
        else:
            print("No results found.")
            
    # handle errors
    except requests.exceptions.HTTPError as errh:
        print(errh)
    except requests.exceptions.ConnectionError as errc:
        print(errc)
    except requests.exceptions.Timeout as errt:
        print(errt)
    except requests.exceptions.RequestException as err:
        print(err)
    
####### getCollections function
# Gets a list of collections from a specified api_url

def getCollections(api_url = "",
                   format = ""):

    endpoint = "getCollectionValues"
    options = {}

    data = queryData(endpoint, options, api_url, format)
    return data
        
####### getBodyPart function
# Gets Body Part Examined metadata from a specified api_url
# Allows filtering by collection and modality

def getBodyPart(collection = "", 
                modality = "", 
                api_url = "",
                format = ""):
    
    endpoint = "getBodyPartValues"

    # create options dict to construct URL
    options = {}

    if collection:
        options['Collection'] = collection
    if modality:
        options['Modality'] = modality

    data = queryData(endpoint, options, api_url, format)
    return data

####### getModality function
# Gets Modalities metadata from a specified api_url
# Allows filtering by collection and bodyPart

def getModality(collection = "", 
                bodyPart = "", 
                api_url = "",
                format = ""):
    
    endpoint = "getModalityValues"

    # create options dict to construct URL
    options = {}

    if collection:
        options['Collection'] = collection
    if bodyPart:
        options['BodyPartExamined'] = bodyPart

    data = queryData(endpoint, options, api_url, format)
    return data

####### getPatient function
# Gets Patient metadata from a specified api_url
# Allows filtering by collection

def getPatient(collection = "", 
               api_url = "",
               format = ""):
    
    endpoint = "getPatient"
    
    # create options dict to construct URL
    options = {}

    if collection:
        options['Collection'] = collection

    data = queryData(endpoint, options, api_url, format)
    return data
        
####### getStudy function
# Gets Study (visit/timepoint) metadata from a specified api_url
# Requires filtering by collection
# Optional filters for patientId and studyUid

def getStudy(collection, 
             patientId = "",
             studyUid = "",
             api_url = "",
             format = ""):
    
    endpoint = "getPatientStudy"

    # create options dict to construct URL
    options = {}
    options['Collection'] = collection

    if patientId:
        options['PatientID'] = patientId
    if studyUid:
        options['StudyInstanceUID'] = studyUid

    data = queryData(endpoint, options, api_url, format)
    return data
        
####### getSeries function
# Gets Series (scan) metadata from a specified api_url
# Allows filtering by collection, patient ID, study UID,
#   series UID, modality, body part, manufacturer & model

def getSeries(collection = "",
              patientId = "", 
              studyUid = "", 
              seriesUid = "", 
              modality = "", 
              bodyPart = "", 
              manufacturer = "", 
              manufacturerModel = "",
              api_url = "",
              format = ""):

    endpoint = "getSeries"

    # create options dict to construct URL
    options = {}

    if collection:
        options['Collection'] = collection
    if patientId:
        options['PatientID'] = patientId
    if studyUid:
        options['StudyInstanceUID'] = studyUid
    if seriesUid:
        options['SeriesInstanceUID'] = seriesUid
    if modality:
        options['Modality'] = modality
    if bodyPart:
        options['BodyPartExamined'] = bodyPart
    if manufacturer:
        options['Manufacturer'] = manufacturer
    if manufacturerModel:
        options['ManufacturerModelName'] = manufacturerModel

    data = queryData(endpoint, options, api_url, format)
    return data
        
####### getSeriesMetadata function
# Gets Series (scan) metadata from a specified api_url
# Requires a specific Series Instance UID as input
# Output includes DOI and license details that are not in getSeries()

def getSeriesMetadata(seriesUid,
                      api_url = "",
                      format = ""):

    endpoint = "getSeriesMetaData"
    
    # create options dict to construct URL
    options = {}
    options['SeriesInstanceUID'] = seriesUid

    data = queryData(endpoint, options, api_url, format)
    return data
        
####### getSopInstanceUids function
# Gets SOP Instance UIDs from a specific series/scan
# Requires a specific Series Instance UID as input

def getSopInstanceUids(seriesUid,
                       api_url = "",
                       format = ""):
    
    endpoint = "getSOPInstanceUIDs"
    
    # create options dict to construct URL
    options = {}
    options['SeriesInstanceUID'] = seriesUid

    data = queryData(endpoint, options, api_url, format)
    return data

####### getManufacturer function
# Gets manufacturer metadata from a specified api_url
# Allows filtering by collection, body part & modality

def getManufacturer(collection = "", 
                    modality = "", 
                    bodyPart = "", 
                    api_url = "",
                    format = ""):

    endpoint = "getManufacturerValues"

    # create options dict to construct URL
    options = {}

    if collection:
        options['Collection'] = collection
    if modality:
        options['Modality'] = modality
    if bodyPart:
        options['BodyPartExamined'] = bodyPart

    data = queryData(endpoint, options, api_url, format)
    return data
        
####### getSharedCart function
# Gets "Shared Cart" (scan) metadata from a specified api_url
# Use https://nbia.cancerimagingarchive.net/nbia-search/ to create a cart
# Add data to your basket, then click "Share" > "Share my cart"
# The "name" parameter is part of the URL that generates.
# E.g https://nbia.cancerimagingarchive.net/nbia-search/?saved-cart=nbia-49121659384603347
#  has a cart "name" of "nbia-49121659384603347".

def getSharedCart(name,
                  api_url = "",
                  format = ""):

    endpoint = "getContentsByName"

    # create options dict to construct URL
    options = {}
    options['name'] = name

    data = queryData(endpoint, options, api_url, format)
    return data
        
####### downloadSeries function
# Ingests a set of seriesUids and downloads them
# By default, series_data expects JSON containing "SeriesInstanceUID" elements
# Set number = n to download the first n series if you don't want the full dataset
# Set hash = y if you'd like to retrieve MD5 hash values for each image
# Set input_type = "list" to pass a list of Series UIDs instead of JSON
# Set input_type = "uid" to download a single Series Instance UID
# Generates a dataframe of the series metadata
# Exports a CSV of the series metadata if csv_filename is specified

def downloadSeries(series_data, 
                   number = 0,
                   hash = "",
                   api_url = "", 
                   input_type = "", 
                   csv_filename=""):

    endpoint = "getImage"
    manifestDF=pd.DataFrame()
    seriesUID = ''
    success = 0
    failed = 0
    previous = 0

    # convert uid to list if uid input_type was specified
    if input_type == "uid":
        series_data = [series_data]
        input_type = "list"

    # get base URL
    base_url = setApiUrl(endpoint, api_url)

    # set sample size if you don't want to download the full set of results
    if number > 0:
        print("Downloading", number, "out of", len(series_data), "Series Instance UIDs (scans).")
    else:
        print("Downloading", len(series_data), "Series Instance UIDs (scans).")
    
    # set option to include md5 hashes
    if hash == "y":
        downloadOptions = "getImageWithMD5Hash?SeriesInstanceUID="
    else:
        downloadOptions = "getImage?NewFileNames=Yes&SeriesInstanceUID="

    # get the data
    try:
        for x in series_data:
            # specify whether input data is json or list
            if input_type == "list":
                seriesUID = x
            else:
                seriesUID = x['SeriesInstanceUID']
            # set path for downloads and check for previously downloaded data
            path = "tciaDownload/" + seriesUID
            if not os.path.isdir(path):
                data_url = base_url + downloadOptions + seriesUID
                metadata_url = base_url + "getSeriesMetaData?SeriesInstanceUID=" + seriesUID
                print("Downloading... " + data_url)
                if api_url == "restricted":
                    data = requests.get(data_url, headers = api_call_headers)
                    if data.status_code == 200:
                        metadata = requests.get(metadata_url, headers = api_call_headers).json()
                        file = zipfile.ZipFile(io.BytesIO(data.content))
                        # print(file.namelist())
                        file.extractall(path = "tciaDownload/" + "/" + seriesUID)
                        # write the series metadata to a dataframe            
                        manifestDF = pd.concat([manifestDF, pd.DataFrame(metadata)], ignore_index=True)
                        success += 1;
                        if number > 0:
                            if success == number:
                                break
                    else:
                        print("Error:", data.status_code, "Series failed:", seriesUID)
                        failed += 1;
                else:
                    data = requests.get(data_url)
                    if data.status_code == 200:
                        metadata = requests.get(metadata_url).json()
                        file = zipfile.ZipFile(io.BytesIO(data.content))
                        # print(file.namelist())
                        file.extractall(path = "tciaDownload/" + "/" + seriesUID)
                        # write the series metadata to a dataframe            
                        manifestDF = pd.concat([manifestDF, pd.DataFrame(metadata)], ignore_index=True)
                        success += 1;
                        if number > 0:
                            if success == number:
                                break
                    else:
                        print("Error:", data.status_code, "Series failed:", seriesUID)
                        failed += 1;
            else:
                print("Series", seriesUID, "already downloaded.")
                previous += 1;
        if number > 0:
            print("Downloaded", success, "out of", number, "requested series from a total of",
                  len(series_data), "Series Instance UIDs (scans).")
        else:
            print("Downloaded", success, "out of", len(series_data), "Series Instance UIDs (scans).")
        print(failed, "failed to download.")
        print(previous, "previously downloaded.")
        
        # display manifest dataframe and/or save manifest to CSV file
        if csv_filename != "":
            manifestDF.to_csv(csv_filename + '.csv')
            print("Manifest CSV saved as", csv_filename + '.csv')
            return manifestDF
        else:
            return manifestDF

    except requests.exceptions.HTTPError as errh:
        print(errh)
    except requests.exceptions.ConnectionError as errc:
        print(errc)
    except requests.exceptions.Timeout as errt:
        print(errt)
    except requests.exceptions.RequestException as err:
        print(err)
        
####### downloadImage function
# Ingests a seriesUids and SopInstanceUid and downloads the image

def downloadImage(seriesUID, 
                  sopUID, 
                  api_url = ""):

    endpoint = "getSingleImage"
    success = 0
    failed = 0
    previous = 0

    # get base URL
    base_url = setApiUrl(endpoint, api_url)

    try:
        path = "tciaDownload/" + seriesUID
        file = sopUID + ".dcm"
        if not os.path.isfile(path + "/" + file):
            data_url = base_url + 'getSingleImage?SeriesInstanceUID=' + seriesUID + '&SOPInstanceUID=' + sopUID
            print("Downloading... " + data_url)
            if api_url == "restricted":
                data = requests.get(data_url, headers = api_call_headers)
                if data.status_code == 200:  
                    if not os.path.exists(path):
                        os.mkdir(path)
                    with open(path + "/" + file, 'wb') as f:
                        f.write(data.content)
                    print("Saved to " + path + "/" + file)
                else:
                    print("Error:", data.status_code, ", double check your permissions and Series/SOP UIDs.")
                    print("Series UID:", seriesUID)
                    print("SOP UID: ", sopUID)
            else:
                data = requests.get(data_url)
                if data.status_code == 200:
                    if not os.path.exists(path):
                        os.mkdir(path)
                    with open(path + "/" + file, 'wb') as f:
                        f.write(data.content)
                    print("Saved to " + path + "/" + file)
                else:
                    print("Error:", data.status_code, ", double check your permissions and Series/SOP UIDs.")
                    print("Series UID:", seriesUID)
                    print("SOP UID: ", sopUID)
        else:
            print("Image", sopUID, "already downloaded to:\n" + path)

    except requests.exceptions.HTTPError as errh:
        print(errh)
    except requests.exceptions.ConnectionError as errc:
        print(errc)
    except requests.exceptions.Timeout as errt:
        print(errt)
    except requests.exceptions.RequestException as err:
        print(err)
        
##########################
##########################
# Advanced API Endpoints

####### getModalityCounts function (Advanced)
# Get counts of Modality metadata from Advanced API
# Allows filtering by collection and bodyPart

def getModalityCounts(collection = "",
                      bodyPart = "",
                      api_url = "",
                      format = ""):

    endpoint = "getModalityValuesAndCounts"
    
    # create options dict to construct URL
    options = {}

    if collection:
        options['Collection'] = collection
    if bodyPart:
        options['BodyPartExamined'] = bodyPart

    data = queryData(endpoint, options, api_url, format)
    return data
        
####### getBodyPartCounts function (Advanced)
# Get counts of Body Part metadata from Advanced API
# Allows filtering by collection and modality

def getBodyPartCounts(collection = "",
                      modality = "",
                      api_url = "",
                      format = ""):

    endpoint = "getBodyPartValuesAndCounts"
    
    # create options dict to construct URL
    options = {}

    if collection:
        options['Collection'] = collection
    if modality:
        options['Modality'] = modality

    data = queryData(endpoint, options, api_url, format)
    return data
        
####### getSeriesList function (Advanced)
# Get series metadata from Advanced API
# Allows submission of a list of UIDs
# Returns result as dataframe and CSV

def getSeriesList(list, api_url = "", csv_filename = ""):

    uids = ",".join(list)
    param = {'list': uids}
    endpoint = "getSeriesMetadata2"

    # set base_url 
    base_url = setApiUrl(endpoint, api_url)
    
    # full url
    url = base_url + endpoint
    print('Calling... ', url)

    # get data & handle any request.post() errors
    try:
        if api_url == "nlst":
            metadata = requests.post(url, headers = nlst_api_call_headers, data = param)
        else:
            metadata = requests.post(url, headers = api_call_headers, data = param)
        metadata.raise_for_status()

        # check for empty results and format output
        if metadata.text != "":
            df = pd.read_csv(io.StringIO(metadata.text), sep=',')
            if csv_filename != "":
                df.to_csv(csv_filename + '.csv')
                print("Report saved as", csv_filename + ".csv")
            else:
                df.to_csv('scan_metadata.csv')
                print("Report saved as scan_metadata.csv")
            return df
        else:
            print("No results found.")

    except requests.exceptions.HTTPError as errh:
        print(errh)
    except requests.exceptions.ConnectionError as errc:
        print(errc)
    except requests.exceptions.Timeout as errt:
        print(errt)
    except requests.exceptions.RequestException as err:
        print(err)
        
####### getDicomTags function (Advanced)
# Gets DICOM tag metadata for a given series UID (scan)

def getDicomTags(seriesUid,
                 api_url = "",
                 format = ""):

    endpoint = "getDicomTags"
    
    # create options dict to construct URL
    options = {}
    options['SeriesUID'] = seriesUid

    data = queryData(endpoint, options, api_url, format)
    return data
    
####### getDoiMetadata function
# Gets a list of Collections or Series associated with a DOI
# Requires a DOI URL and specification of Collection or Series UID output
# Result includes whether the data are 3rd party analyses or not
# Formats output as JSON by default with options for "df" (dataframe) and "csv"

def getDoiMetadata(doi, output, api_url = "", format = ""):

#DOI=https://doifor-CBIS-DDSM&CollectionOrSeries=collection
    param = {'DOI': doi,
             'CollectionOrSeries': output}
    
    endpoint = "getCollectionOrSeriesForDOI"

    # set base_url 
    base_url = setApiUrl(endpoint, api_url)
    
    # full url
    url = base_url + endpoint
    print('Calling... ', url)

    # get data & handle any request.post() errors
    try:
        if api_url == "nlst":
            metadata = requests.post(url, headers = nlst_api_call_headers, data = param)
        else:
            metadata = requests.post(url, headers = api_call_headers, data = param)
        metadata.raise_for_status()

        # check for empty results and format output
        if metadata.text != "[]":
            print(metadata.text)
            metadata = metadata.json()
            # format the output (optional)
            if format == "df":
                df = pd.DataFrame(metadata)
                return df
            elif format == "csv":
                df = pd.DataFrame(metadata)
                df.to_csv(endpoint + ".csv")
                print("CSV saved to: " + endpoint + ".csv")
                return df
            else:
                return metadata
        else:
            print("No results found.")

    except requests.exceptions.HTTPError as errh:
        print(errh)
    except requests.exceptions.ConnectionError as errc:
        print(errc)
    except requests.exceptions.Timeout as errt:
        print(errt)
    except requests.exceptions.RequestException as err:
        print(err)
    
##########################
##########################
# Miscellaneous

####### makeSeriesReport function
# Ingests JSON output from getSeries() or getSharedCart() and creates summary report

def makeSeriesReport(series_data):

    df = pd.DataFrame(series_data)

    # Calculate summary statistics for a given collection 

    # Scan Inventory
    print('Summary Statistics\n')
    print('Subjects: ', len(df['PatientID'].value_counts()), 'subjects')
    print('Studies: ', len(df['StudyInstanceUID'].value_counts()), 'studies')
    print('Series: ', len(df['SeriesInstanceUID'].value_counts()), 'series')
    print('Images: ', df['ImageCount'].sum(), 'images\n')

    # Summarize Collections
    print("Series Counts - Collections:")
    print(df['Collection'].value_counts(dropna=False))

    # Summarize modalities
    print("Series Counts - Modality:")
    print(df['Modality'].value_counts(dropna=False),'\n')

    # Summarize body parts
    print("Series Counts - Body Parts Examined:")
    print(df['BodyPartExamined'].value_counts(dropna=False),'\n')

    # Summarize manufacturers
    print("Series Counts - Device Manufacturers:")
    print(df['Manufacturer'].value_counts(dropna=False))

####### manifestToList function
# Ingests a TCIA manifest file and removes header
# Returns a list of series UIDs 

def manifestToList(manifest):

    # initialize variable
    data = []

    # open file and write lines to a list
    with open(manifest) as f:
        # verify this is a tcia manifest file
        first_line = f.readline()
        f.seek(0, 0)
        if "downloadServerUrl" in first_line:
            print("Removing headers from TCIA mainfest.")
            # write lines to list
            for line in f:
                data.append(line.rstrip())
            # remove the parameters from the list
            del data[:6]
            print("Returning", len(data), "Series Instance UIDs (scans) as a list.")
            return data
        else:
            print("This is not a TCIA manifest file, or you've already removed the header lines.")
            for line in f:
                data.append(line.rstrip())
            print("Returning", len(data), "Series Instance UIDs (scans) as a list.")
            return data

####### makeVizLinks function
# Ingests JSON output of getSeries() or getSharedCart()  
# Creates URLs to visualize them in a browser
# The links appear in the last 2 columns of the dataframe
# TCIA links display the individual series described in each row
# IDC links display the entire study (all scans from that time point)
# IDC links may not work if they haven't mirrored the series from TCIA yet
# This function only works with fully public datasets (no limited-access data)
# Optionally accepts a csv_filename parameter if you'd like to export a CSV file

def makeVizLinks(series_data, csv_filename=""):

    # set base urls for tcia/idc
    tciaVizUrl = "https://nbia.cancerimagingarchive.net/viewer/?series="
    idcVizUrl = "https://viewer.imaging.datacommons.cancer.gov/viewer/"
    
    # create dataframe and append base URLs to study/series UIDs
    df = pd.DataFrame(series_data)
    df['VisualizeSeriesOnTcia'] = tciaVizUrl + df['SeriesInstanceUID']
    df['VisualizeStudyOnIdc'] = idcVizUrl + df['StudyInstanceUID']

    # display manifest dataframe and/or save manifest to CSV file
    if csv_filename != "":
        df.to_csv(csv_filename + '.csv')
        print("Manifest CSV saved as", csv_filename + '.csv')
        return df
    else:
        return df

####### viewSeries function
# Visualize a Series (scan) you've downloaded in the notebook
# Requires EITHER a seriesUid or path parameter
# Leave seriesUid empty if you want to provide a custom path
# The function assumes "tciaDownload/<seriesUid>/" as path if seriesUid is provided
#   since this is how downloadSeries() saves things

def viewSeries(seriesUid = "", path = ""):

    # set path where downloadSeries() saves the data if seriesUid is provide
    if seriesUid != "":
        path = "tciaDownload/" + seriesUid

    # Verify series exists before visualizing
    if os.path.isdir(path):
        # load scan to pydicom
        slices = [pydicom.dcmread(path + '/' + s) for s in               
                  os.listdir(path) if s.endswith(".dcm")]

        # todo: figure out why this breaks in some cases or if it's even needed
        #slices = [s for s in slices if 'SliceLocation' in s]

        slices.sort(key = lambda x: int(x.InstanceNumber))

        try:
            modality = slices[0].Modality
        except IndexError:
            print("Cannot find a valid DICOM series at:")
            print(path)
            print("Try running downloadSeries(seriesUid, input_type = \"uid\") to download it first.")
            print("If the data isn't restricted, you can alternatively view it in your browser (without downloading) using this link:")
            print("https://nbia.cancerimagingarchive.net/viewer/?series=" + seriesUid)
            raise StopExecution

        try:
            slice_thickness = np.abs(slices[0].ImagePositionPatient[2] -   
                              slices[1].ImagePositionPatient[2])
        except:
            slice_thickness = np.abs(slices[0].SliceLocation - 
                                    slices[1].SliceLocation)
        for s in slices:
            s.SliceThickness = slice_thickness

        image = np.stack([s.pixel_array for s in slices])
        image = image.astype(np.int16)

        if modality == "CT":
            # Set outside-of-scan pixels to 0
            # The intercept is usually -1024, so air is approximately 0
            image[image == -2000] = 0
            
            # Convert to Hounsfield units (HU)
            intercept = slices[0].RescaleIntercept
            slope = slices[0].RescaleSlope
            
            if slope != 1:
                image = slope * image.astype(np.float64)
                image = image.astype(np.int16)
                
            image += np.int16(intercept)
        
        pixel_data = np.array(image, dtype=np.int16)

        # slide through dicom images using a slide bar 
        plt.figure(1)
        def dicom_animation(x):
            plt.imshow(pixel_data[x], cmap = plt.cm.gray)
            return x
        interact(dicom_animation, x=(0, len(pixel_data)-1))
    else:
        print("Cannot find a valid DICOM series at:")
        print(path)
        print("Try running downloadSeries(seriesUid, input_type = \"uid\") to download it first.")
        print("If the data isn't restricted, you can alternatively view it in your browser (without downloading) using this link:")
        print("https://nbia.cancerimagingarchive.net/viewer/?series=" + seriesUid)
