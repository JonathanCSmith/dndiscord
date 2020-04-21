import sys

from modules.tavern_simulator.data_packs import default_data_pack
from modules.tavern_simulator.model.data_pack import DataPack, Purchase, Service, Staff, Patron
from modules.tavern_simulator.model.tavern import Tavern
from modules.tavern_simulator.tenday import Tenday


"""
TODO: Integrate with bot

Current user story:

    1) We have a building, it's derelict but we want to turn it into a tavern, how?
    2) List upgrades should show:
        a) Repair options
        b) Available contracts for house
    3) List upgrades with missing requirements
    4) Taproom should require:
        a) Purchase
        b) Contracts:
        
            
    3) Evaluate what 'contracts' are required for 
"""


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
    data_pack = default_data_pack.create_default_data_pack(data_pack, force=True)

    # Test save and load
    data_pack.save()
    data_pack.load()

    # Create a tavern
    tavern = Tavern(None, tavern_status_file, data_pack)
    tavern.clear()

    # Manipulate the tavern
    # tavern.add_upgrade(basic_taproom)
    # tavern.add_upgrade(barrel_vault)
    # tavern.hire_staff(barstaff)

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
