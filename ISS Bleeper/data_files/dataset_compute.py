from datetime import datetime, timedelta
import pandas as pd
import ast
import pprint
import json


def calculate_dataset():

    def convert_time(time, seconds_to_add):
        """This function receives a time (start of loop) and seconds_to_add.
        Adds the seconds to start of the loop and returns a new time string"""

        # Convert the datetime string to a datetime object
        datetime_obj = datetime.strptime(time, "%Y-%m-%d %H:%M:%S")

        # Add seconds to the datetime object
        new_datetime_obj = datetime_obj + timedelta(seconds=seconds_to_add)

        # Convert the new datetime object back to a string
        new_datetime_string = new_datetime_obj.strftime("%Y-%m-%d %H:%M:%S")

        # Print the new datetime string
        # print(f"Original Datetime:, {time}. New Datetime with Added Seconds:, {new_datetime_string}")
        return new_datetime_string

    def get_seconds_passed(iss_cords_to_find):
        """This function gets coordinates, searches the df and returns the seconds_passed """

        for index, row in df.iterrows():
            if row['iss_cords'] == str(iss_cords_to_find):
                return row['seconds_passed']
        return None  # Return None if 'iss_cords' not found


    # create nested dict to hold observations
    observations_dict = {}

    # creating a data frame
    dataset = pd.read_csv('observations_dataset.csv')

    # Sample DataFrame with a column 'numbers'
    df = pd.DataFrame(dataset)

    # Initialize variables to track sequences
    current_sequence = []
    sequences = []

    # Check if the current number continues the sequence
    for num in dataset['seconds_passed']:
        if not current_sequence or num == current_sequence[-1] + 1:
            current_sequence.append(num)
        else:
            # If it doesn't continue the sequence, store the current sequence
            sequences.append(current_sequence)
            current_sequence = [num]

    # Append the last sequence
    sequences.append(current_sequence)

    # Create a nested dictionary and add each sequence with corresponding 'iss_cords' value
    for i, sequence in enumerate(sequences, start=1):
        key = f"Observation ({i})"
        nested_dict = {
            "iss_cords": [ast.literal_eval(coord) for coord in df.loc[df['seconds_passed'].isin(sequence)]['iss_cords']]
        }   # convert the strings of coordinates to tuples of corodinates
        observations_dict[key] = nested_dict

        # get lenght of coords (each coord pair is 1 second), hence total number of pairs is the full encounter duration
        nested_list = observations_dict[key]["iss_cords"]
        length = len(nested_list)

        # Add the length to the nested dictionary for the specified key
        observations_dict[key]["observation_duration"] = length

        # Get the first and last values for each encounter marking the start and end of the observation
        first_value = nested_list[0]
        last_value = nested_list[-1]

        # for the cords from first and last observation points, get the seconds passed
        iss_cords_to_find = first_value
        iss_cords_to_find_ = last_value
        seconds_passed_start = get_seconds_passed(iss_cords_to_find)
        seconds_passed_end = get_seconds_passed(iss_cords_to_find_)

        loop_start = df['loop_start'].iloc[0][0:19]

        observation_start = convert_time(time=loop_start, seconds_to_add=seconds_passed_start)
        observation_end = convert_time(time=loop_start, seconds_to_add=seconds_passed_end)

        # Update the nested dictionary with observation_start and observation_end
        observations_dict[key]['observation_start'] = observation_start
        observations_dict[key]['observation_end'] = observation_end

        # pprint.pprint(observations_dict, indent=4, width=150, compact=True)

    with open("observations_dict_json.json", 'w') as json_file:
        json.dump(observations_dict, json_file, indent=4)
