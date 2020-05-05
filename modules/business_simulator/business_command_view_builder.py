from utils.messages import LongMessage


async def build_status_view_players(business, translation_manager, ctx):
    # Create our status representation in long message form
    long_message = LongMessage()

    # Gather our business status
    long_message.add("===================================")  # Fake new line
    long_message.add("Your business: " + business.get_name() + " has the following properties: ")
    long_message.add("===================================")  # Fake new line
    for property, value in business.get_properties().items():
        key = "business." + business.data_pack.name + "." + property

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

    # Active improvements
    improvements = business.get_improvements()
    long_message.add(None)
    long_message.add("===================================")
    if len(improvements) != 0:
        long_message.add("You have improved your business in the following ways:")
    else:
        long_message.add("You have yet to improve your business")
    long_message.add("===================================")
    for improvement in improvements:
        long_message.add(str(improvement))

    # Active contracts
    contracts = business.get_contracts()
    long_message.add(None)
    long_message.add("===================================")  # Fake new line
    long_message.add("You currently have " + str(len(contracts)) + " contracts ongoing.")
    long_message.add("===================================")
    for contract in contracts:
        long_message.add(str(contract))

    # Gather our staff
    staff = business.get_employees()
    count = len(staff)
    long_message.add(None)
    long_message.add("===================================")  # Fake new line
    long_message.add("You currently have " + str(count) + " employees." + (" They are:" if count > 0 else ""))
    long_message.add("===================================")
    for staff_member in staff:
        long_message.add(str(staff_member))

    # Interested customers
    customers = business.get_interested_customers()
    long_message.add(None)
    long_message.add("===================================")
    long_message.add("The following customer types are interested in your business:")
    long_message.add("===================================")
    for customer in customers:
        long_message.add(str(customer))

    # Customer History
    customer_history = business.get_most_recent_customer_history()
    long_message.add(None)
    long_message.add("===================================")  # Fake new line
    if customer_history:
        long_message.add("Last tenday you had the following customers:")
    else:
        long_message.add("You have had no customers over the last week.")
    long_message.add("===================================")
    for customer_entry in customer_history:
        long_message.add(str(customer_entry))

    # Sales offered
    offered = business.get_services_offered()
    long_message.add(None)
    long_message.add("===================================")
    long_message.add("The following sales and services are offered by your business:")
    long_message.add("===================================")
    for offering in offered:
        long_message.add(str(offering))

    # Offering
    sales = business.get_most_recent_sales_history()
    long_message.add(None)
    long_message.add("===================================")  # Fake new line
    if sales:
        long_message.add("Last tenday you sold the following: ")
    else:
        long_message.add("You have had no sales over the last week.")
    long_message.add("===================================")
    for sale in sales:
        long_message.add(str(sale))

    return long_message


# TODO: Translations


async def build_purchaseable_view_players(business, translation_manager, ctx):
    # Get the results to post
    purchaseables = business.get_improveable()

    # Create an output message
    long_message = LongMessage()
    long_message.add("The business can apply the following improvements: ")

    # Gather our business status
    long_message.add(" ")  # Fake new line
    for purchaseable in purchaseables:
        long_message.add("===================================")

        # Translation
        if translation_manager is not None:
            purchaseable_name = await translation_manager.get_translation_for_current_localization(ctx, purchaseable.get_key())
        else:
            purchaseable_name = purchaseable.get_key()

        long_message.add("Improvement: " + purchaseable.get_key())
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
            contract_name = await translation_manager.get_translation_for_current_localization(ctx, contract.get_key())
        else:
            contract_name = contract.get_key()

        long_message.add("Contract: " + contract.get_key())
        long_message.add(" ")
        long_message.add(contract_name + " can be purchased for " + str(float(contract.cost) / 100.0) + " gold and will last for " + str(contract.duration) + " days.")
        long_message.add(" ")

    # Get the results to post
    hireables = business.get_hireable()

    # Create an output message
    long_message.add(" ")  # Fake new line
    long_message.add("The business can hire the following employees: ")

    # Gather our business status
    long_message.add(" ")  # Fake new line
    for hireable in hireables:
        long_message.add("===================================")

        # Translation
        if translation_manager is not None:
            hireable_name = await translation_manager.get_translation_for_current_localization(ctx, hireable.get_key())
        else:
            hireable_name = hireable.get_key()

        long_message.add("Employee Type: " + hireable.get_key())
        long_message.add(" ")
        long_message.add(hireable_name + " can be hired for " + str(hireable.cost_per_day) + " copper pieces a day.")
        long_message.add(" ")

    return long_message
