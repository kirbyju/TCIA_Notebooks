####### imports
import requests
import pandas as pd
import json
import getpass
import zipfile
from io import BytesIO

####### URLs

# Search APIs (no login required) - Documentation at https://wiki.cancerimagingarchive.net/x/fILTB
pub_search = "https://services.cancerimagingarchive.net/nbia-api/services/v1/"
nlst_search = "https://services.cancerimagingarchive.net/nlst-api/services/v1/"

# Search w/ Authentication API - Documentation at https://wiki.cancerimagingarchive.net/x/X4ATBg
auth_search = "https://services.cancerimagingarchive.net/nbia-api/services/v2/"

# Advanced API - Documentation at https://wiki.cancerimagingarchive.net/x/YoATBg
advanced = "https://services.cancerimagingarchive.net/nbia-api/services/"
nlst_adv = "https://services.cancerimagingarchive.net/nlst-api/services/"

# token URLs (covered in Authentication API and Advanced API docs)
token_url = "https://services.cancerimagingarchive.net/nbia-api/oauth/token?username="
nlst_token_url = "https://nlst.cancerimagingarchive.net/nbia-api/oauth/token?username="

####### get an API token to access restricted collections
def getToken(api_url = ""): 

    # set user name and password
    print("Enter User: ")
    userName = input()
    passWord = getpass.getpass(prompt = 'Enter Password: ')

    # create API token
    try:
        if api_url == "nlst":
            # create nlst token
            # Needed for Search w/ Authentication & Advanced APIs
            url = nlst_token_url + userName + "&password=" + passWord + "&grant_type=password&client_id=nbiaRestAPIClient&client_secret=ItsBetweenUAndMe"
            access_token = requests.get(url).json()["access_token"]
            print ('NLST API Token created successfully: ', access_token)
            return access_token
        else:
            # create regular token
            url = token_url + userName + "&password=" + passWord + "&grant_type=password&client_id=nbiaRestAPIClient&client_secret=ItsBetweenUAndMe"
            access_token = requests.get(url).json()["access_token"]
            print ('API Token created successfully: ', access_token)
            return access_token

    except requests.exceptions.HTTPError as errh:
        print(errh)
    except requests.exceptions.ConnectionError as errc:
        print(errc)
    except requests.exceptions.Timeout as errt:
        print(errt)
    except requests.exceptions.RequestException as err:
        print(err)
        
####### Create a credential file to use with NBIA Data Retriever - Documentation at https://wiki.cancerimagingarchive.net/x/2QKPBQ
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
    

####### Download scans from a list of seriesInstanceUIDs and create a manifest
# Optional: Save a CSV of the manifest if you specify a csv_filename

def downloadSampleSeries(series_data, api_url = "", csv_filename=""):  

    # set API URL
    if api_url == "nlst":
        base_url = "https://services.cancerimagingarchive.net/nlst-api/services/v1/"
        print("Downloading NLST data from", base_url)
    if api_url == "restricted":
        base_url = "https://services.cancerimagingarchive.net/nbia-api/services/v2/"
        print("Downloading restricted-access data from", base_url)
    else:
        base_url = "https://services.cancerimagingarchive.net/nbia-api/services/v1/"
        print("Downloading open-access data from", base_url)

    # download series from list    
    try:
        manifestDF=pd.DataFrame()
        seriesUID = ''
        
        for x in series_data:
            seriesUID = x
            data_url = base_url + "getImage?SeriesInstanceUID=" + seriesUID
            print("Downloading " + data_url)
            data = requests.get(data_url)
            file = zipfile.ZipFile(BytesIO(data.content))
            # print(file.namelist())
            file.extractall(path = "tciaDownload/" + "/" + seriesUID)
            # write the series metadata to a dataframe
            metadata_url = base_url + "getSeriesMetaData?SeriesInstanceUID=" + seriesUID
            metadata = requests.get(metadata_url).json()
            df = pd.DataFrame(metadata)
            manifestDF = pd.concat([manifestDF, df])

        # display manifest dataframe and/or save manifest to CSV file
        if csv_filename != "":
            manifestDF.to_csv(csv_filename + '.csv')
            display(manifestDF)
        else:
            display(manifestDF)

    except requests.exceptions.HTTPError as errh:
        print(errh)
    except requests.exceptions.ConnectionError as errc:
        print(errc)
    except requests.exceptions.Timeout as errt:
        print(errt)
    except requests.exceptions.RequestException as err:
        print(err)
    
####### Download the first 3 scans from a list of seriesInstanceUIDs (for demo purposes) and create a manifest
# Optional: Save a CSV of the manifest if you specify a csv_filename

def downloadSampleSeries(series_data, api_url = "", csv_filename=""):  

    # set API URL
    if api_url == "nlst":
        base_url = "https://services.cancerimagingarchive.net/nlst-api/services/v1/"
        print("Downloading NLST data from", base_url)
    if api_url == "restricted":
        base_url = "https://services.cancerimagingarchive.net/nbia-api/services/v2/"
        print("Downloading restricted-access data from", base_url)
    else:
        base_url = "https://services.cancerimagingarchive.net/nbia-api/services/v1/"
        print("Downloading open-access data from", base_url)

    # download series from list    
    try:
        manifestDF=pd.DataFrame()
        seriesUID = ''
        count = 0
        for x in series_data:
            seriesUID = x
            data_url = base_url + "getImage?SeriesInstanceUID=" + seriesUID
            print("Downloading " + data_url)
            data = requests.get(data_url)
            file = zipfile.ZipFile(BytesIO(data.content))
            # print(file.namelist())
            file.extractall(path = "tciaDownload/" + "/" + seriesUID)
            # write the series metadata to a dataframe
            metadata_url = base_url + "getSeriesMetaData?SeriesInstanceUID=" + seriesUID
            metadata = requests.get(metadata_url).json()
            df = pd.DataFrame(metadata)
            manifestDF = pd.concat([manifestDF, df])
            # Repeat n times for demo purposes - comment out these next 3 lines to download a full results
            count += 1;
            if count == 3:
                break  
        # display manifest dataframe and/or save manifest to CSV file
        if csv_filename != "":
            manifestDF.to_csv(csv_filename + '.csv')
            display(manifestDF)
        else:
            display(manifestDF)

    except requests.exceptions.HTTPError as errh:
        print(errh)
    except requests.exceptions.ConnectionError as errc:
        print(errc)
    except requests.exceptions.Timeout as errt:
        print(errt)
    except requests.exceptions.RequestException as err:
        print(err)
