from modules.tavern_simulator.model.data_pack import DataPack, Purchase

"""
data_state
"""

"""
Define a current state view for the tavern

    0) Initial: Large plot of land with three buildings and a garden area in the north ward.
        1) Main building: Dilapidated but standing. Destroyed and non functional furnishings. Broken shutters and no glazing. Leaky roof. No water. Crumbling basement.
        2) Kitchen & Utilities: Collapsed
        3) Stables and large goods store: Collapsed
        4) Garden: Overgrown
    
Allow the players to view what upgrades are necessary as well as what services can be offered.

Allow the players to determine what prerequisites are necessary to obtain the above.

Allow players to identify the costs and people to speak to.

Allow players to change the state of the tavern over time.=


Data pack initial sketched:

    INITIAL STATES (IMPL ALREADY)
    
    Repair manor:
        Requires:
            main_state: dilapidated
            main_glazing: broken_shutters
            main_basement: crumbling
        Provides:
            main_state: basic
            main_glazing: shutters
            main_basement: small_sturdy            
    
    Roof repair:
        Requires:
            main_roof: NOT repaired
        Provides:
            main_roof: repaired
            
    Plumbing repair:
        Requires:
            main_water_services: NOT functional
        Provides:
            main_water_services: functional
    
    Basic tap room:
        Requires:
            main_state: NOT dilapidated
            main_roof: NOT leaky
            main_glazing: NOT broken_shutters
            main_basement: NOT crumbling
            main_water_services: functional
        Provides:
            main_furnishings: basic
            taproom: basic
            
    Basic drinks supply contract:
        Provides:
            basic_drinks_supply
            
    Taproom Guild Licenses contact:
        Provides:
            taproom_guild_licenses
            
    Street services contact:
        Provides:
            street_services
            
    Water services contact:
        Provides:
            water_services
            
    Refuse services contact:
        Provides:
            bin_services
        
    Basic drinks service:
        Requires:
            basic_drinks_supply
            taproom: ANY
            taproom_guild_licenses
            street_services
            water_services
            bin_services       

# TODO: Add unacceptable to purchases (and other things??). Unacceptable will provide us with the functionality of 'must not have this tag' but we are still missing 'must have one of these tags'. However, in a roundabout manner one could be used to achieve the other?
# TODO: Find a way of mapping tag keys and tag values to translation packs. Namely:
    default_language_pack:
        key: "Human readable representation of this key"
        key.value: "Human readable representation of this value of this key" 
"""


def create_default_data_pack(force):
    data_pack = DataPack("./default_data_pack/.")

    # We have already serialized out this before (or someone has provided their own) so just return
    if not force and len(data_pack.get_patrons()) != 0:
        return data_pack

    # Default data
    data_pack = add_initial_tavern_state(data_pack)
    data_pack = add_rebuilds_from_disrepair(data_pack)
    data_pack = add_minimum_living_services(data_pack)

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
    manor_building.append_provided("main_shutters", "swinging_wildly")
    manor_building.append_provided("main_glazing", "smashed")
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
    # Fix the roof
    roof_key_vals = dict()
    roof_key_vals["functional_roof"] = "YES"
    roof = Purchase("main_roof", 300, provides=roof_key_vals)
    data_pack.add_purchaseable(roof)

    # General repair
    repair_key_vals = dict()
    repair_key_vals["basic_living_environment"] = "YES"
    repair = Purchase("basic_repair", 150, provides=repair_key_vals)
    data_pack.add_purchaseable(repair)

    # Service repair
    service_key_vals = dict()
    service_key_vals["has_water"] = "YES"
    service_key_vals["has_sewers"] = "YES"
    services = Purchase("fixed_services", 50, provides=service_key_vals)
    data_pack.add_purchaseable(services)

    return data_pack


def add_minimum_living_services(data_pack):
    return data_pack
