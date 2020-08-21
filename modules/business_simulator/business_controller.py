import os
from collections import OrderedDict

from modules.business_simulator.model.data_pack import FixedAttribute, BusinessDataPack, Employee, Improvement, Contract, Customer, ServiceOffered, ServiceState
from modules.business_simulator.model.business_model import BusinessStatus

"""
TODO: When saving the state it may be worth remembering who edited it somehow? so that if we block an improvement mid path we can remove all relevant improvements...
"""


class BusinessController:
    @classmethod
    async def create_business(cls, game_master, ctx, data_pack, name):
        business = BusinessController(name)
        await business.set_data_pack(data_pack)
        await game_master.save_game_data(ctx, "businesses", name, business.get_business_status())
        return business

    @classmethod
    async def load_business(cls, engine, game_master, ctx, business_name):
        # Load our business
        #business_status = await game_master.load_game_data(ctx, "businesses", business_name)
        business_status = await game_master.load_game_specific_data(engine, ctx, os.path.join("businesses", business_name))
        if not business_status:
            return None

        # Check we have data packs available
        #data_pack = await BusinessDataPack.load(manager, ctx, business_status.data_pack_path)
        data_pack = await engine.get_file_manager().load_data_pack_by_path(business_status.data_pack_path)
        if not data_pack:
            return "`Could not load the data pack for business: " + business_name + "`"

        # Create our business
        business = BusinessController(business_status=business_status)
        await business.set_data_pack(data_pack)
        return business

    def __init__(self, name=None, business_status=None):
        self.data_pack = None

        # Create if new
        if business_status is None and name is None:
            raise RuntimeError("Cannot create a business without a name or an existing status....")

        elif not business_status:
            # IF the idiot calls their business <guild>+<game>_business we would have a problem

            self.business_status = BusinessStatus(name)

        else:
            self.business_status = business_status

        # Business state holders
        self.recorded_active_state_modifiers = dict()
        self.recorded_inactive_state_modifiers = dict()
        self.recorded_removed_state_modifiers = dict()

        # The business state descriptors
        self.properties = OrderedDict()  # We could rely on 3.7 here but I suspect its better to be explicit
        self.implied_inactive_state_modifiers = list()
        self.active_improvements = list()
        self.active_contracts = list()
        self.active_employees = list()
        self.possible_improvements = list()
        self.possible_contracts = list()
        self.possible_employee_types = list()
        self.available_services = dict()
        self.available_customers = list()

        # Current non-serialized properties
        self.current_maximum_occupancy = 0
        self.provided = dict()
        self.current_services_offered = dict()
        self.visiting_customers = list()
        self.maximum_customers_satisfied = dict()
        self.sales = list()

    """
    Business Data
    """

    def get_name(self):
        return self.business_status.get_name()

    def set_name(self, name):
        self.business_status.set_name(name)

    def get_data_pack(self):
        return self.data_pack

    async def set_data_pack(self, data_pack):
        self.recorded_active_state_modifiers.clear()
        self.recorded_inactive_state_modifiers.clear()
        self.recorded_removed_state_modifiers.clear()
        self.__clear_state_views()

        # Validate our data pack
        if self.business_status.get_data_pack_name() != "" and self.business_status.get_data_pack_name() != data_pack.get_name():
            print("Cannot load the provided business as the specifed data pack is not present.")
            return
        self.data_pack = data_pack

        # Apply to our business
        self.business_status.set_data_pack(data_pack)

        # Apply the data pack's initial
        initials = self.data_pack.get_initial_states()
        for initial in initials:
            self.recorded_active_state_modifiers[initial.get_key()] = initial.get_key()

        # Re-play our history
        history = self.business_status.get_history()
        for item in history.values():
            item.apply(self)

        # Get all of our possible things we could apply
        await self.recalculate_state_views()

    def get_business_status(self):
        return self.business_status

    def get_properties(self):
        return self.properties

    def get_improveable(self):
        return self.possible_improvements

    def get_improvements(self):
        return self.active_improvements

    async def apply_improvement(self, improvement, amount, current_day):
        if improvement not in self.possible_improvements:
            print("There is something wrong - someone told us we could load: " + improvement + " but the data pack could not find it!")
            return False

        # Apply it to our history and our current controller
        await self.business_status.purchase_improvement(self, improvement, current_day, amount)

        # Recalc what purchases can be applied
        await self.recalculate_state_views()

    def get_contractable(self):
        return self.possible_contracts

    def get_contracts(self):
        return self.active_contracts

    async def apply_contract(self, contract, amount, start_date):
        if contract not in self.possible_contracts:
            print("There is something wrong - someone told us we could load: " + contract + " but the data pack could not find it!")
            return

        # Apply it to our history and our current controller
        await self.business_status.purchase_contract(self, contract, start_date, negotiated_amount=amount)

        # Recalc what purchases can be applied
        await self.recalculate_state_views()

    def get_hireable(self):
        return self.possible_employee_types

    def get_employees(self):
        return self.active_employees

    async def hire_employee(self, employee_type, name, start_date):
        if employee_type not in self.possible_employee_types:
            print("There is something wrong - someone told us we could load: " + employee_type + " but the data pack could not find it!")
            return

        # Apply it to our history and our current controller
        await self.business_status.hire_employee(self, employee_type, name, start_date)

        # Recalc what purchases can be applied
        await self.recalculate_state_views()

    def get_interested_customers(self):
        return self.available_customers

    def get_most_recent_customer_history(self):
        return self.business_status.get_customer_history_for_week(-1)

    def get_services_offered(self):
        return self.available_services

    def get_most_recent_sales_history(self):
        return self.business_status.get_sales_history_for_week(-1)

    def get_maximum_occupancy(self):
        return self.current_maximum_occupancy

    def set_maximum_occupancy(self, value):
        self.current_maximum_occupancy = value

    async def save(self, game_master, ctx):
        await game_master.save_game_data(ctx, "businesses", self.get_name(), self.business_status)

    """
    Business State Machine Mechanics
    """

    async def recalculate_state_views(self):
        self.__clear_state_views()

        # Work through our actives and assess if they can still function
        processing = True
        unchecked = self.recorded_active_state_modifiers.copy()
        while processing:
            cant_apply = dict()
            for key, value in unchecked.items():
                item = self.data_pack.get_state_modifier(value)

                if await self.__can_apply(item):
                    if isinstance(item, Improvement):
                        self.active_improvements.append(self.business_status.get_historical_purchase(key))
                    elif isinstance(item, Contract):
                        self.active_contracts.append(self.business_status.get_historical_purchase(key))
                    elif isinstance(item, Employee):
                        self.active_employees.append(self.business_status.get_historical_purchase(key))

                    await self.__apply_state_modifier(item)
                else:
                    cant_apply[key] = item

            if len(unchecked) == len(cant_apply):
                self.implied_inactive_state_modifiers = cant_apply
                processing = False
            else:
                unchecked = cant_apply

        # Recalc our basic business properties
        await self.__determine_self_occupancy()

        # Available services & amounts
        all_services = self.data_pack.get_services()
        for service in all_services:
            if await self.__can_apply(service):
                amount_of_service_provided = await self.__calculate_amount_of_service_provided(service)
                cost_price_of_service = await self.__calculate_cost_price_of_service(service)
                sale_price_of_service = await self.__calculate_sale_price_of_service(service)
                service_state = ServiceState(amount_of_service_provided, cost_price_of_service, sale_price_of_service)
                self.available_services[service.get_key()] = service_state

        # Available customers
        all_customers = self.data_pack.get_customers()
        for customer in all_customers:
            if await self.__can_apply(customer) and await self.__can_supply(customer):
                self.available_customers.append(customer)

        # Determine purchaseables
        all_purchaseables = self.data_pack.get_improvements()
        for purchaseable in all_purchaseables:
            if await self.__can_apply(purchaseable):
                self.possible_improvements.append(purchaseable)

        all_purchaseables = self.data_pack.get_contracts()
        for purchaseable in all_purchaseables:
            if await self.__can_apply(purchaseable):
                self.possible_contracts.append(purchaseable)

        all_purchaseables = self.data_pack.get_employee_archetypes()
        for purchaseable in all_purchaseables:
            if await self.__can_apply(purchaseable):
                self.possible_employee_types.append(purchaseable)

    def __clear_state_views(self):
        self.active_improvements.clear()
        self.active_contracts.clear()
        self.active_employees.clear()
        self.available_services.clear()
        self.available_customers.clear()
        self.properties.clear()
        self.implied_inactive_state_modifiers.clear()
        self.possible_improvements.clear()
        self.possible_contracts.clear()
        self.possible_employee_types.clear()

    async def _record_active_state_modifiers(self, key, state_modifier):
        if key in self.recorded_inactive_state_modifiers:
            del self.recorded_inactive_state_modifiers[key]

        if key in self.recorded_removed_state_modifiers:
            del self.recorded_removed_state_modifiers[key]

        self.recorded_active_state_modifiers[key] = state_modifier

    async def _deactivate_state_modifier(self, key, state_modifier):
        if key in self.recorded_active_state_modifiers:
            del self.recorded_active_state_modifiers[key]

        if key in self.recorded_removed_state_modifiers:
            del self.recorded_removed_state_modifiers[key]

        self.recorded_inactive_state_modifiers[key] = state_modifier

    async def _remove_state_modifier(self, key, state_modifier):
        if key in self.recorded_active_state_modifiers:
            del self.recorded_active_state_modifiers[key]

        if key in self.recorded_inactive_state_modifiers:
            del self.recorded_inactive_state_modifiers[key]

        self.recorded_removed_state_modifiers[key] = state_modifier

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

    async def __can_supply(self, customer):
        services_required = customer.get_consumed_services()
        for service_consumed in services_required:
            if service_consumed not in self.available_services:
                return False

        return True

    async def __apply_state_modifier(self, state):
        for key, attribute in state.provides.items():
            current_value = ""
            if key in self.properties:
                current_value = self.properties[key]

            await self.__apply_attribute(attribute, current_value)

    async def __apply_attribute(self, attribute, current_val):
        if isinstance(attribute, FixedAttribute):
            self.properties[attribute.get_key()] = attribute.get_value()
        else:
            # Depending on our type.
            type = attribute.get_type()

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

    async def __determine_self_occupancy(self):
        if Customer.all_customers_maximum_occupancy_modifier in self.properties:
            self.set_maximum_occupancy(self.properties[Customer.all_customers_maximum_occupancy_modifier])
        else:
            self.set_maximum_occupancy(0)

    async def __calculate_amount_of_service_provided(self, service):
        modifier_tags = service.get_volume_modifiers()
        modifier_tags.append(ServiceOffered.global_maximum_service_amount_of_units_offered)
        results = list()
        for modifier_tag in modifier_tags:
            if modifier_tag in self.properties:
                results.append(self.properties[modifier_tag])

        return min(results)

    async def __calculate_cost_price_of_service(self, service):
        base_cost = service.cost
        modifier_tags = service.get_cost_value_modifiers()
        modifier_tags.append(ServiceOffered.global_service_unit_cost_modifier)
        for modifier_tag in modifier_tags:
            if modifier_tag in self.properties:
                self.__apply_attribute()

        pass

    async def __calculate_sale_price_of_service(self, service):
        pass
    #
    # def determine_visiting_patron_types(self):
    #     for patron_type in self.data_pack.get_patrons():
    #         if self.provides_for(patron_type):
    #             self.visiting_patrons.append(patron_type)

    """
    Business Simulation Mechanics
    """
    async def pass_day(self, ctx, game):
        pass

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
    #         self.business_status.add_purchase(purchase)
    #
    #     elif isinstance(purchase, Staff):
    #         self.business_status.add_staff(purchase)
    #
    #     self.provided.update(purchase.get_provided())
    #
    # def add_purchase(self, purchase):
    #     # TODO Inform business status for logging
    #     self.business_status.purchase(purchase)
    #     self.__apply_state(purchase)
    #
    # def hire_staff(self, staff, amount=1):
    #     for i in range(0, amount):
    #         self.apply_purchase(staff)
    #
    # def clear(self):
    #     # TODO: THIS IS NOT THE SAME
    #     self.business_status.clear()
    #
    # async def validate(self):
    #     # Gather our purchases
    #     all_purchases = list()
    #
    #     # Check purchases
    #     possible_purchases = self.business_status.get_purchases()
    #     for possible_purchase in possible_purchases:
    #         purchase = self.data_pack.get_improvement(possible_purchase)
    #         if purchase is not None and self.provides_for(purchase):
    #             all_purchases.append(purchase)
    #
    #     # Check staff
    #     possible_staff = self.business_status.get_staff().keys()
    #     for possible_staff_member in possible_staff:
    #         staff = self.data_pack.get_staff_archetype(possible_staff_member)
    #         if staff is not None and self.provides_for(staff):
    #             all_purchases.append(staff)
    #
    #     # Clear our status
    #     self.business_status.clear()
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
    # def simulate_attendance(self, tenday):
    #     # Simulate the number and type of patrons served
    #     # For each patron type available get the status' for our current business status
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
    #         current_improvements = self.business_status.get_purchases()
    #         for improvement_key in current_improvements:
    #             improvement = self.data_pack.get_improvement(improvement_key)
    #
    #             applicable_values = improvement.get_provided_value(patron_type.get_mean_patron_occupancy_additive_tag())
    #             avg_occupancy.extend(applicable_values)
    #
    #             applicable_values = improvement.get_provided_value(patron_type.get_maximum_patron_occupancy_limit_tags())
    #             max_occupancy_for_patron_type.extend(applicable_values)
    #
    #         # Determine simulation parameters
    #         max_occupancy_for_patron_type = min(max_occupancy_for_patron_type)
    #         avg_occupancy = sum(avg_occupancy)
    #         simulated = stats.norm.ppf(tenday.get_popularity() / 100, loc=avg_occupancy, scale=avg_occupancy / 2)
    #
    #         # Staff can modify the popularity of the place
    #         # TODO: Should these instead affect the tenday popularity? It would certainly be less drastic
    #         for staff, amount in self.business_status.get_staff().items():
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
