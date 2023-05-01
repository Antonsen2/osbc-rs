import time
import pyautogui as pag
import pytweening
import utilities.random_util as rd
import utilities.api.item_ids as item_ids
import utilities.color as clr
import utilities.imagesearch as imsearch
import utilities.game_launcher as launcher
from model.bot import BotStatus
from model.osrs.osrs_bot import OSRSBot
from utilities.api.status_socket import StatusSocket
from utilities.geometry import Point, RuneLiteObject
from model.osrs.WillowsDad import WillowsDad_bot
import random

# Constants for magic numbers
LOW_HP_THRESHOLD = 3
HIGH_HP_THRESHOLD = 13
NPC_SEARCH_FAIL_LIMIT = 39
COIN_POUCH_THRESHOLD = 27
NO_POUCH_COUNT_LIMIT = 5


class NewPickPocket(OSRSBot):
    def __init__(self):
        title = "Pickpocket"
        description = (
            "This bot steals from NPCs and stalls in OSRS. Position your character near a tagged NPC or stall you wish to steal from. "
        )
        super().__init__(bot_title=title, description=description)
        self.running_time = 5
        self.pickpocket_option = 0
        self.should_click_coin_pouch = True
        self.should_drop_inv = True
        self.protect_rows = 5
        self.deposit_items = True
        self.out_of_food = False


    def create_options(self):
        # Add sliders and dropdown options
        self.options_builder.add_slider_option("running_time", "How long to run (minutes)?", 1, 360)
        self.options_builder.add_dropdown_option("should_click_coin_pouch", "Does this NPC drop coin pouches?", ["Yes", "No"])
        self.options_builder.add_dropdown_option("grab_food_from_bank", "Should the bot take food from bank?", ["Yes", "No"])
        self.options_builder.add_dropdown_option("deposit_items", "Should the bot deposit to bank?", ["Yes", "No"])
        self.options_builder.add_dropdown_option("should_drop_inv", "Drop inventory?", ["Yes", "No"])
        self.options_builder.add_slider_option("protect_rows", "If dropping, protect rows?", 0, 6)


    def save_options(self, options: dict):
        handlers = {
            'running_time': self.handle_running_time,
            'should_click_coin_pouch': self.handle_coin_pouch,
            'should_drop_inv': self.handle_drop_inv,
            'protect_rows': self.handle_protect_rows,
            'grab_food_from_bank': self.handle_banking,
            "deposit_items":  self.handle_deposit_items
        }

        for option, value in options.items():
            handler = handlers.get(option)
            if handler:
                handler(value)
            else:
                self.log_msg(f"Unknown option: {option}")
                print("Developer: ensure that the option keys are correct, and that options are being unpacked correctly.")
                self.options_set = False
                return

        self.options_set = True


    def handle_running_time(self, value):
        self.running_time = value
        self.log_msg(f"Running time: {self.running_time} minutes.")


    def handle_coin_pouch(self, value):
        self.should_click_coin_pouch = value == 'Yes'
        self.log_msg("Coin pouch check " + ("enabled." if self.should_click_coin_pouch else "disabled."))


    def handle_banking(self, value):
        self.handle_banking = value == 'Yes'
        self.log_msg("Banking for food " + ("enabled." if self.handle_banking else "disabled."))


    def handle_deposit_items(self, value):
        self.deposit_items = value == 'Yes'
        self.log_msg("Banking for food " + ("enabled." if self.deposit_items else "disabled."))


    def handle_move_mouse(self, value):
        self.should_move_mouse = value == 'Yes'
        self.log_msg("Dropping inventory " + ("enabled." if self.should_drop_inv else "disabled."))


    def handle_drop_inv(self, value):
        self.should_drop_inv = value == 'Yes'
        self.log_msg("Dropping inventory " + ("enabled." if self.should_drop_inv else "disabled."))


    def handle_protect_rows(self, value):
        self.protect_rows = value
        self.log_msg(f"Protecting first {self.protect_rows} row(s) when dropping inventory.")


    def main_loop(self):
        api = StatusSocket()
        coin_pouch_path = imsearch.BOT_IMAGES.joinpath("items", "coin_pouch.png")
        self.food_path = imsearch.BOT_IMAGES.joinpath("items", "salmon.png")
        self.deposit_all_path = imsearch.BOT_IMAGES.joinpath("items", "deposit_all.png")

        self.log_msg("Selecting inventory...")
        self.mouse.move_to(self.win.cp_tabs[3].random_point())
        self.mouse.click()

        # Anchors/counters
        npc_search_fail_count = 0
        theft_count = 0
        no_pouch_count = 0

        # Main loop
        start_time = time.time()
        end_time = self.running_time * 60
        while time.time() - start_time < end_time:
            # Check if we should eat
            
            if self.out_of_food and self.handle_banking:
                self.grab_food_from_bank()
            
            self.check_and_eat(api, start_time)

            # Check if we should drop inventory
            if self.should_drop_inv and api.get_is_inv_full():
                self.drop_inventory(api)


            # Steal from NPC
            npc_pos: RuneLiteObject = self.get_nearest_tag(clr.CYAN)
            if npc_pos is not None:
                self.steal_from_npc(npc_pos)
                npc_search_fail_count = 0
                theft_count += 1
            else:
                self.handle_npc_not_found(npc_search_fail_count, start_time)

            # Click coin pouch
            stack_size = api.get_inv_item_stack_amount(item_ids.coin_pouches)
            if self.should_click_coin_pouch and stack_size > COIN_POUCH_THRESHOLD:
                self.click_coin_pouch(coin_pouch_path, no_pouch_count)

            # Update progress
            self.update_progress((time.time() - start_time) / end_time)

        self.update_progress(1)
        self.__logout("Finished.")


    def __logout(self, msg):
        self.log_msg(msg)
        self.logout()
        self.stop()


    def check_and_eat(self, api, start_time):
        while self.get_hp() < random.randint(LOW_HP_THRESHOLD, HIGH_HP_THRESHOLD):
            food_indexes = api.get_inv_item_indices(item_ids.all_food)
            if food_indexes:
                self.log_msg("Eating...")
                self.mouse.move_to(self.win.inventory_slots[food_indexes[0]].random_point())
                self.mouse.click()
                # if len(food_indexes) > 1:  # eat another if available
                #     time.sleep(1)
                #     self.mouse.move_to(self.win.inventory_slots[food_indexes[1]].random_point())
                #     self.mouse.click()
            else:
                self.out_of_food = True
                if not self.handle_banking:
                    self.log_msg("Out of food, logging out")
                    self.__logout()

    def grab_food_from_bank(self):
        """Make sure that bank booth is marked yellow
        """
        if banks := self.get_all_tagged_in_rect(self.win.game_view, clr.YELLOW):
            time.sleep(rd.truncated_normal_sample(4, 7))
            banks = sorted(banks, key=RuneLiteObject.distance_from_rect_center)
            self.log_msg(f"Bank found")               
            self.mouse.move_to(banks[0].random_point())
            time.sleep(rd.truncated_normal_sample(0.1, 0.5))
            # self.mouse.click()
            while not self.mouse.click(check_red_click=True):
                self.mouse.move_to(banks[0].random_point())
                self.mouse.click()
                time.sleep(rd.truncated_normal_sample(0.1, 0.5))
            time.sleep(rd.truncated_normal_sample(5, 10))

            food = imsearch.search_img_in_rect(image=self.food_path, rect=self.win.game_view)
            deposit_all = imsearch.search_img_in_rect(image=self.deposit_all_path, rect=self.win.game_view)
            if food:
                if deposit_all and self.deposit_items:
                    self.mouse.move_to(
                    deposit_all.random_point(),
                    mouseSpeed="fastest",
                    tween=pytweening.easeInOutQuad,
                )
                    self.mouse.click(force_delay=True)
                    time.sleep(rd.truncated_normal_sample(0.5, 2))
                self.mouse.move_to(
                    food.random_point(),
                    mouseSpeed="fastest",
                    tween=pytweening.easeInOutQuad,
                )
                self.mouse.click(force_delay=True)
                time.sleep(rd.truncated_normal_sample(0.5, 2))
                self.out_of_food = False
                pag.press('esc')

            else:
                self.log_msg("Could not find food in bank...")


        else:
            self.log_msg(f"You probably forgot to tag the bank yellow")
            self.logout()



    def drop_inventory(self, api):
        skip_slots = api.get_inv_item_indices(item_ids.all_food)
        # Always drop the last row
        remove = range(24, 28)
        for index in remove:
            if index in skip_slots:
                skip_slots.remove(index)
        self.drop_all(skip_rows=self.protect_rows, skip_slots=skip_slots)


    def steal_from_npc(self, npc_pos):
        if not self.mouseover_text(contains="Pickpocket"):
            self.mouse.move_to(npc_pos.random_point(), mouseSpeed="fastest")
            self.log_msg('Moving cursor to higlighted area')
            if self.mouseover_text(contains="Pickpocket"):
                self.mouse.click()
                time.sleep(rd.truncated_normal_sample(0.3, 1.56))
        else:
            self.mouse.click()
            time.sleep(rd.truncated_normal_sample(0.3234, 0.756))
        if not self.mouseover_text(contains="Steal-from"):
            self.mouse.move_to(npc_pos.random_point(), mouseSpeed="fastest")
            self.log_msg('Moving cursor to higlighted area')
        else:
            time.sleep(rd.truncated_normal_sample(0.2, 0.6))
            self.mouse.click()
            time.sleep(rd.truncated_normal_sample(1.5, 2))


    def handle_npc_not_found(self, npc_search_fail_count, start_time):
        npc_search_fail_count += 1
        time.sleep(rd.truncated_normal_sample(0.1, 0.3))
        if npc_search_fail_count > NPC_SEARCH_FAIL_LIMIT:
            self.__logout(f"No NPC found for {npc_search_fail_count} seconds. Bot ran for {(time.time() - start_time) / 60} minutes.")


    def click_coin_pouch(self, coin_pouch_path, no_pouch_count):
        self.log_msg("Clicking coin pouch...")
        pouch = imsearch.search_img_in_rect(image=coin_pouch_path, rect=self.win.control_panel)
        if pouch:
            self.mouse.move_to(
                pouch.random_point(),
                mouseSpeed="fastest",
                tween=pytweening.easeInOutQuad,
            )
            self.mouse.click(force_delay=True)
            no_pouch_count = 0

        else:
            no_pouch_count += 1
            if no_pouch_count > NO_POUCH_COUNT_LIMIT:
                self.log_msg("Could not find coin pouch...")
                self.drop_all(skip_rows=self.protect_rows)
                no_pouch_count = 0
