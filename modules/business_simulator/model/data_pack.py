import os
from collections import OrderedDict

from utils import data
from utils.translations import TranslationSource


class Attribute:
    def __init__(self, attribute_key, attribute_value=None):
        self.attribute_key = attribute_key
        self.attribute_value = attribute_value

    def get_key(self):
        return self.attribute_key

    def get_value(self):
        return self.attribute_value

    def __str__(self):
        return "Property:" + self.attribute_key + (" with value: " + self.attribute_value if self.attribute_value is not None else "")


class FixedAttribute(Attribute):
    def __init__(self, attribute_key, attribute_value):
        super().__init__(attribute_key, attribute_value)


class ModifiesAttribute(Attribute):
    types = ["add", "subtract", "multiply", "divide", "set_upper_bound"]

    def __init__(self, attribute_key, attribute_value, modification_type):
        super().__init__(attribute_key, attribute_value)

        if modification_type not in ModifiesAttribute.types:
            raise RuntimeError("Poor modification type for ModificationAttribute: " + self.attribute_key + " and value " + str(self.attribute_value))
        self.modification_type = modification_type

    def get_type(self):
        return self.modification_type


class Conditional(Attribute):
    types = ["equals", "doesnt_equal", "has", "doesnt_have", "greater", "greater_or_equal", "less", "less_or_equal", "between"]

    def __init__(self, condition_type, attribute_key, attribute_value):
        super().__init__(attribute_key, attribute_value)

        if condition_type not in Conditional.types:
            raise RuntimeError("Poor condition construction. Type was: " + condition_type)

        self.condition_type = condition_type

    def get_type(self):
        return self.condition_type


class BusinessStateModifier:
    def __init__(self, unique_key, requirements=None, provides=None):
        self.unique_key = unique_key

        if not requirements:
            requirements = dict()
        elif not isinstance(requirements, dict):
            requirements = dict()
        self.requirements = requirements

        if not provides:
            provides = dict()
        elif not isinstance(provides, dict):
            provides = dict()
        self.provides = provides

    def get_key(self):
        return self.unique_key

    def get_prerequisites(self):
        return self.requirements

    def append_prerequisite(self, condition: Conditional):
        self.requirements[condition.get_key()] = condition

    def get_provided(self):
        return self.provides

    def append_provided(self, attribute: Attribute):
        self.provides[attribute.get_key()] = attribute


class Improvement(BusinessStateModifier):
    def __init__(self, unique_key, cost, duration, requirements=None, provides=None):
        super().__init__(unique_key,  requirements=requirements, provides=provides)

        self.cost = cost
        self.duration = duration


class Contract(BusinessStateModifier):
    def __init__(self, unique_key, cost, duration, requirements=None, provides=None):
        super().__init__(unique_key, requirements=requirements, provides=provides)

        self.cost = cost
        self.duration = duration


class Employee(BusinessStateModifier):
    def __init__(self, unique_key, cost_per_day, requirements=None, provides=None):
        super().__init__(unique_key, requirements=requirements, provides=provides)

        self.cost_per_day = cost_per_day


class ServiceOffered(BusinessStateModifier):
    def __init__(self, unique_key, cost_price, sale_price, cost_value_modifiers=None, sale_value_modifiers=None, requirements=None, provides=None):
        super().__init__(unique_key, requirements=requirements, provides=provides)

        self.cost_price = cost_price
        self.sale_price = sale_price

        if cost_value_modifiers is None:
            cost_value_modifiers = list()
        self.cost_value_modifiers = ["all_unit_costs_modifier", self.unique_key + "_unit_costs_modifier"]
        for item in cost_value_modifiers:
            if item not in self.cost_value_modifiers:
                self.cost_value_modifiers.append(item)

        if sale_value_modifiers is None:
            sale_value_modifiers = list()
        self.sale_value_modifiers = ["all_unit_sales_modifier", self.unique_key + "_unit_sales_modifier"]
        for item in sale_value_modifiers:
            if item not in self.sale_value_modifiers:
                self.sale_value_modifiers.append(item)

    def get_cost_value_modifiers(self):
        return self.cost_value_modifiers

    def __str__(self):
        return self.unique_key + " are offered for " + str(self.sale_price) + "cp and cost " + str(self.cost_price) + "cp per unit sold / offered"


class Customer(BusinessStateModifier):
    def __init__(self, unique_key, customer_tier, popularity_modifiers=None, occupancy_modifiers=None, services_consumed=None, requirements=None, provides=None):
        super().__init__(unique_key, requirements=requirements, provides=provides)

        self.customer_tier = customer_tier

        if services_consumed is None:
            services_consumed = dict()
        self.services_consumed = services_consumed

        if popularity_modifiers is None:
            popularity_modifiers = list()
        self.popularity_modifiers = ["all_popularity_modifier", self.unique_key + "_popularity_modifier"]
        for item in popularity_modifiers:
            if item not in self.popularity_modifiers:
                self.popularity_modifiers.append(item)

        if occupancy_modifiers is None:
            occupancy_modifiers = list()
        self.occupancy_modifiers = ["all_customers_maximum_occupancy_modifier", self.unique_key + "_maximum_occupancy_modifier"]
        for item in occupancy_modifiers:
            if item not in self.occupancy_modifiers:
                self.occupancy_modifiers.append(item)

    def get_consumed_services(self):
        return self.services_consumed

    def add_consumed_service(self, key, amount):
        if key in self.services_consumed:
            self.services_consumed[key] += amount
        else:
            self.services_consumed[key] = amount

    def get_popularity_modifiers(self):
        return self.popularity_modifiers

    def get_maximum_occupancy_modifiers(self):
        return self.occupancy_modifiers

    def __str__(self):
        return "The " + self.unique_key + " customer type, with a service priority of " + str(self.customer_tier)


class DataPackData:
    def __init__(self, pack_name, business_name, description):
        self.pack_name = pack_name
        self.business_name = business_name
        self.description = description


def return_priority_order(elem):
    return elem.priority


class BusinessDataPack:
    @classmethod
    async def load(cls, manager, ctx, original_path_modifier, data_pack_name=None):
        if data_pack_name is not None:
            path_modifier = os.path.join(original_path_modifier, data_pack_name)
        else:
            pack_name = os.path.basename(original_path_modifier)
            path_modifier = "".join(original_path_modifier.rsplit(pack_name, 1))

        # Try loading from our guilds path
        is_guild = True
        data_pack_data = await manager.load_data_from_data_path_for_guild(ctx, path_modifier, "data_pack.json")
        initial = await manager.load_data_from_data_path_for_guild(ctx, path_modifier, "initial.json")
        services = await manager.load_data_from_data_path_for_guild(ctx, path_modifier, "services.json")
        employees = await manager.load_data_from_data_path_for_guild(ctx, path_modifier, "employees.json")
        customers = await manager.load_data_from_data_path_for_guild(ctx, path_modifier, "customers.json")
        improvements = await manager.load_data_from_data_path_for_guild(ctx, path_modifier, "improvements.json")
        contracts = await manager.load_data_from_data_path_for_guild(ctx, path_modifier, "contracts.json")
        translations = await manager.load_data_from_data_path_for_guild(ctx, path_modifier, "translation_index.json")

        # Try our backup, which is in the bot root
        if initial is None and services is None and employees is None and customers is None and improvements is None and contracts is None:
            is_guild = False
            data_pack_data = await manager.load_data_from_data_path(path_modifier, "data_pack.json")
            initial = await manager.load_data_from_data_path(path_modifier, "initial.json")
            services = await manager.load_data_from_data_path(path_modifier, "services.json")
            employees = await manager.load_data_from_data_path(path_modifier, "employees.json")
            customers = await manager.load_data_from_data_path(path_modifier, "customers.json")
            improvements = await manager.load_data_from_data_path(path_modifier, "improvements.json")
            contracts = await manager.load_data_from_data_path(path_modifier, "contracts.json")
            translations = await manager.load_data_from_data_path(path_modifier, "translation_index.json")

        # Output nothing if there is nothing loaded. Any data whatsoever, and we assume it's correct
        if initial is None and services is None and employees is None and customers is None and improvements is None and contracts is None:
            return None

        # If we have translations to load
        if translations:
            await manager.load_translations_package(ctx, TranslationSource("business." + pack_name, path_modifier, translations, is_guild))

        return BusinessDataPack(original_path_modifier, is_guild, data_pack_data=data_pack_data, initial=initial, services=services, employees=employees, customers=customers, improvements=improvements, contracts=contracts)

    def __init__(self, name, path_modifier, is_guild, business_name=None, description=None, data_pack_data=None, initial=None, services=None, employees=None, customers=None, improvements=None, contracts=None):
        self.name = name
        if " " in self.name:
            raise RuntimeError("You cannot have spaces inside data pack names.")

        self.path_modifier = path_modifier
        self.is_guild = is_guild

        if not initial:
            initial = OrderedDict()
        self.initial = initial

        if not improvements:
            improvements = OrderedDict()
        self.improvements = improvements

        if not employees:
            employees = OrderedDict()
        self.employees = employees

        if not contracts:
            contracts = OrderedDict()
        self.contracts = contracts

        if not customers:
            customers = OrderedDict()
        self.customers = customers

        if not services:
            services = OrderedDict()
        self.services = services

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

    def get_business_name(self):
        return self.data_pack_data.business_name

    def get_business_description(self):
        return self.data_pack_data.description

    def get_initial_states(self):
        return self.initial.values()

    def add_initial(self, obj):
        self.initial[obj.unique_key] = obj

    def get_employee_archetypes(self):
        return self.employees.values()

    def get_employee_archetype(self, key):
        return self.employees[key]

    def add_employee_archetype(self, staff):
        self.employees[staff.unique_key] = staff

    def get_improvements(self):
        return self.improvements.values()

    def get_improvement(self, key):
        return self.improvements[key]

    def add_improvement(self, purchaseable):
        self.improvements[purchaseable.unique_key] = purchaseable

    def get_contracts(self):
        return self.contracts.values()

    def get_contract(self, contract):
        return self.contracts[contract]

    def add_contract(self, contract):
        self.contracts[contract.unique_key] = contract

    def get_services(self):
        return self.services.values()

    def get_service(self, key):
        return self.services[key]

    def add_service(self, service):
        self.services[service.unique_key] = service

    def get_customer_archetype(self, key):
        return self.customers[key]

    def get_customers(self):
        return self.customers.values()

    def add_customer(self, customer):
        self.customers[customer.unique_key] = customer

    def get_state_modifier(self, key):
        if key in self.initial:
            return self.initial[key]

        elif key in self.improvements:
            return self.improvements[key]

        elif key in self.contracts:
            return self.contracts[key]

        elif key in self.employees:
            return self.employees[key]

        elif key in self.services:
            return self.services[key]

        elif key in self.customers:
            return self.customers[key]

        return None

    async def save(self, manager=None, ctx=None):
        save_path = os.path.join(self.path_modifier, self.name)
        if self.is_guild:
            await manager.save_data_in_data_path_for_guild(ctx, save_path, "data_pack.json", self.data_pack_data)
            await manager.save_data_in_data_path_for_guild(ctx, save_path, "initial.json", self.initial)
            await manager.save_data_in_data_path_for_guild(ctx, save_path, "services.json", self.services)
            await manager.save_data_in_data_path_for_guild(ctx, save_path, "employees.json", self.employees)
            await manager.save_data_in_data_path_for_guild(ctx, save_path, "customers.json", self.customers)
            await manager.save_data_in_data_path_for_guild(ctx, save_path, "improvements.json", self.improvements)
            await manager.save_data_in_data_path_for_guild(ctx, save_path, "contracts.json", self.contracts)
        else:
            await manager.save_data_in_data_path(save_path, "data_pack.json", self.data_pack_data)
            await manager.save_data_in_data_path(save_path, "initial.json", self.initial)
            await manager.save_data_in_data_path(save_path, "services.json", self.services)
            await manager.save_data_in_data_path(save_path, "employees.json", self.employees)
            await manager.save_data_in_data_path(save_path, "customers.json", self.customers)
            await manager.save_data_in_data_path(save_path, "improvements.json", self.improvements)
            await manager.save_data_in_data_path(save_path, "contracts.json", self.contracts)
