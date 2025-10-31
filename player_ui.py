from tkinter import Image

import pygame
from pygame_gui.windows import ui_file_dialog
import pygame_gui

class LoginUI:

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((600, 400))
        pygame.display.set_caption("Login UI")
        self.clock = pygame.time.Clock()
        self.UI_manager = pygame_gui.UIManager((600, 400))
        self.usernameField = ""
        self.passwordField = ""
        self.username_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((50, 50), (100, 30)),
            text="Username:",
            manager=self.UI_manager
        )

        self.username_box = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((160, 50), (200, 30)),
            manager=self.UI_manager,
            object_id='username_box'
        )

        self.password_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((50, 100), (100, 30)),
            text="Password:",
            manager=self.UI_manager
        )

        self.password_box = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((160, 100), (200, 30)),
            manager=self.UI_manager,
            object_id='password_box'
        )
        self.password_box.set_text_hidden(True)

        self.login_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((50, 150), (130, 40)),
            text="Login",
            manager=self.UI_manager,
            object_id='login_button'
        )

        self.signup_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((230, 150), (130, 40)),
            text="Sign Up",
            manager=self.UI_manager,
            object_id='signup_button'
        )


    def draw(self):
        time_delta = self.clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

            self.UI_manager.process_events(event)

        self.UI_manager.update(time_delta)

        self.screen.fill((0, 0, 0))
        self.UI_manager.draw_ui(self.screen)

        pygame.display.update()


    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.login_button:
                self.usernameField = self.username_box.get_text()
                self.passwordField = self.password_box.get_text()
                return 'login', self.usernameField, self.passwordField

            elif event.ui_element == self.signup_button:
                self.usernameField = self.username_box.get_text()
                self.passwordField = self.password_box.get_text()
                return 'signup', self.usernameField, self.passwordField

        return None


class StatSelectUI:


    def __init__(self):
        pygame.init()

        width, height = pygame.display.get_surface().get_size()

        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Login UI")
        self.clock = pygame.time.Clock()
        self.UI_manager = pygame_gui.UIManager((width, height))

        self.sword_strength = LabeledSlider(
            manager=self.UI_manager,
            label_text="Sword Damage:",
            rect=pygame.Rect((50, 25), (300, 70)),
            start_value=0,
            value_range=(0, 3)
        )

        self.shield_defense = LabeledSlider(
            manager=self.UI_manager,
            label_text="Shield Defense:",
            rect=pygame.Rect((50, 95), (300, 70)),
            start_value=0,
            value_range=(0, 3)
        )

        self.slaying_strength = LabeledSlider(
            manager=self.UI_manager,
            label_text="Slaying Potion Strength:",
            rect=pygame.Rect((50, 165), (300, 70)),
            start_value=0,
            value_range=(0, 3)
        )

        self.healing_strength = LabeledSlider(
            manager=self.UI_manager,
            label_text="Healing Potion Strength:",
            rect=pygame.Rect((50, 235), (300, 70)),
            start_value=0,
            value_range=(0, 3)
        )

        self.confirm_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((150, 335), (100, 40)),
            text="Confirm",
            manager=self.UI_manager
        )

        # --- FIX: Pass the size to the constructor ---
        self.profile_picture = ImageButton(
            image_path='assets/profile_icon.png',
            position=(370, 25),
            manager=self.UI_manager,
            size=(64, 64)  # Specify the size you want
        )

        # --- ADD THIS LINE ---
        self.file_dialog = None


    def draw(self):
        time_delta = self.clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

            # --- START OF ALL FIXES ---

            # 1. Call your handle_event method for the confirm button
            result = self.handle_event(event)
            if result:
                print("Stats confirmed:", result)

            # 2. Check if the image button was clicked
            # We also check if a dialog is NOT already open
            if self.file_dialog is None:
                if self.profile_picture.handle_event(event):
                    # If clicked, create the dialog and store a reference to it
                    self.file_dialog = ui_file_dialog.UIFileDialog(
                        rect=pygame.Rect(100, 100, 400, 300),
                        manager=self.UI_manager,
                        window_title="Select Profile Picture",
                        initial_file_path=".",
                        allow_existing_files_only=True
                    )

            # 3. Check for events FROM the file dialog

            # This event fires when the user clicks 'Open'
            if event.type == pygame_gui.UI_FILE_DIALOG_PATH_PICKED:
                if event.ui_element == self.file_dialog:
                    # Get the path and update the image
                    self.profile_picture.set_new_image(event.text)
                    self.file_dialog = None  # We're done, reset the tracker

            # This event fires when the user clicks 'Cancel' or the 'X'
            if event.type == pygame_gui.UI_WINDOW_CLOSE:
                if event.ui_element == self.file_dialog:
                    self.file_dialog = None  # We're done, reset the tracker

            # 4. Pass the event to the UI Manager (as you were)
            self.UI_manager.process_events(event)

        self.UI_manager.update(time_delta)
        self.screen.fill((0, 0, 0))
        self.UI_manager.draw_ui(self.screen)


        self.sword_strength.update_value_label()
        self.shield_defense.update_value_label()
        self.slaying_strength.update_value_label()
        self.healing_strength.update_value_label()

        pygame.display.update()


    def handle_event(self, event):
        # This method is now correctly called from the draw() loop
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.confirm_button:
                sword_damage = int(self.sword_strength.get_current_value())
                shield_defense = int(self.shield_defense.get_current_value())
                slaying_strength = int(self.slaying_strength.get_current_value())
                healing_strength = int(self.healing_strength.get_current_value())

                return sword_damage, shield_defense, slaying_strength, healing_strength

        return None

class GameUI:
    def __init__(self, player):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("Game UI")
        self.clock = pygame.time.Clock()
        self.UI_manager = pygame_gui.UIManager((800, 600))

        self.sword_display = InventoryItemDisplay(player.inventory.sword.name,
                                                  player.inventory.sword.damage)

        self.shield_display = InventoryItemDisplay(player.inventory.shield.name,
                                                   player.inventory.shield.defense)

        self.slaying_potion_display = InventoryItemDisplay(player.inventory.slaying_potion.name,
                                                           player.inventory.slaying_potion.strength)

        self.healing_potion_display = InventoryItemDisplay(player.inventory.healing_potion.name,
                                                           player.inventory.healing_potion.strength)

    def draw(self):
        time_delta = self.clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

            self.UI_manager.process_events(event)

        self.UI_manager.update(time_delta)


        self.screen.fill((0, 0, 0))
        self.UI_manager.draw_ui(self.screen)

        self.sword_display.draw(self.screen, (50, 50))
        self.shield_display.draw(self.screen, (50, 100))
        self.slaying_potion_display.draw(self.screen, (50, 150))
        self.healing_potion_display.draw(self.screen, (50, 200))

        pygame.display.update()

# horizontal slider element with label and value display
class LabeledSlider:
    def __init__(self, manager, label_text, rect, start_value, value_range):


        # Split the width for the top row (the labels)
        label_width = int(rect.width * 0.7)  # Main label gets 70%
        value_width = rect.width - label_width  # Value label gets 30%

        # Calculate X position for the value label
        value_x_pos = rect.x + label_width


        self.label = pygame_gui.elements.UILabel(
            # Use the new calculated width
            relative_rect=pygame.Rect((rect.x, rect.y), (label_width, 30)),
            text=label_text,
            manager=manager
        )

        self.slider = pygame_gui.elements.UIHorizontalSlider(
            # The slider is on the next row, so its position is fine
            relative_rect=pygame.Rect((rect.x, rect.y + 40), (rect.width, 30)),
            start_value=start_value,
            value_range=value_range,
            manager=manager
        )

        # No longer need 'labelRight'
        # value label next to the label
        self.value_label = pygame_gui.elements.UILabel(
            # Use the new X position and width
            relative_rect=pygame.Rect((value_x_pos, rect.y), (value_width, 30)),
            text=str(start_value),
            manager=manager
        )


    def update_value_label(self):
        current_value = int(self.slider.get_current_value())
        self.value_label.set_text(str(current_value))

    def get_value(self):
        return int(self.slider.get_current_value())

    def get_current_value(self):
        return self.slider.get_current_value()


class InventoryItemDisplay:
    def __init__(self, name, level):
        self.name = name
        self.level = level

    def draw(self, surface, position):
        font = pygame.font.Font(None, 36)
        text = f"{self.name} (Level {self.level})"
        text_surface = font.render(text, True, (255, 255, 255))
        surface.blit(text_surface, position)

    def update_level(self, new_level):
        self.level = new_level

    def update_name(self, new_name):
        self.name = new_name

class ImageButton:
    def __init__(self, image_path, position, manager, size=(64, 64)):
        self.size = size
        self.manager = manager

        self.image_surface = pygame.image.load(image_path)
        self.image_surface = pygame.transform.scale(self.image_surface, self.size)

        self.rect = self.image_surface.get_rect(topleft=position)

        self.ui_element = pygame_gui.elements.UIImage(
            relative_rect=self.rect,
            image_surface=self.image_surface,
            manager=self.manager
        )

    # This method is called by StatSelectUI when the dialog is successful.
    def set_new_image(self, file_path):
        """Loads, scales, and sets a new image for the UI element."""
        try:
            self.image_surface = pygame.image.load(file_path)
            self.image_surface = pygame.transform.scale(self.image_surface, self.size)
            self.ui_element.set_image(self.image_surface)
        except pygame.error as e:
            print(f"Error loading image {file_path}: {e}")

    # This function just reports if it was clicked.
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button
                if self.ui_element.rect.collidepoint(event.pos):
                    return True  # Signal that we were clicked
        return False

    def get_image_path(self):
        return self.image_surface

    # DO NOT add a draw() method here
    # DO NOT add an is_clicked() method here