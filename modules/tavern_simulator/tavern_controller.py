from modules.tavern_simulator.model.new_data_pack import BusinessStateModifier, FixedAttribute, DataPack, Employee, Upgrade, Contract
from modules.tavern_simulator.model.tavern import TavernStatus, EmployeeEntry, ContractEntry

"""
TODO: When saving the state it may be worth remembering who edited it somehow? so that if we block an upgrade mid path we can remove all relevant upgrades...
"""


class StaffMember:
    def __init__(self, name, type, wages):
        self.name = name
        self.type = type
        self.wages = wages


class ActiveContract:
    def __init__(self, type, start_date):
        self.type = type
        self.start_date = start_date


# Design goal: Simulate a week (tenday) for a D&D Tavern!
class Tavern:
    @classmethod
    async def create_tavern(cls, manager, game_master, ctx, path_modifier, data_pack):
        tavern = Tavern()
        await tavern.set_data_pack(data_pack)
        await game_master.save_game_data(ctx, path_modifier, "tavern.json", tavern.get_tavern_status())
        return tavern

    @classmethod
    async def load_tavern(cls, manager, game_master, ctx, path_modifier):
        # Load our tavern data
        tavern_status = await game_master.load_game_data(ctx, path_modifier, "tavern.json")
        if not tavern_status:
            return None

        data_pack = await DataPack.load_data_pack(manager, ctx, tavern_status.data_pack_path, tavern_status.data_pack_name)
        if not data_pack:
            return "`Could not load the data pack`"

        # Create our tavern
        tavern = Tavern(tavern_status=tavern_status)
        await tavern.set_data_pack(data_pack)
        return tavern

    def __init__(self, tavern_status=None):
        self.data_pack = None

        # Create if new
        if not tavern_status:
            self.tavern_status = TavernStatus()
        else:
            self.tavern_status = tavern_status

        # The business state descriptors
        self.properties = dict()
        self.possible_upgrades = dict()
        self.possible_contracts = dict()
        self.possible_staff_types = dict()
        self.active_upgrades = list()
        self.active_contracts = list()
        self.active_employees = list()

        # Current non-serialized properties
        self.provided = dict()
        self.max_occupancy = 0
        self.current_services_offered = dict()
        self.visiting_patrons = list()
        self.maximum_patrons_satisfied = dict()
        self.sales = list()

    """
    Tavern Data
    """

    def get_name(self):
        return self.tavern_status.get_name()

    def set_name(self, name):
        self.tavern_status.set_name(name)

    def get_data_pack(self):
        return self.data_pack

    async def set_data_pack(self, data_pack):
        self.properties.clear()
        self.possible_upgrades.clear()
        self.possible_contracts.clear()
        self.possible_staff_types.clear()
        self.active_upgrades.clear()
        self.active_contracts.clear()
        self.active_employees.clear()

        # Validate our data pack
        if self.tavern_status.get_data_pack_name() != "" and self.tavern_status.get_data_pack_name() != data_pack.get_name():
            print("Cannot load the provided tavern as the specifed data pack is not present.")
            return
        self.data_pack = data_pack

        # Apply to our tavern_status
        self.tavern_status.set_data_pack(data_pack)

        # Apply the data pack's initial
        initials = self.data_pack.get_initial_states()
        for initial in initials:
            await self.__apply_state(initial)

        # Run through our purchase history
        purchase_history = self.tavern_status.get_purchase_history()
        for item in purchase_history:
            if isinstance(item, EmployeeEntry):
                await self.__hire_employee(item.staff_name, item.staff_archetype, item.daily_hire_cost)
            elif isinstance(item, ContractEntry):
                await self.__apply_contract(item.contract_type, item.start_date)
            else:
                await self.__apply_upgrade(item.upgrade_type)

        # Get all of our possible things we could apply
        await self.add_all_current_purchaseables()

    def get_tavern_status(self):
        return self.tavern_status

    def get_properties(self):
        return self.properties

    def get_upgrades(self):
        return self.active_upgrades

    def get_contracts(self):
        return self.active_contracts

    def get_employees(self):
        return self.active_employees

    def get_most_recent_customer_history(self):
        return self.tavern_status.get_customer_history_for_week(-1)

    def get_most_recent_sales_history(self):
        return self.tavern_status.get_sales_history_for_week(-1)

    def get_upgradeable(self):
        return self.possible_upgrades.values()

    def get_contractable(self):
        return self.possible_contracts.values()

    def get_hireable(self):
        return self.possible_staff_types.values()

    async def save(self, game_master, ctx, path_modifier):
        await game_master.save_game_data(ctx, path_modifier, "tavern.json", self.tavern_status)

    """
    Tavern Simulation Mechanics
    """

    async def add_all_current_purchaseables(self):
        self.possible_upgrades.clear()
        all_purchaseables = self.data_pack.get_upgrades()
        for purchaseable in all_purchaseables:
            if await self.__can_apply(purchaseable):
                self.possible_upgrades[purchaseable.unique_key] = purchaseable

        all_purchaseables = self.data_pack.get_employee_archetypes()
        for purchaseable in all_purchaseables:
            if await self.__can_apply(purchaseable):
                self.possible_staff_types[purchaseable.unique_key] = purchaseable

        all_purchaseables = self.data_pack.get_contracts()
        for purchaseable in all_purchaseables:
            if await self.__can_apply(purchaseable):
                self.possible_contracts[purchaseable.unique_key] = purchaseable

    async def apply_upgrade(self, item_key, amount):
        if item_key not in self.possible_upgrades:
            print("There is something wrong - someone told us we could load: " + item_key + " but the data pack could not find it!")
            return False

        # Get the item in question
        modifier = self.possible_upgrades[item_key]

        # Apply it to our history and our current controller
        self.tavern_status.purchase(modifier, amount=amount)
        await self.__apply_upgrade(modifier)

        # Recalc what purchases can be applied
        await self.add_all_current_purchaseables()
        return True

    async def apply_contract(self, item_key, amount, start_date):
        if item_key not in self.possible_upgrades:
            print("There is something wrong - someone told us we could load: " + item_key + " but the data pack could not find it!")
            return

        # Get the item in question
        modifier = self.possible_upgrades[item_key]

        # Apply it to our history and our current controller
        await self.tavern_status.purchase(modifier, amount=amount, start_date=start_date)
        await self.__apply_contract(modifier)

        # Recalc what purchases can be applied
        await self.add_all_current_purchaseables()

    async def hire_staff(self, item_key, name):
        if item_key not in self.possible_upgrades:
            print("There is something wrong - someone told us we could load: " + item_key + " but the data pack could not find it!")
            return

        # Get the item in question
        modifier = self.possible_upgrades[item_key]

        # Apply it to our history and our current controller
        await self.tavern_status.purchase(modifier, name=name)
        await self.__apply_upgrade(modifier)

        # Recalc what purchases can be applied
        await self.add_all_current_purchaseables()

    async def __hire_employee(self, name, staff, daily_cost):
        if not isinstance(staff, Employee):
            staff = self.data_pack.get_employee_archetype(staff)
        await self.__apply_state(staff)
        self.active_employees.append(StaffMember(name, staff, daily_cost))

    async def __apply_contract(self, contract, start_date):
        if not isinstance(contract, Contract):
            upgrade = self.data_pack.get_contract(contract)
        await self.__apply_state(contract)
        self.active_contracts.append(ActiveContract(contract, start_date))

    async def __apply_upgrade(self, upgrade):
        if not isinstance(upgrade, Upgrade):
            upgrade = self.data_pack.get_upgrade(upgrade)
        await self.__apply_state(upgrade)
        self.active_upgrades.append(upgrade)

    async def __can_apply(self, appliable):
        # Gather the prerequisites
        prerequisites = appliable.get_prerequisites()
        for prerequisite in prerequisites.values():
            key = prerequisite.get_key()
            value = prerequisite.get_value()
            type = prerequisite.get_type()
            if type == "equals":
                if key in self.properties and value != self.properties[key]:
                    return False

            elif type == "doesnt_equal":
                if key in self.properties and value == self.properties[key]:
                    return False

            elif type == "has":
                if key not in self.properties:
                    return False

            elif type == "doesnt_have":
                if key in self.properties:
                    return False

            elif type == "greater":
                if key not in self.properties:
                    return False

                # Try in case we cant convert to float
                try:
                    conditional = float(value)
                    current = float(self.properties[key])
                    return current > conditional
                except:
                    return False

            elif type == "greater_or_equal":
                if key not in self.properties:
                    return False

                # Try in case we cant convert to float
                try:
                    conditional = float(value)
                    current = float(self.properties[key])
                    return current >= conditional
                except:
                    return False

            elif type == "less":
                if key not in self.properties:
                    return False

                # Try in case we cant convert to float
                try:
                    conditional = float(value)
                    current = float(self.properties[key])
                    return current < conditional
                except:
                    return False

            elif type == "less_or_equal":
                if key not in self.properties:
                    return False

                # Try in case we cant convert to float
                try:
                    conditional = float(value)
                    current = float(self.properties[key])
                    return current <= conditional
                except:
                    return False

            elif type == "between":
                if key not in self.properties:
                    return False

                # Try in case we cant convert to float
                try:
                    values = value.split("|")
                    lower_conditional = float(values[0])
                    upper_conditional = float(values[1])
                    current = float(self.properties[key])
                    return lower_conditional < current < upper_conditional
                except:
                    return False

        return True

    async def __apply_state(self, state: BusinessStateModifier):
        for key, attribute in state.provides.items():
            await self.__apply_attribute(attribute)

    async def __apply_attribute(self, attribute):
        if isinstance(attribute, FixedAttribute):
            self.properties[attribute.get_key()] = attribute.get_value()
        else:
            if attribute.get_key() not in self.properties[attribute.get_key()]:
                self.properties[attribute.get_key()] = attribute.get_value()
                return

            # Depending on our type.
            type = attribute.get_type()
            current_val = self.properties[attribute.get_key()]

            # We can count this as being empty
            if current_val == "":
                self.properties[attribute.get_key()] = attribute.get_value()
                return

            # Throw an error
            if isinstance(current_val, str):
                raise RuntimeError("Cannot modify a string value of a property")

            # Get it as a float
            current_val = float(current_val)
            modifying_val = float(attribute.get_value())
            if type == "add":
                current_val += modifying_val
            elif type == "subtract":
                current_val -= modifying_val
            elif type == "multiply":
                current_val *= modifying_val
            elif type == "divide":
                current_val /= modifying_val
            elif type == "set_upper_bound":
                if current_val > modifying_val:
                    current_val = modifying_val

            self.properties[attribute.get_key()] = current_val

    """
    OLD ZONE IS BELOW
    """

    # def provides_for(self, data_obj):
    #     prerequisites = data_obj.get_prerequisites()
    #     for key, value in prerequisites.items():
    #         if key not in self.provided:
    #             return False
    #
    #     precluded_by = data_obj.get_precluded_by()
    #     for key, value in precluded_by.items():
    #         if key in self.provided:
    #             return False
    #
    # def apply_purchase(self, purchase):
    #     if not self.provides_for(purchase):
    #         return
    #
    #     if isinstance(purchase, Purchase):
    #         self.tavern_status.add_purchase(purchase)
    #
    #     elif isinstance(purchase, Staff):
    #         self.tavern_status.add_staff(purchase)
    #
    #     self.provided.update(purchase.get_provided())
    #
    # def add_purchase(self, purchase):
    #     # TODO Inform tavern status for logging
    #     self.tavern_status.purchase(purchase)
    #     self.__apply_state(purchase)
    #
    # def hire_staff(self, staff, amount=1):
    #     for i in range(0, amount):
    #         self.apply_purchase(staff)
    #
    # def clear(self):
    #     # TODO: THIS IS NOT THE SAME
    #     self.tavern_status.clear()
    #
    # async def validate(self):
    #     # Gather our purchases
    #     all_purchases = list()
    #
    #     # Check purchases
    #     possible_purchases = self.tavern_status.get_purchases()
    #     for possible_purchase in possible_purchases:
    #         purchase = self.data_pack.get_upgrade(possible_purchase)
    #         if purchase is not None and self.provides_for(purchase):
    #             all_purchases.append(purchase)
    #
    #     # Check staff
    #     possible_staff = self.tavern_status.get_staff().keys()
    #     for possible_staff_member in possible_staff:
    #         staff = self.data_pack.get_staff_archetype(possible_staff_member)
    #         if staff is not None and self.provides_for(staff):
    #             all_purchases.append(staff)
    #
    #     # Clear our status
    #     self.tavern_status.clear()
    #
    #     # Now validate whether or not our purchases are viable
    #     remaining_purchases = len(all_purchases)
    #     while remaining_purchases > 0:
    #         applied_purchases = list()
    #         for possible_purchase in all_purchases:
    #
    #             # Check if all prerequisites are met
    #             if self.provides_for(possible_purchase):
    #                 self.apply_purchase(possible_purchase)
    #                 applied_purchases.append(possible_purchase)
    #
    #         all_purchases = [i for i in all_purchases if i not in applied_purchases]
    #         sz = len(all_purchases)
    #         if sz == remaining_purchases:
    #             break
    #
    #         remaining_purchases = sz
    #
    # def get_maximum_occupancy(self):
    #     return self.max_occupancy
    #
    # def set_maximum_occupancy(self, value):
    #     self.max_occupancy = value
    #
    # def add_service_offered(self, service, max_offered):
    #     self.provided.update(service.get_provided())
    #     self.current_services_offered[service.name] = max_offered
    #
    # def get_visiting_patrons(self):
    #     return self.visiting_patrons
    #
    # def consume_service(self, service, amount, patron_type):
    #     remaining = self.current_services_offered[service.name]
    #     if remaining == 0:
    #         return False
    #
    #     remaining -= amount
    #     if remaining < 0:
    #         self.current_services_offered[service.name] = 0
    #         self.sales.append(Sale(service.name, amount + remaining, patron_type.name))
    #         return False
    #     else:
    #         self.current_services_offered[service.name] = remaining
    #         self.sales.append(Sale(service.name, amount, patron_type.name))
    #         return True
    #
    # def simulate(self, tenday):
    #     """
    #
    #     Dynamic Costings
    #     1) Determine what services are available
    #     2) Ascertain our maximum services
    #
    #     Staff interlude
    #         Staff:
    #             affect popularity
    #             increase service transitions (TODO: Tiered services)
    #             tips ?
    #             affect maintenance costs (bouncers)
    #             affect number of services
    #
    #     3) Simulate the number of patrons that could have come and limit by 2)
    #     4) For each patron type
    #         4a) Determine what services would be consumed
    #         4b) How many of those services per patron visit would be consumed
    #         4c) Store each successful sale
    #     5) Determine sale modifiers
    #     6) Sum
    #
    #     Fixed Costings:
    #
    #     :param tenday:
    #     :return:
    #     """
    #
    #     # Calculate our flat max occupancy
    #     self.determine_max_occupancy()
    #
    #     # Identify which services we can provide
    #     self.determine_available_services()
    #
    #     # Determine what patron types are available to us
    #     self.determine_visiting_patron_types()
    #
    #     # Simulate attendance
    #     self.simulate_attendance(tenday)
    #
    #     # Serve our patrons as much as we can
    #     self.serve_patrons()
    #
    #     """
    #     We now need to calculate the profits and costs per sale (incl tips)
    #
    #     Dynamic maintenance costs
    #
    #     Fixed costs
    #
    #     Fixed earnings
    #     """
    #
    # def determine_max_occupancy(self):
    #     max_occupancy_modifiers = list()
    #     for upgrade_key in self.tavern_status.get_purchases():
    #         upgrade = self.data_pack.get_upgrade(upgrade_key)
    #         max_occupancy_modifiers.extend(upgrade.get_provided_value(Patron.maximum_occupancy_limit_tag))
    #     self.set_maximum_occupancy(sum(max_occupancy_modifiers))
    #
    # def determine_available_services(self):
    #     # TODO: Move away from sets as it would allow for multiple of the same requirements
    #     for service in self.data_pack.get_services():
    #         remaining_requirements = set(service.get_prerequisites())
    #
    #         # Remove any things provided by our upgrades
    #         for upgrade_key in self.tavern_status.get_purchases():
    #             upgrade = self.data_pack.get_upgrade(upgrade_key)
    #             provided = upgrade.get_provided()
    #             remaining_requirements = remaining_requirements.difference(provided)
    #
    #         # Remove any things provided by our staff:
    #         for staff in self.tavern_status.get_staff():
    #             staff_archetype = self.data_pack.get_staff_archetype(staff)
    #             provided = staff_archetype.get_provided()
    #             remaining_requirements = remaining_requirements.difference(provided)
    #
    #         # If all of our requirements were satisfied add the service and calculate the max supplied
    #         if len(remaining_requirements) == 0:
    #             max_modifier_tags = service.get_maximum_of_service_offered_tags()
    #
    #             # Check our upgrade for inhibitions
    #             applicable_values = list()
    #             for upgrade_key in self.tavern_status.get_purchases():
    #                 upgrade = self.data_pack.get_upgrade(upgrade_key)
    #                 applicable_values.extend(upgrade.get_provided_value(max_modifier_tags))
    #
    #             if len(applicable_values) == 0:
    #                 max_sales_of_service = 0
    #             else:
    #                 max_sales_of_service = min(applicable_values)
    #             self.add_service_offered(service, max_sales_of_service)
    #
    # def determine_visiting_patron_types(self):
    #     for patron_type in self.data_pack.get_patrons():
    #         if self.provides_for(patron_type):
    #             self.visiting_patrons.append(patron_type)
    #
    # def simulate_attendance(self, tenday):
    #     # Simulate the number and type of patrons served
    #     # For each patron type available get the status' for our current tavern status
    #     for patron_type in self.get_visiting_patrons():
    #         """
    #         create a probability curve to represent patron attendance probability
    #
    #             mean = collect_occupancy_modifier_for_patrons but numerically it should be raw patron count
    #             std = 50% of mean? (we can fiddle)
    #
    #             tenday_patron_types_served = use dice roll to indicate where along the bell curve to pick (i.e. is the cumulative probability value or area)
    #         """
    #
    #         # Collect all modifiers to avg occupancy and simulate as above
    #         avg_occupancy = list()
    #         max_occupancy_for_patron_type = list()
    #         max_occupancy_for_patron_type.append(self.get_maximum_occupancy())
    #         current_upgrades = self.tavern_status.get_purchases()
    #         for upgrade_key in current_upgrades:
    #             upgrade = self.data_pack.get_upgrade(upgrade_key)
    #
    #             applicable_values = upgrade.get_provided_value(patron_type.get_mean_patron_occupancy_additive_tag())
    #             avg_occupancy.extend(applicable_values)
    #
    #             applicable_values = upgrade.get_provided_value(patron_type.get_maximum_patron_occupancy_limit_tags())
    #             max_occupancy_for_patron_type.extend(applicable_values)
    #
    #         # Determine simulation parameters
    #         max_occupancy_for_patron_type = min(max_occupancy_for_patron_type)
    #         avg_occupancy = sum(avg_occupancy)
    #         simulated = stats.norm.ppf(tenday.get_popularity() / 100, loc=avg_occupancy, scale=avg_occupancy / 2)
    #
    #         # Staff can modify the popularity of the place
    #         # TODO: Should these instead affect the tenday popularity? It would certainly be less drastic
    #         for staff, amount in self.tavern_status.get_staff().items():
    #             for i in range(0, amount):
    #                 staff_archetype = self.data_pack.get_staff_archetype(staff)
    #                 modifiers = staff_archetype.get_provided_value(patron_type.get_mean_patron_occupancy_multiplier_tag())
    #                 for modifier in modifiers:
    #                     simulated *= modifier
    #
    #         # Clamp services and set in simulation result
    #         services = math.clamp_incl(simulated, 0, max_occupancy_for_patron_type)
    #         self.maximum_patrons_satisfied[patron_type.name] = services
    #
    # def serve_patrons(self):
    #     """
    #     Loop through our patrons served and evaluate what services they will consume.
    #     Sort by priority - under the premise that you serve whales as a priority
    #     TODO: Modifiy the sales and cost where appropriate
    #     :return:
    #     """
    #     # Sort in order of priority
    #     for visiting_patron in sorted(self.visiting_patrons, key=new_data_pack.return_priority_order, reverse=True):
    #         patrons_served = self.maximum_patrons_satisfied[visiting_patron.name]
    #         services_consumed = visiting_patron.get_services_consumed()
    #
    #         has_had_a_service_requirement_met = True
    #         for i in range(0, patrons_served):
    #             if not has_had_a_service_requirement_met:
    #                 break
    #
    #             has_had_a_service_requirement_met = False
    #             for service_key, amount in services_consumed.items():
    #                 if service_key in self.current_services_offered:
    #                     service = self.data_pack.get_service(service_key)
    #                     has_had_a_service_requirement_met |= self.consume_service(service, amount, visiting_patron)
