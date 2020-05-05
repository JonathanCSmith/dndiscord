import uuid

from modules.business_simulator.model.data_pack import Employee, Contract, Improvement


class Entry:
    def __init__(self, key, active=True, removed=False):
        self.key = str(uuid.uuid4())
        self.active = active
        self.removed = removed

    async def apply(self, business):
        pass


class ImprovementPurchaseEntry(Entry):
    def __init__(self, improvement: Improvement, purchase_date, negotiated_amount=None):
        super().__init__(self)

        self.improvement_type = improvement.get_key()
        self.purchase_date = purchase_date

        if negotiated_amount is None:
            negotiated_amount = improvement.cost
        self.purchase_amount = negotiated_amount

    async def apply(self, business):
        await business._record_active_state_modifiers(self.key, self.improvement_type)

    def __str__(self):
        return "<" + str(self.key) + "> Improvement " + self.improvement_type + " purchased on game day: " + str(self.purchase_date) + " for: " + str(self.purchase_amount)


class ContractPurchaseEntry(Entry):
    def __init__(self, contract: Contract, purchase_date, negotiated_amount=None):
        super().__init__(self)

        self.contract_type = contract.get_key()
        self.purchase_date = purchase_date

        if negotiated_amount is None:
            negotiated_amount = contract.cost
        self.purchase_amount = negotiated_amount

    async def apply(self, business):
        await business._record_active_state_modifiers(self.key, self.contract_type)

    def __str__(self):
        return "<" + str(self.key) + "> Contract " + self.contract_type + " purchased on game day: " + str(self.purchase_date) + " for: " + str(self.purchase_amount)


class EmployeeHireEntry(Entry):
    def __init__(self, employee_type: Employee, name, hire_date):
        super().__init__(self)

        self.employee_type = employee_type.get_key()
        self.name = name
        self.hire_date = hire_date

    async def apply(self, business):
        await business._record_active_state_modifiers(self.key, self.employee_type)

    def __str__(self):
        return "<" + str(self.key) + "> Employee " + self.employee_type + " " + self.name + " was hired on: " + str(self.hire_date)


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


class BusinessStatus:
    def __init__(self, name, data_pack_name="", data_pack_path="", is_guild_specific_data_pack=False, purchase_history=None, customer_history_by_week=None, sales_history_by_week=None):
        self.data_pack_name = data_pack_name
        self.data_pack_path = data_pack_path
        self.is_guild_specific_data_pack = is_guild_specific_data_pack

        # Some general properties
        self.name = name
        if purchase_history is None:
            purchase_history = dict()
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

    def get_data_pack_name(self):
        return self.data_pack_name

    def set_data_pack(self, data_pack):
        self.data_pack_name = data_pack.get_name()
        self.data_pack_path = data_pack.get_path()
        self.is_guild_specific_data_pack = data_pack.is_guild

    def get_history(self):
        return self.purchase_history

    def get_historical_purchase(self, key):
        return self.purchase_history[key]

    async def purchase_improvement(self, business_controller, improvement: Improvement, game_days, negotiated_amount=None):
        improvement_entry = ImprovementPurchaseEntry(improvement, game_days, negotiated_amount)
        self.purchase_history[improvement_entry.key] = improvement_entry
        await improvement_entry.apply(business_controller)

    async def purchase_contract(self, business_controller, contract: Contract, game_days, negotiated_amount=None):
        contract_entry = ContractPurchaseEntry(contract, game_days, negotiated_amount)
        self.purchase_history[contract_entry.key] = contract_entry
        await contract_entry.apply(business_controller)

    async def hire_employee(self, business_controller, employee_type: Employee, name, game_days):
        employee_entry = EmployeeHireEntry(employee_type, name, game_days)
        self.purchase_history[employee_entry.key] = employee_entry
        await employee_entry.apply(business_controller)

    def disable(self, item):
        pass

    def remove(self, item):
        pass

    def get_customer_history_for_week(self, week_index):
        try:
            out = self.customer_history_by_week[week_index]
        except IndexError:
            out = list()

        return out

    def get_sales_history_for_week(self, week_index):
        try:
            out = self.sales_history_by_week[week_index]
        except IndexError:
            out = list()

        return out

    def clear(self):
        self.purchase_history.clear()
        self.customer_history_by_week.clear()
        self.sales_history_by_week.clear()
