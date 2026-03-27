```python
import tkinter as tk
from tkinter import ttk

class GUIFix:
    def __init__(self, master):
        self.master = master
        master.title("Wprowad┼║ dane")

        self.label = ttk.Label(master, text="Wprowad┼║ dane:")
        self.label.pack()

        self.entry = ttk.Entry(master, width=30)
        self.entry.pack()

        self.button = ttk.Button(master, text="Potwierd┼║", command=self.potwierdz_dane)
        self.button.pack()

    def potwierdz_dane(self):
        dane = self.entry.get()
        print("Wprowadzone dane:", dane) # Wy┼Ťwietlenie danych w konsoli.
        # Tutaj mo┼╝esz doda─ç logik─Ö do dalszej obr├│bki danych.

def main():
    root = tk.Tk()
    gui = GUIFix(root)
    root.mainloop()

if __name__ == "__main__":
    main()
```

