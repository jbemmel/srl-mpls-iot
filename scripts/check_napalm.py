#!/usr/bin/python3

# Copyright 2022 Nokia
# Licensed under the Apache License 2.0.
# SPDX-License-Identifier: Apache-2.0

from napalm import get_network_driver
import json

driver = get_network_driver("srl")
optional_args = {
    "gnmi_port": 57400,
    "jsonrpc_port": 80,
    "target_name": "172.20.20.2",
    "tls_cert":"/root/gnmic_certs/srl_certs/clientCert.crt",
    "tls_ca": "/root/gnmic_certs/srl_certs/RootCA.crt",
    "tls_key": "/root/gnmic_certs/srl_certs/clientKey.pem",
     #"skip_verify": True,
     #"insecure": False
    "encoding": "JSON_IETF"
} 
device = driver("172.20.20.2", "admin", "admin", 60, optional_args)
device.open()

print(json.dumps(device.get_facts())) 

device.close()
