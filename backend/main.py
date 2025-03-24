from driver import Bot, Fore, Style
import sys
import os

PREFIX = "251"  


class Menu:
    def __init__(self):
        self.bot = None
        self.choices = {
            "1": self.send_message,
            "2": self.send_with_media,
            "3": self.quit,
            "4": self.send_message_to_whatsapp_group,
        }

    def display(self):
        try:
            assert PREFIX != "" and "+" not in PREFIX
            print("WHATSAPP AUTOMATOR")
            print(Fore.YELLOW + f"You have chosen this number prefix: {PREFIX}" + Style.RESET_ALL)
            print("""
                        1. Send messages
                        2. Send messages with media attached
                        3. Quit
                        4. Send message to WhatsApp group
                    """)
        except AssertionError:
            print(Fore.RED + "Please fill the PREFIX variable in main.py OR remove the + in the PREFIX." + Style.RESET_ALL)
            sys.exit(1)

    def settings(self):
        print("- Select the file to use for the message:")
        txt = self.load_file("txt")

        print("- Select the file to use for the numbers:")
        csv = self.load_file("csv")

        include_names = None
        while include_names not in ["y", "n"]:
            include_names = input("- Include names in the messages? Y/N\n> ").lower()

        include_names = True if include_names == "y" else False

        return csv, txt, include_names

    def send_message(self):
        print(Fore.GREEN + "SEND MESSAGES" + Style.RESET_ALL)
        csv, txt, include_names = self.settings()
        print("Ready to start sending messages.")
        self.bot = Bot()
        self.bot.csv_numbers = os.path.join("data", csv)
        self.bot.message = os.path.join("data", txt)
        self.bot.options = [include_names, False]
        self.bot.login(PREFIX, send_to_contacts=True, send_to_groups=False) #added parameter

    def send_with_media(self):
        print(Fore.GREEN + "SEND MESSAGES WITH MEDIA" + Style.RESET_ALL)
        input(Fore.YELLOW + "Please COPY the media you want to send with CTRL+C, then press ENTER." + Style.RESET_ALL)
        csv, txt, include_names = self.settings()
        print("Ready to start sending messages with media.")
        self.bot = Bot()
        self.bot.csv_numbers = os.path.join("data", csv)
        self.bot.message = os.path.join("data", txt)
        self.bot.options = [include_names, True]
        self.bot.login(PREFIX, send_to_contacts=True, send_to_groups=False) #added parameter

    def load_file(self, filetype):
        selection = 0
        idx = 1
        files = {}

        for file in os.listdir("data"):
            if file.endswith("." + filetype):
                files[idx] = file
                print(idx, ") ", file)
                idx += 1

        if len(files) == 0:
            raise FileNotFoundError

        while selection not in files.keys():
            selection = int(input("> "))

        return str(files[selection])

    def send_message_to_whatsapp_group(self):
        print(Fore.GREEN + "SEND MESSAGE TO GROUP" + Style.RESET_ALL)
        print("- Select the file to use for the group message:")
        txt = self.load_file("txt")

        print("- Select the file to use for the Group list:")
        csv_groups = self.load_file("csv")

        self.bot = Bot()
        self.bot.message = os.path.join("data", txt)
        self.bot.csv_groups = os.path.join("data", csv_groups)
        self.bot.login(PREFIX, send_to_contacts=False, send_to_groups=True)
        self.bot.quit_driver()

    def quit(self):
        print("If you like this script, please donate.")
        print("Send MATIC, BEP20, ERC20, BTC, BCH, CRO, LTC, DASH, CELO, ZEC, XRP to:")
        print(Fore.GREEN, "landifrancesco.wallet", Style.RESET_ALL)
        sys.exit(0)

    def run(self):
        while True:
            self.display()
            choice = input("Enter an option: ")
            action = self.choices[choice]
            if action:
                action()
            else:
                print(Fore.RED, choice, " is not a valid choice")
                print(Style.RESET_ALL)


m = Menu()
m.run()

if __name__ == "__main__":
    try:
        test_bot = Bot()
        test_bot.driver.get("https://www.google.com")
        print(test_bot.driver.title)
        test_bot.driver.quit()
        print("Bot class started successfully!")
    except Exception as e:
        print(f"Error in Bot class: {e}")