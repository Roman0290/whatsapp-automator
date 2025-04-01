import csv
import os.path
import random
import time
import traceback
from time import sleep

from colorama import Fore, Style
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

timeout = 120


class Bot:
    """
    Bot class that automates WhatsApp Web interactions using a Chrome driver.
    """

    def __init__(self):
        
        options = Options()
        options.add_argument("--user-data-dir=D:\\c drive files\\AiQeM Files\\Whatsapp-Automator\\backend\\chrome-data")  

       
        self.driver = webdriver.Chrome(service=ChromeService(r"D:\c drive files\AiQeM Files\Whatsapp-Automator\backend\chromedriver.exe"), options=options)
        self._message = None
        self._csv_numbers = None
        self._csv_groups = None 
        self._options = [False, False]  
        self._start_time = None
        self.__prefix = None

        self.__main_selector = "//p[@dir='ltr']"
        self.__fallback_selector = "//div[@class='x1hx0egp x6ikm8r x1odjw0f x1k6rcq7 x6prxxf']//p[@class='selectable-text copyable-text x15bjb6t x1n2onr6']"
        self.__media_selector = "//div[@class='x1hx0egp x6ikm8r x1odjw0f x1k6rcq7 x1lkfr7t']//p[@class='selectable-text copyable-text x15bjb6t x1n2onr6']"

    def click_button(self, css_selector):
        """
        Clicks a button specified by its CSS selector.
        """
        button = WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector))
        )
        sleep(random.uniform(1, 2))  
        self.driver.execute_script("arguments[0].click();", button)

    def construct_whatsapp_url(self, number):
        """
        Constructs the WhatsApp Web URL for opening a chat with a contact.
        """
        return f'https://web.whatsapp.com/send?phone={self.__prefix}{number.strip()}&type=phone_number&app_absent=0'

    def construct_whatsapp_group_url(self, group_name):
        """
        Constructs the WhatsApp Web URL for a group.
        """
        encoded_group_name = group_name.replace(" ", "%20") 
        return f"https://web.whatsapp.com/accept?code={encoded_group_name}" 

    def login(self, prefix, send_to_contacts=True, send_to_groups=False): 
        """
        Logs in to WhatsApp Web by navigating to the login page.
        Waits for the user to scan the QR code and logs in.
        """
        self.__prefix = prefix
        logged_in = False

        while not logged_in:
            try:
                self.driver.get('https://web.whatsapp.com')
                print("Attempting to load WhatsApp Web...")

                
                logged_in = self.wait_for_element_to_be_clickable(
                    "//div[@class='x1n2onr6 x14yjl9h xudhj91 x18nykt9 xww2gxu']",
                    success_message="Logged in successfully!",
                    error_message="Waiting for QR code to be scanned..."
                )

                if logged_in:
                    break

            except Exception as e:
                print(f"Error during login: {e}. Retrying...")
                time.sleep(5)

        self._start_time = time.strftime("%d-%m-%Y_%H%M%S", time.localtime())
        
        if send_to_groups:
            self.send_messages_to_all_groups()

    def quit_driver(self):
        """
        Closes the WebDriver session and quits the browser.
        """
        if self.driver:
            self.driver.quit()
            print(Fore.YELLOW, "Driver closed successfully.", Style.RESET_ALL)

    def send_message_to_contact(self, url, message, max_retries=3):
    
        message_sent = False
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                if not message_sent:  
                    self.driver.get(url)
                    
                    WebDriverWait(self.driver, 20).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                    sleep(2)  

                    selectors = [
                        "//div[@contenteditable='true'][@data-tab='10']",  
                        "//div[@contenteditable='true'][@data-tab='9']",   
                        "//div[contains(@class, 'selectable-text')]"       
                    ]

                    message_box = None
                    for selector in selectors:
                        try:
                            message_box = WebDriverWait(self.driver, 15).until(
                                EC.presence_of_element_located((By.XPATH, selector))
                            )
                            break
                        except:
                            continue

                    if not message_box:
                        raise Exception("Could not find message input box")

                   
                    try:
                        message_box.clear()
                        message_box.send_keys(message)
                    except StaleElementReferenceException:
                        
                        message_box = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, selectors[0]))
                        )
                        message_box.clear()
                        message_box.send_keys(message)

                    
                    send_button_selectors = [
                        "span[data-icon='send']",
                        "button[aria-label='Send']",
                        "//span[@data-testid='send']"
                    ]
                    
                    send_success = False
                    for selector in send_button_selectors:
                        try:
                            if 'span' in selector or 'button' in selector:
                                send_button = WebDriverWait(self.driver, 10).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                                )
                            else:
                                send_button = WebDriverWait(self.driver, 10).until(
                                    EC.element_to_be_clickable((By.XPATH, selector))
                                )
                            
                            try:
                                send_button.click()
                                send_success = True
                                break
                            except:
                                self.driver.execute_script("arguments[0].click();", send_button)
                                send_success = True
                                break
                        except:
                            continue

                    if not send_success:
                        
                        message_box.send_keys(Keys.RETURN)

                    
                    sleep(2)  
                    message_sent = True
                    print(Fore.GREEN + "Message sent successfully." + Style.RESET_ALL)
                    return False  

            except Exception as e:
                last_exception = e
                print(Fore.YELLOW + f"Attempt {attempt + 1} failed: {str(e)}" + Style.RESET_ALL)
                if attempt < max_retries - 1:
                    sleep(2 * (attempt + 1))  
                continue

        
        print(Fore.RED + f"Failed to send message after {max_retries} attempts. Last error: {str(last_exception)}" + Style.RESET_ALL)
        return True  

    def send_messages_to_all_contacts(self):
        """
        Sends messages to all contacts listed in the provided CSV file.
        """
        if not os.path.isfile(self._csv_numbers):
            print(Fore.RED, "Contact CSV file not found!", Style.RESET_ALL)
            return

        try:
            with open(self._csv_numbers, mode="r") as file:
                csv_reader = csv.reader(file)

                for row in csv_reader:
                    name, number = row[0], row[1]
                    print(f"Sending message to: {name} | {number}")

                    message = self._message.replace("%NAME%", name) if self._options[0] else self._message
                    url = self.construct_whatsapp_url(number)

                    error = self.send_message_to_contact(url, message)
                    self.log_result(number, error)

                    sleep(random.uniform(1, 10))

        except Exception as e:
            print(Fore.RED + f"Error in send_messages_to_all_contacts: {e}" + Style.RESET_ALL)
        finally:
            pass 

    def send_message_to_group(self, group_name, message):
        """Searches for and sends a message to a group by its name."""
        try:
           
            search_box = WebDriverWait(self.driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@contenteditable='true' and @role='textbox']"))
            )
            search_box.clear()
            search_box.send_keys(group_name)
            time.sleep(2) 
            
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//span[@title='" + group_name + "']"))
            )

           
            group_chat = WebDriverWait(self.driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, f"//span[@title='{group_name}']"))
            )
            self.driver.execute_script("arguments[0].click();", group_chat)  # Force click

            time.sleep(3)  
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//div[@data-testid='conversation-panel-messages']"))
            )

            
            try:
                message_box = WebDriverWait(self.driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, self.__main_selector))
                )
            except TimeoutException:
                try:
                    message_box = WebDriverWait(self.driver, 20).until(
                        EC.element_to_be_clickable((By.XPATH, self.__fallback_selector))
                    )
                except TimeoutException:
                    print(Fore.RED + "Message box not found." + Style.RESET_ALL)
                    return True
            except Exception as e:
                print(Fore.RED + f"Error finding message box: {e}" + Style.RESET_ALL)
                print(Fore.RED + f"Stacktrace: {traceback.format_exc()}" + Style.RESET_ALL)
                return True

            if self._options[1]:  
                message_box.send_keys(Keys.CONTROL, "v")
                sleep(random.uniform(2, 5))
                message_box = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, self.__media_selector))
                )

            message_box.send_keys(message)
            self.click_button("span[data-icon='send']")
            sleep(random.uniform(2, 5))

            print(Fore.GREEN + "Message sent successfully." + Style.RESET_ALL)
            return False

        except TimeoutException as te:
            print(Fore.RED + f"Timeout error: {te}" + Style.RESET_ALL)
            print(Fore.RED + f"Stacktrace: {traceback.format_exc()}" + Style.RESET_ALL)
            return True
        except Exception as e:
            print(Fore.RED + f"Error sending message to group '{group_name}': {e}" + Style.RESET_ALL)
            print(Fore.RED + f"Stacktrace: {traceback.format_exc()}" + Style.RESET_ALL)
            return True
    def send_messages_to_all_groups(self):
        """
        Sends messages to all groups listed in the provided CSV file.
        """
        if not os.path.isfile(self._csv_groups):
            print(Fore.RED, "Group CSV file not found!", Style.RESET_ALL)
            return

        try:
            with open(self._csv_groups, mode="r") as file:
                csv_reader = csv.reader(file)

                for row in csv_reader:
                    group_name = row[0]
                    print(f"Sending message to group: {group_name}")

                    url = self.construct_whatsapp_group_url(group_name)

                    error = self.send_message_to_contact(url, self._message)
                    self.log_result(group_name, error)

                    sleep(random.uniform(1, 10))

        except Exception as e:
            print(Fore.RED + f"Error in send_messages_to_all_groups: {e}" + StyleStyle.RESET_ALL)
        finally:
            pass 


    def wait_for_element_to_be_clickable(self, xpath, success_message=None, error_message=None):
        """
        Waits for an element to be clickable.
        """
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            if success_message:
                print(Fore.GREEN + success_message + Style.RESET_ALL)
            return True
        except TimeoutException:
            if error_message:
                print(Fore.RED + error_message + Style.RESET_ALL)
            return False

    def log_result(self, number, error):
        """
        Logs the result of each message sent attempt.
        """
        assert self._start_time is not None
        log_path = f"logs/{self._start_time}_{'notsent' if error else 'sent'}.txt"

        with open(log_path, "a") as logfile:
            logfile.write(number.strip() + "\n")

    def check_message_status(self, message_text=None):
        """
        Checks if the last message (or a specific message) has been read.
        Returns: "read", "delivered", "unknown", or "error"
        """
        try:
            
            status_elements = self.driver.find_elements(
                By.XPATH, "//span[@data-testid='msg-dblcheck' or @data-testid='msg-check']"
            )
            
            
            if message_text:
                messages = self.driver.find_elements(
                    By.XPATH, f"//div[contains(@class, 'message-out')]//div[contains(., '{message_text}')]"
                )
                if messages:
                    status = messages[-1].find_element(
                        By.XPATH, ".//following-sibling::div//span[@data-testid]"
                    )
                    return "read" if status.get_attribute("data-testid") == "msg-dblcheck" else "delivered"
            
            
            if status_elements:
                last_status = status_elements[-1].get_attribute("data-testid")
                return "read" if last_status == "msg-dblcheck" else "delivered"
                
            return "unknown"
            
        except Exception as e:
            print(f"Error checking message status: {e}")
            return "error"


        




    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, txt_file):
        with open(txt_file, "r") as file:
            self._message = file.read()

    @property
    def csv_numbers(self):
        return self._csv_numbers

    @csv_numbers.setter
    def csv_numbers(self, csv_file):
        self._csv_numbers = csv_file

    @property
    def csv_groups(self):
        return self._csv_groups

    @csv_groups.setter
    def csv_groups(self, csv_file):
        self._csv_groups = csv_file

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, opt):
        self._options = opt

    
    