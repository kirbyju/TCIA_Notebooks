####### imports
import requests
import pandas as pd
import json
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
        if api_url == "NLST":
            # create nlst token
            # Needed for Search w/ Authentication & Advanced APIs
            url = nlst_token_url + userName + "&password=" + passWord + "&grant_type=password&client_id=nbiaRestAPIClient&client_secret=ItsBetweenUAndMe"
            access_token = requests.get(url).json()["access_token"]
            print ('NLST API Token created successfully: ', access_token)
        else:
            # create regular token
            url = token_url + userName + "&password=" + passWord + "&grant_type=password&client_id=nbiaRestAPIClient&client_secret=ItsBetweenUAndMe"
            access_token = requests.get(token_url).json()["access_token"]
            print ('API Token created successfully: ', access_token)

        # set API call headers to use the access token we created
        api_call_headers = {'Authorization': 'Bearer ' + access_token}

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
    print("Specify credential file name: ")
    cred_file = input()

    # create credential file to use with NBIA Data Retriever  
    lines = ['userName=' + userName, 'passWord=' + passWord]
    with open(cred_file, 'w') as f:
        f.write('\n'.join(lines))
    print("Credential file for NBIA Data Retriever saved as", cred_file)
