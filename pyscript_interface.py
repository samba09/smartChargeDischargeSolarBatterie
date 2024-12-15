import sys

if "/config/pyscript_modules" not in sys.path:
    sys.path.append("/config/pyscript_modules")

from downloadData import downloadData
from readData import getBatteryActions

temp_data = "/config/temp_data"

@service
def debug_test_call(action=None, id=None):
    log.info(f"hello_world called {action} {id}")
    
    task.executor(downloadData,temp_data)
    charge_discharge = task.executor(getBatteryActions,temp_data)
    do_charge, dont_discharge = charge_discharge
    log.info(f"do charge: {do_charge} and dont discharge: {dont_discharge}")

    if do_charge:
        input_boolean.do_charge.turn_on()
    else:
        input_boolean.do_charge.turn_off()

    if dont_discharge:
        input_boolean.dont_discharge.turn_on()
    else:
        input_boolean.dont_discharge.turn_off()

# call_script_every_3_hours.py
@time_trigger("cron(0 */3 * * *)")  # Run every 3 hours
def call_download_data():
    log.info("Calling external DownloadData from via pyscript")
    task.executor(downloadData, temp_data)


@time_trigger("cron(1/15 * * * *)")  # Start at minute 1 and repeat every 15 minutes
def call_calculate_data():
    charge_discharge = task.executor(getBatteryActions, temp_data)
    do_charge, dont_discharge = charge_discharge
    log.info(f"do charge: {do_charge} and dont discharge: {dont_discharge}")

    if do_charge:
        input_boolean.do_charge.turn_on()
    else:
        input_boolean.do_charge.turn_off()

    if dont_discharge:
        input_boolean.dont_discharge.turn_on()
    else:
        input_boolean.dont_discharge.turn_off()
