# call_script_every_3_hours.py
from downloadData import downloadData
from readData import getBatteryActions

@time_trigger("cron(0 */3 * * *)")  # Run every 3 hours
def call_download_data():
    log.info("Calling external DownloadData from via pyscript")
    downloadData()


@time_trigger("cron(1/15 * * * *)")  # Start at minute 1 and repeat every 15 minutes
def call_calculate_data():
    do_charge, dont_discharge = getBatteryActions()
    log.info(f"do charge: {do_charge} and dont discharge: {dont_discharge}")

    # Update Home Assistant entities
    hass.states.set("sensor.do_charge", do_charge)
    hass.states.set("sensor.dont_discharge", dont_discharge)