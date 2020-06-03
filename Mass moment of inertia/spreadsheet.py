from typing import Optional, Any

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import numpy as np


# normalize function
# copied directly from https://stackoverflow.com/questions/21030391/how-to-normalize-an-array-in-numpy
def normalize(v):
    norm = np.linalg.norm(v)
    if norm == 0:
        return v
    return v / norm


# use creds to create a client to interact with the Google Drive API
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
client = gspread.authorize(creds)

# Find a workbook by name and open the first sheet
# Make sure you use the right name here.
sheet = client.open("Mass of components for mass moment inertia calculation").sheet1

# Extract and print all of the values
list_of_hashes = sheet.get_all_records()
# print(list_of_hashes)

# the data is stored in list of hashes as a list containing dict(ionarie)s by the import script

# calculate center of gravity using the weighted average
cgx = 0.0
cgy = 0.0
cgz = 0.0
mass = 0.0

for column in list_of_hashes:
    cgx = cgx + (column.get('mass [kg]') * column.get('x [m]'))
    cgy = cgy + (column.get('mass [kg]') * column.get('y [m]'))
    cgz = cgz + (column.get('mass [kg]') * column.get('z [m]'))
    mass = mass + column.get('mass [kg]')
# divide by sum of mass
cgx, cgy, cgz = cgx / mass, cgy / mass, cgz / mass
# format the center of gravity into a dict
center_of_gravity = {'x': cgx,
                     'y': cgy,
                     'z': cgz}
# update the corresponding cell G2
sheet.update('J2', str(center_of_gravity))

# update the positions of components with respect to the center of gravity

# This is the position of the components with respect to the body axis system: origin is the Center of gravity,
# x lies in the symmetry plane and points forward, z lies in the symmetry plane and points downward, y from the right
# handrule
cellvalues = []
for column in list_of_hashes:
    column['Xb [m]'] = center_of_gravity.get('x') - column.get('y [m]')
    column['Yb [m]'] = center_of_gravity.get('y') - column.get('x [m]')
    column['Zb [m]'] = center_of_gravity.get('z') + column.get('z [m]')
    # format for cellupdate
    cellvalues.append([column['Xb [m]'], column['Yb [m]'], column['Zb [m]']])

# update the cells in the sheet
sheet.update('K2', cellvalues)

# Calculate mass moment of inertia for each piece
InertiaTensor = np.zeros((3, 3))
for column in list_of_hashes:
    m = column.get('mass [kg]')

#    if column['shape'] == 'Solid cuboid of width w, height h, depth d': # this piece will not be used. cuboids are the only option.
    w = column.get('w [m]')
    d = column.get('d [m]')
    h = column.get('h [m]')
    """We will not orient the cubes they will all point up Keep it simple stupid. That's why this piece of code will be ignored
        
        # use orientationvector provided or use z-axis
        try:
            orientationVector = np.array(str(column.get('orientation vector')).split(','), dtype=float)
        except:
            orientationVector = np.array([0., 0., 1.])
            print("For " + column.get("component name or description") + ", no orientation vector was found.")
            print("Orientation vector [0., 0., 1.] was assumed.")
        orientationVector = normalize(orientationVector)
    """
    InertiaTensor = InertiaTensor + 1. / 12. * np.array([[m * (h ** 2 + d ** 2), 0.0, 0.0],
                                                         [0.0, m * (w ** 2 + d ** 2), 0.0],
                                                         [0.0, 0.0, m * (w ** 2 + h ** 2)]])

"""Cylinders will not be used for this estimation
    elif column['shape'] == 'Solid cylinder of radius r, height h':
        r = column.get('w or r [m]')
        h = column.get('h [m]')
        try:
            orientationVector = np.array(str(column.get('orientation vector')).split(','), dtype=float)
        except:
            orientationVector = np.array([0., 0., 1.])
            print("For " + column.get("component name or description") + ", no orientation vector was found.")
            print("Orientation vector [0., 0., 1.] was assumed.")
        orientationVector = normalize(orientationVector)
"""
# calculate Steiner term
for column in list_of_hashes:
    m = column.get('mass [kg]')
    x = column.get('Xb [m]')
    y = column.get('Yb [m]')
    z = column.get('Zb [m]')
    InertiaTensor = InertiaTensor + np.array(
        [[m * x * x, m * x * y, m * x * z], [m * y * x, m * y * y, m * y * z], [m * z * x, m * z * y, m * z * z]])

# update the cells in the sheet
sheet.update('O5', InertiaTensor.tolist())
