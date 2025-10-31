import json, os, player
import socket, time
from logger import ServerLogger


class Server:
    # --- Server class ---
    def __init__(self, host='localhost', port=9999):
        # The Server class now creates and owns the logger instance
        self.sl = ServerLogger()

        self.server_address = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(1.0)  # 1 second timeout for recvfrom
        self.sock.bind(self.server_address)
        self.players = {}  # This is the persistent DB
        self.active_players = {}  # This stores in-memory player objects
        self.server_db_path = "server_db.json"
        self.sl.info(f"Server started at {host}:{port}")  # Use self.sl

    def receive_data(self):
        try:
            data, client_address = self.sock.recvfrom(4096)
            return data.decode(), client_address
        except socket.timeout:
            return "TIMEOUT", None
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

    def check_for_timeouts(self):
        """
        Checks for timed-out clients and removes them from active players.
        """
        TIMEOUT_DURATION = 15
        inactive_clients = []

        for address, data in self.active_players.items():
            time_since_last_ping = time.time() - data['last_ping']
            if time_since_last_ping > TIMEOUT_DURATION:
                inactive_clients.append(address)

        for address in inactive_clients:
            self.sl.warning(f"Client {address} has timed out and will be removed.")
            del self.active_players[address]


# --- End of Server class ---


# Now takes 'sl' as a parameter
def handle_client_request(pServer, data, client_address, sl):
    """
    Parses and responds to a single client request.
    """

    if client_address in pServer.active_players:
        pServer.active_players[client_address]['last_ping'] = time.time()

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

            # Load their inventory and stats if available
            stats = pServer.get_player_stats_in_db(player_id)
            if stats:
                new_player.init_stats(
                    int(stats["sword_damage"]),
                    int(stats["shield_defense"]),
                    int(stats["slaying_potion_strength"]),
                    int(stats["healing_potion_strength"])
                )

            pServer.active_players[client_address] = {
                "player": new_player,
                "last_ping": time.time()
            }

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

    elif command.startswith("GET_STATS"):
        player_id = pServer.check_db(username, password)
        if player_id:
            stats = pServer.get_player_stats_in_db(player_id)
            if stats:
                stats_str = f"{stats['sword_damage']},{stats['shield_defense']}," + \
                            f"{stats['slaying_potion_strength']},{stats['healing_potion_strength']}"
                pServer.send_data(f"GET_STATS_SUCCESS {stats_str}", client_address)
                sl.info(f"Sent stats to player {username} (ID: {player_id})")
            else:
                pServer.send_data("GET_STATS_FAIL No stats found", client_address)
        else:
            pServer.send_data("GET_STATS_FAIL Invalid credentials", client_address)

    elif command.startswith("HEARTBEAT"):
        pass

    else:
        sl.warning(f"Received unknown command from {client_address}: {command}")


# Now takes 'sl' as a parameter
def run_server_loop(pServer, maxPlayers, sl):
    """
    Main loop to listen for and handle client data.
    """
    try:
        while True:
            data, client_address = pServer.receive_data()

            if data == "TIMEOUT":
                # Check for timed-out clients
                pServer.check_for_timeouts()
                continue

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
    run_server_loop(server, 8, server.sl)