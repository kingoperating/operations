# Import packages needed
from ast import keyword
from http import client
from posixpath import split
from time import strftime
from black import out
import requests
import os
from datetime import date, datetime, timedelta
import datetime as dt
import glob
import re
from dotenv import load_dotenv
import json
import pandas as pd
import numpy as np
from combocurve_api_v1 import ServiceAccount, ComboCurveAuth
from combocurve_api_v1.pagination import get_next_page_url

load_dotenv()  # load enviroment variables

pullFromAllocation = False

# connect to service account
service_account = ServiceAccount.from_file(os.getenv("API_SEC_CODE_LIVE"))
# set API Key from enviroment variable
api_key = os.getenv("API_KEY_PASS_LIVE")
# specific Python ComboCurve authentication
combocurve_auth = ComboCurveAuth(service_account, api_key)

print("Authentication Worked")

# adding the Master Battery List for Analysis
masterBatteryList = pd.read_csv(
    r"C:\Users\mtanner\OneDrive - King Operating\Documents 1\code\kingoperating\data\masterBatteryList.csv", encoding="windows-1252"
)

masterAllocationList = pd.read_excel(
    r"C:\Users\mtanner\OneDrive - King Operating\Documents 1\code\kingoperating\data\masterWellAllocation.xlsx"
)

# set some date variables we will need later
dateToday = dt.datetime.today()
todayYear = dateToday.strftime("%Y")
todayMonth = dateToday.strftime("%m")
todayDay = dateToday.strftime("%d")
dateYes = dateToday - timedelta(days=1)
yesDayString = dateYes.strftime("%d")

if pullFromAllocation == False:

    # set the interval for the API call
    numberOfDaysToPull = 60
    dateThirtyDays = dateToday - timedelta(days=numberOfDaysToPull)
    dateThirtyDaysYear = dateThirtyDays.strftime("%Y")
    dateThirtyDaysMonth = dateThirtyDays.strftime("%m")
    dateThirtyDaysDay = dateThirtyDays.strftime("%d")
    productionInterval = (
        "&start="
        + dateThirtyDaysYear
        + "-"
        + dateThirtyDaysMonth
        + "-"
        + dateThirtyDaysDay
        + "&end="
    )

    # Master API call to Greasebooks
    url = (
        "https://integration.greasebook.com/api/v1/batteries/daily-production?apiKey="
        + str(os.getenv("GREASEBOOK_API_KEY"))
        + productionInterval
        + todayYear
        + "-"
        + todayMonth
        + "-"
        + todayDay
    )

    # make the API call
    response = requests.request(
        "GET",
        url,
    )

    responseCode = response.status_code  # sets response code to the current state

    # parse as json string
    results = response.json()
    # setting to length of results
    numEntries = len(results)

    # checks to see if the GB API call was successful
    if responseCode == 200:
        print("Status Code is 200")
        print(str(numEntries) + " entries read")
    else:
        print("The Status Code: " + str(response.status_code))

    # adds the header to string
    headerCombocurve = [
        "Date",
        "Client",
        "API",
        "Well Accounting Name",
        "Oil Volume",
        "Gas Volume",
        "Water Volume",
        "Oil Sold Volume",
        "Data Source"
    ]

    totalComboCurveAllocatedProduction = pd.DataFrame(columns=headerCombocurve)

    wellIdList = []
    wellNameList = []
    wellIdOilSoldList = []
    wellVolumeOilSoldList = []
    gotDayData = np.full([200], False)
    totalOilVolume = 0
    totalGasVolume = 0
    totalWaterVolume = 0
    welopOilVolume = 0
    welopGasVolume = 0
    welopWaterVolume = 0
    welopOilSalesVolume = 0
    welopCounter = 0
    adamsRanchCounter = 0
    adamsRanchOilVolume = 0
    adamsRanchGasVolume = 0
    adamsRanchOilVolume = 0
    adamsRanchOilSalesVolume = 0

    # Gets list of Battery id's that are clean for printing
    listOfBatteryIds = masterAllocationList["Id in Greasebooks"].tolist()
    wellNameAccountingList = masterAllocationList["Name in Accounting"].tolist(
    )
    accountingIdList = masterAllocationList["Subaccount"].tolist()
    apiList = masterAllocationList["API"].tolist()
    allocationOilList = masterAllocationList["Allocation Ratio Oil"].tolist()
    allocationGasList = masterAllocationList["Allocation Ratio Gas"].tolist()

    apiHelpList = []

    for i in apiList:
        apiHelpList.append(str(i).split(".")[0])

    kComboCurve = 0  # variable for loop
    startingIndex = 0  # variable for loop

    lastDate = ""

    # gets length of totalAllocatedProduction
    initalSizeOfTotalAllocatedProduction = len(
        totalComboCurveAllocatedProduction)

    # MASTER loop that goes through each of the items in the response
    for currentRow in range(numEntries - 1, 0, -1):
        row = results[currentRow]  # get row i in results
        keys = list(row.items())  # pull out the headers

        # set some intial variables for core logic
        oilDataExist = False
        gasDataExist = False
        waterDataExist = False
        oilSalesDataExist = False
        oilVolumeClean = 0
        gasVolumeClean = 0
        waterVolumeClean = 0
        oilSalesDataClean = 0

        # Loops through each exposed API variable. If it exisits - get to correct variable
        for idx, key in enumerate(keys):
            if key[0] == "batteryId":
                batteryId = row["batteryId"]
            elif key[0] == "batteryName":
                batteryName = row["batteryName"]
            elif key[0] == "date":
                date = row["date"]
            # if reported, set to True, otherwise leave false
            elif key[0] == "oil":
                oilDataExist = True
                oilVolumeRaw = row["oil"]
                if oilVolumeRaw == "":  # if "" means it not reported
                    oilVolumeClean = 0
                else:
                    oilVolumeClean = oilVolumeRaw
            elif key[0] == "mcf":  # same as oil
                gasDataExist = True
                gasVolumeRaw = row["mcf"]
                if gasVolumeRaw == "":
                    gasVolumeClean = 0
                else:
                    gasVolumeClean = gasVolumeRaw
            elif key[0] == "water":  # same as oil
                waterDataExist = True
                waterVolumeRaw = row["water"]
                if waterVolumeRaw == "":
                    waterVolumeClean = 0
                else:
                    waterVolumeClean = waterVolumeRaw
            elif key[0] == "oilSales":
                oilSalesDataExist = True
                oilSalesDataRaw = row["oilSales"]
                if oilSalesDataRaw == "":
                    oilSalesDataClean = 0
                else:
                    oilSalesDataClean = oilSalesDataRaw

        # spliting date correctly
        splitDate = re.split("T", date)
        splitDate2 = re.split("-", splitDate[0])
        year = int(splitDate2[0])
        month = int(splitDate2[1])
        day = int(splitDate2[2])

        # CORE LOGIC BEGINS FOR MASTER LOOP

        # Colorado set MCF to zero
        if batteryId == 25381 or batteryId == 25382:
            gasVolumeClean = 0

        subAccountId = []  # empty list for subaccount id
        allocationRatioOil = []  # empty list for allocation ratio oil
        allocationRatioGas = []  # empty list for allocation ratio gas
        subAccountIdIndex = []  # empty list for index of subaccount id INDEX - used for matching

        wellAccountingName = []

        # gets all the indexs that match the battery id (sometimes 1, sometimes more)
        batteryIndexId = [m for m, x in enumerate(
            listOfBatteryIds) if x == batteryId]
        if batteryIndexId == []:
            continue
        # if only 1 index - then just get the subaccount id and allocation ratio
        if len(batteryIndexId) == 1:
            subAccountId = accountingIdList[batteryIndexId[0]]
            allocationRatioOil = allocationOilList[batteryIndexId[0]]
            allocationRatioGas = allocationGasList[batteryIndexId[0]]
            wellAccountingName = wellNameAccountingList[batteryIndexId[0]]
        else:  # if more than 1 index - then need to check if they are the same subaccount id
            # gets allocation for each subaccount
            for t in range(len(batteryIndexId)):
                subAccountId.append(accountingIdList[batteryIndexId[t]])
                allocationRatioOil.append(allocationOilList[batteryIndexId[t]])
                allocationRatioGas.append(allocationGasList[batteryIndexId[t]])
                wellAccountingName.append(
                    wellNameAccountingList[batteryIndexId[t]])

        dateString = str(month) + "/" + str(day) + "/" + str(year)
        dateStringComboCurve = datetime.strptime(dateString, "%m/%d/%Y")

        # clears the counters if the date changes
        if lastDate != dateString:
            welopCounter = 0
            welopGasVolume = 0
            welopOilVolume = 0
            welopWaterVolume = 0
            welopOilSalesVolume = 0
            adamsRanchCounter = 0
            adamsRanchGasVolume = 0
            adamsRanchOilSalesVolume = 0
            adamsRanchOilVolume = 0
            adamsRanchWaterVolume = 0

        # Splits battery name up
        splitString = re.split("-|–", batteryName)
        # sets client name to client name from ETX/STX and GCT
        clientName = splitString[0]
        # if field name exisits - add the batteryName
        if clientName == "CWS ":
            clientName = "KOSOU"
        elif clientName == "Peak ":
            clientName = "KOEAS"
        elif clientName == "Otex ":
            clientName = "KOGCT"
        elif clientName == "Midcon ":
            clientName = "KOAND"
        elif clientName == "Wellman ":
            clientName = "KOPRM"
        elif clientName == "Wellington ":
            clientName = "WELOP"
        elif clientName == "Scurry ":
            clientName = "KOPRM"
        elif clientName == "Wyoming":
            clientName = "KOWYM"

        # CORE LOGIC FOR WELLOP
        if len(batteryIndexId) == 1:
            if batteryId != 23012:
                newRowComboCurve = [dateStringComboCurve, clientName, apiHelpList[batteryIndexId[0]], wellAccountingName, oilVolumeClean,
                                    gasVolumeClean, waterVolumeClean, oilSalesDataClean, "di"]

                totalComboCurveAllocatedProduction.loc[startingIndex +
                                                       kComboCurve] = newRowComboCurve  # sets new row to combo curve
                kComboCurve = kComboCurve + 1  # counter for combo curve

            if batteryId == 23012:
                adamsRanchOilVolume = adamsRanchOilVolume + oilVolumeClean
                adamsRanchGasVolume = adamsRanchGasVolume + gasVolumeClean
                adamsRanchWaterVolume = adamsRanchWaterVolume + waterVolumeClean
                adamsRanchOilSalesVolume = adamsRanchOilSalesVolume + oilSalesDataClean
                adamsRanchCounter = adamsRanchCounter + 1

        elif len(batteryIndexId) > 1:
            for j in range(len(batteryIndexId)):
                wellOilVolume = oilVolumeClean * allocationRatioOil[j]/100
                wellGasVolume = gasVolumeClean * allocationRatioGas[j]/100
                wellWaterVolume = waterVolumeClean * allocationRatioOil[j]/100
                wellOilSalesVolume = oilSalesDataClean * \
                    allocationRatioOil[j]/100

                if batteryId != 25381 and batteryId != 25382:
                    newRow = [dateStringComboCurve, clientName, apiHelpList[batteryIndexId[j]], wellAccountingName[j], wellOilVolume,
                              wellGasVolume, wellWaterVolume, wellOilSalesVolume, "di"]
                    junk = 0

                else:
                    newRow = [dateStringComboCurve, clientName, "0" + apiHelpList[batteryIndexId[j]], wellAccountingName[j], wellOilVolume,
                              wellGasVolume, wellWaterVolume, wellOilSalesVolume, "di"]

                totalComboCurveAllocatedProduction.loc[startingIndex +
                                                       kComboCurve] = newRow
                kComboCurve = kComboCurve + 1

            if batteryId == 25381 or batteryId == 25382:
                welopOilVolume = welopOilVolume + oilVolumeClean
                welopGasVolume = welopGasVolume + gasVolumeClean
                welopWaterVolume = welopWaterVolume + waterVolumeClean
                welopOilSalesVolume = welopOilSalesVolume + oilSalesDataClean
                welopCounter = welopCounter + 1

        lastDate = dateString
else:
    totalComboCurveAllocatedProduction = pd.read_csv(
        r"C:\Users\mtanner\OneDrive - King Operating\Documents 1\code\kingoperating\data\comboCurveAllocatedProduction.csv")
    totalComboCurveAllocatedProduction = totalComboCurveAllocatedProduction.astype({
                                                                                   "API": "string"})

# converts API to int (removing decimals) and then back to string for JSON
totalComboCurveAllocatedProduction = totalComboCurveAllocatedProduction.astype({
                                                                               "Date": "string"})

# helps when uploading to ComboCurve to check for length of data (can only send 20,000 data points at a time)
print("Length of Total Asset Production: " +
      str(len(totalComboCurveAllocatedProduction)))

# drops columns that are not needed
totalComboCurveAllocatedProduction = totalComboCurveAllocatedProduction.drop(
    ["Well Accounting Name", "Client"], axis=1)

totalComboCurveAllocatedProduction = totalComboCurveAllocatedProduction.iloc[0:19999]

# renames columns to match ComboCurve
totalComboCurveAllocatedProduction.rename(
    columns={"Oil Volume": "oil", "Date": "date", "Gas Volume": "gas", "Water Volume": "water", "API": "chosenID", "Data Source": "dataSource", "Oil Sold Volume": "customNumber0"}, inplace=True)

# exports to json for storage
totalComboCurveAllocatedProduction.to_json(
    r".\kingoperating\data\totalAssetsProduction.json", orient="records")

totalAssetProductionJson = totalComboCurveAllocatedProduction.to_json(
    orient="records")  # converts to internal json format
# loads json into format that can be sent to ComboCurve
cleanTotalAssetProduction = json.loads(totalAssetProductionJson)

# prints length as final check (should be less than 20,000)
print("Length of Sliced Data: " + str(len(cleanTotalAssetProduction)))

# test data
testData = [{
    "date": "2021-05-01",
    "chosenID": "42357337470000",
    "oil": 1,
    "gas": 73.0,
    "water": 60.0,
    "dataSource": "di"
}]


# sets url to daily production for combo curve for daily production
url = "https://api.combocurve.com/v1/daily-productions"
auth_headers = combocurve_auth.get_auth_headers()  # authenticates ComboCurve

# put request to ComboCurve
response = requests.put(url, headers=auth_headers,
                        json=cleanTotalAssetProduction)

responseCode = response.status_code  # sets response code to the current state
responseText = response.text  # sets response text to the current state

print("Response Code: " + str(responseCode))  # prints response code

if "successCount" in responseText:  # checks if the response text contains successCount
    # finds the index of successCount
    # prints the successCount and the number of data points sent
    indexOfSuccessFail = responseText.index("successCount")
    print(responseText[indexOfSuccessFail:])

print("Check 3: Done with ComboCurve")
