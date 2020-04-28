from modules.tavern_simulator.model.new_data_pack import Employee, Contract


class EmployeeEntry:
    def __init__(self, staff_name, staff_archetype):
        self.staff_name = staff_name
        self.staff_archetype = staff_archetype

    def __str__(self):
        return self.staff_name + " is a " + self.staff_archetype


class ContractEntry:
    def __init__(self, contract_type, amount_paid, start_date):
        self.contract_type = contract_type
        self.amount_paid = amount_paid
        self.start_date = start_date

    def __str__(self):
        return "Contract: " + self.contract_type + " started on " + str(self.start_date) + ". You pay: " + str(self.amount_paid) + " per day for them."


class UpgradeEntry:
    def __init__(self, upgrade_type, amount_paid):
        self.upgrade_type = upgrade_type
        self.amount_paid = amount_paid

    def __str__(self):
        return "Uprade: " + self.upgrade_type + ". You paid: " + str(self.amount_paid) + " for it."


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
    def __init__(self, name="", data_pack_name="", data_pack_path="", is_guild_specific_data_pack=False, purchase_history=None, customer_history_by_week=None, sales_history_by_week=None):
        self.data_pack_name = data_pack_name
        self.data_pack_path = data_pack_path
        self.is_guild_specific_data_pack = is_guild_specific_data_pack

        # Some general properties
        self.name = name
        if purchase_history is None:
            purchase_history = list()
        self.purchase_history = purchase_history
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

    def set_data_pack(self, data_pack):
        self.data_pack_name = data_pack.get_name()
        self.data_pack_path = data_pack.get_path()
        self.is_guild_specific_data_pack = data_pack.is_guild

    def get_purchase_history(self):
        return self.purchase_history

    def purchase(self, item, amount=None, name=None, start_date=None):
        if isinstance(item, Employee):
            purchase_history = EmployeeEntry(name, item.unique_key)
        elif isinstance(item, Contract):
            purchase_history = ContractEntry(item.unique_key, amount, start_date)
        else:
            purchase_history = UpgradeEntry(item.unique_key, amount)

        self.purchase_history.append(purchase_history)

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
        self.purchase_history.clear()
        self.customer_history_by_week.clear()
        self.sales_history_by_week.clear()
