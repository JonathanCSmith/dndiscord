import os
from collections import OrderedDict

from data.data_pack import DataPack


class BusinessDataPack(DataPack):
    def __init__(self, pack_name, pack_description, business_name, business_description, **kwargs):
        super().__init__(**kwargs)

        self.pack_name = pack_name
        self.pack_description = pack_description
        self.business_name = business_name
        self.business_description = business_description

        self.add_item_to_be_ignored("initial_state")
        self.initial_state = OrderedDict()

        self.add_item_to_be_ignored("improvements")
        self.improvements = OrderedDict()

        self.add_item_to_be_ignored("employees")
        self.employees = OrderedDict()

        self.add_item_to_be_ignored("contracts")
        self.contracts = OrderedDict()

        self.add_item_to_be_ignored("customers")
        self.customers = OrderedDict()

        self.add_item_to_be_ignored("services")
        self.services = OrderedDict()

    def load_data_pack(self, file_system):
        self.initial_state = file_system.load_file(os.path.join(self.current_path, "initial_state.json"))

    def save_data_pack(self, file_system):
        file_system.save_file(os.path.join(self.current_path, "initial_state.json"), self.initial_state)


def generate_data_pack(source_file):
    # IF file is python, load it and assume it has a function we can call?
    pass



# class BusinessDataPack:
#     @classmethod
#     async def load(cls, manager, ctx, original_path_modifier, data_pack_name=None):
#         if data_pack_name is not None:
#             pack_name = data_pack_name
#             pack_path = os.path.join(original_path_modifier, data_pack_name)
#         else:
#             pack_name = os.path.basename(original_path_modifier)
#             pack_path = original_path_modifier
#
#         # Try loading from our guilds path
#         is_guild = True
#         data_pack_data = await manager.load_data_from_data_path_for_guild(ctx, pack_path, "data_pack.json")
#         initial = await manager.load_data_from_data_path_for_guild(ctx, pack_path, "initial.json")
#         services = await manager.load_data_from_data_path_for_guild(ctx, pack_path, "services.json")
#         employees = await manager.load_data_from_data_path_for_guild(ctx, pack_path, "employees.json")
#         customers = await manager.load_data_from_data_path_for_guild(ctx, pack_path, "customers.json")
#         improvements = await manager.load_data_from_data_path_for_guild(ctx, pack_path, "improvements.json")
#         contracts = await manager.load_data_from_data_path_for_guild(ctx, pack_path, "contracts.json")
#         translations = await manager.load_data_from_data_path_for_guild(ctx, pack_path, "translation_index.json")
#
#         # Try our backup, which is in the bot root
#         if initial is None and services is None and employees is None and customers is None and improvements is None and contracts is None:
#             is_guild = False
#             data_pack_data = await manager.load_data_from_data_path(pack_path, "data_pack.json")
#             initial = await manager.load_data_from_data_path(pack_path, "initial.json")
#             services = await manager.load_data_from_data_path(pack_path, "services.json")
#             employees = await manager.load_data_from_data_path(pack_path, "employees.json")
#             customers = await manager.load_data_from_data_path(pack_path, "customers.json")
#             improvements = await manager.load_data_from_data_path(pack_path, "improvements.json")
#             contracts = await manager.load_data_from_data_path(pack_path, "contracts.json")
#             translations = await manager.load_data_from_data_path(pack_path, "translation_index.json")
#
#         # Output nothing if there is nothing loaded. Any data whatsoever, and we assume it's correct
#         if initial is None and services is None and employees is None and customers is None and improvements is None and contracts is None:
#             return None
#
#         # If we have translations to load
#         if translations:
#             await manager.load_translations_package(ctx, TranslationSource("business." + pack_name, pack_path, translations, is_guild))
#
#         return BusinessDataPack(pack_name, pack_path, is_guild, data_pack_data=data_pack_data, initial=initial, services=services, employees=employees, customers=customers, improvements=improvements, contracts=contracts)
#
#     def __init__(self, name, path_modifier, is_guild, business_name=None, description=None, data_pack_data=None):
#         self.name = name
#         if " " in self.name:
#             raise RuntimeError("You cannot have spaces inside data pack names.")
#
#         self.path = path_modifier
#         self.is_guild = is_guild
#
#         if not data_pack_data and not business_name:
#             raise RuntimeError("You cannot create a data pack without a business name or a data_pack_data object")
#         elif data_pack_data:
#             self.data_pack_data = data_pack_data
#         else:
#             self.data_pack_data = DataPackData(self.name, business_name, description)
#
#     def get_name(self):
#         return self.name
#
#     def get_path(self):
#         return self.path
#
#     def get_business_name(self):
#         return self.data_pack_data.business_name
#
#     def get_business_description(self):
#         return self.data_pack_data.description
#
#     def get_initial_states(self):
#         return self.initial.values()
#
#     def add_initial(self, obj):
#         self.initial[obj.unique_key] = obj
#
#     def get_employee_archetypes(self):
#         return self.employees.values()
#
#     def get_employee_archetype(self, key):
#         return self.employees[key]
#
#     def add_employee_archetype(self, staff):
#         self.employees[staff.unique_key] = staff
#
#     def get_improvements(self):
#         return self.improvements.values()
#
#     def get_improvement(self, key):
#         return self.improvements[key]
#
#     def add_improvement(self, purchaseable):
#         self.improvements[purchaseable.unique_key] = purchaseable
#
#     def get_contracts(self):
#         return self.contracts.values()
#
#     def get_contract(self, contract):
#         return self.contracts[contract]
#
#     def add_contract(self, contract):
#         self.contracts[contract.unique_key] = contract
#
#     def get_services(self):
#         return self.services.values()
#
#     def get_service(self, key):
#         return self.services[key]
#
#     def add_service(self, service):
#         self.services[service.unique_key] = service
#
#     def get_customer_archetype(self, key):
#         return self.customers[key]
#
#     def get_customers(self):
#         return self.customers.values()
#
#     def add_customer(self, customer):
#         self.customers[customer.unique_key] = customer
#
#     def get_state_modifier(self, key):
#         if key in self.initial:
#             return self.initial[key]
#
#         elif key in self.improvements:
#             return self.improvements[key]
#
#         elif key in self.contracts:
#             return self.contracts[key]
#
#         elif key in self.employees:
#             return self.employees[key]
#
#         elif key in self.services:
#             return self.services[key]
#
#         elif key in self.customers:
#             return self.customers[key]
#
#         return None
#
#     async def save(self, manager=None, ctx=None):
#         save_path = self.path
#         if self.is_guild:
#             await manager.save_data_in_data_path_for_guild(ctx, save_path, "data_pack.json", self.data_pack_data)
#             await manager.save_data_in_data_path_for_guild(ctx, save_path, "initial.json", self.initial)
#             await manager.save_data_in_data_path_for_guild(ctx, save_path, "services.json", self.services)
#             await manager.save_data_in_data_path_for_guild(ctx, save_path, "employees.json", self.employees)
#             await manager.save_data_in_data_path_for_guild(ctx, save_path, "customers.json", self.customers)
#             await manager.save_data_in_data_path_for_guild(ctx, save_path, "improvements.json", self.improvements)
#             await manager.save_data_in_data_path_for_guild(ctx, save_path, "contracts.json", self.contracts)
#         else:
#             await manager.save_data_in_data_path(save_path, "data_pack.json", self.data_pack_data)
#             await manager.save_data_in_data_path(save_path, "initial.json", self.initial)
#             await manager.save_data_in_data_path(save_path, "services.json", self.services)
#             await manager.save_data_in_data_path(save_path, "employees.json", self.employees)
#             await manager.save_data_in_data_path(save_path, "customers.json", self.customers)
#             await manager.save_data_in_data_path(save_path, "improvements.json", self.improvements)
#             await manager.save_data_in_data_path(save_path, "contracts.json", self.contracts)
