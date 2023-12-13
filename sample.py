import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
from IPython.display import display

chrome_driver_path = '/Users/got/Documents/retune/chromedriver-mac-x64/chromedriver'
chrome_driver_service = webdriver.chrome.service.Service(chrome_driver_path)
driver = webdriver.Chrome(service=chrome_driver_service)
driver.get("https://www.ticketmelon.com")

wait = WebDriverWait(driver, 10)
wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
### click Entertainment
scroll_distance = 1000
scroll_script = f"window.scrollBy(0, {scroll_distance});"
driver.execute_script(scroll_script)

entertainment_button = wait.until(
    EC.element_to_be_clickable(
        (By.CSS_SELECTOR, '.slick-slide.slick-active.slick-current')))
entertainment_button.click()

wait = WebDriverWait(driver, 10)
time.sleep(2)
### click See More
scroll_distance = 1500
scroll_script = f"window.scrollBy(0, {scroll_distance});"
driver.execute_script(scroll_script)

see_more_button = driver.find_element(
    By.CSS_SELECTOR, '.HomeStyled__EventSeeMore-sc-125xn4a-2.eMhTTB')
driver.execute_script("arguments[0].click();", see_more_button)

wait = WebDriverWait(driver, 10)

### get html
page_source = driver.page_source
soup = BeautifulSoup(page_source, 'html.parser')
elements = soup.find_all('div',
                         class_='MelonEventCardStyled__EventDetail-sc-8kc3ju-2'
                         )  #event-date, event-name, event-location
event_data = []
for element in elements:
    event_info = {
        "Title": element.find('p', class_='event-name'),
        "Date": element.find('p', class_='event-date'),
        "Location": element.find('p', class_='event-location')
    }
    event_data.append(event_info)

melon_concert = pd.DataFrame(event_data)
display(melon_concert)