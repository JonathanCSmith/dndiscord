from utils import math, dice


class Tenday:
    def __init__(self, roll, situational_modifiers):
        if roll == "":
            self.roll = dice.do_roll(1, 100)

        else:
            self.roll = math.clamp_incl(roll, 1, 100)

        if situational_modifiers == "":
            self.situational_modifier = 0
        else:
            self.situational_modifier = math.clamp_incl(situational_modifiers, 1, 100)

        self.dynamic_modifier = 0

    def set_dynamic_modifier(self, modifier):
        self.dynamic_modifier = modifier

    def add_to_dynamic_modififer(self, amount):
        self.dynamic_modifier += amount

    def subtract_from_dynamic_modifier(self, amount):
        self.dynamic_modifier -= amount

    def get_popularity(self):
        return math.clamp_incl(self.roll + self.situational_modifier + self.dynamic_modifier, 1, 100)
