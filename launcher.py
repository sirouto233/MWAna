import tkinter as tk
from tkinter import ttk


def launch_app(language, root_window):
    root_window.destroy()
    main_root = tk.Tk()


    if language == 'en':
        import main_gui_en
        app = main_gui_en.BioAssayApp(main_root)
    else:
        import main_gui_zh
        app = main_gui_zh.BioAssayApp(main_root)

    main_root.mainloop()


def main():
    """Open the language selector."""
    root = tk.Tk()
    root.title("Language / 语言")
    root.geometry("300x150")


    root.eval('tk::PlaceWindow . center')

    label = ttk.Label(root, text="Please select a language\n请选择运行语言", justify="center")
    label.pack(pady=20)

    btn_frame = ttk.Frame(root)
    btn_frame.pack()

    btn_en = ttk.Button(btn_frame, text="English", command=lambda: launch_app('en', root))
    btn_en.grid(row=0, column=0, padx=10)

    btn_zh = ttk.Button(btn_frame, text="中文", command=lambda: launch_app('zh', root))
    btn_zh.grid(row=0, column=1, padx=10)

    root.mainloop()


if __name__ == "__main__":
    main()
