import os

from utils import data

"""
TODO: Tag Library? Would allow for inheritance but it seems ridiculously overcomplicated
TODO: We could turn the 'values' of prerequisites into an alias repository instead
"""


class Data:
    def __int__(self, name, prerequisites=None, provided=None):
        self.name = name

        if prerequisites is None:
            prerequisites = dict()
        elif not isinstance(prerequisites, dict):
            print("Prerequisites: " + str(prerequisites) + " are not valid for: " + name)
            prerequisites = dict()
        self.prerequisites = prerequisites

        if provided is None:
            provided = dict()
        elif not isinstance(provided, dict):
            print("Provided: " + str(provided) + " are not valid for: " + name)
            provided = dict()
        self.provided = provided

    def get_prerequisites(self):
        return self.prerequisites

    def get_provided(self):
        return self.provided

    def get_provided_value(self, keys):
        values = list()
        if isinstance(keys, list):
            for key in keys:
                if key in self.provided:
                    values.append(self.provided[key])

        elif keys in self.provided:
            values.append(self.provided[keys])

        return values


class Service(Data):
    maximum_services_tag = "maximum_services"

    def __init__(self, name, cost, sale, prerequisites=None, provided=None, service_maximum_tags=None, served=None):
        super().__int__(name, prerequisites=prerequisites, provided=provided)

        self.cost = cost
        self.sale = sale
        self.service_maximum_tags = self.name + "_" + Service.maximum_services_tag

    def get_maximum_of_service_offered_tags(self):
        return self.service_maximum_tags

    def get_served(self):
        return self.served


class Staff(Data):
    """
    TODO: Names, Service type transitions (i.e. upsell)? Staff common rooms? Staff limit the volume of sales
    """

    def __init__(self, name, cost, prerequisites=None, provided=None):
        super().__int__(name, prerequisites=prerequisites, provided=provided)

        self.cost = cost


class Upgrade(Data):
    def __init__(self, name, cost, provided=None, prerequisites=None):
        super().__int__(name, provided=provided, prerequisites=prerequisites)

        self.cost = cost


class Patron(Data):
    mean_occupancy_additive_tag = "average_attendance_addition"
    mean_occupancy_multiplier_tag = "average_attendance_multiplier"
    maximum_occupancy_limit_tag = "maximum_occupancy"

    def __init__(self, name, priority, consumed, mean_patron_occupancy_additive_tag=None,
                 mean_patron_occupancy_multiplier_tag=None, maximum_patron_occupancy_limit_tag=None, prerequisites=None,
                 provided=None):
        super().__int__(name, prerequisites=prerequisites, provided=provided)
        self.name = name
        self.priority = priority

        if not isinstance(consumed, dict):
            self.consumed = dict()
            self.consumed[consumed] = 1
        else:
            self.consumed = consumed

        if mean_patron_occupancy_additive_tag is None:
            mean_patron_occupancy_additive_tag = self.name + "_" + Patron.mean_occupancy_additive_tag
        self.mean_patron_occupancy_additive_tag = mean_patron_occupancy_additive_tag

        if mean_patron_occupancy_multiplier_tag is None:
            mean_patron_occupancy_multiplier_tag = self.name + "_" + Patron.mean_occupancy_multiplier_tag
        self.mean_patron_occupancy_multiplier_tag = mean_patron_occupancy_multiplier_tag

        if maximum_patron_occupancy_limit_tag is None:
            maximum_patron_occupancy_limit_tag = self.name + "_" + Patron.maximum_occupancy_limit_tag
        self.maximum_patron_occupancy_limit_tag = maximum_patron_occupancy_limit_tag

    def get_mean_patron_occupancy_additive_tag(self):
        return self.mean_patron_occupancy_additive_tag

    def get_mean_patron_occupancy_multiplier_tag(self):
        return self.mean_patron_occupancy_multiplier_tag

    def get_maximum_patron_occupancy_limit_tags(self):
        return self.maximum_patron_occupancy_limit_tag

    def get_services_consumed(self):
        return self.consumed


class DataPack:
    def __init__(self, path):
        self.path = path
        self.services = dict()
        self.staff = dict()
        self.patrons = dict()
        self.upgrades = dict()

    def add_tag(self, tag):
        if isinstance(tag, Tag):
            self.tag_library[tag.name] = tag

    def add_service(self, service):
        self.services[service.name] = service

    def get_service(self, key):
        return self.services[key]

    def get_services(self):
        return self.services.values()

    def add_staff_archetype(self, staff):
        self.staff[staff.name] = staff

    def get_staff_archetype(self, key):
        return self.staff[key]

    def get_all_staff(self):
        return self.staff.values()

    def add_patron(self, patron):
        self.patrons[patron.name] = patron

    def get_patron(self, key):
        return self.patrons[key]

    def get_patrons(self):
        return self.patrons.values()

    def add_upgrade(self, upgrade):
        self.upgrades[upgrade.name] = upgrade

    def get_upgrade(self, key):
        return self.upgrades[key]

    def get_upgrades(self):
        return self.upgrades.values()

    def save(self):
        data.save(self.services, os.path.join(self.path, "services.json"))
        data.save(self.staff, os.path.join(self.path, "staff.json"))
        data.save(self.patrons, os.path.join(self.path, "patrons.json"))
        data.save(self.upgrades, os.path.join(self.path, "upgrades.json"))

    def load(self):
        self.services = data.load(os.path.join(self.path, "services.json"))
        self.staff = data.load(os.path.join(self.path, "staff.json"))
        self.patrons = data.load(os.path.join(self.path, "patrons.json"))
        self.upgrades = data.load(os.path.join(self.path, "upgrades.json"))

    def clear(self):
        self.patrons.clear()
        self.upgrades.clear()

    def return_priority_order(self, elem):
        return elem.priority