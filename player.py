import json, os
from enum import Enum
import pygame

class Sword:
    def __init__(self, name, damage):
        self.name = name
        self.damage = damage

    def use(self, target):
        if type(target) == Player:
            target.health -= self.damage


class Shield:
    def __init__(self, name, defense):
        self.name = name
        self.defense = defense

    def use(self, target):
        if type(target) == Player:
            target.health += self.defense


class Potion:
    class Effect(Enum):
        SLAYING = "slaying"
        HEALING = "healing"

    def __init__(self, name, effect, strength=-1):
        self.name = name
        self.effect = effect
        self.strength = strength

    def use(self, target):
        if type(target) == Player:
            if self.effect == Potion.Effect.SLAYING:
                target.health -= self.strength
            elif self.effect == Potion.Effect.HEALING:
                target.health += self.strength


class Profile:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.avatar = None

    def load_avatar(self, avatar_path):
        # Select avatar image from the given path
        if os.path.exists(avatar_path):
            self.avatar = avatar_path
        else:
            raise FileNotFoundError("Avatar image not found.")


class Inventory:
    def __init__(self):
        self.sword = Sword("Basic Sword", -1)
        self.shield = Shield("Basic Shield", -1)
        self.slaying_potion = Potion("Slaying Potion", Potion.Effect.SLAYING, -1)
        self.healing_potion = Potion("Healing Potion", Potion.Effect.HEALING, -1)


class Player:
    def __init__(self):
        self.profile = None
        self.inventory = Inventory()
        self.lives = 2

    def create_profile(self, username, password):
        self.profile = Profile(username, password)


    def save_profile(self, filepath):
        if self.profile is None:
            raise ValueError("No profile to save.")
        data = {
            "username": self.profile.username,
            "password": self.profile.password,
            "avatar": self.profile.avatar
        }
        with open(filepath, 'w') as f:
            json.dump(data, f)


    def load_profile(self, filepath):
        if not os.path.exists(filepath):
            raise FileNotFoundError("Profile file not found.")
        with open(filepath, 'r') as f:
            data = json.load(f)
        self.profile = Profile(data["username"], data["password"])
        self.profile.avatar = data.get("avatar", None)


    def load_inventory(self, filepath):
        if not os.path.exists(filepath):
            raise FileNotFoundError("Inventory file not found.")
        with open(filepath, 'r') as f:
            data = json.load(f)
        sword_data = data.get("sword", {})
        shield_data = data.get("shield", {})
        slaying_potion_data = data.get("slaying_potion", {})
        healing_potion_data = data.get("healing_potion", {})

        self.inventory.sword = Sword(sword_data.get("name", "Basic Sword"), sword_data.get("damage", -1))
        self.inventory.shield = Shield(shield_data.get("name", "Basic Shield"), shield_data.get("defense", -1))
        self.inventory.slaying_potion = Potion(slaying_potion_data.get("name", "Slaying Potion"),
                                               Potion.Effect.SLAYING,
                                               slaying_potion_data.get("strength", -1))
        self.inventory.healing_potion = Potion(healing_potion_data.get("name", "Healing Potion"),
                                               Potion.Effect.HEALING,
                                               healing_potion_data.get("strength", -1))

    def save_inventory(self, filepath):
        data = {
            "sword": {
                "name": self.inventory.sword.name,
                "damage": self.inventory.sword.damage
            },
            "shield": {
                "name": self.inventory.shield.name,
                "defense": self.inventory.shield.defense
            },
            "slaying_potion": {
                "name": self.inventory.slaying_potion.name,
                "strength": self.inventory.slaying_potion.strength
            },
            "healing_potion": {
                "name": self.inventory.healing_potion.name,
                "strength": self.inventory.healing_potion.strength
            }
        }
        with open(filepath, 'w') as f:
            json.dump(data, f)


    def init_stats(self, sword_damage, shield_defense, slaying_strength, healing_strength):
        self.inventory.sword.damage = sword_damage
        self.inventory.shield.defense = shield_defense
        self.inventory.slaying_potion.strength = slaying_strength
        self.inventory.healing_potion.strength = healing_strength


def hash_password(password):
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()