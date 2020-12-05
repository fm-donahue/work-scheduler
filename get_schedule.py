import sys
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import (NoAlertPresentException,
                                        NoSuchElementException,
                                        TimeoutException,
                                        UnexpectedAlertPresentException)
# from selenium.webdriver.firefox.options import Options
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class Schedule():
    url = 'https://feed.kroger.com'

    def __init__(self, username, password):
        options = Options()
        options.add_argument('--headless')
        # options.add_argument('--disable-logging')
        options.add_argument('--log-level=3')
        # firefox_profile = webdriver.FirefoxProfile()
        # firefox_profile.set_preference('browser.privatebrowsing.autostart', True)
        # self.browser = webdriver.Firefox(options=options)
        self.browser = webdriver.Chrome(chrome_options=options) 
        self.username = username
        self.password = password
        self.logged_in = False
        
    # Use selenium to enter credentials and navigate to the page where schedules are posted.
    def get_schedule(self):
        self.browser.get(Schedule.url)
        try:
            wait = WebDriverWait(self.browser, 10)
            if self.logged_in:
                self.refresh_tab()            
            else:
                for x in range(5):
                    try:
                        wait.until(EC.presence_of_element_located((By.ID, 'KSWUSER')))
                        break
                    except TimeoutException:
                        if x != 4:
                            self.refresh_tab()
                            continue
                        print('There might be a problem in your network connection or the website.')
                        self.browser.quit() 
                        return None, None

                # Send credentials to login page
                euid = self.browser.find_element_by_id('KSWUSER')
                euid.send_keys(self.username)
                pwd = self.browser.find_element_by_id('PWD')
                pwd.send_keys(self.password)
                self.browser.find_element_by_xpath('//input[@value="I AGREE"][@type="submit"]').click()
                self.logged_in = True
                print('Logged in.')

                while True:
                    try:
                        wait.until(EC.presence_of_element_located((By.ID, 'tabs')))
                        break

                    # Clicks a button. The cause of this if the session is not yet cleared or deleted
                    # it will go to a page which will continue the last session
                    except TimeoutException:
                        try:
                            self.browser.find_element_by_id('btnContinue').click()
                            break
                        except NoSuchElementException:
                            print('There might be a problem in your network connection or the website.')
                            self.browser.quit() 
                            return None, None

                    # Accept alert popups
                    except UnexpectedAlertPresentException:
                        self.accept_popups()
                print('On page home tab.')

            # Click the schedule tab for table of schedules
            while True: 
                try:
                    wait.until(EC.element_to_be_clickable((By.ID, 'ui-id-2'))).click()
                    if wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'calDate'))):
                        break

                # Accept alert popups
                except UnexpectedAlertPresentException:
                    self.accept_popups()
                except (NoSuchElementException, TimeoutException):
                    self.refresh_tab()
                    pass

            source_code = self.browser.page_source
            return self.parse_sched(source_code)

        except KeyboardInterrupt:
            self.browser_quit()
            return None, None

    def accept_popups(self):
        try:
            alert = self.browser.switch_to.alert()
            alert.accept()
        except NoAlertPresentException:
            pass            

    def refresh_tab(self):
        self.browser.refresh()
        print('Refreshing.')

    def browser_quit(self):
        self.browser.quit()
        print("Browser closed.")

    # Parse the content of the source code using beautifulsoup to get the data(schedule date and time).
    def parse_sched(self, source_code):
        soup = BeautifulSoup(source_code, 'lxml')
        print('Parsing.')
        section_sched = soup.find('section', id='calMobile')
        date_sched = section_sched.find_all('div', class_='date')
        date = [date.text.strip().replace(',', '') for date in date_sched]
        time_sched = section_sched.find_all('div', class_='time')
        time = [time.text.replace(' ','').replace('a','AM').replace('p','PM') for time in time_sched]
        return date, time
