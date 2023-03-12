"""
Scrape the Control Board for real-time alerts

Script will keep running and need to be initialted again when connection site is lost
refresh browser or press refresh tag below

REFRESH should be performed at intervals

"""
import os
import time
import logging
import shutil
import re
from datetime import date, datetime



from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException

from bs4 import BeautifulSoup

# initialize chrome driver
# TODO  DeprecationWarning: executable_path has been deprecated, please pass in a Service object
driver = webdriver.Chrome("chrome")
driver.maximize_window()
driver.implicitly_wait(30)

url = r"http://cavl-pvme201:8090/MOBILEvhm/Login?ReturnUrl=%2fMOBILEvhm%2fDevicesGroups%2fVHM" 
driver.get(url)

# Mobile-Eco-2 Credentials
username = "inita"
password = "init"

# Login
driver.find_element("id", "UserShortName").send_keys(username)
driver.find_element("id", "Password").send_keys(password)

driver.find_element(By.XPATH, "//div[input/@name='loginRequest']/button[1]").click()

# Navigate NAV for Dashboard | Control Board | Veh & Components | Realtime Cockpit | Config | Fleet History
URLS = {
        "fleetHistory":r"http://cavl-pvme201:8090/MOBILEvhm/DevicesGroups/FleetHistory",
        "vehHistory":r"http://cavl-pvme201:8090/MOBILEvhm/DevicesGroups/History",
        "ctrlBoard":r"http://cavl-pvme201:8090/MOBILEvhm/DevicesGroups/VHM",
        }

# NAVIGATE to control board
driver.get(URLS["ctrlBoard"])



# APPLY filters
# INPUT current date into LAST CHANGE field
# TODO include time "05/03/2023 09:02:40"
currentDATE = date.today().strftime("%d/%m/%Y")
currentTIME = datetime.now().strftime("%H:%M:%S")
currentHOUR = datetime.now().strftime("%H")
input_DT = currentDATE #+" "+currentHOUR
lastChange = driver.find_element(By.XPATH,'//*[@id="vehicleGrid_DXFREditorcol1_I"]').send_keys(input_DT)

# Wait for page to load
time.sleep(10)

# DETECT precence of Child Errors
# TODO GET all OP veh w/ child errors
# SET Child Errors Select All
#---------Warning FlashingSlow | Off | On (either or)
#---------Mal Function Indicator (MIL) Off | On (either or)
childError_filter = driver.find_element(By.XPATH,'//*[@id="vehicleGrid_col8"]/table/tbody/tr/td[2]/img').click()
childError_filter_select_all_checkbox = driver.find_element(By.XPATH,'//*[@id="vehicleGrid_HFSACheckBox"]').click()
childError_filter_OK = driver.find_element(By.XPATH,'//*[@id="vehicleGrid_DXHFP_TPCFCm1_O"]').click()
# page_dropDN_btn = driver.find_element(By.XPATH,'//*[@id="vehicleGrid_DXPagerBottom"]/a[5]')

# //*[@id="vehicleGrid_DXPagerBottom_PSI"]  , //*[@id="vehicleGrid_DXPagerBottom_PSB"],,,,/html/body/main/div/div/div[1]/div[2]/div[1]/table/tbody/tr/td/div[6]/div[1]/a[5],,,,,,/html/body/main/div/div/div[1]/div[2]/div[1]/table/tbody/tr/td/div[6]/div[1]/a[5]/img

# Wait for filters to APPLY
time.sleep(10)


# //// FUNCTIONS
def tableExtract(veh_id):
    """
    This function extracts additional detail on the vehicle errors
    Fault Codes
    Error Messages
    Error value readings

    """
    j=0
    err_rows = []
    while True:
        try:
            time.sleep(5)
            time_err = driver.find_element(By.XPATH,f'//*[@id="messagesGrid_DXDataRow{j}"]/td[1]').text
            # print(time_err)
            comp_err = driver.find_element(By.XPATH,f'//*[@id="messagesGrid_DXDataRow{j}"]/td[2]').text
            # print(comp_err)
            code_err = driver.find_element(By.XPATH,f'//*[@id="messagesGrid_DXDataRow{j}"]/td[3]/span').text
            # print(code_err)
            status_err_icon = driver.find_element(By.XPATH,f'//*[@id="messagesGrid_DXDataRow{j}"]/td[4]/div')
            status_err=status_err_icon.get_attribute("title")
            # print(status_err)
            msg_err_elem = driver.find_element(By.XPATH,f'//*[@id="messagesGrid_DXDataRow{j}"]/td[5]')
            msg_err = msg_err_elem.get_attribute("textContent")
            
            msg_dict = {
                'failure code':"",
                'SPN':"",
                'FMI':"",
                'current value':"",
                'alarm type':"",
                'mode':"",
                'ecuname':"",
                }
            
            # Parse message
            for msg in msg_dict:
                pat=fr'{msg}:(.*?)[;,)]'
                # print(re.findall(pat,msg_err))
                # # print("printing msg_err----",msg_err)
                if re.search(pat,msg_err):
                    msg_value = re.findall(pat,msg_err)
                    msg_dict[msg]=msg_value[0]
                    # print(msg_value)
                else:
                    msg_dict[msg]=None

            # Error message j for veh at row i 
            err_row = {
                "veh_id":veh_id,
                "time":time_err,
                "component":comp_err,
                "error_code":code_err,
                "status":status_err,
                "message":msg_dict,
                    }
        
            print(f"printing for {veh_id}\n-----------------\n",err_row,"\n-----------------")
            # print(veh_id,"----",err_row)
            # row_id = f"{veh_id}-{j}"
            comb_err_row = (err_row | msg_dict)
            err_rows.append(comb_err_row)
            # print(err_rows)
            j+=1
        except Exception:
            print("no more err to click ")
            return err_rows

    
def main():
    # Veh grid indexer
    i=0
    vehGridDataList = []
    # Loop row by row vehicle grid
    while True:
        try:
            vehgrid_row = driver.find_element(By.XPATH,f'//*[@id="vehicleGrid_DXDataRow{i}"]').click()
            veh_id = driver.find_element(By.XPATH,f'//*[@id="vehicleGrid_DXDataRow{i}"]/td[1]').text
            time.sleep(5)
            
            # Call function to extract veh incident descriptions for veh at row i
            vehGridDataList.append(tableExtract(veh_id))
            i+=1    
            print(i,"/n",veh_id)
            time.sleep(5)
        except Exception:
            print("no more to click: end of list")
            break     
    


    # Refresh vehicle grid
    refresh = driver.find_element(By.XPATH,'//*[@id="forceRefresh"]/a').click()

    df_list = []
    for veh in vehGridDataList:
        for r in veh:
            df = pd.DataFrame(veh).drop(columns=["message"])
            df_list.append(df)


    close_browser = driver.quit()

    data = pd.concat(df_list).reset_index().drop(columns=["index"])


    if __name__ == "__main__":
        main()

