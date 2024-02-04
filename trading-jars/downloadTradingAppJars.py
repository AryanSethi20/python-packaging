# Copyright (C) 2023 CloudFrame, Inc - All Rights Reserved
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential

import shutil
import subprocess
import time
import requests
import json
import logging
from urllib3.connection import HTTPConnection
import sys
import os
from zipfile import ZipFile

def enableHTTPTrace():

    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True

    HTTPConnection.debuglevel = 1

    return

def readConfig():
    configFile = "./ConfigFile.txt"
    if not (os.path.exists(configFile)) :
        print("E X C E P T I O N")
        print("")
        print("ConfigFile.txt is missing!! Setup Config file in ",os.getcwd())
        printSample()
        abend()

    configJson = ''
    cfile = open(configFile, "r")
    try:
        configJson = json.load(cfile)
    except Exception as parseExcp:
        print("E X C E P T I O N")
        print("")
        print("Config file JSON Parse Exception ! Refer below sample and correct ConfigFile.txt !!")
        printSample()
        print("")
        print("Error Details:")
        print("--------------")
        print(parseExcp)

    cfile.close()

    if ("CloudFrameServerUrl" not in configJson) or ("username" not in configJson) or ("password" not in configJson) or ("downloadApplicationJars" not in configJson) or ("appFolder" not in configJson):
        print("E X C E P T I O N")
        print("")
        print("Invalid ConfigFile.txt ! Refer below sample and correct ConfigFile.txt !!")
        printSample()
        abend()

    if ("JCLs" not in configJson["downloadApplicationJars"]) :
        print("E X C E P T I O N")
        print("")
        print("Invalid ConfigFile.txt ! 'JCLs' array missing under 'downloadApplicationJars' !!")
        printSample()
        abend()

    if ("debug"  in configJson):
        traceFlag = configJson["debug"]
        if traceFlag:
            enableHTTPTrace()

    return configJson

def printSample():

    print("")
    print("Sample Config file setup")
    print('       {')
    print('          "CloudFrameServerUrl": "http://localhost:9889",')
    print('          "username": "admin",')
    print('          "password": "cloudframeadmin",')
    print('          "debug": false,')
    print('          "appFolder": "C:\TradingSettlement\TradingSettlementApp\AppJars",')
    print('          "downloadApplicationJars": {')
    print('             "JCLs": [')
    print('                  "ACCPCAD",')
    print('                  "SETLCHF"')
    print('             ]')
    print('          }')
    print('       }')
    return

def connectToCFServerAndAuthenticate(configJson):

    global CloudFrameServerUrl
    CloudFrameServerUrl = configJson["CloudFrameServerUrl"]
    username = configJson["username"]
    password = configJson["password"]

    # Set up session
    session = requests.Session()
    # Make authentication request
    auth_path = "/CloudFrame/authenticate"
    auth_data = {"ldapUsername": username, "ldapPassword": password}
    #
    auth_response = session.post(CloudFrameServerUrl+auth_path, json=auth_data)
    # Check if authentication was successful
    if auth_response.status_code != 200:
        print("E X C E P T I O N")
        print("")
        print("CloudFrame Server Authentication failed !! HTTP Error Code = ",auth_response.status_code, ' Validate CloudFrame Server credentials in ConfigFile.txt !!')
        print("")
        print("CloudFrame Server Authentication Response")
        print("")
        print(auth_response.text)
        abend()
    return session


def getJCLs(cfSession):
    global CloudFrameServerUrl
    rest_path = "/CloudFrame/jcl"
    jclResponseJson = cfSession.get(CloudFrameServerUrl + rest_path)
    # Process REST response
    if jclResponseJson.status_code != 200:
        print("E X C E P T I O N")
        print("")
        print(rest_path," service invocation failed : HTTP Return Code = ",jclResponseJson.status_code)
        print("")
        print(jclResponseJson.text)
        abend()
    try:
        jclListJson = json.loads(jclResponseJson.text)
    except Exception as parseExcp:
        print("E X C E P T I O N")
        print("")
        print(rest_path,"did not return valid JSON response !!")
        print("")
        print("Response Details:")
        print("-----------------")
        print(jclResponseJson.text)
        print(parseExcp)
        abend()

    return jclListJson["jcl"]


def clearDownloads(cfSession):
    #       Trigger download of JCL with selected programs
    rest_path = "/CloudFrameServices/clearDownloads"

    clearDownloadResponse = cfSession.get(CloudFrameServerUrl + rest_path)
    # Process REST response
    if clearDownloadResponse.status_code != 200:
        print("E X C E P T I O N")
        print("")
        print(rest_path, " service invocation failed : HTTP Return Code = ", clearDownloadResponse.status_code)
        print("")
        print(clearDownloadResponse.text)
        abend()
    try:
        clearDownloadResponseJson = json.loads(clearDownloadResponse.text)
    except Exception as parseExcp:
        print("E X C E P T I O N")
        print("")
        print(rest_path, "did not return valid JSON response !!")
        print("")
        print("Response Details:")
        print("-----------------")
        print(clearDownloadResponseJson.text)
        print(parseExcp)
        abend()
    if clearDownloadResponseJson["message"] != "Successfully Cleard":
        print("E X C E P T I O N")
        print("")
        print(rest_path, "did not clear the downloads!!")
        print("")
        print("Response Details:")
        print("-----------------")
        print(clearDownloadResponse.text)
        abend()

    return

def triggerDownloadAllJars(cfSession, jclsToBeDownloded):
    global CloudFrameServerUrl
    programs = []
    jcl = ''
#   Extract programs to be downloaded for each JCL
    for jcl in jclsToBeDownloded:
        rest_path = "/CloudFrameServices/parseJcl/"+jcl
        jclResponseJson = cfSession.get(CloudFrameServerUrl + rest_path)
        # Process REST response
        if jclResponseJson.status_code != 200:
            print("E X C E P T I O N")
            print("")
            print(rest_path," service invocation failed : HTTP Return Code = ",jclResponseJson.status_code)
            print("")
            print(jclResponseJson.text)
            abend()
        try:
            programListJson = json.loads(jclResponseJson.text)
        except Exception as parseExcp:
            print("E X C E P T I O N")
            print("")
            print(rest_path,"did not return valid JSON response !!")
            print("")
            print("Response Details:")
            print("-----------------")
            print(jclResponseJson.text)
            print(parseExcp)
            abend()
        # extract programs to be downloaded for this JCL
        programs=[]
        for listinfo in programListJson["listInfo"]:
            program = listinfo["listingName"]
            includeflag =  listinfo["selected"]
            if includeflag:
                programs.append(program)

#       Trigger download of JCL with selected programs
        rest_path = "/CloudFrameServices/packageSbCode"
        payload = '{'\
                    '"progName":"'+jcl+'",'\
                    '"downloadAs":"maven",'\
                    '"downloadWithDCIO":"on",'\
                    '"jcl":"'+jcl+'",'\
                    '"progList":['
        for index, program in enumerate(programs):
            payload = payload + '"' + program + '"'
            if index != len(programs) - 1 :
                payload = payload + ','

        payload = payload +']}'
        payloadJson = json.loads(payload)

        #print(CloudFrameServerUrl + rest_path, '\nPayload : '+payload)
        downloadResponse = cfSession.post(CloudFrameServerUrl + rest_path,json=payloadJson)
        # Process REST response
        if downloadResponse.status_code != 200:
            print("E X C E P T I O N")
            print("")
            print(rest_path," service invocation failed : HTTP Return Code = ",downloadResponse.status_code)
            print("")
            print(downloadResponse.text)
            abend()
        try:
            downloadResponseJson = json.loads(downloadResponse.text)
        except Exception as parseExcp:
            print("E X C E P T I O N")
            print("")
            print(rest_path,"did not return valid JSON response !!")
            print("")
            print("Response Details:")
            print("-----------------")
            print(downloadResponse.text)
            print(parseExcp)
            abend()
        #If http status code is 200  then the response will should be  {"message":"Creation of zip <jclname>.zip is in-progress.","delay":5000}. Assume valid response indicates download is triggered

        print("Download of",jcl,"application jar triggered!")
        time.sleep(0.25)

    return


def downloadAllJars(cfSession,jclsToBeDownloded,appFolder):
    global CloudFrameServerUrl
    rest_path = "/CloudFrameServices/downloadStats"
    # extract programs to be downloaded for this JCL
    downloadStatusCheckLoop = True
    while downloadStatusCheckLoop:
        #   Extract programs to be downloaded for each JCL
        downloadStatsResponse = cfSession.get(CloudFrameServerUrl + rest_path)
        # Process REST response
        if downloadStatsResponse.status_code != 200:
            print("E X C E P T I O N")
            print("")
            print(rest_path, " service invocation failed : HTTP Return Code = ", downloadStatsResponse.status_code)
            print("")
            print(downloadStatsResponse.text)
            abend()

        # parse response
        try:
            downloadStatsResponseJson = json.loads(downloadStatsResponse.text)
        except Exception as parseExcp:
            print("E X C E P T I O N")
            print("")
            print(rest_path, "did not return valid JSON response !!")
            print("")
            print("Response Details:")
            print("-----------------")
            print(downloadStatsResponse.text)
            print(parseExcp)
            abend()

        downloadReady = True;
        for statinfo in downloadStatsResponseJson:
            # print(statinfo["jcl"],'**',statinfo["status"])

            if statinfo["status"] == 'FAILED':
                print("E X C E P T I O N")
                print("")
                print("Download failed ", statinfo)
                print("Retry by running this utility again!!")
                abend()

            if statinfo["status"] != 'COMPLETED':
                downloadReady = False
                break
        if downloadReady:
            downloadStatusCheckLoop = False
        else:
            # print("Download not yet ready")
            time.sleep(1)
#   print("Download ready")
#   Now we are ready to download jars to workstation
    for jcl in jclsToBeDownloded:
        rest_path = "/CloudFrame/getSpring/"+jcl
        downloadResponseJson = cfSession.get(CloudFrameServerUrl + rest_path)
        # Process REST response
        if downloadResponseJson.status_code == 200:
            f = open(appFolder+"\\"+jcl+".zip", "wb")
            f.write(downloadResponseJson.content)
            f.close()
            with ZipFile(appFolder+"\\"+jcl+".zip", "r") as zipObject:
                zipObject.extractall(path=appFolder+"\\"+jcl)
            os.remove(appFolder + '\\' + jcl + ".zip")
            print('Downloaded', jcl,'application to',appFolder+"\\"+jcl)
        else:
            print("E X C E P T I O N")
            print("")
            print(rest_path," service invocation failed : HTTP Return Code = ",downloadResponseJson.status_code)
            print("")
            print(downloadResponseJson.text)
            abend()
    return


def mavenBuildApplication(jclsToBeDownloded, appFolder):
    #   Extract programs to be downloaded for each JCL
    for jcl in jclsToBeDownloded:
        print ("mvn clean install cwd=" ,appFolder+"\\"+jcl)
        result = subprocess.run("mvn clean install", shell=True, cwd=appFolder+"\\"+jcl,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if ("BUILD SUCCESS" in str(result.stdout)):
            jarSourcePath = appFolder+"\\"+jcl+"\\target\\"+jcl+"-0.0.1-SNAPSHOT.jar"
            jarTargetPath = appFolder+"\\"+jcl+"-0.0.1-SNAPSHOT.jar"
            shutil.copy(jarSourcePath,jarTargetPath)
            print("Maven build of",jcl,"is successful!!",jcl+"-0.0.1-SNAPSHOT.jar","copied to",appFolder)
            #
            # Below code was used to copy property files to an external property folder as one time usage code. Retaining the code template as comments for future
            #
            # appPropFolder = appFolder + "\\..\\AppProperties\\"+jcl
            # os.mkdir(appPropFolder)
            # appSourcePath = appFolder+"\\"+jcl+"\\src\main\\resources\\application.properties"
            # appTargetPath = appFolder + "\\..\\AppProperties\\"+jcl+"\\application.properties"
            # shutil.copy(appSourcePath, appTargetPath)
            #
            # appSourcePath = appFolder+"\\"+jcl+"\\src\main\\resources\\db.properties"
            # appTargetPath = appFolder + "\\..\\AppProperties\\"+jcl+"\\db.properties"
            # shutil.copy(appSourcePath, appTargetPath)
            #
            # appSourcePath = appFolder+"\\"+jcl+"\\src\main\\resources\\program.properties"
            # appTargetPath = appFolder + "\\..\\AppProperties\\"+jcl+"\\program.properties"
            # shutil.copy(appSourcePath, appTargetPath)
            #
            # appSourcePath = appFolder+"\\"+jcl+"\\src\main\\resources\\utils.properties"
            # appTargetPath = appFolder + "\\..\\AppProperties\\"+jcl+"\\utils.properties"
            # if os.path.exists(appSourcePath):
            #   shutil.copy(appSourcePath, appTargetPath)
            #

        else:
            print("Maven build of", jcl, "failed!!")
            print(str(result.stdout))

    return

def abend():

    input("\n\nProcessing Failed!! Press Enter to close Console")
    sys.exit(12)

def main():
    print("")
    print("This utility automates download of CloudFrame migrated application jars using JCL downloader option")
    print("---------------------------------------------------------------------------------------------------")
    print("")

#   read and parse ConfigFile.txt
    configJson = readConfig()

#   extract all JCL jobnames to be downloaded from parsed ConfigFile.txt
    jclsToBeDownloded = configJson["downloadApplicationJars"]["JCLs"]

#   Connect to CF Server (Session mode)
    cfSession = connectToCFServerAndAuthenticate(configJson)

#   Get list of JCLs migrated and available for download
    availableJCLs = getJCLs(cfSession)

#   Validate if all JCLs requested for download are available
    allJclsAvailable = True
    missingJcls = []
    for jclToBeDownloded in jclsToBeDownloded:
        if jclToBeDownloded not in availableJCLs:
            missingJcls.append(jclToBeDownloded)
            allJclsAvailable = False

    if missingJcls !=[]:
        print("")
        print("E X C E P T I O N")
        print("")
        print("Following JCLs are not migrated. Either remove it from ConfigFile.txt or upload the JCLs before downloading application jars !!")
        for jcl in missingJcls:
            print("    - ",jcl)
        abend()

#   Clear Downloads
    clearDownloads(cfSession)

#   Now we are ready to trigger download of all jars
    triggerDownloadAllJars(cfSession,jclsToBeDownloded)

#   Extract appFolder in which appjars to be saved  from parsed ConfigFile.txt
    appFolder = configJson["appFolder"]
    if not os.path.exists(appFolder):
        os.makedirs(appFolder)
    if not os.path.isdir(appFolder):
        print("")
        print("E X C E P T I O N")
        print("")
        print("Folder", appFolder,'is not a directory! check ConfigFile.txt for the appFolder configuration')
        abend()

#   cleanup all zip files in appFolder
    fileList = os.listdir(appFolder)
    # print(fileList)

    for file in fileList:
        if file.endswith(".zip"):
            print("Deleting old archive file ",appFolder+'\\'+file)
            os.remove(appFolder+'\\'+file)
        if file.endswith(".jar"):
            print("Deleting old application jar file ",appFolder+'\\'+file)
            os.remove(appFolder+'\\'+file)

        if os.path.isdir(appFolder+'\\'+file) and file in jclsToBeDownloded:
            shutil.rmtree(appFolder+'\\'+file)
            print("Deleting old application folder ",appFolder+'\\'+file)

#   Validate if all downloads are ready (in COMPLETED status) and then download jars to workstation

    downloadAllJars(cfSession,jclsToBeDownloded,appFolder)

#
    mavenBuildApplication(jclsToBeDownloded,appFolder)

#
# Invoke main

def initiate():

    #validate if java is installed
    javaInstalled = True
    mavenInstalled = True
    if not shutil.which("java"):
        print("Java is not installed. Install Java and ensure java 'bin' folder is added to system path configuration")
        print("Steps to check if java is installed")
        print("  - Open Command window or shell ")
        print("  - Type Command 'java -version'")
        print("This should show the installed java version")
        javaInstalled=False

    if not shutil.which("mvn"):
        print("Apache Maven is not installed. Install it from https://maven.apache.org/download.cgi and ensure maven 'bin' folder is added to system path configuration")
        print("Steps to check if java is installed")
        print("  - Open Command window or shell ")
        print("  - Type Command 'mvn --version'")
        print("This should show the installed maven version")
        mavenInstalled=False

    if javaInstalled & mavenInstalled :
        pass
    else:
        print("")
        print("E X C E P T I O N")
        print("")
        print("Pre-requisite software not installed! Install & Validate missing software before re-running this utility!!")
        abend()

    main()

    input("Processing Successful, Press Enter to close Console")