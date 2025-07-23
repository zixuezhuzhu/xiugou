import tkinter as tk
from tkinter import ttk, messagebox
import time
import random
import json
import os
from PIL import Image, ImageTk, ImageDraw, ImageFilter
import tkinter.simpledialog
import sys
import re

LAST_ACCOUNT_FILE = "last_account.json"

class PomodoroApp:
    def __init__(self, root):
        # ====== 账户相关 ======
        self.accounts_file = "accounts.json"
        self.current_account = None
        self.accounts = self.load_accounts()
        self.last_account = self.load_last_account()
        self.select_or_create_account()
        # ====== 基础参数与配色 ======
        self.root = root
        self.root.title("番茄钟奖励系统")
        self.bg_color = "#F6E7D8"  # 莫兰迪浅杏色
        self.blue_color = "#7EC8E3"  # 莫兰迪蓝
        self.btn_color = "#A3D8F4"  # 按钮蓝
        self.btn_fg = "#2D4059"  # 按钮字体色
        self.root.configure(bg=self.bg_color)
        self.work_time = 25*60
        self.break_time = 5*60
        self.time_left = self.work_time
        self.is_running = False
        self.is_working = True
        self.timer_id = None
        self.rewards = []
        self.collection = self.load_collection()  # collection依赖账户
        self.reward_images = []  # 保存图片引用，防止被回收
        self.reward_dir = "dopjpg"
        self.reward_list = [f for f in os.listdir(self.reward_dir) if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))]
        # 新增：循环次数相关
        self.total_cycles = 3
        self.last_set_cycles = 3
        self.cycles_left = 3
        # 绑定空格键切换暂停/继续
        self.root.bind('<space>', self.toggle_pause)
        # ====== 界面初始化 ======
        self.create_scrollable_area()  # 滚动与居中区域
        self.create_widgets()          # 主界面控件
        self.update_timer_display()    # 初始化计时器显示
        self.create_account_button()  # 新增：账户管理按钮持久化
        # ====== 抽卡券相关 ======
        self.gacha_ticket = self.load_gacha_ticket()
        self.last_signin_date = self.load_last_signin_date()

    # ====== 滚动与居中区域 ======
    def create_scrollable_area(self):
        self.outer_frame = tk.Frame(self.root, bg=self.bg_color)
        self.outer_frame.pack(fill='both', expand=True)
        self.canvas = tk.Canvas(self.outer_frame, bg=self.bg_color, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.outer_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.bg_color)
        self.scrollable_frame_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="center")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind('<Configure>', self._center_content)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        # 支持鼠标滚轮/触控板滚动
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)
        self.canvas.bind_all('<Shift-MouseWheel>', self._on_shift_mousewheel)
        self.canvas.bind_all('<Button-4>', self._on_mousewheel)  # Linux兼容
        self.canvas.bind_all('<Button-5>', self._on_mousewheel)  # Linux兼容

    def _center_content(self, event):
        canvas_width = event.width
        canvas_height = event.height
        self.canvas.coords(self.scrollable_frame_id, canvas_width/2, canvas_height/2)

    def _on_mousewheel(self, event):
        if event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")

    def _on_shift_mousewheel(self, event):
        if event.delta < 0:
            self.canvas.xview_scroll(1, "units")
        else:
            self.canvas.xview_scroll(-1, "units")

    # ====== 主界面控件 ======
    def create_widgets(self):
        self.create_timer_area()
        self.create_gacha_button()  # 抽卡按钮放在计时器下方
        self.create_settings_button()  # 新增：设置时间按钮
        # 初始化循环剩余标签，防止未定义报错
        self.cycle_left_label = tk.Label(self.scrollable_frame, text="", font=("楷体", 12), bg=self.bg_color, fg=self.btn_fg)
        self.cycle_left_label.pack(pady=2, anchor="center")
        self.cycle_left_label.config(text=f"剩余循环: {self.cycles_left}")
        self.create_button_area()
        self.create_reward_area()
        self.create_collection_area()
        # self.create_gacha_button()  # 移除原位置

    def create_settings_button(self):
        btn = tk.Button(self.scrollable_frame, text="设置时间", font=("楷体", 13), bg=self.btn_color, fg=self.btn_fg, command=self.open_settings_window)
        btn.pack(pady=5, anchor="center")

    def open_settings_window(self):
        win = tk.Toplevel(self.root)
        win.title("设置时间与循环")
        win.configure(bg=self.bg_color)
        win.geometry("320x180")
        win.resizable(False, False)
        # 工作时间
        tk.Label(win, text="工作(分钟):", font=("楷体", 12), bg=self.bg_color).place(x=30, y=20)
        work_var = tk.StringVar(value=str(self.work_time//60))
        tk.Entry(win, textvariable=work_var, width=6, font=("楷体", 12)).place(x=120, y=20)
        # 休息时间
        tk.Label(win, text="休息(分钟):", font=("楷体", 12), bg=self.bg_color).place(x=30, y=60)
        break_var = tk.StringVar(value=str(self.break_time//60))
        tk.Entry(win, textvariable=break_var, width=6, font=("楷体", 12)).place(x=120, y=60)
        # 循环次数
        tk.Label(win, text="循环次数:", font=("楷体", 12), bg=self.bg_color).place(x=30, y=100)
        cycle_var = tk.StringVar(value=str(self.total_cycles if hasattr(self, 'total_cycles') else 1))
        tk.Entry(win, textvariable=cycle_var, width=6, font=("楷体", 12)).place(x=120, y=100)
        # 应用按钮
        def apply():
            try:
                work = int(work_var.get())
                brk = int(break_var.get())
                cycles = int(cycle_var.get())
                if work <= 0 or brk < 0 or cycles <= 0:
                    raise ValueError
                self.work_time = work * 60
                self.break_time = brk * 60
                self.time_left = self.work_time
                self.total_cycles = cycles
                self.last_set_cycles = cycles  # 新增：记录上次设置
                self.cycles_left = cycles
                self.update_timer_display()
                if hasattr(self, 'cycle_left_label'):
                    self.cycle_left_label.config(text=f"剩余循环: {self.cycles_left}")
                self.status_label.config(text="设置已应用，准备开始工作", fg="black")
                win.destroy()
            except Exception:
                messagebox.showerror("输入错误", "请输入有效的数字（工作时间>0，休息时间>=0，循环次数>0）")
        tk.Button(win, text="应用设置", font=("楷体", 12), bg=self.btn_color, fg=self.btn_fg, command=apply).place(x=120, y=140)

    def create_timer_area(self):
        self.timer_label = tk.Label(self.scrollable_frame, font=("楷体", 48, "bold"), fg=self.blue_color, bg=self.bg_color)
        self.timer_label.pack(pady=30, anchor="center")
        self.status_label = tk.Label(self.scrollable_frame, font=("楷体", 18), fg=self.btn_fg, bg=self.bg_color)
        # self.status_label.pack(pady=10, anchor="center")  # 暂时不显示
        # 状态栏去掉“状态”二字，只保留内容
        self.state_frame = tk.Frame(self.scrollable_frame, bg=self.bg_color, bd=2, relief="ridge", highlightbackground=self.blue_color, highlightcolor=self.blue_color, highlightthickness=2)
        self.state_frame.pack(pady=5, anchor="center")
        self.state_text = tk.Label(self.state_frame, text="", font=("楷体", 14), bg=self.bg_color, fg=self.btn_fg)
        self.state_text.pack(padx=20, pady=5)
        self.update_state_text("待开始")

    def create_button_area(self):
        btn_frame = tk.Frame(self.scrollable_frame, bg=self.bg_color)
        btn_frame.pack(pady=10, anchor="center")
        # 开始按钮用#FFD580背景
        self.start_btn = tk.Button(btn_frame, text="🐶 开始", width=10, command=self.start_timer, font=("楷体", 14), bg="#FFD580", fg=self.btn_fg, relief="ridge", bd=3, highlightbackground=self.blue_color, highlightthickness=2)
        self.start_btn.pack(side=tk.LEFT, padx=10)
        self.pause_btn = tk.Button(btn_frame, text="🐾 暂停", width=10, command=self.pause_timer, state=tk.DISABLED, font=("楷体", 14), bg=self.btn_color, fg=self.btn_fg, relief="ridge", bd=3, highlightbackground=self.blue_color, highlightthickness=2)
        self.pause_btn.pack(side=tk.LEFT, padx=10)
        self.reset_btn = tk.Button(btn_frame, text="🦴 重置", width=10, command=self.reset_timer, font=("楷体", 14), bg=self.btn_color, fg=self.btn_fg, relief="ridge", bd=3, highlightbackground=self.blue_color, highlightthickness=2)
        self.reset_btn.pack(side=tk.LEFT, padx=10)
        # 结束计时按钮用self.btn_color背景，文字始终为结束计时
        self.finish_btn = tk.Button(btn_frame, text="⏹ 结束计时", width=12, command=self.early_finish, font=("楷体", 14), bg=self.btn_color, fg=self.btn_fg, relief="ridge", bd=3, highlightbackground=self.blue_color, highlightthickness=2)
        self.finish_btn.pack(side=tk.LEFT, padx=10)

    def create_reward_area(self):
        reward_frame = tk.LabelFrame(self.scrollable_frame, text="当前奖励", padx=20, pady=20, font=("楷体", 16, "bold"), fg=self.btn_fg, bg=self.bg_color, bd=4, relief="groove", highlightbackground=self.blue_color, highlightcolor=self.blue_color, highlightthickness=3, labelanchor='n')
        reward_frame.pack(pady=30, fill=tk.X, padx=40, anchor="center")
        self.reward_display = tk.Label(reward_frame, bg=self.bg_color)
        self.reward_display.pack(pady=10, anchor="center")

    def create_collection_area(self):
        collection_frame = tk.LabelFrame(self.scrollable_frame, text="收集册", padx=15, pady=15, font=("楷体", 14, "bold"), fg=self.btn_fg, bg=self.bg_color, bd=3, relief="ridge", highlightbackground=self.blue_color, highlightcolor=self.blue_color, highlightthickness=2, labelanchor='n')
        collection_frame.pack(pady=10, fill=tk.BOTH, expand=True, padx=40, anchor="center")
        self.collection_text = tk.Text(collection_frame, height=8, state=tk.DISABLED, font=("楷体", 12), bg="#F8F6F0", fg=self.btn_fg, bd=2, relief="flat")
        self.collection_text.pack(fill=tk.BOTH, expand=True)
        self.update_collection_display()
        # 清空收集进度按钮
        clear_btn = tk.Button(collection_frame, text="清空收集进度", font=("楷体", 11), bg="#FFB6B6", fg=self.btn_fg, command=self.clear_collection_progress)
        clear_btn.pack(pady=6, anchor="center")

    # ====== 抽卡系统入口按钮 ======
    def create_gacha_button(self):
        btn = tk.Button(self.scrollable_frame, text="抽卡系统", font=("楷体", 12, "bold"), bg="#F7C873", fg=self.btn_fg, command=self.open_gacha_window)
        btn.pack(pady=8, anchor="center")

    # ====== 抽卡界面设计 ======
    def open_gacha_window(self):
        win = tk.Toplevel(self.root)
        win.title("扭蛋抽卡")
        win.configure(bg=self.bg_color)
        win.geometry("500x650")
        win.resizable(False, False)
        # 统计行
        self.gacha_stat_label = tk.Label(win, text="", font=("楷体", 13), bg=self.bg_color, fg=self.btn_fg)
        self.gacha_stat_label.pack(pady=4, anchor="center")
        self.update_gacha_stat()
        # ====== 抽卡券数量显示在扭蛋图片上方 ======
        self.ticket_label = tk.Label(win, text=f"抽卡券：{self.gacha_ticket}", font=("楷体", 13, "bold"), bg=self.bg_color, fg=self.btn_fg, anchor="center")
        self.ticket_label.pack(pady=(8, 0), anchor="center")
        # 优先使用桌面dog文件夹下的niudan图片作为扭蛋图像
        niudan_path = os.path.join(os.getcwd(), "niudan.png")
        if not os.path.exists(niudan_path):
            niudan_path = os.path.join(os.getcwd(), "niudan.jpg")
        if not os.path.exists(niudan_path):
            niudan_path = os.path.join(os.getcwd(), "niudan.jpeg")
        if os.path.exists(niudan_path):
            img = Image.open(niudan_path).convert("RGBA")
            img = img.resize((160, 160))
            photo = ImageTk.PhotoImage(img)
            label_img = tk.Label(win, image=photo, bg=self.bg_color)
            label_img.image = photo  # 防止被回收
            label_img.pack(pady=10, anchor="center")
        else:
            # lucky文件夹图片池
            lucky_dir = "lucky"
            lucky_list = [f for f in os.listdir(lucky_dir) if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))]
            gacha_img_path = os.path.join(lucky_dir, lucky_list[0]) if lucky_list else None
            if gacha_img_path and os.path.exists(gacha_img_path):
                img = Image.open(gacha_img_path).convert("RGBA")
                img = img.resize((160, 160))
                photo = ImageTk.PhotoImage(img)
                label_img = tk.Label(win, image=photo, bg=self.bg_color)
                label_img.image = photo  # 防止被回收
                label_img.pack(pady=10, anchor="center")
            else:
                label_img = tk.Label(win, text="[扭蛋图像]", font=("楷体", 18), bg=self.bg_color, fg=self.btn_fg, width=16, height=8)
                label_img.pack(pady=10, anchor="center")
        # 签到按钮
        signin_btn = tk.Button(win, text="每日签到领抽卡券", font=("楷体", 11), bg="#B6E2D3", fg=self.btn_fg, command=self.daily_signin)
        signin_btn.pack(pady=2, anchor="center")
        # 抽一次、抽十次按钮
        btn_frame = tk.Frame(win, bg=self.bg_color)
        btn_frame.pack(pady=18, anchor="center")
        draw1_btn = tk.Button(btn_frame, text="抽一次", font=("楷体", 13), bg="#FFD580", fg=self.btn_fg, width=10)
        draw1_btn.pack(side=tk.LEFT, padx=12)
        draw10_btn = tk.Button(btn_frame, text="抽十次", font=("楷体", 13), bg="#FFD580", fg=self.btn_fg, width=10)
        draw10_btn.pack(side=tk.LEFT, padx=12)
        # 预留抽卡结果区域
        self.gacha_result_label = tk.Label(win, text="", font=("楷体", 12), bg=self.bg_color, fg=self.btn_fg)
        self.gacha_result_label.pack(pady=10, anchor="center")
        # 展示柜标题
        showcase_label = tk.Label(win, text="展示柜", font=("楷体", 13, "bold"), bg=self.bg_color, fg=self.btn_fg)
        showcase_label.pack(pady=4, anchor="center")
        # 展示柜滚动区域
        showcase_outer = tk.Frame(win, bg=self.bg_color)
        showcase_outer.pack(pady=4, fill=tk.BOTH, expand=False, padx=20)
        showcase_canvas = tk.Canvas(showcase_outer, bg=self.bg_color, highlightthickness=0, height=220)
        showcase_scrollbar = tk.Scrollbar(showcase_outer, orient="vertical", command=showcase_canvas.yview)
        showcase_canvas.pack(side="left", fill="both", expand=True)
        showcase_scrollbar.pack(side="right", fill="y")
        showcase_canvas.configure(yscrollcommand=showcase_scrollbar.set)
        showcase_frame = tk.Frame(showcase_canvas, bg=self.bg_color)
        showcase_window = showcase_canvas.create_window((0, 0), window=showcase_frame, anchor="nw")
        def _on_showcase_configure(event):
            showcase_canvas.configure(scrollregion=showcase_canvas.bbox("all"))
        showcase_frame.bind("<Configure>", _on_showcase_configure)
        def _on_mousewheel(event):
            if event.delta:
                showcase_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            elif event.num == 5:
                showcase_canvas.yview_scroll(1, "units")
            elif event.num == 4:
                showcase_canvas.yview_scroll(-1, "units")
        showcase_canvas.bind_all('<MouseWheel>', _on_mousewheel)
        showcase_canvas.bind_all('<Button-4>', _on_mousewheel)
        showcase_canvas.bind_all('<Button-5>', _on_mousewheel)
        self.gacha_showcase_images = []
        self.gacha_showcase_frame = showcase_frame
        self.gacha_showcase_canvas = showcase_canvas
        if not hasattr(self, 'gacha_history'):
            self.gacha_history = {}
        self.update_gacha_showcase()
        draw1_btn.config(command=lambda: self.try_gacha(1))
        draw10_btn.config(command=lambda: self.try_gacha(10))
        # 移除update_btn_state相关内容（如无用）

    def gacha_draw(self, times):
        # 新版：从lucky文件夹下五个子文件夹按概率抽取图片，含保底机制
        base_lucky_dir = os.path.join(os.getcwd(), "lucky")
        rarity_probs = {
            'N': 0.50,
            'R': 0.30,
            'SR': 0.15,
            'SSR': 0.049,
            'UR': 0.001
        }
        rarity_dirs = ['N', 'R', 'SR', 'SSR', 'UR']
        rarity_to_files = {}
        for r in rarity_dirs:
            subdir = os.path.join(base_lucky_dir, r)
            if os.path.exists(subdir):
                files = [f for f in os.listdir(subdir) if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))]
                rarity_to_files[r] = [os.path.join(subdir, f) for f in files]
            else:
                rarity_to_files[r] = []
        # 保底计数器
        if not hasattr(self, 'gacha_no_ssr_count'):
            self.gacha_no_ssr_count = 0
        if not hasattr(self, 'gacha_no_ur_count'):
            self.gacha_no_ur_count = 0
        results = []
        if times == 10:
            # 十连抽保底：至少获得1只SR及以上
            for _ in range(9):
                # 累计保底
                if self.gacha_no_ur_count >= 200 and rarity_to_files['UR']:
                    chosen_rarity = 'UR'
                    chosen_file = random.choice(rarity_to_files['UR'])
                    self.gacha_no_ur_count = 0
                    self.gacha_no_ssr_count += 1
                elif self.gacha_no_ssr_count >= 50 and rarity_to_files['SSR']:
                    chosen_rarity = 'SSR'
                    chosen_file = random.choice(rarity_to_files['SSR'])
                    self.gacha_no_ssr_count = 0
                    self.gacha_no_ur_count += 1
                else:
                    available = [r for r in rarity_dirs if rarity_to_files[r]]
                    available_probs = [rarity_probs[r] for r in available]
                    total = sum(available_probs)
                    norm_probs = [p/total for p in available_probs]
                    chosen_rarity = random.choices(available, weights=norm_probs, k=1)[0]
                    chosen_file = random.choice(rarity_to_files[chosen_rarity])
                results.append((chosen_rarity, chosen_file))
            # 判断前9次是否有SR及以上
            has_sr_or_higher = any(r in ['SR', 'SSR', 'UR'] for r, _ in results)
            if not has_sr_or_higher:
                # 第10次强制SR及以上
                pool = rarity_to_files['SR'] + rarity_to_files['SSR'] + rarity_to_files['UR']
                if pool:
                    chosen_file = random.choice(pool)
                    # 判断稀有度
                    for r in ['SR', 'SSR', 'UR']:
                        if chosen_file in rarity_to_files[r]:
                            chosen_rarity = r
                            break
                else:
                    # 没有SR及以上，正常抽
                    available = [r for r in rarity_dirs if rarity_to_files[r]]
                    available_probs = [rarity_probs[r] for r in available]
                    total = sum(available_probs)
                    norm_probs = [p/total for p in available_probs]
                    chosen_rarity = random.choices(available, weights=norm_probs, k=1)[0]
                    chosen_file = random.choice(rarity_to_files[chosen_rarity])
                results.append((chosen_rarity, chosen_file))
            else:
                # 第10次正常抽
                if self.gacha_no_ur_count >= 200 and rarity_to_files['UR']:
                    chosen_rarity = 'UR'
                    chosen_file = random.choice(rarity_to_files['UR'])
                    self.gacha_no_ur_count = 0
                    self.gacha_no_ssr_count += 1
                elif self.gacha_no_ssr_count >= 50 and rarity_to_files['SSR']:
                    chosen_rarity = 'SSR'
                    chosen_file = random.choice(rarity_to_files['SSR'])
                    self.gacha_no_ssr_count = 0
                    self.gacha_no_ur_count += 1
                else:
                    available = [r for r in rarity_dirs if rarity_to_files[r]]
                    available_probs = [rarity_probs[r] for r in available]
                    total = sum(available_probs)
                    norm_probs = [p/total for p in available_probs]
                    chosen_rarity = random.choices(available, weights=norm_probs, k=1)[0]
                    chosen_file = random.choice(rarity_to_files[chosen_rarity])
                results.append((chosen_rarity, chosen_file))
        else:
            for _ in range(times):
                # 累计保底
                if self.gacha_no_ur_count >= 200 and rarity_to_files['UR']:
                    chosen_rarity = 'UR'
                    chosen_file = random.choice(rarity_to_files['UR'])
                    self.gacha_no_ur_count = 0
                    self.gacha_no_ssr_count += 1
                elif self.gacha_no_ssr_count >= 50 and rarity_to_files['SSR']:
                    chosen_rarity = 'SSR'
                    chosen_file = random.choice(rarity_to_files['SSR'])
                    self.gacha_no_ssr_count = 0
                    self.gacha_no_ur_count += 1
                else:
                    available = [r for r in rarity_dirs if rarity_to_files[r]]
                    available_probs = [rarity_probs[r] for r in available]
                    total = sum(available_probs)
                    norm_probs = [p/total for p in available_probs]
                    chosen_rarity = random.choices(available, weights=norm_probs, k=1)[0]
                    chosen_file = random.choice(rarity_to_files[chosen_rarity])
                results.append((chosen_rarity, chosen_file))
        # 更新保底计数
        for rarity, _ in results:
            if rarity == 'UR':
                self.gacha_no_ur_count = 0
                self.gacha_no_ssr_count += 1
            elif rarity == 'SSR':
                self.gacha_no_ssr_count = 0
                self.gacha_no_ur_count += 1
            else:
                self.gacha_no_ssr_count += 1
                self.gacha_no_ur_count += 1
        # 显示结果
        display_names = [os.path.splitext(os.path.basename(f))[0] for _, f in results]
        self.gacha_result_label.config(text=f"获得奖励: {', '.join(display_names)}")
        # 展示图片（只在抽奖系统内展示，不影响主界面）
        if results:
            try:
                img = Image.open(results[-1][1]).convert("RGBA")
                img = img.resize((128, 128))
                photo = ImageTk.PhotoImage(img)
                self.gacha_showcase_images.append(photo)  # 只用于展示柜
                # 不再调用self.reward_display.config，避免影响主界面
            except Exception:
                pass
        # 统计历史奖励，key为绝对路径
        if not hasattr(self, 'gacha_history'):
            self.gacha_history = {}
        for rarity, img_file in results:
            key = os.path.abspath(img_file)
            self.gacha_history[key] = self.gacha_history.get(key, 0) + 1
        # 统计各稀有度获得数量
        if not hasattr(self, 'gacha_rarity_count'):
            self.gacha_rarity_count = {r: 0 for r in rarity_dirs}
        for rarity, _ in results:
            self.gacha_rarity_count[rarity] = self.gacha_rarity_count.get(rarity, 0) + 1
        self.update_gacha_showcase()
        self.update_gacha_stat()

    def update_gacha_showcase(self):
        # 展示柜奖励按UR、SSR、SR、R、N顺序排序
        if not hasattr(self, 'gacha_showcase_frame') or not hasattr(self, 'gacha_history'):
            return
        frame = self.gacha_showcase_frame
        for widget in frame.winfo_children():
            widget.destroy()
        self.gacha_showcase_images.clear()
        thumb_size = 72
        # 先构建稀有度映射
        rarity_order = ['UR', 'SSR', 'SR', 'R', 'N']
        def get_rarity_from_path(img_path):
            # 路径中包含/UR/、/SSR/等
            for r in rarity_order:
                if os.sep + r + os.sep in img_path or (os.sep + r.lower() + os.sep) in img_path:
                    return r
            # 兼容旧数据
            name = os.path.basename(img_path).upper()
            for r in rarity_order:
                if name.startswith(r):
                    return r
            return 'N'
        # 按稀有度分组
        rarity_to_items = {r: [] for r in rarity_order}
        for img_path, count in self.gacha_history.items():
            rarity = get_rarity_from_path(img_path)
            rarity_to_items[rarity].append((img_path, count))
        # 按顺序合并
        sorted_items = []
        for r in rarity_order:
            sorted_items.extend(rarity_to_items[r])
        # 展示
        for idx, (img_path, count) in enumerate(sorted_items):
            try:
                img = Image.open(img_path).convert("RGBA")
                img = img.resize((thumb_size, thumb_size))
                photo = ImageTk.PhotoImage(img)
                self.gacha_showcase_images.append(photo)
                sub_frame = tk.Frame(frame, bg=self.bg_color)
                sub_frame.grid(row=idx//5, column=idx%5, padx=6, pady=6)
                label_img = tk.Label(sub_frame, image=photo, bg=self.bg_color)
                label_img.pack()
                label_count = tk.Label(sub_frame, text=f"*{count}", font=("楷体", 9), bg=self.bg_color, fg=self.btn_fg)
                label_count.pack()
            except Exception as e:
                continue
        self.update_gacha_stat()

    def update_gacha_stat(self):
        # 统计每个等级获得数量，纯文本显示，按gacha_rarity_count
        if not hasattr(self, 'gacha_rarity_count'):
            self.gacha_rarity_count = {'N':0, 'R':0, 'SR':0, 'SSR':0, 'UR':0}
        stat_text = '  '.join([f"{r}: {self.gacha_rarity_count.get(r,0)}" for r in ['N','R','SR','SSR','UR']])
        if hasattr(self, 'gacha_stat_label'):
            self.gacha_stat_label.config(text=stat_text, font=("楷体", 13))

    # ====== 账户管理 ======
    def load_accounts(self):
        if os.path.exists(self.accounts_file):
            try:
                with open(self.accounts_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_accounts(self):
        with open(self.accounts_file, "w", encoding="utf-8") as f:
            json.dump(self.accounts, f, ensure_ascii=False)

    def load_last_account(self):
        if os.path.exists(LAST_ACCOUNT_FILE):
            try:
                with open(LAST_ACCOUNT_FILE, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except:
                return None
        return None

    def save_last_account(self, account):
        try:
            with open(LAST_ACCOUNT_FILE, "w", encoding="utf-8") as f:
                f.write(account)
        except Exception as e:
            pass

    def select_or_create_account(self):
        # 弹窗选择或新建账户
        if not self.accounts:
            self.create_new_account()
        else:
            # 优先自动登录上次账户
            account_names = list(self.accounts.keys())
            if self.last_account and self.last_account in self.accounts:
                self.current_account = self.last_account
            else:
                account = tkinter.simpledialog.askstring("选择账户", f"已有账户：{', '.join(account_names)}\n输入新账户名或选择已有账户：", initialvalue=account_names[0])
                if account is None or account.strip() == "":
                    account = account_names[0]
                if account not in self.accounts:
                    self.accounts[account] = {"collection": {}}
                    self.save_accounts()
                self.current_account = account
            self.save_last_account(self.current_account)

    def create_new_account(self):
        while True:
            account = tkinter.simpledialog.askstring("新建账户", "请输入新账户名：")
            if account is None:
                account = "默认账户"
            account = account.strip()
            if account == "":
                continue
            if account in self.accounts:
                messagebox.showerror("错误", "账户名已存在！")
                continue
            self.accounts[account] = {"collection": {}}
            self.save_accounts()
            self.current_account = account
            self.save_last_account(account)
            break

    def create_account_button(self):
        btn = tk.Button(self.scrollable_frame, text="账户管理", font=("楷体", 12), bg=self.btn_color, fg=self.btn_fg, command=self.account_manage_window)
        btn.pack(pady=2, anchor="center")

    def account_manage_window(self):
        win = tk.Toplevel(self.root)
        win.title("账户管理")
        win.configure(bg=self.bg_color)
        win.geometry("300x220")
        win.resizable(False, False)
        tk.Label(win, text="当前账户：" + self.current_account, font=("楷体", 13), bg=self.bg_color).pack(pady=10)
        # 账户列表
        frame = tk.Frame(win, bg=self.bg_color)
        frame.pack(pady=5)
        for name in self.accounts:
            def switch_account(n=name):
                self.current_account = n
                self.collection = self.load_collection()
                self.update_collection_display()
                self.update_state_text("待开始")
                self.update_title()
                self.save_last_account(n)
                win.destroy()
            btn = tk.Button(frame, text=name, font=("楷体", 11), bg="#E0F7FA" if name==self.current_account else self.btn_color, fg=self.btn_fg, command=switch_account)
            btn.pack(pady=2, fill=tk.X)
        # 新建账户按钮
        def new_account():
            win.destroy()
            self.create_new_account()
            self.collection = self.load_collection()
            self.update_collection_display()
            self.update_state_text("待开始")
            self.update_title()
            self.save_last_account(self.current_account)
        tk.Button(win, text="新建账户", font=("楷体", 12), bg=self.btn_color, fg=self.btn_fg, command=new_account).pack(pady=10)

    def update_title(self):
        base_title = "番茄钟奖励系统"
        state = self.state_text.cget("text") if hasattr(self, 'state_text') else ""
        self.root.title(f"{base_title} - {self.current_account} - {state}")

    # ====== 奖励与收集逻辑 ======
    def load_collection(self):
        if self.current_account and self.current_account in self.accounts:
            data = self.accounts[self.current_account].get("collection", {})
            # 兼容老数据
            for k, v in list(data.items()):
                if isinstance(v, int):
                    data[k] = {"count": v, "stage": 1}
            return data
        return {}

    def save_collection(self):
        if self.current_account:
            self.accounts[self.current_account]["collection"] = self.collection
            self.save_accounts()

    def give_reward(self):
        """给予随机奖励（图片），满10进化"""
        reward_file = random.choice(self.reward_list)
        # 读取当前stage
        info = self.collection.get(reward_file, {"count": 0, "stage": 1})
        count = info["count"]
        stage = info["stage"]
        # 进化判断
        if count + 1 >= 10:
            # 进化到下一阶段
            stage += 1
            count = 0
        else:
            count += 1
        self.collection[reward_file] = {"count": count, "stage": stage}
        self.save_collection()
        self.update_collection_display()
        # 显示奖励图片（按stage）
        if stage == 1:
            reward_path = os.path.join(self.reward_dir, reward_file)
        else:
            name, ext = os.path.splitext(reward_file)
            lv2_file = f"{name} lv2{ext}"
            reward_path = os.path.join("dogjpg2", lv2_file)
        img = Image.open(reward_path).convert("RGBA")
        img = self.rounded_image_with_shadow(img, radius=32, shadow_offset=8)
        img = img.resize((128, 128))
        photo = ImageTk.PhotoImage(img)
        self.reward_images.append(photo)
        self.reward_display.config(image=photo, text="")
        # self.rewards.append(reward_file)  # 不再单独维护
        # 完成一次番茄钟工作时间奖励1张抽卡券
        self.gacha_ticket += 1
        self.save_gacha_ticket()
        if hasattr(self, 'ticket_label'):
            self.ticket_label.config(text=f"抽卡券：{self.gacha_ticket}")

    def update_collection_display(self):
        """更新收集册显示为缩略图"""
        self.collection_text.pack_forget()
        if hasattr(self, 'collection_thumb_frame'):
            self.collection_thumb_frame.destroy()
        parent = self.collection_text.master
        self.collection_thumb_frame = tk.Frame(parent, bg=self.bg_color)
        self.collection_thumb_frame.pack(fill=tk.BOTH, expand=True, anchor="center")
        if not self.collection:
            label = tk.Label(self.collection_thumb_frame, text="收集册为空\n完成番茄钟获得奖励吧！", font=("楷体", 14), bg=self.bg_color, fg=self.btn_fg)
            label.pack(pady=20, anchor="center")
            return
        thumb_size = 64
        col = 0
        row = 0
        self.collection_thumbs = []
        for reward_file, info in self.collection.items():
            count = info["count"]
            stage = info["stage"]
            name = os.path.splitext(reward_file)[0]
            # 根据stage选择图片路径
            if stage == 1:
                img_path = os.path.join(self.reward_dir, reward_file)
            else:
                name, ext = os.path.splitext(reward_file)
                lv2_file = f"{name} lv2{ext}"
                img_path = os.path.join("dogjpg2", lv2_file)
            try:
                img = Image.open(img_path).convert("RGBA")
                img = self.rounded_image_with_shadow(img, radius=12, shadow_offset=4)
                img = img.resize((thumb_size, thumb_size))
                photo = ImageTk.PhotoImage(img)
                self.collection_thumbs.append(photo)
                frame = tk.Frame(self.collection_thumb_frame, bg=self.bg_color)
                frame.grid(row=row, column=col, padx=12, pady=12, sticky="nsew")
                label_img = tk.Label(frame, image=photo, bg=self.bg_color)
                label_img.pack(anchor="center")
                # 第一行：文件名（根据stage变化）
                if stage == 1:
                    display_name = name
                else:
                    display_name = f"lv{stage} {name}"
                label_name = tk.Label(frame, text=display_name, font=("楷体", 11), bg=self.bg_color, fg=self.btn_fg)
                label_name.pack(anchor="center")
                # 第二行：进度条
                bar_len = 10
                filled = min(count, bar_len)
                empty = bar_len - filled
                bar = "■" * filled + "□" * empty
                bar_text = f"{bar} {count}/10"
                label_bar = tk.Label(frame, text=bar_text, font=("Consolas", 10), bg=self.bg_color, fg=self.btn_fg)
                label_bar.pack(anchor="center")
                col += 1
                if col >= 4:
                    col = 0
                    row += 1
            except Exception as e:
                continue
        for i in range(4):
            self.collection_thumb_frame.grid_columnconfigure(i, weight=1)

    # ====== 清空收集进度功能 ======
    def clear_collection_progress(self):
        if messagebox.askyesno("确认清空", "确定要清空当前账户的奖励收集进度吗？此操作不可恢复！"):
            self.collection = {}
            self.save_collection()
            messagebox.showinfo("已清空", "收集进度已清空！")

    # ====== 计时器与流程控制 ======
    def update_timer_display(self):
        minutes = self.time_left // 60
        seconds = self.time_left % 60
        self.timer_label.config(text=f"{minutes:02d}:{seconds:02d}")

    def update_state_text(self, state):
        self.state_text.config(text=state)
        # 同步窗口标题
        self.update_title()

    def start_timer(self):
        if not self.is_running:
            self.is_running = True
            self.start_btn.config(state=tk.DISABLED)
            self.pause_btn.config(state=tk.NORMAL)
            # 状态切换为赚狗时间或休息时间
            if self.is_working:
                self.update_state_text("赚狗时间")
            else:
                self.update_state_text("休息时间")
            self.run_timer()

    def pause_timer(self):
        if self.is_running:
            self.is_running = False
            self.start_btn.config(state=tk.NORMAL)
            self.pause_btn.config(state=tk.DISABLED)
            if self.timer_id:
                self.root.after_cancel(self.timer_id)
            self.update_state_text("暂停中")

    def reset_timer(self):
        self.pause_timer()
        self.is_working = True
        self.time_left = self.work_time
        self.cycles_left = self.last_set_cycles  # 用上次设置的循环数
        self.update_timer_display()
        # self.status_label.config(text="准备开始工作", fg="black")  # 暂时不显示
        if hasattr(self, 'cycle_left_label'):
            self.cycle_left_label.config(text=f"剩余循环: {self.cycles_left}")
        self.update_state_text("待开始")

    def run_timer(self):
        if self.is_running:
            if self.time_left > 0:
                self.time_left -= 1
                self.update_timer_display()
                self.timer_id = self.root.after(1000, self.run_timer)
            else:
                self.timer_completed()

    def timer_completed(self):
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.pause_btn.config(state=tk.DISABLED)
        if self.is_working:
            self.give_reward()
            self.is_working = False
            self.time_left = self.break_time
            self.status_label.config(text="休息时间！", fg="green")
            self.update_state_text("休息时间")
            self.finish_btn.config(text="⏹ 结束计时")
            messagebox.showinfo("完成！", "工作阶段完成！获得一个奖励！")
        else:
            self.cycles_left -= 1
            if self.cycles_left > 0:
                self.is_working = True
                self.time_left = self.work_time
                self.status_label.config(text="工作时间", fg="red")
                self.update_state_text("赚狗时间")
                self.finish_btn.config(text="⏹ 结束计时")
                if hasattr(self, 'cycle_left_label'):
                    self.cycle_left_label.config(text=f"剩余循环: {self.cycles_left}")
                messagebox.showinfo("完成！", "休息结束，回到工作！")
            else:
                self.status_label.config(text="全部循环已完成！", fg="blue")
                self.update_state_text("已完成")
                if hasattr(self, 'cycle_left_label'):
                    self.cycle_left_label.config(text="剩余循环: 0")
                messagebox.showinfo("恭喜！", "所有循环已完成！可以休息啦~")
                # 新增：自动重置循环数，恢复初始状态，等待用户点击开始
                self.is_working = True
                self.time_left = self.work_time
                self.cycles_left = self.last_set_cycles
                self.update_timer_display()
                if hasattr(self, 'cycle_left_label'):
                    self.cycle_left_label.config(text=f"剩余循环: {self.cycles_left}")
                self.update_state_text("待开始")
                # 不自动开始，等待用户点击“开始”
        self.update_timer_display()

    def early_finish(self):
        if self.is_running:
            if self.timer_id:
                self.root.after_cancel(self.timer_id)
            self.is_running = False
            if self.is_working:
                self.give_reward()
                self.is_working = False
                self.time_left = self.break_time
                self.status_label.config(text="休息时间！", fg="green")
                self.update_timer_display()
                self.is_running = True
                self.start_btn.config(state=tk.DISABLED)
                self.pause_btn.config(state=tk.NORMAL)
                self.update_state_text("休息时间")
                self.run_timer()
            else:
                self.cycles_left -= 1
                if self.cycles_left > 0:
                    self.is_working = True
                    self.time_left = self.work_time
                    self.status_label.config(text="工作时间", fg="red")
                    self.update_timer_display()
                    if hasattr(self, 'cycle_left_label'):
                        self.cycle_left_label.config(text=f"剩余循环: {self.cycles_left}")
                    self.is_running = True
                    self.start_btn.config(state=tk.DISABLED)
                    self.pause_btn.config(state=tk.NORMAL)
                    self.update_state_text("赚狗时间")
                    self.run_timer()
                else:
                    self.is_working = True
                    self.time_left = self.work_time
                    self.status_label.config(text="全部循环已完成！", fg="blue")
                    self.update_timer_display()
                    if hasattr(self, 'cycle_left_label'):
                        self.cycle_left_label.config(text="剩余循环: 0")
                    self.is_running = False
                    self.start_btn.config(state=tk.NORMAL)
                    self.pause_btn.config(state=tk.DISABLED)
                    self.update_state_text("已完成")
                    # 新增：自动重置循环数，恢复初始状态，等待用户点击开始
                    self.cycles_left = self.last_set_cycles
                    self.is_working = True
                    self.time_left = self.work_time
                    if hasattr(self, 'cycle_left_label'):
                        self.cycle_left_label.config(text=f"剩余循环: {self.cycles_left}")
                    self.update_state_text("待开始")
            self.finish_btn.config(text="⏹ 结束计时")

    def toggle_pause(self, event=None):
        if self.is_running:
            self.pause_timer()
        else:
            # 只有在未运行但有剩余时间时才继续
            if self.time_left > 0 and self.start_btn['state'] == tk.NORMAL:
                self.start_timer()

    # ====== 图片处理工具 ======
    def rounded_image_with_shadow(self, img, radius=32, shadow_offset=8):
        mask = Image.new("L", img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([0, 0, img.size[0], img.size[1]], radius, fill=255)
        rounded = Image.new("RGBA", img.size)
        rounded.paste(img, (0, 0), mask=mask)
        shadow = Image.new("RGBA", (img.size[0]+shadow_offset*2, img.size[1]+shadow_offset*2), (0,0,0,0))
        shadow_mask = Image.new("L", (img.size[0], img.size[1]), 0)
        shadow_draw = ImageDraw.Draw(shadow_mask)
        shadow_draw.rounded_rectangle([0, 0, img.size[0], img.size[1]], radius, fill=180)
        shadow.paste((50,50,50,90), (shadow_offset, shadow_offset), mask=shadow_mask)
        final_img = Image.new("RGBA", shadow.size, (0,0,0,0))
        final_img.paste(shadow, (0,0))
        final_img.paste(rounded, (shadow_offset, shadow_offset), mask=rounded)
        return final_img

    def load_gacha_ticket(self):
        try:
            if os.path.exists('gacha_ticket.json'):
                with open('gacha_ticket.json', 'r', encoding='utf-8') as f:
                    return int(f.read().strip())
        except:
            pass
        return 0

    def save_gacha_ticket(self):
        try:
            with open('gacha_ticket.json', 'w', encoding='utf-8') as f:
                f.write(str(self.gacha_ticket))
        except:
            pass

    def load_last_signin_date(self):
        try:
            if os.path.exists('last_signin_date.txt'):
                with open('last_signin_date.txt', 'r', encoding='utf-8') as f:
                    return f.read().strip()
        except:
            pass
        return None

    def save_last_signin_date(self, date_str):
        try:
            with open('last_signin_date.txt', 'w', encoding='utf-8') as f:
                f.write(date_str)
        except:
            pass

    def try_gacha(self, times):
        if self.gacha_ticket < times:
            # 弹窗以抽奖窗口为父窗口，彻底避免主界面抢占焦点
            gacha_win = self.gacha_showcase_canvas.winfo_toplevel() if hasattr(self, 'gacha_showcase_canvas') else self.root
            def close_tip():
                top.destroy()
                gacha_win.lift()
                gacha_win.focus_force()
            top = tk.Toplevel(gacha_win)
            top.title("抽卡券不足")
            top.configure(bg=self.bg_color)
            top.geometry("280x120")
            top.resizable(False, False)
            tk.Label(top, text=f"需要{times}张抽卡券，当前仅有{self.gacha_ticket}张！", font=("楷体", 12), bg=self.bg_color, fg=self.btn_fg, wraplength=260).pack(pady=20)
            tk.Button(top, text="知道了", font=("楷体", 12), bg=self.btn_color, fg=self.btn_fg, command=close_tip).pack(pady=8)
            top.transient(gacha_win)
            top.lift()  # 保证弹窗在抽奖窗口之上
            return
        self.gacha_ticket -= times
        self.save_gacha_ticket()
        if hasattr(self, 'ticket_label'):
            self.ticket_label.config(text=f"抽卡券：{self.gacha_ticket}")
        self.gacha_draw(times)

    def daily_signin(self):
        import datetime
        today = datetime.date.today().isoformat()
        if self.last_signin_date == today:
            # 修改：自定义弹窗，父窗口为抽奖窗口，点击后不切换主界面
            gacha_win = self.gacha_showcase_canvas.winfo_toplevel() if hasattr(self, 'gacha_showcase_canvas') else self.root
            def close_tip():
                top.destroy()
                gacha_win.lift()
                gacha_win.focus_force()
            top = tk.Toplevel(gacha_win)
            top.title("已签到")
            top.configure(bg=self.bg_color)
            top.geometry("280x120")
            top.resizable(False, False)
            tk.Label(top, text="今天已经签到过啦！", font=("楷体", 12), bg=self.bg_color, fg=self.btn_fg, wraplength=260).pack(pady=20)
            tk.Button(top, text="知道了", font=("楷体", 12), bg=self.btn_color, fg=self.btn_fg, command=close_tip).pack(pady=8)
            top.transient(gacha_win)
            top.lift()  # 保证弹窗在抽奖窗口之上
            return
        self.gacha_ticket += 1
        self.save_gacha_ticket()
        self.last_signin_date = today
        self.save_last_signin_date(today)
        if hasattr(self, 'ticket_label'):
            self.ticket_label.config(text=f"抽卡券：{self.gacha_ticket}")
        messagebox.showinfo("签到成功", "获得1张抽卡券！")

if __name__ == "__main__":
    root = tk.Tk()
    app = PomodoroApp(root)
    root.mainloop()