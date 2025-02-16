
import requests

def downloadData(path):
    ## tibber 

    tibber_payload = {"query":"{viewer{homes{currentSubscription{priceInfo{current{total energy tax startsAt}today{total startsAt}tomorrow{total startsAt}}}}}}"}
    header = {"Authorization": "Bearer GrSWNTl2LO_ieQs8E30NDJI7SaBc1OIPOjuuKhzXQPc"}

    response = requests.post("https://api.tibber.com/v1-beta/gql",  json=tibber_payload, headers=header)

    if response.status_code == requests.codes.ok:
        with open(path + '/tibber.json', mode='w') as file:
            file.write(response.text)
    

    ### solcast

    url = "https://api.solcast.com.au/rooftop_sites/9046-f9e0-6d73-78dc/forecasts?format=csv"
    payload={}
    header = {"Authorization": "Bearer 47ftOh6XKX9d9oFdWamsNhOV3nnTzeF6"}

    response = requests.request("GET", url, headers=header, data=payload)

    if response.status_code == requests.codes.ok:
        with open(path + '/solcast.csv', mode='w') as file:
            file.write(response.text)

    print("done")

if __name__ == '__main__':
    downloadData("temp_data")