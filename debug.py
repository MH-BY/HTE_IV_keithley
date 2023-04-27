#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 27 16:50:45 2023

@author: ebeem
"""
import csv
import tkinter as tk

# Initialize the parameter variables
param_min_volt = None
param_max_volt = None
param_steps_no = None
param_cell_area = None
param_scan_rate = None
param_irr = None
param_temp = None
param_curr_lim = None
param_delay = None
param_multidelay = None
param_voltrange = None
param_currentrange = None

# Read the measurement parameters from the CSV file
filename = 'parameters.csv'
with open(filename, 'r') as file:
    reader = csv.reader(file)
    next(reader)  # Skip the header row
    for row in reader:
        if row[0] == 'param_min_volt':
            param_min_volt = row[1]
        elif row[0] == 'param_max_volt':
            param_max_volt = row[1]
        elif row[0] == 'param_steps_no':
            param_steps_no =row[1]
        elif row[0] == 'param_cell_area':
            param_cell_area = row[1]
        elif row[0] == 'param_scan_rate':
            param_scan_rate =row[1]
        elif row[0] == 'param_irr':
            param_irr = row[1]
        elif row[0] == 'param_temp':
            param_temp =row[1]
        elif row[0] == 'param_curr_lim':
            param_curr_lim = row[1]
        elif row[0] == 'param_delay':
            param_delay =row[1]
        elif row[0] == 'param_multidelay':
            param_multidelay = row[1]
        elif row[0] == 'param_voltrange':
            param_voltrange =row[1]
        elif row[0] == 'param_currentrange':
            param_currentrange = row[1]
        

print(param_min_volt)
print(param_max_volt)
print(param_steps_no)
print(param_cell_area)
print(param_scan_rate)
print(param_irr)
print(param_temp)
print(param_curr_lim)
print(param_delay)
print(param_multidelay)
print(param_voltrange)
print(param_currentrange)


class Application(tk.Tk):

    def __init__(self):
        # Declaration of self is required for all object variables and object methods, because of python.

        super().__init__()
        

        self.frame_ic = tk.LabelFrame(self.sub_frame, text = "INSTRUMENT CONTROL")
        self.frame_ic.grid(row = 0, column = 1)
        
        # Buttons for starting and stopping
        self.start_run = tk.Button (self.frame_ic, text = 'START RUN', command =lambda:(self.start()))
        self.start_run.grid(row = 3, column = 0, sticky = 'w')
    
    def start(self):
        print("Button clicked!")
        

if __name__ == "__main__":
    app = Application()  # Create the tk object (the program itself)
    app.mainloop() # Run the mainloop() as required. 
        