import os
import sys
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import (NoAlertPresentException,
                                        NoSuchElementException,
                                        TimeoutException,
                                        UnexpectedAlertPresentException)
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.by import By
# from selenium.webdriver.firefox.options import Options
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tzlocal import get_localzone


# Use selenium to enter credentials and navigate to the page where schedules are posted.
def get_data_from_site():
    options = Options()
    options.add_argument('--headless')
    # firefox_profile = webdriver.FirefoxProfile()
    # firefox_profile.set_preference('browser.privatebrowsing.autostart', True)
    # browser = webdriver.Firefox(options=options)
    
    browser = webdriver.Chrome(chrome_options=options)
    url = 'https://feed.kroger.com'
    browser.get(url)
    try:
        wait = WebDriverWait(browser, 10)

        username = os.environ.get('work_username')
        pwd = os.environ.get('work_pw')

        # Send credentials to login page
        euid = browser.find_element_by_id('KSWUSER')
        euid.send_keys(username)
        password = browser.find_element_by_id('PWD')
        password.send_keys(pwd)

        browser.find_element_by_xpath('//input[@value="I AGREE"][@type="submit"]').click()

        print('Logged in.')

        try:
            wait.until(EC.presence_of_element_located((By.ID, 'tabs')))

        # Clicks a button. The cause of this if the session is not yet cleared or deleted
        # it will go to a page which will continue the last session
        except TimeoutException:
            try:
                browser.find_element_by_id('btnContinue').click()
            except NoSuchElementException:
                print('There might be a problem in your network connection or website.')
                browser.quit() 
                sys.exit()

        print('On page home tab.')

        # Click the schedule tab for table of schedules
        while True: 
            try:
                wait.until(EC.element_to_be_clickable((By.ID, 'ui-id-2'))).click()

                if wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'calDate'))):
                    break

            # Accept alert popups
            except UnexpectedAlertPresentException:
                try:
                    alert = browser.switch_to.alert()
                    alert.accept()
                except NoAlertPresentException:
                    continue

            except (NoSuchElementException, TimeoutException):
                continue

        source_code = browser.page_source
        browser.quit()

        return source_code

    except KeyboardInterrupt:
        browser.quit()
        return None

# Parse the content of the source code using beautifulsoup to get the data(schedule date and time).
def parse_date(source_code):
    soup = BeautifulSoup(source_code, 'lxml')
    print('Parsing.')
    section_sched = soup.find('section', id='calMobile')
    date_sched = section_sched.find_all('div', class_='date')
    date = [date.text.strip().replace(',', '') for date in date_sched]
    time_sched = section_sched.find_all('div', class_='time')
    time = [time.text.replace(' ','').replace('a','AM').replace('p','PM') for time in time_sched]
    return date, time


def get_schedule():
    source_code = get_data_from_site()
    return parse_date(source_code)
