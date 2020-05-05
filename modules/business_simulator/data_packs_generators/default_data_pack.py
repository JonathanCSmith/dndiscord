import os
import sys

from modules.business_simulator.model.data_pack import BusinessStateModifier, FixedAttribute, ModifiesAttribute, Improvement, Conditional, BusinessDataPack, ServiceOffered, Customer, Employee, Contract
from utils import data


def create_default_data_pack(path):
    data_pack = BusinessDataPack("default_data_pack", path, False, business_name="business.trollskull_manor", description="business.trollskull_manor.description")

    data_pack = add_initial_tavern_states(data_pack)
    data_pack = add_basic_rebuild_purchases(data_pack)

    # Tier 1
    data_pack = add_services(data_pack)
    data_pack = add_customers(data_pack)
    data_pack = add_employees(data_pack)
    data_pack = add_basic_drinks_prerequisites(data_pack)

    return data_pack


def add_initial_tavern_states(data_pack):
    trollskull_manor_outset = BusinessStateModifier("trollskull_manor")
    trollskull_manor_outset.append_provided(FixedAttribute("trollskull_manor_land", 0))
    trollskull_manor_outset.append_provided(FixedAttribute("trollskull_manor_land.private_street", 0))
    trollskull_manor_outset.append_provided(FixedAttribute("trollskull_manor_land.outdoor_lighting", 0))
    trollskull_manor_outset.append_provided(FixedAttribute("trollskull_manor_land.outdoor_signage", 0))
    data_pack.add_initial(trollskull_manor_outset)

    main_building = BusinessStateModifier("trollskull_manor_building")
    main_building.append_provided(FixedAttribute("trollskull_manor_building.appearance", 0))
    main_building.append_provided(FixedAttribute("trollskull_manor_building.condition", 0))
    main_building.append_provided(FixedAttribute("trollskull_manor_building.roof.condition", 0))
    main_building.append_provided(FixedAttribute("trollskull_manor_building.attic.condition", 0))
    main_building.append_provided(FixedAttribute("trollskull_manor_building.furnishings.condition", 0))
    main_building.append_provided(FixedAttribute("trollskull_manor_building.windows.condition", 0))
    main_building.append_provided(FixedAttribute("trollskull_manor_building.basement.condition", 0))
    main_building.append_provided(FixedAttribute("trollskull_manor_building.utilities.state", "off"))
    main_building.append_provided(FixedAttribute("trollskull_manor_building.roof_slot", 0))
    main_building.append_provided(FixedAttribute("trollskull_manor_building.communal_spaces.count", 7))
    main_building.append_provided(FixedAttribute("trollskull_manor_building.rooms.count", 30))
    main_building.append_provided(FixedAttribute("trollskull_manor_building.bathrooms.count", 7))
    data_pack.add_initial(main_building)

    # Add the kitchen and utilities building
    kitchen_and_utilities_building = BusinessStateModifier("kitchen_and_utilities_building")
    kitchen_and_utilities_building.append_provided(FixedAttribute("kitchen_and_utilities_building.condition", 0))
    kitchen_and_utilities_building.append_provided(FixedAttribute("kitchen_and_utilities_building.utilities.state", "off"))
    data_pack.add_initial(kitchen_and_utilities_building)

    # Add the stable and warehouse building
    stable_and_warehouse_building = BusinessStateModifier("stable_and_warehouse_building")
    stable_and_warehouse_building.append_provided(FixedAttribute("stable_and_warehouse_building.condition", 0))
    stable_and_warehouse_building.append_provided(FixedAttribute("stable_and_warehouse_building.utilities.state", "off"))
    data_pack.add_initial(stable_and_warehouse_building)

    # Add the garden
    garden = BusinessStateModifier("garden_plots")
    garden.append_provided(FixedAttribute("garden_plots.condition", 0))
    data_pack.add_initial(garden)

    return data_pack


def add_basic_rebuild_purchases(data_pack):
    manor_repair = Improvement("trollskull_manor_building_repair", 30000, 1)
    manor_repair.append_prerequisite(Conditional("has", "trollskull_manor_building.condition", ""))
    manor_repair.append_prerequisite(Conditional("equals", "trollskull_manor_building.condition", 0))
    manor_repair.append_prerequisite(Conditional("has", "trollskull_manor_building.windows.condition", ""))
    manor_repair.append_prerequisite(Conditional("equals", "trollskull_manor_building.windows.condition", 0))
    manor_repair.append_prerequisite(Conditional("has", "trollskull_manor_building.basement.condition", ""))
    manor_repair.append_prerequisite(Conditional("equals", "trollskull_manor_building.basement.condition", 0))
    manor_repair.append_provided(FixedAttribute("trollskull_manor_building.condition", 1))
    manor_repair.append_provided(FixedAttribute("trollskull_manor_building.windows.condition", 1))
    manor_repair.append_provided(FixedAttribute("trollskull_manor_building.basement.condition", 1))
    manor_repair.append_provided(FixedAttribute("trollskull_manor_building.appearance", 1))
    data_pack.add_improvement(manor_repair)

    roof_repair = Improvement("trollskull_manor_building_repair_roof", 30000, 1)
    roof_repair.append_prerequisite(Conditional("has", "trollskull_manor_building.attic", ""))
    roof_repair.append_prerequisite(Conditional("equals", "trollskull_manor_building.attic", 0))
    roof_repair.append_prerequisite(Conditional("has", "trollskull_manor_building.roof.condition", ""))
    roof_repair.append_prerequisite(Conditional("equals", "trollskull_manor_building.roof.condition", 0))
    roof_repair.append_provided(FixedAttribute("trollskull_manor_building.roof.condition", 4))
    roof_repair.append_provided(FixedAttribute("trollskull_manor_building.attic", 1))
    data_pack.add_improvement(roof_repair)

    plumbing_repair = Improvement("trollskull_manor_building.services.repair", 10000, 1)
    plumbing_repair.append_prerequisite(Conditional("equals", "trollskull_manor_building.utilities.state", "off"))
    plumbing_repair.append_provided(FixedAttribute("trollskull_manor_building.utilities.state", "on"))
    data_pack.add_improvement(plumbing_repair)

    return data_pack


def add_services(data_pack):
    basic_drinks = ServiceOffered("basic_drinks", 1, 2, cost_value_modifiers=["drinks_unit_cost_modifier"], sale_value_modifiers=["drinks_unit_sales_modifier"])
    basic_drinks.append_prerequisite(Conditional("has", "basic_drinks_supplied", ""))
    basic_drinks.append_prerequisite(Conditional("has", "basic_drinks_stored", ""))
    basic_drinks.append_prerequisite(Conditional("has", "basic_drinks_sold", ""))
    basic_drinks.append_prerequisite(Conditional("has", "basic_drinks_served", ""))
    data_pack.add_service(basic_drinks)
    return data_pack


def add_customers(data_pack):
    commoner_patron = Customer("common_patron", 2)
    commoner_patron.add_consumed_service("basic_drinks", 5)
    data_pack.add_customer(commoner_patron)

    rough_patron = Customer("rough_patron", 1)
    rough_patron.add_consumed_service("basic_drinks", 3)
    data_pack.add_customer(rough_patron)
    return data_pack


def add_employees(data_pack):
    barstaff = Employee("barstaff", 10)
    barstaff.append_prerequisite(Conditional("has", "taproom", ""))
    barstaff.append_provided(ModifiesAttribute("basic_drinks_served", 80, "add"))
    barstaff.append_provided(FixedAttribute("barstaff", ""))
    # TODO: When we know how these tags are going to work:
    """
    maintenance
    tip rate
    """
    data_pack.add_employee_archetype(barstaff)

    return data_pack


def add_basic_drinks_prerequisites(data_pack):
    basic_taproom = Improvement("basic_tap_room", 25000, 10)
    basic_taproom.append_prerequisite(Conditional("doesnt_have", "trollskull_manor_building.taproom", ""))
    basic_taproom.append_prerequisite(Conditional("doesnt_equal", "trollskull_manor_building.condition", 0))
    basic_taproom.append_prerequisite(Conditional("doesnt_equal", "trollskull_manor_building.roof.condition", 0))
    basic_taproom.append_prerequisite(Conditional("doesnt_equal", "trollskull_manor_building.windows.condition", 0))
    basic_taproom.append_prerequisite(Conditional("doesnt_equal", "trollskull_manor_building.utilities.state", "off"))
    basic_taproom.append_prerequisite(Conditional("has", "refuse_services", ""))
    basic_taproom.append_provided(FixedAttribute("basic_drinks_sold", 200))
    basic_taproom.append_provided(FixedAttribute("trollskull_manor_building.taproom", 1))
    basic_taproom.append_provided(FixedAttribute("taproom", 1))
    # TODO: Furninshing
    basic_taproom.append_provided(ModifiesAttribute("common_patron_popularity_modifier", 10, "add"))
    basic_taproom.append_provided(ModifiesAttribute("rough_patron_popularity_modifier", 2, "add"))
    basic_taproom.append_provided(ModifiesAttribute("all_customers_maximum_occupancy_modifier", 50, "add"))
    data_pack.add_improvement(basic_taproom)

    basic_cellar = Improvement("basic_basement_storeroom", 5000, 5)
    basic_cellar.append_prerequisite(Conditional("doesnt_have", "trollskull_manor_building.basement.cellar", ""))
    basic_cellar.append_prerequisite(Conditional("doesnt_equal", "trollskull_manor_building.basement.condition", 0))
    basic_cellar.append_provided(FixedAttribute("trollskull_manor_building.basement.cellar", 1))
    basic_cellar.append_provided(ModifiesAttribute("basic_drinks_stored", 500, "add"))
    data_pack.add_improvement(basic_cellar)

    taproom_license_long = Contract("taproom_guild_license_long", 10000, 365)
    taproom_license_long.append_prerequisite(Conditional("doesnt_have", "taproom_guild_license", ""))
    taproom_license_long.append_provided(FixedAttribute("taproom_guild_license", "YES"))
    data_pack.add_contract(taproom_license_long)

    taproom_license_medium = Contract("taproom_guild_license_medium", 1000, 30)
    taproom_license_medium.append_prerequisite(Conditional("doesnt_have", "taproom_guild_license", ""))
    taproom_license_medium.append_provided(FixedAttribute("taproom_guild_license", "YES"))
    data_pack.add_contract(taproom_license_medium)

    taproom_license_short = Contract("taproom_guild_license_short", 350, 10)
    taproom_license_short.append_prerequisite(Conditional("doesnt_have", "taproom_guild_license", ""))
    taproom_license_short.append_provided(FixedAttribute("taproom_guild_license", "YES"))
    data_pack.add_contract(taproom_license_short)

    street_services_long = Contract("street_services_long", 10000, 365)
    street_services_long.append_prerequisite(Conditional("doesnt_have", "street_services", ""))
    street_services_long.append_provided(FixedAttribute("street_services", "YES"))
    data_pack.add_contract(street_services_long)

    street_services_medium = Contract("street_services_medium", 1000, 30)
    street_services_medium.append_prerequisite(Conditional("doesnt_have", "street_services", ""))
    street_services_medium.append_provided(FixedAttribute("street_services", "YES"))
    data_pack.add_contract(street_services_medium)

    street_services_short = Contract("street_services_short", 350, 10)
    street_services_short.append_prerequisite(Conditional("doesnt_have", "street_services", ""))
    street_services_short.append_provided(FixedAttribute("street_services", "YES"))
    data_pack.add_contract(street_services_short)

    water_services_long = Contract("water_services_long", 10000, 365)
    water_services_long.append_prerequisite(Conditional("doesnt_have", "water_services", ""))
    water_services_long.append_provided(FixedAttribute("water_services", "YES"))
    data_pack.add_contract(water_services_long)

    water_services_medium = Contract("water_services_medium", 1000, 30)
    water_services_medium.append_prerequisite(Conditional("doesnt_have", "water_services", ""))
    water_services_medium.append_provided(FixedAttribute("water_services", "YES"))
    data_pack.add_contract(water_services_medium)

    water_services_short = Contract("water_services_short", 350, 10)
    water_services_short.append_prerequisite(Conditional("doesnt_have", "water_services", ""))
    water_services_short.append_provided(FixedAttribute("water_services", "YES"))
    data_pack.add_contract(water_services_short)

    refuse_services_year = Contract("refuse_services_long", 10000, 365)
    refuse_services_year.append_prerequisite(Conditional("doesnt_have", "refuse_services", ""))
    refuse_services_year.append_provided(FixedAttribute("refuse_services", "YES"))
    data_pack.add_contract(refuse_services_year)

    refuse_services_month = Contract("refuse_services_medium", 1000, 30)
    refuse_services_month.append_prerequisite(Conditional("doesnt_have", "refuse_services", ""))
    refuse_services_month.append_provided(FixedAttribute("refuse_services", "YES"))
    data_pack.add_contract(refuse_services_month)

    refuse_services_short = Contract("refuse_services_short", 359, 10)
    refuse_services_short.append_prerequisite(Conditional("doesnt_have", "refuse_services", ""))
    refuse_services_short.append_provided(FixedAttribute("refuse_services", "YES"))
    data_pack.add_contract(refuse_services_short)

    supply_basic_drinks_contract = Contract("drinks_guild_license_long", 10000, 365)
    supply_basic_drinks_contract.append_prerequisite(Conditional("doesnt_have", "basic_drinks_supplied", ""))
    supply_basic_drinks_contract.append_provided(FixedAttribute("basic_drinks_supplied", ""))
    data_pack.add_contract(supply_basic_drinks_contract)

    supply_basic_drinks_contract = Contract("drinks_guild_license_medium", 1000, 30)
    supply_basic_drinks_contract.append_prerequisite(Conditional("doesnt_have", "basic_drinks_supplied", ""))
    supply_basic_drinks_contract.append_provided(FixedAttribute("basic_drinks_supplied", ""))
    data_pack.add_contract(supply_basic_drinks_contract)

    supply_basic_drinks_contract = Contract("drinks_guild_license_short", 350, 10)
    supply_basic_drinks_contract.append_prerequisite(Conditional("doesnt_have", "basic_drinks_supplied", ""))
    supply_basic_drinks_contract.append_provided(FixedAttribute("basic_drinks_supplied", ""))
    data_pack.add_contract(supply_basic_drinks_contract)

    return data_pack


if __name__ == "__main__":
    dp = create_default_data_pack(sys.argv[1])

    data.save(dp.data_pack_data, os.path.join(dp.path_modifier, dp.name, "data_pack.json"))
    data.save(dp.initial, os.path.join(dp.path_modifier, dp.name, "initial.json"))
    data.save(dp.services, os.path.join(dp.path_modifier, dp.name, "services.json"))
    data.save(dp.employees, os.path.join(dp.path_modifier, dp.name, "employees.json"))
    data.save(dp.customers, os.path.join(dp.path_modifier, dp.name, "customers.json"))
    data.save(dp.improvements, os.path.join(dp.path_modifier, dp.name, "improvements.json"))
    data.save(dp.contracts, os.path.join(dp.path_modifier, dp.name, "contracts.json"))
