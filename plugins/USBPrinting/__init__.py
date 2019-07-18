# Copyright (c) 2019 Ultimaker B.V.
# Cura is released under the terms of the LGPLv3 or higher.

from . import USBPrinterOutputDeviceManager
from . import ConnectUSBAction


def getMetaData():
    return {}


def register(app):
    # We are violating the QT API here (as we use a factory, which is technically not allowed).
    # but we don't really have another means for doing this (and it seems to you know -work-)
    return {
        "machine_action": ConnectUSBAction.ConnectUSBAction(),
        "output_device": USBPrinterOutputDeviceManager.USBPrinterOutputDeviceManager(app)
    }
