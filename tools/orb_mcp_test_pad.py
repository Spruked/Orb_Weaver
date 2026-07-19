import tkinter as tk


def main() -> None:
    root = tk.Tk()
    root.title("ORB MCP TEST PAD — SAFE WINDOW")
    root.geometry("600x400+100+100")
    root.configure(bg="#0f172a")

    def confirm_test() -> None:
        button.config(text="VERIFIED", bg="#10b981", fg="white")
        print("[AUDIT] Test Pad: Confirm Test button clicked and state changed.", flush=True)

    label = tk.Label(
        root,
        text="System Isolation Test Pad",
        bg="#0f172a",
        fg="#38bdf8",
        font=("Arial", 14, "bold"),
    )
    label.pack(pady=10)

    canvas = tk.Canvas(root, width=400, height=100, bg="#1e293b", highlightthickness=0)
    canvas.pack(pady=20)
    canvas.create_text(
        200,
        50,
        text="CALIBRATION TOKEN: OW-7K2-913",
        fill="#f8fafc",
        font=("Courier", 12, "bold"),
    )

    button = tk.Button(
        root,
        text="Confirm Test",
        command=confirm_test,
        bg="#3b82f6",
        fg="white",
        font=("Arial", 10, "bold"),
        padx=10,
        pady=5,
    )
    button.pack(pady=20)

    print("[INFO] Safe Window Ready. Title: ORB MCP TEST PAD — SAFE WINDOW", flush=True)
    root.mainloop()


if __name__ == "__main__":
    main()
