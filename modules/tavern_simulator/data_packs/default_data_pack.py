import os

from modules.tavern_simulator.model.data_pack import DataPack, Purchase, Contract, Service, Patron, Staff


def create_default_data_pack(path):
    data_pack = DataPack(os.path.join(path, "default_data_pack"))

    # Default data
    data_pack = add_initial_tavern_state(data_pack)
    data_pack = add_rebuilds_from_disrepair(data_pack)
    data_pack = add_tier_1_service(data_pack)
    data_pack = add_patrons(data_pack)
    data_pack = add_staff(data_pack)
    data_pack = add_basic_drinks_service(data_pack)

    return data_pack


def add_initial_tavern_state(data_pack):
    # Add the initial plot of land in
    land = Purchase("trollskull_manor", 0)
    land.append_provided("main_building", "YES")
    land.append_provided("kitchen_and_utilities_building", "YES")
    land.append_provided("stables_and_storage_building", "YES")
    land.append_provided("garden", "YES")
    data_pack.add_initial(land)

    # Add the manor building
    manor_building = Purchase("main_building", 0)
    manor_building.append_provided("main_state", "dilapidated")
    manor_building.append_provided("main_roof", "leaky")
    manor_building.append_provided("main_furnishings", "destroyed")
    manor_building.append_provided("main_glazing", "broken_shutters_only")
    manor_building.append_provided("main_basement", "crumbling_and_unsafe")
    manor_building.append_provided("main_water_services", "non_functional")
    data_pack.add_initial(manor_building)

    # Add the kitchen and utilities building
    kitchen_and_utilities_building = Purchase("kitchen_and_utilities_building", 0)
    kitchen_and_utilities_building.append_provided("kitchen_and_utilities_state", "collapsed")
    kitchen_and_utilities_building.append_provided("kitchen_and_utilities_water_services", "non_functional")
    data_pack.add_initial(kitchen_and_utilities_building)

    # Add the stable and warehouse building
    stable_and_warehouse_building = Purchase("stable_and_warehouse_building", 0)
    stable_and_warehouse_building.append_provided("stable_and_warehouse_state", "collapsed")
    stable_and_warehouse_building.append_provided("stable_and_warehouse_water_services", "non_functional")
    data_pack.add_initial(stable_and_warehouse_building)

    # Add the garden
    garden = Purchase("garden", 0)
    garden.append_provided("garden_state", "overgrown")
    data_pack.add_initial(garden)

    return data_pack


def add_rebuilds_from_disrepair(data_pack):
    """
    """
    manor_repair = Purchase("main_building_repair_full", 300)
    manor_repair.append_prerequisite("main_state", "dilapidated")
    manor_repair.append_prerequisite("main_glazing", "broken_shutters_only")
    manor_repair.append_prerequisite("main_basement", "crumbling_and_unsafe")
    manor_repair.append_provided("main_state", "basic")
    manor_repair.append_provided("main_glazing", "shutters")
    manor_repair.append_provided("main_basement", "small_sturdy")
    data_pack.add_purchaseable(manor_repair)

    roof_repair = Purchase("main_building_roof_repair", 300)
    roof_repair.append_prerequisite("main_roof", "leaky")
    roof_repair.append_provided("main_roof", "repaired")
    data_pack.add_purchaseable(roof_repair)

    plumbing_repair = Purchase("plumbing_repair", 100)
    plumbing_repair.append_prerequisite("main_water_services", "non_functional")
    plumbing_repair.append_provided("main_water_services", "functional")
    data_pack.add_purchaseable(plumbing_repair)

    return data_pack


def add_tier_1_service(data_pack):

    # Offer basic drinks
    basic_drinks_key_vals = dict()
    basic_drinks_key_vals["store_basic_drinks"] = "YES"
    basic_drinks_key_vals["sell_basic_drinks"] = "YES"
    basic_drinks_key_vals["serve_basic_drinks"] = "YES"
    basic_drinks_key_vals["supply_basic_drinks"] = "YES"
    basic_drinks = Service("basic_drinks", 1, 2, prerequisites=basic_drinks_key_vals)
    data_pack.add_service(basic_drinks)

    return data_pack


def add_patrons(data_pack):
    # Need to reference some things
    basic_drinks = data_pack.get_service("basic_drinks")

    # Prebuilt patrons
    commoner_patron = Patron("common_patron", 2, {basic_drinks.name: 5})
    data_pack.add_patron(commoner_patron)
    rough_patron = Patron("rough_patron", 1, {basic_drinks.name: 3})
    data_pack.add_patron(rough_patron)

    return data_pack


def add_staff(data_pack):
    # Need to reference some things
    commoner = data_pack.get_patron("common_patron")
    rough = data_pack.get_patron("rough_patron")

    barstaff = Staff("barstaff", 1)
    barstaff.append_prerequisite("taproom", "YES")
    barstaff.append_provided("maximum_patrons_served", 100)
    barstaff.append_provided(commoner.get_mean_patron_occupancy_multiplier_tag(), 1.1)
    barstaff.append_provided(rough.get_mean_patron_occupancy_multiplier_tag(), 1.2)
    barstaff.append_provided("maintenance_modifier", 1.1)
    barstaff.append_provided("modify_tip_rate", 1.1)
    barstaff.append_provided("serve_basic_drinks", "YES")
    barstaff.append_provided("barstaff", "YES")
    data_pack.add_staff_archetype(barstaff)

    return data_pack


def add_basic_drinks_service(data_pack):
    """
    """

    # Need to reference some things
    commoner = data_pack.get_patron("common_patron")
    rough = data_pack.get_patron("rough_patron")
    basic_drinks = data_pack.get_service("basic_drinks")

    basic_tap_room = Purchase("basic_tap_room", 250)
    basic_tap_room.append_precluded_by("main_state", "dilapidated")
    basic_tap_room.append_precluded_by("main_roof", "leaky")
    basic_tap_room.append_precluded_by("main_glazing", "broken_shutters_only")
    basic_tap_room.append_prerequisite("main_water_services", "functional")
    basic_tap_room.append_provided("main_furnishings", "basic")
    basic_tap_room.append_provided("sell_basic_drinks", "YES")
    basic_tap_room.append_provided("taproom", "basic")
    basic_tap_room.append_provided(commoner.get_mean_patron_occupancy_additive_tag(), 10)
    basic_tap_room.append_provided(rough.get_mean_patron_occupancy_additive_tag(), 2)
    basic_tap_room.append_provided(Patron.maximum_occupancy_limit_tag, 50)
    data_pack.add_purchaseable(basic_tap_room)

    basic_basement_storeroom = Purchase("basic_basement_storeroom", 50)
    basic_basement_storeroom.append_precluded_by("main_basement", "crumbling_and_unsafe")
    basic_basement_storeroom.append_provided("maximum_drinks", 50)
    basic_basement_storeroom.append_provided(basic_drinks.get_maximum_of_service_offered_tags(), 50)
    basic_basement_storeroom.append_provided("store_basic_drinks", "YES")

    taproom_license_long = Contract("taproom_guild_license_long", 50, 36)
    taproom_license_long.append_provided("taproom_guild_license", "YES")
    data_pack.add_contract(taproom_license_long)

    taproom_license_medium = Contract("taproom_guild_license_medium", 50, 3)
    taproom_license_medium.append_provided("taproom_guild_license", "YES")
    data_pack.add_contract(taproom_license_medium)

    taproom_license_short = Contract("taproom_guild_license_short", 50, 1)
    taproom_license_short.append_provided("taproom_guild_license", "YES")
    data_pack.add_contract(taproom_license_short)

    street_services_long = Contract("street_services_long", 50, 36)
    street_services_long.append_provided("street_services", "YES")
    data_pack.add_contract(street_services_long)

    street_services_medium = Contract("street_services_medium", 50, 3)
    street_services_medium.append_provided("street_services", "YES")
    data_pack.add_contract(street_services_medium)

    street_services_short = Contract("street_services_short", 50, 1)
    street_services_short.append_provided("street_services", "YES")
    data_pack.add_contract(street_services_short)

    water_services_long = Contract("water_services_long", 50, 36)
    water_services_long.append_provided("water_services", "YES")
    data_pack.add_contract(water_services_long)

    water_services_medium = Contract("water_services_medium", 50, 36)
    water_services_medium.append_provided("water_services", "YES")
    data_pack.add_contract(water_services_medium)

    water_services_short = Contract("water_services_short", 50, 36)
    water_services_short.append_provided("water_services", "YES")
    data_pack.add_contract(water_services_short)

    refuse_services_year = Contract("refuse_services_long", 50, 36)
    refuse_services_year.append_provided("refuse_services", "YES")
    data_pack.add_contract(refuse_services_year)

    refuse_services_month = Contract("refuse_services_medium", 50, 3)
    refuse_services_month.append_provided("refuse_services", "YES")
    data_pack.add_contract(refuse_services_month)

    refuse_services_short = Contract("refuse_services_short", 50, 1)
    refuse_services_short.append_provided("refuse_services", "YES")
    data_pack.add_contract(refuse_services_short)

    supply_basic_drinks_contract_good = Contract("supply_basic_drinks_contract_poor", 0, 36, hidden=True)
    supply_basic_drinks_contract_good.append_provided("supply_basic_drinks", 8)
    data_pack.add_contract(supply_basic_drinks_contract_good)

    supply_basic_drinks_contract_medium = Contract("supply_basic_drinks_contract_poor", 0, 36, hidden=True)
    supply_basic_drinks_contract_medium.append_provided("supply_basic_drinks", 9)
    data_pack.add_contract(supply_basic_drinks_contract_medium)

    supply_basic_drinks_contract_poor = Contract("supply_basic_drinks_contract_poor", 0, 36, hidden=True)
    supply_basic_drinks_contract_poor.append_provided("supply_basic_drinks", 10)
    data_pack.add_contract(supply_basic_drinks_contract_poor)

    return data_pack
