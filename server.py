import json, os, player
import socket, time
from logger import ServerLogger


class Server:
    # --- Server class (no changes) ---
    def __init__(self, host='localhost', port=9999):
        self.sl = ServerLogger()
        self.server_address = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(1.0)  # 1 second timeout for recvfrom
        self.sock.bind(self.server_address)
        self.players = {}  # This is the persistent DB
        self.active_players = {}  # This stores in-memory player objects
        self.server_db_path = "server_db.json"
        self.sl.info(f"Server started at {host}:{port}")

    def receive_data(self):
        try:
            data, client_address = self.sock.recvfrom(4096)
            return data.decode(), client_address
        except socket.timeout:
            return "TIMEOUT", None
        except Exception as e:
            self.sl.error(f"Error receiving data: {e}")
            return None, None

    def send_data(self, data, client_address):
        try:
            message = data.encode()
            self.sock.sendto(message, client_address)
        except Exception as e:
            self.sl.error(f"Error sending data: {e}")

    def load_db(self):
        try:
            if os.path.exists(self.server_db_path):
                with open(self.server_db_path, 'r') as f:
                    self.players = json.load(f)
                self.sl.info("Server database loaded.")
            else:
                self.sl.warning("No existing server database found. Starting fresh.")
        except Exception as e:
            self.sl.error(f"Error loading server database: {e}")
            self.players = {}

    def add_player_to_db(self, player_id, Player):
        self.players[player_id] = {
            "username": Player.profile.username,
            "password": Player.profile.password,
            "logins": 0
        }
        with open(self.server_db_path, 'w') as f:
            json.dump(self.players, f, indent=4)

    def set_player_stats_in_db(self, player_id, stats):
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
            username = self.active_players[address].get("player", None)
            if username:
                username = username.profile.username
            else:
                username = "Unknown"
            self.sl.warning(f"Client {username} at {address} has timed out and will be removed.")
            del self.active_players[address]


# --- End of Server class ---


# --- REFACTORED to use session-based authentication ---
def handle_client_request(pServer, data, client_address, sl):
    """
    Parses and responds to a single client request.
    """
    sl.info(f"Received data from {client_address}: {data}")
    parts = data.split()
    command = parts[0]

    # --- Handle non-authenticated commands first ---
    if command == "LOGIN":
        try:
            username = parts[1]
            password = parts[2]
            player_id = pServer.check_db(username, password)
            if player_id:
                sl.info(f"Player {username} (ID: {player_id}) logged in from {client_address}")

                new_player = player.Player()
                new_player.create_profile(username, password)

                stats = pServer.get_player_stats_in_db(player_id)
                if stats:
                    new_player.init_stats(
                        int(stats["sword_damage"]),
                        int(stats["shield_defense"]),
                        int(stats["slaying_potion_strength"]),
                        int(stats["healing_potion_strength"])
                    )

                # --- THIS IS THE KEY: Store the session ---
                pServer.active_players[client_address] = {
                    "player": new_player,
                    "last_ping": time.time(),
                    "player_id": player_id  # Store the DB key
                }

                pServer.send_data(f"LOGIN_SUCCESS {player_id}", client_address)

                pServer.players[player_id]["logins"] += 1
                try:
                    with open(pServer.server_db_path, 'w') as f:
                        json.dump(pServer.players, f, indent=4)
                except Exception as e:
                    sl.error(f"Error updating server database: {e}")

            else:
                sl.info(f"Failed login attempt for {username} from {client_address}")
                pServer.send_data("LOGIN_FAIL Invalid credentials", client_address)
        except IndexError:
            sl.warning(f"Malformed LOGIN from {client_address}")
        return  # --- End of LOGIN ---

    elif command == "SIGNUP":
        try:
            username = parts[1]
            password = parts[2]
            if pServer.check_username_exists(username):
                sl.info(f"Failed signup, username {username} already exists.")
                pServer.send_data("SIGNUP_FAIL Username taken", client_address)
            else:
                new_player = player.Player()
                new_player.create_profile(username, password)
                new_player_id = str(len(pServer.players) + 1)
                pServer.add_player_to_db(new_player_id, new_player)
                sl.info(f"New player {username} signed up with ID {new_player_id}")
                pServer.send_data(f"SIGNUP_SUCCESS {new_player_id}", client_address)
        except IndexError:
            sl.warning(f"Malformed SIGNUP from {client_address}")
        return  # --- End of SIGNUP ---

    # --- All commands below this point REQUIRE authentication ---

    if client_address not in pServer.active_players:
        sl.warning(f"Unauthenticated request from {client_address}: {data}")
        pServer.send_data("ERROR Not logged in", client_address)
        return

    # If we get here, user is logged in. Get their session data.
    active_data = pServer.active_players[client_address]
    player_obj = active_data["player"]
    player_id = active_data["player_id"]
    username = player_obj.profile.username

    # Update their ping time
    active_data['last_ping'] = time.time()

    # --- Handle Authenticated Commands ---
    if command == "LOGINS":
        sl.info(f"Received login count request from {username} (ID: {player_id})")
        num_logins = pServer.get_num_of_logins(player_id)
        pServer.send_data(f"LOGINS_COUNT {num_logins}", client_address)

    elif command.startswith("SET_STATS"):
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
            "healing_potion_strength": healing_potion_strength,
            "health": 2  # Default lives
        }

        pServer.set_player_stats_in_db(player_id, stats_dict)
        sl.info(f"Updated stats for player {username} (ID: {player_id})")
        pServer.send_data("SET_STATS_SUCCESS", client_address)

    elif command.startswith("GET_STATS"):
        stats = pServer.get_player_stats_in_db(player_id)
        if stats:
            stats_str = f"{stats['sword_damage']},{stats['shield_defense']}," + \
                        f"{stats['slaying_potion_strength']},{stats['healing_potion_strength']},{stats['health']}"
            pServer.send_data(f"GET_STATS_SUCCESS {stats_str}", client_address)
            sl.info(f"Sent stats to player {username} (ID: {player_id})")
        else:
            pServer.send_data("GET_STATS_FAIL No stats found", client_address)

    elif command == "P2P_MESSAGE":
        # Data format: P2P_MESSAGE target_username message_text...
        try:
            parts = data.split(maxsplit=2)
            target_username = parts[1]
            message_text = parts[2]

            sender_username = username  # From our session data

            target_address = None
            for addr, p_data in pServer.active_players.items():
                if p_data["player"].profile.username == target_username:
                    target_address = addr
                    break

            if target_address:
                pServer.send_data(f"P2P_MESSAGE_FROM {sender_username}:{message_text}", target_address)
                sl.info(f"Relayed message from {sender_username} to {target_username}")
            else:
                sl.warning(f"User {sender_username} tried to message non-existent user {target_username}")
                pServer.send_data(f"P2P_FAIL User '{target_username}' not online", client_address)
        except IndexError:
            sl.warning(f"Malformed P2P_MESSAGE from {client_address}")
            pServer.send_data(f"P2P_FAIL Invalid format. Use: msg:user:msg", client_address)

    elif command == "LIST_USERS":
        active_user_list = [
            p_data["player"].profile.username
            for p_data in pServer.active_players.values()
        ]
        user_string = ", ".join(active_user_list)
        pServer.send_data(f"LIST_USERS_SUCCESS {user_string}", client_address)
        sl.info(f"Sent user list to {client_address}")

    elif command.startswith("HEARTBEAT"):
        pass  # Already handled by the ping update at the top

    # --- REBUILT BATTLE LOGIC ---
    elif command.startswith("ATTACK"):
        # Format: ATTACK target_username

        # --- 1. Identify Attacker & Target ---
        attacker_address = client_address
        attacker_id = player_id
        attacker_username = username

        try:
            target_username = parts[1]
        except IndexError:
            sl.warning(f"Malformed ATTACK from {attacker_address}")
            pServer.send_data("ATTACK_FAIL Invalid command. Use: attack:username", attacker_address)
            return

        if target_username == attacker_username:
            pServer.send_data("ATTACK_FAIL You cannot attack yourself.", attacker_address)
            return

        # Find target's address and Player ID
        target_address = None
        target_id = None
        for addr, p_data in pServer.active_players.items():
            if p_data["player"].profile.username == target_username:
                target_address = addr
                target_id = p_data["player_id"]
                break

        if not target_address or not target_id:
            pServer.send_data(f"ATTACK_FAIL User '{target_username}' not online", attacker_address)
            return

        # --- 2. Load Stats for Both Players ---
        a_stats_db = pServer.get_player_stats_in_db(attacker_id)
        t_stats_db = pServer.get_player_stats_in_db(target_id)

        if not a_stats_db or not t_stats_db:
            pServer.send_data("ATTACK_FAIL Could not load stats for battle", attacker_address)
            return

        # Load stats into "in-battle" variables
        a_sword = int(a_stats_db["sword_damage"])
        a_shield = int(a_stats_db["shield_defense"])
        a_lives = int(a_stats_db["health"])

        t_sword = int(t_stats_db["sword_damage"])
        t_shield = int(t_stats_db["shield_defense"])
        t_lives = int(t_stats_db["health"])

        if a_lives <= 0:
            pServer.send_data(f"ATTACK_FAIL You cannot fight, you have no lives left!", attacker_address)
            return
        if t_lives <= 0:
            pServer.send_data(f"ATTACK_FAIL {target_username} has no lives left to fight.", attacker_address)
            return

        sl.info(f"Battle started: {attacker_username} (Lives: {a_lives}) vs {target_username} (Lives: {t_lives})")

        # --- 3. Run the Battle Loop ---
        battle_log = []
        turn = "attacker"

        # Run for a max of 20 rounds to prevent weird infinite loops
        for _ in range(20):
            if a_lives <= 0 or t_lives <= 0:
                break  # Battle is over

            if turn == "attacker":
                damage = a_sword - t_shield
                if damage < 0: damage = 0
                t_lives -= damage
                battle_log.append(
                    f"{attacker_username} hits {target_username} for {damage} damage! ({t_lives} lives left)")
                turn = "target"
            else:
                damage = t_sword - a_shield
                if damage < 0: damage = 0
                a_lives -= damage
                battle_log.append(
                    f"{target_username} hits {attacker_username} for {damage} damage! ({a_lives} lives left)")
                turn = "attacker"

        # --- 4. Determine Winner and Send Results ---
        log_string = " | ".join(battle_log)

        if a_lives <= 0:
            # Attacker lost
            sl.info(f"Battle over: {target_username} defeated {attacker_username}")
            pServer.send_data(f"BATTLE_RESULT LOSE:You were defeated by {target_username}. Log: {log_string}",
                              attacker_address)
            pServer.send_data(f"BATTLE_RESULT WIN:You defeated {attacker_username}! Log: {log_string}", target_address)

            # Update DB
            a_stats_db["health"] = a_lives
            pServer.set_player_stats_in_db(attacker_id, a_stats_db)

        elif t_lives <= 0:
            # Target lost
            sl.info(f"Battle over: {attacker_username} defeated {target_username}")
            pServer.send_data(f"BATTLE_RESULT WIN:You defeated {target_username}! Log: {log_string}", attacker_address)
            pServer.send_data(f"BATTLE_RESULT LOSE:You were defeated by {attacker_username}. Log: {log_string}",
                              target_address)

            # Update DB
            t_stats_db["health"] = t_lives
            pServer.set_player_stats_in_db(target_id, t_stats_db)

        else:
            # It was a draw (max rounds hit)
            sl.info(f"Battle over: {attacker_username} and {target_username} drew.")
            msg = f"BATTLE_RESULT DRAW:The battle ended in a draw! {log_string}"
            pServer.send_data(msg, attacker_address)
            pServer.send_data(msg, target_address)
            # Optionally update health for both
            a_stats_db["health"] = a_lives
            t_stats_db["health"] = t_lives
            pServer.set_player_stats_in_db(attacker_id, a_stats_db)
            pServer.set_player_stats_in_db(target_id, t_stats_db)


def run_server_loop(pServer, maxPlayers, sl):
    """
    Main loop to listen for and handle client data.
    """
    try:
        while True:
            data, client_address = pServer.receive_data()

            if data == "TIMEOUT":
                pServer.check_for_timeouts()
                continue

            if data:
                handle_client_request(pServer, data, client_address, sl)

    except KeyboardInterrupt:
        sl.info("\nShutting down server (KeyboardInterrupt).")
    finally:
        sl.info("Closing server socket.")
        pServer.close()


if __name__ == "__main__":
    server = Server()
    server.load_db()
    run_server_loop(server, 8, server.sl)