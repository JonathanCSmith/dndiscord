"""
TODO: Tag Library? Would allow for inheritance but it seems ridiculously overcomplicated
TODO: We could turn the 'values' of prerequisites into an alias repository instead
"""


class Data:
    def __int__(self, unique_key, prerequisites=None, provides=None, precluded_by=None, description="", hidden=False):
        self.unique_key = unique_key

        if prerequisites is None:
            prerequisites = dict()
        elif not isinstance(prerequisites, dict):
            print("Prerequisites: " + str(prerequisites) + " are not valid for: " + unique_key)
            prerequisites = dict()
        self.prerequisites = prerequisites

        if provides is None:
            provides = dict()
        elif not isinstance(provides, dict):
            print("Provided: " + str(provides) + " are not valid for: " + unique_key)
            provides = dict()
        self.provides = provides

        if precluded_by is None:
            precluded_by = dict()
        elif not isinstance(precluded_by, dict):
            print("Provided: " + str(precluded_by) + " are not valid for: " + unique_key)
            precluded_by = dict()
        self.precluded_by = precluded_by

        self.description = description

    def append_prerequisite(self, key, value):
        self.prerequisites[key] = value

    def get_prerequisites(self):
        return self.prerequisites

    def append_provided(self, key, value):
        self.provides[key] = value

    def get_provided(self):
        return self.provides

    def append_precluded_by(self, key, value):
        self.precluded_by[key] = value

    def get_precluded_by(self):
        return self.precluded_by

    def get_provided_value(self, keys):
        values = list()
        if isinstance(keys, list):
            for key in keys:
                if key in self.provides:
                    values.append(self.provides[key])

        elif keys in self.provides:
            values.append(self.provides[keys])

        return values


class Service(Data):
    maximum_services_tag = "maximum_services"

    def __init__(self, name, cost, sale, prerequisites=None, provides=None, precluded_by=None, description="", hidden=False, service_maximum_tags=None, served=None):
        super().__int__(name, prerequisites=prerequisites, provides=provides, precluded_by=precluded_by, description=description, hidden=hidden)

        self.cost = cost
        self.sale = sale
        self.service_maximum_tags = self.unique_key + "_" + Service.maximum_services_tag

    def get_maximum_of_service_offered_tags(self):
        return self.service_maximum_tags


class Staff(Data):
    """
    TODO: Names, Service type transitions (i.e. upsell)? Staff common rooms? Staff limit the volume of sales
    """

    def __init__(self, name, cost, prerequisites=None, provides=None, precluded_by=None, description="", hidden=False):
        super().__int__(name, prerequisites=prerequisites, provides=provides, precluded_by=precluded_by, description=description, hidden=hidden)

        self.cost = cost


class Purchase(Data):
    def __init__(self, name, cost, prerequisites=None, provides=None, precluded_by=None, description="", hidden=False):
        super().__int__(name, provides=provides, prerequisites=prerequisites, precluded_by=precluded_by, description=description, hidden=hidden)

        self.cost = cost


class Contract(Purchase):
    def __init__(self, name, cost, duration, prerequisites=None, provides=None, precluded_by=None, description="", hidden=False):
        super().__init__(name, cost, provides=provides, prerequisites=prerequisites, precluded_by=precluded_by, description=description, hidden=hidden)

        self.duration = duration


class Patron(Data):
    mean_occupancy_additive_tag = "average_attendance_addition"
    mean_occupancy_multiplier_tag = "average_attendance_multiplier"
    maximum_occupancy_limit_tag = "maximum_occupancy"

    def __init__(self, name, priority, consumed, prerequisites=None, provides=None, precluded_by=None, description="", hidden=False, mean_patron_occupancy_additive_tag=None, mean_patron_occupancy_multiplier_tag=None, maximum_patron_occupancy_limit_tag=None):
        super().__int__(name, prerequisites=prerequisites, provides=provides, precluded_by=precluded_by, description=description, hidden=hidden)
        self.name = name
        self.priority = priority

        if not isinstance(consumed, dict):
            self.consumed = dict()
            self.consumed[consumed] = 1
        else:
            self.consumed = consumed

        if mean_patron_occupancy_additive_tag is None:
            mean_patron_occupancy_additive_tag = self.name + "_" + Patron.mean_occupancy_additive_tag
        self.mean_patron_occupancy_additive_tag = mean_patron_occupancy_additive_tag

        if mean_patron_occupancy_multiplier_tag is None:
            mean_patron_occupancy_multiplier_tag = self.name + "_" + Patron.mean_occupancy_multiplier_tag
        self.mean_patron_occupancy_multiplier_tag = mean_patron_occupancy_multiplier_tag

        if maximum_patron_occupancy_limit_tag is None:
            maximum_patron_occupancy_limit_tag = self.name + "_" + Patron.maximum_occupancy_limit_tag
        self.maximum_patron_occupancy_limit_tag = maximum_patron_occupancy_limit_tag

    def get_mean_patron_occupancy_additive_tag(self):
        return self.mean_patron_occupancy_additive_tag

    def get_mean_patron_occupancy_multiplier_tag(self):
        return self.mean_patron_occupancy_multiplier_tag

    def get_maximum_patron_occupancy_limit_tags(self):
        return self.maximum_patron_occupancy_limit_tag

    def get_services_consumed(self):
        return self.consumed


