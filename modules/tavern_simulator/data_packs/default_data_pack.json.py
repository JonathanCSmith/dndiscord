from modules.tavern_simulator.model.data_pack import DataPack, Purchase


"""
Data pack design notes:
    Basic environment will not incl glazing.
    
    Basic tap room requires:
        functional roof
        basic living environment
        water
        sewers
        
"""


def create_default_data_pack(force):
    data_pack = DataPack("./default_data_pack/.")

    # We have already serialized out this before (or someone has provided their own) so just return
    if not force and len(data_pack.get_patrons()) != 0:
        return data_pack

    # Default data
    data_pack = add_rebuilds_from_disrepair(data_pack)
    data_pack = add_minimum_living_services(data_pack)


def add_rebuilds_from_disrepair(data_pack):
    # Fix the roof
    roof_key_vals = dict()
    roof_key_vals["functional_roof"] = "YES"
    roof = Purchase("main_roof", 300, provided=roof_key_vals)
    data_pack.add_purchaseable(roof)

    # General repair
    repair_key_vals = dict()
    repair_key_vals["basic_living_environment"] = "YES"
    repair = Purchase("basic_repair", 150, provided=repair_key_vals)
    data_pack.add_purchaseable(repair)

    # Service repair
    service_key_vals = dict()
    service_key_vals["has_water"] = "YES"
    service_key_vals["has_sewers"] = "YES"
    services = Purchase("fixed_services", 50, provided=service_key_vals)
    data_pack.add_purchaseable(services)

    return data_pack


def add_minimum_living_services(data_pack):
    return data_pack
