#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import matplotlib.pyplot as plt

# -----------------------------------------------------------------------------
# Load data from txt file (d = depth, p = profile)
f_d_edep = 'output/gamma-depth-Edep.txt'
f_d_uncert = 'output/gamma-depth-Edep-Uncertainty.txt'

d_edep = np.loadtxt(f_d_edep)
d_uncert = np.loadtxt(f_d_uncert)


# -----------------------------------------------------------------------------
# Print out range, R80. Might need better resolution and more primaries.
max_index = d_edep.argmax()
max_val = d_edep[ max_index ]

found_R80 = 1
for i,d in enumerate( d_edep[max_index:] ):
    if d < max_val*0.8:
        #if not found_R80:
        if found_R80 < 10:
            #print("R80 = {}mm".format( (max_index+i)*0.1  ) )
            #found_R80 = True
            print("R80_{} = {}mm".format( found_R80, (max_index+i)*0.1  ) )
            found_R80 = found_R80 + 1
      


# -----------------------------------------------------------------------------
# Declare a figure with 2 rows
fig, ax = plt.subplots(ncols=1, nrows=1, figsize=(10, 5))

# X values from 0 to 100 every 1
x = np.linspace(0, 400, 2000)

# First curve, gamma depth in green
y = d_edep
a = ax
c1 = a.plot(x, y, 'g-', label='edep', linewidth=2)

# Second curve, gamma uncertainty in blue, share the same x axis, but use a
# different y axis
y = d_uncert
ax2 = a.twinx()
c2 = ax2.plot(x, y, 'b-', label='$\sigma$ (uncertainty)')

# Add the legend and the title
lns = c1+c2
labs = [l.get_label() for l in lns]
a.legend(lns, labs, loc=0)
a.set_title('Depth deposited energy')
a.set_xlabel('Increments (0.1mm)')
a.set_ylabel('Deposited energy in MeV')
ax2.set_ylabel('Uncertainty')

# Show the figure
plt.show()
