from modules.tavern_simulator.model.new_data_pack import BusinessStateModifier, FixedAttribute, ModifiesAttribute, Upgrade, Conditional, DataPack, ServiceOffered, Customer, Employee, Contract


def create_default_data_pack(path):
    data_pack = DataPack("default_data_pack", path, False, business_name="business.trollskull_manor", description="business.trollskull_manor.description")

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
    trollskull_manor_outset.append_provided(FixedAttribute("trollskull_manor_land", "poor"))
    trollskull_manor_outset.append_provided(FixedAttribute("trollskull_manor_land.private_street", "poor"))
    trollskull_manor_outset.append_provided(FixedAttribute("trollskull_manor_land.outdoor_lighting", "poor"))
    trollskull_manor_outset.append_provided(FixedAttribute("trollskull_manor_land.outdoor_signage", "poor"))
    data_pack.add_initial(trollskull_manor_outset)

    main_building = BusinessStateModifier("trollskull_manor_building")
    main_building.append_provided(FixedAttribute("trollskull_manor_building.appearance", "poor"))
    main_building.append_provided(FixedAttribute("trollskull_manor_building.condition", "poor"))
    main_building.append_provided(FixedAttribute("trollskull_manor_building.roof.condition", "poor"))
    main_building.append_provided(FixedAttribute("trollskull_manor_building.attic.condition", "poor"))
    main_building.append_provided(FixedAttribute("trollskull_manor_building.furnishings.condition", "poor"))
    main_building.append_provided(FixedAttribute("trollskull_manor_building.windows.condition", "poor"))
    main_building.append_provided(FixedAttribute("trollskull_manor_building.basement.condition", "poor"))
    main_building.append_provided(FixedAttribute("trollskull_manor_building.utilities.state", "off"))
    main_building.append_provided(FixedAttribute("trollskull_manor_building.roof_slot", "poor"))
    main_building.append_provided(FixedAttribute("trollskull_manor_building.communal_spaces.count", 7))
    main_building.append_provided(FixedAttribute("trollskull_manor_building.rooms.count", 30))
    main_building.append_provided(FixedAttribute("trollskull_manor_building.bathrooms.count", 7))
    data_pack.add_initial(main_building)

    # Add the kitchen and utilities building
    kitchen_and_utilities_building = BusinessStateModifier("kitchen_and_utilities_building")
    kitchen_and_utilities_building.append_provided(FixedAttribute("kitchen_and_utilities_building.condition", "poor"))
    kitchen_and_utilities_building.append_provided(FixedAttribute("kitchen_and_utilities_building.utilities.state", "off"))
    data_pack.add_initial(kitchen_and_utilities_building)

    # Add the stable and warehouse building
    stable_and_warehouse_building = BusinessStateModifier("stable_and_warehouse_building")
    stable_and_warehouse_building.append_provided(FixedAttribute("stable_and_warehouse_building.condition", "poor"))
    stable_and_warehouse_building.append_provided(FixedAttribute("stable_and_warehouse_building.utilities.state", "off"))
    data_pack.add_initial(stable_and_warehouse_building)

    # Add the garden
    garden = BusinessStateModifier("garden_plots")
    garden.append_provided(FixedAttribute("garden_plots.condition", "poor"))
    data_pack.add_initial(garden)

    return data_pack


def add_basic_rebuild_purchases(data_pack):
    manor_repair = Upgrade("trollskull_manor_building_repair", 30000, 1)
    manor_repair.append_prerequisite(Conditional("has", "trollskull_manor_building.condition", ""))
    manor_repair.append_prerequisite(Conditional("equals", "trollskull_manor_building.condition", "poor"))
    manor_repair.append_prerequisite(Conditional("has", "trollskull_manor_building.windows.condition", ""))
    manor_repair.append_prerequisite(Conditional("equals", "trollskull_manor_building.windows.condition", "poor"))
    manor_repair.append_prerequisite(Conditional("has", "trollskull_manor_building.basement.condition", ""))
    manor_repair.append_prerequisite(Conditional("equals", "trollskull_manor_building.basement.condition", "poor"))
    manor_repair.append_provided(FixedAttribute("trollskull_manor_building.condition", "basic"))
    manor_repair.append_provided(FixedAttribute("trollskull_manor_building.windows.condition", "basic"))
    manor_repair.append_provided(FixedAttribute("trollskull_manor_building.basement.condition", "basic"))
    manor_repair.append_provided(FixedAttribute("trollskull_manor_building.appearance", "basic"))
    data_pack.add_upgrade(manor_repair)

    roof_repair = Upgrade("trollskull_manor_building_repair_roof", 30000, 1)
    roof_repair.append_prerequisite(Conditional("has", "trollskull_manor_building.attic", ""))
    roof_repair.append_prerequisite(Conditional("equals", "trollskull_manor_building.attic", "poor"))
    roof_repair.append_prerequisite(Conditional("has", "trollskull_manor_building.roof.condition", ""))
    roof_repair.append_prerequisite(Conditional("equals", "trollskull_manor_building.roof.condition", "poor"))
    roof_repair.append_provided(FixedAttribute("trollskull_manor_building.roof.condition", "good"))
    roof_repair.append_provided(FixedAttribute("trollskull_manor_building.attic", "basic"))
    data_pack.add_upgrade(roof_repair)

    plumbing_repair = Upgrade("trollskull_manor_building.services.repair", 10000, 1)
    plumbing_repair.append_prerequisite(Conditional("equals", "trollskull_manor_building.utilities.state", "off"))
    plumbing_repair.append_provided(FixedAttribute("trollskull_manor_building.utilities.state", "on"))
    data_pack.add_upgrade(plumbing_repair)

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
    basic_taproom = Upgrade("basic_tap_room", 25000, 10)
    basic_taproom.append_prerequisite(Conditional("doesnt_have", "trollskull_manor_building.taproom", ""))
    basic_taproom.append_prerequisite(Conditional("doesnt_equal", "trollskull_manor_building.condition", "poor"))
    basic_taproom.append_prerequisite(Conditional("doesnt_equal", "trollskull_manor_building.roof.condition", "poor"))
    basic_taproom.append_prerequisite(Conditional("doesnt_equal", "trollskull_manor_building.windows.condition", "poor"))
    basic_taproom.append_prerequisite(Conditional("doesnt_equal", "trollskull_manor_building.utilities.state", "off"))
    basic_taproom.append_prerequisite(Conditional("has", "refuse_services", ""))
    basic_taproom.append_provided(FixedAttribute("basic_drinks_sold", 200))
    basic_taproom.append_provided(FixedAttribute("trollskull_manor_building.taproom", "basic"))
    # TODO: Furninshing
    basic_taproom.append_provided(ModifiesAttribute("common_patron_popularity_modifier", 10, "add"))
    basic_taproom.append_provided(ModifiesAttribute("rough_patron_popularity_modifier", 2, "add"))
    basic_taproom.append_provided(ModifiesAttribute("all_customers_maximum_occupancy_modifier", 50, "add"))
    data_pack.add_upgrade(basic_taproom)

    basic_cellar = Upgrade("basic_basement_storeroom", 5000, 5)
    basic_cellar.append_prerequisite(Conditional("doesnt_have", "trollskull_manor_building.basement.use", ""))
    basic_cellar.append_prerequisite(Conditional("doesnt_equal", "trollskull_manor_building.basement.condition", "poor"))
    basic_cellar.append_provided(ModifiesAttribute("basic_drinks_stored", 500, "add"))
    data_pack.add_upgrade(basic_cellar)

    taproom_license_long = Contract("taproom_guild_license_long", 10000, 365)
    taproom_license_long.append_provided(FixedAttribute("taproom_guild_license", "YES"))
    data_pack.add_contract(taproom_license_long)

    taproom_license_medium = Contract("taproom_guild_license_medium", 1000, 30)
    taproom_license_medium.append_provided(FixedAttribute("taproom_guild_license", "YES"))
    data_pack.add_contract(taproom_license_medium)

    taproom_license_short = Contract("taproom_guild_license_short", 350, 10)
    taproom_license_short.append_provided(FixedAttribute("taproom_guild_license", "YES"))
    data_pack.add_contract(taproom_license_short)

    street_services_long = Contract("street_services_long", 10000, 365)
    street_services_long.append_provided(FixedAttribute("street_services", "YES"))
    data_pack.add_contract(street_services_long)

    street_services_medium = Contract("street_services_medium", 1000, 30)
    street_services_medium.append_provided(FixedAttribute("street_services", "YES"))
    data_pack.add_contract(street_services_medium)

    street_services_short = Contract("street_services_short", 350, 10)
    street_services_short.append_provided(FixedAttribute("street_services", "YES"))
    data_pack.add_contract(street_services_short)

    water_services_long = Contract("water_services_long", 10000, 365)
    water_services_long.append_provided(FixedAttribute("water_services", "YES"))
    data_pack.add_contract(water_services_long)

    water_services_medium = Contract("water_services_medium", 1000, 30)
    water_services_medium.append_provided(FixedAttribute("water_services", "YES"))
    data_pack.add_contract(water_services_medium)

    water_services_short = Contract("water_services_short", 350, 10)
    water_services_short.append_provided(FixedAttribute("water_services", "YES"))
    data_pack.add_contract(water_services_short)

    refuse_services_year = Contract("refuse_services_long", 10000, 365)
    refuse_services_year.append_provided(FixedAttribute("refuse_services", "YES"))
    data_pack.add_contract(refuse_services_year)

    refuse_services_month = Contract("refuse_services_medium", 1000, 30)
    refuse_services_month.append_provided(FixedAttribute("refuse_services", "YES"))
    data_pack.add_contract(refuse_services_month)

    refuse_services_short = Contract("refuse_services_short", 359, 10)
    refuse_services_short.append_provided(FixedAttribute("refuse_services", "YES"))
    data_pack.add_contract(refuse_services_short)

    supply_basic_drinks_contract = Contract("drinks_guild_license_long", 10000, 365)
    supply_basic_drinks_contract.append_provided(FixedAttribute("basic_drinks_supplied", ""))
    data_pack.add_contract(supply_basic_drinks_contract)

    supply_basic_drinks_contract = Contract("drinks_guild_license_long", 1000, 30)
    supply_basic_drinks_contract.append_provided(FixedAttribute("basic_drinks_supplied", ""))
    data_pack.add_contract(supply_basic_drinks_contract)

    supply_basic_drinks_contract = Contract("drinks_guild_license_long", 350, 10)
    supply_basic_drinks_contract.append_provided(FixedAttribute("basic_drinks_supplied", ""))
    data_pack.add_contract(supply_basic_drinks_contract)

    return data_pack
