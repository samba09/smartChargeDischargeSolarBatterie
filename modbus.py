from pyModbusTCP.client import ModbusClient
import pyModbusTCP.utils as util
import logging
import time
import ctypes
import csv









logging.basicConfig()
logging.getLogger('pyModbusTCP.client').setLevel(logging.DEBUG)


allregister = []
# Replace 'your_file.csv' with the path to your CSV file
with open('sunnyislandregisterRO.csv', encoding='utf-8-sig', mode='r') as file:
    csv_reader = csv.DictReader(file)
    
    # Convert each row to a dictionary and print it
    for row in csv_reader:
        allregister.append(row)

#print(allregister)
regdict = {}
for r in allregister:
    regdict[r["register"]]=r


def createConnection():
    connection = ModbusClient(host="192.168.0.208", port=502, unit_id=3, auto_open=True)
    return connection

def readKapaitätAndState():
    c = createConnection()
    regs = c.read_input_registers(40187, 2)
    capa = ctypes.c_int32(util.word_list_to_long(regs)[0]).value

    regs = c.read_input_registers(40719, 2)
    tief = ctypes.c_int32(util.word_list_to_long(regs)[0]).value / 100.0

    regs = c.read_input_registers(31009, 2)
    untere = ctypes.c_int32(util.word_list_to_long(regs)[0]).value / 100.0

    regs = c.read_input_registers(30845, 2)
    soc = ctypes.c_int32(util.word_list_to_long(regs)[0]).value / 100.0

    state = (soc - (untere + tief))*capa / 1000
    capa_rel = (capa - (untere + tief)*capa) / 1000

    return capa_rel, state

if __name__ == '__main__':
    # Execute when the module is not initialized from an import stateme

    # TCP auto connect on first modbus request
    c = createConnection()
    start = time.time()

    charge_discharge = False
    power = 10


    if charge_discharge:
        # no out to net
        regs = util.long_list_to_word([0])
        c.write_multiple_registers(40801, regs)
        time.sleep(1)
        # correct bms mode
        regs = util.long_list_to_word([2424])
        c.write_multiple_registers(40236, regs)
        time.sleep(1)
        # set maxium of discharge (could be less)
        regs = util.long_list_to_word([3300])
        c.write_multiple_registers(40799, regs)
        time.sleep(1)

        # set maxium of charge (could be less)
        regs = util.long_list_to_word([3300])
        c.write_multiple_registers(40795, regs)
        time.sleep(1)
        # power negative (charge)
        if power < 100:
            # set direct the wish
            regs = util.long_list_to_word([power])
            c.write_multiple_registers(40149, regs)

            time.sleep(2)
            # on/off manuall
            regs = util.long_list_to_word([802])
            c.write_multiple_registers(40151, regs)
        else:
            # on/off manuall
            regs = util.long_list_to_word([803])
            c.write_multiple_registers(40151, regs)
            time.sleep(1)
        
            # set maxium of discharge (could be less)
            regs = util.long_list_to_word([abs(power)])
            c.write_multiple_registers(40799, regs)
            time.sleep(1)

            # set maxium of charge (could be less)
            #regs = util.long_list_to_word([abs(power)])
            #c.write_multiple_registers(40795, regs)
            #time.sleep(1)


    #read = list(regdict.keys())[:]
    read = ["40191","40189","30053","30775", "30845", "31009","40187","40719", "41259"] 
    print(read)
    try:
        while (c.open()):
            print("read regs")
            out = {}
            for r in read:
                reg = regdict[r]
                print(reg)
                n = int(reg["words"])
                print(n)
                if reg["access"] == "RW":
                    regs = c.read_holding_registers(int(r), n)
                elif reg["access"] == "RO":
                    regs = c.read_input_registers(int(r), n)
                if n == 2:
                    out[r] = (ctypes.c_int32(util.word_list_to_long(regs)[0]).value, regdict[r]["name"])
                else:
                    out[r] = (regs[0], regdict[r]["name"])


            for r in out.keys():
                print(r, ":", out[r][0], regdict[r]["unit"], ":", regdict[r]["name"])
            print(time.time()-start)
            time.sleep(5)



    except KeyboardInterrupt:
        pass