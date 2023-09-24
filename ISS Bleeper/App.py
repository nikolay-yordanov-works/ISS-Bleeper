from data_files.satellite_load import satellite, ts
from tkintermapview import TkinterMapView
from geopy.distance import geodesic
from data_files.dataset_compute import calculate_dataset
import tkinter.messagebox as tk_msg
from PIL import Image, ImageTk
from skyfield.api import wgs84
import customtkinter
import pandas as pd
import requests
import datetime
import json
import os

customtkinter.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"
geo_api_key = "9a54aa335dc21480b55086abc908d5c2"


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        # configure counters, variables, containers, other settings
        self.generating_observations = False
        self.data_is_collected = False
        self.radius = 0
        self.counter = 1
        self.visibility_conditions = None
        self.city_params = None
        self.city_is_valid = False
        self.marker_observer_on = False
        self.FONT = ('Helvetica', 15, "bold")
        self.FONT_HEADER = ('Helvetica', 22, "bold")
        self.zoom = 1
        self.refresh_rate = 1000
        self.iss_lat = 0
        self.iss_lon = 0
        self.labels = []
        self.marker_iss_on = False
        self.current_index = 0
        self.seconds = 0
        self.current_path = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        self.icon = ImageTk.PhotoImage(Image.open(os.path.join(self.current_path, "./images", "0.png")).resize((50, 50)))

        # configure main window
        self.title("ISS Bleeper.py")
        self.geometry(f"{1650}x{800}")
        self.attributes('-fullscreen', False)

        # configure grid size and weight
        self.columnconfigure((1, 2, 3, 4, 5, 6, 7, 8, 9), weight=1)
        self.rowconfigure((0, 1, 2, 3, 4, 5, 6, 7, 8, 9), weight=1)
        self.columnconfigure(0, weight=0)

        # create and configure the map widget
        self.map_widget = TkinterMapView(self, corner_radius=8)
        self.map_widget.set_address("Varna")
        self.map_widget.set_zoom(1)
        self.map_widget.grid(row=1, column=2, columnspan=7, rowspan=7, padx=(10, 10), sticky="nsew", pady=(10, 10))

        # slidebar for zoom
        self.zoom_slider = customtkinter.CTkSlider(self,
                                                   from_=2, to=15,
                                                   number_of_steps=13,
                                                   command=self.get_slider_value)
        self.zoom_slider.grid(row=8, column=3, columnspan=6, padx=(20, 10), pady=(10, 10), sticky="ew")

        # slidebar for refresh rate of map
        self.refresh_slider = customtkinter.CTkSlider(self,
                                                      from_=5000, to=100,
                                                      number_of_steps=25,
                                                      command=self.refresh_slider_value)
        self.refresh_slider.grid(row=9, column=3, columnspan=6, padx=(20, 10), pady=(10, 10), sticky="ew")

        # city entry
        self.city_entry = customtkinter.CTkEntry(master=self,
                                                 placeholder_text="Type the name of your city to mark it on the map")
        self.city_entry.grid(row=0, column=2,  columnspan=7, padx=(10, 10), sticky="nsew", pady=(10, 10))

        # buttons
        self.search_city_btn = customtkinter.CTkButton(master=self,
                                                       text="Mark my city",
                                                       command=lambda: (self.get_city_and_place(),
                                                                        self.visibility_check(),
                                                                        self.update_labels()))
        self.search_city_btn.grid(pady=(10, 10), padx=(10, 10), row=0, column=9, sticky="nsew")

        self.search_iss_btn = customtkinter.CTkButton(master=self, text="Find the ISS", command=self.find_iss)
        self.search_iss_btn.grid(pady=(10, 10), padx=(10, 10), row=1, column=9, sticky="nsew")

        self.calc_distance_btn = customtkinter.CTkButton(master=self,
                                                         text="Calculate distance from observer",
                                                         command=self.calculate_distance)
        self.calc_distance_btn.grid(pady=(10, 10), padx=(10, 10), row=3, column=9, sticky="nsew")


        self.change_icon_btn = customtkinter.CTkButton(master=self, text="Change icon", command=self.set_icon)
        self.change_icon_btn.grid(pady=(10, 10), padx=(10, 10), row=2, column=9, sticky="nsew")

        self.find_observations_btn = customtkinter.CTkButton(master=self,
                                                             text="Compute Next Observations",
                                                             command=self.get_some_passes)
        self.find_observations_btn.grid(pady=(10, 10), padx=(10, 10), row=8, column=9, sticky="nsew")

        self.open_obser_window_btn = customtkinter.CTkButton(master=self,
                                                                    text="Show Results",
                                                                    command=self.check_if_data_is_collected)

        self.open_obser_window_btn.grid(pady=(10, 10), padx=(10, 10), row=9, column=9, sticky="nsew")



        # labels
        self.header_label = customtkinter.CTkLabel(self,
                                                   font=('Helvetica', 18, "bold"),
                                                   text="Some observational details about your location:",
                                                   anchor="w")
        self.header_label.grid(row=0, column=0, padx=(20, 20), pady=(5, 5), columnspan=2, sticky="nsew")

        self.zoom_slider_label = customtkinter.CTkLabel(self,
                                                        font=('Helvetica', 15),
                                                        text="Map zoom (1-14):  ",
                                                        anchor="e")
        self.zoom_slider_label.grid(row=8, column=2, padx=(10, 10), pady=(10, 10), sticky="nsew")

        self.days_to_compute_label = customtkinter.CTkLabel(self,
                                                            font=('Helvetica', 12),
                                                            text=f'Select how many days to compute. \nFor one day it takes'
                                                                 ' around \none minute of computation to yeild results.')
        self.days_to_compute_label.grid(row=4, column=9, padx=(10, 10), pady=(10, 10), sticky="nsew")
        self.choose_radius_label = customtkinter.CTkLabel(self,
                                                          font=('Helvetica', 12),
                                                          text=f'Select the radius around the observation \npoint.  '
                                                               'the optimal radius is 500km,\n and the smaller it is - '
                                                                '\nthe less results are returned.')
        self.choose_radius_label.grid(row=6, column=9, padx=(10, 10), pady=(10, 10), sticky="nsew")

        self.zoom_slider_label = customtkinter.CTkLabel(self,
                                                        font=('Helvetica', 15, "bold"),
                                                        text="Map - refresh rate (5.0s - 0.1s): ",
                                                        anchor="e")
        self.zoom_slider_label.grid(row=9, column=2, padx=(10, 10), pady=(10, 10), sticky="w")

        self.optionmenu_var = customtkinter.StringVar(value="Select days :")
        self.optionmenu = customtkinter.CTkOptionMenu(self, values=["1", "2", "3"],
                                                      command=self.optionmenu_callback,
                                                      variable=self.optionmenu_var)
        self.optionmenu.grid(row=5, column=9, padx=(10, 10), pady=(10, 10), sticky="wnes")


        self.optionmenu_var_ = customtkinter.StringVar(value="Select radius :")
        self.optionmenu_ = customtkinter.CTkOptionMenu(self, values=["100", "250", "500", "1000"],
                                                      command=self.optionmenu_callback_,
                                                      variable=self.optionmenu_var_)
        self.optionmenu_.grid(row=7, column=9, padx=(10, 10), pady=(10, 10), sticky="wnse")


    def optionmenu_callback(self, choice):
        """Get the days selected and turn them into seconds to use in further calculations """
        if int(choice) == 1:
            self.seconds = 86400
        elif int(choice) == 2:
            self.seconds = 172800
        elif int(choice) == 3:
            self.seconds = 259200

    def optionmenu_callback_(self, choice):
        """Get the radius selected to use in further calculations """
        if int(choice) == 100:
            self.radius = 100
        elif int(choice) == 250:
            self.radius = 250
        elif int(choice) == 500:
            self.radius = 500
        elif int(choice) == 1000:
            self.radius = 1000

    def check_if_data_is_collected(self):
        """This fuction check is data is collected, if not returns
        info message, else computes the data and opens Toplevel"""
        if self.data_is_collected is False:
            tk_msg.showinfo(title="No data collected yet!", message="You have not yet Computed Next Observations")
        else:
            calculate_dataset()
            self.open_predictive_mode_window()
            self.main()


    def open_predictive_mode_window(self):
        """Create the Toplevel window to map the observations."""
        if self.data_is_collected is True:
            observations_dict = self.read_json_data()
            self.number_of_observations = len(observations_dict)
            self.counter = 1  # counter == 1 at the beginning to show 1st observation
            self.predictive_mode = customtkinter.CTkToplevel(self)  # create the toplevel and set the grid
            self.predictive_mode.columnconfigure((0, 1, 2, 3, 4, 5, 6, 7, 8, 9), weight=1)
            self.predictive_mode.rowconfigure((0, 1, 2, 3, 4, 5, 6, 7, 8, 9), weight=1)
            self.predictive_mode.attributes('-topmost', True)
            self.predictive_mode.title("Predicted Observations")
            self.predictive_mode.geometry(f"{1200}x{800}")

            # static header and navigation buttons
            header = customtkinter.CTkLabel(self.predictive_mode,
                                            font=self.FONT_HEADER,
                                            text=f"For your selected observation point there"
                                                 f" are {self.number_of_observations} occurances ",
                                            anchor="w")
            header.grid(row=0, column=2, columnspan=7, rowspan=2, padx=(10, 10), pady=(10, 10), sticky="nsew")

            previous_btn = customtkinter.CTkButton(master=self.predictive_mode,
                                                   text=f"Previous",
                                                   command=self.previous)
            previous_btn.grid(pady=(10, 10), padx=(10, 10), row=8, column=2, sticky="nsew")

            next_btn = customtkinter.CTkButton(master=self.predictive_mode,
                                               text=f"Next",
                                               command=self.next)
            next_btn.grid(pady=(10, 10), padx=(10, 10), row=8, column=8, sticky="nsew")
        else:
            tk_msg.showinfo(title="There is no data collected yet to show observations!",
                            message='Please navigate to "Compute Next Observations" and after completion try again.')

    def main(self):
        """Re/Creates all the widgets and places them on the TopLevel."""
        # set map widget
        self.map_widget_ = TkinterMapView(self.predictive_mode, corner_radius=8)
        self.map_widget_.set_zoom(4)
        self.map_widget_.grid(row=2, column=2, columnspan=7, rowspan=6, padx=(10, 10), sticky="nsew", pady=(10, 10))

        # set all variables for the labels
        observations_dict = self.read_json_data()
        self.path = observations_dict[f'Observation ({self.counter})']['iss_cords']
        self.position_start = observations_dict[f'Observation ({self.counter})']['iss_cords'][0]
        self.starting_pt_start = float(self.position_start[0])
        self.ending_pt_start = float(self.position_start[-1])
        self.position_end = observations_dict[f'Observation ({self.counter})']['iss_cords'][-1]
        self.starting_pt_end = float(self.position_end[0])
        self.ending_pt_end = float(self.position_end[-1])
        self.duration = observations_dict[f'Observation ({self.counter})']['observation_duration']
        self.datetime_start = observations_dict[f'Observation ({self.counter})']['observation_start']
        self.datetime_end = observations_dict[f'Observation ({self.counter})']['observation_end']
        self.number_of_observations = len(observations_dict)

        # set path, starting and ending points on the map so user knows from where to start looking
        self.path_1 = self.map_widget_.set_path(self.path)
        self.observation_end_position = self.map_widget_.set_position(self.starting_pt_end, self.ending_pt_end,
                                                                      marker=True)
        self.observation_end_position.set_text(f"Ending")
        self.observation_start_position = self.map_widget_.set_position(self.starting_pt_start, self.ending_pt_start,
                                                                        marker=True)
        self.observation_start_position.set_text(f"Beginning")

        # set labels for the observation details
        self.duration_of_event = customtkinter.CTkLabel(self.predictive_mode,
                                                   font=self.FONT,
                                                   text=f"Duration of observation (in seconds): {self.duration}",
                                                   anchor="w")
        self.duration_of_event.grid(row=2, column=0, padx=(10, 10), pady=(10, 10), sticky="w")
        self.start_observing = customtkinter.CTkLabel(self.predictive_mode,
                                                 font=self.FONT,
                                                 text=f"Start observing at: {self.datetime_start}",
                                                 anchor="w")
        self.start_observing.grid(row=3, column=0, padx=(10, 10), pady=(10, 10), sticky="w")
        self.end_observing = customtkinter.CTkLabel(self.predictive_mode,
                                               font=self.FONT,
                                               text=f"End of observation : {self.datetime_end}",
                                               anchor="w")
        self.end_observing.grid(row=4, column=0, padx=(10, 10), pady=(10, 10), sticky="w")


    def next(self):
        """This function adds 1 to the counter if not more than len(observations_dict).
        Afterward reset the toplevel widgets."""
        observations_dict = self.read_json_data()
        if self.counter <= len(observations_dict) - 1:
            self.counter += 1
            self.reset_toplevel_items()

    def previous(self):
        """This function removes 1 from the counter if not less than 2.
        Afterward reset the toplevel widgets."""
        if self.counter >= 2:
            self.counter -= 1
            self.reset_toplevel_items()

    def reset_toplevel_items(self):
        """Delete all widgets in toplevel window and call main() to re-create them.
        This is to be used in conjunction with next/previous buttons."""
        self.path_1.delete()
        self.observation_end_position.delete()
        self.observation_start_position.delete()
        self.duration_of_event.destroy()
        self.start_observing.destroy()
        self.end_observing.destroy()
        self.main()

    def get_slider_value(self, value):
        """ Get the slider value and set the map zoom accordingly"""
        self.zoom = int(value)
        self.map_widget.set_zoom(int(value))  # to enable this for non-live view

    def refresh_slider_value(self, value):
        """ Get the slider value and set the tkinter.after() function accordingly.
        This makes the calculations and hence the whole app refresh faster"""
        self.refresh_rate = int(value)

    def update_labels(self):
        """This function holds and updates all the leftside labels concerning observer location details"""
        # city name
        if self.city_is_valid is True:
            self.all_leftside_labels = customtkinter.CTkLabel(self,
                                                              font=self.FONT,
                                                              text=f"Your City: {self.city_params['city_name']}",
                                                              anchor="w")
            self.all_leftside_labels.grid(row=1, column=0, padx=(10, 10), pady=(10, 10), sticky="w")
            self.labels.append(self.all_leftside_labels)
            # country name
            self.all_leftside_labels = customtkinter.CTkLabel(self,
                                                              font=self.FONT,
                                                              text=f"Your Country: {self.city_params['country']}",
                                                              anchor="w")
            self.all_leftside_labels.grid(row=2, column=0, padx=(10, 10), pady=(10, 10), sticky="w")
            self.labels.append(self.all_leftside_labels)
            #  lat / lon of observer
            self.all_leftside_labels = customtkinter.CTkLabel(self,
                                                              font=self.FONT,
                                                              text=f"Oberver Geo Coordinates: ({self.city_params['city_lon']} /"
                                                                   f" {self.city_params['city_lat']})",
                                                              anchor="w")
            self.all_leftside_labels.grid(row=3, column=0, padx=(10, 10), pady=(10, 10), sticky="w")
            self.labels.append(self.all_leftside_labels)
            # weather conditions
            self.all_leftside_labels = customtkinter.CTkLabel(self,
                                                              font=self.FONT,
                                                              text=f"Weather Conditions:{self.visibility_conditions['current_weather']}, "
                                                                   f"{self.visibility_conditions['weather_details'].title()}",
                                                              anchor="w")
            self.all_leftside_labels.grid(row=4, column=0, padx=(10, 10), pady=(10, 10), sticky="w")
            self.labels.append(self.all_leftside_labels)
            # sunset and sunrise
            self.all_leftside_labels = customtkinter.CTkLabel(self,
                                                              font=self.FONT,
                                                              text=f"Sunset and Sunrise: {self.visibility_conditions['sunrise']} /"
                                                                   f" {self.visibility_conditions['sunset']}",
                                                              anchor="w")
            self.all_leftside_labels.grid(row=5, column=0, padx=(10, 10), pady=(10, 10), sticky="w")
            self.labels.append(self.all_leftside_labels)

    def find_iss(self):
        """Check if ISS marker is placed on the map, if not then call
         update_iss_location() to create, place and update the marker"""
        if self.marker_iss_on is False:
            self.update_iss_location()

    def update_iss_location(self):
        """Calculate the current/live position of ISS from TLE file according to the time.now().Places a marker on the
            tkintermap at intervals of refresh_rate after which marker is destroyed and the function is called again"""

        # import satellite and time(ts) objects created from the TLE file
        t = ts.now()  # get current time and calculate the geocentric position
        geocentric = satellite.at(t)  # calculate the geocentric position at time (t)
        position = str(wgs84.geographic_position_of(geocentric))  # return lat/lon/elevation for geographic position

        # separate lat/lon/elevation from the position
        self.iss_lat, self.iss_lon = float(position[14:23]), float(position[35:43])
        self.iss_elevation = position[56:]

        # set the marker on the map
        marker_iss = self.map_widget.set_position(self.iss_lat, self.iss_lon, marker=True, icon=self.icon)
        marker_iss.set_text(f"ISS Live Position - ({self.iss_lat} / {self.iss_lon})")
        self.marker_iss_on = True

        self.map_widget.set_zoom(self.zoom)  # set zoom from slider last value, or get default of 1
        # set zoom before calling the function again
        self.map_widget.after(self.refresh_rate, marker_iss.delete)  # afer a certain period delete the marker
        self.map_widget.after(self.refresh_rate, self.update_iss_location)  # re-create the marker on new position

    def set_icon(self):
        """This function changes the icons of the ISS"""
        if self.marker_iss_on is False:  # if ISS is not on map, place it and continue
            self.update_iss_location()

        # set the path, open the images, resize them, create ImageTK obejcts and initiate the list
        current_path = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        img_0 = ImageTk.PhotoImage(Image.open(os.path.join(current_path, "./images", "0.png")).resize((50, 50)))
        img_1 = ImageTk.PhotoImage(Image.open(os.path.join(current_path, "./images", "1.png")).resize((70, 70)))
        img_2 = ImageTk.PhotoImage(Image.open(os.path.join(current_path, "./images", "2.png")).resize((70, 70)))
        img_3 = ImageTk.PhotoImage(Image.open(os.path.join(current_path, "./images", "3.png")).resize((80, 60)))
        img_4 = ImageTk.PhotoImage(Image.open(os.path.join(current_path, "./images", "4.png")).resize((70, 70)))
        img_5 = ImageTk.PhotoImage(Image.open(os.path.join(current_path, "./images", "5.png")).resize((70, 70)))
        img_6 = ImageTk.PhotoImage(Image.open(os.path.join(current_path, "./images", "6.png")).resize((70, 70)))
        img_7 = ImageTk.PhotoImage(Image.open(os.path.join(current_path, "./images", "7.png")).resize((80, 40)))
        # the deathstar image has to be bigger for obvious reasons
        img_8 = ImageTk.PhotoImage(Image.open(os.path.join(current_path, "./images", "8.png")).resize((80, 80)))

        self.icon_list = [img_0, img_1, img_2, img_3, img_4, img_5, img_6, img_7, img_8]

        # perform checks to make sure we are not outside the list
        if self.current_index < len(self.icon_list):
            self.current_index += 1
            if self.current_index == len(self.icon_list):
                self.current_index = 0  # Reset to the beginning of the list if end was reached
        self.icon = self.icon_list[self.current_index]

    def get_city_and_place(self):
        """This function takes as input a string of a city name and
        returns in a dictionary the lat, lon, city name and country code."""

        if self.marker_observer_on is False:  # if is not placed - create it and update marker status
            try:
                city = self.city_entry.get().strip().capitalize()

                geo_api_call = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={geo_api_key}"
                response = requests.get(f"{geo_api_call}")
                response.raise_for_status()
                data = response.json()

                lat = float(str(data[0]['lat'])[0:8])
                lon = float(str(data[0]['lon'])[0:8])

                self.city_params = {
                    "city_lon": float(lon),
                    "city_lat": float(lat),
                    "city_name": data[0]['name'],
                    "country": data[0]['country']
                }
                self.marker_observer = self.map_widget.set_position(lat, lon, marker=True)
                self.marker_observer.set_text(f"{self.city_params['city_name']},{self.city_params['country']}")
                self.marker_observer_on = True
                self.city_is_valid = True
            except Exception as e:
                self.city_is_valid = False
                tk_msg.showinfo(title="Error when placing city on the map",
                                message="Perhaps you made a typo, or wrote invalid observation location. "
                                        "Please try writing your city name again.")
        else:
            # delete old labels and observation marker, then run again
            for label in self.labels:
                label.destroy()
            self.marker_observer.delete()
            self.marker_observer_on = False
            self.get_city_and_place()

    def visibility_check(self):
        """This function takes as input a string of a city name and returns in
        a dictionary the weather conditions, Sunrise, Sunset, and Current Time """
        # get city and find weather conditions, sunrise, sunset
        city = self.city_entry.get()
        city_name = city.strip().capitalize()
        try:
            city_api_call = f"https://api.openweathermap.org/data/2.5/weather?q={city_name}&appid={geo_api_key}"
            response = requests.get(f"{city_api_call}")
            response.raise_for_status()
            data = response.json()
            self.visibility_conditions = {
                "current_weather": data['weather'][0]['main'],
                "weather_details": data['weather'][0]['description'],
                "sunset": self.time_converter(data['sys']['sunset']),
                "sunrise": self.time_converter(data['sys']['sunrise']),
            }
            self.city_is_valid = True
        except Exception as e:
            self.city_is_valid = False


    def calculate_distance(self):
        """This function calculates the distance between current city and ISS. Returns the distance in kms"""
        if self.marker_observer_on is False:
            tk_msg.showinfo(title="There is no city marked on the map!", message="First search your observation "
                                                                                 "location and then place it on the map"
                                                                                 ". Then try to compute  the distance.")
        else:
            if self.marker_iss_on is False:  # if ISS not shown, put it on the map, and continue
                self.update_iss_location()

            city_cords = (self.city_params['city_lat'], self.city_params['city_lon'])
            cords = (self.iss_lat, self.iss_lon)
            self.kms_distance = f"{geodesic(cords, city_cords).kilometers:.1f} km"

            # kms distance to observer
            self.all_leftside_labels = customtkinter.CTkLabel(self,
                                                              font=self.FONT,
                                                              text=f"Distance from observer: {self.kms_distance}",
                                                              anchor="w")
            self.all_leftside_labels.grid(row=6, column=0, padx=(10, 10), pady=(10, 10), sticky="w")
            # elevation
            self.all_leftside_labels = customtkinter.CTkLabel(self,
                                                              font=self.FONT,
                                                              text=f"Elevation: {self.iss_elevation}",
                                                              anchor="w")
            self.all_leftside_labels.grid(row=7, column=0, padx=(10, 10), pady=(10, 10), sticky="w")

            # status of generating distance
            if self.generating_observations is True:
                self.all_leftside_labels = customtkinter.CTkLabel(self,
                                                                  font=self.FONT,
                                                                  text=f"STATUS: GENERATING OBSERVATIONS...",
                                                                  anchor="w")
                self.all_leftside_labels.grid(row=8, column=0, padx=(10, 10), pady=(10, 10), sticky="w")
            elif self.generating_observations is False:
                self.all_leftside_labels = customtkinter.CTkLabel(self,
                                                                  font=self.FONT,
                                                                  text=f"STATUS: IDLE WAITING FOR TASKS...",
                                                                  anchor="w")
                self.all_leftside_labels.grid(row=8, column=0, padx=(10, 10), pady=(10, 10), sticky="w")

            # call function again and update label
            self.after(self.refresh_rate, self.calculate_distance)

    def time_converter(self, unix_time):
        """This function converts a Unix/Epoch timestamp integer into regular string of
        YYYY-MM-DD HH:MM:SS which is returned"""

        date_time = str(datetime.datetime.fromtimestamp(unix_time))
        self.just_time = date_time[11::]

        return self.just_time

    def get_some_passes(self):
        """Gets the city lat/lon and ISS lat/lon, then computes the overhead passes for the seelcted days and radius"""
        if self.marker_observer_on is False:
            tk_msg.showinfo(title="There is no city marked on the map!",
                            message='Please type your city and click "Mark my city".')
        elif self.radius == 0 or self.seconds == 0:
            tk_msg.showinfo(title="The Radius and Days to compute are not set!",
                            message="Please navigate to the dropdown menus and select radius and days.")
        else:
            tk_msg.showinfo(title="Patience is bitter, but its fruit is sweet.",
                            message="Why does it take one minute to compute one day of calculations? Well, to calculate"
                                    " orbit is not an easy task. There are some heavy equations at play here which "
                                    "(for context) even factor the seconds delay that the sun takes to travel to the"
                                    " earth. At maximum radius of 1000 results will be calculated in approximately 3 "
                                    "minutes. You will be notified once we are done :). Thank you for your patience. ")
            self.find_iss()
            seconds_to_add = 0

            # to use as starting point for the loop and to mark at what point in time to start adding the seconds_to_add
            current_time = datetime.datetime.now()
            overhead_pass_dataset = {           #container for the dataset
                "loop_start": current_time,
                "iss_cords": [],
                "city_cords": [],
                "seconds_passed": []
            }

            # passes_city_params = get_city_params(city)  # call function with city to get latitude and longitude
            passes_city_lat, passes_city_lon = float(self.city_params['city_lat']), float(self.city_params['city_lon'])
            self.generating_observations = True
            while seconds_to_add <= self.seconds:
                d = ts.utc(year=current_time.year, month=current_time.month, day=current_time.day, hour=current_time.hour,
                           minute=current_time.minute, second=current_time.second + seconds_to_add)
                # current position of satellite at 'd', return tuple of floats
                geocentric = satellite.at(d)
                position = str(wgs84.geographic_position_of(geocentric))
                iss_passes_lat, iss_passes_lon = float(position[14:23]), float(position[35:42])

                city_cords = (passes_city_lat, passes_city_lon)
                iss_cords = (iss_passes_lat, iss_passes_lon)
                kms_distance = geodesic(iss_cords, city_cords).kilometers
                # print(f" Distance between objects -> {kms_distance} km. Added seconds -> {seconds_to_add}."
                #       f" ISS / City locations -> {iss_cords} / {city_cords} ")

                if kms_distance <= self.radius:
                    overhead_pass_dataset['iss_cords'].append(iss_cords)
                    overhead_pass_dataset['city_cords'].append(city_cords)
                    overhead_pass_dataset['seconds_passed'].append(seconds_to_add)

                seconds_to_add += 1

                self.update()

            #  catch here occurance if the dataset is lenght of 0
            if overhead_pass_dataset['iss_cords'] == []:
                tk_msg.showinfo(title="WAITING IS OVER! ",
                                message=f"No observations are found for your criterea. Please increase the radius or number of days.")
            else:
                tk_msg.showinfo(title="WAITING IS OVER! ",
                                message=f"We did some tough maths there! Now click on Show Generated "
                                        f"Observations to see them mapped out. ")
                df = pd.DataFrame.from_dict(overhead_pass_dataset)
                df.to_csv('observations_dataset.csv', mode='w')
                self.data_is_collected = True
            self.generating_observations = False
            return overhead_pass_dataset



    def read_json_data(self):
        # Read the JSON file and convert it into a dictionary
        with open('data_files/observations_dict_json.json', 'r') as json_file:
            observations_dict = json.load(json_file)
        return observations_dict


if __name__ == "__main__":
    app = App()
    app.read_json_data()
    app.mainloop()
