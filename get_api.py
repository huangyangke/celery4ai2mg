import requests
import json
import numpy as np


service_url=f"http://10.1.224.7:4111/func_call" 

if __name__ == '__main__':
    test_time = 10
    image_url = ''
    input_data = {"image_url":image_url}

    for i in range(test_time):
        result = requests.post(service_url,data=json.dumps(input_data)).json()
        print(result)