"""
TODO: Convert all of this to a handbook data pack - that way we could convert anything
"""
import math

gold_pieces = "gold"
silver_pieces = "silver"
copper_pieces = "copper"
gold_to_silver_conversion = silver_to_gold_conversion = silver_to_copper_conversion = copper_to_silver_conversion = 10


class CurrencyError(Exception):
    def __init__(self, detail):
        self.detail = detail


def subtract(purse, type, amount):
    if type == gold_pieces:
        if amount < purse[gold_pieces]:
            purse[gold_pieces] -= amount

        else:
            amount -= purse[gold_pieces]
            purse[gold_pieces] = 0
            amount *= gold_to_silver_conversion
            subtract(purse, silver_pieces, amount)

    elif type == silver_pieces:
        if amount < purse[silver_pieces]:
            purse[silver_pieces] -= amount

        elif purse[gold_pieces] != 0:
            amount -= purse[silver_pieces]
            purse[silver_pieces] = 0
            amount_to_convert = int(math.ceil(float(amount) / float(silver_to_gold_conversion)))
            purse[silver_pieces] += (amount_to_convert * 10) - amount
            subtract(purse, gold_pieces, amount_to_convert)

        elif purse[copper_pieces] != 0:
            amount -= purse[silver_pieces]
            purse[silver_pieces] = 0
            amount *= silver_to_copper_conversion
            subtract(purse, copper_pieces, amount)

        else:
            raise CurrencyError("Not enough money")

    elif type == copper_pieces:
        if amount < purse[copper_pieces]:
            purse[copper_pieces] -= amount

        else:
            amount -= purse[copper_pieces]
            purse[copper_pieces] = 0
            amount_to_convert = int(math.ceil(float(amount) / float(copper_to_silver_conversion)))
            purse[copper_pieces] += (amount_to_convert * 10) - amount
            subtract(purse, silver_pieces, amount_to_convert)

    return purse
    p
