####### setup
import requests
import pandas as pd
import getpass
import json
import zipfile
import io
from datetime import datetime
from datetime import timedelta

class StopExecution(Exception):
    def _render_traceback_(self):
        pass

token_exp_time = datetime.now()
nlst_token_exp_time = datetime.now()

####### setApiUrl()
# Called by other functions to select base URL
# Checks for valid security tokens where needed

def setApiUrl(api_url = ""):
    global token_exp_time, nlst_token_exp_time

    if api_url == "":
        # Search API (no login required): https://wiki.cancerimagingarchive.net/x/fILTB
        base_url = "https://services.cancerimagingarchive.net/nbia-api/services/v1/"
        # print("Using open-access APIs from", base_url)
        return base_url
    elif api_url == "nlst":
        # Search API (no login required): https://wiki.cancerimagingarchive.net/x/fILTB
        base_url = "https://services.cancerimagingarchive.net/nlst-api/services/v1/"
        # print("Using open-access NLST APIs from", base_url)
        return base_url
    elif api_url == "restricted":
        # Restricted-access API (login required): https://wiki.cancerimagingarchive.net/x/X4ATBg
        if datetime.now() < token_exp_time:
            base_url = "https://services.cancerimagingarchive.net/nbia-api/services/v2/"
            return base_url
        else:
            print("Your security token for accessing the Restricted API is expired or does not exist. Create one using getToken().")
            raise StopExecution
    elif api_url == "advanced":
        # Advanced API (login required): https://wiki.cancerimagingarchive.net/x/YoATBg
        if datetime.now() < token_exp_time:
            base_url = "https://services.cancerimagingarchive.net/nbia-api/services/"
            return base_url
        else:
            print("Your security token for accessing the Advanced API is expired or does not exist. Create one using getToken().")
            raise StopExecution
        # print("Using Advanced APIs from", base_url)
    elif api_url == "nlst-advanced":
        # Advanced API docs (login required): https://wiki.cancerimagingarchive.net/x/YoATBg
        if datetime.now() < nlst_token_exp_time:
            base_url = "https://services.cancerimagingarchive.net/nlst-api/services/"
            return base_url
        else:
            print("Your security token for accessing the NLST Advanced API is expired or does not exist. Create one using getToken().")
            raise StopExecution
        # print("Using Advanced NLST APIs from", base_url)
    else:
        base_url = "https://services.cancerimagingarchive.net/nbia-api/services/v1/"
        print("Invalid api_url selection. Try 'nlst', 'restricted', 'advanced', and 'nlst-advanced' for special use cases.\nDefaulting to open-access APIs from", base_url)
        return base_url

####### getToken()
# Retrieves security token to access APIs that require authorization 
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
    try:
        if api_url == "nlst":
            # create nlst token
            url = nlst_token_url + userName + "&password=" + passWord + "&grant_type=password&client_id=nbiaRestAPIClient&client_secret=ItsBetweenUAndMe"
            access_token = requests.get(url).json()["access_token"]
            # track expiration status/time (2 hours from creation)
            current_time = datetime.now()
            nlst_token_exp_time = current_time + timedelta(hours=2)
            nlst_api_call_headers = {'Authorization': 'Bearer ' + access_token}
            print ('Success - Token saved to nlst_api_call_headers variable and expires at', nlst_token_exp_time)
        else:
            # create regular token
            url = token_url + userName + "&password=" + passWord + "&grant_type=password&client_id=nbiaRestAPIClient&client_secret=ItsBetweenUAndMe"
            access_token = requests.get(url).json()["access_token"]
            # track expiration status/time (2 hours from creation)
            current_time = datetime.now()
            token_exp_time = current_time + timedelta(hours=2)
            api_call_headers = {'Authorization': 'Bearer ' + access_token}
            print ('Success - Token saved to api_call_headers variable and expires at', token_exp_time)

    except requests.exceptions.HTTPError as errh:
        print(errh)
    except requests.exceptions.ConnectionError as errc:
        print(errc)
    except requests.exceptions.Timeout as errt:
        print(errt)
    except requests.exceptions.RequestException as err:
        print(err)
        
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
    
####### getCollections function
# Gets a list of collections from a specified api_url
# Returns result as JSON

def getCollections(api_url = ""):

    # read api_call_headers from global variable
    global api_call_headers

    try:
        # set base URL
        if api_url == "" or api_url == "nlst" or api_url == "restricted":
            base_url = setApiUrl(api_url)
        else:
            base_url = setApiUrl()
            print("Invalid api_url selection. Try 'nlst' or 'restricted' for special use cases. Defaulting to open-access API.")
        data_url = base_url + 'getCollectionValues'
        print('Calling... ', data_url)
        # pass headers if restricted
        if api_url == "restricted":
            data = requests.get(data_url, headers = api_call_headers)
        else:
            data = requests.get(data_url)
        # return data or error message
        if data.text != "":
            return data.json()
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
        
####### getBodyPart function
# Gets Body Part Examined metadata from a specified api_url
# Allows filtering by collection and modality
# Returns result as JSON

def getBodyPart(collection = "", 
              modality = "", 
              api_url = ""):

    # read api_call_headers from global variable
    global api_call_headers
    
    # create options dict to construct URL
    options = {}

    if collection:
        options['Collection'] = collection
    if modality:
        options['Modality'] = modality

    try:
        # set API URL function
        if api_url == "" or api_url == "nlst":
            base_url = setApiUrl(api_url)
            data_url = base_url + 'getBodyPartValues'
            print('Calling... ', data_url, 'with parameters', options)
            data = requests.get(data_url, params = options)
            if data.text != "":
                return data.json()
            else:
                print("No results found.")
        elif api_url == "restricted":
            base_url = setApiUrl(api_url)
            data_url = base_url + 'getBodyPartValues'
            print('Calling... ', data_url, 'with parameters', options)
            data = requests.get(data_url, headers = api_call_headers, params = options)
            if data.text != "":
                return data.json()
            else:
                print("No results found.")
        else:
            base_url = setApiUrl()
            print("Invalid api_url selection. Try 'nlst' or 'restricted' for special use cases.\nDefaulting to open-access APIs from", base_url)
            data_url = base_url + 'getBodyPartValues'
            print('Calling... ', data_url, 'with parameters', options)
            data = requests.get(data_url, params = options)
            if data.text != "":
                return data.json()
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

####### getModality function
# Gets Modalities metadata from a specified api_url
# Allows filtering by collection and bodyPart
# Returns result as JSON

def getModality(collection = "", 
              bodyPart = "", 
              api_url = ""):

    # read api_call_headers from global variable
    global api_call_headers
    
    # create options dict to construct URL
    options = {}

    if collection:
        options['Collection'] = collection
    if bodyPart:
        options['BodyPartExamined'] = bodyPart

    try:
        # set API URL function
        if api_url == "" or api_url == "nlst":
            base_url = setApiUrl(api_url)
            data_url = base_url + 'getModalityValues'
            print('Calling... ', data_url, 'with parameters', options)
            data = requests.get(data_url, params = options)
            if data.text != "":
                return data.json()
            else:
                print("No results found.")
        elif api_url == "restricted":
            base_url = setApiUrl(api_url)
            data_url = base_url + 'getModalityValues'
            print('Calling... ', data_url, 'with parameters', options)
            data = requests.get(data_url, headers = api_call_headers, params = options)
            if data.text != "":
                return data.json()
            else:
                print("No results found.")
        else:
            base_url = setApiUrl()
            print("Invalid api_url selection. Try 'nlst' or 'restricted' for special use cases.\nDefaulting to open-access APIs from", base_url)
            data_url = base_url + 'getModalityValues'
            print('Calling... ', data_url, 'with parameters', options)
            data = requests.get(data_url, params = options)
            if data.text != "":
                return data.json()
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

####### getPatient function
# Gets Patient metadata from a specified api_url
# Allows filtering by collection
# Returns result as JSON

def getPatient(collection = "", 
              api_url = ""):

    # read api_call_headers from global variable
    global api_call_headers
    
    # create options dict to construct URL
    options = {}

    if collection:
        options['Collection'] = collection

    try:
        # set API URL function
        if api_url == "" or api_url == "nlst":
            base_url = setApiUrl(api_url)
            data_url = base_url + 'getPatient'
            print('Calling... ', data_url, 'with parameters', options)
            data = requests.get(data_url, params = options)
            if data.text != "":
                return data.json()
            else:
                print("No results found.")
        elif api_url == "restricted":
            base_url = setApiUrl(api_url)
            data_url = base_url + 'getPatient'
            print('Calling... ', data_url, 'with parameters', options)
            data = requests.get(data_url, headers = api_call_headers, params = options)
            if data.text != "":
                return data.json()
            else:
                print("No results found.")
        else:
            base_url = setApiUrl()
            print("Invalid api_url selection. Try 'nlst' or 'restricted' for special use cases.\nDefaulting to open-access APIs from", base_url)
            data_url = base_url + 'getPatient'
            print('Calling... ', data_url, 'with parameters', options)
            data = requests.get(data_url, params = options)
            if data.text != "":
                return data.json()
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
        
####### getStudy function
# Gets Study (visit/timepoint) metadata from a specified api_url
# Allows filtering by collection
# Returns result as JSON

def getStudy(collection, 
             patientId = "",
             studyUid = "",
              api_url = ""):

    # read api_call_headers from global variable
    global api_call_headers
    
    # create options dict to construct URL
    options = {}

    if collection:
        options['Collection'] = collection
    if patientId:
        options['PatientID'] = patientId
    if studyUid:
        options['StudyInstanceUID'] = studyUid

    try:
        # set API URL function
        if api_url == "" or api_url == "nlst":
            base_url = setApiUrl(api_url)
            data_url = base_url + 'getPatientStudy'
            print('Calling... ', data_url, 'with parameters', options)
            data = requests.get(data_url, params = options)
            if data.text != "":
                return data.json()
            else:
                print("No results found.")
        elif api_url == "restricted":
            base_url = setApiUrl(api_url)
            data_url = base_url + 'getPatientStudy'
            print('Calling... ', data_url, 'with parameters', options)
            data = requests.get(data_url, headers = api_call_headers, params = options)
            if data.text != "":
                return data.json()
            else:
                print("No results found.")
        else:
            base_url = setApiUrl()
            print("Invalid api_url selection. Try 'nlst' or 'restricted' for special use cases.\nDefaulting to open-access APIs from", base_url)
            data_url = base_url + 'getPatientStudy'
            print('Calling... ', data_url, 'with parameters', options)
            data = requests.get(data_url, params = options)
            if data.text != "":
                return data.json()
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
        
####### getSeries function
# Gets Series (scan) metadata from a specified api_url
# Allows filtering by collection
# Returns result as JSON

def getSeries(collection, 
              patientId = "", 
              studyUid = "", 
              seriesUid = "", 
              modality = "", 
              bodyPart = "", 
              manufacturer = "", 
              manufacturerModel = "", 
              api_url = ""):

    # read api_call_headers from global variable
    global api_call_headers

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

    try:
        # set API URL function
        if api_url == "" or api_url == "nlst":
            base_url = setApiUrl(api_url)
            data_url = base_url + 'getSeries'
            print('Calling... ', data_url, 'with parameters', options)
            data = requests.get(data_url, params = options)
            if data.text != "":
                return data.json()
            else:
                print("No results found.")
        elif api_url == "restricted":
            base_url = setApiUrl(api_url)
            data_url = base_url + 'getSeries'
            print('Calling... ', data_url, 'with parameters', options)
            data = requests.get(data_url, headers = api_call_headers, params = options)
            if data.text != "":
                return data.json()
            else:
                print("No results found.")
        else:
            base_url = setApiUrl()
            print("Invalid api_url selection. Try 'nlst' or 'restricted' for special use cases.\nDefaulting to open-access APIs from", base_url)
            data_url = base_url + 'getSeries'
            print('Calling... ', data_url, 'with parameters', options)
            data = requests.get(data_url, params = options)
            if data.text != "":
                return data.json()
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
        
####### getSeriesMetadata function
# Gets Series (scan) metadata from a specified api_url
# Requires a specific Series Instance UID as input
# Output includes DOI and license details that are not in getSeries()
# Returns result as JSON

def getSeriesMetadata(seriesUid, api_url = ""):

    # read api_call_headers from global variable
    global api_call_headers

    try:
        # set API URL function
        if api_url == "" or api_url == "nlst":
            base_url = setApiUrl(api_url)
        elif api_url == "restricted":
            base_url = setApiUrl(api_url)
        else:
            base_url = setApiUrl()
            print("Invalid api_url selection. Try 'nlst' or 'restricted' for special use cases.\nDefaulting to open-access APIs from", base_url)
        data_url = base_url + 'getSeriesMetaData?SeriesInstanceUID=' + seriesUid
        print('Calling... ', data_url)
        if api_url == "restricted":
            data = requests.get(data_url, headers = api_call_headers)
        else:
            data = requests.get(data_url)
        if data.text != "":
            return data.json()
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
        
####### getSharedCart function
# Gets "Shared Cart" (scan) metadata from a specified api_url
# Allows filtering by collection
# Returns result as JSON

def getSharedCart(name, api_url = ""):

    # read api_call_headers from global variable
    global api_call_headers

    try:
        # set API URL function
        if api_url == "" or api_url == "nlst":
            base_url = setApiUrl(api_url)
            data_url = base_url + 'getContentsByName?name=' + name
            print('Calling... ', data_url)
            data = requests.get(data_url)
            if data.text != "":
                return data.json()
            else:
                print("No results found.")
        elif api_url == "restricted":
            base_url = setApiUrl(api_url)
            data_url = base_url + 'getContentsByName?name=' + name
            print('Calling... ', data_url)
            data = requests.get(data_url, headers = api_call_headers)
            if data.text != "":
                return data.json()
            else:
                print("No results found.")
        else:
            base_url = setApiUrl()
            print("Invalid api_url selection. Try 'nlst' or 'restricted' for special use cases.\nDefaulting to open-access APIs from", base_url)
            data_url = base_url + 'getContentsByName?name=' + name
            print('Calling... ', data_url)
            data = requests.get(data_url)
            if data.text != "":
                return data.json()
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
        
####### downloadSampleSeries function
# Ingests a set of seriesUids and downloads the first 3 series
# By default, series_data expects JSON containing "SeriesInstanceUID" elements
# Set input_type = "list" to pass a list of Series UIDs instead of JSON
# Generates a dataframe of the series metadata
# Exports a CSV of the series metadata if csv_filename is specified

def downloadSampleSeries(series_data, api_url = "", input_type = "", csv_filename=""):

    global api_call_headers
    manifestDF = pd.DataFrame()
    seriesUID = ''
    count = 0

    # set API URL function
    if api_url == "" or api_url == "nlst" or api_url == "restricted":
        base_url = setApiUrl(api_url)            
    else:
        base_url = setApiUrl()
        print("Invalid api_url selection. Try 'nlst' or 'restricted' for special use cases.\nDefaulting to open-access APIs from", base_url)

    print("Downloading first 3 out of", len(series_data), "Series Instance UIDs (scans).")

    try:
        for x in series_data:
            # specify whether input data is json or list
            if input_type == "list":
                seriesUID = x
            else:
                seriesUID = x['SeriesInstanceUID']
    
            data_url = base_url + 'getImage?NewFileNames=Yes&SeriesInstanceUID=' + seriesUID
            metadata_url = base_url + "getSeriesMetaData?SeriesInstanceUID=" + seriesUID
            print("Downloading... " + data_url)
            if api_url == "restricted":
                data = requests.get(data_url, headers = api_call_headers)
                metadata = requests.get(metadata_url, headers = api_call_headers).json()
            else:
                data = requests.get(data_url)
                metadata = requests.get(metadata_url).json()
            file = zipfile.ZipFile(BytesIO(data.content))
            # print(file.namelist())
            file.extractall(path = "tciaDownload/" + "/" + seriesUID)
            # write the series metadata to a dataframe            
            manifestDF = pd.concat([manifestDF, pd.DataFrame(metadata)], ignore_index=True)
            # Repeat n times for demo purposes
            count += 1;
            if count == 3:
                break
        print("Sample download complete.")

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
        
####### downloadSeries function
# Ingests a set of seriesUids and downloads them
# By default, series_data expects JSON containing "SeriesInstanceUID" elements
# Set input_type = "list" to pass a list of Series UIDs instead of JSON
# Generates a dataframe of the series metadata
# Exports a CSV of the series metadata if csv_filename is specified

def downloadSeries(series_data, api_url = "", input_type = "", csv_filename=""):

    global api_call_headers
    manifestDF=pd.DataFrame()
    seriesUID = ''

    # set API URL function
    if api_url == "" or api_url == "nlst" or api_url == "restricted":
        base_url = setApiUrl(api_url)            
    else:
        base_url = setApiUrl()
        print("Invalid api_url selection. Try 'nlst' or 'restricted' for special use cases.\nDefaulting to open-access APIs from", base_url)

    print("Downloading", len(series_data), "Series Instance UIDs (scans).")

    try:
        for x in series_data:
            # specify whether input data is json or list
            if input_type == "list":
                seriesUID = x
            else:
                seriesUID = x['SeriesInstanceUID']
    
            data_url = base_url + 'getImage?NewFileNames=Yes&SeriesInstanceUID=' + seriesUID
            metadata_url = base_url + "getSeriesMetaData?SeriesInstanceUID=" + seriesUID
            print("Downloading... " + data_url)
            if api_url == "restricted":
                data = requests.get(data_url, headers = api_call_headers)
                metadata = requests.get(metadata_url, headers = api_call_headers).json()
            else:
                data = requests.get(data_url)
                metadata = requests.get(metadata_url).json()
            file = zipfile.ZipFile(BytesIO(data.content))
            # print(file.namelist())
            file.extractall(path = "tciaDownload/" + "/" + seriesUID)
            # write the series metadata to a dataframe            
            manifestDF = pd.concat([manifestDF, pd.DataFrame(metadata)], ignore_index=True)
        print("Download Complete:", len(series_data), "Series Instance UIDs (scans).")
        
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
        
##########################
##########################
# Advanced API Endpoints

####### getModalityCounts function (Advanced)
# Get counts of Modality metadata from Advanced API
# Allows filtering by collection and bodyPart
# Returns result as JSON

def getModalityCounts(collection = "", 
              bodyPart = "",
              api_url = ""):

    # read api_call_headers from global variable
    global api_call_headers, nlst_api_call_headers
    
    # create options dict to construct URL
    options = {}

    if collection:
        options['Collection'] = collection
    if bodyPart:
        options['BodyPartExamined'] = bodyPart

    try:
        # set base URL
        if api_url == "advanced" or api_url == "":
            base_url = setApiUrl("advanced")
        elif api_url == "nlst-advanced" or api_url == "nlst":
            base_url = setApiUrl("nlst-advanced")
        else:
            print("Invalid api_url selection. Valid options are 'advanced' (or blank) and 'nlst-advanced' (or 'nlst'). Defaulting to 'advanced' API.")
            base_url = setApiUrl("advanced")
        data_url = base_url + 'getModalityValuesAndCounts'
        print('Calling... ', data_url, 'with parameters', options)
        if api_url == "nlst-advanced" or api_url == "nlst":
            data = requests.get(data_url, headers = nlst_api_call_headers, params = options)
        else:
            data = requests.get(data_url, headers = api_call_headers, params = options)
        if data.text != "[]":
            return data.json()
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
        
####### getBodyPartCounts function (Advanced)
# Get counts of Modality metadata from Advanced API
# Allows filtering by collection and modality
# Returns result as JSON

def getBodyPartCounts(collection = "", 
              modality = "",
              api_url = ""):

    # read api_call_headers from global variable
    global api_call_headers, nlst_api_call_headers
    
    # create options dict to construct URL
    options = {}

    if collection:
        options['Collection'] = collection
    if modality:
        options['Modality'] = modality

    try:
        # set base URL
        if api_url == "advanced" or api_url == "":
            base_url = setApiUrl("advanced")
        elif api_url == "nlst-advanced" or api_url == "nlst":
            base_url = setApiUrl("nlst-advanced")
        else:
            print("Invalid api_url selection. Valid options are 'advanced' (or blank) and 'nlst-advanced' (or 'nlst'). Defaulting to 'advanced' API.")
            base_url = setApiUrl("advanced")
        data_url = base_url + 'getBodyPartValuesAndCounts'
        print('Calling... ', data_url, 'with parameters', options)
        if api_url == "nlst-advanced" or api_url == "nlst":
            data = requests.get(data_url, headers = nlst_api_call_headers, params = options)
        else:
            data = requests.get(data_url, headers = api_call_headers, params = options)
        if data.text != "[]":
            return data.json()
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
        
####### getSeriesList function (Advanced)
# Get series metadata from Advanced API
# Allows submission of a list of UIDs
# Returns result as JSON

def getSeriesList(list, api_url = ""):
    
    # read api_call_headers from global variable
    global api_call_headers, nlst_api_call_headers

    uids = ",".join(list)
    param = {'list': uids}

    try:
        # set base_url 
        if api_url == "nlst":
            base_url = setApiUrl("nlst-advanced")
        else:
            base_url = setApiUrl("advanced")
        data_url = base_url + "getSeriesMetadata2"
        print('Calling... ', data_url)
        if api_url == "nlst":
            data = requests.get(data_url, headers = nlst_api_call_headers, data = param)
        else:
            metadata = requests.post(data_url, headers = api_call_headers, data = param)
        # save output
        df = pd.read_csv(io.StringIO(metadata.text), sep=',')
        df.to_csv('scan_metadata.csv')
        print("scan_metadata.csv report saved successfully")
        return df

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
# Ingests the output of getSeries() and creates summary report

def makeSeriesReport(getSeries_data):

    df = pd.DataFrame(getSeries_data)

    # Calculate summary statistics for a given collection 

    # Summarize patients
    print('Summary Statistics\n')
    print('Subjects: ', len(df['PatientID'].value_counts()), 'subjects')
    print('Subjects: ', len(df['StudyInstanceUID'].value_counts()), 'studies')
    print('Subjects: ', len(df['SeriesInstanceUID'].value_counts()), 'series')
    print('Images: ', df['ImageCount'].sum(), 'images\n')

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
            print("Ignoring headers from TCIA mainfest.")
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
