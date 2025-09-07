import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from tkinterdnd2 import DND_FILES, TkinterDnD
import threading
import os
from datetime import datetime
from pathlib import Path
import queue
from typing import List, Dict, Any, Optional

from config_manager import ConfigManager
from s3_client import S3Client

class S3GUI:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.s3_client = None
        self.current_prefix = ""
        self.selected_items = []
        self.upload_queue = queue.Queue()
        self.download_queue = queue.Queue()
        
        self.setup_ui()
        self.connect_s3()
    
    def setup_ui(self):
        self.root = TkinterDnD.Tk()
        self.root.title("S3 文件管理器")
        
        ui_settings = self.config_manager.get_ui_settings()
        self.root.geometry(f"{ui_settings['window_width']}x{ui_settings['window_height']}")
        
        self.create_menu()
        self.create_toolbar()
        self.create_main_frame()
        self.create_status_bar()
        
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_drop)
    
    def create_menu(self):
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)
        
        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="上传文件", command=self.upload_files_dialog)
        file_menu.add_command(label="上传文件夹", command=self.upload_folder_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="新建文件夹", command=self.create_new_folder)
        file_menu.add_separator()
        file_menu.add_command(label="重命名", command=self.rename_selected)
        file_menu.add_command(label="下载", command=self.download_selected)
        file_menu.add_command(label="删除", command=self.delete_selected)
        file_menu.add_separator()
        file_menu.add_command(label="刷新", command=self.refresh_view)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        settings_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="设置", menu=settings_menu)
        settings_menu.add_command(label="连接设置", command=self.show_connection_settings)
    
    def create_toolbar(self):
        self.toolbar = ttk.Frame(self.root)
        self.toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(self.toolbar, text="返回上级", command=self.go_parent).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="刷新", command=self.refresh_view).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        ttk.Button(self.toolbar, text="上传文件", command=self.upload_files_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="上传文件夹", command=self.upload_folder_dialog).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        ttk.Button(self.toolbar, text="新建文件夹", command=self.create_new_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="重命名", command=self.rename_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="下载", command=self.download_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="删除", command=self.delete_selected).pack(side=tk.LEFT, padx=2)
        
        self.path_label = ttk.Label(self.toolbar, text="路径: /")
        self.path_label.pack(side=tk.RIGHT, padx=10)
    
    def create_main_frame(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ("name", "type", "size", "modified")
        self.tree = ttk.Treeview(self.main_frame, columns=columns, show='tree headings')
        
        self.tree.heading("#0", text="名称", anchor=tk.W)
        self.tree.heading("name", text="名称", anchor=tk.W)
        self.tree.heading("type", text="类型", anchor=tk.W)
        self.tree.heading("size", text="大小", anchor=tk.W)
        self.tree.heading("modified", text="修改时间", anchor=tk.W)
        
        self.tree.column("#0", width=300)
        self.tree.column("name", width=0)
        self.tree.column("type", width=80)
        self.tree.column("size", width=100)
        self.tree.column("modified", width=150)
        
        self.tree_scrollbar = ttk.Scrollbar(self.main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.tree_scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree_scrollbar.grid(row=0, column=1, sticky="ns")
        
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)
        
        self.create_sorting_frame()
    
    def create_sorting_frame(self):
        self.sort_frame = ttk.Frame(self.main_frame)
        self.sort_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        
        ttk.Label(self.sort_frame, text="排序:").pack(side=tk.LEFT)
        
        self.sort_var = tk.StringVar(value="name")
        sort_options = [("名称", "name"), ("类型", "type"), ("大小", "size"), ("时间", "modified")]
        
        for text, value in sort_options:
            ttk.Radiobutton(self.sort_frame, text=text, variable=self.sort_var, 
                           value=value, command=self.sort_items).pack(side=tk.LEFT, padx=5)
        
        self.sort_desc_var = tk.BooleanVar()
        ttk.Checkbutton(self.sort_frame, text="降序", variable=self.sort_desc_var,
                       command=self.sort_items).pack(side=tk.LEFT, padx=10)
    
    def create_status_bar(self):
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.status_label = ttk.Label(self.status_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.status_frame, variable=self.progress_var, 
                                           maximum=100, length=200)
        self.progress_bar.pack(side=tk.RIGHT, padx=10)
    
    def connect_s3(self):
        if not self.config_manager.is_configured():
            self.show_connection_settings()
            return
        
        self.status_label.config(text="连接中...")
        self.s3_client = S3Client(self.config_manager)
        
        if self.s3_client.test_connection():
            self.status_label.config(text="已连接")
            self.refresh_view()
        else:
            self.status_label.config(text="连接失败")
            messagebox.showerror("连接错误", "无法连接到S3存储，请检查配置")
    
    def refresh_view(self):
        if not self.s3_client:
            return
        
        self.tree.delete(*self.tree.get_children())
        self.status_label.config(text="加载中...")
        self.progress_var.set(0)
        
        def progress_callback(page_count, current_count, has_more):
            self.root.after(0, lambda: self.status_label.config(
                text=f"正在加载第{page_count}页... 已加载{current_count}个项目" + ("，还有更多..." if has_more else "")
            ))
        
        def load_objects():
            try:
                folders, files = self.s3_client.list_objects(self.current_prefix, progress_callback=progress_callback)
                self.root.after(0, self.populate_tree, folders, files)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"加载失败: {e}"))
                self.root.after(0, lambda: self.status_label.config(text="加载失败"))
        
        threading.Thread(target=load_objects, daemon=True).start()
    
    def populate_tree(self, folders: List[Dict], files: List[Dict]):
        self.current_items = folders + files
        self.sort_items()
        self.path_label.config(text=f"路径: /{self.current_prefix}")
        
        # 检查是否达到了最大文件数限制
        max_objects = self.config_manager.get_app_settings().get('max_list_objects', 10000)
        total_items = len(folders) + len(files)
        
        if total_items >= max_objects:
            self.status_label.config(text=f"加载完成 - {len(folders)}个文件夹, {len(files)}个文件 (已达到最大显示数量)")
        else:
            self.status_label.config(text=f"加载完成 - {len(folders)}个文件夹, {len(files)}个文件")
    
    def sort_items(self):
        if not hasattr(self, 'current_items'):
            return
        
        self.tree.delete(*self.tree.get_children())
        
        sort_key = self.sort_var.get()
        reverse = self.sort_desc_var.get()
        
        folders = [item for item in self.current_items if item['type'] == 'folder']
        files = [item for item in self.current_items if item['type'] == 'file']
        
        def get_sort_key(item):
            if sort_key == "name":
                return item['name'].lower()
            elif sort_key == "type":
                return item['type']
            elif sort_key == "size":
                return item.get('size', 0)
            elif sort_key == "modified":
                return item.get('last_modified', datetime.min)
            return item['name'].lower()
        
        folders.sort(key=get_sort_key, reverse=reverse)
        files.sort(key=get_sort_key, reverse=reverse)
        
        for folder in folders:
            self.tree.insert("", "end", text=f"📁 {folder['name']}", 
                           values=("", "文件夹", "", ""), tags=("folder",))
        
        for file in files:
            size_str = self.format_size(file['size'])
            time_str = file['last_modified'].strftime("%Y-%m-%d %H:%M")
            self.tree.insert("", "end", text=f"📄 {file['name']}", 
                           values=("", "文件", size_str, time_str), tags=("file",))
    
    def format_size(self, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def on_double_click(self, event):
        item = self.tree.selection()[0]
        item_text = self.tree.item(item, "text")
        
        if item_text.startswith("📁"):
            folder_name = item_text[2:]
            if self.current_prefix:
                self.current_prefix = f"{self.current_prefix}{folder_name}/"
            else:
                self.current_prefix = f"{folder_name}/"
            self.refresh_view()
    
    def go_parent(self):
        if self.current_prefix:
            self.current_prefix = "/".join(self.current_prefix.rstrip("/").split("/")[:-1])
            if self.current_prefix and not self.current_prefix.endswith("/"):
                self.current_prefix += "/"
            self.refresh_view()
    
    def on_drop(self, event):
        files = self.root.tk.splitlist(event.data)
        for file_path in files:
            if os.path.isdir(file_path):
                self.upload_folder(file_path)
            else:
                self.upload_file(file_path)
    
    def upload_files_dialog(self):
        files = filedialog.askopenfilenames(title="选择要上传的文件")
        for file_path in files:
            self.upload_file(file_path)
    
    def upload_folder_dialog(self):
        folder_path = filedialog.askdirectory(title="选择要上传的文件夹")
        if folder_path:
            self.upload_folder(folder_path)
    
    def upload_file(self, file_path: str):
        if not self.s3_client:
            messagebox.showerror("错误", "未连接到S3")
            return
        
        filename = os.path.basename(file_path)
        s3_key = f"{self.current_prefix}{filename}"
        
        def upload_thread():
            def progress_callback(progress):
                self.root.after(0, lambda: self.progress_var.set(progress))
                self.root.after(0, lambda: self.status_label.config(text=f"上传中: {progress:.1f}%"))
            
            success = self.s3_client.upload_file(file_path, s3_key, progress_callback)
            
            self.root.after(0, lambda: self.progress_var.set(0))
            if success:
                self.root.after(0, lambda: self.status_label.config(text="上传完成"))
                self.root.after(0, self.refresh_view)
            else:
                self.root.after(0, lambda: messagebox.showerror("错误", f"上传失败: {filename}"))
        
        threading.Thread(target=upload_thread, daemon=True).start()
    
    def upload_folder(self, folder_path: str):
        if not self.s3_client:
            messagebox.showerror("错误", "未连接到S3")
            return
        
        folder_name = os.path.basename(folder_path)
        s3_prefix = f"{self.current_prefix}{folder_name}"
        
        def upload_thread():
            def progress_callback(progress):
                self.root.after(0, lambda: self.progress_var.set(progress))
                self.root.after(0, lambda: self.status_label.config(text=f"上传文件夹: {progress:.1f}%"))
            
            success_count, total_count = self.s3_client.upload_folder(folder_path, s3_prefix, progress_callback)
            
            self.root.after(0, lambda: self.progress_var.set(0))
            self.root.after(0, lambda: self.status_label.config(text=f"上传完成: {success_count}/{total_count}"))
            self.root.after(0, self.refresh_view)
        
        threading.Thread(target=upload_thread, daemon=True).start()
    
    def download_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请选择要下载的项目")
            return
        
        download_path = filedialog.askdirectory(title="选择下载目录")
        if not download_path:
            return
        
        for item in selected:
            item_text = self.tree.item(item, "text")
            if item_text.startswith("📁"):
                folder_name = item_text[2:]
                s3_prefix = f"{self.current_prefix}{folder_name}/"
                local_folder = os.path.join(download_path, folder_name)
                self.download_folder(s3_prefix, local_folder)
            else:
                file_name = item_text[2:]
                s3_key = f"{self.current_prefix}{file_name}"
                local_path = os.path.join(download_path, file_name)
                self.download_file(s3_key, local_path)
    
    def download_file(self, s3_key: str, local_path: str):
        def download_thread():
            def progress_callback(progress):
                self.root.after(0, lambda: self.progress_var.set(progress))
                self.root.after(0, lambda: self.status_label.config(text=f"下载中: {progress:.1f}%"))
            
            success = self.s3_client.download_file(s3_key, local_path, progress_callback)
            
            self.root.after(0, lambda: self.progress_var.set(0))
            if success:
                self.root.after(0, lambda: self.status_label.config(text="下载完成"))
            else:
                self.root.after(0, lambda: messagebox.showerror("错误", f"下载失败: {s3_key}"))
        
        threading.Thread(target=download_thread, daemon=True).start()
    
    def download_folder(self, s3_prefix: str, local_folder: str):
        def download_thread():
            def progress_callback(progress):
                self.root.after(0, lambda: self.progress_var.set(progress))
                self.root.after(0, lambda: self.status_label.config(text=f"下载文件夹: {progress:.1f}%"))
            
            success_count, total_count = self.s3_client.download_folder(s3_prefix, local_folder, progress_callback)
            
            self.root.after(0, lambda: self.progress_var.set(0))
            self.root.after(0, lambda: self.status_label.config(text=f"下载完成: {success_count}/{total_count}"))
        
        threading.Thread(target=download_thread, daemon=True).start()
    
    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请选择要删除的项目")
            return
        
        if not messagebox.askyesno("确认删除", f"确定要删除选中的 {len(selected)} 个项目吗？"):
            return
        
        def delete_thread():
            deleted_items = 0
            total_items = len(selected)
            
            for i, item in enumerate(selected):
                item_text = self.tree.item(item, "text")
                
                if item_text.startswith("📁"):
                    folder_name = item_text[2:]
                    s3_prefix = f"{self.current_prefix}{folder_name}/"
                    
                    # 文件夹删除进度回调
                    def folder_progress_callback(phase, current, total, message, idx=i, fname=folder_name, titems=total_items):
                        if phase == "scan":
                            self.root.after(0, lambda: self.status_label.config(
                                text=f"[{idx+1}/{titems}] 删除文件夹 '{fname}': {message}"
                            ))
                        elif phase == "delete":
                            if total > 0:
                                folder_progress = (current / total) * 100
                                self.root.after(0, lambda p=folder_progress: self.progress_var.set(p))
                                self.root.after(0, lambda m=message: self.status_label.config(
                                    text=f"[{idx+1}/{titems}] 删除文件夹 '{fname}': {m}"
                                ))
                        elif phase == "complete":
                            self.root.after(0, lambda m=message: self.status_label.config(
                                text=f"[{idx+1}/{titems}] 文件夹 '{fname}' {m}"
                            ))
                        elif phase == "error":
                            self.root.after(0, lambda m=message: self.status_label.config(
                                text=f"[{idx+1}/{titems}] 删除文件夹 '{fname}' 失败: {m}"
                            ))
                    
                    success_count, _ = self.s3_client.delete_folder(s3_prefix, folder_progress_callback)
                    if success_count > 0:
                        deleted_items += 1
                else:
                    file_name = item_text[2:]
                    s3_key = f"{self.current_prefix}{file_name}"
                    
                    self.root.after(0, lambda idx=i, fname=file_name, titems=total_items: self.status_label.config(
                        text=f"[{idx+1}/{titems}] 删除文件: {fname}"
                    ))
                    
                    if self.s3_client.delete_object(s3_key):
                        deleted_items += 1
                        self.root.after(0, lambda idx=i, fname=file_name, titems=total_items: self.status_label.config(
                            text=f"[{idx+1}/{titems}] 文件 '{fname}' 删除成功"
                        ))
                    else:
                        self.root.after(0, lambda idx=i, fname=file_name, titems=total_items: self.status_label.config(
                            text=f"[{idx+1}/{titems}] 文件 '{fname}' 删除失败"
                        ))
                
                # 更新总体进度
                overall_progress = ((i + 1) / total_items) * 100
                if not item_text.startswith("📁"):  # 只在文件删除时更新进度条，文件夹删除有自己的进度
                    self.root.after(0, lambda p=overall_progress: self.progress_var.set(p))
            
            # 完成所有删除操作
            self.root.after(0, lambda: self.progress_var.set(0))
            self.root.after(0, lambda: self.status_label.config(text=f"删除完成: {deleted_items}/{total_items} 个项目"))
            self.root.after(0, self.refresh_view)
        
        threading.Thread(target=delete_thread, daemon=True).start()
    
    def create_new_folder(self):
        """新建文件夹"""
        if not self.s3_client:
            messagebox.showerror("错误", "未连接到S3")
            return
        
        folder_name = tk.simpledialog.askstring("新建文件夹", "请输入文件夹名称:")
        if not folder_name:
            return
        
        # 检查文件夹名称是否合法
        if '/' in folder_name or '\\' in folder_name:
            messagebox.showerror("错误", "文件夹名称不能包含 / 或 \\ 字符")
            return
        
        folder_path = f"{self.current_prefix}{folder_name}/"
        
        def create_thread():
            success = self.s3_client.create_folder(folder_path)
            
            if success:
                self.root.after(0, lambda: self.status_label.config(text="文件夹创建成功"))
                self.root.after(0, self.refresh_view)
            else:
                self.root.after(0, lambda: messagebox.showerror("错误", f"创建文件夹失败: {folder_name}"))
        
        threading.Thread(target=create_thread, daemon=True).start()
    
    def rename_selected(self):
        """重命名选中的文件或文件夹"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("提示", "请选择要重命名的项目")
            return
        
        if len(selected) > 1:
            messagebox.showwarning("提示", "一次只能重命名一个项目")
            return
        
        if not self.s3_client:
            messagebox.showerror("错误", "未连接到S3")
            return
        
        item = selected[0]
        item_text = self.tree.item(item, "text")
        
        # 获取当前名称（去掉图标）
        if item_text.startswith("📁"):
            current_name = item_text[2:]
            is_folder = True
        else:
            current_name = item_text[2:]
            is_folder = False
        
        # 弹出重命名对话框
        new_name = tk.simpledialog.askstring("重命名", f"请输入新名称:", initialvalue=current_name)
        if not new_name or new_name == current_name:
            return
        
        # 检查名称是否合法
        if '/' in new_name or '\\' in new_name:
            messagebox.showerror("错误", "名称不能包含 / 或 \\ 字符")
            return
        
        def rename_thread():
            if is_folder:
                # 重命名文件夹
                old_prefix = f"{self.current_prefix}{current_name}/"
                new_prefix = f"{self.current_prefix}{new_name}/"
                
                success_count, total_count = self.s3_client.rename_folder(old_prefix, new_prefix)
                
                if success_count > 0:
                    self.root.after(0, lambda: self.status_label.config(text=f"文件夹重命名完成: {success_count}/{total_count}"))
                    self.root.after(0, self.refresh_view)
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", f"重命名文件夹失败: {current_name}"))
            else:
                # 重命名文件
                old_key = f"{self.current_prefix}{current_name}"
                new_key = f"{self.current_prefix}{new_name}"
                
                success = self.s3_client.rename_object(old_key, new_key)
                
                if success:
                    self.root.after(0, lambda: self.status_label.config(text="文件重命名成功"))
                    self.root.after(0, self.refresh_view)
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", f"重命名文件失败: {current_name}"))
        
        threading.Thread(target=rename_thread, daemon=True).start()
    
    def show_context_menu(self, event):
        try:
            item = self.tree.identify_row(event.y)
            if item:
                self.tree.selection_set(item)
                
                context_menu = tk.Menu(self.root, tearoff=0)
                context_menu.add_command(label="重命名", command=self.rename_selected)
                context_menu.add_separator()
                context_menu.add_command(label="下载", command=self.download_selected)
                context_menu.add_command(label="删除", command=self.delete_selected)
                context_menu.add_separator()
                context_menu.add_command(label="属性", command=self.show_properties)
                
                context_menu.tk_popup(event.x_root, event.y_root)
        except:
            pass
    
    def show_properties(self):
        selected = self.tree.selection()
        if not selected:
            return
        
        item = selected[0]
        item_text = self.tree.item(item, "text")
        
        if not item_text.startswith("📁"):
            file_name = item_text[2:]
            s3_key = f"{self.current_prefix}{file_name}"
            
            info = self.s3_client.get_object_info(s3_key)
            if info:
                props_text = f"""文件名: {file_name}
路径: {s3_key}
大小: {self.format_size(info['size'])}
修改时间: {info['last_modified'].strftime('%Y-%m-%d %H:%M:%S')}
内容类型: {info['content_type']}
ETag: {info['etag']}"""
                
                props_window = tk.Toplevel(self.root)
                props_window.title("文件属性")
                props_window.geometry("400x200")
                
                text_widget = tk.Text(props_window, wrap=tk.WORD)
                text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                text_widget.insert(tk.END, props_text)
                text_widget.config(state=tk.DISABLED)
    
    def show_connection_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("连接设置")
        settings_window.geometry("500x350")
        settings_window.resizable(False, False)
        
        s3_config = self.config_manager.get_s3_config()
        app_settings = self.config_manager.get_app_settings()
        
        ttk.Label(settings_window, text="S3 端点:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        endpoint_var = tk.StringVar(value=s3_config.get('endpoint', ''))
        ttk.Entry(settings_window, textvariable=endpoint_var, width=60).grid(row=0, column=1, padx=10, pady=5)
        
        ttk.Label(settings_window, text="存储桶:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        bucket_var = tk.StringVar(value=s3_config.get('bucket', ''))
        ttk.Entry(settings_window, textvariable=bucket_var, width=60).grid(row=1, column=1, padx=10, pady=5)
        
        ttk.Label(settings_window, text="访问密钥:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        access_key_var = tk.StringVar(value=s3_config.get('access_key', ''))
        ttk.Entry(settings_window, textvariable=access_key_var, width=60).grid(row=2, column=1, padx=10, pady=5)
        
        ttk.Label(settings_window, text="秘密密钥:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        secret_key_var = tk.StringVar(value=s3_config.get('secret_key', ''))
        secret_entry = ttk.Entry(settings_window, textvariable=secret_key_var, width=60, show="*")
        secret_entry.grid(row=3, column=1, padx=10, pady=5)
        
        ttk.Label(settings_window, text="区域:").grid(row=4, column=0, sticky="w", padx=10, pady=5)
        region_var = tk.StringVar(value=s3_config.get('region', 'auto'))
        ttk.Entry(settings_window, textvariable=region_var, width=60).grid(row=4, column=1, padx=10, pady=5)
        
        # 添加分隔线
        ttk.Separator(settings_window, orient=tk.HORIZONTAL).grid(row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        
        # 添加应用设置
        ttk.Label(settings_window, text="最大文件数:").grid(row=6, column=0, sticky="w", padx=10, pady=5)
        max_objects_var = tk.StringVar(value=str(app_settings.get('max_list_objects', 10000)))
        max_objects_entry = ttk.Entry(settings_window, textvariable=max_objects_var, width=20)
        max_objects_entry.grid(row=6, column=1, sticky="w", padx=10, pady=5)
        ttk.Label(settings_window, text="(单个文件夹最多显示的文件数量)").grid(row=6, column=1, sticky="e", padx=10, pady=5)
        
        def test_connection():
            temp_config = self.config_manager.config.copy()
            temp_config['s3_config'] = {
                'endpoint': endpoint_var.get(),
                'bucket': bucket_var.get(),
                'access_key': access_key_var.get(),
                'secret_key': secret_key_var.get(),
                'region': region_var.get()
            }
            
            temp_config_manager = ConfigManager.__new__(ConfigManager)
            temp_config_manager.config = temp_config
            temp_s3_client = S3Client(temp_config_manager)
            
            if temp_s3_client.test_connection():
                messagebox.showinfo("测试连接", "连接成功！")
            else:
                messagebox.showerror("测试连接", "连接失败，请检查配置")
        
        def save_settings():
            try:
                # 验证最大文件数设置
                max_objects = int(max_objects_var.get())
                if max_objects < 100 or max_objects > 100000:
                    messagebox.showerror("设置错误", "最大文件数必须在100-100000之间")
                    return
                
                # 保存S3配置
                self.config_manager.config['s3_config'] = {
                    'endpoint': endpoint_var.get(),
                    'bucket': bucket_var.get(),
                    'access_key': access_key_var.get(),
                    'secret_key': secret_key_var.get(),
                    'region': region_var.get()
                }
                
                # 保存应用设置
                self.config_manager.config['app_settings']['max_list_objects'] = max_objects
                
                self.config_manager.save_config()
                settings_window.destroy()
                self.connect_s3()
                
            except ValueError:
                messagebox.showerror("设置错误", "最大文件数必须是数字")
        
        button_frame = ttk.Frame(settings_window)
        button_frame.grid(row=7, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="测试连接", command=test_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="保存", command=save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=settings_window.destroy).pack(side=tk.LEFT, padx=5)
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = S3GUI()
    app.run()