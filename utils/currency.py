"""
TODO: Convert all of this to a handbook data pack - that way we could convert anything
"""


gold_pieces = "gold_pieces"
silver_pieces = "silver_pieces"
copper_pieces = "copper_pieces"
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
            amount = amount // silver_to_gold_conversion
            subtract(purse, gold_pieces, amount)

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
            amount = amount // copper_to_silver_conversion
            subtract(purse, silver_pieces, amount)

    return purse
