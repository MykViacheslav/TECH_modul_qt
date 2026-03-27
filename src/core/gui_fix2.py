import tkinter as tk

def confirm_data():
    global input_value
    if input_value:
        print("Wprowadzone dane:", input_value)
    else:
        print("Nie wprowadzono danych.")

root = tk.Tk()
root.title("Wprowadz Dane")

label = tk.Label(root, text="Wprowadź dane:")
label.pack(pady=10)

input_value = tk.StringVar()
entry = tk.Entry(root, textvariable=input_value)
entry.pack(pady=10)

confirm_button = tk.Button(root, text="Potwierdz", command=confirm_data)
confirm_button.pack(pady=10)

root.mainloop()
