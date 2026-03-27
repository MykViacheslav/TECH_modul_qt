import tkinter as tk
from tkinter import ttk

class GUI:
    def __init__(self, master):
        self.master = master
        master.title("Test AI")

        self.label = ttk.Label(master, text="Wprowad┼║ dane:")
        self.label.pack(pady=10)

        self.entry_name = ttk.Entry(master)
        self.entry_name.pack(pady=5)

        self.button_test = ttk.Button(master, text="Testuj AI", command=self.test_ai)
        self.button_test.pack(pady=10)

        self.text_output = tk.Text(master, height=10, width=40)
        self.text_output.pack(pady=10)

    def test_ai(self):
        name = self.entry_name.get()
        result = f"Test AI dla: {name}"
        self.text_output.delete("1.0", tk.END)
        self.text_output.insert(tk.END, result)

if __name__ == "__main__":
    root = tk.Tk()
    gui = GUI(root)
    root.mainloop()
