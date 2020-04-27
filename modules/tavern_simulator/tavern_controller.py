import os

from scipy import stats

from modules.tavern_simulator.model.data_pack import Patron, Purchase, Staff, DataPack
from modules.tavern_simulator.model.new_data_pack import BusinessState, Attribute, FixedStateAttribute
from modules.tavern_simulator.model.outcomes import Sale
from modules.tavern_simulator.model.tavern import TavernStatus
from utils import math


"""
TODO: When saving the state it may be worth remembering who edited it somehow? so that if we block an upgrade mid path we can remove all relevant upgrades...
"""


# Design goal: Simulate a week (tenday) for a D&D Tavern!
class Tavern:
    @classmethod
    async def load_tavern(cls, manager, game_master, ctx, path_modifier, data_pack=None):
        tavern_status = None
        if game_master and ctx:
            tavern_status = await game_master.load_game_data(ctx, path_modifier, "tavern.json")

        # Ensure we have a data pack when creating the tavern for the first time
        if not tavern_status and not data_pack:
            return None

        # Now we should load our relevant data pack into mem
        if not data_pack:
            data_pack = await DataPack.load_data_pack(manager, ctx, tavern_status.data_pack_path, tavern_status.data_pack_name)

        if not data_pack:
            return None

        # Create our tavern
        tavern = Tavern(data_pack, tavern_status=tavern_status)

        # If its empty the new tavern would have created a tavern state, so we should save it to disk
        if not tavern_status:
            await game_master.save_game_data(ctx, path_modifier, "tavern.json", tavern.get_tavern_status())

        return tavern

    def __init__(self, data_pack, tavern_status=None):
        self.data_pack = data_pack

        # The business state descriptors
        self.properties = dict()

        # Current non-serialized properties
        self.provided = dict()
        self.max_occupancy = 0
        self.current_services_offered = dict()
        self.visiting_patrons = list()
        self.maximum_patrons_satisfied = dict()
        self.sales = list()

        # Create if new
        if not tavern_status:
            self.tavern_status = TavernStatus(self.data_pack.get_name(), self.data_pack.get_path(), self.data_pack.is_guild)
        else:
            self.tavern_status = tavern_status

        # TODO: This should only be when creating status so we dont dupe
        # Apply the data pack's initial? TODO: Move to a func somewhere
        initials = self.data_pack.get_initial()
        for key, initial in initials.items():
            self.apply_state(initial)

    """
    Tavern Data
    """
    def get_name(self):
        return self.tavern_status.get_name()

    def get_data_pack(self):
        return self.data_pack

    def get_properties(self):
        return self.properties

    def get_staff(self):
        return self.tavern_status.get_staff()

    def get_contracts(self):
        return self.tavern_status.get_active_contracts()

    def get_most_recent_customer_history(self):
        return self.tavern_status.get_customer_history_for_week(-1)

    def get_most_recent_sales_history(self):
        return self.tavern_status.get_sales_history_for_week(-1)

    async def save(self, manager, game_master, ctx, path_modifier):
        if manager and game_master and ctx:
            await game_master.save_game_data(ctx, path_modifier, "tavern.json", self.tavern_status)
        else:
            raise RuntimeError("You haven't implemented this yet.")

    """
    Tavern Mechanics
    """

    def add_purchase(self, purchase):
        # TODO Inform tavern status for logging
        self.tavern_status.purchase(purchase)
        self.apply_state(purchase)

    def apply_state(self, state: BusinessState):
        # TODO: Check requirements
        for key, attribute in state.provides.items():
            self.apply_attribute(attribute)

    def apply_attribute(self, attribute):
        if isinstance(attribute, FixedStateAttribute):
            self.properties[attribute.get_key()] = attribute.get_value()
        else:
            raise RuntimeError("You havent made this yet")

    """
    TESTED ZONE IS BELOW
    """

    def get_tavern_status(self):
        return self.tavern_status

    def set_name(self, name):
        self.tavern_status.set_name(name)

    def provides_for(self, data_obj):
        prerequisites = data_obj.get_prerequisites()
        for key, value in prerequisites.items():
            if key not in self.provided:
                return False

        precluded_by = data_obj.get_precluded_by()
        for key, value in precluded_by.items():
            if key in self.provided:
                return False

    def apply_purchase(self, purchase):
        if not self.provides_for(purchase):
            return

        if isinstance(purchase, Purchase):
            self.tavern_status.add_purchase(purchase)

        elif isinstance(purchase, Staff):
            self.tavern_status.add_staff(purchase)

        self.provided.update(purchase.get_provided())

    def add_upgrade(self, upgrade):
        self.apply_purchase(upgrade)

    def hire_staff(self, staff, amount=1):
        for i in range(0, amount):
            self.apply_purchase(staff)

    def clear(self):
        self.tavern_status.clear()

    async def validate(self):
        # Gather our purchases
        all_purchases = list()

        # Check purchases
        possible_purchases = self.tavern_status.get_purchases()
        for possible_purchase in possible_purchases:
            purchase = self.data_pack.get_purchaseable(possible_purchase)
            if purchase is not None and self.provides_for(purchase):
                all_purchases.append(purchase)

        # Check staff
        possible_staff = self.tavern_status.get_staff().keys()
        for possible_staff_member in possible_staff:
            staff = self.data_pack.get_staff_archetype(possible_staff_member)
            if staff is not None and self.provides_for(staff):
                all_purchases.append(staff)

        # Clear our status
        self.tavern_status.clear()

        # Now validate whether or not our purchases are viable
        remaining_purchases = len(all_purchases)
        while remaining_purchases > 0:
            applied_purchases = list()
            for possible_purchase in all_purchases:

                # Check if all prerequisites are met
                if self.provides_for(possible_purchase):
                    self.apply_purchase(possible_purchase)
                    applied_purchases.append(possible_purchase)

            all_purchases = [i for i in all_purchases if i not in applied_purchases]
            sz = len(all_purchases)
            if sz == remaining_purchases:
                break

            remaining_purchases = sz

    def get_maximum_occupancy(self):
        return self.max_occupancy

    def set_maximum_occupancy(self, value):
        self.max_occupancy = value

    def add_service_offered(self, service, max_offered):
        self.provided.update(service.get_provided())
        self.current_services_offered[service.name] = max_offered

    def get_visiting_patrons(self):
        return self.visiting_patrons

    def consume_service(self, service, amount, patron_type):
        remaining = self.current_services_offered[service.name]
        if remaining == 0:
            return False

        remaining -= amount
        if remaining < 0:
            self.current_services_offered[service.name] = 0
            self.sales.append(Sale(service.name, amount + remaining, patron_type.name))
            return False
        else:
            self.current_services_offered[service.name] = remaining
            self.sales.append(Sale(service.name, amount, patron_type.name))
            return True

    def simulate(self, tenday):
        """

        Dynamic Costings
        1) Determine what services are available
        2) Ascertain our maximum services

        Staff interlude
            Staff:
                affect popularity
                increase service transitions (TODO: Tiered services)
                tips ?
                affect maintenance costs (bouncers)
                affect number of services

        3) Simulate the number of patrons that could have come and limit by 2)
        4) For each patron type
            4a) Determine what services would be consumed
            4b) How many of those services per patron visit would be consumed
            4c) Store each successful sale
        5) Determine sale modifiers
        6) Sum

        Fixed Costings:

        :param tenday:
        :return:
        """

        # Calculate our flat max occupancy
        self.determine_max_occupancy()

        # Identify which services we can provide
        self.determine_available_services()

        # Determine what patron types are available to us
        self.determine_visiting_patron_types()

        # Simulate attendance
        self.simulate_attendance(tenday)

        # Serve our patrons as much as we can
        self.serve_patrons()

        """
        We now need to calculate the profits and costs per sale (incl tips)
        
        Dynamic maintenance costs
        
        Fixed costs
        
        Fixed earnings
        """

    def determine_max_occupancy(self):
        max_occupancy_modifiers = list()
        for upgrade_key in self.tavern_status.get_purchases():
            upgrade = self.data_pack.get_purchaseable(upgrade_key)
            max_occupancy_modifiers.extend(upgrade.get_provided_value(Patron.maximum_occupancy_limit_tag))
        self.set_maximum_occupancy(sum(max_occupancy_modifiers))

    def determine_available_services(self):
        # TODO: Move away from sets as it would allow for multiple of the same requirements
        for service in self.data_pack.get_services():
            remaining_requirements = set(service.get_prerequisites())

            # Remove any things provided by our upgrades
            for upgrade_key in self.tavern_status.get_purchases():
                upgrade = self.data_pack.get_purchaseable(upgrade_key)
                provided = upgrade.get_provided()
                remaining_requirements = remaining_requirements.difference(provided)

            # Remove any things provided by our staff:
            for staff in self.tavern_status.get_staff():
                staff_archetype = self.data_pack.get_staff_archetype(staff)
                provided = staff_archetype.get_provided()
                remaining_requirements = remaining_requirements.difference(provided)

            # If all of our requirements were satisfied add the service and calculate the max supplied
            if len(remaining_requirements) == 0:
                max_modifier_tags = service.get_maximum_of_service_offered_tags()

                # Check our upgrade for inhibitions
                applicable_values = list()
                for upgrade_key in self.tavern_status.get_purchases():
                    upgrade = self.data_pack.get_purchaseable(upgrade_key)
                    applicable_values.extend(upgrade.get_provided_value(max_modifier_tags))

                if len(applicable_values) == 0:
                    max_sales_of_service = 0
                else:
                    max_sales_of_service = min(applicable_values)
                self.add_service_offered(service, max_sales_of_service)

    def determine_visiting_patron_types(self):
        for patron_type in self.data_pack.get_patrons():
            if self.provides_for(patron_type):
                self.visiting_patrons.append(patron_type)

    def simulate_attendance(self, tenday):
        # Simulate the number and type of patrons served
        # For each patron type available get the status' for our current tavern status
        for patron_type in self.get_visiting_patrons():
            """
            create a probability curve to represent patron attendance probability

                mean = collect_occupancy_modifier_for_patrons but numerically it should be raw patron count
                std = 50% of mean? (we can fiddle)

                tenday_patron_types_served = use dice roll to indicate where along the bell curve to pick (i.e. is the cumulative probability value or area)
            """

            # Collect all modifiers to avg occupancy and simulate as above
            avg_occupancy = list()
            max_occupancy_for_patron_type = list()
            max_occupancy_for_patron_type.append(self.get_maximum_occupancy())
            current_upgrades = self.tavern_status.get_purchases()
            for upgrade_key in current_upgrades:
                upgrade = self.data_pack.get_purchaseable(upgrade_key)

                applicable_values = upgrade.get_provided_value(patron_type.get_mean_patron_occupancy_additive_tag())
                avg_occupancy.extend(applicable_values)

                applicable_values = upgrade.get_provided_value(patron_type.get_maximum_patron_occupancy_limit_tags())
                max_occupancy_for_patron_type.extend(applicable_values)

            # Determine simulation parameters
            max_occupancy_for_patron_type = min(max_occupancy_for_patron_type)
            avg_occupancy = sum(avg_occupancy)
            simulated = stats.norm.ppf(tenday.get_popularity() / 100, loc=avg_occupancy, scale=avg_occupancy / 2)

            # Staff can modify the popularity of the place
            # TODO: Should these instead affect the tenday popularity? It would certainly be less drastic
            for staff, amount in self.tavern_status.get_staff().items():
                for i in range(0, amount):
                    staff_archetype = self.data_pack.get_staff_archetype(staff)
                    modifiers = staff_archetype.get_provided_value(patron_type.get_mean_patron_occupancy_multiplier_tag())
                    for modifier in modifiers:
                        simulated *= modifier

            # Clamp services and set in simulation result
            services = math.clamp_incl(simulated, 0, max_occupancy_for_patron_type)
            self.maximum_patrons_satisfied[patron_type.name] = services

    def serve_patrons(self):
        """
        Loop through our patrons served and evaluate what services they will consume.
        Sort by priority - under the premise that you serve whales as a priority
        TODO: Modifiy the sales and cost where appropriate
        :return:
        """
        # Sort in order of priority
        for visiting_patron in sorted(self.visiting_patrons, key=self.data_pack.return_priority_order, reverse=True):
            patrons_served = self.maximum_patrons_satisfied[visiting_patron.name]
            services_consumed = visiting_patron.get_services_consumed()

            has_had_a_service_requirement_met = True
            for i in range(0, patrons_served):
                if not has_had_a_service_requirement_met:
                    break

                has_had_a_service_requirement_met = False
                for service_key, amount in services_consumed.items():
                    if service_key in self.current_services_offered:
                        service = self.data_pack.get_service(service_key)
                        has_had_a_service_requirement_met |= self.consume_service(service, amount, visiting_patron)
