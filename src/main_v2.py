import tkinter as tk
from ui_version2 import MarkovUI


def main():
    root = tk.Tk()
    root.title("Markov Music Generator")

    app = MarkovUI(root)
    app.pack(fill="both", expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()