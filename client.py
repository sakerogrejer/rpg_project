# client.py

import pygame, player, player_ui, platform
import socket


class Client:
    # --- Client class (no changes) ---
    def __init__(self, server_ip, server_port):
        self.server_address = (server_ip, server_port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.player = player.Player()

    def send_data(self, data):
        try:
            message = data.encode()
            self.sock.sendto(message, self.server_address)
        except Exception as e:
            print(f"Error sending data: {e}")

    def receive_data(self):
        try:
            data, _ = self.sock.recvfrom(4096)
            return data.decode()
        except Exception as e:
            print(f"Error receiving data: {e}")
            return None

    def close(self):
        self.sock.close()


# --- End of Client class ---


def handle_login_response(response):
    """
    Parses the server's login/signup response.
    Returns True if login was successful, False otherwise.
    """
    if response and response.startswith("LOGIN_SUCCESS"):
        print("Login successful!")
        # player_id = response.split()[1] # You can store this if needed
        return True

    elif response and response.startswith("SIGNUP_SUCCESS"):
        print("Sign-up successful! Please log in.")
        # Or, you could modify this to auto-login and return True
        return False

    elif response and response.startswith("LOGIN_FAIL"):
        print(f"Login failed: {response.split(maxsplit=1)[1]}")
        return False

    elif response and response.startswith("SIGNUP_FAIL"):
        print(f"Sign-up failed: {response.split(maxsplit=1)[1]}")
        return False

    else:
        print(f"Unknown or empty server response: {response}")
        return False


def run_login_screen(screen, client, login_ui):
    """
    Shows the login UI and handles login/signup logic.
    Returns True if login is successful, False if the user quits.
    """
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False  # User quit the program

            # Let the UI handle the event
            login_result = login_ui.handle_event(event)

            # login_result is (action, username, password) if a button was clicked
            if login_result is not None:
                action, username, password = login_result

                # Hash the password before sending
                password = player.hash_password(password)

                if not username or not password:
                    print("Username and password cannot be empty.")
                    continue  # Skip this event, wait for more input

                # Send the correct command based on the button pressed
                if action == 'login':
                    client.send_data(f"LOGIN {username} {password}")
                elif action == 'signup':
                    client.send_data(f"SIGNUP {username} {password}")

                response = client.receive_data()

                # Check if the response means we are logged in
                if handle_login_response(response):
                    return True  # Login was successful!

        # Draw the login UI
        login_ui.draw()

    return False  # Should only be reached if loop exits abnormally

def run_stats_selector(screen, client, stats_ui):
    """
    Placeholder for stats selection screen after login.
    """
    # For simplicity, we'll just return some default stats.
    # You can implement a full UI here similar to the login UI.
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None  # User quit the program

            stats_result = stats_ui.handle_event(event)

            if stats_result is not None:
                sword_damage, shield_defense, slaying_strength, healing_strength = stats_result
                print(f"Stats selected: Sword {sword_damage}, Shield {shield_defense}, ")
                print(f"Slaying Potion {slaying_strength}, Healing Potion {healing_strength}")

        stats_ui.draw()

    return False # Should only be reached if loop exits abnormally

def run_game_loop(screen, client):
    """
    Runs the main game loop after the player is logged in.
    """
    running = True
    clock = pygame.time.Clock()  # Good practice for a game loop

    while running:
        # --- Event Loop ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # --- Game Logic ---
        # (e.g., client.send_data("UPDATE_MY_POSITION ..."))
        # (e.g., game_state = client.receive_data())
        # (e.g., update_all_players(game_state))

        # --- Drawing ---
        screen.fill((50, 50, 100))  # Game background
        # ... draw your game (player, other players, platforms) ...

        pygame.display.flip()
        clock.tick(60)  # Cap at 60 FPS

    print("Game loop ended.")


def main():
    """Main function to initialize and run the client."""
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    login_ui = player_ui.LoginUI()
    client = Client('localhost', 9999)

    try:
        # Step 1: Run the login screen. This loop will run
        # until the user logs in or quits.
        login_successful = run_login_screen(screen, client, login_ui)

        # Step 2: If login was successful, run the game
        if login_successful:
            print("Moving to game loop...")
            client.send_data(f"LOGINS {client.player.profile.username} {client.player.profile.password}")
            run_game_loop(screen, client)

    except KeyboardInterrupt:
        print("Shutting down client (KeyboardInterrupt).")
    finally:
        print("Client connection closed.")
        client.close()
        pygame.quit()


if __name__ == "__main__":
    main()