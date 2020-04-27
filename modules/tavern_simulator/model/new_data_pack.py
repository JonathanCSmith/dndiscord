class Attribute:
    def __init__(self, attribute_key, attribute_value=None):
        self.attribute_key = attribute_key
        self.attribute_value = attribute_value

    def get_key(self):
        return self.attribute_key

    def get_value(self):
        return self.attribute_value

    def __str__(self):
        return "Property:" + self.attribute_key + (" with value: " + self.attribute_value if self.attribute_value is not None else "")


class FixedStateAttribute(Attribute):
    def __init__(self, attribute_key, attribute_value):
        super().__init__(attribute_key, attribute_value)


class ModificationAttribute(Attribute):
    types = ["add", "subtract", "multiply", "divide"]

    def __init__(self, attribute_key, attribute_value, modification_type):
        super().__init__(attribute_key, attribute_value)

        if modification_type not in ModificationAttribute.types:
            raise RuntimeError("Poor modification type for ModificationAttribute: " + self.attribute_key + " and value " + str(self.attribute_value))
        self.modification_type = modification_type


class Condition(Attribute):
    types = ["equals", "doesnt_equal", "has", "doesnt_have", "greater", "greater_or_equal", "less", "less_or_equal", "between"]

    def __init__(self, condition_type, attribute_key, attribute_value):
        super().__init__(attribute_key, attribute_value)

        if condition_type not in Condition.types:
            raise RuntimeError("Poor condition construction. Type was: " + condition_type)

        self.condition_type = condition_type

    def get_type(self):
        return self.condition_type


class BusinessState:
    def __init__(self, unique_key, name=None, requirements=None, provides=None):
        self.unique_key = unique_key
        self.name = unique_key

        if not requirements:
            requirements = dict()
        elif not isinstance(requirements, dict):
            requirements = dict()
        self.requirements = requirements

        if not provides:
            provides = dict()
        elif not isinstance(provides, dict):
            provides = dict()
        self.provides = provides

    def get_key(self):
        return self.unique_key

    def get_prerequisites(self):
        return self.requirements

    def append_prerequisite(self, condition: Condition):
        self.requirements[condition.get_key()] = condition

    def get_provided(self):
        return self.provides

    def append_provided(self, attribute: Attribute):
        self.provides[attribute.get_key()] = attribute

    def get_precluded_by(self):
        return dict()


class Purchaseable(BusinessState):
    def __init__(self, unique_key, cost, duration, name=None, requirements=None, provides=None):
        super().__init__(unique_key, name=name, requirements=requirements, provides=provides)

        self.cost = cost
        self.duration = duration


class Contract(BusinessState):
    def __init__(self, unique_key, cost, duration, name=None, requirements=None, provides=None):
        super().__init__(unique_key, name=name, requirements=requirements, provides=provides)

        self.cost = cost
        self.duration = duration
