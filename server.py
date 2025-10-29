import pygame, json, os, player
import socket
from logger import ServerLogger

class Server:
    # --- Server class ---
    def __init__(self, host='localhost', port=9999):
        # The Server class now creates and owns the logger instance
        self.sl = ServerLogger()

        self.server_address = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(self.server_address)
        self.players = {}  # This is the persistent DB
        self.active_players = {}  # This stores in-memory player objects
        self.server_db_path = "server_db.json"
        self.sl.info(f"Server started at {host}:{port}")  # Use self.sl

    def receive_data(self):
        try:
            data, client_address = self.sock.recvfrom(4096)
            return data.decode(), client_address
        except Exception as e:
            self.sl.error(f"Error receiving data: {e}")  # Use self.sl
            return None, None

    def send_data(self, data, client_address):
        try:
            message = data.encode()
            self.sock.sendto(message, client_address)
        except Exception as e:
            self.sl.error(f"Error sending data: {e}")  # Use self.sl

    def load_db(self):
        try:
            if os.path.exists(self.server_db_path):
                with open(self.server_db_path, 'r') as f:
                    self.players = json.load(f)
                self.sl.info("Server database loaded.")  # Use self.sl
            else:
                self.sl.warning("No existing server database found. Starting fresh.")  # Use self.sl
        except Exception as e:
            self.sl.error(f"Error loading server database: {e}")  # Use self.sl
            self.players = {}

    def add_player_to_db(self, player_id, Player):
        self.players[player_id] = {
            "username": Player.profile.username,
            "password": Player.profile.password,
            "logins": 0
        }
        with open(self.server_db_path, 'w') as f:
            json.dump(self.players, f, indent=4)  # Added indent for readability

    def set_player_stats_in_db(self, player_id, stats):
        # stat_type = ["sword_level", "shield_level", "slaying_potion_level", "healing_potion_level"]
        if player_id in self.players:
            self.players[player_id]["stats"] = stats
            with open(self.server_db_path, 'w') as f:
                json.dump(self.players, f, indent=4)  # Save updated DB

    def get_player_stats_in_db(self, player_id):
        if player_id in self.players and "stats" in self.players[player_id]:
            return self.players[player_id]["stats"]
        return None

    def check_db(self, username, password):
        for pid, pdata in self.players.items():
            if pdata["username"] == username and pdata["password"] == password:
                return pid
        return None

    def get_num_of_logins(self, player_id):
        if player_id in self.players:
            return self.players[player_id]["logins"]
        return 0

    def check_username_exists(self, username):
        for pid, pdata in self.players.items():
            if pdata["username"] == username:
                return True
        return False

    def close(self):
        self.sock.close()


# --- End of Server class ---


# Now takes 'sl' as a parameter
def handle_client_request(pServer, data, client_address, sl):
    """
    Parses and responds to a single client request.
    """
    parts = data.split()
    if len(parts) < 3:
        sl.warning(f"Received malformed data from {client_address}: {data}")
        return  # Ignore malformed commands

    command = parts[0]
    username = parts[1]
    password = parts[2]

    # --- Handle LOGIN Command ---
    if command == "LOGIN":
        player_id = pServer.check_db(username, password)
        if player_id:
            # User exists and password is correct
            sl.info(f"Player {username} (ID: {player_id}) logged in from {client_address}")

            # Create a new player object for them in memory
            new_player = player.Player()
            new_player.create_profile(username, password)

            # TODO: Load their real data (inventory, stats, etc.)
            # e.g., new_player.load_inventory(f"{username}_inventory.json")

            pServer.active_players[client_address] = new_player
            pServer.send_data(f"LOGIN_SUCCESS {player_id}", client_address)

            # Increment their login count
            pServer.players[player_id]["logins"] += 1
            try:
                with open(pServer.server_db_path, 'w') as f:
                    json.dump(pServer.players, f, indent=4)  # Save updated DB
            except Exception as e:
                sl.error(f"Error updating server database: {e}")

        else:
            # User not found or wrong password
            sl.info(f"Failed login attempt for {username} from {client_address}")
            pServer.send_data("LOGIN_FAIL Invalid credentials", client_address)

    # --- Handle SIGNUP Command ---
    elif command == "SIGNUP":
        if pServer.check_username_exists(username):
            # Check if username is already taken
            sl.info(f"Failed signup, username {username} already exists.")
            pServer.send_data("SIGNUP_FAIL Username taken", client_address)
        else:
            # Create new player
            new_player = player.Player()
            new_player.create_profile(username, password)

            # Create a new ID for them (simple increment)
            new_player_id = str(len(pServer.players) + 1)

            # Add them to the persistent database
            pServer.add_player_to_db(new_player_id, new_player)

            # TODO: Create their default inventory file
            # new_player.init_stats(10, 5, 15, 20) # Example stats
            # new_player.save_inventory(f"{username}_inventory.json")

            sl.info(f"New player {username} signed up with ID {new_player_id}")
            pServer.send_data(f"SIGNUP_SUCCESS {new_player_id}", client_address)

    elif command == "LOGINS":
        player_id = pServer.check_db(username, password)
        if player_id:
            sl.info(f"Received login count request from {username} (ID: {player_id})")
            num_logins = pServer.get_num_of_logins(player_id)
            pServer.send_data(f"LOGINS_COUNT {num_logins}", client_address)
        else:
            pServer.send_data("LOGINS_FAIL Invalid credentials", client_address)

    elif command.startswith("SET_STATS"):
        player_id = pServer.check_db(username, password)
        if player_id:
            # Split SET_STATS:value1,value2,...
            stats_data = command[len("SET_STATS:"):].strip()
            stats = stats_data.split(",")
            sword_damage = stats[0]
            shield_defense = stats[1]
            slaying_potion_strength = stats[2]
            healing_potion_strength = stats[3]
            stats_dict = {
                "sword_damage": sword_damage,
                "shield_defense": shield_defense,
                "slaying_potion_strength": slaying_potion_strength,
                "healing_potion_strength": healing_potion_strength
            }
            pServer.set_player_stats_in_db(player_id, stats_dict)
            sl.info(f"Updated stats for player {username} (ID: {player_id})")
            pServer.send_data("SET_STATS_SUCCESS", client_address)

        else:
            pServer.send_data("SET_STATS_FAIL Invalid credentials", client_address)

    else:
        sl.warning(f"Received unknown command from {client_address}: {command}")

def send_alive_ping(pServer, client_address, sl):
    """
    Sends an ALIVE ping to the specified client.
    """
    try:
        pServer.send_data("ALIVE", client_address)
        sl.info(f"Sent ALIVE ping to {client_address}")
    except Exception as e:
        sl.error(f"Error sending ALIVE ping to {client_address}: {e}")

def check_client_timeout(pServer, client_address, last_ping_time, timeout_duration, sl):
    """
    Checks if the client has timed out based on the last ping time.
    """
    current_time = pygame.time.get_ticks()
    if current_time - last_ping_time > timeout_duration:
        sl.warning(f"Client {client_address} has timed out.")
        # Handle timeout (e.g., remove from active players)
        if client_address in pServer.active_players:
            del pServer.active_players[client_address]
        return True
    return False

# Now takes 'sl' as a parameter
def run_server_loop(pServer, sl):
    """
    Main loop to listen for and handle client data.
    """
    try:
        while True:
            data, client_address = pServer.receive_data()
            if data:
                # Pass the logger instance down to the handler
                handle_client_request(pServer, data, client_address, sl)


    except KeyboardInterrupt:
        sl.info("\nShutting down server (KeyboardInterrupt).")
    finally:
        sl.info("Closing server socket.")
        pServer.close()


if __name__ == "__main__":
    # 1. Initialize the server object (this also creates server.sl)
    server = Server()

    # 2. Load persistent data (uses server.sl internally)
    server.load_db()

    # 3. Run the main loop, passing the server's logger instance
    run_server_loop(server, server.sl)