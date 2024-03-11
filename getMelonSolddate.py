import time
import re
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup
import pandas as pd

chrome_driver_path = '/Users/got/Documents/retune/t+im/chromedriver-mac/chromedriver'

def get_entertainment_soup() :
    chrome_driver_service = webdriver.chrome.service.Service(chrome_driver_path)

    driver = webdriver.Chrome(service=chrome_driver_service)
    driver.maximize_window()
    driver.get("https://www.ticketmelon.com")

    wait = WebDriverWait(driver, 10) #timeout=10 sec

    scroll_distance = 1200
    scroll_script = f"window.scrollBy(0, {scroll_distance});"
    driver.execute_script(scroll_script)

    print("scroll to entertainment :" , scroll_distance, "px")

    entertainment_button = wait.until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, '.slick-slide.slick-active.slick-current')))
    entertainment_button.click()

    scroll_distance = 1500
    scroll_script = f"window.scrollBy(0, {scroll_distance});"
    driver.execute_script(scroll_script)

    print("scroll to see more :" , scroll_distance, "px")

    see_more_button = driver.find_element(
        By.CSS_SELECTOR, '.HomeStyled__EventSeeMore-sc-125xn4a-2.eMhTTB')
    driver.execute_script("arguments[0].click();", see_more_button)

    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')

    driver.quit()

    return soup

def create_event_list(soup):
    elements = soup.find_all('div',
                            class_='MelonEventCardStyled__EventCardContainer-sc-8kc3ju-0'
                            )  #event-date, event-name, event-location
    event_data = []
    for element in elements:

        event_info = {
            "title": element.find('p', class_='event-name').text,
            "date": element.find('p', class_='event-date').text,
            "location": element.find('p', class_='event-location').text,
            "url": "https://www.ticketmelon.com" + element.find('a').get('href')
        }
        event_data.append(event_info)
    return event_data

def extract_dates(date_str):
    date_parts = re.findall(r'(\d{1,2}\s*[A-Za-z]{3})', date_str)
    if len(date_parts) == 2:
        start_date, end_date = date_parts
    elif len(date_parts) == 1:
        start_date = end_date = date_parts[0]
    else:
        start_date = end_date = None
    return start_date.strip(), end_date.strip()

def calculate_year(date_str):
    # Convert month abbreviations to numeric values
    month_values = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4,
        'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8,
        'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
    } 
    # Extract the month from the date
    month = date_str.split()[1]
    if month_values.get(month):
        if month_values[month] >= 8:
            return 2023
        else:
            return 2024
    else:
        return None  # Handle invalid month
    
def getSoup(url) :
    chrome_driver_service = webdriver.chrome.service.Service(chrome_driver_path)
    driver = webdriver.Chrome(service=chrome_driver_service)
    driver.get(url)
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')
    driver.quit()
    return soup

def getInfo(soup):
    types = []
    prices = []
    qtys = []

    elements = soup.find_all('div', class_='ticket--type')
    for element in elements :
        div_text = element.contents[0].strip()
        types.append(div_text)

    elements = soup.find_all('div', class_='ticket--price')
    for element in elements :
        prices.append(element.text)

    elements = soup.find_all('div', class_='ticket--qty')
    for element in elements :
        qtys.append(element.text)
    return types, prices, qtys

def createTypelist(title, types, prices, qtys):
    type_list = []
    for i, type in enumerate(types) :
        if prices[0].strip(" ") != 'Price' : #skip event that's not concert
            continue
        #prevent header
        if (type == 'Ticket Type') or (prices[i].strip(" ") =='Price'):
            continue
        #if SOLDOUT --> get today, if sale ended --> sale ended, else none
        solddate = None
        if qtys[i] == 'Sales Ended' :
            solddate = 'Sales Ended'
        elif qtys[i] == 'Sold Out' :
            solddate = datetime.now().strftime("%Y-%m-%d")

        type_info = {
            'title': title,
            'type': types[i],
            'price': prices[i].split(' ')[0],
            'solddate': solddate
        }
        type_list.append(type_info)

    return type_list

soup = get_entertainment_soup()
event_data = create_event_list(soup)
df = pd.DataFrame(event_data)

df[['startdate', 'enddate']] = df['date'].apply(extract_dates).apply(pd.Series)

df['startyear'] = df['startdate'].apply(calculate_year)
df['endyear'] = df['enddate'].apply(calculate_year)
df['startyear'] = df['startyear'].astype(str)
df['endyear'] = df['endyear'].astype(str)

df['startdate'] = df['startdate'] + ' ' + df['startyear']
df['startdate'] = pd.to_datetime(df['startdate'], format='%d %b %Y', errors='coerce')
df['enddate'] = df['enddate'] + ' ' + df['endyear']
df['enddate'] = pd.to_datetime(df['enddate'], format='%d %b %Y', errors='coerce')

df.drop(columns=['startyear', 'endyear'], inplace=True)
df = df.sort_values(by=['startdate', 'enddate'])

df.drop(columns=['date'], inplace=True)

df.drop_duplicates()

unique_concert = df['title'].unique()
today_date = datetime.now()
types_list = []
count = 0
for title in unique_concert :
    count +=1
    # title = unique_concert[i]
    starttime = time.time()
    print(title)
    enddate = df.loc[df['title']==title, 'enddate'].iloc[0] + timedelta(days=1) #add 1 days to include the enddate
    if enddate < today_date: 
        continue
    url = df.loc[df['title']==title, 'url'].iloc[0]
    soup = getSoup(url)
    types, prices, qtys = getInfo(soup)
    endtime = time.time()
    print(endtime - starttime)
    if len(types) == 0 :         
        print('count =',count)
        count =0
        time.sleep(660)
        print('-------------------------------------------')
        starttime = time.time()
        print(title)
        soup = getSoup(url)
        types, prices, qtys = getInfo(soup)
        type_list = createTypelist(title, types, prices, qtys)
        types_list += type_list
        endtime = time.time()
        print(endtime - starttime)
        print('-------------------------------------------')
        continue
    print('-------------------------------------------')
    type_list = createTypelist(title, types, prices, qtys)
    types_list += type_list

temp = pd.DataFrame(types_list)
df = pd.merge(df, temp, on='title', how='outer')

date = datetime.now().date()
print(date)
path = '/Users/got/Documents/retune/t+im/melon_solddate/melonSolddate'+'('+str(date)+')'+'.csv'
df.to_csv(path, index=False)