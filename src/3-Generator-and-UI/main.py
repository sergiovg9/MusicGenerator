import tkinter as tk
from ui import MarkovUI


def main():
    root = tk.Tk()
    root.title("Markov Music Generator")

    try:
        root.state("zoomed")    # Windows
    except:
        root.attributes("-zoomed", True)    # Linux

    app = MarkovUI(root)
    app.pack(fill="both", expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()