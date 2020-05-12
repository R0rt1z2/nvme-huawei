#!/usr/bin/env python3

#   Huawei NVME "parser" - Roger Ortiz (R0rt1z2) - 2020.
#   I'm not responsable of any damages caused to the phone by using this tool.
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

import sys
import struct
import re

VERSION = 1.0
MAGIC = "486973692D4E562D506172746974696F6E"
MAX_GAP = 20
STRING_LENGHT = 45

# List of strings that have a value defined. Will be expanded...
VALUES = {
    "53575645525349":"SWVERSI", # Software version.
    "424F4152444944":"BOARDID", # Board ID.
    "534E":"SN", # S/N or Serial.
    "4D414341444452":"MACADDR", # MAC Address.
    "4D44415445":"MDATE", # DATE (?)
    "4553575652":"ESWVR", # Software version of something (need to check).
    "4953575652":"ISWVR", # Software version of something (need to check).
    "4548575652":"EHWVR", # Hardware version of something (need to check).
    "4948575652":"IHWVR", # Hardware version of something (need to check).
    "544D4D49":"TMMI", # ?? (need to check).
    "4D4143574C414E":"MACWLAN", # WLAN MAC Address.
    "4D41434254":"MACBT", # BT MAC Address.
    "57564C4F434B":"WVLOCK", # WVLOCK
    "57564445564944":"WVDEVID", # WVDEVID
    "48494D4E544E":"HIMNTN", # ?? (need to check).
    "44554D5043544C":"DUMPCTL", # ?? (need to check).
    "4652504B4559":"FRPKEY", # FRP Key (not correctly decoded).
    "53504B5F5041":"SPK_PA", # ?? (need to check).
    "4249444241434B":"BIDBACK", # ?? (need to check).
    "5450434F4C4F52":"TPCOLOR", # Phone color (?)
}

def get_value_offset(data, value):
    """ Checks in the given data for the given value. (Uses "find()" method).
        No need to specify the value type (i.e: if value is a hex, the function 
        itself will try convert those to bytes)

        :returns: the offset of the value (if found)."""
    if len(data) <= 0:
        raise RuntimeError("Given data is too short!")
    try:
        OFFSET = data.find(value)
    except TypeError:
        try:
            OFFSET = data.find(bytes.fromhex(value))
        except ValueError:
            raise RuntimeError("Could not determine the type of the given value!")
    return OFFSET

def get_gap_num(string):
    """ Checks the blank gaps that are between the string and it's specific value.
        This gap number may be different depending on the lenght of the string. To 
        calculate this number, just do 20 - len(string).

        :returns: the number of gaps found.
    """
    _GAP_NUMBER_ = MAX_GAP - len(string)
    return _GAP_NUMBER_

def parse_null_bytes(image):
    """ Ironically, Huawei decided to put a lot of null (b'\x00') bytes in the top of
        the image and we don't care about those. This function, get's the offset of where 
        they end. In most of the cases, the number of null bytes is 131076 but may change 
        (depending on the image).

        :returns: the offset where those null bytes end.
    """
    with open(image, "rb") as fp:
        _DATA_ = fp.read()
        _OFFSET_ = get_value_offset(_DATA_, MAGIC)
        fp.seek(_OFFSET_)
        _HDR_ = fp.read(17)

    if _HDR_ != b'Hisi-NV-Partition':
        raise RuntimeError("Expected {} but got {}!".format(MAGIC, _HDR_))
    else:
        return _OFFSET_

def parse_string(offset, gap, image, buf):
    """ Parses the value of a string that is stored in the NVME image.
        Uses the string offset previously calculated by get_value_offset and the
        number of gaps that are between the string and the value.

        :returns: the value of the given string.
    """
    with open(image, "rb") as fp:
        fp.seek(offset + buf + gap)
        try:
            _VALUE_ = str(fp.read(STRING_LENGHT).decode('ascii')) # (remove b'\x00).
        except UnicodeDecodeError:
            try:
                _VALUE_ = str(fp.read(STRING_LENGHT).decode('ascii', 'ignore'))
            except UnicodeDecodeError:
                _VALUE_ = str(fp.read(STRING_LENGHT)) # is the value type of bytes?
    
    if bool(re.search('[a-z0-9]', _VALUE_, re.IGNORECASE)) is not True or _VALUE_ == "": # (check if value is empty)
        return "NULL"
    else:
        return _VALUE_

def show_help():
    print("""USAGE:
      -r nvme.img --> Read the nvme values.
      -d (optional second arg) --> Print debug info (offset).
          """)

def main():
    """ Main function.

        :returns: nothing
    """
    print("\nHi-Si NVME parser -- v{}\n".format(VERSION))

    # 0- Parse program arguments.
    if len(sys.argv) < 3:
        print("ERROR: Expected more arguments...\n")
        show_help()
        exit(0)

    if sys.argv[1] == "-r":
        # 1- Open and read the data of the NVME image.
        if len(sys.argv) == 4:
            _NVME_ = sys.argv[3]
        elif len(sys.argv) == 3:
            _NVME_ = sys.argv[2]

        with open(_NVME_, "rb") as fp:
            _DATA_ = fp.read()

        # 2- Does the image has a valid header.
        parse_null_bytes(_NVME_)

        # 3- Loop on the image to read all the values.
        for _VALUE_ in VALUES.keys():
             # 3.1- Get the value offset.
             _VALUE_OFFSET_ = get_value_offset(_DATA_, _VALUE_)
             # 3.2- Get the gaps that are between string and value.
             _VALUE_GAP_ = get_gap_num(_VALUE_)
             # 3.3- Get/read the value.
             _VALUE_RES_ = parse_string(_VALUE_OFFSET_, _VALUE_GAP_, _NVME_, len(bytes.fromhex(_VALUE_)))
             # 3.4- Check debug & print.
             if len(sys.argv) == 4 and sys.argv[2] == "-d":
                 print("{} = {} (OFFSET = {}) (LENGHT = {})".format(bytes.fromhex(_VALUE_).decode('ascii'), _VALUE_RES_, _VALUE_OFFSET_, len(_VALUE_)))
             else:
                 print("{} = {}".format(bytes.fromhex(_VALUE_).decode('ascii'), _VALUE_RES_))

        print("")

    else:
        print("ERROR: Unknown option: {}\n".format(sys.argv[1]))
        show_help()

if __name__ == "__main__":
    main()    
