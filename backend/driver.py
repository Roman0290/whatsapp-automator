import csv
import os.path
import random
import time
from datetime import datetime
from time import sleep
import json
import traceback

from colorama import Fore, Style
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException
timeout = 120


class Bot:
    

    def __init__(self):
        
        options = Options()
        options.add_argument("--user-data-dir=D:\\c drive files\\AiQeM Files\\Whatsapp-Automator\\backend\\chrome-data")  
        options.add_argument("--disable-extensions")
        options.add_argument("--headless")
       
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
       
        button = WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, css_selector))
        )
        sleep(random.uniform(1, 2))  
        self.driver.execute_script("arguments[0].click();", button)

    def construct_whatsapp_url(self, number):
        
        return f'https://web.whatsapp.com/send?phone={self.__prefix}{number.strip()}&type=phone_number&app_absent=0'

    def construct_whatsapp_group_url(self, group_name):
        
        encoded_group_name = group_name.replace(" ", "%20") 
        return f"https://web.whatsapp.com/accept?code={encoded_group_name}" 
    def login(self, prefix, send_to_contacts=True, send_to_groups=False): 
       
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
        """Searches for and sends a message to a group by its name with advanced error handling."""
        try:
            
            self.driver.get('https://web.whatsapp.com')
            print(f"Searching for group: {group_name}")
            sleep(5)  
            
           
            try:
                
                archived_link = self.driver.find_elements(By.XPATH, "//div[contains(text(), 'Archived')]")
                if archived_link and len(archived_link) > 0:
                    print("Checking archived chats...")
                    self.driver.execute_script("arguments[0].click();", archived_link[0])
                    sleep(2)
                    
                    
                    archived_group = self.driver.find_elements(By.XPATH, f"//span[contains(@title, '{group_name}')]")
                    if archived_group and len(archived_group) > 0:
                        print(f"Found group '{group_name}' in archived chats. Unarchiving...")
                        
                        self.driver.execute_script("arguments[0].click();", archived_group[0])
                        sleep(2)
                        
                        
                        menu_button = self.driver.find_elements(By.XPATH, "//span[@data-testid='menu']")
                        if menu_button and len(menu_button) > 0:
                            self.driver.execute_script("arguments[0].click();", menu_button[0])
                            sleep(1)
                            
                           
                            unarchive_option = self.driver.find_elements(By.XPATH, "//div[contains(text(), 'Unarchive')]")
                            if unarchive_option and len(unarchive_option) > 0:
                                self.driver.execute_script("arguments[0].click();", unarchive_option[0])
                                sleep(2)
                    
                    self.driver.get('https://web.whatsapp.com')
                    sleep(3)
            except Exception as e:
                print(f"Note: Could not check archived chats: {e}")
            
            
            search_button = None
            search_button_selectors = [
                "//button[@aria-label='Search']", 
                "//button[contains(@aria-label, 'search')]",
                "//div[@role='button' and contains(@aria-label, 'Search')]"
            ]
            
            for selector in search_button_selectors:
                try:
                    search_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    search_button.click()
                    print("Clicked search button")
                    sleep(2)
                    break
                except Exception as e:
                    continue
            
            
            search_box = None
            search_box_selectors = [
                "//div[@contenteditable='true']",
                "//div[@role='textbox']",
                "//div[contains(@title, 'Search')]//div[@contenteditable='true']",
                "//div[contains(@data-testid, 'search')]"
            ]
            
            for selector in search_box_selectors:
                try:
                    search_box = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    
                    search_box.clear()
                    sleep(1)
                    
                    
                    for char in group_name:
                        search_box.send_keys(char)
                        sleep(0.2) 
                    sleep(3)  
                    break
                except Exception as e:
                    continue
            
            if not search_box:
                print(Fore.RED + "Could not find search box" + Style.RESET_ALL)
                return True
            
            
            found_group = False
            group_selectors = [
                f"//span[@title='{group_name}']",
                f"//span[contains(@title, '{group_name}')]",
                f"//div[contains(@title, '{group_name}')]",
                f"//div[contains(text(), '{group_name}')]//ancestor::div[@role='row']"
            ]
            
            group_element = None
            for selector in group_selectors:
                try:
                    group_elements = self.driver.find_elements(By.XPATH, selector)
                    if group_elements and len(group_elements) > 0:
                        # Take screenshot for debugging if needed
                        # self.driver.save_screenshot(f"found_group_{time.time()}.png")
                        
                        
                        print(f"Found group matching '{group_name}', attempting to click...")
                        self.driver.execute_script("arguments[0].click();", group_elements[0])
                        sleep(3)  
                        found_group = True
                        group_element = group_elements[0]
                        break
                except Exception as e:
                    continue
            
            if not found_group:
                print(Fore.RED + f"Group '{group_name}' not found. Check spelling or if it's archived." + Style.RESET_ALL)
                
                self.driver.save_screenshot(f"group_not_found_{time.time()}.png")
                return True
            
            
            message_box = None
            message_selectors = [
                "//div[@contenteditable='true' and @data-tab='10']",
                "//div[@contenteditable='true' and @data-tab='9']",
                "//footer//div[@contenteditable='true']",
                "//div[@role='textbox']",
                "//div[contains(@class, 'selectable-text')][@contenteditable='true']"
            ]
            
            for selector in message_selectors:
                try:
                    message_box = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    message_box.click()
                    message_box.clear()
                    
                   
                    for chunk in [message[i:i+10] for i in range(0, len(message), 10)]:
                        message_box.send_keys(chunk)
                        sleep(random.uniform(0.3, 0.7))
                    
                    print("Entered message text")
                    sleep(1)
                    break
                except Exception as e:
                    continue
            
            if not message_box:
                print(Fore.RED + "Could not find message input field" + Style.RESET_ALL)
                return True
            
            send_success = False
            send_selectors = [
                "//span[@data-icon='send']",
                "//button[@aria-label='Send']", 
                "//span[@data-testid='send']",
                "//button[contains(@aria-label, 'Send')]"
            ]
            
            for selector in send_selectors:
                try:
                    send_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector if 'span' in selector else selector))
                    )
                    send_button.click()
                    send_success = True
                    print(Fore.GREEN + f"Message sent to '{group_name}' successfully!" + Style.RESET_ALL)
                    sleep(2)
                    break
                except Exception as e:
                    continue
            
           
            if not send_success:
                try:
                    message_box.send_keys(Keys.RETURN)
                    print(Fore.GREEN + f"Message sent to '{group_name}' using Enter key!" + Style.RESET_ALL)
                    send_success = True
                except Exception as e:
                    print(Fore.RED + f"Could not send message: {e}" + Style.RESET_ALL)
            
            return not send_success
            
        except Exception as e:
            print(Fore.RED + f"Selenium error occurred: {e}" + Style.RESET_ALL)
            print(Fore.RED + f"Stacktrace: {traceback.format_exc()}" + Style.RESET_ALL)
            return True
    def send_messages_to_all_groups(self):
        if not os.path.isfile(self._csv_groups):
            print(Fore.RED, "Group CSV file not found!", Style.RESET_ALL)
            return

        try:
            with open(self._csv_groups, mode="r") as file:
                csv_reader = csv.reader(file)

                for row in csv_reader:
                    group_name = row[0]
                    print(f"Sending message to group: {group_name}")

                    error = self.send_message_to_group(group_name, self._message) #used correct function.
                    self.log_result(group_name, error)

                    sleep(random.uniform(1, 10))

        except Exception as e:
            print(Fore.RED + f"Error in send_messages_to_all_groups: {e}" + Style.RESET_ALL)
        finally:
            pass

    def wait_for_element_to_be_clickable(self, xpath, success_message=None, error_message=None):
       
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

    def log_result(self, contact, error=None, status=None):
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "contact": str(contact),
            "status": status if status else ("failed" if error else "delivered"),
            "message": str(self._message)[:200]  
        }
        
        
        if not error and not status:
            try:
                current_status = self.check_message_status()
                log_entry["status"] = current_status
            except Exception as e:
                print(f"Status check error: {e}")
                log_entry["status"] = "delivered"
        
   
        log_path = os.path.join("logs", f"{self._start_time}_detailed.json")
        with open(log_path, "a", encoding='utf-8') as f:
            json.dump(log_entry, f, ensure_ascii=False)
            f.write("\n")
        
       
        text_log_path = os.path.join("logs", f"{self._start_time}_{'notsent' if error else 'sent'}.txt")
        with open(text_log_path, "a", encoding='utf-8') as f:
            f.write(f"{contact}\n")

    def check_message_status(self, message_text=None):
        try:
           
            outgoing_messages = self.driver.find_elements(
                By.XPATH, "//div[contains(@class, 'message-out')]"
            )
            
            if not outgoing_messages:
                return "unknown"
                
            
            last_message = outgoing_messages[-1]
            
            
            try:
                status = last_message.find_element(
                    By.XPATH, ".//span[@data-testid='msg-dblcheck' or @data-testid='msg-check']"
                )
                return "read" if status.get_attribute("data-testid") == "msg-dblcheck" else "delivered"
            except:
                
                try:
                    last_message.find_element(By.XPATH, ".//div[contains(@class, 'copyable-text')]")
                    return "sent" 
                except:
                    return "failed"  
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