import threading
import Keithley2450_voltage_sweep as kvs
import time
import queue

class Runner(threading.Thread):

    def __init__(self,dataqueue,smu_id, \
                    steps_no, \
                    pattern, \
                    nplc, \
                    min, \
                    max,\
                    scan_rate, \
                    cell_area,\
                    irradiance,\
                    current_limit,\
                    save_params,\
                    timeout,\
                    sleeptime,\
                    stop_thread_queue,\
                    voltrange,\
                    currentrange):
        
        super().__init__()
        threading.Thread.__init__(self)
        
        self.should_stop = 0
        #self.buffer = []
        self.dataqueue = dataqueue
        self.smu_id = smu_id
        self.steps_no = steps_no
        self.pattern = pattern
        self.nplc = nplc
        self.min = min
        self.max = max
        self.scan_rate = scan_rate
        self.cell_area = cell_area
        self.irradiance = irradiance
        self.current_limit = current_limit
        self.save_params = save_params
        self.timeout = timeout
        self.sleeptime = sleeptime
        self.stop_thread_queue = stop_thread_queue
        self.voltrange = voltrange
        self.currentrange = currentrange

    def run(self):

        for i in range(len(self.pattern)):

            test_output = kvs.sweep_operation(self.smu_id, \
                                        self.steps_no, \
                                        self.pattern, \
                                        self.nplc, \
                                        self.min, \
                                        self.max, \
                                        self.scan_rate,\
                                        i,\
                                        self.cell_area,\
                                        self.irradiance,\
                                        self.current_limit,\
                                        self.save_params,\
                                        self.timeout,\
                                        self.voltrange,\
                                        self.currentrange) 

            self.dataqueue.put(test_output)

            # Get from stop_thread_queue. If empty, continue; if got signal, then break from this loop.

            try:
                stop_now = self.stop_thread_queue.get_nowait()
                if stop_now == 1:
                    print("thread_wrapper detects a stop signal, and will break out of this loop once the SMU is done.")
                    self.dataqueue.task_done()
                    return
                else:
                    pass

            except queue.Empty:
                print("EMTPY")
                pass


            time.sleep(self.sleeptime)
        
        self.dataqueue.task_done()
        
        pass


    pass