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


def print_async_message(message):
    """
    Helper function to print a message from a thread
    without mangling the user's current input line.
    """
    sys.stdout.write(f"\n{message}\n")
    sys.stdout.write("> ")  # Re-print the prompt
    sys.stdout.flush()  # Ensure it appears


def server_listener_task(self, client, cl, stop_event):
    """
    This function runs in a separate thread.
    It waits for incoming messages from the server and prints them.
    """
    while not stop_event.is_set():
        try:
            # Use select to wait for data on the socket with a 1-second timeout
            ready_to_read, _, _ = select.select([self.sock], [], [], 1.0)

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
                            print_async_message(f"[Message from {username}]: {message}")
                        except Exception as e:
                            cl.error(f"Error parsing P2P message: {e}")

                    elif response.startswith("LIST_USERS_SUCCESS"):
                        # Handle the response from the 'ls' command
                        try:
                            users = response.split(maxsplit=1)[1]
                            print_async_message(f"[Connected Users]: {users}")
                        except Exception as e:
                            cl.error(f"Error parsing user list: {e}")

                    # --- REPLACED PROCESS_DAMAGE WITH BATTLE_RESULT ---
                    elif response.startswith("BATTLE_RESULT"):
                        # Format: BATTLE_RESULT [WIN|LOSE]:{message_log}
                        try:
                            parts = response.split(':', 1)
                            outcome_msg = parts[1]

                            # Also update local player lives if we can parse it
                            if "You were defeated" in outcome_msg:
                                client.player.lives = 0  # Or fetch from server

                            print_async_message(f"[BATTLE]: {outcome_msg}")

                        except Exception as e:
                            cl.error(f"Error processing battle result: {e}")

                    elif response.startswith("ERROR"):
                        # Generic error from server
                        try:
                            error_msg = response.split(maxsplit=1)[1]
                            print_async_message(f"[SERVER ERROR]: {error_msg}")
                        except Exception as e:
                            cl.error(f"Error parsing server error: {e}")


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
            password_plain = getpass.getpass("Password: ").strip()

            if not username or not password_plain:
                cl.error("Username and password cannot be empty.")
                continue  # Ask for choice again

            password_hashed = player.hash_password(password_plain)

            action = "LOGIN" if choice == '1' else "SIGNUP"

            # --- This is the ONLY place we send username/password ---
            client.send_data(f"{action} {username} {password_hashed}")

            response = client.receive_data()

            if handle_login_response(response, cl):
                # We don't need to store these anymore, but we can
                # for the 'stats' command.
                ret_info.append(username)
                return True  # Login was successful!

        else:
            cl.warning("Invalid choice. Please enter 1, 2, or 3.")


def get_stat_input(prompt, stat_min, stat_max, cl):
    """Helper function to get a single valid integer stat from the user."""
    # (No changes from original)
    while True:
        try:
            value_str = input(prompt)
            value_int = int(value_str)
            if value_int < 0:
                cl.warning("Stat value must be non-negative.")
                continue
            if value_int > stat_max:
                cl.warning(f"Stat value cannot exceed {stat_max}.")
                continue
            if value_int < stat_min:
                cl.warning(f"Stat value must be at least {stat_min}.")
                continue
            return value_int
        except ValueError:
            cl.error("Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            cl.warning("\nStat selection cancelled.")
            return None


def battle(client, target_usr, cl):
    """
    Sends a fight request to another user.
    Now only sends the command, not username/password.
    """
    try:
        # --- SIMPLIFIED: No credentials needed ---
        client.send_data(f"ATTACK {target_usr}")
        cl.log(f"Sent fight request to {target_usr}.")
    except Exception as e:
        cl.error(f"Error sending fight request: {e}")


def run_stats_selector_cli(cl):
    """
    Prompts the user to enter their stats via the command line.
    (No changes from original)
    """
    cl.log("This appears to be your first login. Please set your stats.")
    cl.log("Distribute a total of 10 points among the following stats:")
    cl.log(" - Sword Damage - [0-3]")
    cl.log(" - Shield Defense - [0-3]")
    cl.log(" - Slaying Strength - [0-3]")
    cl.log(" - Healing Strength - [0-3]")

    print("--- Stat Selection ---")

    POINT_BANK = 10

    try:
        sword_damage = get_stat_input("Enter Sword Damage: ", 0, min(POINT_BANK, 3), cl)
        if sword_damage is None: return None
        POINT_BANK -= sword_damage

        shield_defense = get_stat_input("Enter Shield Defense: ", 0, min(POINT_BANK, 3), cl)
        if shield_defense is None: return None
        POINT_BANK -= shield_defense

        slaying_strength = get_stat_input("Enter Slaying Strength: ", 0, min(POINT_BANK, 3), cl)
        if slaying_strength is None: return None
        POINT_BANK -= slaying_strength

        healing_strength = get_stat_input("Enter Healing Strength: ", 0, min(POINT_BANK, 3), cl)
        if healing_strength is None: return None
        POINT_BANK -= healing_strength

        if POINT_BANK != 0:
            cl.warning(f"You have {POINT_BANK} unallocated points. Please allocate exactly 10 points.")
            return run_stats_selector_cli(cl)

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
    --- SIMPLIFIED: No credentials needed ---
    """
    try:
        client.send_data(f"HEARTBEAT")
        if not client.suppress_output:
            cl.info("Sent ALIVE ping to server.")
    except Exception as e:
        cl.error(f"Error sending ALIVE ping: {e}")


def run_game_loop_cli(client, cl):
    """
    Runs the main game loop after the player is logged in.
    """
    stop_event = threading.Event()

    def heartbeat_task(client, cl, stop_event):
        """This function will run in a separate thread."""
        while not stop_event.is_set():
            client_heartbeat(client, cl)
            for _ in range(5):
                if stop_event.is_set():
                    break
                time.sleep(1)

    heartbeat_thread = threading.Thread(target=heartbeat_task, daemon=True, args=(client, cl, stop_event))
    heartbeat_thread.start()

    listener_thread = threading.Thread(target=server_listener_task, daemon=True, args=(client, client, cl, stop_event))
    listener_thread.start()

    cl.log("Game loop started. Type 'stats' to see your stats or 'quit' to exit.")

    try:
        while True:
            command = input("> ").strip().lower()

            if command == 'quit':
                cl.log("Quitting...")
                break  # Exit the while loop

            elif command == 'stats':
                # This just prints the locally stored stats
                try:
                    stats_str = (
                        f"Current Stats - "
                        f"Sword: {client.player.inventory.sword.damage}, "
                        f"Shield: {client.player.inventory.shield.defense}, "
                        f"Slaying: {client.player.inventory.slaying_potion.strength}, "
                        f"Healing: {client.player.inventory.healing_potion.strength}"
                        f" Lives: {client.player.lives}"
                    )
                    cl.info(stats_str)
                except AttributeError as e:
                    cl.error(f"Error retrieving stats: {e}")

            elif command.startswith(f'msg:'):
                try:
                    # Format: msg:username:your_message
                    parts = command.split(':', 2)
                    target_usr = parts[1]
                    user_msg = parts[2]

                    # --- SIMPLIFIED: No credentials needed ---
                    client.send_data(f"P2P_MESSAGE {target_usr} {user_msg}")
                    cl.log(f"Sent message to {target_usr}.")
                except IndexError:
                    cl.error("Invalid message format. Use: msg:username:your_message")

            elif command.startswith('ls'):
                try:
                    # --- SIMPLIFIED: No credentials needed ---
                    client.send_data(f"LIST_USERS")
                    cl.log("Requesting user list... (response will appear)")
                except Exception as e:
                    cl.error(f"Error sending 'ls' request: {e}")

            elif command.startswith('enable_heartbeat'):
                client.suppress_output = False
                cl.log("Heartbeat output enabled.")
            elif command.startswith('disable_heartbeat'):
                client.suppress_output = True
                cl.log("Heartbeat output disabled.")

            elif command.startswith('clr'):
                if sys.platform.startswith('win'):
                    _ = os.system('cls')
                else:
                    _ = os.system('clear')
                cl.log("Console cleared.")

            elif command.startswith('attack:'):
                try:
                    parts = command.split(':', 1)
                    target_usr = parts[1]
                    if not target_usr:
                        raise IndexError
                    battle(client, target_usr, cl)  # battle() is now simplified
                except IndexError:
                    cl.error("Invalid attack format. Use: attack:username")

            elif command.startswith('help'):
                # ... (no change here)
                print("\n--- Available Commands ---")
                print("stats                 - Show current player stats")
                print("msg:username:message  - Send a message to another user")
                print("ls                    - List connected users")
                print("attack:username      - Attack another user")
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
        cl.log("Stopping threads...")
        stop_event.set()

        heartbeat_thread.join(timeout=2)
        listener_thread.join(timeout=2)

        cl.log("Game loop ended.")


def main():
    """Main function to initialize and run the client."""
    client = Client('localhost', 9999)
    cl = client.cl

    try:
        # Step 1: Run the login screen.
        result = []  # Will store [username]
        login_successful = run_login_cli(client, result, cl)

        if not login_successful:
            cl.warning("User quit at login. Exiting.")
            client.close()
            sys.exit(0)

        cl.log("Moving to game setup...")

        cl.info(f"Requesting login count...")
        # --- SIMPLIFIED: No credentials needed ---
        client.send_data(f"LOGINS")

        while True:
            response = client.receive_data()
            if response is None:
                cl.error("No response from server for LOGINS request. Retrying...")
                client.send_data(f"LOGINS")
                time.sleep(1)
                continue

            login_count = handle_login_counter(response, cl)
            if login_count == -1:
                cl.error("Failed to parse login count. Retrying...")
                client.send_data(f"LOGINS")
                time.sleep(1)
                continue

            # If first login, run stat selector
            if login_count <= 1:
                stats_result = run_stats_selector_cli(cl)
                if stats_result is None:
                    cl.error(f"User quit during stats selection. Exiting.")
                    return  # Finally block will handle cleanup

                sword, shield, slaying, healing = stats_result

                # --- SIMPLIFIED: No credentials needed ---
                client.send_data(
                    f"SET_STATS:{sword},{shield},{slaying},{healing}")

                stats_response = client.receive_data()
                if stats_response and stats_response.startswith("SET_STATS_SUCCESS"):
                    cl.log(f"Stats set successfully on server.")
                    break  # Break from the while loop
                else:
                    cl.error(f"Failed to set stats on server. Retrying stat selection...")
            else:
                cl.log("Existing user. Skipping stat selection.")
                break  # Break from the while loop

        # Request player stats from server
        cl.log("Requesting player stats from server...")

        # --- SIMPLIFIED: No credentials needed ---
        client.send_data(f"GET_STATS")

        stat_fail_count = 0

        while True:
            stats_response = client.receive_data()
            if stats_response and stats_response.startswith("GET_STATS_SUCCESS"):
                try:
                    stats_data = stats_response.split(maxsplit=1)[1]
                    sword_damage, shield_defense, slaying_strength, healing_strength, lives = map(int,
                                                                                                  stats_data.split(','))
                    # Store stats locally
                    client.player.init_stats(sword_damage, shield_defense, slaying_strength, healing_strength)
                    client.player.lives = lives
                    cl.log(f"Received player stats from server: {stats_data}")
                    break  # Success
                except (IndexError, ValueError) as e:
                    cl.error(f"Error parsing player stats from server response: {e}")
            else:
                cl.error(f"Failed to receive player stats from server. Response: {stats_response}. Retrying...")
                if stat_fail_count >= 3:
                    cl.error("Multiple failures receiving stats. Re-entering stat selection.")
                    stats_result = run_stats_selector_cli(cl)
                    if stats_result is None:
                        cl.error(f"User quit during stats selection. Exiting.")
                        return  # Finally block will handle cleanup
                    sword, shield, slaying, healing = stats_result
                    client.send_data(
                        f"SET_STATS:{sword},{shield},{slaying},{healing}")
                    stat_fail_count = 0  # Reset fail count after re-setting stats

                stat_fail_count += 1

                client.send_data(f"GET_STATS")
                time.sleep(2)  # Wait before retrying

        # Run the main interactive game loop
        run_game_loop_cli(client, cl)

    except KeyboardInterrupt:
        cl.warning("\nShutting down client (KeyboardInterrupt).")
    finally:
        cl.warning("Client connection closed.")
        client.close()


if __name__ == "__main__":
    main()