from utils.data import ContextDependent


class DataPack(ContextDependent):
    def __init__(self, **kwargs):
        super().__init__()

        # If we are creating the data pack programmatically
        if "current_path" in kwargs:
            self.current_path = kwargs["current_path"]

        self.file_names = list()
        self.data = dict()

        # Stuff to ignore when serializing
        self.ignored_items.append("data")

    def add_path(self, file_name):
        self.file_names.append(file_name)

    def load_data_pack(self, file_system):
        for file_name in self.file_names:
            self.data[file_name] = file_system.load_file(self.current_path, file_name)

    def save_data_pack(self, file_system):
        pass
