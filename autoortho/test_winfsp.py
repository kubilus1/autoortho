import os

dir = "E:\X-Plane-12\Custom Scenery\z_autoortho"

# direct real file
print(os.path.exists(dir + "\_textures\water_transition.png"))

#same through winfsp
print(os.path.exists(dir + "/textures/water_transition.png"))

# 'virtual' DDS
print(os.path.exists(dir + "/textures/21552_34032_BI16.dds"))

# non existent
#print(os.path.exists(dir + "/textures/bad.dds"))

fh = open(dir + "/textures/21552_34032_BI16.dds", "rb")
print(fh)
data = fh.read(1024)
print(len(data))

fh = open(dir + "/textures/21584_34176_BI16.dds", "rb")
print(fh)
data = fh.read(1024)
print(len(data))
