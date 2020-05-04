from utils.messages import LongMessage


async def build_status_view_players(business, translation_manager, ctx):
    # Create our status representation in long message form
    long_message = LongMessage()

    # Gather our business status
    long_message.add("===================================")  # Fake new line
    long_message.add("Your business: " + business.get_name() + " has the following properties: ")
    long_message.add("===================================")  # Fake new line
    for property, value in business.get_properties().items():
        key = "tavern." + business.data_pack.name + "." + property

        if value is not None or value is not "":
            detail_key = key + "." + str(value)

            # Translation
            if translation_manager is not None:
                translation = await translation_manager.get_translation_for_current_localization(ctx, detail_key)
            else:
                translation = detail_key

            if translation != detail_key:
                long_message.add(translation)
                continue

        # Translation
        if translation_manager is not None:
            translation = await translation_manager.get_translation_for_current_localization(ctx, key)
        else:
            translation = key

        long_message.add(str(translation) + (" " + str(value) if value is not None else ""))

    # Gather our staff
    staff = business.get_employees()
    count = len(staff)
    long_message.add(None)
    long_message.add("===================================")  # Fake new line
    long_message.add("You currently have " + str(count) + " employees." + (" They are:" if count > 0 else ""))
    for staff_member in staff:
        long_message.add(str(staff_member))

    # Active contracts
    contracts = business.get_contracts()
    long_message.add(None)
    long_message.add("===================================")  # Fake new line
    long_message.add("You currently have " + str(len(contracts)) + " contracts ongoing.")
    for contract in contracts:
        long_message.add(str(contract))

    # Customers
    customers = business.get_most_recent_customer_history()
    long_message.add(None)
    long_message.add("===================================")  # Fake new line
    if customers:
        long_message.add("Last tenday you had the following customers:")
        for customer_entry in customers:
            long_message.add(str(customer_entry))
    else:
        long_message.add("You have had no customers over the last week.")

    # Offering
    services = business.get_most_recent_sales_history()
    long_message.add(None)
    long_message.add("===================================")  # Fake new line
    if services:
        long_message.add("Last tenday you served the following: ")
        for service in services:
            long_message.add(str(service))
    else:
        long_message.add("You have had no sales over the last week.")

    return long_message


# TODO: Translations


async def build_purchaseable_view_players(business, translation_manager, ctx):
    # Get the results to post
    purchaseable = business.get_upgradeable()

    # Create an output message
    long_message = LongMessage()
    long_message.add("The business can apply the following upgrades: ")

    # Gather our business status
    long_message.add(" ")  # Fake new line
    for purchaseable in purchaseable:
        long_message.add("===================================")

        # Translation
        if translation_manager is not None:
            purchaseable_name = await translation_manager.get_translation_for_current_localization(ctx, purchaseable.get_key())
        else:
            purchaseable_name = purchaseable.get_key()

        long_message.add("Upgrade: " + purchaseable.get_key())
        long_message.add(" ")
        long_message.add(purchaseable_name + " can be purchased for " + str(float(purchaseable.cost) / 100.0) + " gold and will take " + str(purchaseable.duration) + " days to construct")
        long_message.add(" ")

    # Get the results to post
    contractables = business.get_contractable()

    long_message.add(" ")  # Fake new line
    long_message.add("The business can apply the following contracts: ")

    # Gather our business status
    long_message.add(" ")  # Fake new line
    for contract in contractables:
        long_message.add("===================================")

        # Translation
        if translation_manager is not None:
            purchaseable_name = await translation_manager.get_translation_for_current_localization(ctx, contract.get_key())
        else:
            purchaseable_name = purchaseable.get_key()

        long_message.add("Contract: " + contract.get_key())
        long_message.add(" ")
        long_message.add(purchaseable_name + " can be purchased for " + str(float(contract.cost) / 100.0) + " gold and will last for " + str(contract.duration) + " days.")
        long_message.add(" ")

        # Get the results to post
        hireables = business.get_hireable()

        # Create an output message
        long_message.add(" ")  # Fake new line
        long_message.add("The business can apply the following upgrades: ")

        # Gather our business status
        long_message.add(" ")  # Fake new line
        for hireable in hireables:
            long_message.add("===================================")

            # Translation
            if translation_manager is not None:
                purchaseable_name = await translation_manager.get_translation_for_current_localization(ctx, hireable.get_key())
            else:
                purchaseable_name = purchaseable.get_key()

            long_message.add("Employee Type: " + hireable.get_key())
            long_message.add(" ")
            long_message.add(purchaseable_name + " can be hired for " + str(hireable.cost_per_day) + " copper pieces a day.")
            long_message.add(" ")

    return long_message
