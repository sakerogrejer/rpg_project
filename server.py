# In server.py
import pygame, json, os, player
import socket


class Server:
    # --- Server class (no changes) ---
    def __init__(self, host='localhost', port=9999):
        self.server_address = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(self.server_address)
        self.players = {}  # This is the persistent DB
        self.active_players = {}  # This stores in-memory player objects
        self.server_db_path = "server_db.json"
        print(f"Server started at {host}:{port}")

    def receive_data(self):
        try:
            data, client_address = self.sock.recvfrom(4096)
            return data.decode(), client_address
        except Exception as e:
            print(f"Server - Error receiving data: {e}")
            return None, None

    def send_data(self, data, client_address):
        try:
            message = data.encode()
            self.sock.sendto(message, client_address)
        except Exception as e:
            print(f"Server - Error sending data: {e}")

    def load_db(self):
        try:
            if os.path.exists(self.server_db_path):
                with open(self.server_db_path, 'r') as f:
                    self.players = json.load(f)
                print("Server database loaded.")
            else:
                print("No existing server database found. Starting fresh.")
        except Exception as e:
            print(f"Error loading server database: {e}")
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


def handle_client_request(server, data, client_address):
    """
    Parses and responds to a single client request.
    """
    parts = data.split()
    if len(parts) < 3:
        print(f"Server - Received malformed data from {client_address}: {data}")
        return  # Ignore malformed commands

    command = parts[0]
    username = parts[1]
    password = parts[2]

    # --- Handle LOGIN Command ---
    if command == "LOGIN":
        player_id = server.check_db(username, password)
        if player_id:
            # User exists and password is correct
            print(f"Player {username} (ID: {player_id}) logged in from {client_address}")

            # Create a new player object for them in memory
            new_player = player.Player()
            new_player.create_profile(username, password)

            # TODO: Load their real data (inventory, stats, etc.)
            # e.g., new_player.load_inventory(f"{username}_inventory.json")

            server.active_players[client_address] = new_player
            server.send_data(f"LOGIN_SUCCESS {player_id}", client_address)

            # Increment their login count
            server.players[player_id]["logins"] += 1
            try:
                with open(server.server_db_path, 'w') as f:
                    json.dump(server.players, f, indent=4)  # Save updated DB
            except Exception as e:
                print(f"Error updating server database: {e}")

        else:
            # User not found or wrong password
            print(f"Server - Failed login attempt for {username} from {client_address}")
            server.send_data("LOGIN_FAIL Invalid credentials", client_address)

    # --- Handle SIGNUP Command ---
    elif command == "SIGNUP":
        if server.check_username_exists(username):
            # Check if username is already taken
            print(f"Server - Failed signup, username {username} already exists.")
            server.send_data("SIGNUP_FAIL Username taken", client_address)
        else:
            # Create new player
            new_player = player.Player()
            new_player.create_profile(username, password)

            # Create a new ID for them (simple increment)
            new_player_id = str(len(server.players) + 1)

            # Add them to the persistent database
            server.add_player_to_db(new_player_id, new_player)

            # TODO: Create their default inventory file
            # new_player.init_stats(10, 5, 15, 20) # Example stats
            # new_player.save_inventory(f"{username}_inventory.json")

            print(f"Server - New player {username} signed up with ID {new_player_id}")
            server.send_data(f"SIGNUP_SUCCESS {new_player_id}", client_address)

    elif command == "LOGINS":
        player_id = server.check_db(username, password)
        if player_id:
            print(f"Server - Received login count request from {username} (ID: {player_id})")
            num_logins = server.get_num_of_logins(player_id)
            server.send_data(f"LOGINS_COUNT {num_logins}", client_address)
        else:
            server.send_data("LOGINS_FAIL Invalid credentials", client_address)

    elif command.startswith("SET_STATS"):
        player_id = server.check_db(username, password)
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
            server.set_player_stats_in_db(player_id, stats_dict)
            print(f"Server - Updated stats for player {username} (ID: {player_id})")
            server.send_data("SET_STATS_SUCCESS", client_address)

        else:
            server.send_data("SET_STATS_FAIL Invalid credentials", client_address)

    else:
        print(f"Server - Received unknown command from {client_address}: {command}")

def run_server_loop(server):
    """
    Main loop to listen for and handle client data.
    """
    try:
        while True:
            data, client_address = server.receive_data()
            if data:
                # Pass the data to the handler function
                handle_client_request(server, data, client_address)

    except KeyboardInterrupt:
        print("\nShutting down server (KeyboardInterrupt).")
    finally:
        print("Server - Closing server socket.")
        server.close()


if __name__ == "__main__":
    # 1. Initialize the server object
    server = Server()

    # 2. Load persistent data
    server.load_db()

    # 3. Run the main loop
    run_server_loop(server)