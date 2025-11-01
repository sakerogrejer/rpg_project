# client.py
import os
import socket
import getpass  # For securely reading a password
import threading  # For the non-blocking heartbeat
import sys  # For exiting the program
import time
import select

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
        self.suppress_output = True

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

#
def server_listener_task(self, cl, stop_event):
       """
       This function runs in a separate thread.
       It waits for incoming messages from the server and prints them.
       """
       while not stop_event.is_set():
           try:
               # Use select to wait for data on the socket with a 1-second timeout
               # This allows the loop to check the stop_event every second
               ready_to_read, _, _ = select.select([self.sock], [], [], 1.0)
               # If the socket is ready, there's data to read
               if ready_to_read:
                   response = self.receive_data()
                   if response:
                       # --- Handle all ASYNCHRONOUS messages here ---
                       if response.startswith("P2P_MESSAGE_FROM"):
                           # Format from server: P2P_MESSAGE_FROM sender_username:message_text
                           try:
                               # Split only on the first colon
                               header, message = response.split(':', 1)
                               username = header.split()[1]  # Get username from "P2P_MESSAGE_FROM username"
                               # This is a small hack to print the message
                               # without mangling the user's current input line.
                               sys.stdout.write(f"\n[Message from {username}]: {message}\n")
                               sys.stdout.write("> ")  # Re-print the prompt
                               sys.stdout.flush()  # Ensure it appears
                           except Exception as e:
                               cl.error(f"Error parsing P2P message: {e}")
                       elif response.startswith("LIST_USERS_SUCCESS"):
                           # Handle the response from the 'ls' command
                           try:
                               users = response.split(maxsplit=1)[1]
                               sys.stdout.write(f"\n[Connected Users]: {users}\n")
                               sys.stdout.write("> ")  # Re-print the prompt
                               sys.stdout.flush()
                           except Exception as e:
                               cl.error(f"Error parsing user list: {e}")
                       # You could add other server "push" messages here
                       # elif response.startswith("GLOBAL_ANNOUNCEMENT"):
                       #    ...
           except Exception as e:
               if not stop_event.is_set():  # Don't log errors if we're just shutting down
                   cl.error(f"Error in listener thread: {e}")
       cl.log("Server listener thread shutting down.")


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
        if not client.suppress_output:
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

    def heartbeat_task(client, cl, stop_event):  # <-- Modified to accept stop_event
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
    # Pass stop_event as an argument
    heartbeat_thread = threading.Thread(target=heartbeat_task, daemon=True, args=(client, cl, stop_event))
    heartbeat_thread.start()

    # --- Start the new Server Listener Thread ---
    listener_thread = threading.Thread(target=server_listener_task, daemon=True, args=(client, cl, stop_event))
    listener_thread.start()

    cl.log("Game loop started. Type 'stats' to see your stats or 'quit' to exit.")

    try:
        while True:
            # This input() BLOCKS the main thread
            command = input("> ").strip().lower()

            target_usr = ""

            if command == 'quit':
                cl.log("Quitting...")
                break  # Exit the while loop

            elif command == 'stats':
                # ... (no change here)
                try:
                    stats_str = (
                        f"Current Stats - "
                        f"Sword: {client.player.inventory.sword.damage}, "
                        f"Shield: {client.player.inventory.shield.defense}, "
                        f"Slaying: {client.player.inventory.slaying_potion.strength}, "
                        f"Healing: {client.player.inventory.healing_potion.strength}"
                    )
                    cl.info(stats_str)
                except AttributeError as e:
                    cl.error(f"Error retrieving stats: {e}")

            elif command.startswith(f'msg:'):
                # ... (no change here)
                try:
                    message = command.split(':', 2)
                    target_usr = message[1]
                    user_msg = message[2]
                    client.send_data(f"P2P_MESSAGE {target_usr} {user_msg}")
                    cl.log(f"Sent message to {target_usr}.")
                except IndexError:
                    cl.error("Invalid message format. Use: msg:username:your_message")

            elif command.startswith('ls'):
                # --- THIS IS THE KEY CHANGE ---
                # We no longer wait for a response here.
                # We just send the request. The listener thread will get the answer.
                try:
                    client.send_data(f"LIST_USERS NONE NONE")
                    cl.log("Requesting user list... (response will appear)")
                except Exception as e:
                    cl.error(f"Error sending 'ls' request: {e}")

            elif command.startswith('enable_heartbeat'):
                # ... (no change here)
                client.suppress_output = False
                cl.log("Heartbeat output enabled.")
            elif command.startswith('disable_heartbeat'):
                # ... (no change here)
                client.suppress_output = True
                cl.log("Heartbeat output disabled.")

            elif command.startswith('clr'):
                # ... (no change here)
                if sys.platform.startswith('win'):
                    _ = os.system('cls')
                else:
                    _ = os.system('clear')
                cl.log("Console cleared.")

            elif command.startswith('help'):
                # ... (no change here)
                print("\n--- Available Commands ---")
                print("stats                 - Show current player stats")
                print("msg:username:message  - Send a message to another user")
                print("ls                    - List connected users")
                print("enable_heartbeat      - Enable heartbeat output")
                print("disable_heartbeat     - Disable heartbeat output")
                print("clr                   - Clear the console")
                print("help                  - Show this help message")
                print("quit                  - Exit the game\n")

            else:
                cl.warning(f"Unknown command: '{command}'. Type help for a list of commands.")

    except KeyboardInterrupt:
        cl.log("\nCaught Ctrl+C. Shutting down game loop.")

    finally:
        # Signal BOTH threads to stop
        cl.log("Stopping threads...")
        stop_event.set()

        # Wait for both threads to finish (this is the "join")
        heartbeat_thread.join(timeout=2)
        listener_thread.join(timeout=2)  # <-- JOIN THE NEW THREAD

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