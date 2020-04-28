import math
from collections import OrderedDict

import utils.currency as currency_handler


"""
TODO: Currency weight
TODO: Ordering of currency when iterating through it
"""


class Inventory:
    def __init__(self, id, items=None, currency=None):
        self.id = id

        if items is None:
            items = list()
        self.items = items

        if currency is None:
            currency = OrderedDict()
            currency.update({currency_handler.gold_pieces: 0})
            currency.update({currency_handler.silver_pieces: 0})
            currency.update({currency_handler.copper_pieces: 0})
        self.currency = currency

    def __iter__(self):
        return self.items.__iter__()

    def size(self):
        return len(self.items)

    def get_inventory_id(self):
        return self.id

    def get_currency(self):
        return self.currency

    async def add_object_to_inventory(self, obj, number, weight_per_obj):
        if obj in self.currency:
            self.currency[obj] += number
            return str(number) + " " + obj

        for item in self.items:
            if obj == item.obj:
                item.number += number
                return item

        item = InventoryEntry(obj, number, weight_per_obj)
        self.items.append(item)
        return item

    async def get_total_weight(self):
        weight = 0
        for item in self.items:
            weight += (item.number * item.weight_per_obj)

        # Capture the currency weight
        total_currency = 0
        for currency, amount in self.currency.items():
            total_currency += amount
        weight += math.ceil(float(total_currency) / 50.0)

        return weight

    async def remove(self, obj, amount):
        if obj in self.currency:
            return self.remove_currency(obj, amount)

        item_to_remove = None
        for item in self.items:
            if obj == item.obj:
                if item.number >= amount:
                    item.number -= amount

                    if item.number == 0:
                        item_to_remove = item
                        break
                    else:
                        return True

        if item_to_remove:
            self.items.remove(item_to_remove)
            return True

        return False

    def remove_currency(self, obj, amount):
        if self.currency[obj] >= amount:
            self.currency -= amount
            return True

        else:
            try:
                new_currency = currency_handler.subtract(self.currency.copy(), obj, amount)
            except currency_handler.CurrencyError:
                return False

            self.currency = new_currency
            return True

    def clear(self):
        self.items = dict()
        self.currency = {currency_handler.gold_pieces: 0, currency_handler.silver_pieces: 0, currency_handler.copper_pieces: 0}


class InventoryEntry:
    def __init__(self, obj, number, weight_per_obj):
        self.obj = obj
        self.number = number
        self.weight_per_obj = weight_per_obj

    def __str__(self):
        return str(self.number) + " " + self.obj + ("s each weighing " if self.number != 1 else " weighing ") + str(self.weight_per_obj) + " pounds for a total of " + str(self.number * self.weight_per_obj) + " pounds."
