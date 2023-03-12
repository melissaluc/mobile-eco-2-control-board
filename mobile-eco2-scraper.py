"""
Scrape the Control Board for real-time alerts

Script will keep running and need to be initialted again when connection site is lost
refresh browser or press refresh tag below

REFRESH should be performed at intervals

"""
import os
import time
import logging
import re
from datetime import date, datetime

import psycopg2
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options as ChromeOptions

st_cpu= time.process_time()
st = time.time()

fp_log = r"C:\Users\MelissaLu\OneDrive - Metrolinx\Desktop\Projects\data dump\mobile_eco2_dump\logging"

# # Log handler
# logging.basicConfig(level=logging.DEBUG,
#                     format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
#                     datefmt='%m-%d %H:%M',
#                     filename=r'{fp_log}\mobile-eco2-scraper.log',
#                     filemode='w')


# console = logging.StreamHandler()
# console.setLevel(logging.INFO)
# # set a format which is simpler for console use
# formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
# # tell the handler to use this format
# console.setFormatter(formatter)
# # add the handler to the root logger
# logging.getLogger('').addHandler(console)




# initialize chrome driver
# TODO  DeprecationWarning: executable_path has been deprecated, please pass in a Service object
options = ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-gpu")
options.add_experimental_option('excludeSwitches', ['enable-logging'])
driver = webdriver.Chrome(options=options)
driver.maximize_window()
driver.implicitly_wait(60)

url = r"http://cavl-pvme201:8090/MOBILEvhm/Login?ReturnUrl=%2fMOBILEvhm%2fDevicesGroups%2fVHM" 
driver.get(url)

# Mobile-Eco-2 Credentials
username = "inita"
password = "init"

# Login
driver.find_element("id", "UserShortName").send_keys(username)
driver.find_element("id", "Password").send_keys(password)
driver.find_element(By.XPATH, "//div[input/@name='loginRequest']/button[1]").click()
logging.info("Login Sucessful")

# Navigate NAV for Dashboard | Control Board | Veh & Components | Realtime Cockpit | Config | Fleet History
URLS = {
        "fleetHistory":r"http://cavl-pvme201:8090/MOBILEvhm/DevicesGroups/FleetHistory",
        "vehHistory":r"http://cavl-pvme201:8090/MOBILEvhm/DevicesGroups/History",
        "ctrlBoard":r"http://cavl-pvme201:8090/MOBILEvhm/DevicesGroups/VHM",
        }

# NAVIGATE to control board
driver.get(URLS["ctrlBoard"])


# INPUT current date into LAST CHANGE field
# Time string format: "05/03/2023 09:02:40"
currentTIME = datetime.now().strftime("%H:%M:%S")
currentHOUR = datetime.now().strftime("%H")
currentDATE = date.today().strftime("%d/%m/%Y")
input_DT = currentDATE #+" "+currentHOUR
# lastChange = driver.find_element(By.XPATH,'//*[@id="vehicleGrid_DXFREditorcol1_I"]').send_keys(input_DT)

# Wait for page to load
time.sleep(10)

# Select all Child Error
childError_filter = driver.find_element(By.XPATH,'//*[@id="vehicleGrid_col8"]/table/tbody/tr/td[2]/img').click()
childError_filter_select_all_checkbox = driver.find_element(By.XPATH,'//*[@id="vehicleGrid_HFSACheckBox"]').click()
childError_filter_OK = driver.find_element(By.XPATH,'//*[@id="vehicleGrid_DXHFP_TPCFCm1_O"]').click()

time.sleep(10)

num_pages = driver.find_element(By.XPATH,'//*[@id="vehicleGrid_DXPagerBottom"]/b[1]').text
next_page_li_idx = num_pages.split(" ")[3]



def tableExtract(veh_id):
    """
    Extract errors on the right table of the control board.

    """
    logging.info(f"TableExtracter function called for vehicle {veh_id}")
    j=0
    err_rows = []
    while True:
        try:
            time.sleep(5)
            time_err = driver.find_element(By.XPATH,f'//*[@id="messagesGrid_DXDataRow{j}"]/td[1]').text
            comp_err = driver.find_element(By.XPATH,f'//*[@id="messagesGrid_DXDataRow{j}"]/td[2]').text
            code_err = driver.find_element(By.XPATH,f'//*[@id="messagesGrid_DXDataRow{j}"]/td[3]/span').text
            status_err_icon = driver.find_element(By.XPATH,f'//*[@id="messagesGrid_DXDataRow{j}"]/td[4]/div')
            status_err=status_err_icon.get_attribute("title")
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
                if re.search(pat,msg_err):
                    msg_value = re.findall(pat,msg_err)
                    msg_dict[msg]=msg_value[0]
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
        
            comb_err_row = (err_row | msg_dict)
            err_rows.append(comb_err_row)

            logging.info(f"{status_err} for vehicle {veh_id}")
            j+=1
        except Exception:
            logging.debug(f"No more errors listed for vehicle {veh_id}")
            break
    return err_rows


def page_turner(idx):
        logging.info("page_turner function called:")
        try:       
            next_page = driver.find_element(By.XPATH,f'//*[@id="vehicleGrid_DXPagerBottom"]/a[{idx}]')
            next_page.click()
            logging.info("Turned to next page >>")
        except Exception:
            print(f"No more pages left to turn: {idx}")

    
def vehGridTableExtracter(i):
    logging.info("vehGridTableExtracter function called:") 
    
    vehGridDataList = []
    # Loop row by row vehicle grid
    while True:
        try:
            vehgrid_row = driver.find_element(By.XPATH,f'//*[@id="vehicleGrid_DXDataRow{i}"]').click()
            veh_id = driver.find_element(By.XPATH,f'//*[@id="vehicleGrid_DXDataRow{i}"]/td[1]').text
            time.sleep(5)
            
            # Call function to extract veh incident descriptions for veh at row i
            errExtract = tableExtract(veh_id)
            print(errExtract)
            vehGridDataList.append(errExtract)
            i+=1    
            # print(i,"/n",veh_id)
        except Exception:
            logging.debug("No more vehicles to click on: end of page")
            break
    
    return [vehGridDataList,i]

def vehGridTableParser(dataList):
    logging.info("vehGridTableParser function called:") 
    df_list = []
    for veh in dataList:
        for r in veh:
            df = pd.DataFrame(veh).drop(columns=["message"])
            df_list.append(df)

    try:
        data = pd.concat(df_list).reset_index().drop(columns=["index"])
        return data
    except Exception:
        logging.debug("Could not parse data in vehGridTableParser")

df_list_pages = []
pg = 1
idx=0
while True:
    logging.info("Start of Page {pg}")
    extractVehGrid = vehGridTableExtracter(idx)
    data_list = extractVehGrid[0]
    df_page = vehGridTableParser(data_list)
    df_list_pages.append(df_page)
    idx=extractVehGrid[1]+1
    if pg < (int(next_page_li_idx)):
        pg+=1
        print(f"Page {pg} of {next_page_li_idx}")
        page_turner(next_page_li_idx)
    else:
        break
    time.sleep(10)

close_browser = driver.quit()
logging.info("Browser closed.")

# Refresh vehicle grid
# refresh = driver.find_element(By.XPATH,'//*[@id="forceRefresh"]/a').click()


data = pd.concat(df_list_pages)

rename_dict = {
        "time":"timestamp",
        "failure code":"failure_code",
        "current value":"current_value",
        "alarm type":"alarm_type",
        }
data.rename(columns=rename_dict,inplace=True)

logging.info("Sucessfully scrapping of control board")
file_name = f"{currentDATE}-{currentTIME.split("/").join("-")}.csv"
data.to_csv(fr"C:\Users\MelissaLu\OneDrive - Metrolinx\Desktop\Projects\data dump\mobile_eco2_dump\output\{file_name}")

# # credentials
# db = "mx_tester_db"
# db_table = "mbl_eco2_ctrl_brd"
# username ='postgres'
# password='mxpassword'

# #establishing the connection
# conn = psycopg2.connect(
#    database=db, user=username, password=password, host='localhost', port= '5432'
# )



et = time.time()
et_cpu= time.process_time()
elapsed_time = (et - st)/60
print(elapsed_time," minutes")