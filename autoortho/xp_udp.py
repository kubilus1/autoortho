import os
import socket
import struct

UDP_IP = "127.0.0.1"

def reload_obj(path):
  sock = socket.socket(socket.AF_INET, # Internet
                       socket.SOCK_DGRAM) # UDP
  
  cmd = b"OBJN"
  idx = 1
  #string = "Custom Scenery/z_autoortho/Earth nav data/+40-120/+40-112.dsf"
  string = os.path.join("Custom Scenery/z_autoortho", path)
  message = struct.pack("<4sxi500s", cmd, idx, string.encode('utf-8'))

  sock.sendto(message, ("127.0.01", 49000))


# List of datarefs to request. 
datarefs = [
    # ( dataref, unit, description, num decimals to display in formatted output )
    ("sim/flightmodel/position/latitude","°N","The latitude of the aircraft",6),
    ("sim/flightmodel/position/longitude","°E","The longitude of the aircraft",6),
    ("sim/flightmodel/misc/h_ind", "ft", "",0),
    ("sim/flightmodel/position/y_agl","m", "AGL", 0), 
    ("sim/flightmodel/position/mag_psi", "°", "The real magnetic heading of the aircraft",0),
    ("sim/flightmodel/position/indicated_airspeed", "kt", "Air speed indicated - this takes into account air density and wind direction",0), 
    ("sim/flightmodel/position/groundspeed","m/s", "The ground speed of the aircraft",0),
    ("sim/flightmodel/position/vh_ind", "m/s", "vertical velocity",1)
  ]

def RequestDataRefs(sock, UDP_PORT=49000, REG_FREQ=2):
  for idx,dataref in enumerate(datarefs):
    # Send one RREF Command for every dataref in the list.
    # Give them an index number and a frequency in Hz.
    # To disable sending you send frequency 0. 
    cmd = b"RREF\x00"
    freq=REQ_FREQ
    string = datarefs[idx][0].encode()
    message = struct.pack("<5sii400s", cmd, freq, idx, string)
    assert(len(message)==413)
    sock.sendto(message, (UDP_IP, UDP_PORT))

def DecodePacket(data):
  retvalues = {}
  # Read the Header "RREFO".
  header=data[0:4]
  #print(header)
  if(header!=b"RREF"):
    print("Unknown packet: ", binascii.hexlify(data))
  else:
    # We get 8 bytes for every dataref sent:
    #    An integer for idx and the float value. 
    values =data[5:]
    lenvalue = 8
    numvalues = int(len(values)/lenvalue)
    idx=0
    value=0
    for i in range(0,numvalues):
      singledata = data[(5+lenvalue*i):(5+lenvalue*(i+1))]
      (idx,value) = struct.unpack("<if", singledata)
      retvalues[idx] = (value, datarefs[idx][1], datarefs[idx][0])
  return retvalues

