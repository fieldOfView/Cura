# Copyright (c) 2018 Ultimaker B.V.
# Cura is released under the terms of the LGPLv3 or higher.

import threading
import time
import serial.tools.list_ports
from os import environ
from re import search

from PyQt5.QtCore import QObject

from cura.PrinterOutput.PrinterOutputDevice import ConnectionState

from UM.Preferences import Preferences
from UM.Signal import Signal, signalemitter
from UM.OutputDevice.OutputDevicePlugin import OutputDevicePlugin
from UM.Util import parseBool
from UM.i18n import i18nCatalog

from . import USBPrinterOutputDevice

i18n_catalog = i18nCatalog("cura")


##  Manager class that ensures that an USBPrinterOutput device is created for connected USB printers.
@signalemitter
class USBPrinterOutputDeviceManager(QObject, OutputDevicePlugin):
    addUSBOutputDeviceSignal = Signal()
    removeUSBOutputDeviceSignal = Signal()
    serialPortsChanged = Signal()

    def __init__(self, application, parent = None):
        if USBPrinterOutputDeviceManager.__instance is not None:
            raise RuntimeError("Try to create singleton '%s' more than once" % self.__class__.__name__)
        USBPrinterOutputDeviceManager.__instance = self

        super().__init__(parent = parent)
        self._application = application

        self._serial_port_list = []
        self._usb_output_devices = {}
        self._usb_output_devices_model = None
        self._update_thread = threading.Thread(target = self._updateThread)
        self._update_thread.setDaemon(True)

        self._check_updates = True

        self._application.applicationShuttingDown.connect(self.stop)
        # Because the model needs to be created in the same thread as the QMLEngine, we use a signal.
        self.addUSBOutputDeviceSignal.connect(self.addOutputDevice)
        self.removeUSBOutputDeviceSignal.connect(self.removeOutputDevice)

        self._application.globalContainerStackChanged.connect(self.updateUSBPrinterOutputDevices)

        self._preferences = self._application.getPreferences()
        self._preferences.addPreference("usb_printing/list_all_serial_ports", "False")
        self._list_all_serial_ports = self._preferences.getValue("usb_printing/list_all_serial_ports")

    # The method updates/reset the USB settings for all connected USB devices
    def updateUSBPrinterOutputDevices(self):
        global_container_stack = self._application.getGlobalContainerStack()
        auto_connect = parseBool(global_container_stack.getMetaDataEntry("serial_auto_connect"))

        for key, device in self._usb_output_devices.items():
            if isinstance(device, USBPrinterOutputDevice.USBPrinterOutputDevice):
                device.resetDeviceSettings()

            if global_container_stack:
                if key == global_container_stack.getMetaDataEntry("serial_port") or global_container_stack.getMetaDataEntry("serial_port") == "AUTO":
                    device.setBaudRate(global_container_stack.getMetaDataEntry("serial_rate", "AUTO"))
                    device.connectionStateChanged.connect(self._onConnectionStateChanged)
                    if auto_connect or global_container_stack.getMetaDataEntry("serial_port") == "AUTO":
                        device.connect()
                else:
                    device.connectionStateChanged.disconnect(self._onConnectionStateChanged)
                    if device.isConnected():
                        device.close()

    def start(self):
        self._check_updates = True
        self._update_thread.start()

    def stop(self, store_data: bool = True):
        self._check_updates = False

    def _onConnectionStateChanged(self, serial_port):
        if serial_port not in self._usb_output_devices:
            return

        changed_device = self._usb_output_devices[serial_port]
        if changed_device.connectionState == ConnectionState.Connected:
            self.getOutputDeviceManager().addOutputDevice(changed_device)
        else:
            self.getOutputDeviceManager().removeOutputDevice(serial_port)

    def _updateThread(self):
        while self._check_updates:
            container_stack = self._application.getGlobalContainerStack()
            if container_stack is None:
                time.sleep(5)
                continue
            port_list = []  # Just an empty list; all USB devices will be removed.
            if container_stack.getMetaDataEntry("supports_usb_connection"):
                machine_file_formats = [file_type.strip() for file_type in container_stack.getMetaDataEntry("file_formats").split(";")]
                if "text/x-gcode" in machine_file_formats:
                    port_list = self.getSerialPortList(only_list_usb=not self._list_all_serial_ports)
            self._addRemovePorts(port_list)
            time.sleep(5)

    ##  Helper to identify serial ports (and scan for them)
    def _addRemovePorts(self, serial_ports):
        ports_changed = False

        # First, find and add all new or changed keys
        for serial_port in list(serial_ports):
            if serial_port not in self._serial_port_list:
                ports_changed = True
                self.addUSBOutputDeviceSignal.emit(serial_port)  # Hack to ensure its created in main thread
        self._serial_port_list = list(serial_ports)

        for port, device in self._usb_output_devices.items():
            if port not in self._serial_port_list:
                ports_changed = True
                self.removeUSBOutputDeviceSignal.emit(port)  # Hack to ensure this happens in main thread

        if ports_changed:
            self.serialPortsChanged.emit()

    ##  Because the model needs to be created in the same thread as the QMLEngine, we use a signal.
    def addOutputDevice(self, serial_port):
        device = USBPrinterOutputDevice.USBPrinterOutputDevice(serial_port)
        device.connectionStateChanged.connect(self._onConnectionStateChanged)
        self._usb_output_devices[serial_port] = device

        auto_connect = parseBool(global_container_stack.getMetaDataEntry("serial_auto_connect"))
        if auto_connect or global_container_stack.getMetaDataEntry("serial_port") == "AUTO":
            device.connect()

    ##  Because the model needs to be created in the same thread as the QMLEngine, we use a signal.
    def removeOutputDevice(self, serial_port):
        device = self._usb_output_devices.pop(serial_port, None)
        if device:
            device.connectionStateChanged.disconnect(self._onConnectionStateChanged)
            if device.isConnected():
                device.close()

    ##  Create a list of serial ports on the system.
    #   \param only_list_usb If true, only usb ports are listed
    def getSerialPortList(self, only_list_usb = False):
        base_list = []
        for port in serial.tools.list_ports.comports():
            if not isinstance(port, tuple):
                port = (port.device, port.description, port.hwid)
            if only_list_usb and not port[2].startswith("USB"):
                continue

            # To prevent cura from messing with serial ports of other devices,
            # filter by regular expressions passed in as environment variables.
            # Get possible patterns with python3 -m serial.tools.list_ports -v

            # set CURA_DEVICENAMES=USB[1-9] -> e.g. not matching /dev/ttyUSB0
            pattern = environ.get('CURA_DEVICENAMES')
            if pattern and not search(pattern, port[0]):
                continue

            # set CURA_DEVICETYPES=CP2102 -> match a type of serial converter
            pattern = environ.get('CURA_DEVICETYPES')
            if pattern and not search(pattern, port[1]):
                continue

            # set CURA_DEVICEINFOS=LOCATION=2-1.4 -> match a physical port
            # set CURA_DEVICEINFOS=VID:PID=10C4:EA60 -> match a vendor:product
            pattern = environ.get('CURA_DEVICEINFOS')
            if pattern and not search(pattern, port[2]):
                continue

            base_list += [port[0]]

        return list(base_list)

    def portList(self):
        return self._serial_port_list

    def setListAllSerialPorts(self, list_all_serial_ports):
        if self._list_all_serial_ports == list_all_serial_ports:
            return

        self._list_all_serial_ports = list_all_serial_ports
        self._preferences.setValue("usb_printing/list_all_serial_ports", str(list_all_serial_ports))

        result = self.getSerialPortList(only_list_usb = not list_all_serial_ports)
        self._addRemovePorts(result)

    __instance = None # type: USBPrinterOutputDeviceManager

    @classmethod
    def getInstance(cls, *args, **kwargs) -> "USBPrinterOutputDeviceManager":
        return cls.__instance
