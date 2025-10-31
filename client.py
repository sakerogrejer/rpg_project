# client.py

import socket
import getpass  # For securely reading a password
import threading  # For the non-blocking heartbeat
import sys  # For exiting the program
import time

# Assuming player.py and logger.py exist in the same directory
import player
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
    (No changes from original)
    """
    if response and response.startswith("LOGIN_SUCCESS"):
        cl.log("Login successful!")
        return True

    elif response and response.startswith("SIGNUP_SUCCESS"):
        cl.log("Sign-up successful! Please log in.")
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
    (No changes from original)
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


def run_login_cli(client, ret_info, cl):
    """
    Handles the login/signup logic via the command line.
    Returns True if login is successful, False if the user quits.
    """
    while True:
        print("\n--- Welcome ---")
        print("1. Login")
        print("2. Sign Up")
        print("3. Quit")
        choice = input("Enter your choice (1-3): ").strip()

        if choice == '3':
            return False  # User quit

        if choice in ('1', '2'):
            username = input("Username: ").strip()
            # Use getpass to hide password entry
            password_plain = getpass.getpass("Password: ").strip()

            if not username or not password_plain:
                cl.error("Username and password cannot be empty.")
                continue  # Ask for choice again

            # Hash the password before sending
            password_hashed = player.hash_password(password_plain)

            action = "LOGIN" if choice == '1' else "SIGNUP"
            client.send_data(f"{action} {username} {password_hashed}")

            response = client.receive_data()

            # Check if the response means we are logged in
            if handle_login_response(response, cl):
                ret_info.append(username)
                ret_info.append(password_hashed)  # Store the hashed password
                return True  # Login was successful!

            # If login/signup failed or was signup, the loop continues

        else:
            cl.warning("Invalid choice. Please enter 1, 2, or 3.")


def get_stat_input(prompt, cl):
    """Helper function to get a single valid integer stat from the user."""
    while True:
        try:
            value_str = input(prompt)
            value_int = int(value_str)
            if value_int < 0:
                cl.warning("Stat value must be non-negative.")
                continue
            return value_int
        except ValueError:
            cl.error("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            cl.warning("\nStat selection cancelled.")
            return None


def run_stats_selector_cli(cl):
    """
    Prompts the user to enter their stats via the command line.
    Returns (sword, shield, slaying, healing) or None if user quits.
    """
    cl.log("This appears to be your first login. Please set your stats.")
    print("--- Stat Selection ---")

    try:
        sword_damage = get_stat_input("Enter Sword Damage: ", cl)
        if sword_damage is None: return None

        shield_defense = get_stat_input("Enter Shield Defense: ", cl)
        if shield_defense is None: return None

        slaying_strength = get_stat_input("Enter Slaying Strength: ", cl)
        if slaying_strength is None: return None

        healing_strength = get_stat_input("Enter Healing Strength: ", cl)
        if healing_strength is None: return None

        cl.info(
            f"Stats selected: Sword {sword_damage}, Shield {shield_defense}, "
            f"Slaying {slaying_strength}, Healing {healing_strength}")
        return sword_damage, shield_defense, slaying_strength, healing_strength

    except KeyboardInterrupt:
        cl.warning("\nStat selection cancelled.")
        return None


def client_heartbeat(client, cl):
    """
    Sends periodic ALIVE pings to the server to maintain connection.
    (No changes from original)
    """
    try:
        client.send_data(f"HEARTBEAT NONE NONE")
        cl.info("Sent ALIVE ping to server.")
    except Exception as e:
        cl.error(f"Error sending ALIVE ping: {e}")


def run_game_loop_cli(client, cl):
    """
    Runs the main game loop after the player is logged in.
    Uses a thread for the heartbeat and waits for user input.
    """

    # Use an event to signal the heartbeat thread to stop
    stop_event = threading.Event()

    def heartbeat_task():
        """This function will run in a separate thread."""
        while not stop_event.is_set():
            client_heartbeat(client, cl)
            # Wait 5 seconds, but check the stop_event every second
            # This makes shutdown much faster
            for _ in range(5):
                if stop_event.is_set():
                    break
                time.sleep(1)

    # Start the heartbeat thread
    heartbeat_thread = threading.Thread(target=heartbeat_task, daemon=True)
    heartbeat_thread.start()

    cl.log("Game loop started. Type 'stats' to see your stats or 'quit' to exit.")

    try:
        while True:
            command = input("> ").strip().lower()

            if command == 'quit':
                cl.log("Quitting...")
                break

            elif command == 'stats':
                # Access the stats stored in the client's player object
                try:
                    stats_str = (
                        f"Current Stats - "
                        f"Sword: {client.player.sword_damage}, "
                        f"Shield: {client.player.shield_defense}, "
                        f"Slaying: {client.player.slaying_strength}, "
                        f"Healing: {client.player.healing_strength}"
                    )
                    cl.info(stats_str)
                except AttributeError:
                    cl.error("Player stats not initialized yet.")

            else:
                cl.warning(f"Unknown command: '{command}'. Try 'stats' or 'quit'.")

    except KeyboardInterrupt:
        cl.log("\nCaught Ctrl+C. Shutting down game loop.")

    finally:
        # Signal the heartbeat thread to stop
        cl.log("Stopping heartbeat timer...")
        stop_event.set()
        heartbeat_thread.join(timeout=2)  # Wait for thread to finish
        cl.log("Game loop ended.")


def main():
    """Main function to initialize and run the client."""
    # No Pygame init

    client = Client('localhost', 9999)
    cl = client.cl

    try:
        # Step 1: Run the login screen.
        result = []  # Will store [username, hashed_password]
        login_successful = run_login_cli(client, result, cl)

        # Step 2: If login was successful, run the game
        if not login_successful:
            cl.warning("User quit at login. Exiting.")
            client.close()
            sys.exit(0)

        cl.log("Moving to game setup...")
        username = result[0]
        hashed_password = result[1]

        cl.info(f"Requesting login count for {username}...")
        client.send_data(f"LOGINS {username} {hashed_password}")

        while True:
            response = client.receive_data()
            if response is None:
                cl.error("No response from server for LOGINS request. Retrying...")
                client.send_data(f"LOGINS {username} {hashed_password}")
                time.sleep(1)
                continue

            login_count = handle_login_counter(response, cl)
            if login_count == -1:
                cl.error("Failed to parse login count. Retrying...")
                client.send_data(f"LOGINS {username} {hashed_password}")
                time.sleep(1)
                continue

            # If first login, run stat selector
            if login_count <= 1:
                stats_result = run_stats_selector_cli(cl)
                if stats_result is None:
                    cl.error(f"{username} quit during stats selection. Exiting.")
                    return  # Finally block will handle cleanup

                sword, shield, slaying, healing = stats_result
                client.send_data(
                    f"SET_STATS:{sword},{shield},{slaying},{healing}" +
                    f" {username} {hashed_password}")

                stats_response = client.receive_data()
                if stats_response and stats_response.startswith("SET_STATS_SUCCESS"):
                    cl.log(f"{username} stats set successfully on server.")
                    break  # Break from the while loop
                else:
                    cl.error(f"Failed to set {username} stats on server. Retrying stat selection...")
                    # Loop will continue, re-prompting for stats (or you could exit)
            else:
                cl.log("Existing user. Skipping stat selection.")
                break  # Break from the while loop

        # Request player stats from server
        cl.log("Requesting player stats from server...")
        client.send_data(f"GET_STATS {username} {hashed_password}")

        while True:
            stats_response = client.receive_data()
            if stats_response and stats_response.startswith("GET_STATS_SUCCESS"):
                try:
                    stats_data = stats_response.split(maxsplit=1)[1]
                    sword_damage, shield_defense, slaying_strength, healing_strength = map(int, stats_data.split(','))
                    client.player.init_stats(sword_damage, shield_defense, slaying_strength, healing_strength)
                    cl.log(f"Received player stats from server: {stats_data}")
                    break  # Success
                except (IndexError, ValueError) as e:
                    cl.error(f"Error parsing player stats from server response: {e}")
            else:
                cl.error(f"Failed to receive player stats from server. Response: {stats_response}. Retrying...")
                client.send_data(f"GET_STATS {username} {hashed_password}")
                time.sleep(2)  # Wait before retrying

        # Run the main interactive game loop
        run_game_loop_cli(client, cl)

    except KeyboardInterrupt:
        cl.warning("\nShutting down client (KeyboardInterrupt).")
    finally:
        cl.warning("Client connection closed.")
        client.close()
        # No pygame.quit()


if __name__ == "__main__":
    main()