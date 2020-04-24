class Inventory:
    def __init__(self, id, items=None):
        self.id = id

        if items is None:
            items = list()
        self.items = items

    def __iter__(self):
        return self.items.__iter__()

    def size(self):
        return len(self.items)

    def get_inventory_id(self):
        return self.id

    async def add_object_to_inventory(self, obj, number, weight_per_obj):
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
        return weight

    async def remove(self, obj, amount):
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


class InventoryEntry:
    def __init__(self, obj, number, weight_per_obj):
        self.obj = obj
        self.number = number
        self.weight_per_obj = weight_per_obj

    def __str__(self):
        return str(self.number) + " " + self.obj + ("s each weighing " if self.number != 1 else " weighing ") + str(self.weight_per_obj) + " pounds for a total of " + str(self.number * self.weight_per_obj) + " pounds."
