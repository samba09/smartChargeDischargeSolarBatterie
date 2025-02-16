import dateparser
import datetime as dt
import pytz
import json
import csv
import numpy as np
import math
from modbus import readCapacityAndState
from scipy.signal import find_peaks, peak_widths
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from convertPNG import convertImage
### defines
min_peakheight = 0.04 # cent
max_power_bat = 3.300 # kW
max_battery_capacity = 15 # KWh will be fetched from battery inverter
price_push = 0.1
efficiency_charge = 0.93
efficiency_discharge = 0.93
price_battery = 0.04 # Euro per kWh
# globals
debug = 0
N = 24*2*4 # two days a 4 points per hour (15 min)
timezone = pytz.timezone('Europe/Berlin')

start_battery = 0  # kWh will be fetched from battery inverter

class Frame:
    def __init__(self, startsAt):
        self.startsAt = startsAt

    cons = 0
    cons_acc = 0
    prod = 0
    prod_acc = 0
    charge = 0
    discharge = 0
    price = 0
    startsAt = 0
    soc = 0
    pull = 0
    push = 0
    cost = 0
    cost_acc = 0
    original_cost_acc = 0
    do_charge = False
    dont_discharge = False
    def print(self):
        return f"price: {self.price}, at {self.startsAt}, charge/dont discharge: {self.do_charge},{self.dont_discharge}, sol: {self.prod}, pull: {self.pull}, push: {self.push}, prod_acc: {self.prod_acc}, cons_acc: {self.cons_acc}, cost_acc: {self.cost_acc}"
    
def round_up_to_next_hour(t):
    # Check if datetime is already at the start of an hour
    if t.minute == 0 and t.second == 0 and t.microsecond == 0:
        return t
    # Otherwise, round up to the next full hour
    return (t + dt.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)

def read_consumption():

    factor = 1.2
    # jahreszeit?
    jahreszeit = ""
    if start_time.date().month in [6,7,8]:
        jahreszeit = "Sommer"
    elif start_time.date().month in [1,2,12]:
        jahreszeit = "Winter"

    # tag
    day = "Werktag"
    if start_time.date().isoweekday() == 6:
        day = "Samstag"
    elif start_time.date().isoweekday() == 7:
        day = "Sonntag"

    tag = day + jahreszeit
    print(tag)
    last = []


    p = Path(__file__).with_name('lastprofil.csv')

    with p.open(encoding='utf-8-sig', mode='r') as file:
        csv_reader = csv.DictReader(file)
        i = 0
        # Convert each row to a dictionary and print it
        for row in csv_reader:
            last.append(float(row[tag])*factor / 1000)
                        
    index = start_time.time().hour * 4 + start_time.time().minute // 15
    for i in range(len(data)):
        data[i].cons = last[(index + i) % (N//2)]

    #print(start_time.time(), index, sum(last))

######################

def read_solcast(path):
    # Replace 'your_file.csv' with the path to your CSV file
    with open(path + '/solcast.csv', encoding='utf-8-sig', mode='r') as file:
        csv_reader = csv.DictReader(file)
        
        i = 0
        # Convert each row to a dictionary and print it
        for row in csv_reader:
            ptime = dateparser.parse(row['PeriodEnd']) - dt.timedelta(minutes = 30)
            ptime = ptime.replace(tzinfo=pytz.UTC)
            
            if i == 0:
                while  data[i].startsAt < ptime:
                    i += 2

            if ptime >= start_time and i < N:
                data[i].prod = float(row['PvEstimate']) / 4
                data[i+1].prod = float(row['PvEstimate']) / 4
                #print(ptime, data[i].startsAt, data[i].prod, i)
                i += 2


    return


########################################

def read_analyse_tibber(path, start_time):
    global data
    with open(path + '/tibber.json', mode='r') as file:

        t = json.loads(file.read())
        i = 0
        for e in t['data']['viewer']['homes'][0]['currentSubscription']['priceInfo']['today']:
            ptime = dateparser.parse(e['startsAt'])
            
            if ptime >= start_time:
                print(ptime, start_time,  e['total'])
                data[i].price = e['total']
                data[i+1].price = e['total']
                data[i+2].price = e['total']
                data[i+3].price = e['total']
                i += 4
        for e in t['data']['viewer']['homes'][0]['currentSubscription']['priceInfo']['tomorrow']:
            ptime = dateparser.parse(e['startsAt'])
            if ptime >= start_time:
                data[i].price = e['total']
                data[i+1].price = e['total']
                data[i+2].price = e['total']
                data[i+3].price = e['total']
                i += 4
        
        # cleanup data with zero price
        data = list(filter(lambda d : d.price > 0, data))

        price = np.array([d.price for d in data])
        pmax = max(price)
        pmin = min(price)
        pavg = np.mean(price)
        pstd = np.std(price)
        print(f"max: {pmax}, min: {pmin}, average: {pavg}, derivation: {pstd}")

        peaks, _ = find_peaks(price, height=pavg+min_peakheight)
        peaks = sorted(peaks, key= lambda x: price[x], reverse=True)
        print("peaks",peaks)


        if len(peaks) > 0:
            peak = peaks[0]


            w1, w2 = peak_widths(price, peaks)[2:4]
            w1 = math.ceil(w1[0])
            w2 = int(w2[0])
            print(f"peak: {peak}, windows: {w1} - {w2}")
            
            ## find load peaks
            unpeaks, _ = find_peaks(-price[:w1])
            unpeaks = sorted(unpeaks, key= lambda x: price[x], reverse=False)
            print("uneaks",unpeaks)
            if len(unpeaks) > 0:
                unpeak = unpeaks[0]
                unw1, unw2 = peak_widths(-price[:w1], unpeaks)[2:4]
                unw1 = math.ceil(unw1[0])
                unw2 = int(unw2[0])
                print(f"unpeak: {unpeak}, windows: {unw1} - {unw2}")

        
    return pmin, pmax, pavg, pstd


def calculation(p1,p2, charge_power):
    soc = start_battery
    cost_acc = 0
    cons_acc = 0
    prod_acc = 0
    state = 0
    # calculations
    for d in data:
        pull = 0
        push = 0 
        discharge = 0
        charge = False
        dont_discharge = False

        # price bezogenes laden/entladen
        if d.price <= p2 and state != 2:
            if state == 0:
                state = 1
            charge =  True
        elif d.price <= p1:
            if state == 1:
                state = 2
            dont_discharge =  True

        d.do_charge = charge
        d.dont_discharge = dont_discharge

        # force charge?
        if charge:
            charge = min((max_battery_capacity-soc) / 1, max_power_bat*charge_power / 4) 
            soc += charge * efficiency_charge
            diff = d.cons - d.prod + charge
            if diff > 0:
                pull = diff
            else:
                push = -diff
        else:
            # eigenverbrauch
            if d.cons > d.prod:
                if not dont_discharge:
                    discharge = min(d.cons - d.prod, soc * efficiency_discharge / 1, max_power_bat / 4) 
                    soc -= discharge / efficiency_discharge
                pull = d.cons - d.prod - discharge
            if d.cons < d.prod:
                charge_wihth_solar = min(d.prod - d.cons, (max_battery_capacity-soc) / 1, max_power_bat / 4) 
                soc += charge_wihth_solar * efficiency_charge
                push = d.prod - d.cons - charge_wihth_solar

        d.cost = d.price * pull - push * price_push + charge * price_battery
        cost_acc += d.cost
        d.cost_acc = cost_acc
        cons_acc += d.cons
        d.cons_acc = cons_acc
        prod_acc += d.prod
        d.prod_acc = prod_acc
        if p1 == 0 and p2 == 0:
            d.original_cost_acc = cost_acc

        d.pull = pull
        d.push = push
        d.soc = soc

    return cost_acc

def calc(path, debug = 0):
    global start_time
    global data
    error = "noerror"
    global max_battery_capacity
    global start_battery

    #init
    data = []

    start_time = dt.datetime.now(tz=pytz.UTC)
    #start_time = dateparser.parse('2025-01-15T11:00:00.000+01:00')
    print("start_time", start_time)
    start_time = round_up_to_next_hour(start_time)
    print("start_time", start_time)
    for i in range(N):
        data.append(Frame(start_time + dt.timedelta(minutes = 15*i)))

    read_consumption()
    read_solcast(path)
    #print("solcast:", solcast)
    price_min, price_max, price_avg, price_std = read_analyse_tibber(path, start_time)

    # read from battery:
    if debug == 0:
        capa, state = readCapacityAndState()
        if capa > 5 and capa < 100 and state < capa and state > 0:
            start_battery = state
            max_battery_capacity = capa
    print(f"read from battery capa:{max_battery_capacity}, state:{start_battery}")

    c = calculation(0,0,0)
    print("Costs without interfere:", c)
    cost_without_interfere = c
    charge_at = 0
    discharge_over_price = []
    for p in np.arange(price_min-0.01,price_max+0.01,0.01):
        c = calculation(p,charge_at,0)
        discharge_over_price.append((p,c,data[-1].soc))

    min_cost = min(discharge_over_price, key = lambda x: x[1])

    discharge_at = min_cost[0]
    print("without charging dont discharge at:", discharge_at, min_cost)

    # soc at end of minimal cost zero? Try with charging
    if min_cost[2] < 0.1:
        
        charge_over_price = []
        for p in np.arange(price_min-0.01,price_max+0.01,0.01):
            c = calculation(price_avg,p,1)
            charge_over_price.append((p,c,data[-1].soc))

        min_cost = min(charge_over_price, key = lambda x: x[1])

        # use charge only when we have benefit! 
        if min_cost[1] < cost_without_interfere:
            discharge_at = price_avg
            charge_at = min_cost[0]
            print("best charge point:", min_cost)

    price = calculation(discharge_at,charge_at,1)

    print(f"charge at {charge_at}, dont discharge at:", discharge_at)
    print(f"price: {price}, production sum: {data[-1].prod_acc}, consumption sum: {data[-1].cons_acc}")


    # Set figure size for a 4.7-inch diagonal display
    fig_height= 4.12  # in inches
    fig_width = 6.47 # in inches
    dpi = 150 # Resolution 
    #fig = plt.figure(figsize=(fig_width, fig_height), dpi=dpi)
    #ax1 = fig.gca()
    fig, (ax1, ax2) = plt.subplots(2, gridspec_kw={'height_ratios': [5, 1]})
    fig.set_size_inches(fig_width, fig_height)
    ax12 = ax1.twinx()
    ax12.plot([d.startsAt for d in data], [d.price for d in data], color = 'black')
    ax12.set_ylabel("Price in €")
    ax12.set_ylim(0.2, max(0.8, max([d.price for d in data])))

    ax1.plot([d.startsAt for d in data], [d.prod*4 for d in data], color = 'black', linestyle='--')
    ax1.set_ylabel("Solar in kW")
    ax1.set_ylim(-0.1, max(4, max([d.prod*4 for d in data])))
    #ax1.plot([d.cons for d in data], color='red')
    # Format the x-axis with date and hour
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%a %H:%M', tz=timezone))
    ax1.xaxis.set_major_locator(mdates.HourLocator(interval=6))  # Major ticks every 6 hours
    ax1.xaxis.set_minor_locator(mdates.HourLocator(interval=1))  # Minor ticks every hour

    
    #ax2.plot([d.push for d in data], color='green')
    #ax2.plot([d.pull for d in data], color='red')
    #ax22 = ax2.twinx()
    ax2.plot([d.startsAt for d in data], [d.soc for d in data], color='gray')
    ax2.set_ylim(-0.1, 1.1*max(10, max([d.soc for d in data])))
    # Format the x-axis with date and hour
   
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('', tz=timezone))
    ax2.xaxis.set_major_locator(mdates.HourLocator(interval=6))  # Major ticks every 6 hours
    ax2.xaxis.set_minor_locator(mdates.HourLocator(interval=1))  # Minor ticks every hour
    ax2.yaxis.set_label_position("right")
    ax2.yaxis.tick_right()
    ax2.set_ylabel("Bat kWh")
    """
    ax3.plot([d.cost for d in data], color='red')
    ax32 = ax3.twinx()
    ax32.plot([d.cost_acc for d in data], color='orange')
    ax32.plot([d.original_cost_acc for d in data], color='darkorange')
    """

    try:
        plt.savefig(path + '/4_7_inch_plot.png', dpi=dpi, bbox_inches='tight')
        convertImage(path)
    except Exception as e:
        error = type(e).__name__ +  "–" + e

    if debug:
        for d in data:
            print(d.print())
        plt.show()

    return data[0].do_charge, data[0].dont_discharge, charge_at, discharge_at, error

def getBatteryActions(path):
    try:
        do_charge, dont_discharge, charge_point, discharge_point, error = calc(path, debug=0)
        print(f"do charge: {do_charge} and dont discharge: {dont_discharge}")
        print(f"forbidd discharge when below: {discharge_point}, charge when below: {charge_point}")
        return (do_charge, dont_discharge, charge_point, discharge_point, error)
    except Exception as e:
        return (False, False, 0,0, "exception in getBatteryActions")


if __name__ == '__main__':
        do_charge, dont_discharge, charge_point, discharge_point, error = calc('temp_data', debug=1)
        print(f"do charge: {do_charge} and dont discharge: {dont_discharge}")
        print(f"forbidd discharge when below: {discharge_point}, charge when below: {charge_point}")



