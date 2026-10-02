import os
import tkinter as tk
from buck_gui import BuckSimulatorGUI

if __name__ == "__main__":
    root = tk.Tk()
    app = BuckSimulatorGUI(root)
    root.mainloop()