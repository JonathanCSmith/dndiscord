class StaffEntry:
    def __init__(self, staff_name, staff_archetype, weekly_hire_cost):
        self.staff_name = staff_name
        self.staff_archetype = staff_archetype
        self.weekly_hire_cost = weekly_hire_cost

    def __str__(self):
        return self.staff_name + " is a " + self.staff_archetype + " and is paid " + str(self.weekly_hire_cost)


class ContractEntry:
    def __init__(self, contract_type, amount_paid, remaining_duration):
        self.contract_type = contract_type
        self.amount_paid = amount_paid
        self.remaining_duration = remaining_duration

    def __str__(self):
        return "Contract: " + self.contract_type + " has " + str(self.remaining_duration) + " weeks remaining. You paid: " + str(self.amount_paid) + " for it."


class CustomerHistory:
    def __init__(self, relative_week_index, customers=None):
        self.relative_week_index = relative_week_index
        if customers is None:
            customers = dict()
        self.customers = customers

    def add_customers(self, customer_type, amount):
        self.customers[customer_type] = amount

    def __str__(self):
        out = "Customers for Week: " + self.relative_week_index + "\n"
        for customer, amount in self.customers.items():
            out += customer + ": " + str(amount) + "\n"


class SalesHistory:
    def __init__(self, relative_week_index, sales=None):
        self.relative_week_index = relative_week_index
        if sales is None:
            sales = dict()
        self.sales = sales

    def add_sales(self, sale_type, amount):
        self.sales[sale_type] = amount

    def __str__(self):
        out = "Sales for Week: " + self.relative_week_index + "\n"
        for sale, amount in self.sales.items():
            out += sale + ": " + str(amount) + "\n"


class TavernStatus:
    def __init__(self, data_pack_name, data_pack_path, is_guild_specific_data_pack, name="", tavern_purchases=None, staff=None, active_contracts=None, customer_history_by_week=None, sales_history_by_week=None):
        self.data_pack_name = data_pack_name
        self.data_pack_path = data_pack_path
        self.is_guild_specific_data_pack = is_guild_specific_data_pack

        # Some general properties
        self.name = name
        if tavern_purchases is None:
            tavern_purchases = list()
        self.tavern_purchases = tavern_purchases
        if staff is None:
            staff = dict()
        self.staff = staff
        if active_contracts is None:
            active_contracts = list()
        self.active_contracts = active_contracts
        if customer_history_by_week is None:
            customer_history_by_week = list()
        self.customer_history_by_week = customer_history_by_week
        if sales_history_by_week is None:
            sales_history_by_week = list()
        self.sales_history_by_week = sales_history_by_week

    def get_name(self):
        return self.name

    def set_name(self, name):
        self.name = name

    def get_purchases(self):
        return self.tavern_purchases

    def add_purchase(self, upgrade):
        self.tavern_purchases.append(upgrade.name)

    def set_purchases(self, upgrades):
        self.tavern_purchases = upgrades

    def get_staff(self):
        return self.staff

    def add_staff(self, staff, amount=1):
        if staff.name in self.staff:
            self.staff[staff.name] += amount
        else:
            self.staff[staff.name] = amount

    def get_active_contracts(self):
        return self.active_contracts

    def get_customer_history_for_week(self, week_index):
        try:
            out = self.customer_history_by_week[week_index]
        except IndexError:
            out = None

        return out

    def get_sales_history_for_week(self, week_index):
        try:
            out = self.sales_history_by_week[week_index]
        except IndexError:
            out = None

        return out

    def clear(self):
        self.tavern_purchases.clear()
        self.staff.clear()
