#!/usr/bin/env python
# coding: utf-8

#  Keithley 2450 SMU TFT Characterization

#  Libraries

import numpy as np
import pyvisa
import csv
import datetime 
from scipy.stats import linregress
import pandas as pd
import csv
from time import sleep

#def get_resources():
#    rm = pyvisa.ResourceManager()
#    address = rm.list_resources()
#    resources = (rm, address)
#    return resources

# CHANGE RANGE VALUES HERE. IN VOLTS AND AMPS


def get_target_volt(start_volt):
    """
    Return the target volt. Check validity of the input.
    :param start_volt: The starting point of the voltage sweep. 
    """
    while True:
        # Keeps asking the user for the valid target volt until they correclty provide one.
        target_volt = float (input ('Set the target voltage (in Volts) for sweep: '))
        return target_volt
        
def get_step_volt(start_volt, target_volt):
    """
    Return the step volt. It is the magnitude of steps in which the sweep will occur. Check validity of the input.
    :param start_volt: The starting point of the voltage sweep. 
    :param target_volt: The end point of the voltage sweep. 
    """
    while True:

        step_volt = float (input ('Set the size of steps (in Volts) of sweep: ')) 
        
        if step_volt <= target_volt - start_volt:
            return step_volt
        else:
            print ('INVALID INPUT: Step must be less than or equal to the difference between starting and target voltage')

def get_integration_time ():
    """
    Return integration time. Check if input is within the range suggested by Keithley2600 manual.
    """
    while True:
        integration_time = float (input('Set the integration time for each data point (in PLC): '))
        if integration_time >= 0.001 and integration_time <= 25:
            return integration_time
        else: 
            print('INVALID INPUT: The integration time must be between 0.001 and 25 PLC.')

def get_sweep_type():
    """
    Return boolean for sweep type based on the character input.
    """
    while True:
        sweep_type = input ('Choose between pulsed and continuous sweep (enter P or C): ')
        if sweep_type == 'P' or sweep_type == 'p':
            return True  
        elif sweep_type == 'C' or sweep_type == 'c':
            return False
        else:
            print ('INVALID INPUT')

def sweep_operation(smu_id, \
                    steps_no, \
                    pattern, \
                    nplc, \
                    min, \
                    max,\
                    scan_rate, \
                    loop_no,\
                    cell_area,\
                    irradiance,\
                    current_limit,\
                    save_params,\
                    timeout,\
                    volt_range,\
                    current_range):

    smu_id.timeout = timeout

    # This is for inclusion in the filename later - a file-naming convention we use.
    pce = 0
    
    #smu_id.write("errorqueue.clear()")
    smu_id.write("*RST") # EDITED 2023-01-05

    print("Scan rate is: " + str(scan_rate))
    # Set source function to DC volts
    smu_id.write (":SOUR:FUNC VOLT")  # EDITED 2023-01-05
  
    """
    if start > end:
        max = start
        min = end
    else:
        max = end
        min = start
    """
    

    
    # calculate time per voltage
    scan_interval_time = (((max *1.0000000000 - min * 1.0000000000)/(steps_no - 1)) / (scan_rate/1000))
    
    # Subtract NPLC delay
    scan_interval_time = scan_interval_time - (nplc/50)
    #log.info("Wait time for voltage = %f" % scan_interval_time)
    
    print("Interval time is: " + str(scan_interval_time))
    
    # Set source delay 
    #smu_id.write("smu.source.delay = %f" % scan_interval_time)   # EDITED 2023-01-05 MOVED TO SWEEP FUNCTION IN 2450 TSP

    #smu_id.write (f"smu.measure.nplc = {nplc}")
    
    # Dictionary to contain the data for plotting. 
    plotting_dictionary = {'Potential (V)':[],'Current Density (mA/cm2)':[],'Scan Rep':[], 'Voc (V)':[],'Isc (mA)':[],'Jsc (mA/cm2)':[],'Imax (mA)':[],'Vmax (V)':[],'Pmax (mW/cm2)':[],'FF (%)':[],'PCE (%)':[],'Rseries (ohm)':[],'Rshunt (ohm)':[]}
    


    # Set current compliance. From my code. This is necessary for measuring our devices. 
    
    # For lists, either you need to predetermine its size, or dynamically expand. Otherwise the line where you do:
    # outputs[i] = [voltage, current, timestamps]
    # will fail because outputs[0] doesn't exist (it's still empty.) 
    # I therefore added the step below to deliberately expand the list as the loop progresses. 0 is just a random number that
    # will be replaced later. 

    # UPDATE 2021-11-24
    # I have replaced the list completely with dictionaries. Dictionaries are easier to keep track; essentially I treat them like an array of 1D lists (The values)
    # with unique names (the key). From a dictionary, I can convert them easily into a Pandas DataFrame for easy exporting to csv, as well as for easy plotting.
 
    current_limit_actual = current_limit/1000
    
    print("Entered loop i = " + str(loop_no) + " with scan direction = " + pattern[loop_no])

    smu_id.write(f":SOUR:VOLT:ILIM:LEV {current_limit_actual}")  # EDITED 2023-01-05
    print("Current limit set.")
    
    smu_id.write(":SOUR:VOLT:DEL:AUTO OFF")
    smu_id.write(":SOUR:VOLT:DEL 0")
    
    smu_id.write(":SENS:CURR:AZER:STAT OFF")
    #smu_id.write(":SENS:AZER:ONCE")
    
    smu_id.write(":SOUR:VOLT:RANG:AUTO OFF")
    smu_id.write(f":SOUR:VOLT:RANG {volt_range}")

    # Clear the buffers for storage
    smu_id.write (":TRAC:CLE \"defbuffer1\"")  # EDITED 2023-01-05

    smu_id.write(f":TRAC:POIN {steps_no},\"defbuffer1\"")


    print("Buffers cleared.")

    smu_id.write(":FORM:DATA ASC")
    print("Data format set to ASCII.")
    smu_id.write(":FORM:ASC:PREC 6")
    print("Data precision set to 6.")

    # Configure timestamp collection option. I changed it to buffer1   # EDITED 2023-01-05 NOT NEEDED FOR 2450
    #smu_id.write ("smu.nvbuffer1.collecttimestamps = 1")
    #print("Timestamp collection activated.")

    # Even though the for loop is called from the GUI, we still need to keep track of which direction here.
    # Hence, the pattern and direction variables are passed to this function too.

    direction = pattern[loop_no]

    # We need to include a sweep direction option. 
    # Set the sweep parameters
    if direction == 'f':

        smu_id.write (f":SOUR:SWE:VOLT:LIN {min},{max},{steps_no},{scan_interval_time}")
        print("Forward sweep configured.")
    elif direction == 'r':
        smu_id.write (f":SOUR:SWE:VOLT:LIN {max},{min},{steps_no},{scan_interval_time}")
        print("Reverse sweep configured.")
    else:
        print("Breaking loop.")
        

    # EDITED 2023-01-05 NOT NEEDED IN 2450

    #smu_id.write("smu.trigger.measure.action = smu.ENABLE")  # ENABLE the sweep
    #print("Sweep parameters enabled.")

    # Set to measure current, and collect both current and voltage
    #smu_id.write ("smu.trigger.measure.iv(smu.nvbuffer1, smu.nvbuffer2)")
    #smu_id.write ("smu.trigger.source.action = smu.ENABLE")
    #print("Set to measure current.")

    # EDITED 2023-01-05 SET SENSE AND AUTORANGE
    smu_id.write(":SENS:FUNC:ON \"CURR:DC\"")
    print("SENSE set to DC_CURR.")
    smu_id.write(":SENS:CURR:RANG:AUTO OFF")
    print("Autorange on.")
    smu_id.write(f":SENS:CURR:NPLC {nplc}")
    smu_id.write(f":SENS:CURR:RANG {current_range}")

    # EDIT 2023-01-05 NOT REQUIRED
    # Set trigger count 
    #smu_id.write (f"smu.trigger.count = {steps_no}")
    #print("Trigger count set: " + str(steps_no))

    # Turn on output and run
    smu_id.write (":OUTP:STAT ON")         # EDITED 2023-01-05 
    print("Output turned on. Next step is initiate.")
    smu_id.write (":INIT")


    # To check if the sweep is complete. This is necessary. Otherwise python continues executing the rest of the code,
    # while the Keithley is still measuring. We can technically add just a sleep, but I don't fancy using a hardcoded sleep.
    # Users won't want to include the time it should sleep too. Therefore it must be automatic.
    smu_id.write("*OPC?")
    id = smu_id.read()
    print("Initial OPC ID = " + str(id))


    while int(id) != 1:
        smu_id.write("*OPC?")
        id = smu_id.read()
        sleep(1)
        print("Current ID = " + str(id))
    
    # Turn output off. We should do this. Otherwise the Keithley holds it at the voltage it stops at.
    # This will affect the measurement of our devices. We cannot leave it under bias for too long due to ionic migration.
    smu_id.write(":OUTP:STAT OFF")

   
   
   
    ##################################### GET OUTPUT (TYPE IS STRING) THEN CONVERT TO FLOAT NUMPY ARRAY #####################################

    # Get the currents
    smu_id.write(f":TRAC:DATA? 1, {steps_no}, \"defbuffer1\", READ")
    current_string = smu_id.read()
    print("Currents obtained (string form).")

    # Get the voltages
    smu_id.write(f":TRAC:DATA? 1, {steps_no}, \"defbuffer1\", SOUR")
    voltage_string = smu_id.read()
    print("Voltages obtained (string form).")

    # Get the timestamps
    smu_id.write(f":TRAC:DATA? 1, {steps_no}, \"defbuffer1\", SEC")
    sec_string = smu_id.read()
    print("Timestamps obtained (string form).")
    
    smu_id.write(f":TRAC:DATA? 1, {steps_no}, \"defbuffer1\", FRAC")
    frac_string = smu_id.read()
    print("Timestamps obtained (string form).")   

    current_string_array = current_string.split(',')
    voltage_string_array = voltage_string.split(',')
    sec_string_array = sec_string.split(',')
    frac_string_array = frac_string.split(',')

    currents = np.multiply(np.array(current_string_array, dtype=float),-1)
    print("Successful conversion of current string to array of floats. Sign reversed")
    voltages = np.array(voltage_string_array, dtype=float)
    print("Successful conversion of voltage string to array of floats.")
    
    secstamps = np.array(sec_string_array,dtype=float)
    fracstamps = np.array(frac_string_array,dtype=float)
    
    timestamps = np.add(secstamps,fracstamps)
    
    #timestamps = np.array(timestamp_string_array, dtype=float)
    print("Successful conversion of timestamp string to array of floats.")


    # For calculation of actual scan rate. I have decided to include this because the profs do ask, and we need to show
    # what the actual scan rate is, since we artifically introduced this by lengthening the delay time.
    scan_rate_dict = {'Voltage (V)': voltages,'Timestamps':timestamps}
    scan_rates = calculate_scan_rate(scan_rate_dict)
    actual_scan_rate = scan_rates[0]
    actual_scan_rate_error = scan_rates[1]

    # For solar cell parameter calculations

    # This dictionary will first be converted into a DataFrame, then be passed to the calculate_jv_params.
    # Power is required as one of the JV parameters.
    jvparamsdict = {'Voltage (V)':voltages,'Current (mA)':currents,'Power (mW)': np.multiply(voltages,currents).tolist()}
    df_jvparams = pd.DataFrame.from_dict(jvparamsdict)
    
    # Left here for debugging. 
    print("df_jvparams: " + str(df_jvparams))

    # Now the same data is transferred to the plotting dictionary. This will be sent to the plotting function.
    plotting_dictionary['Potential (V)'].extend(voltages)
    plotting_dictionary['Current Density (mA/cm2)'].extend(np.multiply(np.divide(currents,cell_area),1000))
    plotting_dictionary['Scan Rep'].extend([loop_no+1]*steps_no)



    ##################################### JV PARAMETERS CALCULATION CODE ##########################################

    # Calculate JV params
    # Updated 2021-11-26: Irradiance multiplied by 100 because value input is in Suns rather than mW/cm2
    overall = calculate_jv_params(df_jvparams,cell_area,(irradiance*100),min,max)
    jv_params = overall['Data']
    jv_params_errors = overall['Errors']

    plotting_dictionary['Voc (V)'].append(jv_params['Voc'])
    plotting_dictionary['Isc (mA)'].append(jv_params['Isc'])
    plotting_dictionary['Jsc (mA/cm2)'].append(jv_params['Jsc'])
    plotting_dictionary['Imax (mA)'].append(jv_params['Imax'])
    plotting_dictionary['Vmax (V)'].append(jv_params['Vmax'])
    plotting_dictionary['Pmax (mW/cm2)'].append(jv_params['Pmax'])
    plotting_dictionary['FF (%)'].append(jv_params['FF'])
    plotting_dictionary['PCE (%)'].append(jv_params['PCE'])
    plotting_dictionary['Rseries (ohm)'].append(jv_params['Rser'])
    plotting_dictionary['Rshunt (ohm)'].append(jv_params['Rshunt'])

    ##################################### FILE SAVING AND CSV FORMATTING CODE #####################################

    # These parameters are required for metadata purposes.
    directory = save_params[0]
    operator = save_params[1]
    sample_id = save_params[2]
    measurement_type = save_params[3]
    celltype = save_params[4]
    temp = save_params[5]

    # Get pce, change it to a format where 1.2345 --> 1[2345]. I want to avoid dots in the filename. Some programs can handle it, some cannot.
    pce = np.abs(jv_params['PCE'])
    formattedpce = "{:.4f}".format(pce)

    # Edit pce to remove the decimal place. The efficiency will go into the name of the file.
    split_pce = formattedpce.split('.')
    bracketed_pce = split_pce[0] + "[" + split_pce[1] + "]"
     

    

    # Collect date for metadata purposes, and show them in the csv file.
    now = datetime.datetime.now()

    datec = now.strftime("%Y-%m-%d %H:%M:%S")
    datec_name = now.strftime("%Y_%m_%d-%H_%M_%S")
    
    # Change direction to long form (i.e. instead of "r", say "rev")
    if direction == "r":
        direction_long = 'rev'
    elif direction == "f":
        direction_long = 'fwd'

    # If case to separate single scans from multiple scans. Multiple scans will have an extra 1,2,3,4 numeral at the back to show which scan it is
    if len(pattern) > 1:
        # Multiple scans condition
        filename = sample_id + "-" + "Rep_" +str(loop_no+1) + "-" + datec_name + '-' + direction_long + "-" + bracketed_pce  +  ".csv"

    else:
        filename = sample_id + "-" + datec_name + "-" + direction_long + "-" + bracketed_pce +  ".csv"
    



    # Formatting the csv file will require two parts. Following the old convention, JV parameters are laid out in rows.
    # This makes it easier for the others who rely on copy-pasting the cells into Origin/Excel, rather than use code to extract out the data for plotting.
    # However, due to the limitation of DataFrames, some trickery is required.
    #
    # DataFrames allow appending, if the column names are the same. With export_dictionary1, a DataFrame is constructed out of it, but with the key 
    # as the index rather than column name. The columns will then be numbered [0,1,2,...] unless a column variable is specified. 
    # (see pandas.DataFrame.from_dict(dict,orient=index))
    #
    # With export_dictionary2, the data is best represented vertically, especially since one side of it contains the actual JV graph, and the other side
    # is the sample data. The keys are named with numbers, so that when converting to DataFrame, the columns are now numbers, and they can match up with 
    # the DataFrame from export_dictionary1. 
    #
    # DataFrames cannot handle unequal matrices though. Therefore the key:pd.Series section pads all empty spaces with np.NAN, such that the overall combined
    # DataFrame will have 13 full columns and as many rows as needed, with all missing spaces filled with np.NAN. This doees not affect others who use Excel,
    # where NANs do not show. 
    #
    # Finally, DataFrames require homogeneous data type within a column. This is not the case with this csv file. Therefore, everything is converted into
    # strings. It does not affect the actual csv file; when opening in Excel, for example, the numbers are still recognised as numbers.

    export_dictionary1 = { \
    
        'Device_Parameters':['Voc (V)','Isc (mA)','Jsc (mA/cm2)','Imax (mA)','Vmax (V)','Pmax (mW/cm2)','FF (%)','PCE (%)','Rseries (ohm)','Rshunt (ohm)','CellArea (cm2)','ScanRate (mV/s)','ActualScanRate (mV/s)'], \
        'Values': [str(jv_params['Voc']),\
                    str(jv_params['Isc']),\
                    str(jv_params['Jsc']),\
                    str(jv_params['Imax']),\
                    str(jv_params['Vmax']),\
                    str(jv_params['Pmax']),\
                    str(jv_params['FF']),\
                    str(jv_params['PCE']),\
                    str(jv_params['Rser']),\
                    str(jv_params['Rshunt']),\
                    str(cell_area),str(scan_rate),str(actual_scan_rate)], \
        'Errors': [str(jv_params_errors['Voc']),\
                    str(jv_params_errors['Isc']),\
                    str(jv_params_errors['Jsc']),\
                    str(jv_params_errors['Imax']),\
                    str(jv_params_errors['Vmax']),\
                    str(jv_params_errors['Pmax']),\
                    str(jv_params_errors['FF']),\
                    str(jv_params_errors['PCE']),\
                    str(jv_params_errors['Rser']),\
                    str(jv_params_errors['Rshunt']),\
                    '-','-',str(actual_scan_rate_error)],\
        
        }
   
   
    """
    # Stringformatter (defined below) used to convert voltages, currents, and timestamps into list of strings instead of floats.
    export_dictionary2 = { \

        0: ['Potential (V)'] + (string_formatter(voltages)), \
        1: ['Current (mA)'] + string_formatter(currents), \
        2: ['Timestamp'] + string_formatter(timestamps), \
        3: ['-'], \
        4: ['SampleInfo'] + (['Operator','Sample_ID','Cell_Type','Measurement_Type','Temp','Irradiance','DateCreated','MinVolt','MaxVolt']),\
        5: ['Values'] + ([operator,'\''+sample_id,celltype,measurement_type,str(temp),str(irradiance),str(datec),str(min),str(max)]),\
        6: ['Units'] + (['-','-','-','-',"degC","Sun(s)",'-','V','V']), \
        7: ['-','-','-','-','-','-','-','-','-','-'],\
        8: ['-','-','-','-','-','-','-','-','-','-'],\
        9: ['-','-','-','-','-','-','-','-','-','-'],\
        10: ['-','-','-','-','-','-','-','-','-','-'],\
        11: ['-','-','-','-','-','-','-','-','-','-'],\
        12: ['-','-','-','-','-','-','-','-','-','-']
        }
    """
    header1_info = ['# METADATA']
    header1_label = ['Operator','Sample_ID','Cell_Type','Measurement_Type','Temp (degC)','Irradiance (Sun(s))','DateCreated','MinVolt (V)','MaxVolt (V)']
    header1_data = [operator,'\''+sample_id,celltype,measurement_type,str(temp),str(irradiance),str(datec),str(min),str(max)]
    

    separator = [' ' for x in range(13)]
    
    header2_info = ['# CALCULATED JV PARAMETERS']
    header2_label = export_dictionary1['Device_Parameters']
    header2_data = export_dictionary1['Values']
    header2_error = export_dictionary1['Errors']
    
    header3_info = ['# RAW DATA']
    header3_label = ['Potential (V)','Current (A)','Timestamps']
    
    newfilename =  str(directory)+'/'+filename 
    
    with open(newfilename,'w',encoding='UTF8',newline='') as f:
        
        writer = csv.writer(f)

        writer.writerow(header1_info)
        writer.writerow(header1_label)
        writer.writerow(header1_data)
        writer.writerow(separator)
        writer.writerow(separator)
        writer.writerow(separator)
        writer.writerow(header2_info)
        writer.writerow(header2_label)
        writer.writerow(header2_data)
        writer.writerow(header2_error)
        writer.writerow(separator)
        writer.writerow(separator)
        writer.writerow(separator)
        writer.writerow(header3_info)
        writer.writerow(header3_label)
        
        for i in range(len(voltages)):
            
            templist = [voltages[i],currents[i],timestamps[i]]
            
            writer.writerow(templist)
        
        print("CSV file exported.")
                
    """
    # Creation of first DataFrame
    export_df1 = pd.DataFrame.from_dict(export_dictionary1,orient='index')

    # Creation of second DataFrame
    export_df2 = pd.DataFrame({ key:pd.Series(value) for key, value in export_dictionary2.items() })

    #print(export_df2)

    combined = export_df1.append(export_df2,ignore_index=True,sort=False)

    #print(combined)

    combined.to_csv(str(directory)+"/"+filename,index=False,header=False)

    """

    smu_id.write (":TRAC:CLE")

    print("Buffers cleared again.")

    # Left here for debugging
    print(plotting_dictionary)
    print("Returning to Tk window.")

    wholedictionary = {"Loop":loop_no,"Dictionary":plotting_dictionary}

    # Returns the plotting dictionary because the GUI needs to plot it. 
    return wholedictionary



def stop_scan(smu_id):
    """
    Resets the system to stop the scan.
    """
    smu_id.write("smu.reset()")
    print("Keithley stopped and reset.")


def calculate_jv_params(data,cell_area,irradiance,min_bound,max_bound):

    """
    Takes data collected from Keithley, and returns a dictionary of values containing:
    
    1) Voc     : Open-circuit voltage. Requires min_bound, max_bound
    2) Isc     : Short-circult current. Requires min_bound, max_bound
    3) Jsc     : Short-circuit current density. Requires cell_area
    4) Imax    : Current at MPP
    5) Vmax    : Voltage at MPP
    6) Pmax    : MPP
    7) FF      : Fill factor
    8) PCE     : Efficiency. Requires irradiance, cell_area
    9) Rser    : Estimated series resistance (R at Voc)
    10) Rshunt : Estimated shunt resistance (R at Isc)

    Function added on 2021-11-22

    Voc is calculated by taking 6 points around the sign change for current (where current goes from positive to negative). This means there is a point
    where I = 0, and the voltage at that point is called the open-circuit voltage. A straight line (x=my+c) is plotted from the six points , and the intercept is 
    the voc. Note that the equation reads x = my+c; the axes are reversed. Taking the negative of the gradient gives the estimated Rseries.

    Isc is calculated by taking 6 points around the sign change for voltage (where voltage goes from positive to negative). This means there is a point
    where V = 0, and the current at that point is called the short-circuit current. A straight line (y=mx+c) is plotted from the six points, and the
    intercept is the Isc. Taking the negative of the inverse of the gradient gives the estimated Rshunt.

    Determining the 6 points is difficult. Here, I decided to scan the values down the DataFrame until it detects a sign change. The index where the sign
    is changed is then saved, and these six points are used:
    [i-3, i-2, i-1, i, i+1, i+2]
    where i is the index where the sign changes.

    This will lead to issues if i is too small (e.g. if i is 2, then i-3 is -1, which will then refer to the last data) or if i is too large 
    (e.g. if there are only 120 points and i = 118, then i+2 = 120 which exceeds the maximum index of the DataFrame.). 
    
    Possible reasons for i being too small is if, for calculating Isc, the voltage range is too small, or does not cross zero. I did not write cases to address
    this issue (e.g. extrapolation), since there are so many cases. I will assume that everyone scans at least 60 points, and uses a minimum voltage of -0.1V. 
    This should not pose any issue. Possible reasons for i being too large is similar. In that case, increase the voltage scanning range and make sure the graph 
    crosses the x-axis.

    As a mini solution, the code checks if any of the indices are negative or positive. It then enters a loop, which either adds 1 to all the indices until i-3
    is positive, or subtract 1 until i+2 is smaller than the length of the DataFrame. However it is unlikely that the Voc and Isc calculated will be accurate.
    More is explained in the code below where this happens.

    Pmax is determined by direct, element-by-element multiplication for the voltage and current, and getting the maximum power. The corresponding V and I 
    which gives Pmax are termed Vmax and Imax. Pmax is known as the MPP, or the Maximum Power Point.

    FF (Fill Factor) is defined as the ratio of Pmax against (Voc * Isc). This gives a measure of the "rectangular-ness" of the IV curve, which is rarely
    rectangular in shape due to defect losses. 

    PCE is the efficiency, and is the ratio of Pmax/area against the intensity of illumination.

    """


    # Contains the values
    jv_params = {
        'Voc': np.NAN, \
        'Isc': np.NAN, \
        'Jsc': np.NAN, \
        'Imax': np.NAN, \
        'Vmax': np.NAN, \
        'Pmax': np.NAN, \
        'FF': np.NAN, \
        'PCE': np.NAN, \
        'Rser': np.NAN, \
        'Rshunt': np.NAN \
    }

    # Contains the errors
    jv_params_errors = {
        'Voc': np.NAN, \
        'Isc': np.NAN, \
        'Jsc': np.NAN, \
        'Imax': np.NAN, \
        'Vmax': np.NAN, \
        'Pmax': np.NAN, \
        'FF': np.NAN, \
        'PCE': np.NAN, \
        'Rser': np.NAN, \
        'Rshunt': np.NAN \
    
    }


    ################################################################ VOC AND JSC CALCULATIONS ########################################################

    # Sort the dataframe with increasing voltage first
    
    # Data is received as a DataFrame, and usually assigning an existing DataFrame to a new variable only assigns the reference (pointer) rather 
    # than creating a new DataFrame. Hence deep copy is required. 

    data1 = data.copy(deep=True)  

    # Sort the values for easy processing, so it is known that t he first few rows have the smallest voltage.
    # Index resetting is necessary as a stupid DataFrame quirk. Note that this introduces a new column, shifting the voltage, current, etc by 1 to the right.
    data1.sort_values(by=['Voltage (V)'],inplace=True)
    data1.reset_index(inplace=True)

    # Left here for debugging purposes.
    print("Data 1 \n" + str(data1))

    # Find sign changes. Initialise variables first.

    index_voc = -1
    init_current_voc_sgn = 0
    calculate_voc = 0

    index_isc = -1
    init_voltage_isc_sgn = 0
    calculate_isc = 0

    # Left here for debugging purposes
    print("Values = " + str([data1.iloc[0][2],data1.iloc[0][1]]))

    # FIND ISC WITH VOLTAGE = 0
    for i in range(data1.shape[0]):

        # Left here for debugging purposes. 
        print("i = " + str(i)+ " and value is " +str(data1.iloc[i][1]) + "\n")
        print("Present value of init_voltage_isc_sgn = " + str(init_voltage_isc_sgn)+"\n")

        if i==0:

            # Here, the initial sign (the sign of the first data entry) is noted. Subsequent ones are compared with this
            init_voltage_isc_sgn = np.sign(data1.iloc[0][1])
            print("Initalvoltage_iscsign = " +str(init_voltage_isc_sgn)+"\n")
            print("Continuing. \n")
            continue

        # FOR ISC
        # This only runs for i >= 1. Compares the sign with the initial one.
        # If sign changes, it means it has crossed the y-axis of the jv-plot.
        if int(np.sign(data1.iloc[i][1])) != int(init_voltage_isc_sgn):
            index_isc = i
            print("Breaking loop.")
            break
        else:
            continue


    # FIND VOC WITH CURRENT = 0
    for i in range(data1.shape[0]):
                
        if i==0:

            # Here, the initial sign (the sign of the first data entry) is noted. Subsequent ones are compared with this
            init_current_voc_sgn = np.sign(data1.iloc[0][2])

            continue        
        
        #print("check: " + str(np.sign(data.iloc[i][2])) + " " +str(init_current_voc_sgn))

        # FOR VOC
        # This only runs for i >= 1. Compares the sign with the initial one.
        # If sign changes, it means it has crossed the X-axis of the jv-plot.
        if int(np.sign(data1.iloc[i][2])) != int(init_current_voc_sgn):

            index_voc = i
            break
        
    # Left for debugging
    print("Index isc = " +str(index_isc))
    print("Index Voc = " + str(index_voc))

    # If sign does not change for either, don't bother calculating - meaning the graph never crossed the x-axis or y-axis.
    # Extrapolation is possible, but a waste of effort.
    if index_voc != -1:
        calculate_voc = 1
    if index_isc != -1:
        calculate_isc = 1
    
    # Initialise the initial indices. 
    isc_addition_indices = [-3,-2,-1,0,1,2]
    voc_addition_indices = [-3,-2,-1,0,1,2]
    
    
    # Now check if the -3 and +2 causes the voltage to go out of range (due to not enough points)

    # FOR ISC. First add the index to the declared indices.
    isc_addition_indices = np.add(isc_addition_indices,index_isc)
    
    # While the first index in the array is still below 0, add 1 to all of the indices. 
    while isc_addition_indices[0] < 0:
        isc_addition_indices = np.add(isc_addition_indices,1)
        print("Current indices are (isc) " + str(isc_addition_indices))
    
    print("Indices for Isc: " + str(isc_addition_indices.tolist()))

    # FOR VOCC. First add the index to the declared indices.
    voc_addition_indices = np.add(voc_addition_indices,index_voc)
    print("Voc before addition: " + str(voc_addition_indices))

    # For voc, only the last two are likely to exceed the maximum index, should the crossing point be at the last index.
    # Therefore while the last index in the array is larger than the size of the DataFrame, subtract 1 from all the indices.
    while voc_addition_indices[5] > data.shape[0] - 1:
        voc_addition_indices = np.subtract(voc_addition_indices,1)
        print("Current indices are (voc) " + str(voc_addition_indices))

    print("Indices for Voc: " + str(voc_addition_indices.tolist()))


    # Calculate!

    if calculate_voc == 1:
        
        # Extract the voltages near the Voc
        voc_calc_voltage = [data1.iloc[voc_addition_indices[0]][1],\
                            data1.iloc[voc_addition_indices[1]][1],\
                            data1.iloc[voc_addition_indices[2]][1],\
                            data1.iloc[voc_addition_indices[3]][1],\
                            data1.iloc[voc_addition_indices[4]][1],\
                            data1.iloc[voc_addition_indices[5]][1]\
        ]

        # Extract the corresponding currents
        voc_calc_current = [data1.iloc[voc_addition_indices[0]][2],\
                            data1.iloc[voc_addition_indices[1]][2],\
                            data1.iloc[voc_addition_indices[2]][2],\
                            data1.iloc[voc_addition_indices[3]][2],\
                            data1.iloc[voc_addition_indices[4]][2],\
                            data1.iloc[voc_addition_indices[5]][2]\
        ]

        # regression of voltage against current (reverse!)

        voc_result = linregress(voc_calc_current,voc_calc_voltage)

        # Collect terms
        jv_params['Voc'] = voc_result.intercept
        jv_params_errors['Voc'] = voc_result.intercept_stderr
        jv_params['Rser'] = voc_result.slope * -1
        jv_params_errors['Rser'] = voc_result.stderr

    if calculate_isc == 1:
            
            # Extract the voltages around the Isc
            isc_calc_voltage = [data1.iloc[isc_addition_indices[0]][1],\
                                data1.iloc[isc_addition_indices[1]][1],\
                                data1.iloc[isc_addition_indices[2]][1],\
                                data1.iloc[isc_addition_indices[3]][1],\
                                data1.iloc[isc_addition_indices[4]][1],\
                                data1.iloc[isc_addition_indices[5]][1]\
            ]

            # Extract the currents around the Isc
            isc_calc_current = [data1.iloc[isc_addition_indices[0]][2],\
                                data1.iloc[isc_addition_indices[1]][2],\
                                data1.iloc[isc_addition_indices[2]][2],\
                                data1.iloc[isc_addition_indices[3]][2],\
                                data1.iloc[isc_addition_indices[4]][2],\
                                data1.iloc[isc_addition_indices[5]][2]\
            ]

            # regression of current against voltage

            isc_result = linregress(isc_calc_voltage,isc_calc_current)

            # Collect terms

            jv_params['Rshunt'] = -1/isc_result.slope
            jv_params_errors['Rshunt'] = (isc_result.stderr/np.multiply(isc_result.slope,-1))*jv_params['Rshunt'] # Percentage error

            jv_params['Isc'] = np.multiply(isc_result.intercept,1000)
            jv_params_errors['Isc'] = np.multiply(isc_result.intercept_stderr,1000)

    
    ######################################################## FILL FACTOR AND OTHERS ###########################################################

    # Here, I sort the data again, this time to have the Power in descending order. 
    # I created a new DataFrame again from the old unsorted one. I find DataFrames unpredictable, and so I opted to do this instead. 
    # Note that the reset_index introduces a new column, shifting the voltage, current, etc by 1 to the right.
    data2 = data.copy(deep=True)
    data2.sort_values(by=['Power (mW)'],inplace=True,ascending=False)
    data2.reset_index(inplace=True)

    # Left here for debugging 
    print("Line 587: " + str(data2))

    jv_params['Jsc'] = jv_params['Isc']/cell_area

    # Pmax calculated directly from raw IV curve. current was in A, not mA
    jv_params['Pmax'] = np.multiply(data2.iloc[0][3],1000)
    
    jv_params['Vmax'] = data2.iloc[0][1]
    
    # Imax calculated directly from raw IV curve. current was in A, not mA
    jv_params['Imax'] = np.multiply(data2.iloc[0][2],1000)

    # Left here for debugging
    #print("Vmax, Imax, Pmax are " + str([data2.iloc[0][1],data2.iloc[0][2],data2.iloc[0][3]]))

    jv_params['FF'] = jv_params['Pmax']/(jv_params['Voc']*jv_params['Isc']) * 100
    jv_params['PCE'] = (jv_params['Pmax']/cell_area)/(irradiance) * 100

    # Uncertainty Propagation
    # Uncertainty for Imax and Vmax taken to be tolerance of instrument

    # INCOMPLETE. Errors from the regressions are collected, but error for Vmax and Imax is related to the tolerance of the instrument, which I am not sure.
    # The manual is confusing
    

    combined_dictionary = {'Data': jv_params,'Errors':jv_params_errors}

    return combined_dictionary


def calculate_scan_rate(data):


    """
    Calculates the actual scan rate.
    I thought it was a good idea to leave it in here, so that we can continually keep track whether the actual scan rate matches the
    one we entered.

    SciPy used instead of numpy.
    """

    t_uncorrected = data['Timestamps']

    initial_t = t_uncorrected[0]

    t_corrected = np.subtract(t_uncorrected,initial_t)
    v = data['Voltage (V)']

    result = linregress(t_corrected,v)
    
    scan_rate = result.slope
    scan_rate_error = result.stderr

    return [scan_rate*1000,scan_rate_error*1000]


def string_formatter(listdata):

    """
    Takes a list of floats and converts it to a list of strings.
    If str([1,2,3]) is done then it becomes "[1,2,3]" rather than ['1','2','3']
    Hence the need for this function.
    """

    formattedStr = ['{:.4f}'.format(x) for x in listdata]

    return formattedStr
