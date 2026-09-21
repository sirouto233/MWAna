import os


# 在导入 OpenCV 及业务模块前设置日志等级。
os.environ["OPENCV_LOG_LEVEL"] = "FATAL"

import sys
import threading
import multiprocessing
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox


try:
    from logic_zh import image_classifier
    from logic_zh import light_balance
    from logic_zh import microwell_detection
    from logic_zh import bead_prediction
    from logic_zh import fluorescence_analysis
    from logic_zh import manual_labeling
    from logic_zh import train_model

    MODULES_LOADED = True
except ImportError as e:
    print(f"注意：运行在 UI 预览模式 (缺少逻辑模块: {e})")
    MODULES_LOADED = False
    image_classifier = light_balance = microwell_detection = None
    bead_prediction = fluorescence_analysis = manual_labeling = train_model = None


class TextRedirector:
    """将日志写入原输出流，并调度至 Tkinter 文本框。"""

    def __init__(self, widget, original_stream, tag="stdout"):
        self.widget = widget
        self.original_stream = original_stream
        self.tag = tag

    def write(self, str_msg):

        try:
            if self.original_stream:
                self.original_stream.write(str_msg)
                self.original_stream.flush()
        except Exception:
            pass


        try:
            self.widget.after(0, self._write_to_widget, str_msg)
        except Exception:
            pass

    def _write_to_widget(self, str_msg):
        try:
            self.widget.configure(state="normal")
            self.widget.insert("end", str_msg, (self.tag,))
            self.widget.see("end")
            self.widget.configure(state="disabled")
        except Exception:
            pass

    def flush(self):
        try:
            if self.original_stream:
                self.original_stream.flush()
        except Exception:
            pass


class BioAssayApp:
    """微坑磁珠识别与荧光统计桌面界面。"""

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
            "main": ("微软雅黑", 10), "bold": ("微软雅黑", 10, "bold"),
            "title": ("微软雅黑", 11, "bold"), "log": ("微软雅黑", 10)
        }

        self.setup_styles()
        self.root.configure(bg=self.colors["bg"])

        self.stop_event = threading.Event()
        self.is_running = False
        self.widgets = {}

        self.create_widgets()


        # 保留原输出流以同步控制台日志。
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr


        sys.stdout = TextRedirector(self.log_text, self.original_stdout)
        sys.stderr = TextRedirector(self.log_text, self.original_stderr)

        if not MODULES_LOADED:
            print(">>>以此模式启动仅供预览 UI，逻辑功能不可用<<<")

    def setup_styles(self):
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
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_predict = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_predict, text='  🚀 全流程处理  ')
        self.setup_predict_tab(self.tab_predict)

        self.tab_train = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_train, text='  🛠️ 打标与训练  ')
        self.setup_train_tab(self.tab_train)

        self.create_log_area(main_frame)

    def setup_predict_tab(self, parent):
        content = ttk.Frame(parent)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        step_frame = ttk.LabelFrame(content, text="📋 步骤配置", style="Card.TLabelframe", padding=15)
        step_frame.pack(fill=tk.X, pady=(0, 15))

        self.do_sort = tk.BooleanVar(value=False)
        self.do_balance = tk.BooleanVar(value=True)
        self.do_mask = tk.BooleanVar(value=True)
        self.do_predict = tk.BooleanVar(value=True)
        self.do_count = tk.BooleanVar(value=True)

        self.do_sort.trace_add('write', self.update_widget_states)
        self.do_predict.trace_add('write', self.update_widget_states)

        steps = [
            ("Step 0: 图像分类/整理", self.do_sort),
            ("Step 1: 光场平衡处理", self.do_balance),
            ("Step 2: 微坑 Mask 识别", self.do_mask),
            ("Step 3: AI 磁珠分类预测", self.do_predict),
            ("Step 4: 荧光强度统计", self.do_count)
        ]

        for idx, (text, var) in enumerate(steps):
            cb = ttk.Checkbutton(step_frame, text=text, variable=var)
            cb.grid(row=0, column=idx, padx=15, sticky="w")

        path_frame = ttk.LabelFrame(content, text="📂 文件路径", style="Card.TLabelframe", padding=15)
        path_frame.pack(fill=tk.X, pady=5)

        self.path_source = tk.StringVar()
        self.path_bri = tk.StringVar()
        self.path_fluo = tk.StringVar()
        self.path_model = tk.StringVar()

        self.widgets['source'] = self._create_path_row(path_frame, "主文件夹 (含混杂图片):", self.path_source, 0,
                                                       mode='dir')
        self.widgets['bri'] = self._create_path_row(path_frame, "明场文件夹 (bri):", self.path_bri, 1, mode='dir')
        self.widgets['fluo'] = self._create_path_row(path_frame, "荧光文件夹 (flu):", self.path_fluo, 2, mode='dir')
        self.widgets['model'] = self._create_path_row(path_frame, "AI 模型文件 (.pth):", self.path_model, 3,
                                                      mode='file')

        btn_frame = ttk.Frame(content)
        btn_frame.pack(fill=tk.X, pady=25)

        self.btn_run = ttk.Button(btn_frame, text="▶ 启动全流程处理", style="Accent.TButton", command=self.run_process)
        self.btn_run.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 10))

        self.btn_stop = ttk.Button(btn_frame, text="⛔ 中止任务", style="Danger.TButton", command=self.abort_process,
                                   state='disabled')
        self.btn_stop.pack(side=tk.RIGHT, ipady=5)

        self.update_widget_states()

    def setup_train_tab(self, parent):
        content = ttk.Frame(parent)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)


        lbl_frame = ttk.LabelFrame(content, text="🏷️ 数据集制作", style="Card.TLabelframe", padding=15)
        lbl_frame.pack(fill=tk.X, pady=(0, 20))

        self.path_lbl_img = tk.StringVar()
        self._create_path_row(lbl_frame, "单张明场图 (TIF):", self.path_lbl_img, 0, mode='file')

        self.path_lbl_mask = tk.StringVar()
        self._create_path_row(lbl_frame, "对应Mask图 (TIF):", self.path_lbl_mask, 1, mode='file')

        self.path_lbl_csv = tk.StringVar()
        self._create_path_row(lbl_frame, "追加至已有CSV (选填):", self.path_lbl_csv, 2, mode='file')

        ttk.Button(lbl_frame, text="▶ 启动打标工具", style="Accent.TButton", command=self.start_labeling_tool).grid(
            row=3, column=1, pady=10, sticky="w")


        train_frame = ttk.LabelFrame(content, text="🧠 模型训练", style="Card.TLabelframe", padding=15)
        train_frame.pack(fill=tk.X)

        self.path_csv = tk.StringVar()
        self._create_path_row(train_frame, "标签文件 (CSV):", self.path_csv, 0, mode='file')

        self.path_pretrained = tk.StringVar()
        self._create_path_row(train_frame, "预训练权重 (.pth):", self.path_pretrained, 1, mode='file')

        self.path_save_model = tk.StringVar()
        self._create_path_row(train_frame, "模型保存路径 (.pth):", self.path_save_model, 2, mode='save')

        param_frame = ttk.Frame(train_frame)
        param_frame.grid(row=3, column=1, sticky="w", pady=5)

        ttk.Label(param_frame, text="Epoch (训练轮数):").pack(side=tk.LEFT, padx=(0, 5))
        self.var_epochs = tk.IntVar(value=30)
        ttk.Entry(param_frame, textvariable=self.var_epochs, width=8).pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(param_frame, text="Batch Size (批次大小):").pack(side=tk.LEFT, padx=(0, 5))
        self.var_batch_size = tk.IntVar(value=16)
        ttk.Entry(param_frame, textvariable=self.var_batch_size, width=8).pack(side=tk.LEFT)

        ttk.Button(train_frame, text="▶ 开始训练", style="Accent.TButton", command=self.start_training).grid(row=4,
                                                                                                             column=1,
                                                                                                             pady=10,
                                                                                                             sticky="w")

    def create_log_area(self, parent):
        log_frame = ttk.LabelFrame(parent, text="📝 系统日志", style="Card.TLabelframe", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(15, 0))

        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=10, state='disabled', font=self.fonts["log"],
            bg=self.colors["log_bg"], fg=self.colors["log_fg"],
            insertbackground="white", relief="flat", padx=10, pady=10
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _create_path_row(self, parent, label_text, variable, row, mode='file'):
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
                filetypes=[("PyTorch Model", "*.pth"), ("所有文件", "*.*")],
                title="选择保存模型的位置"
            ))
        else:
            cmd = lambda: None

        btn = ttk.Button(parent, text="📂 浏览...", command=cmd)
        btn.grid(row=row, column=2, padx=5)
        parent.columnconfigure(1, weight=1)

        return {'entry': entry, 'btn': btn}

    def update_widget_states(self, *args):
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
            messagebox.showerror("错误", "打标模块未加载！请确保已在非预览模式下运行。")
            return

        img_path = self.path_lbl_img.get()
        mask_path = self.path_lbl_mask.get()
        csv_path = self.path_lbl_csv.get()

        if not img_path or not mask_path:
            messagebox.showwarning("提示", "请务必选择【明场图】及其对应的【Mask图】！")
            return

        output_folder = os.path.dirname(csv_path) if csv_path and os.path.exists(csv_path) else os.path.join(
            os.path.dirname(img_path), "dataset")

        print(f"\n--- 正在启动打标工具 ---")
        print(f"明场图: {img_path}")
        print(f"输出目录: {output_folder}")
        if csv_path:
            print(f"目标CSV: {csv_path}")

        threading.Thread(
            target=self._run_labeling_thread,
            args=(img_path, mask_path, output_folder, csv_path),
            daemon=True
        ).start()

    def _run_labeling_thread(self, img_path, mask_path, output_folder, csv_path):
        try:
            manual_labeling.run_labeling_tool(img_path, mask_path, output_folder, csv_path)
        except Exception:
            import traceback
            print(f"\n!!! 打标工具运行出错 !!!\n{traceback.format_exc()}")

    def start_training(self):
        if not MODULES_LOADED or train_model is None:
            messagebox.showerror("错误", "训练模块未加载！请确保已在非预览模式下运行。")
            return

        csv_path = self.path_csv.get()
        pretrained_path = self.path_pretrained.get()
        model_path = self.path_save_model.get()

        if not csv_path or not model_path or not pretrained_path:
            messagebox.showwarning("提示", "请务必选择【标签文件(CSV)】、【预训练权重】并设置【模型保存路径】！")
            return

        try:
            epochs = self.var_epochs.get()
            batch_size = self.var_batch_size.get()
            if epochs <= 0 or batch_size <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("参数错误", "Epoch 和 Batch Size 必须为正整数！")
            return

        print(f"\n--- 准备启动模型训练 ---")
        print(f"数据集: {csv_path}")
        print(f"预训练权重: {pretrained_path}")
        print(f"目标模型: {model_path}")
        print(f"参数: Epoch={epochs}, BatchSize={batch_size}")
        print("请注意观察控制台日志中的 Epoch 训练进度...")

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
            self.root.after(0, lambda: messagebox.showinfo("训练完成", f"模型已成功保存至:\n{model_path}"))
        except Exception:
            import traceback
            print(f"\n!!! 模型训练出错 !!!\n{traceback.format_exc()}")
            self.root.after(0, lambda: messagebox.showerror("训练失败", "详细信息请查看日志框。"))

    def run_process(self):
        if not MODULES_LOADED:
            messagebox.showwarning("演示模式", "未检测到后台逻辑文件，无法执行真实处理。")
            return

        self.stop_event.clear()
        self.is_running = True
        self.btn_run.config(state='disabled')
        self.btn_stop.config(state='normal')
        threading.Thread(target=self._process_pipeline).start()

    def abort_process(self):
        if self.is_running and messagebox.askyesno("确认", "要中止当前任务吗？"):
            self.stop_event.set()
            print("\n!!! 正在发送中止信号... !!!")

    def _check_stop(self):
        if self.stop_event.is_set():
            raise InterruptedError("Stopped")

    def _process_pipeline(self):
        try:
            print(f"\n{'=' * 20} 任务开始: {datetime.now().strftime('%H:%M:%S')} {'=' * 20}")

            source_dir = self.path_source.get()
            bri_dir = self.path_bri.get()
            fluo_dir = self.path_fluo.get()
            model_path = self.path_model.get()


            if self.do_sort.get():
                self._check_stop()
                print(f"\n--- [Step 0] 图像分类与整理 ---")
                res_bri, res_fluo = image_classifier.organize_images(source_dir, stop_event=self.stop_event)

                if res_bri and res_fluo:
                    bri_dir, fluo_dir = res_bri, res_fluo
                    print(f"✅ 路径自动更新为:\n  明场: {bri_dir}\n  荧光: {fluo_dir}")
                else:
                    raise InterruptedError("图像分类被中止或未生成有效路径")

            if not bri_dir:
                raise ValueError("未获取到有效的明场文件夹路径，无法继续。")

            current_working_root = os.path.dirname(bri_dir)
            bri_sol_dir = os.path.join(current_working_root, "bri_sol")
            bri_mask_dir = os.path.join(current_working_root, "bri_mask")
            bri_bead_dir = os.path.join(current_working_root, "bri_bead")


            if self.do_balance.get():
                self._check_stop()
                print(f"\n--- [Step 1] 光场平衡 ---")
                print(f"输入: {bri_dir}\n输出: {bri_sol_dir}")
                light_balance.run_balance(bri_dir)


            if self.do_mask.get():
                self._check_stop()
                print(f"\n--- [Step 2] 微坑 Mask 识别 ---")
                if not os.path.exists(bri_sol_dir):
                    print("警告：未找到 bri_sol 文件夹，如果是首次运行，请务必勾选 Step 1。")
                microwell_detection.run_detection(bri_sol_dir, bri_mask_dir)


            if self.do_predict.get():
                self._check_stop()
                print(f"\n--- [Step 3] AI 磁珠分类 ---")
                bead_prediction.run_prediction(bri_sol_dir, bri_mask_dir, model_path, stop_event=self.stop_event)


            if self.do_count.get():
                self._check_stop()
                print(f"\n--- [Step 4] 荧光统计 ---")
                fluorescence_analysis.run_fluo_analysis(fluo_dir, bri_bead_dir)

            print(f"\n{'=' * 20} 任务全部完成 {'=' * 20}")
            messagebox.showinfo("成功", "所有选定任务已完成！")

        except InterruptedError:
            print("\n!!! 任务已中止 !!!")
            messagebox.showinfo("中止", "任务已被用户中止。")
        except Exception as e:
            import traceback
            print(f"\n!!! 发生异常 !!!\n{traceback.format_exc()}")
            messagebox.showerror("错误", f"运行出错: {str(e)}")
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
