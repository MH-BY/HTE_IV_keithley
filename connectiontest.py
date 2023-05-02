#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec  7 17:25:49 2022

@author: ebeem
"""

import pyvisa as visa
import numpy as np

rm = visa.ResourceManager()
instruments = np.array(rm.list_resources())

for instrument in instruments:
    my_instrument = rm.open_resource(instrument)
    try:
        identity = my_instrument.query('*IDN?')
        print("Resource: '" + instrument + "' is")
        print(identity + '\n')
    except visa.VisaIOError:
        print('No connection to: ' + instrument)