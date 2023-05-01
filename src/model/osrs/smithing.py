import time
import random
import pyautogui as pag
import pytweening
import pathlib
import utilities.random_util as rd
import utilities.api.item_ids as item_ids
import utilities.color as clr
import utilities.imagesearch as imsearch
import utilities.game_launcher as launcher
from model.bot import BotStatus
from model.osrs.osrs_bot import OSRSBot
from utilities.api.status_socket import StatusSocket
from utilities.geometry import Point, RuneLiteObject


class Furnace(OSRSBot, launcher.Launchable):

    def __init__(self):
        bot_title = "Madmak smelting"
        description = "This bot smelts everything"
        super().__init__(bot_title=bot_title, description=description)
        self.what_to_smelt = None
        self.running_time = 60
        self.take_breaks = True
        self.break_length_min = 1
        self.break_length_max = 300
        self.time_between_actions_min = 0.5
        self.time_between_actions_max = 2
        self.mouse_speed = "medium"
        self.break_probabilty = 0.05
        self.item1 = None
        self.item2 = None
        self.item3 = None

    def create_options(self):
        """Creates the option dropdown
        """
        super().create_options()
        self.options_builder.add_dropdown_option(
            "smelt", "What Do you want to smelt?", ["Cannonballs", "Gold_bracelet"]
        )

    def save_options(self, options: dict):
        for option in options:
            if  option == "smelt":
                self.what_to_smelt = options[option]         
            elif option == "running_time":
                self.running_time = options[option]
            elif option == "take_breaks":
                self.take_breaks = options[option] != []
            elif option == "break_length_min":
                self.break_length_min = options[option]
            elif option == "break_length_max":
                self.break_length_max = (options[option])
            elif option == "time_between_actions_min":
                self.time_between_actions_min = options[option]/1000
            elif option == "time_between_actions_max":
                self.time_between_actions_max = options[option]/1000
            elif option == "break_probabilty":
                self.break_probabilty = options[option]/100
                
            else:
                self.log_msg(f"Unknown option: {option}")
                self.options_set = False
                return

        self.log_msg(f"Running time: {self.running_time} minutes.")
        self.log_msg(f"Bot will{' ' if self.take_breaks else ' not '}take breaks.")
        self.log_msg(f"We are making {self.what_to_smelt}s")
        self.log_msg("Options set successfully.")
        self.options_set = True


    def launch_game(self):
        settings = pathlib.Path(__file__).parent.joinpath("custom_settings.properties")
        launcher.launch_runelite_with_settings(self, settings)

    def determine_what_we_are_making(self):
        if self.what_to_smelt == 'Cannonballs':
            self.item1 = imsearch.BOT_IMAGES.joinpath("items", "cannonball.png")
            self.item2 = imsearch.BOT_IMAGES.joinpath("items", "steel_bar.png")
            self.item3 = imsearch.BOT_IMAGES.joinpath("items", "ammo_mould.png")
            self.log_msg('Making Cannonballs')
        elif self.what_to_smelt == 'Gold_bracelet':
            self.item1 = imsearch.BOT_IMAGES.joinpath("items", "gold_bracelet.png")
            self.item2 = imsearch.BOT_IMAGES.joinpath("items", "gold_bar.png")
            self.log_msg('Making Gold_bracelet')
        else:
            self.log_msg('I dont know what I"m smelting')


    def deposit_items(self):
        """Deposits all items that are same as 2nd item in inventory
        """
        while not self.is_bank_open():
            time.sleep(rd.truncated_normal_sample(0.2, 0.4))
        
        if self.is_bank_open():
            self.log_msg("Bank open")
            time.sleep(rd.truncated_normal_sample(0.2, 0.5))
            Slot_to_click = self.win.inventory_slots[int(rd.fancy_normal_sample(2,27))]
            self.log_msg('depositing_items')
            self.mouse.move_to(Slot_to_click.random_point())#change this line to click on item in inventory
            self.mouse.click()
                

    def use_furnace(self):
        """smelts what is currently space. for setup make sure what you are makins is set to space.
            This is done on purpose to simulate humanlike behaviour.
        """
        crafting_view_path = imsearch.BOT_IMAGES.joinpath("items", "crafting_view.png")
        pink_object = self.get_nearest_tag(clr.PINK)
        if pink_object is not None:
            self.mouse.move_to(pink_object.random_point())
            self.mouse.click()
            self.log_msg('waiting for crafting screen to open...')
        else:
            self.log_msg("No pink object found...")

        while not imsearch.search_img_in_rect(crafting_view_path, self.win.game_view):
            time.sleep(rd.truncated_normal_sample(0.2, 0.4))

            
        # Press space on keyboard
        pag.press('space')
        # Wait for some time to let the action finish
        time.sleep(rd.truncated_normal_sample(0.2, 0.4))
 
    def main_loop(self):
        self.determine_what_we_are_making()
        start_time = time.time()
        end_time = self.running_time * 60
        self.open_inventory()
        self.find_nearest_bank()

        start_time = time.time()
        end_time = self.running_time * 60
        while time.time() - start_time < end_time:
            # 5% chance to take a break between tree searches
            if rd.random_chance(probability=self.break_probabilty) and self.take_breaks:
                self.take_break(min_seconds =self.break_length_min, max_seconds=self.break_length_max, fancy=True)   
            self.update_progress((time.time() - start_time) / end_time)
            self.bot_loop_main()
        self.update_progress(1)
        self.log_msg("Finished.")
        self.stop()


    def bot_loop_main(self):
        self.log_msg('starting cycle')
        self.withdrawl_ingrediants()
        time.sleep(rd.fancy_normal_sample(self.time_between_actions_min, self.time_between_actions_max))
        pag.press('esc')
        self.use_furnace()
        self.check_inv()
        self.find_nearest_bank()
        self.deposit_items()
        self.log_msg('one cycle done')
        
    def open_inventory(self):
        self.log_msg("Selecting inventory...")
        self.mouse.move_to(self.win.cp_tabs[3].random_point())
        self.mouse.click()


    def find_nearest_bank(self):
        if banks := self.get_all_tagged_in_rect(self.win.game_view, clr.YELLOW):
            banks = sorted(banks, key=RuneLiteObject.distance_from_rect_center)
            self.log_msg(f"Bank found")
            time.sleep(rd.fancy_normal_sample(self.time_between_actions_min, self.time_between_actions_max))
            self.mouse.move_to(banks[0].random_point())
            self.mouse.click()
 
        else:
            self.log_msg(f"You probably forgot to tag the bank yellow")  

    def check_inv(self):
        Sleep_time = rd.fancy_normal_sample(self.time_between_actions_min, self.time_between_actions_max)
        empty_inv_slot = imsearch.BOT_IMAGES.joinpath("items", "empty_inv.png")
        start_time = time.time()
        finished = False
        while not finished:
            while True:
                #Sets the bar as last_inv_item
                if self.what_to_smelt == 'Cannonballs':
                    last_inv_item = imsearch.search_img_in_rect(empty_inv_slot, self.win.inventory_slots[27])
                else:
                    last_inv_item = imsearch.search_img_in_rect(self.item1, self.win.inventory_slots[27])
                if last_inv_item:
                    self.log_msg(f"Finished items")
                    finished = True
                    break
                time.sleep(1)
                current_time = time.time()
                elapsed_time = current_time -start_time
                if elapsed_time > 120:
                    self.log_msg('Crafting for too long, something probably happend')
                    self.stop()
                    break
        if finished:
            self.log_msg(f"All items were made")
            time.sleep(Sleep_time)
            return True
        else:
            self.log_msg(f"failed to determine if all items were made")
            self.stop()


    def is_bank_open(self):
        bank_open = imsearch.BOT_IMAGES.joinpath("items", "deposit_all.png")
        if imsearch.search_img_in_rect(bank_open, self.win.game_view):
            return True
        else:
            return False

    def withdrawl_ingrediants(self):
        Sleep_time = rd.fancy_normal_sample(self.time_between_actions_min, self.time_between_actions_max)

        while not self.is_bank_open():
            time.sleep(rd.fancy_normal_sample(2, 5))
    
        if self.is_bank_open():
            self.log_msg("Bank open")
            time.sleep(Sleep_time)
            bar = imsearch.search_img_in_rect(self.item2, self.win.game_view)
            if bar:
                self.mouse.move_to(bar.random_point())
                self.mouse.click()
                time.sleep(Sleep_time)
            else:
                self.log_msg(f"Out of ingredients")
                self.stop()
                    
