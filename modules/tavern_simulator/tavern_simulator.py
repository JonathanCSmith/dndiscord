import sys


from module_properties.tavern_simulator.model.data_pack import DataPack, Upgrade, Service, Staff, Patron
from module_properties.tavern_simulator.model.tavern import Tavern
from module_properties.tavern_simulator.tenday import Tenday


# Runtime flags for dev
testing = True  # TODO: Change to false


# Input arguments
args = sys.argv
roll = ""
situational_modifiers = ""
tavern_status_file = "../../tavern.json"
data_pack = "./data/."
for i in range(1, len(args)):
    arg = args[i]
    if arg.startswith("-roll="):
        roll = arg.replace("-roll=", "")

    elif arg.startswith("-modifier="):
        situational_modifiers = arg.replace("-modifier=", "")

    elif arg.startswith("-tavern="):
        tavern_status_file = arg.replace("-tavern=", "")

    elif arg.startswith("-data_pack="):
        data_pack = arg.replace("-data_pack=", "")

    elif arg.startswith("-t"):
        testing = True

if testing:
    # Put the params back
    roll = ""
    situational_modifiers = ""
    tavern_status_file = "../../tavern.json"
    data_pack = "./data/."

    # Data packs
    data_pack = DataPack(data_pack)
    data_pack.clear()

    # TODO: Can we sufficiently define a service that we can hardcode paths & tag naming conventions?

    # Prebuilt services
    basic_drinks_key_vals = dict()
    basic_drinks_key_vals["store_basic_drinks"] = "YES"
    basic_drinks_key_vals["sell_basic_drinks"] = "YES"
    basic_drinks_key_vals["serve_basic_drinks"] = "YES"
    basic_drinks = Service("basic_drinks", 1, 2, prerequisites=basic_drinks_key_vals)
    data_pack.add_service(basic_drinks)

    # Prebuilt patrons
    commoner_patron = Patron("commoner", 2, {basic_drinks.name: 5})
    data_pack.add_patron(commoner_patron)
    rough_patron = Patron("rough", 1, {basic_drinks.name: 3})
    data_pack.add_patron(rough_patron)

    # Prebuild upgrades
    barrel_vault_key_vals = dict()
    barrel_vault_key_vals[basic_drinks.get_maximum_of_service_offered_tags()] = 100
    barrel_vault_key_vals["maximum_drinks"] = 50
    barrel_vault_key_vals["store_basic_drinks"] = "YES"
    barrel_vault = Upgrade("basic_barrel_vault", 500, provided=barrel_vault_key_vals)
    data_pack.add_upgrade(barrel_vault)

    basic_taproom_key_vals = dict()
    basic_taproom_key_vals[commoner_patron.get_mean_patron_occupancy_additive_tag()] = 10
    basic_taproom_key_vals[rough_patron.get_mean_patron_occupancy_additive_tag()] = 2
    basic_taproom_key_vals[Patron.maximum_occupancy_limit_tag] = 50
    basic_taproom_key_vals["sell_basic_drinks"] = "YES"
    basic_taproom_key_vals["taproom"] = "YES"
    basic_taproom = Upgrade("basic_taproom", 500, provided=basic_taproom_key_vals)
    data_pack.add_upgrade(basic_taproom)

    # Prebuilt staff
    barstaff_prerequisite_key_vals = dict()
    barstaff_prerequisite_key_vals["taproom"] = "YES"
    barstaff_key_vals = dict()
    barstaff_key_vals["maximum_patrons_served"] = 100
    barstaff_key_vals[commoner_patron.get_mean_patron_occupancy_multiplier_tag()] = 1.1
    barstaff_key_vals[rough_patron.get_mean_patron_occupancy_multiplier_tag()] = 1.2
    barstaff_key_vals["modify_maintenance"] = 1.1
    barstaff_key_vals["modify_tip_rate"] = 1.1
    barstaff_key_vals["serve_basic_drinks"] = "YES"
    barstaff = Staff("barstaff", 1, prerequisites=barstaff_prerequisite_key_vals, provided=barstaff_key_vals)
    data_pack.add_staff_archetype(barstaff)

    # Save & Load test
    data_pack.save()
    data_pack.load()

    # Create a tavern
    tavern = Tavern(tavern_status_file, data_pack)
    tavern.clear()
    tavern.add_upgrade(basic_taproom)
    tavern.add_upgrade(barrel_vault)
    tavern.hire_staff(barstaff)

    # Save & Load test
    tavern.save()
    tavern.load()

    # Create a tenday!
    tenday = Tenday(roll, situational_modifiers)

    # Simulate
    tavern.simulate(tenday)

    print("This tenday your net outcome was: " + str(tavern.sales))

else:
    # TODO: GUI
    pass
