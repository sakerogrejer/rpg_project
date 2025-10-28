import pygame
import pygame_gui

class LoginUI:

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((400, 400))
        pygame.display.set_caption("Login UI")
        self.clock = pygame.time.Clock()
        self.UI_manager = pygame_gui.UIManager((400, 400))
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
        self.screen = pygame.display.set_mode((400, 400))
        pygame.display.set_caption("Login UI")
        self.clock = pygame.time.Clock()
        self.UI_manager = pygame_gui.UIManager((400, 400))

        self.sword_strength = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect((50, 50), (300, 30)),
            start_value=2,
            value_range=(0, 3),
            manager=self.UI_manager,
            object_id='sword_strength'
        )

        self.shield_defense = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect((50, 100), (300, 30)),
            start_value=2,
            value_range=(0, 3),
            manager=self.UI_manager,
            object_id='shield_defense'
        )

        self.slaying_strength = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect((50, 150), (300, 30)),
            start_value=2,
            value_range=(0, 3),
            manager=self.UI_manager,
            object_id='slaying_strength'
        )

        self.healing_strength = pygame_gui.elements.UIHorizontalSlider(
            relative_rect=pygame.Rect((50, 200), (300, 30)),
            start_value=2,
            value_range=(0, 3),
            manager=self.UI_manager,
            object_id='healing_strength'
        )

        self.confirm_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((150, 300), (100, 40)),
            text="Confirm",
            manager=self.UI_manager,
            object_id='confirm_button'
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
            if event.ui_element == self.confirm_button:
                sword_damage = int(self.sword_strength.get_current_value())
                shield_defense = int(self.shield_defense.get_current_value())
                slaying_strength = int(self.slaying_strength.get_current_value())
                healing_strength = int(self.healing_strength.get_current_value())

                return sword_damage, shield_defense, slaying_strength, healing_strength

        return None