import matplotlib.pyplot as plt
import numpy as np


#%%
# test data
t = np.linspace(0, 2 * np.pi, 30)
x = np.sin(t)
y = np.cos(t)


colors={0:"darkred",
           0.5:"saddlebrown",
           1:"orange"}


# normal values
plt.scatter(t, x, c = colors)
plt.show()



#%%

from matplotlib import pyplot as plt

x = [1, 2, 3, 4, 5, 6, 7, 8, 9]
y = [125, 32, 54, 253, 67, 87, 233, 56, 67]

color = ["saddlebrown" for item in y]

plt.scatter(x, y, s=500, c=color)

plt.show()