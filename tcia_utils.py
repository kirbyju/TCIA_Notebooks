####### imports
import requests
import pandas as pd
import json
import getpass
import zipfile
from io import BytesIO
from datetime import datetime
from datetime import timedelta

####### set API base_url
# TODO: add checks make sure there's a valid token if restricted APIs are selected and create one if there's not

def setApiUrl(api_url = ""):
    if api_url == "":
        # Search API (no login required): https://wiki.cancerimagingarchive.net/x/fILTB
        base_url = "https://services.cancerimagingarchive.net/nbia-api/services/v1/"
        print("Using open-access APIs from", base_url)
        return base_url
    elif api_url == "nlst":
        # Search API (no login required): https://wiki.cancerimagingarchive.net/x/fILTB
        base_url = "https://services.cancerimagingarchive.net/nlst-api/services/v1/"
        print("Using open-access NLST APIs from", base_url)
        return base_url
    elif api_url == "restricted":
        # Restricted-access API (login required): https://wiki.cancerimagingarchive.net/x/X4ATBg
        #if token_status = "valid":
        api_call_headers = {'Authorization': 'Bearer ' + access_token}
        base_url = "https://services.cancerimagingarchive.net/nbia-api/services/v2/"
        print("Using restricted-access APIs from", base_url)
        return base_url
        #else:
            #print("You must create a token to access this API.")
            #access_token = getToken()
    elif api_url == "advanced":
        # Advanced API (login required): https://wiki.cancerimagingarchive.net/x/YoATBg
        base_url = "https://services.cancerimagingarchive.net/nbia-api/services/"
        print("Using Advanced APIs from", base_url)
        return base_url
    elif api_url == "nlst-advanced":
        # Advanced API docs (login required): https://wiki.cancerimagingarchive.net/x/YoATBg
        base_url = "https://services.cancerimagingarchive.net/nlst-api/services/"
        print("Using Advanced NLST APIs from", base_url)
        return base_url
    else:
        base_url = "https://services.cancerimagingarchive.net/nbia-api/services/v1/"
        print("Invalid selection. Try 'nlst', 'restricted', 'advanced', and 'nlst-advanced' for special use cases.\nDefaulting to open-access APIs from", base_url)
        return base_url

####### get an API token to access restricted collections
# TODO: add feature to track token expiration time/status

def getToken(api_url = ""): 

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
            #current_time = datetime.now()
            #exp_time = current_time + timedelta(hours=2)
            #token_status = "valid"
            print ('API Token created successfully: ', access_token)
            #print('Token expires at', exp_time)
            return access_token
        else:
            # create regular token
            url = token_url + userName + "&password=" + passWord + "&grant_type=password&client_id=nbiaRestAPIClient&client_secret=ItsBetweenUAndMe"
            access_token = requests.get(url).json()["access_token"]
            # track expiration status/time (2 hours from creation)
            #current_time = datetime.now()
            #exp_time = current_time + timedelta(hours=2)
            #token_status = "valid"
            print ('API Token created successfully: ', access_token)
            #print('Token expires at', exp_time)
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
