import os

from scipy import stats

from module_properties.tavern_simulator.model.data_pack import Patron, Upgrade, Staff
from module_properties.tavern_simulator.model.outcomes import Sale
from utils import math, data


class TavernStatus:
    def __init__(self, tavern_upgrades=None, staff=None):
        if tavern_upgrades is None:
            tavern_upgrades = list()
        if staff is None:
            staff = dict()

        self.tavern_upgrades = tavern_upgrades
        self.staff = staff

    def add_upgrade(self, upgrade):
        self.tavern_upgrades.append(upgrade.name)

    def get_upgrades(self):
        return self.tavern_upgrades

    def set_upgrades(self, upgrades):
        self.tavern_upgrades = upgrades

    def hire_staff(self, staff, amount=1):
        if staff.name in self.staff:
            self.staff[staff.name] += amount
        else:
            self.staff[staff.name] = amount

    def get_staff(self):
        return self.staff

    def clear(self):
        self.tavern_upgrades.clear()
        self.staff.clear()


# Design goal: Simulate a week (tenday) for a D&D Tavern!
class Tavern:
    def __init__(self, tavern_status_file, data_pack):
        self.tavern_status_file = tavern_status_file
        self.data_pack = data_pack

        # Current non-serialized properties
        self.provided = dict()
        self.max_occupancy = 0
        self.current_services_offered = dict()
        self.visiting_patrons = list()
        self.maximum_patrons_satisfied = dict()
        self.sales = list()

        # Force data state to serialize
        self.load()

    def provides_for(self, prerequisites):
        return len(set(prerequisites) - set(self.provided)) == 0

    def apply_purchase(self, purchase):
        if not self.provides_for(purchase.get_prerequisites()):
            return

        if isinstance(purchase, Upgrade):
            self.tavern_status.add_upgrade(purchase)

        elif isinstance(purchase, Staff):
            self.tavern_status.hire_staff(purchase)

        self.provided.update(purchase.get_provided())

    def add_upgrade(self, upgrade):
        self.apply_purchase(upgrade)

    def hire_staff(self, staff, amount=1):
        for i in range(0, amount):
            self.apply_purchase(staff)

    def save(self):
        data.save(self.tavern_status, self.tavern_status_file)

    def load(self):
        if os.path.isfile(self.tavern_status_file):
            self.tavern_status = data.load(self.tavern_status_file)
        else:
            self.tavern_status = TavernStatus()
            self.save()

        self.validate()

    def clear(self):
        self.tavern_status.clear()

    def validate(self):
        # Gather our purchases
        all_purchases = list()

        # Check upgrades
        possible_upgrades = self.tavern_status.get_upgrades()
        for possible_upgrade in possible_upgrades:
            upgrade = self.data_pack.get_upgrade(possible_upgrade)
            if upgrade is not None and self.provides_for(upgrade.get_prerequisites()):
                all_purchases.append(upgrade)

        # Check staff
        possible_staff = self.tavern_status.get_staff().keys()
        for possible_staff_member in possible_staff:
            staff = self.data_pack.get_staff_archetype(possible_staff_member)
            if staff is not None and self.provides_for(staff.get_prerequisites()):
                all_purchases.append(staff)

        # Clear our status
        self.tavern_status.clear()

        # Now validate whether or not our purchases are viable
        remaining_purchases = len(all_purchases)
        while remaining_purchases > 0:
            applied_purchases = list()
            for possible_purchase in all_purchases:
                prerequisites = possible_purchase.get_prerequisites()

                # Check if all prerequisites are met
                if self.provides_for(prerequisites):
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
        for upgrade_key in self.tavern_status.get_upgrades():
            upgrade = self.data_pack.get_upgrade(upgrade_key)
            max_occupancy_modifiers.extend(upgrade.get_provided_value(Patron.maximum_occupancy_limit_tag))
        self.set_maximum_occupancy(sum(max_occupancy_modifiers))

    def determine_available_services(self):
        # TODO: Move away from sets as it would allow for multiple of the same requirements
        for service in self.data_pack.get_services():
            remaining_requirements = set(service.get_prerequisites())

            # Remove any things provided by our upgrades
            for upgrade_key in self.tavern_status.get_upgrades():
                upgrade = self.data_pack.get_upgrade(upgrade_key)
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
                for upgrade_key in self.tavern_status.get_upgrades():
                    upgrade = self.data_pack.get_upgrade(upgrade_key)
                    applicable_values.extend(upgrade.get_provided_value(max_modifier_tags))

                if len(applicable_values) == 0:
                    max_sales_of_service = 0
                else:
                    max_sales_of_service = min(applicable_values)
                self.add_service_offered(service, max_sales_of_service)

    def determine_visiting_patron_types(self):
        for patron_type in self.data_pack.get_patrons():
            if self.provides_for(patron_type.get_prerequisites()):
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
            current_upgrades = self.tavern_status.get_upgrades()
            for upgrade_key in current_upgrades:
                upgrade = self.data_pack.get_upgrade(upgrade_key)

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
