# client.py

import pygame, player, player_ui, platform
import socket

from logger import ClientLogger


class Client:
    # --- Client class (no changes) ---
    def __init__(self, server_ip, server_port):
        self.server_address = (server_ip, server_port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.player = player.Player()
        self.cl = ClientLogger()

    def send_data(self, data):
        try:
            message = data.encode()
            self.sock.sendto(message, self.server_address)
        except Exception as e:
            self.cl.error(f"Error sending data: {e}")

    def receive_data(self):
        try:
            data, _ = self.sock.recvfrom(4096)
            return data.decode()
        except Exception as e:
            self.cl.error(f"Error receiving data: {e}")
            return None

    def close(self):
        self.sock.close()


# --- End of Client class ---


def handle_login_response(response, cl):
    """
    Parses the server's login/signup response.
    Returns True if login was successful, False otherwise.
    """
    if response and response.startswith("LOGIN_SUCCESS"):
        cl.log("Login successful!")
        # player_id = response.split()[1] # You can store this if needed
        return True

    elif response and response.startswith("SIGNUP_SUCCESS"):
        cl.log("Sign-up successful! Please log in.")
        # Or, you could modify this to auto-login and return True
        return False

    elif response and response.startswith("LOGIN_FAIL"):
        cl.error(f"Login failed: {response.split(maxsplit=1)[1]}")
        return False

    elif response and response.startswith("SIGNUP_FAIL"):
        cl.error(f"Sign-up failed: {response.split(maxsplit=1)[1]}")
        return False

    else:
        cl.warning(f"Unknown or empty server response: {response}")
        return False


def handle_login_counter(response, cl):
    """
    Parses the server's login counter response.
    Returns the number of logins if successful, -1 otherwise.
    """
    if response and response.startswith("LOGINS_COUNT"):
        try:
            count = int(response.split()[1])
            cl.info(f"Number of previous logins: {count}")
            return count
        except (IndexError, ValueError):
            cl.error("Error parsing login count from server response.")
            return -1
    else:
        cl.error(f"Unknown or empty server response: {response}")
        return -1


def run_login_screen(screen, client, login_ui, ret_info, cl):
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
                    cl.error("Username and password cannot be empty.")
                    continue  # Skip this event, wait for more input

                # Send the correct command based on the button pressed
                if action == 'login':
                    client.send_data(f"LOGIN {username} {password}")
                elif action == 'signup':
                    client.send_data(f"SIGNUP {username} {password}")

                response = client.receive_data()

                # Check if the response means we are logged in
                if handle_login_response(response, cl):
                    ret_info.append(username)
                    ret_info.append(password)
                    return True  # Login was successful!

        # Draw the login UI
        login_ui.draw()

    return False  # Should only be reached if loop exits abnormally


def run_stats_selector(screen, client, stats_ui, cl):
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
                cl.info(
                    f"Stats selected: Sword {sword_damage}, Shield {shield_defense}, Slaying {slaying_strength}, Healing {healing_strength}")
                return sword_damage, shield_defense, slaying_strength, healing_strength

        stats_ui.draw()

    return False  # Should only be reached if loop exits abnormally


def client_heartbeat(client, cl):
    """
    Sends periodic ALIVE pings to the server to maintain connection.
    """
    try:
        client.send_data(f"HEARTBEAT NONE NONE")
        cl.info("Sent ALIVE ping to server.")
    except Exception as e:
        cl.error(f"Error sending ALIVE ping: {e}")


def run_game_loop(screen, client, game_ui, cl):
    """
    Runs the main game loop after the player is logged in.
    """
    running = True


    should_heartbeat = pygame.USEREVENT + 1
    pygame.time.set_timer(should_heartbeat, 5000)  # Every 5

    while running:
        # --- Event Loop ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == should_heartbeat:
                client_heartbeat(client, cl)

        game_ui.draw()

    cl.log("Game loop ended.")


#TODO: Add a response timeout for server communications

def main():
    """Main function to initialize and run the client."""
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    login_ui = player_ui.LoginUI()
    client = Client('localhost', 9999)
    cl = client.cl

    try:
        # Step 1: Run the login screen. This loop will run
        # until the user logs in or quits.
        result = []
        login_successful = run_login_screen(screen, client, login_ui, result, cl)

        # Step 2: If login was successful, run the game
        if login_successful:
            cl.log("Moving to game loop...")
            cl.info(f"LOGINS {result[0]} {result[1]}")
            client.send_data(f"LOGINS {result[0]} {result[1]}")

            while True:
                response = client.receive_data()
                login_count = handle_login_counter(response, cl)
                if response is not None and login_count <= 1:
                    stats_ui = player_ui.StatSelectUI()
                    stats_result = run_stats_selector(screen, client, stats_ui, cl)
                    if stats_result is None:
                        cl.error(f"{result[0]} quit during stats selection.")
                        return
                    sword_damage, shield_defense, slaying_strength, healing_strength = stats_result
                    client.send_data(
                        f"SET_STATS:{sword_damage},{shield_defense},{slaying_strength},{healing_strength}" +
                        f" {result[0]} {result[1]}")
                    stats_response = client.receive_data()
                    if stats_response and stats_response.startswith("SET_STATS_SUCCESS"):
                        cl.log(f"{result[0]} stats set successfully on server.")
                        break
                    else:
                        cl.error(f"Failed to set {result[0]} stats on server. Retrying...")
                else:
                    break


            # Request player stats from server
            client.send_data(f"GET_STATS {result[0]} {result[1]}")

            while True:
                stats_response = client.receive_data()
                if stats_response and stats_response.startswith("GET_STATS_SUCCESS"):
                    try:
                        stats_data = stats_response.split()[1]
                        sword_damage, shield_defense, slaying_strength, healing_strength = map(int, stats_data.split(','))
                        client.player.init_stats(sword_damage, shield_defense, slaying_strength, healing_strength)
                        cl.log(f"Received player stats from server: {stats_data}")
                        break
                    except (IndexError, ValueError):
                        cl.error("Error parsing player stats from server response.")
                else:
                    cl.error("Failed to receive player stats from server.")


            gm = player_ui.GameUI(client.player)
            run_game_loop(screen, client, gm, cl)

    except KeyboardInterrupt:
        cl.warning("Shutting down client (KeyboardInterrupt).")
    finally:
        cl.warning("Client connection closed.")
        client.close()
        pygame.quit()


if __name__ == "__main__":
    main()
