#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 27 15:06:15 2023

@author: ebeem

2023/04/27
- read parameters from parameters.csv
- add auto_click() and self.after(1000, self.auto_click) to autorun the "START RUN" button after x seconds

"""


import tkinter as tk
import pyvisa
import tkinter.filedialog
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, 
NavigationToolbar2Tk)
import numpy as np 
from time import sleep
import pandas as pd
import seaborn as sns
import queue
import thread_wrapper_2450 as m_thread
import csv



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


#------------------------------


# To add new user to the 'Operator Name' dropdown menu:
#   1.) Press 'Ctrl' + 'F'
#   2.) Search "usernames"
#   3.) Look for the line which defines 'self.usernames'
#   4.) Add new name to the list (within the '[]' brackets) by entering a comma and then "<Name of new user>"

class Application(tk.Tk):

    def __init__(self):
        # Declaration of self is required for all object variables and object methods, because of python.

        super().__init__()
        
        # Define the object variables. These variables will be shared (i.e. 'global') within the defined objects.
        # Functions in objects have full access to the object variables, so we can call a function, and return its output to one of these variables.
        # That way, data collected from the scan can be transferred to another function (the plot())

        # Since the canvas and matplotlib fig (and axes) will remain the same, I have declared them as object variables instead. 
        # Likewise, the connection to the smu is made in this py file, but the start() requires it as well, so I declared it as an object variable.

        self.dict_data = None
        self.address_list = None
        self.directory = None
        self.fig = None
        self.smu = None
        self.rm = None
        self.multidelay = None
        self.canvas = None
        self.plot1 = None
        self.graph_container = None
        self.should_stop = 0
        self.dataqueue = queue.Queue()
        self.params = None
        self.update_dataqueue = None
        self.i = None
        self.is_done = 0
        self.stop_thread_queue = queue.Queue()
        
        #autoclick check function auto_click(self)
        self.after(1000, self.auto_click) #1000 ms
        
        ####################################### LAYOUT ####################################################

        self.title('Voltage Sweep - Keithley 2450')

        # The main frame contains the main canvas and the vertical scrollbar
        self.main_frame = tk.Frame(self)
        self.main_frame.pack(side = 'top', fill = 'both', expand = True)

        # Created a specific frame underneath the main frame to place the horizontal scrollbar.
        self.xscrollbar_frame = tk.Frame(self)
        self.xscrollbar_frame.pack(side = 'bottom', fill = 'both', expand = True, anchor = 'n')

        # The main canvas contains the sub frame. 604
        self.main_canvas = tk.Canvas(self.main_frame, height = 800, width = 1200)
        self.main_canvas.pack(side= 'left', fill='both', anchor = 'n', expand=True)

        # Initializing scrollbars
        y_scrollbar = tk.Scrollbar(self.main_frame, orient='vertical', command=self.main_canvas.yview)
        y_scrollbar.pack(side='right',fill='y', anchor = 'ne')
        x_scrollbar = tk.Scrollbar(self.xscrollbar_frame, orient='horizontal', command=self.main_canvas.xview)
        x_scrollbar.pack(side='top', anchor='n', fill='x')

        # Configuring the scrollbars
        self.main_canvas.configure(yscrollcommand=y_scrollbar.set)
        self.main_canvas.configure(xscrollcommand=x_scrollbar.set)
        self.main_canvas.bind("<Configure>", lambda e: self.main_canvas.config(scrollregion= self.main_canvas.bbox('all'))) 

        # The sub frame overlaps the main canvas to. This is the parent container for all the widgets. This was necessary for the scroll function to work when the window is resized. 
        self.sub_frame = tk.Frame (self.main_canvas)
        self.main_canvas.create_window ((0,0), window = self.sub_frame, anchor = 'nw') 


        # Input Parameters frame
        self.frame_in_par = tk.LabelFrame(self.sub_frame, text = "INPUT PARAMETERS")
        self.frame_in_par.grid(rowspan = 3)

        # Operator Name
        self.op_label = tk.Label (self.frame_in_par, text = 'Operator Name:')
        self.op_label.grid(sticky = 'w')
        self.op_name = tk.StringVar(self, 'Emha')
        
        # Get usernames
        operatordf = pd.read_excel("OperatorList.xlsx",header=None)
        operatorlist = operatordf.iloc[:][0].tolist()
        operatorlist.sort()
        print("Users = " + str(operatorlist))
        
        self.usernames = operatorlist
        
        self.name_drop = tk.OptionMenu (self.frame_in_par, self.op_name, *self.usernames)
        self.name_drop.grid()

        # Cell Type
        self.type_select = tk.Label (self.frame_in_par, text = "Select type:")
        self.type_select.grid(row=2, sticky = 'w')
        self.celltype = tk.StringVar()
        self.celltype.set('Carbon small')
        self.type_option_1 = tk.Radiobutton (self.frame_in_par, text = 'Spin Coated', variable = self.celltype, value = 'Spin Coated',tristatevalue='x')
        self.type_option_1.grid(row = 3, sticky = 'w')
        self.type_option_2 = tk.Radiobutton (self.frame_in_par, text = 'Slot-die small', variable = self.celltype, value = 'Slot-die small',tristatevalue='x')
        self.type_option_2.grid(row = 3, column = 1, sticky = 'w')
        self.type_option_3 = tk.Radiobutton (self.frame_in_par, text = 'Slot-die large', variable = self.celltype, value = 'Slot-die large',tristatevalue='x')
        self.type_option_3.grid(row = 4, sticky = 'w')
        self.type_option_4 = tk.Radiobutton (self.frame_in_par, text = 'Carbon small', variable = self.celltype, value = 'Carbon small',tristatevalue='x')
        self.type_option_4.grid(row = 4, column = 1, sticky = 'w')
        self.type_option_5 = tk.Radiobutton (self.frame_in_par, text = 'Carbon large', variable = self.celltype, value = 'Carbon large',tristatevalue='x')
        self.type_option_5.grid(row = 5, sticky = 'w')

        self.celltype.trace('w',self.showCellType)

        # Measurement Type
        self.measurement_type_select = tk.Label (self.frame_in_par, text = 'Select measurement type:')
        self.measurement_type_select.grid(row = 7, sticky = 'w')
        self.measurement_type = tk.StringVar()
        self.measurement_type.set ('Normal')
        self.measurement_type_option_1 = tk.Radiobutton (self.frame_in_par, text = 'Normal', variable = self.measurement_type, value = 'Normal',tristatevalue='x')
        self.measurement_type_option_1.grid(row = 8, sticky = 'w')
        self.measurement_type_option_2 = tk.Radiobutton (self.frame_in_par, text = 'Thermal Stability', variable = self.measurement_type, value = 'Thermal Stability',tristatevalue='x')
        self.measurement_type_option_2.grid(row = 9, sticky = 'w')
        self.measurement_type_option_3 = tk.Radiobutton (self.frame_in_par, text = 'Intensity J-V scans', variable = self.measurement_type, value = 'Intensity J-V scans',tristatevalue='x')
        self.measurement_type_option_3.grid(row = 10, sticky = 'w')

        self.measurement_type.trace('w',self.showMeasurementType)

        # Sample_ID
        self.sample_id_label = tk.Label (self.frame_in_par, text = 'Sample ID:')
        self.sample_id_label.grid(row = 12, sticky = 'w')
        self.sample_id = tk.StringVar(self,"HT-1")
        self.sample_id_box = tk.Entry (self.frame_in_par, textvariable = self.sample_id)
        self.sample_id_box.grid (row = 12, column = 1, sticky = 'w')

        # Min Voltage
        self.min_volt_label = tk.Label (self.frame_in_par, text = 'Min Voltage (V):')
        self.min_volt_label.grid(row = 13, sticky = 'w')
        self.min_volt = tk.DoubleVar(self,param_min_volt)
        self.min_volt_box = tk.Entry (self.frame_in_par, textvariable = self.min_volt)
        self.min_volt_box.grid (row = 13, column = 1, sticky = 'w')

        # Max Voltage
        self.max_volt_label = tk.Label (self.frame_in_par, text = 'Max Voltage (V):')
        self.max_volt_label.grid(row = 14, sticky = 'w')
        self.max_volt = tk.DoubleVar(self,param_max_volt)
        self.max_volt_box = tk.Entry (self.frame_in_par, textvariable = self.max_volt)
        self.max_volt_box.grid (row = 14, column = 1, sticky = 'w')

        # Number of steps
        self.steps_no_label = tk.Label (self.frame_in_par, text = 'Number of steps:')
        self.steps_no_label.grid(row = 15, sticky = 'w')
        self.steps_no = tk.IntVar(self,param_steps_no)
        self.steps_no_box = tk.Entry (self.frame_in_par, textvariable = self.steps_no)
        self.steps_no_box.grid (row = 15, column = 1, sticky = 'w')

        # Scan direction
        self.scan_dir_select = tk.Label (self.frame_in_par, text = 'Scan direction/ Pattern:' )
        self.scan_dir_select.grid(row = 16, sticky = 'w')
        self.scan_dir = tk.StringVar()
        self.scan_dir.set('p')
        self.scan_dir_option_1 = tk.Radiobutton (self.frame_in_par, text = 'Forward', variable = self.scan_dir, value = 'f',tristatevalue='x')
        self.scan_dir_option_1.grid(row = 17, sticky = 'w')
        self.scan_dir_option_2 = tk.Radiobutton (self.frame_in_par, text = 'Reverse', variable = self.scan_dir, value = 'r',tristatevalue='x')
        self.scan_dir_option_2.grid(row = 18, sticky = 'w')
        self.scan_dir_option_3 = tk.Radiobutton (self.frame_in_par, text = 'Pattern', variable = self.scan_dir, value = 'p',tristatevalue='x')
        self.scan_dir_option_3.grid(row = 19, sticky = 'w')
        self.pattern_entry = tk.StringVar(self,"frfrfr")

        # Trace keeps track of the radio button selected. Try this out and check the logs.
        self.scan_dir.trace('w',self.configure_pattern)


        self.pattern_box = tk.Entry (self.frame_in_par, textvariable = self.pattern_entry)
        self.pattern_box.grid (row = 19, column = 1, sticky = 'w')
        self.pattern_box.config(state='disabled')


        # Cell Area
        self.cell_area_label = tk.Label (self.frame_in_par, text = 'Cell Area (sq. cm):')
        self.cell_area_label.grid(row = 21, sticky = 'w')
        self.cell_area = tk.DoubleVar(self,param_cell_area)
        self.cell_area_box = tk.Entry (self.frame_in_par, textvariable = self.cell_area)
        self.cell_area_box.grid (row = 21, column = 1, sticky = 'w')

        # Scan Rate
        self.scan_rate_label = tk.Label (self.frame_in_par, text = 'Scan Rate (mV/sec):')
        self.scan_rate_label.grid(row = 23, sticky = 'w')
        self.scan_rate = tk.DoubleVar(self,param_scan_rate)
        self.scan_rate_box = tk.Entry (self.frame_in_par, textvariable = self.scan_rate)
        self.scan_rate_box.grid (row = 23, column = 1, sticky = 'w')

        # Irradiance
        self.irr_label = tk.Label (self.frame_in_par, text = 'Irradiance (Suns):')
        self.irr_label.grid(row = 25, sticky = 'w')
        self.irr = tk.DoubleVar(self, param_irr)
        self.irr_box = tk.Entry (self.frame_in_par, textvariable = self.irr)
        self.irr_box.grid (row = 25, column = 1, sticky = 'w')

        # Temperature
        self.temp_label = tk.Label (self.frame_in_par, text = 'Temperature (C):')
        self.temp_label.grid(row = 27, sticky = 'w')
        self.temp = tk.DoubleVar(self, param_temp)
        self.temp_box = tk.Entry (self.frame_in_par, textvariable = self.temp)
        self.temp_box.grid (row = 27, column = 1, sticky = 'w')

        # Current compliance
        self.curr_lim_label = tk.Label (self.frame_in_par, text = 'Current Limit (mA):')
        self.curr_lim_label.grid(row = 29, sticky = 'w')
        self.curr_lim = tk.DoubleVar(self,param_curr_lim)
        self.curr_lim_box = tk.Entry (self.frame_in_par, textvariable = self.curr_lim)
        self.curr_lim_box.grid (row = 29, column = 1, sticky = 'w')

        # NPLC DELAY 
        self.delay_label = tk.Label (self.frame_in_par, text = 'NPLC:')
        self.delay_label.grid(row = 31, sticky = 'w')
        self.delay = tk.DoubleVar(self,param_delay)
        self.delay_box = tk.Entry (self.frame_in_par, textvariable = self.delay)
        self.delay_box.grid (row = 31, column = 1, sticky = 'w')

        # DELAY PER SCAN (FOR MULTIPLE SCANS) 
        self.multidelay_label = tk.Label (self.frame_in_par, text = 'Delay per scan (s):')
        self.multidelay_label.grid(row = 32, sticky = 'w')
        self.multidelay = tk.DoubleVar(self,param_multidelay)
        self.multidelay_box = tk.Entry (self.frame_in_par, textvariable = self.multidelay)
        self.multidelay_box.grid (row = 32, column = 1, sticky = 'w')
        
        # VOLTAGE RANGE SETTING
        self.voltrange_label = tk.Label (self.frame_in_par, text = 'Voltage Range (V)')
        self.voltrange_label.grid(row = 33, sticky = 'w')
        self.voltrange = tk.DoubleVar(self,param_voltrange)
        self.voltrange_box = tk.Entry (self.frame_in_par, textvariable = self.voltrange)
        self.voltrange_box.grid (row = 33, column = 1, sticky = 'w')    


        # CURRENT RANGE SETTING
        self.currentrange_label = tk.Label (self.frame_in_par, text = 'Current Range (A)')
        self.currentrange_label.grid(row = 34, sticky = 'w')
        self.currentrange = tk.DoubleVar(self,param_currentrange)
        self.currentrange_box = tk.Entry (self.frame_in_par, textvariable = self.currentrange)
        self.currentrange_box.grid (row = 34, column = 1, sticky = 'w')    



        # Directory. I changed it to a button to choose the directory. 
        # Auto-saving of data is preferred, and it saves time with the whole scanning process
        # For the same reason in the Keithley py file, the filename is automatically created. 
        self.savedir = tk.Button (self.frame_in_par, text = 'Choose Save Location', command = lambda: self.getDirectory())
        self.savedir.grid(row = 35, sticky = 'w')
        self.directory_fill = tk.StringVar()
        self.directory_box = tk.Entry (self.frame_in_par, textvariable = self.directory_fill)
        self.directory_box.grid (row = 35, column = 1, sticky = 'w')
        self.directory_fill.trace('w',self.directory_fill_setter)

        #self.clear_button = Button (self.frame_jv, text = 'CLEAR', command = lambda:self.clear_canvas())
        #self.clear_button.grid(row = 0, column = 0, sticky = 'e')

        # Instrument Control frame
        # Need to fix in automated measurement
        self.frame_ic = tk.LabelFrame(self.sub_frame, text = "INSTRUMENT CONTROL")
        self.frame_ic.grid(row = 0, column = 1)
        
        # PyVisa set-up.
        # I chose to make the ResourceManager an object variable as well, so that the actual connection,
        # which is done by another function (selectResource()), need not declare a new ResourceManager just to make the connection.
        # This code will fail if no devices are detected. 
        
        self.rm = pyvisa.ResourceManager()
        self.address_list = list(self.rm.list_resources()) # list_resources() gives a tuple, I converted it to a list.
        print("Address list: " + str(self.address_list))
        
        self.address_select_label = tk.Label (self.frame_ic, text = 'Devices:')
        self.address_select_label.grid(sticky = 'w')

        # selected_resc will change when an option in the OptionMenu is clicked. This click is tracked by the trace function below.
        self.selected_resc = tk.StringVar()
        self.address_drop = tk.OptionMenu (self.frame_ic, self.selected_resc, *self.address_list)
        self.address_drop.grid(row = 0, column = 1, sticky = 'w')
        
        self.selected_resc.trace('w',self.selectResource)  
        

        # Check status button
        self.check_status = tk.Button (self.frame_ic, text = 'Show Status', command = lambda: self.show_status())
        self.check_status.grid(row = 1, sticky = 'w')

        self.timeout = tk.DoubleVar(self,30000)
        self.timeout_label = tk.Label (self.frame_ic, text = 'Timeout (sec):').grid(row = 2, sticky = 'w')
        self.timeout_box = tk.Entry (self.frame_ic, textvariable = self.timeout)
        self.timeout_box.grid (row = 2, column = 1, sticky = 'w')


        # Buttons for starting and stopping
        self.start_run = tk.Button (self.frame_ic, text = 'START RUN', command =lambda:(self.start()))
        self.start_run.grid(row = 3, column = 0, sticky = 'w')

        self.stop_run = tk.Button (self.frame_ic, text = 'STOP RUN',command = lambda:(self.stop()))
        self.stop_run.grid(row = 3, column = 2, sticky = 'w')

        #self.save_data = Button (self.frame_ic, text = 'SAVE DATA')
        #self.save_data.grid(row = 3, column = 2, sticky = 'w')
    
        
        # JV Curve frame 
        self.frame_jv = tk.LabelFrame(self.sub_frame, text = "JV CURVE")
        self.frame_jv.grid(row = 1, column = 1, rowspan = 2)
        self.canvas = self.clear_canvas()

        # Output Log frame
        self.out_log = tk.LabelFrame(self.sub_frame, text = "OUTPUT LOG")
        self.out_log.grid (row = 0, column = 2, rowspan = 3, sticky = 'n' )
        
        # If you want to change the width of log window, edit the width attribute of the following canvas.
        # Then go to line 431 and change the width of the textbox to match that of the canvas. You can see the width of the textbox
        # by giving it a 'bg' colour
        # Accordingly, change the width of the tkinter window from line 53
        self.out_canvas = tk.Canvas (self.out_log, height = 580, width = 300, bg = 'white').grid (row = 0, column = 0, sticky ='n')

        

        # Removed the ones below.
        # When we scan, we expect that the graphs show immediately, and on starting the next scan, the screen is cleared and 
        # immediately ready for the next scan.
        # This is to make this program as similar as the one we are currently using. 

        #self.clear_button = tk.Button (self.frame_jv, text = 'CLEAR', command = lambda:self.clear_canvas())
        #self.clear_button.grid(row = 0, column = 0, sticky = 'e')
        #self.plot_button = tk.Button (self.frame_jv, text = 'PLOT', command = lambda:self.plot())
        #self.plot_button.grid(row = 0, column = 0)




    ######################################################################  FUNCTIONS  ###################################################################

    def getDirectory(self,*args):

        """
        Gets the directory path for the exporting of files. 
        Called by the savedir button.
        """

        self.directory = tkinter.filedialog.askdirectory()
        print("Selected directory is: " + str(self.directory))
        self.directory_fill.set(self.directory)

    def directory_fill_setter(self,*args):

        """
        A pointless function merely to fill the box beside the savedir button,
        so that people may confirm that the path they chose is correct.
        (Don't we all doubt the paths we choose)
        """

        self.directory_fill.set(self.directory)


    def showMeasurementType(self, *args):
        """
        A pointless function meant to log the changes to the measurement type, to check
        if the RadioButtons are working. Left here for future debugging.
        """
        mea_type = self.measurement_type.get()
        
        print('Measured Type is = ' + mea_type)

    def showCellType(self, *args):

        """
        A pointless function meant to log the changes to the cell type, to check
        if the RadioButtons are working. Left here for future debugging.
        """

        typecell = self.celltype.get()
        print('Cell type is ' + typecell)

    def selectResource(self,*args):

        """
        Function to select the instrument to use once an option in OptionMenu is clicked.
        """

        rsc = self.selected_resc.get()
        print("Selected resource: " + str(rsc))
        

        # Make connection here
        self.smu = self.rm.open_resource(rsc)
        print("Connection to " + str(rsc) + " successful.")


    def configure_pattern(self,*args):
        
        """
        Function to set the text in the textbox for the pattern scan, because the text in the box is the variable that will be sent
        to the start() function eventually.
        """
        
        collected_pattern = self.scan_dir.get()
        print("Collected pattern is: " + collected_pattern)

        if collected_pattern == 'f':
            pattern = 'f'
            print("Reached 83")
            self.pattern_entry.set('f')
            self.pattern_box.config(state='disabled')
            #pattern_box = Entry (frame_in_par, textvariable = pattern_entry)
            #pattern_box.grid (row = 19, column = 1, sticky = 'w')
            a = 1

        elif collected_pattern == 'r':
            pattern = 'r'
            print("Reached 88")
            self.pattern_entry.set('r')
            self.pattern_box.config(state='disabled')
            #pattern_box = Entry (frame_in_par, textvariable = pattern_entry)
            #pattern_box.grid (row = 19, column = 1, sticky = 'w')
            a = 2
        else:
            self.pattern_entry.set("frfrfr")
            self.pattern_box.config(state='normal')
            #pattern_box = Entry (frame_in_par, textvariable = pattern_entry)
            #pattern_box.grid (row = 19, column = 1, sticky = 'w')
            a = 3
        
        return a
        

    def showTimeOut(self,*args):

        """
        A pointless function meant to log the changes to the TimeOut box, to check
        if the RadioButtons are working. Left here for future debugging.
        """

        tout = self.timeout.get()
        print('Timeout set to '+str(tout))


    def show_status(self):

        """
        Function to show the connection to the VISA resource.
        """

        tk.Label (self.frame_ic, text = f"Connected to: {self.smu}").grid(row = 1, column = 1)



    def start(self):

        """
        Starts the scanning process. Calls the plot() as well, to plot the data immediately after receiving the data from the Keithley.

        Here, the patterning will be handled instead. The idea is to attempt to plot and export the files with each scan, rather than to do all at once.
        Two functions will be required here.
        1) Running the JV code
            1.1 Running the scan
            1.2 Calculating the parameters
            1.3 Exporting the csv file
        2) Plotting the graph


        """


        self.clear_canvas()
        self.should_stop = 0
        self.is_done = 0
        self.dataqueue = queue.Queue()
        self.stop_thread_queue = queue.Queue()


        # Disable button
        self.start_run.config(state="disabled")

        print("Pattern is " + str(self.pattern_box.get()))

        # Created text widget for output log
        
        self.out_txt = tk.Text(self.out_log, width = '35', height = '36')
        self.out_txt.grid(row = 0, column = 0, sticky = 'n')

        # CHECK INPUTS
        hasError = self.check_inputs(self.out_txt)
        if hasError == True:
            self.should_stop = 1
            self.start_run.config(state="active")
            return
        

        if self.should_stop == 1:
            print("STOPPED in start(). Breaking from loop.")
            self.is_done = 1
            self.start_run.config(state="active")
            return

        save_params = [self.directory_box.get(),\
                        self.op_name.get(),\
                        self.sample_id_box.get(),\
                        self.measurement_type.get(),\
                        self.celltype.get(),\
                        self.temp_box.get() \
        ]
        

        # UPDATE 2023-01-05: ADDED THREADING FUNCTIONALITY
        
        self.runner = m_thread.Runner(self.dataqueue, self.smu, \
                                            int(self.steps_no_box.get()), \
                                            self.pattern_box.get(), \
                                            float(self.delay_box.get()), \
                                            float(self.min_volt_box.get()), \
                                            float(self.max_volt_box.get()), \
                                            float(self.scan_rate_box.get()),\
                                            float(self.cell_area_box.get()),\
                                            float(self.irr_box.get()),\
                                            float(self.curr_lim_box.get()),\
                                            save_params,\
                                            float(self.timeout_box.get()),\
                                            float(self.multidelay_box.get()),\
                                            self.stop_thread_queue,\
                                            float(self.voltrange_box.get()),\
                                            float(self.currentrange_box.get()))

        if self.should_stop == 1:
            print("STOPPED in start(). Breaking from loop.")
            self.start_run.config(state="active")
            return
            
        self.runner.start()

        if self.should_stop == 1:
            print("STOPPED in start(). Breaking from loop. Nothing will be plotted.")
            self.stop_thread_queue.put(1)
            self.runner.join()
            self.start_run.config(state="active")
            return            

        self.process_queue()


        if self.should_stop == 1:
            print("STOPPED in start(). Breaking from loop.")
            self.stop_thread_queue.put(1)
            self.runner.join()
            self.start_run.config(state="active")
            return

       


    def stop(self):
        
        """
        Method to call the stop process from the Keithley scanner py file.

        """

        self.should_stop = 1
        self.stop_thread_queue.put(1)

        self.runner.join()

        self.start_run.config(state='active')
        self.out_txt.insert('end', "STOPPED. OPERATION COMPLETE.")
        self.out_txt.insert('end', "\n")

        self.dict_data = None

        self.directory = None
        self.fig = None



        self.dataqueue = queue.Queue()
        self.params = None
        self.update_dataqueue = None

        self.stop_thread_queue = queue.Queue()
        print("STOPPED SIGNAL RECEIVED.")



    def process_queue(self):

        """
        UPDATE 2023-01-05: ADDED THREADING FUNCTIONALITY

        Perodically scans the queue for new data; when received, then attempts to send the data back for plotting.
        """

        if self.should_stop == 1:
            print("QUEUE STOPPED.")
            return

        if self.is_done == 1:
            print("OPERATION COMPLETE.")
            self.start_run.config(state="active")
            self.out_txt.insert('end', "OPERATION COMPLETE.")
            self.out_txt.insert('end', "\n")
            return

        try:
            self.params = self.dataqueue.get_nowait()
            
            # Params will contain all information that needs to be transferred to GUI.

            test_output = self.params

            if self.should_stop == 1:
                print("STOPPED in process_queue(). Breaking from loop. Nothing will be plotted.")                
                self.stop_thread_queue.put(1)
                self.runner.join()
                self.start_run.config(state="active")
                return



            # Receive the data and set it as an object variable.
            self.dict_data = test_output["Dictionary"]

            # This is sent to the plot() function to be the label for that line, and will appear in the legend.
            repetition = "Scan " + str(test_output["Loop"]+1)

            print("HERE1")

            #temp_df = pd.DataFrame.from_dict(self.dict_data)

            plottingdict = {'Potential (V)': self.dict_data['Potential (V)'],'Current Density (mA/cm2)':self.dict_data['Current Density (mA/cm2)']}
            temp_df = pd.DataFrame.from_dict(plottingdict)   
            print("HERE2")
            print(temp_df)
            
            # Calls the plot function to plot it immediately.
            self.plot(temp_df,self.canvas,repetition,int(test_output["Loop"]),self.pattern_box.get()[int(test_output["Loop"])])

            # Calls function to display the output parameters in the log
            #self.display_log(test_output, self.out_txt, i)

            if self.should_stop == 1:
                print("STOPPED in process_queue(). Breaking from loop.")
                self.stop_thread_queue.put(1)
                self.runner.join()
                self.start_run.config(state="active")
                return 

            print(test_output["Loop"])
            print()

            if int(test_output["Loop"])+1 == (len(self.pattern_box.get())):
                self.is_done = 1

            self.graph_container.after(100,self.process_queue)


            
        except queue.Empty:
            
            self.graph_container.after(100,self.process_queue)
            print("Waiting for Data.")
            
            # Recursion used. Keep calling until something is returned.

        if self.should_stop == 1:
            print("QUEUE STOPPED.")
            self.stop_thread_queue.put(1)
            self.runner.join()
            return
            

    def check_inputs(self,out_txt):

        """
        Checks the entries, and if it is wrong, then show an error.
        """

        # Check types first.

        error_in_inputs = False

        try:
            int(self.steps_no_box.get())
        except:
            out_txt.insert('end',"Number of Steps must be an integer.")
            out_txt.insert('end',"\n")
            self.should_stop = 1
            error_in_inputs = True
        try:    
            float(self.delay_box.get())
        except:
            out_txt.insert('end',"NPLC must be an float in seconds")
            out_txt.insert('end',"\n")
            self.should_stop = 1
            error_in_inputs = True

        try:
            float(self.min_volt_box.get())
        except:
            out_txt.insert('end',"Min Voltage must be a floating point value.")
            out_txt.insert('end',"\n")
            self.should_stop = 1
            self.should_stop = 1
            error_in_inputs = True
            

        try:
            float(self.max_volt_box.get())
        except:
            out_txt.insert('end',"Max Voltage must be a floating point value.")
            out_txt.insert('end',"\n")
            self.should_stop = 1
            error_in_inputs = True


        try:
            float(self.scan_rate_box.get())
        except: 
            out_txt.insert('end',"Scan Rate must be a floating point value.")
            out_txt.insert('end',"\n")
            self.should_stop = 1 
            error_in_inputs = True      

        try:
            float(self.cell_area_box.get())
        except:
            out_txt.insert('end',"Cell Area must be a floating point value.")
            out_txt.insert('end',"\n")
            self.should_stop = 1
            error_in_inputs = True

        try:
            float(self.irr_box.get())
        except:
            out_txt.insert('end',"Irradiance must be a floating point value.")
            out_txt.insert('end',"\n")
            self.should_stop = 1
            error_in_inputs = True

        try:
            float(self.curr_lim_box.get())
        except:
            out_txt.insert('end',"Current Limit must be a floating point value.")
            out_txt.insert('end',"\n")
            self.should_stop = 1
            error_in_inputs = True

        try:
            float(self.timeout_box.get())
        except:
            out_txt.insert('end',"Timeout must be a floating point value.")
            out_txt.insert('end',"\n")
            self.should_stop = 1
            error_in_inputs = True

        try:
            float(self.multidelay_box.get())
        except:
            out_txt.insert('end',"Delay between scans must be a floating point value.")
            out_txt.insert('end',"\n")
            self.should_stop = 1
            error_in_inputs = True

        if error_in_inputs == True:
            return error_in_inputs








        # Check signs. All should be positive.

        if int(self.steps_no_box.get()) <= 0:
            out_txt.insert('end',"Number of Steps must be larger than 0.")
            out_txt.insert('end',"\n")
            self.should_stop = 1
            error_in_inputs = True         

        if  float(self.delay_box.get()) <= 0:
            out_txt.insert('end',"NPLC must be larger than 0.")
            out_txt.insert('end',"\n")
            self.should_stop = 1
            error_in_inputs = True   

        if float(self.min_volt_box.get()) > float(self.max_volt_box.get()):
            out_txt.insert('end',"Min Voltage cannot be larger than Max Voltage. Use the 'Forward' or 'Reverse' radiobuttons to control the direction of sweep.")
            out_txt.insert('end',"\n")
            self.should_stop = 1
            error_in_inputs = True           

        if float(self.scan_rate_box.get()) <= 0:
            out_txt.insert('end',"Scan Rate must be larger than 0.")
            out_txt.insert('end',"\n")
            self.should_stop = 1 
            error_in_inputs = True                  

        if float(self.cell_area_box.get()) <= 0:
            out_txt.insert('end',"Cell Area must be must be larger than 0.")
            out_txt.insert('end',"\n")
            self.should_stop = 1
            error_in_inputs = True


        if float(self.irr_box.get()) <= 0:
            out_txt.insert('end',"Irradiance must be a floating point value.")
            out_txt.insert('end',"\n")
            self.should_stop = 1
            error_in_inputs = True

        if float(self.curr_lim_box.get()) <= 0:
            out_txt.insert('end',"Current Limit must be larger than 0.")
            out_txt.insert('end',"\n")
            self.should_stop = 1
            error_in_inputs = True


        if float(self.timeout_box.get()) <= 0:
            out_txt.insert('end',"Timeout must be larger than 0.")
            out_txt.insert('end',"\n")
            self.should_stop = 1
            error_in_inputs = True

        if float(self.multidelay_box.get()) < 0:
            out_txt.insert('end',"Delay between scans must be larger than 0.")
            out_txt.insert('end',"\n")
            self.should_stop = 1
            error_in_inputs = True
        
        if error_in_inputs == True:
            return error_in_inputs





        # Check pattern string

        for ch in self.pattern_box.get():

            if ch != 'r':
                if ch != 'f':
                    out_txt.insert('end',"Pattern should only contain 'r','f', or combinations of 'r' and 'f' (e.g. 'rfrfrf','rrfff',etc.). Check the pattern entry.")
                    out_txt.insert('end',"\n")
                    self.should_stop = 1
                    error_in_inputs = True
                    return error_in_inputs
                else:
                    continue


        return error_in_inputs



        



    def clear_canvas (self):
        
        """
        Function to reset the matplotlib canvas.
        """


        self.graph_container = tk.Canvas (self.frame_jv, height = 400, width = 600, bg = 'white')
        self.graph_container.grid(row = 1, column = 0)
        self.fig = Figure(figsize = (6, 4), dpi = 100)
        self.plot1 = self.fig.add_subplot(111)
        self.plot1.set_xlabel('Voltage (V)')
        self.plot1.set_ylabel('Current Density (mA/cm2)')
        self.plot1.set_yticks([0], minor = True)
        self.plot1.yaxis.grid(True)
        self.plot1.xaxis.grid(True)
        self.canvas = FigureCanvasTkAgg(self.fig, master = self.frame_jv)  
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row = 1, column = 0)





   


    def plot(self,data,canvas,rep_legend,rep_no,direction):
    
        # the figure that will contain the plot

        """
        Function to plot the data. This will be called from the start(). That way, a new plot can be made each time the Keithley sends 
        over a set of data from each scan. 
        """

        # Since most of the plotting variables have been declared earlier in the clear.canvas() function, and these variables are object variables,
        # no need to call them here. 
        
        self.plot1.plot(data['Potential (V)'],data['Current Density (mA/cm2)'],linewidth=3,label=rep_legend)
        self.plot1.legend(loc="lower left")

    

        self.fig.canvas.draw()
    
        # placing the canvas on the Tkinter window
        self.canvas.get_tk_widget().grid(row = 1, column = 0)

        # This is essential, for ensuring that the plot shows right after data is received. Without this update(), for multiple scans, the plot will
        # only appear after all scans are done. With update(), the canvas is updated with each iteration of the loop in start().

        self.display_log(self.dict_data, self.out_txt, rep_no,direction)

        self.update()
    



    def display_log(self, output_params, textbox, scan_rep,direction):
            """
            Function to display parameters in the output log. The log will update automatically with each scan.
            """
            textbox.insert('end', f" Scan {scan_rep+1}:\n")
            textbox.insert('end', "__________\n")
            textbox.insert('end', f"    Voc: {np.round(output_params['Voc (V)'], 2)} V\n")
            textbox.insert('end', f"    Isc: {np.round(output_params['Isc (mA)'], 2)} mA\n")
            textbox.insert('end', f"    Jsc: {np.round(output_params['Jsc (mA/cm2)'], 2)} mA/cm2\n")
            textbox.insert('end', f"    Imax: {np.round(output_params['Imax (mA)'], 2)} mA\n")
            textbox.insert('end', f"    Vmax: {np.round(output_params['Vmax (V)'], 2)} V\n")
            textbox.insert('end', f"    Pmax: {np.round(output_params['Pmax (mW/cm2)'], 2)} mW/cm2\n")
            textbox.insert('end', f"    FF: {np.round(output_params['FF (%)'], 2)}%\n")
            textbox.insert('end', f"    PCE: {np.round(output_params['PCE (%)'], 2)}%\n")
            textbox.insert('end', f"    Rseries: {np.round(output_params['Rseries (ohm)'], 2)} ohm\n")
            textbox.insert('end', f"    Rshunt: {np.round(output_params['Rshunt (ohm)'], 2)} ohm\n")
            textbox.insert('end', f"    Direction: {direction}\n")
            textbox.insert('end', "\n")
            textbox.insert('end', "\n")
            textbox.see("end")

    
    #make the start_run button autoclicked
    def auto_click(self):
        self.start_run.invoke()
    

           

        

if __name__ == "__main__":
    app = Application()  # Create the tk object (the program itself)
    app.mainloop() # Run the mainloop() as required. 
