import os
from collections import OrderedDict

from utils import data
from utils.translations import TranslationSource

"""
TODO: Tag Library? Would allow for inheritance but it seems ridiculously overcomplicated
TODO: We could turn the 'values' of prerequisites into an alias repository instead
"""


class Data:
    def __int__(self, name, prerequisites=None, provides=None, precluded_by=None, description="", hidden=False):
        self.name = name

        if prerequisites is None:
            prerequisites = dict()
        elif not isinstance(prerequisites, dict):
            print("Prerequisites: " + str(prerequisites) + " are not valid for: " + name)
            prerequisites = dict()
        self.prerequisites = prerequisites

        if provides is None:
            provides = dict()
        elif not isinstance(provides, dict):
            print("Provided: " + str(provides) + " are not valid for: " + name)
            provides = dict()
        self.provides = provides

        if precluded_by is None:
            precluded_by = dict()
        elif not isinstance(precluded_by, dict):
            print("Provided: " + str(precluded_by) + " are not valid for: " + name)
            precluded_by = dict()
        self.precluded_by = precluded_by

        self.description = description

    def append_prerequisite(self, key, value):
        self.prerequisites[key] = value

    def get_prerequisites(self):
        return self.prerequisites

    def append_provided(self, key, value):
        self.provides[key] = value

    def get_provided(self):
        return self.provides

    def append_precluded_by(self, key, value):
        self.precluded_by[key] = value

    def get_precluded_by(self):
        return self.precluded_by

    def get_provided_value(self, keys):
        values = list()
        if isinstance(keys, list):
            for key in keys:
                if key in self.provides:
                    values.append(self.provides[key])

        elif keys in self.provides:
            values.append(self.provides[keys])

        return values


class Service(Data):
    maximum_services_tag = "maximum_services"

    def __init__(self, name, cost, sale, prerequisites=None, provides=None, precluded_by=None, description="", hidden=False, service_maximum_tags=None, served=None):
        super().__int__(name, prerequisites=prerequisites, provides=provides, precluded_by=precluded_by, description=description, hidden=hidden)

        self.cost = cost
        self.sale = sale
        self.service_maximum_tags = self.name + "_" + Service.maximum_services_tag

    def get_maximum_of_service_offered_tags(self):
        return self.service_maximum_tags


class Staff(Data):
    """
    TODO: Names, Service type transitions (i.e. upsell)? Staff common rooms? Staff limit the volume of sales
    """

    def __init__(self, name, cost, prerequisites=None, provides=None, precluded_by=None, description="", hidden=False):
        super().__int__(name, prerequisites=prerequisites, provides=provides, precluded_by=precluded_by, description=description, hidden=hidden)

        self.cost = cost


class Purchase(Data):
    def __init__(self, name, cost, prerequisites=None, provides=None, precluded_by=None, description="", hidden=False):
        super().__int__(name, provides=provides, prerequisites=prerequisites, precluded_by=precluded_by, description=description, hidden=hidden)

        self.cost = cost


class Contract(Purchase):
    def __init__(self, name, cost, duration, prerequisites=None, provides=None, precluded_by=None, description="", hidden=False):
        super().__init__(name, cost, provides=provides, prerequisites=prerequisites, precluded_by=precluded_by, description=description, hidden=hidden)

        self.duration = duration


class Patron(Data):
    mean_occupancy_additive_tag = "average_attendance_addition"
    mean_occupancy_multiplier_tag = "average_attendance_multiplier"
    maximum_occupancy_limit_tag = "maximum_occupancy"

    def __init__(self, name, priority, consumed, prerequisites=None, provides=None, precluded_by=None, description="", hidden=False, mean_patron_occupancy_additive_tag=None, mean_patron_occupancy_multiplier_tag=None, maximum_patron_occupancy_limit_tag=None):
        super().__int__(name, prerequisites=prerequisites, provides=provides, precluded_by=precluded_by, description=description, hidden=hidden)
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


class DataPackData:
    def __init__(self, pack_name, business_name, description):
        self.pack_name = pack_name
        self.business_name = business_name
        self.description = description


class DataPack:
    @classmethod
    async def load_data_pack(cls, manager, ctx, original_path_modifier, pack_name):
        path_modifier = os.path.join(original_path_modifier, pack_name)

        # Try loading from our guilds path
        is_guild = True
        data_pack_data = await manager.load_data_from_data_path_for_guild(ctx, path_modifier, "data_pack.json")
        initial = await manager.load_data_from_data_path_for_guild(ctx, path_modifier, "initial.json")
        services = await manager.load_data_from_data_path_for_guild(ctx, path_modifier, "services.json")
        staff = await manager.load_data_from_data_path_for_guild(ctx, path_modifier, "staff.json")
        patrons = await manager.load_data_from_data_path_for_guild(ctx, path_modifier, "patrons.json")
        purchaseable = await manager.load_data_from_data_path_for_guild(ctx, path_modifier, "purchaseable.json")
        contracts = await manager.load_data_from_data_path_for_guild(ctx, path_modifier, "contracts.json")
        translations = await manager.load_data_from_data_path_for_guild(ctx, path_modifier, "translation_index.json")

        # Try our backup, which is in the bot root
        if initial is None and services is None and staff is None and patrons is None and purchaseable is None and contracts is None:
            is_guild = False
            data_pack_data = await manager.load_data_from_data_path(path_modifier, "data_pack.json")
            initial = await manager.load_data_from_data_path(path_modifier, "initial.json")
            services = await manager.load_data_from_data_path(path_modifier, "services.json")
            staff = await manager.load_data_from_data_path(path_modifier, "staff.json")
            patrons = await manager.load_data_from_data_path(path_modifier, "patrons.json")
            purchaseable = await manager.load_data_from_data_path(path_modifier, "purchaseable.json")
            contracts = await manager.load_data_from_data_path(path_modifier, "contracts.json")
            translations = await manager.load_data_from_data_path(path_modifier, "translation_index.json")

        # Output nothing if there is nothing loaded. Any data whatsoever, and we assume it's correct
        if initial is None and services is None and staff is None and patrons is None and purchaseable is None and contracts is None:
            return None

        # If we have translations to load
        if translations:
            await manager.load_translations_package(ctx, TranslationSource("tavern." + pack_name, path_modifier, translations, is_guild))

        return DataPack(pack_name, original_path_modifier, is_guild, data_pack_data=data_pack_data, initial=initial, services=services, staff=staff, patrons=patrons, purchaseable=purchaseable, contracts=contracts)

    def __init__(self, name, path_modifier, is_guild, business_name=None, description=None, data_pack_data=None, initial=None, services=None, staff=None, patrons=None, purchaseable=None, contracts=None):
        self.name = name
        self.path_modifier = path_modifier
        self.is_guild = is_guild

        if not services:
            services = OrderedDict()
        self.services = services

        if not staff:
            staff = OrderedDict()
        self.staff = staff

        if not patrons:
            patrons = OrderedDict()
        self.patrons = patrons

        if not purchaseable:
            purchaseable = OrderedDict()
        self.purchaseable = purchaseable

        if not contracts:
            contracts = OrderedDict()
        self.contracts = contracts

        if not initial:
            initial = OrderedDict()
        self.initial = initial

        if not data_pack_data and not business_name:
            raise RuntimeError("You cannot create a data pack without a business name or a data_pack_data object")
        elif data_pack_data:
            self.data_pack_data = data_pack_data
        else:
            self.data_pack_data = DataPackData(self.name, business_name, description)

    def get_name(self):
        return self.name

    def get_path(self):
        return self.path_modifier

    def add_initial(self, obj):
        self.initial[obj.name] = obj

    def get_initial(self):
        return self.initial

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

    def add_purchaseable(self, purchaseable):
        self.purchaseable[purchaseable.name] = purchaseable

    def get_purchaseable(self, key):
        return self.purchaseable[key]

    def get_purchaseables(self):
        return self.purchaseable.values()

    def add_contract(self, contract):
        self.contracts[contract.name] = contract

    def get_contracts(self):
        return self.contracts

    async def save(self, manager=None, ctx=None):
        save_path = os.path.join(self.path_modifier, self.name)
        if self.is_guild:
            await manager.save_data_in_data_path_for_guild(ctx, save_path, "data_pack.json", self.data_pack_data)
            await manager.save_data_in_data_path_for_guild(ctx, save_path, "initial.json", self.initial)
            await manager.save_data_in_data_path_for_guild(ctx, save_path, "services.json", self.services)
            await manager.save_data_in_data_path_for_guild(ctx, save_path, "staff.json", self.staff)
            await manager.save_data_in_data_path_for_guild(ctx, save_path, "patrons.json", self.patrons)
            await manager.save_data_in_data_path_for_guild(ctx, save_path, "purchaseable.json", self.purchaseable)
            await manager.save_data_in_data_path_for_guild(ctx, save_path, "contracts.json", self.contracts)
        else:
            await manager.save_data_in_data_path(save_path, "data_pack.json", self.data_pack_data)
            await manager.save_data_in_data_path(save_path, "initial.json", self.initial)
            await manager.save_data_in_data_path(save_path, "services.json", self.services)
            await manager.save_data_in_data_path(save_path, "staff.json", self.staff)
            await manager.save_data_in_data_path(save_path, "patrons.json", self.patrons)
            await manager.save_data_in_data_path(save_path, "purchaseable.json", self.purchaseable)
            await manager.save_data_in_data_path(save_path, "contracts.json", self.contracts)

    def clear(self):
        self.patrons.clear()
        self.purchaseable.clear()

    def return_priority_order(self, elem):
        return elem.priority
