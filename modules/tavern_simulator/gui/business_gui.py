import asyncio
import os
from tkinter import Tk, Menu, filedialog, ttk, messagebox, Label, PanedWindow, Button, END, Frame
from tkinter.scrolledtext import ScrolledText

from modules.tavern_simulator.gui.gui_view_builder import build_status_view, build_data_pack_overview, build_data_pack_items_view
from modules.tavern_simulator.gui.player_view_builder import build_status_view_players, build_purchaseable_view_players
from modules.tavern_simulator.gui.widgets import ScrollFrame
from modules.tavern_simulator.model.new_data_pack import DataPack
from modules.tavern_simulator.tavern_controller import Tavern
from utils import data

"""
USER STOREIS:
    1) Create new data pack
    
        or
        
    2) Load existing


"""


class BusinessGUI(Tk):
    def __init__(self):
        super().__init__()
        self.geometry("640x480")

        self.title = "Business Viewer"
        self.loop = asyncio.new_event_loop()

        # Menus
        self.__setup_menus()

        # Main display
        self.window = PanedWindow(orient="horizontal")
        self.window.pack(expand=1, fill="both")

        # Data pack properties
        self.data_pack_path = ""
        self.current_data_pack = None
        self.data_pack_raw_display = False
        self.__setup_data_pack_views()

        # Simulation properties
        self.simulation_path = ""
        self.simulation_name = ""
        self.simulation = None
        self.discord_view = False
        self.simulation_summary = None
        self.__setup_simulation_views()

    def new_data_pack(self):
        data_pack_path = filedialog.askdirectory(title="Please select the data pack folder.")
        if data_pack_path == "":
            return

        if len(os.listdir(data_pack_path)) != 0:
            messagebox.showerror("Error", "The provided folder is not empty. Please provide an empty folder.")
            return

        data_pack_name = os.path.basename(os.path.dirname(self.data_pack_path))

        self.current_data_pack = DataPack(data_pack_name, self.data_pack_path, False, business_name=data_pack_name, description="")
        self.data_pack_path = data_pack_path
        self.save_data_pack()

    def load_data_pack(self):
        self.data_pack_path = filedialog.askdirectory(title="Please select the data pack folder.")
        if self.data_pack_path == "":
            return

        data_pack_name = os.path.basename(os.path.dirname(self.data_pack_path))

        data_pack_data = data.load(os.path.join(self.data_pack_path, "data_pack.json"))
        initial = data.load(os.path.join(self.data_pack_path, "initial.json"))
        services = data.load(os.path.join(self.data_pack_path, "services.json"))
        employees = data.load(os.path.join(self.data_pack_path, "employees.json"))
        customers = data.load(os.path.join(self.data_pack_path, "customers.json"))
        upgrades = data.load(os.path.join(self.data_pack_path, "upgrades.json"))
        contracts = data.load(os.path.join(self.data_pack_path, "contracts.json"))
        self.current_data_pack = DataPack(data_pack_name, self.data_pack_path, False, data_pack_data=data_pack_data, initial=initial, services=services, staff=employees, patrons=customers, upgrades=upgrades, contracts=contracts)

        self.__refresh_data_pack()

    def save_data_pack_as(self):
        data_pack_path = filedialog.askdirectory(title="Please select the folder to save the data pack in.")
        if data_pack_path == "":
            return

        topmost_folder = os.path.basename(os.path.dirname(data_pack_path))
        if topmost_folder == self.current_data_pack.get_name():
            self.data_pack_path = data_pack_path
        else:
            self.data_pack_path = os.path.join(data_pack_path, self.current_data_pack.get_name())
            os.makedirs(self.data_pack_path)

        self.save_data_pack()

    def save_data_pack(self):
        data.save(self.current_data_pack.data_pack_data, os.path.join(self.data_pack_path, "data_pack.json"))
        data.save(self.current_data_pack.initial, os.path.join(self.data_pack_path, "initial.json"))
        data.save(self.current_data_pack.services, os.path.join(self.data_pack_path, "services.json"))
        data.save(self.current_data_pack.employee, os.path.join(self.data_pack_path, "employees.json"))
        data.save(self.current_data_pack.patrons, os.path.join(self.data_pack_path, "customers.json"))
        data.save(self.current_data_pack.upgrades, os.path.join(self.data_pack_path, "upgrades.json"))
        data.save(self.current_data_pack.contracts, os.path.join(self.data_pack_path, "contracts.json"))

        self.__refresh_data_pack()

    def clear_data_pack(self):
        self.data_pack_path = ""
        self.current_data_pack = None
        self.__toggle_data_pack(force=False)

    def new_simulation(self):
        if self.current_data_pack is None:
            messagebox.showerror("Error", "You cannot start a simulation without a data pack present.")
            return

        simulation_path = filedialog.askdirectory()
        if simulation_path == "":
            return

        simulation_name = self.current_data_pack.get_name() + "_simulation.json"
        full_path = os.path.join(simulation_path, simulation_name)
        if os.path.isfile(full_path):
            messagebox.showerror("Error", "Cannot create the desired simulation as a file already exists with that name.")

        self.simulation_name = simulation_name
        self.simulation_path = simulation_path
        self.simulation = Tavern()
        self.loop.run_until_complete(self.simulation.set_data_pack(self.current_data_pack))

        data.save(self.simulation.get_tavern_status(), full_path)
        self.__refresh_simulation()

    def load_simulation(self):
        answer = filedialog.askopenfilename(title="Please select your existing simulation file:", filetypes=[("simulation files", ".json")])
        if answer == "":
            return

        self.simulation_path = os.path.dirname(answer)
        self.simulation_name = os.path.basename(answer)
        tavern_status = data.load(answer)
        self.simulation = Tavern(tavern_status=tavern_status)
        self.loop.run_until_complete(self.simulation.set_data_pack(self.current_data_pack))
        self.__refresh_simulation()

    def save_simulation(self):
        data.save(self.simulation.get_tavern_status(), os.path.join(self.simulation_path, self.simulation_name))
        self.__refresh_simulation()

    def save_simulation_as(self):
        answer = filedialog.asksaveasfilename(title="Please select a file name for saving:", filetypes=[("simulation files", ".json")])
        if answer == "":
            return

        self.simulation_path = os.path.dirname(answer)
        self.simulation_name = os.path.basename(answer)
        data.save(self.simulation.get_tavern_status(), os.path.join(self.simulation_path, self.simulation_name))
        self.__refresh_simulation()

    def clear_simulation(self):
        self.simulation_path = ""
        self.simulation_name = ""
        self.simulation = None
        self.__refresh_simulation()

    def toggle_discord(self):
        self.discord_view = not self.discord_view
        self.__refresh_simulation()

    def purchase_upgrade(self):
        available_upgrades = self.simulation.get_upgradeable()
        display_values = list()
        for item in available_upgrades:
            display_values.append(item.get_key())

        pass

    def purchase_contract(self):
        pass

    def purchase_staff(self):
        pass

    def __setup_menus(self):
        self.menu = Menu(self)

        self.data_pack_menu = Menu(self.menu, tearoff=0)
        self.data_pack_menu.add_command(label="New", command=self.new_data_pack)
        self.data_pack_menu.add_command(label="Load", command=self.load_data_pack)
        self.data_pack_menu.add_command(label="Save", command=self.save_data_pack)
        self.data_pack_menu.add_command(label="Save As", command=self.save_data_pack_as)
        self.data_pack_menu.add_command(label="Clear", command=self.clear_data_pack)
        self.menu.add_cascade(label="Data Pack", menu=self.data_pack_menu)

        self.simulation_menu = Menu(self.menu, tearoff=0)
        self.simulation_menu.add_command(label="New", command=self.new_simulation)
        self.simulation_menu.add_command(label="Load", command=self.load_simulation)
        self.simulation_menu.add_command(label="Save", command=self.save_simulation)
        self.simulation_menu.add_command(label="Save As", command=self.save_simulation_as)
        self.simulation_menu.add_command(label="Clear", command=self.clear_simulation)
        self.menu.add_cascade(label="Simulation", menu=self.simulation_menu)

        self.config(menu=self.menu)

    def __setup_data_pack_views(self):
        self.data_pack_frame = Frame(self.window)

        # View frame
        self.data_pack_tabs = ttk.Notebook(self.data_pack_frame)

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

        self.data_pack_upgrades = Frame(self.data_pack_tabs)
        self.data_pack_tabs.add(self.data_pack_upgrades, text="Upgrades")
        self.data_pack_upgrades_content = None

        self.data_pack_contracts = Frame(self.data_pack_tabs)
        self.data_pack_tabs.add(self.data_pack_contracts, text="Contracts")
        self.data_pack_contracts_content = None

        self.data_pack_employees = Frame(self.data_pack_tabs)
        self.data_pack_tabs.add(self.data_pack_employees, text="Employees")
        self.data_pack_employees_content = None

        # Controls frame
        self.data_pack_controls = Frame(self.data_pack_frame)
        test_label = Label(self.data_pack_controls, text="Name:")
        test_label.grid(column=0, row=0)

        # Packing
        self.data_pack_tabs.pack(expand=1, fill="both")
        self.data_pack_controls.pack(expand=0, fill="x")
        self.data_pack_frame.pack(expand=1, fill="both")
        self.window.add(self.data_pack_frame)

    def __refresh_data_pack(self):
        if self.current_data_pack is not None:
            self.__fill_data_pack()
        else:
            self.__delete_data_pack_display()

    def __fill_data_pack(self):
        self.__delete_data_pack_display()

        # Display raw string
        if self.data_pack_raw_display:
            pass

        # Display as gui objects
        else:
            # Add the overview information
            self.overview_content = Frame(self.data_pack_overview)
            build_data_pack_overview(self.overview_content, self.current_data_pack)
            self.overview_content.pack(expand=1, fill="both")

            # Add the initial items
            self.data_pack_initial_content = ScrollFrame(self.data_pack_initial)
            build_data_pack_items_view(self.data_pack_initial_content.view_port, self.current_data_pack.get_initial_states())
            self.data_pack_initial_content.pack(expand=1, fill="both")

            # Add the services
            self.data_pack_services_content = ScrollFrame(self.data_pack_services)
            build_data_pack_items_view(self.data_pack_services_content.view_port, self.current_data_pack.get_services())
            self.data_pack_services_content.pack(expand=1, fill="both")

            # Add the services
            self.data_pack_customers_content = ScrollFrame(self.data_pack_customers)
            build_data_pack_items_view(self.data_pack_customers_content.view_port, self.current_data_pack.get_customers())
            self.data_pack_customers_content.pack(expand=1, fill="both")

            # Add the upgrades
            self.data_pack_upgrades_content = ScrollFrame(self.data_pack_upgrades)
            build_data_pack_items_view(self.data_pack_upgrades_content.view_port, self.current_data_pack.get_upgrades())
            self.data_pack_upgrades_content.pack(expand=1, fill="both")

            # Add the contracts
            self.data_pack_contracts_content = ScrollFrame(self.data_pack_contracts)
            build_data_pack_items_view(self.data_pack_contracts_content.view_port, self.current_data_pack.get_contracts())
            self.data_pack_contracts_content.pack(expand=1, fill="both")

            # Add the employees
            self.data_pack_employees_content = ScrollFrame(self.data_pack_employees)
            build_data_pack_items_view(self.data_pack_employees_content.view_port, self.current_data_pack.get_employee_archetypes())
            self.data_pack_employees_content.pack(expand=1, fill="both")

    def __delete_data_pack_display(self):
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

        if self.data_pack_upgrades_content is not None:
            self.data_pack_upgrades_content.pack_forget()
            self.data_pack_upgrades_content.destroy()

        if self.data_pack_contracts_content is not None:
            self.data_pack_contracts_content.pack_forget()
            self.data_pack_contracts_content.destroy()

        if self.data_pack_employees_content is not None:
            self.data_pack_employees_content.pack_forget()
            self.data_pack_employees_content.destroy()

    def __setup_simulation_views(self):
        self.simulation_frame = Frame(self.window)

        # View frame
        self.simulation_tabs = ttk.Notebook(self.simulation_frame)

        self.simulation_overview = Frame(self.simulation_tabs)
        self.simulation_tabs.add(self.simulation_overview, text="Overview")

        self.simulation_available = Frame(self.simulation_tabs)
        self.simulation_tabs.add(self.simulation_available, text="Available")

        # TODO: Resizeable split here
        # TODO: Tabs with purchase type
        # TODO: Purchase button
        # TODO: This should depend on the view
        # TODO: Removed / Not working / Not available

        # Controls frame
        self.simulation_controls = Frame(self.simulation_frame)

        overview_frame = Frame(self.simulation_controls)
        test_label = Label(overview_frame, text="Simulation Controls:")
        test_label.grid(column=0, row=0)

        overview_frame.pack(expand=0, fill="x")
        views = ttk.LabelFrame(self.simulation_controls, text="Views:")
        discord_view = Button(views, text="Toggle Discord", command=self.toggle_discord)
        discord_view.grid(column=0, row=0)
        views.pack(expand=0, fill="x")

        # Packing
        self.simulation_tabs.pack(expand=1, fill="both")
        self.simulation_controls.pack(expand=0, fill="x")
        self.simulation_frame.pack(expand=1, fill="both")
        self.window.add(self.simulation_frame)

    def __refresh_simulation(self):
        if self.simulation is not None:
            self.__fill_simulation()
        else:
            self.__forget_simulation()

    def __fill_simulation(self):
        self.__fill_overview()
        self.__fill_purchaseable()

        # TODO: This should depend on the view
        # TODO: Current / Potential / Removed / Not working / Not available

    def __fill_overview(self):
        # Clean up
        if self.simulation_summary is not None:
            self.simulation_summary.pack_forget()
            self.simulation_summary.destroy()

        # Are we attempting to represent what the players would see?
        if self.discord_view:
            # Create our status representation in long message form
            long_message = self.loop.run_until_complete(build_status_view_players(self.simulation, None, None))

            # Just convert this to a string for our display
            string_form = ""
            for message in long_message:
                string_form += message + "\n"

            # Strip out the formatting marks
            string_form = string_form.replace("`", "")

            # Add this to our view
            self.simulation_summary = ScrolledText(self.simulation_overview)
            self.simulation_summary.insert(1.0, string_form)
            self.simulation_summary.pack(expand=1, fill="both")

        # We should just build it in gui form
        else:
            # Add the actual display items
            self.simulation_summary = ScrollFrame(self.simulation_overview)
            build_status_view(self.simulation_summary.view_port, self.simulation)
            self.simulation_summary.pack(expand=1, fill="both")

    def __fill_purchaseable(self):
        # Create our status representation in long message form
        long_message = self.loop.run_until_complete(build_purchaseable_view_players(self.simulation, None, None))

        # Just convert this to a string for our display
        string_form = ""
        for message in long_message:
            string_form += message + "\n"

        # Strip out the formatting marks
        string_form = string_form.replace("`", "")

        # Add this to our view
        self.simulation_purchaseable = ScrolledText(self.simulation_available)
        self.simulation_purchaseable.insert(1.0, string_form)
        self.simulation_purchaseable.pack(expand=1, fill="both")

    def __forget_simulation(self):
        self.simulation_summary.delete(1.0, END)
        self.simulation_purchaseable.delete(1.0, END)


gui = BusinessGUI()
gui.mainloop()
