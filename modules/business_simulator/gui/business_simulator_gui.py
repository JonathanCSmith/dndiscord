import asyncio
import os
from tkinter import Tk, Menu, Frame, LEFT, Button, PanedWindow, NSEW, EW, RIGHT, ttk, Label
from tkinter.filedialog import asksaveasfilename, askopenfilename, askdirectory
from tkinter.messagebox import showinfo, askquestion
from tkinter.scrolledtext import ScrolledText
from tkinter.simpledialog import askstring

from modules.business_simulator.business_command_view_builder import build_status_view_players, build_purchaseable_view_players
from modules.business_simulator.business_controller import BusinessController
from modules.business_simulator.gui.gui_view_builder import build_data_pack_overview, build_data_pack_items_view, build_status_view, build_purchaseable_view
from modules.business_simulator.gui.widgets import ScrollFrame
from modules.business_simulator.model.business_model import BusinessStatus
from modules.business_simulator.model.data_pack import BusinessDataPack
from utils import data
from utils.translations import TranslationManager


class Session:
    def __init__(self, active_business="", businesses=None):
        self.active_business = active_business
        if businesses is None:
            businesses = dict()
        self.businesses = businesses

    def get_active_business(self):
        return self.active_business

    def set_active_business(self, active_business):
        self.active_business = active_business

    def get_businesses(self):
        return self.businesses

    def get_business(self, name):
        if name in self.businesses:
            return self.businesses[name]
        return None

    def add_business(self, name, path):
        self.businesses[name] = path

    @classmethod
    def load(cls, file):
        return data.load(file)

    def save(self, file):
        data.save(self, file)


class FakeGuild:
    def __init__(self):
        self.id = ""


class FakeContext:
    def __init__(self):
        self.guild = FakeGuild()
        self.path = ""


class BusinessSimulatorGUI(Tk):
    def __init__(self):
        super().__init__()

        # Create our asyncio loop so we can complete async tasks
        self.loop = asyncio.new_event_loop()

        # Add in a translation manager that will have a go at translating any strings in the data packs
        self.translation_manager = TranslationManager()
        self.fake_context = FakeContext()

        # Initial session
        self.active_businesses = dict()
        self.session = Session()

        # Basic window props
        self.title("Business Simulator")

        # Set to max size for the current monitor
        self.__setup_initial_geometry()

        # Create some basic session props
        self.__create_menu()
        self.__setup_core_frames()
        self.__create_businesses_view()
        self.__create_data_pack_view()
        self.__create_simulation_views()

    def __setup_initial_geometry(self):
        width = self.winfo_screenwidth()
        height = self.winfo_screenheight()
        self.geometry("%dx%d+0+0" % (width, height))

    def __create_menu(self):
        self.menu = Menu(self)
        self.session_menu = Menu(self.menu, tearoff=0)
        self.session_menu.add_command(label="Save Session", command=self.save_session)
        self.session_menu.add_command(label="Load Session", command=self.load_session)
        self.session_menu.add_command(label="Clear Session", command=self.clear_session)
        self.menu.add_cascade(label="Session", menu=self.session_menu)
        self.config(menu=self.menu)

    def __setup_core_frames(self):
        # Active businesses
        self.businesses_view = Frame(self, width=100)
        self.businesses_view.pack(side=LEFT, expand=0, fill="y")

        # Core window
        self.window = PanedWindow(self, orient="horizontal")
        self.window.pack(side=LEFT, expand=1, fill="both")

        # Business specific data pack
        self.data_pack_view = Frame(self.window, background="red")
        self.data_pack_view.pack(expand=1, fill="both")
        self.window.add(self.data_pack_view)

        # Business gui view
        self.simulation_view = Frame(self.window, background="yellow")
        self.simulation_view.pack(expand=1, fill="both")
        self.window.add(self.simulation_view)

    def __create_businesses_view(self):
        self.business_scroll_frame = ScrollFrame(self.businesses_view)

        add_remove_business_frame = Frame(self.business_scroll_frame.view_port, background="blue")
        add_remove_business_frame.grid(column=0, row=0, sticky=EW)

        add_button = Button(add_remove_business_frame, text="New", command=self.new_business)
        add_button.grid(column=0, row=0, sticky=EW)

        add_remove_business_frame.grid_columnconfigure(0, weight=1)

        item_count = 1
        for business in self.active_businesses.values():
            button = Button(self.business_scroll_frame.view_port, text=business.get_name(), command=lambda: self.choose_business(business.get_name()))
            button.grid(column=0, row=item_count, sticky=EW)
            item_count += 1

        self.business_scroll_frame.view_port.grid_columnconfigure(0, weight=1)
        self.business_scroll_frame.view_port.pack(expand=1, fill="both")
        self.business_scroll_frame.pack(expand=1, fill="both")

    def __refresh_business_view(self):
        if self.business_scroll_frame is not None:
            self.business_scroll_frame.pack_forget()
            self.business_scroll_frame.destroy()

        self.__create_businesses_view()

    def __create_data_pack_view(self):
        # View frame
        self.data_pack_tabs = ttk.Notebook(self.data_pack_view)

        self.data_pack_overview = Frame(self.data_pack_tabs)
        self.data_pack_tabs.add(self.data_pack_overview, text="Overview")
        self.overview_content = None

        self.data_pack_initial = Frame(self.data_pack_tabs)
        self.data_pack_tabs.add(self.data_pack_initial, text="Initial")
        self.data_pack_initial_content = None

        self.data_pack_services = Frame(self.data_pack_tabs)
        self.data_pack_tabs.add(self.data_pack_services, text="Services")
        self.data_pack_services_content = None

        self.data_pack_customers = Frame(self.data_pack_tabs)
        self.data_pack_tabs.add(self.data_pack_customers, text="Customers")
        self.data_pack_customers_content = None

        self.data_pack_improvements = Frame(self.data_pack_tabs)
        self.data_pack_tabs.add(self.data_pack_improvements, text="Improvements")
        self.data_pack_improvements_content = None

        self.data_pack_contracts = Frame(self.data_pack_tabs)
        self.data_pack_tabs.add(self.data_pack_contracts, text="Contracts")
        self.data_pack_contracts_content = None

        self.data_pack_employees = Frame(self.data_pack_tabs)
        self.data_pack_tabs.add(self.data_pack_employees, text="Employees")
        self.data_pack_employees_content = None

        # Controls frame
        self.data_pack_controls = Frame(self.data_pack_view)
        test_label = Label(self.data_pack_controls, text="Name:")
        test_label.grid(column=0, row=0)

        # Packing
        self.data_pack_tabs.pack(expand=1, fill="both")
        self.data_pack_controls.pack(expand=0, fill="x")

    def __delete_data_pack_view(self):
        if self.overview_content is not None:
            self.overview_content.pack_forget()
            self.overview_content.destroy()

        if self.data_pack_initial_content is not None:
            self.data_pack_initial_content.pack_forget()
            self.data_pack_initial_content.destroy()

        if self.data_pack_services_content is not None:
            self.data_pack_services_content.pack_forget()
            self.data_pack_services_content.destroy()

        if self.data_pack_customers_content is not None:
            self.data_pack_customers_content.pack_forget()
            self.data_pack_customers_content.destroy()

        if self.data_pack_improvements_content is not None:
            self.data_pack_improvements_content.pack_forget()
            self.data_pack_improvements_content.destroy()

        if self.data_pack_contracts_content is not None:
            self.data_pack_contracts_content.pack_forget()
            self.data_pack_contracts_content.destroy()

        if self.data_pack_employees_content is not None:
            self.data_pack_employees_content.pack_forget()
            self.data_pack_employees_content.destroy()

    def __refresh_data_pack_view(self):
        self.__delete_data_pack_view()
        if self.session.active_business != "":
            self.__fill_data_pack_view()

    def __fill_data_pack_view(self):
        # Display raw string
        self.data_pack_raw_display = False
        if self.data_pack_raw_display:
            pass

        # Display as gui objects
        else:
            current_business = self.active_businesses[self.session.get_active_business()]
            current_data_pack = current_business.get_data_pack()

            # Add the overview information
            self.overview_content = Frame(self.data_pack_overview)
            build_data_pack_overview(self.overview_content, current_data_pack)
            self.overview_content.pack(expand=1, fill="both")

            # Add the initial items
            self.data_pack_initial_content = ScrollFrame(self.data_pack_initial)
            build_data_pack_items_view(self.data_pack_initial_content.view_port, current_data_pack.get_initial_states())
            self.data_pack_initial_content.pack(expand=1, fill="both")

            # Add the services
            self.data_pack_services_content = ScrollFrame(self.data_pack_services)
            build_data_pack_items_view(self.data_pack_services_content.view_port, current_data_pack.get_services())
            self.data_pack_services_content.pack(expand=1, fill="both")

            # Add the services
            self.data_pack_customers_content = ScrollFrame(self.data_pack_customers)
            build_data_pack_items_view(self.data_pack_customers_content.view_port, current_data_pack.get_customers())
            self.data_pack_customers_content.pack(expand=1, fill="both")

            # Add the improvements
            self.data_pack_improvements_content = ScrollFrame(self.data_pack_improvements)
            build_data_pack_items_view(self.data_pack_improvements_content.view_port, current_data_pack.get_improvements())
            self.data_pack_improvements_content.pack(expand=1, fill="both")

            # Add the contracts
            self.data_pack_contracts_content = ScrollFrame(self.data_pack_contracts)
            build_data_pack_items_view(self.data_pack_contracts_content.view_port, current_data_pack.get_contracts())
            self.data_pack_contracts_content.pack(expand=1, fill="both")

            # Add the employees
            self.data_pack_employees_content = ScrollFrame(self.data_pack_employees)
            build_data_pack_items_view(self.data_pack_employees_content.view_port, current_data_pack.get_employee_archetypes())
            self.data_pack_employees_content.pack(expand=1, fill="both")

    """         
    TODO:   
    Potential Sales & Customers
    Unavailable Purchases
    Removed Purchases
    Inactive Purchases
    """

    def __create_simulation_views(self):
        # View frame
        self.simulation_tabs = ttk.Notebook(self.simulation_view)

        # Summary of current status
        self.simulation_overview = Frame(self.simulation_tabs)
        self.simulation_tabs.add(self.simulation_overview, text="Overview")

        # Summary of available purchases
        self.simulation_available = Frame(self.simulation_tabs)
        self.simulation_tabs.add(self.simulation_available, text="Available")

        # Controls frame
        self.simulation_controls = Frame(self.simulation_view)
        overview_frame = Frame(self.simulation_controls)
        test_label = Label(overview_frame, text="Simulation Controls:")
        test_label.grid(column=0, row=0)
        overview_frame.pack(expand=0, fill="x")

        # Packing
        self.simulation_tabs.pack(expand=1, fill="both")
        self.simulation_controls.pack(expand=0, fill="x")

    def __delete_simulation_views(self):
        if hasattr(self, "simulation_overview_panes") and self.simulation_overview_panes is not None:
            self.simulation_overview_panes.pack_forget()
            self.simulation_overview_panes.destroy()

        if hasattr(self, "simulation_available_panes") and self.simulation_available_panes is not None:
            self.simulation_available_panes.pack_forget()
            self.simulation_available_panes.destroy()

    def __refresh_simulation_views(self):
        self.__delete_simulation_views()
        if self.session.active_business != "":
            self.__fill_simulation_views()

    def __fill_simulation_views(self):
        current_business = self.active_businesses[self.session.get_active_business()]

        # Create the split pane for status overview
        self.simulation_overview_panes = PanedWindow(self.simulation_overview, orient="horizontal")
        self.simulation_overview_panes.pack(side=LEFT, expand=1, fill="both")

        # Build the summary obj view
        simulation_summary_obj_view = ScrollFrame(self.simulation_overview_panes)
        build_status_view(simulation_summary_obj_view.view_port, current_business)
        simulation_summary_obj_view.pack(expand=1, fill="both")
        self.simulation_overview_panes.add(simulation_summary_obj_view)

        # Build the summary text view
        long_message = self.loop.run_until_complete(build_status_view_players(current_business, None, None))
        string_form = ""
        for message in long_message:
            string_form += message + "\n"

        # Strip out the formatting marks
        string_form = string_form.replace("`", "")

        # Add this to our view
        simulation_summary_txt_view = ScrolledText(self.simulation_overview_panes)
        simulation_summary_txt_view.insert(1.0, string_form)
        simulation_summary_txt_view.pack(expand=1, fill="both")
        self.simulation_overview_panes.add(simulation_summary_txt_view)

        # Create the split pane for potential purchases
        self.simulation_available_panes = PanedWindow(self.simulation_available, orient="horizontal")
        self.simulation_available_panes.pack(side=LEFT, expand=1, fill="both")

        # Build the avaiable obj view
        simulation_available_obj_view = ScrollFrame(self.simulation_available_panes)
        build_purchaseable_view(self, simulation_available_obj_view.view_port, current_business)
        simulation_available_obj_view.pack(expand=1, fill="both")
        self.simulation_available_panes.add(simulation_available_obj_view)

        # Create our status representation in long message form
        long_message = self.loop.run_until_complete(build_purchaseable_view_players(current_business, None, None))
        string_form = ""
        for message in long_message:
            string_form += message + "\n"

        # Strip out the formatting marks
        string_form = string_form.replace("`", "")

        # Add this to our view
        simulation_available_txt_view = ScrolledText(self.simulation_available_panes)
        simulation_available_txt_view.insert(1.0, string_form)
        simulation_available_txt_view.pack(expand=1, fill="both")
        self.simulation_available_panes.add(simulation_available_txt_view)

    def refresh_gui(self):
        self.__refresh_business_view()
        self.__refresh_data_pack_view()
        self.__refresh_simulation_views()

    def save_session(self):
        file = asksaveasfilename(title="Please enter the save file for this session.", filetypes=[("json", "*.json")], defaultextension=".json")
        if file is None:
            return

        self.session.save(file)

        # Save our businesses and our data packs
        for business in self.active_businesses.values():
            data_pack = business.get_data_pack()
            self.loop.run_until_complete(data_pack.save(self, self.fake_context))
            self.loop.run_until_complete(self.active_businesses[business.get_name()].save(self, self.fake_context))

        self.refresh_gui()

    def load_session(self):
        file = askopenfilename(title="Please locate the session file you wish to load.", filetypes=[("json", "*.json")])
        if file is None or file == "":
            return

        self.session = Session.load(file)

        # Load the actual businesses
        for business_name, path in self.session.get_businesses().items():
            #business = self.loop.run_until_complete(BusinessController.load_business(self, self, self.fake_context, business_name))
            business = self.loop.run_until_complete(BusinessController.load_business(self, self, self.fake_context, business_name))
            self.active_businesses[business_name] = business

        self.refresh_gui()

    def clear_session(self):
        self.session = Session()
        self.refresh_gui()

    def new_business(self):
        # Are we creating a new data pack?
        reply = askquestion("New Data Pack?", "Do you already have a data pack you wish to use for this business?", icon="info")
        if reply == "yes":
            directory = askdirectory(title="Please select the data pack directory")
            if directory is None:
                return
            # Load our data
            data_pack = self.loop.run_until_complete(BusinessDataPack.load(self, self.fake_context, directory))

        else:
            name = askstring("Data pack name", "What is the name of your data pack?")
            if reply is None or reply == "":
                return

            directory = askdirectory(title="Data pack save location")
            if directory is None:
                return

            # Ensure this folder exists
            os.makedirs(os.path.join(directory, name))
            data_pack = BusinessDataPack(name, directory, False, business_name="", description="")
            self.loop.run_until_complete(data_pack.save(manager=self, ctx=self.fake_context))

        # Get a name
        file = asksaveasfilename(title="Please enter the name and location for your business.", filetypes=[("json", "*.json")], defaultextension=".json")
        if file is None:
            return

        # Create the business
        business_name = os.path.basename(file).replace(".json", "")
        self.session.add_business(business_name, file)
        business = self.loop.run_until_complete(BusinessController.create_business(self, self.fake_context, data_pack, business_name))
        self.active_businesses[business_name] = business
        self.choose_business(business_name)

    def choose_business(self, name):
        self.session.set_active_business(name)
        self.refresh_gui()

    # FAKE BOT STUFF
    async def load_game_data(self, ctx, folder_path, file_name):
        return await self.load_data(folder_path, file_name)

    async def load_data_from_data_path_for_guild(self, ctx, folder_path, file_name):
        return await self.load_data(folder_path, file_name)

    async def load_data_from_data_path(self, folder_path, file_name):
        return await self.load_data(folder_path, file_name)

    async def load_data(self, folder_path, file_name):
        if not file_name.endswith(".json"):
            nom = file_name
            file_name += ".json"
        else:
            nom = file_name.replace(".json", "")

        if nom in self.session.get_businesses():
            file = self.session.get_business(nom)
        else:
            file = os.path.join(folder_path, file_name)

        if not os.path.isfile(file):
            return None
        else:
            return data.load(file)

    async def load_translations_package(self, ctx, translation_source):
        return await self.translation_manager.load_translations(self, self.fake_context, translation_source)

    async def save_game_data(self, ctx, folder_path, file_name, business):
        await self.save_data_in_data_path_for_guild(ctx, folder_path, file_name, business)

    async def save_data_in_data_path_for_guild(self, ctx, folder_path, file_name, item):
        await self.save_data(folder_path, file_name, item)

    async def save_data_in_data_path(self, folder_path, file_name, item):
        await self.save_data(folder_path, file_name, item)

    async def save_data(self, folder_path, file_name, item):
        if isinstance(item, BusinessStatus):
            file = self.session.get_business(item.get_name())

        else:
            if not file_name.endswith(".json"):
                file_name += ".json"

            if not os.path.exists(folder_path):
                os.makedirs(folder_path)

            file = os.path.join(folder_path, file_name)

        data.save(item, file)

    def purchase_improvement(self, item):
        current_business = self.active_businesses[self.session.get_active_business()]
        self.loop.run_until_complete(current_business.apply_improvement(item, item.cost, 0))
        self.__refresh_simulation_views()

    def purchase_contract(self, item):
        current_business = self.active_businesses[self.session.get_active_business()]
        self.loop.run_until_complete(current_business.apply_contract(item, item.cost, 0))
        self.__refresh_simulation_views()

    def purchase_employee(self, item):
        current_business = self.active_businesses[self.session.get_active_business()]
        self.loop.run_until_complete(current_business.hire_employee(item, "BOB", 0))
        self.__refresh_simulation_views()
