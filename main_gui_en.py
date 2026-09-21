import os


# Set before importing OpenCV or backend modules.
os.environ["OPENCV_LOG_LEVEL"] = "FATAL"

import sys
import threading
import multiprocessing
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox


try:
    from logic_en import image_classifier
    from logic_en import light_balance
    from logic_en import microwell_detection
    from logic_en import bead_prediction
    from logic_en import fluorescence_analysis
    from logic_en import manual_labeling
    from logic_en import train_model

    MODULES_LOADED = True
except ImportError as e:
    print(f"Notice: Running in UI Preview Mode (Missing logic module: {e})")
    MODULES_LOADED = False
    image_classifier = light_balance = microwell_detection = None
    bead_prediction = fluorescence_analysis = manual_labeling = train_model = None


class TextRedirector:
    """Schedule log insertion into the Tkinter text widget."""

    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, str_msg):


        self.widget.after(0, self._write_to_widget, str_msg)

    def _write_to_widget(self, str_msg):
        try:
            self.widget.configure(state="normal")
            self.widget.insert("end", str_msg, (self.tag,))
            self.widget.see("end")
            self.widget.configure(state="disabled")
        except Exception:
            pass

    def flush(self):
        pass


class BioAssayApp:
    """Desktop interface for microwell bead and fluorescence analysis."""

    def __init__(self, root):
        self.root = root
        self.root.title("MWAna_V1.0")
        self.root.geometry("1000x850")


        self.colors = {
            "bg": "#dbb9e1", "fg": "#660874", "panel_bg": "#dbb9e1",
            "accent": "#660874", "accent_hover": "#ead6ed",
            "stop": "#C26BA0", "stop_hover": "#E0B3CE",
            "log_bg": "#ead6ed", "log_fg": "#660874",
        }
        self.fonts = {
            "main": ("Segoe UI", 10), "bold": ("Segoe UI", 10, "bold"),
            "title": ("Segoe UI", 11, "bold"), "log": ("Segoe UI", 10)
        }

        self.setup_styles()
        self.root.configure(bg=self.colors["bg"])

        self.stop_event = threading.Event()
        self.is_running = False
        self.widgets = {}

        self.create_widgets()


        sys.stdout = TextRedirector(self.log_text)
        sys.stderr = TextRedirector(self.log_text)

        if not MODULES_LOADED:
            print(">>> Started in Preview Mode. UI is visible, but logic features are unavailable <<<")

    def setup_styles(self):
        """Configure ttk colors and fonts."""
        style = ttk.Style()
        style.theme_use('clam')

        style.configure(".", background=self.colors["bg"], foreground=self.colors["fg"], font=self.fonts["main"])
        style.configure("Card.TLabelframe", background=self.colors["panel_bg"], relief="flat", borderwidth=1)
        style.configure("Card.TLabelframe.Label", background=self.colors["panel_bg"], foreground=self.colors["accent"],
                        font=self.fonts["title"])

        style.configure("TButton", padding=8, relief="flat", background="#E0E0E0", foreground="#333333", borderwidth=0)
        style.map("TButton", background=[('active', '#D0D0D0'), ('disabled', '#F0F0F0')],
                  foreground=[('disabled', '#AAAAAA')])

        style.configure("Accent.TButton", background=self.colors["accent"], foreground="white", font=self.fonts["bold"])
        style.map("Accent.TButton", background=[('active', self.colors["accent_hover"]), ('disabled', '#A0CFFF')])

        style.configure("Danger.TButton", background=self.colors["stop"], foreground="white", font=self.fonts["bold"])
        style.map("Danger.TButton", background=[('active', self.colors["stop_hover"]), ('disabled', '#FFCCC7')])

        style.configure("TCheckbutton", background=self.colors["panel_bg"], font=self.fonts["main"],
                        indicatorcolor="white", indicatorrelief="flat")
        style.map("TCheckbutton", indicatorcolor=[('selected', self.colors["accent"])])

        style.configure("TEntry", fieldbackground="white", borderwidth=1, relief="solid", padding=5)
        style.configure("TLabel", background=self.colors["panel_bg"])
        style.configure("Main.TLabel", background=self.colors["bg"])

    def create_widgets(self):
        """Build the processing, training, and log panels."""
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_predict = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_predict, text='  🚀 Full Pipeline  ')
        self.setup_predict_tab(self.tab_predict)

        self.tab_train = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_train, text='  🛠️ Labeling & Training  ')
        self.setup_train_tab(self.tab_train)

        self.create_log_area(main_frame)

    def setup_predict_tab(self, parent):
        """Build the batch-processing tab."""
        content = ttk.Frame(parent)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)


        step_frame = ttk.LabelFrame(content, text="📋 Step Configuration", style="Card.TLabelframe", padding=15)
        step_frame.pack(fill=tk.X, pady=(0, 15))

        self.do_sort = tk.BooleanVar(value=False)
        self.do_balance = tk.BooleanVar(value=True)
        self.do_mask = tk.BooleanVar(value=True)
        self.do_predict = tk.BooleanVar(value=True)
        self.do_count = tk.BooleanVar(value=True)

        self.do_sort.trace_add('write', self.update_widget_states)
        self.do_predict.trace_add('write', self.update_widget_states)

        steps = [
            ("Step 0: Image Sorting", self.do_sort),
            ("Step 1: Light Balance", self.do_balance),
            ("Step 2: Microwell Extraction", self.do_mask),
            ("Step 3: AI Bead Prediction", self.do_predict),
            ("Step 4: Flu Statistics", self.do_count)
        ]

        for idx, (text, var) in enumerate(steps):
            cb = ttk.Checkbutton(step_frame, text=text, variable=var)
            cb.grid(row=0, column=idx, padx=15, sticky="w")


        path_frame = ttk.LabelFrame(content, text="📂 File Paths", style="Card.TLabelframe", padding=15)
        path_frame.pack(fill=tk.X, pady=5)

        self.path_source = tk.StringVar()
        self.path_bri = tk.StringVar()
        self.path_fluo = tk.StringVar()
        self.path_model = tk.StringVar()

        self.widgets['source'] = self._create_path_row(path_frame, "Main Folder (Mixed images):", self.path_source, 0,
                                                       mode='dir')
        self.widgets['bri'] = self._create_path_row(path_frame, "Brightfield Folder (bri):", self.path_bri, 1,
                                                    mode='dir')
        self.widgets['fluo'] = self._create_path_row(path_frame, "Fluorescence Folder (flu):", self.path_fluo, 2,
                                                     mode='dir')
        self.widgets['model'] = self._create_path_row(path_frame, "AI Model File (.pth):", self.path_model, 3,
                                                      mode='file')


        btn_frame = ttk.Frame(content)
        btn_frame.pack(fill=tk.X, pady=25)

        self.btn_run = ttk.Button(btn_frame, text="▶ Start Full Pipeline", style="Accent.TButton",
                                  command=self.run_process)
        self.btn_run.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 10))

        self.btn_stop = ttk.Button(btn_frame, text="⛔ Abort Task", style="Danger.TButton", command=self.abort_process,
                                   state='disabled')
        self.btn_stop.pack(side=tk.RIGHT, ipady=5)

        self.update_widget_states()

    def setup_train_tab(self, parent):
        """Build the labeling and training tab."""
        content = ttk.Frame(parent)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)


        lbl_frame = ttk.LabelFrame(content, text="🏷️ Dataset Creation", style="Card.TLabelframe", padding=15)
        lbl_frame.pack(fill=tk.X, pady=(0, 20))

        self.path_lbl_img = tk.StringVar()
        self._create_path_row(lbl_frame, "Single Brightfield Image (TIF):", self.path_lbl_img, 0, mode='file')

        self.path_lbl_mask = tk.StringVar()
        self._create_path_row(lbl_frame, "Corresponding Mask (TIF):", self.path_lbl_mask, 1, mode='file')

        self.path_lbl_csv = tk.StringVar()
        self._create_path_row(lbl_frame, "Append to CSV (Optional):", self.path_lbl_csv, 2, mode='file')

        ttk.Button(lbl_frame, text="▶ Start Labeling Tool", style="Accent.TButton",
                   command=self.start_labeling_tool).grid(row=3, column=1, pady=10, sticky="w")


        train_frame = ttk.LabelFrame(content, text="🧠 Model Training", style="Card.TLabelframe", padding=15)
        train_frame.pack(fill=tk.X)

        self.path_csv = tk.StringVar()
        self._create_path_row(train_frame, "Label File (CSV):", self.path_csv, 0, mode='file')

        self.path_pretrained = tk.StringVar()
        self._create_path_row(train_frame, "Pre-trained Weights (.pth):", self.path_pretrained, 1, mode='file')

        self.path_save_model = tk.StringVar()
        self._create_path_row(train_frame, "Model Save Path (.pth):", self.path_save_model, 2, mode='save')

        param_frame = ttk.Frame(train_frame)
        param_frame.grid(row=3, column=1, sticky="w", pady=5)

        ttk.Label(param_frame, text="Epochs:").pack(side=tk.LEFT, padx=(0, 5))
        self.var_epochs = tk.IntVar(value=30)
        ttk.Entry(param_frame, textvariable=self.var_epochs, width=8).pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(param_frame, text="Batch Size:").pack(side=tk.LEFT, padx=(0, 5))
        self.var_batch_size = tk.IntVar(value=16)
        ttk.Entry(param_frame, textvariable=self.var_batch_size, width=8).pack(side=tk.LEFT)

        ttk.Button(train_frame, text="▶ Start Training", style="Accent.TButton", command=self.start_training).grid(
            row=4, column=1, pady=10, sticky="w")

    def create_log_area(self, parent):
        """Create the read-only log panel."""
        log_frame = ttk.LabelFrame(parent, text="📝 System Logs", style="Card.TLabelframe", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(15, 0))

        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=10, state='disabled', font=self.fonts["log"],
            bg=self.colors["log_bg"], fg=self.colors["log_fg"],
            insertbackground="white", relief="flat", padx=10, pady=10
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _create_path_row(self, parent, label_text, variable, row, mode='file'):
        """Create a path entry with a browse button."""
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky='w', padx=5, pady=8)

        entry = ttk.Entry(parent, textvariable=variable, width=50)
        entry.grid(row=row, column=1, sticky='ew', padx=5)

        if mode == 'file':
            cmd = lambda: variable.set(filedialog.askopenfilename())
        elif mode == 'dir':
            cmd = lambda: variable.set(filedialog.askdirectory())
        elif mode == 'save':
            cmd = lambda: variable.set(filedialog.asksaveasfilename(
                defaultextension=".pth",
                filetypes=[("PyTorch Model", "*.pth"), ("All Files", "*.*")],
                title="Select path to save the model"
            ))
        else:
            cmd = lambda: None

        btn = ttk.Button(parent, text="📂 Browse...", command=cmd)
        btn.grid(row=row, column=2, padx=5)
        parent.columnconfigure(1, weight=1)

        return {'entry': entry, 'btn': btn}

    def update_widget_states(self, *args):
        """Enable path controls required by the selected steps."""
        if self.do_sort.get():
            self._set_state('source', 'normal')
            self._set_state('bri', 'disabled')
            self._set_state('fluo', 'disabled')
        else:
            self._set_state('source', 'disabled')
            self._set_state('bri', 'normal')
            self._set_state('fluo', 'normal')

        if self.do_predict.get():
            self._set_state('model', 'normal')
        else:
            self._set_state('model', 'disabled')

    def _set_state(self, key, state):
        w = self.widgets.get(key)
        if w:
            w['entry'].configure(state=state)
            w['btn'].configure(state=state)

    def start_labeling_tool(self):
        if not MODULES_LOADED or manual_labeling is None:
            messagebox.showerror("Error", "Labeling module not loaded! Ensure you are not running in Preview Mode.")
            return

        img_path = self.path_lbl_img.get()
        mask_path = self.path_lbl_mask.get()
        csv_path = self.path_lbl_csv.get()

        if not img_path or not mask_path:
            messagebox.showwarning("Warning", "Please select a [Brightfield Image] and its [Corresponding Mask]!")
            return

        output_folder = os.path.dirname(csv_path) if csv_path and os.path.exists(csv_path) else os.path.join(
            os.path.dirname(img_path), "dataset")

        print(f"\n--- Starting Labeling Tool ---")
        print(f"Brightfield Image: {img_path}")
        print(f"Output Directory: {output_folder}")
        if csv_path:
            print(f"Target CSV: {csv_path}")

        threading.Thread(
            target=self._run_labeling_thread,
            args=(img_path, mask_path, output_folder, csv_path),
            daemon=True
        ).start()

    def _run_labeling_thread(self, img_path, mask_path, output_folder, csv_path):
        try:

            manual_labeling.run_labeling(img_path, mask_path, output_folder, csv_path)
        except Exception:
            import traceback
            print(f"\n!!! Labeling Tool Error !!!\n{traceback.format_exc()}")

    def start_training(self):
        if not MODULES_LOADED or train_model is None:
            messagebox.showerror("Error", "Training module not loaded! Ensure you are not running in Preview Mode.")
            return

        csv_path = self.path_csv.get()
        pretrained_path = self.path_pretrained.get()
        model_path = self.path_save_model.get()

        if not csv_path or not model_path or not pretrained_path:
            messagebox.showwarning("Warning",
                                   "Please ensure [Label File (CSV)], [Pre-trained Weights], and [Model Save Path] are selected!")
            return

        try:
            epochs = self.var_epochs.get()
            batch_size = self.var_batch_size.get()
            if epochs <= 0 or batch_size <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Parameter Error", "Epochs and Batch Size must be positive integers!")
            return

        print(f"\n--- Preparing to Start Model Training ---")
        print(f"Dataset: {csv_path}")
        print(f"Pre-trained Weights: {pretrained_path}")
        print(f"Target Model: {model_path}")
        print(f"Parameters: Epochs={epochs}, BatchSize={batch_size}")
        print("Please monitor the console log for Epoch training progress...")

        threading.Thread(
            target=self._run_training_thread,
            args=(csv_path, model_path, pretrained_path, epochs, batch_size),
            daemon=True
        ).start()

    def _run_training_thread(self, csv_path, model_path, pretrained_path, epochs, batch_size):
        try:

            train_model.run_training(
                label_csv=csv_path,
                output_model_path=model_path,
                pretrained_weight_path=pretrained_path,
                epochs=epochs,
                batch_size=batch_size
            )
            self.root.after(0, lambda: messagebox.showinfo("Training Complete",
                                                           f"Model successfully saved to:\n{model_path}"))
        except Exception:
            import traceback
            print(f"\n!!! Model Training Error !!!\n{traceback.format_exc()}")
            self.root.after(0, lambda: messagebox.showerror("Training Failed", "Check the log window for details."))

    def run_process(self):
        if not MODULES_LOADED:
            messagebox.showwarning("Preview Mode", "No backend logic files detected. Cannot execute real processing.")
            return

        self.stop_event.clear()
        self.is_running = True
        self.btn_run.config(state='disabled')
        self.btn_stop.config(state='normal')
        threading.Thread(target=self._process_pipeline).start()

    def abort_process(self):
        if self.is_running and messagebox.askyesno("Confirm", "Are you sure you want to abort the current task?"):
            self.stop_event.set()
            print("\n!!! Sending abort signal... !!!")

    def _check_stop(self):
        if self.stop_event.is_set():
            raise InterruptedError("Stopped")

    def _process_pipeline(self):
        try:
            print(f"\n{'=' * 20} Task Started: {datetime.now().strftime('%H:%M:%S')} {'=' * 20}")

            source_dir = self.path_source.get()
            bri_dir = self.path_bri.get()
            fluo_dir = self.path_fluo.get()
            model_path = self.path_model.get()


            if self.do_sort.get():
                self._check_stop()
                print(f"\n--- [Step 0] Image Sorting and Organization ---")
                res_bri, res_fluo = image_classifier.organize_images(source_dir, stop_event=self.stop_event)

                if res_bri and res_fluo:
                    bri_dir, fluo_dir = res_bri, res_fluo
                    print(f"✅ Paths automatically updated to:\n  Brightfield: {bri_dir}\n  Fluorescence: {fluo_dir}")
                else:
                    raise InterruptedError("Image sorting aborted or no valid paths generated.")

            if not bri_dir:
                raise ValueError("Valid brightfield folder path not found. Cannot proceed.")

            current_working_root = os.path.dirname(bri_dir)
            bri_sol_dir = os.path.join(current_working_root, "bri_sol")
            bri_mask_dir = os.path.join(current_working_root, "bri_mask")
            bri_bead_dir = os.path.join(current_working_root, "bri_bead")


            if self.do_balance.get():
                self._check_stop()
                print(f"\n--- [Step 1] Light Field Balance ---")
                print(f"Input: {bri_dir}\nOutput: {bri_sol_dir}")
                light_balance.run_balance(bri_dir)


            if self.do_mask.get():
                self._check_stop()
                print(f"\n--- [Step 2] Microwell Mask Detection ---")
                if not os.path.exists(bri_sol_dir):
                    print("Warning: bri_sol folder not found. Ensure Step 1 is checked if running for the first time.")
                microwell_detection.run_detection(bri_sol_dir, bri_mask_dir)


            if self.do_predict.get():
                self._check_stop()
                print(f"\n--- [Step 3] AI Bead Classification ---")

                bead_prediction.run_prediction(bri_sol_dir, bri_mask_dir, model_path, stop_event=self.stop_event)


            if self.do_count.get():
                self._check_stop()
                print(f"\n--- [Step 4] Fluorescence Statistics ---")

                fluorescence_analysis.analyze_fluorescence(fluo_dir, bri_bead_dir)

            print(f"\n{'=' * 20} All Tasks Completed {'=' * 20}")
            messagebox.showinfo("Success", "All selected tasks have been completed!")

        except InterruptedError:
            print("\n!!! Task Aborted !!!")
            messagebox.showinfo("Aborted", "The task was aborted by the user.")
        except Exception as e:
            import traceback
            print(f"\n!!! Exception Occurred !!!\n{traceback.format_exc()}")
            messagebox.showerror("Error", f"Execution error: {str(e)}")
        finally:
            self.is_running = False
            self.btn_run.config(state='normal')
            self.btn_stop.config(state='disabled')


if __name__ == "__main__":
    multiprocessing.freeze_support()


    root = tk.Tk()
    try:
        root.iconbitmap('assets/1_256.ico')
    except Exception:
        pass

    app = BioAssayApp(root)
    root.mainloop()
