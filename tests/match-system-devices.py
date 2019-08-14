#!/usr/bin/python3

from Dell.recovery_common import match_system_device
import subprocess

pci_call = subprocess.Popen(['lspci', '-n'], stdout=subprocess.PIPE,
                            universal_newlines=True)
pci_output = pci_call.communicate()[0]
for line in pci_output.split('\n'):
    if line:
        vendor = line.split(':')[2].strip()
        product = line.split(':')[3].split()[0]
        print("Trying to match PCI %s:%s (using python): %i."  % (vendor,product,match_system_device('pci','0x' + vendor, '0x' + product)))

usb_call = subprocess.Popen(['lsusb'], stdout = subprocess.PIPE,
                            universal_newlines=True)
usb_output = usb_call.communicate()[0]
for line in pci_output.split('\n'):
    if line:
        vendor = line.split(':')[2].strip()
        product = line.split(':')[3].split()[0]
        print("Trying to match USB %s:%s (using python): %i."  % (vendor,product,match_system_device('pci','0x' + vendor, '0x' + product)))
