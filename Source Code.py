import pygame
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox, ttk
from tkinter import font as tkfont
import json
import os
import threading
import importlib.util
import shutil
from PIL import Image, ImageTk
import sys
import subprocess
import math

class SparEngineEditor:
    def __init__(self, root):
        self.root = root
        self.current_directory = ""
        self.root.title("SparEngine Editor")
        self.project_path = None
        self.scenes = {}
        self.current_scene = None
        self.objects = []
        self.selected_object_index = None
        self.dragging_object = None
        self.drag_offset = (0, 0)
        self.camera_offset = [0, 0]
        self.camera_drag_start = None
        self.running_simulation = False
        self.global_script = None
        self.object_images = {}  # Cache de imágenes para los sprites
        self.parenting_target = None  # Para el sistema de parenting

        # Configuración de la UI
        self.setup_ui()
        
        # Cargar iconos por defecto
        self.load_default_icons()

    def setup_ui(self):
        self.root.configure(bg="#2d2d2d")
        self.root.geometry("1200x800")
        
        # Configurar estilo
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TFrame', background='#2d2d2d')
        self.style.configure('TButton', background='#3c3c3c', foreground='white')
        self.style.configure('TLabel', background='#2d2d2d', foreground='white')
        self.style.configure('TEntry', fieldbackground='#3c3c3c', foreground='white')
        self.style.configure('TCombobox', fieldbackground='#3c3c3c', foreground='white')
        
        # Frame superior
        self.top_frame = ttk.Frame(self.root)
        self.top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Botones principales
        ttk.Button(self.top_frame, text="Abrir Proyecto", command=self.select_project).pack(side=tk.LEFT, padx=2)
        self.play_btn = ttk.Button(self.top_frame, text="▶ Play", command=self.play_simulation)
        self.play_btn.pack(side=tk.LEFT, padx=2)
        ttk.Button(self.top_frame, text="+ Escena", command=self.create_new_scene).pack(side=tk.LEFT, padx=2)
        
        # Selector de escenas
        self.scene_combo = ttk.Combobox(self.top_frame, state="readonly")
        self.scene_combo.pack(side=tk.LEFT, padx=10)
        self.scene_combo.bind("<<ComboboxSelected>>", self.change_scene)
        
        # Resolución
        ttk.Label(self.top_frame, text="Resolución:").pack(side=tk.LEFT, padx=2)
        self.resolution_combo = ttk.Combobox(self.top_frame, values=["800x600", "1024x768", "1280x720", "1920x1080"], width=10)
        self.resolution_combo.set("1024x768")
        self.resolution_combo.pack(side=tk.LEFT, padx=2)
        
        # Frame principal
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Panel izquierdo (jerarquía y navegador)
        self.left_panel = ttk.Frame(self.main_frame, width=250)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y)
        self.left_panel.pack_propagate(False)
        
        # Jerarquía
        hierarchy_frame = ttk.LabelFrame(self.left_panel, text="Jerarquía")
        hierarchy_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.hierarchy_tree = ttk.Treeview(hierarchy_frame, show="tree")
        self.hierarchy_tree.pack(fill=tk.BOTH, expand=True)
        self.hierarchy_tree.bind("<<TreeviewSelect>>", self.on_object_select)
        self.hierarchy_tree.bind("<Button-3>", self.hierarchy_right_click)
        
        # Navegador de proyectos
        browser_frame = ttk.LabelFrame(self.left_panel, text="Navegador de Proyectos")
        browser_frame.pack(fill=tk.BOTH, expand=True)
        
        self.path_label = ttk.Label(browser_frame, text="")
        self.path_label.pack(fill=tk.X)
        
        self.project_browser = ttk.Treeview(browser_frame, show="tree")
        self.project_browser.pack(fill=tk.BOTH, expand=True)
        self.project_browser.bind("<Double-1>", self.project_browser_double_click)
        self.project_browser.bind("<Button-3>", self.project_browser_right_click)
        
        # Panel central (escena)
        self.center_panel = ttk.Frame(self.main_frame)
        self.center_panel.pack(fill=tk.BOTH, expand=True)
        
        self.scene_canvas = tk.Canvas(self.center_panel, bg="#1e1e1e", bd=0, highlightthickness=0)
        self.scene_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Configurar eventos del canvas
        self.scene_canvas.bind("<Button-1>", self.start_drag)
        self.scene_canvas.bind("<B1-Motion>", self.do_drag)
        self.scene_canvas.bind("<ButtonRelease-1>", self.stop_drag)
        self.scene_canvas.bind("<Button-3>", self.start_camera_drag)
        self.scene_canvas.bind("<B3-Motion>", self.move_camera)
        self.scene_canvas.bind("<ButtonRelease-3>", self.stop_camera_drag)
        self.scene_canvas.bind("<MouseWheel>", self.zoom_camera)
        
        # Panel derecho (inspector)
        self.right_panel = ttk.Frame(self.main_frame, width=300)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        self.right_panel.pack_propagate(False)
        
        self.inspector_frame = ttk.LabelFrame(self.right_panel, text="Inspector")
        self.inspector_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configurar el inspector vacío (se llenará cuando se seleccione un objeto)
        self.setup_inspector()
        
    def setup_inspector(self):
        # Limpiar el inspector
        for widget in self.inspector_frame.winfo_children():
            widget.destroy()
        
        if self.selected_object_index is None:
            ttk.Label(self.inspector_frame, text="Ningún objeto seleccionado").pack(pady=10)
            return
            
        obj = self.objects[self.selected_object_index]
        
        # Nombre del objeto
        name_frame = ttk.Frame(self.inspector_frame)
        name_frame.pack(fill=tk.X, pady=5)
        ttk.Label(name_frame, text="Nombre:").pack(side=tk.LEFT)
        name_var = tk.StringVar(value=obj["name"])
        name_entry = ttk.Entry(name_frame, textvariable=name_var)
        name_entry.pack(side=tk.RIGHT, expand=True, fill=tk.X)
        name_entry.bind("<FocusOut>", lambda e: self.update_object_name(name_var.get()))
        
        # Transformación
        transform_frame = ttk.LabelFrame(self.inspector_frame, text="Transformación")
        transform_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # Posición
        pos_frame = ttk.Frame(transform_frame)
        pos_frame.pack(fill=tk.X, pady=2)
        ttk.Label(pos_frame, text="Posición:").pack(side=tk.LEFT)
        
        pos_x_var = tk.DoubleVar(value=obj["x"])
        pos_y_var = tk.DoubleVar(value=obj["y"])
        
        ttk.Label(pos_frame, text="X").pack(side=tk.LEFT)
        ttk.Spinbox(pos_frame, from_=-10000, to=10000, textvariable=pos_x_var, width=8,
                   command=lambda: self.update_object_position(pos_x_var.get(), pos_y_var.get())).pack(side=tk.LEFT, padx=2)
        ttk.Label(pos_frame, text="Y").pack(side=tk.LEFT)
        ttk.Spinbox(pos_frame, from_=-10000, to=10000, textvariable=pos_y_var, width=8,
                   command=lambda: self.update_object_position(pos_x_var.get(), pos_y_var.get())).pack(side=tk.LEFT, padx=2)
        
        pos_x_var.trace_add("write", lambda *_: self.update_object_position(pos_x_var.get(), pos_y_var.get()))
        pos_y_var.trace_add("write", lambda *_: self.update_object_position(pos_x_var.get(), pos_y_var.get()))
        
        # Rotación
        rot_frame = ttk.Frame(transform_frame)
        rot_frame.pack(fill=tk.X, pady=2)
        ttk.Label(rot_frame, text="Rotación:").pack(side=tk.LEFT)
        
        rot_var = tk.DoubleVar(value=obj.get("rotation", 0))
        ttk.Spinbox(rot_frame, from_=0, to=360, textvariable=rot_var, width=8,
                   command=lambda: self.update_object_rotation(rot_var.get())).pack(side=tk.RIGHT)
        rot_var.trace_add("write", lambda *_: self.update_object_rotation(rot_var.get()))
        
        # Escala
        scale_frame = ttk.Frame(transform_frame)
        scale_frame.pack(fill=tk.X, pady=2)
        ttk.Label(scale_frame, text="Escala:").pack(side=tk.LEFT)
        
        scale_x_var = tk.DoubleVar(value=obj.get("scale_x", 1))
        scale_y_var = tk.DoubleVar(value=obj.get("scale_y", 1))
        
        ttk.Label(scale_frame, text="X").pack(side=tk.LEFT)
        ttk.Spinbox(scale_frame, from_=0.1, to=10, increment=0.1, textvariable=scale_x_var, width=6,
                   command=lambda: self.update_object_scale(scale_x_var.get(), scale_y_var.get())).pack(side=tk.LEFT, padx=2)
        ttk.Label(scale_frame, text="Y").pack(side=tk.LEFT)
        ttk.Spinbox(scale_frame, from_=0.1, to=10, increment=0.1, textvariable=scale_y_var, width=6,
                   command=lambda: self.update_object_scale(scale_x_var.get(), scale_y_var.get())).pack(side=tk.LEFT, padx=2)
        
        scale_x_var.trace_add("write", lambda *_: self.update_object_scale(scale_x_var.get(), scale_y_var.get()))
        scale_y_var.trace_add("write", lambda *_: self.update_object_scale(scale_x_var.get(), scale_y_var.get()))
        
        # Parenting
        parent_frame = ttk.Frame(transform_frame)
        parent_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(parent_frame, text="Establecer como Padre", 
                  command=self.start_parenting).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(parent_frame, text="Quitar Parent", 
                  command=self.remove_parenting).pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        # Mostrar padre actual
        if "parent" in obj:
            ttk.Label(transform_frame, text=f"Padre: {obj['parent']}").pack()
        
        # Propiedades específicas del tipo de objeto
        if obj["type"] == "Sprite2D":
            self.setup_sprite_inspector(obj)
            
    def setup_sprite_inspector(self, obj):
        sprite_frame = ttk.LabelFrame(self.inspector_frame, text="Sprite")
        sprite_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # Mostrar imagen previa si existe
        if obj.get("sprite"):
            img_path = os.path.join(self.project_path, obj["sprite"])
            if os.path.exists(img_path):
                try:
                    img = Image.open(img_path)
                    img.thumbnail((100, 100))
                    photo = ImageTk.PhotoImage(img)
                    
                    img_label = ttk.Label(sprite_frame, image=photo)
                    img_label.image = photo  # Guardar referencia
                    img_label.pack()
                except:
                    pass
        
        ttk.Button(sprite_frame, text="Cambiar Sprite", 
                  command=lambda: self.change_sprite(self.selected_object_index)).pack(fill=tk.X)
        
        # Opacidad
        opacity_frame = ttk.Frame(sprite_frame)
        opacity_frame.pack(fill=tk.X, pady=2)
        ttk.Label(opacity_frame, text="Opacidad:").pack(side=tk.LEFT)
        
        opacity_var = tk.DoubleVar(value=obj.get("opacity", 1.0))
        ttk.Scale(opacity_frame, from_=0, to=1, variable=opacity_var, 
                 command=lambda v: self.update_object_opacity(float(v))).pack(side=tk.RIGHT, fill=tk.X, expand=True)
        opacity_var.trace_add("write", lambda *_: self.update_object_opacity(opacity_var.get()))
        
    def update_object_name(self, new_name):
        if self.selected_object_index is not None:
            self.objects[self.selected_object_index]["name"] = new_name
            self.save_scene()
            self.update_hierarchy()
            
    def update_object_position(self, x, y):
        if self.selected_object_index is not None:
            try:
                self.objects[self.selected_object_index]["x"] = float(x)
                self.objects[self.selected_object_index]["y"] = float(y)
                self.save_scene()
                self.draw_scene()
            except ValueError:
                pass
                
    def update_object_rotation(self, rotation):
        if self.selected_object_index is not None:
            self.objects[self.selected_object_index]["rotation"] = float(rotation)
            self.save_scene()
            self.draw_scene()
            
    def update_object_scale(self, scale_x, scale_y):
        if self.selected_object_index is not None:
            self.objects[self.selected_object_index]["scale_x"] = float(scale_x)
            self.objects[self.selected_object_index]["scale_y"] = float(scale_y)
            self.save_scene()
            self.draw_scene()
            
    def update_object_opacity(self, opacity):
        if self.selected_object_index is not None:
            self.objects[self.selected_object_index]["opacity"] = float(opacity)
            self.save_scene()
            self.draw_scene()
            
    def start_parenting(self):
        if self.selected_object_index is not None:
            self.parenting_target = self.objects[self.selected_object_index]["name"]
            messagebox.showinfo("Parenting", f"Selecciona el objeto hijo para {self.parenting_target}")
            
    def remove_parenting(self):
        if self.selected_object_index is not None:
            obj = self.objects[self.selected_object_index]
            if "parent" in obj:
                del obj["parent"]
                self.save_scene()
                self.update_hierarchy()
                self.setup_inspector()
                
    def complete_parenting(self, child_name):
        if self.parenting_target:
            for obj in self.objects:
                if obj["name"] == child_name:
                    obj["parent"] = self.parenting_target
                    self.save_scene()
                    self.update_hierarchy()
                    self.setup_inspector()
                    break
            self.parenting_target = None
            
    def on_object_select(self, event):
        selection = self.hierarchy_tree.selection()
        if selection:
            item = self.hierarchy_tree.item(selection[0])
            obj_name = item["text"]
            
            for i, obj in enumerate(self.objects):
                if obj["name"] == obj_name:
                    self.selected_object_index = i
                    break
                    
            self.setup_inspector()
            
            # Si estamos en modo parenting, completar la operación
            if self.parenting_target and self.parenting_target != obj_name:
                self.complete_parenting(obj_name)
                
    def load_default_icons(self):
        # Crear iconos por defecto para los objetos
        self.default_icons = {
            "EmptyObject": self.create_default_icon("#ffffff"),
            "Sprite2D": self.create_default_icon("#888888")
        }
        
    def create_default_icon(self, color):
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle([2, 2, 14, 14], fill=color)
        return ImageTk.PhotoImage(img)
        
    def select_project(self):
        path = filedialog.askdirectory(title="Seleccionar Carpeta de Proyecto")
        if path:
            self.project_path = path
            self.load_project_files()
            self.load_project_config()
            self.path_label.config(text=path)
            
    def load_project_config(self):
        config_path = os.path.join(self.project_path, "project_config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
                self.scenes = config.get("scenes", {})
                self.global_script = config.get("global_script")
                
                if self.scenes:
                    self.scene_combo["values"] = list(self.scenes.keys())
                    self.current_scene = list(self.scenes.keys())[0]
                    self.scene_combo.set(self.current_scene)
                    self.load_scene(self.current_scene)

    def save_project_config(self):
        if not self.project_path:
            return
            
        config_path = os.path.join(self.project_path, "project_config.json")
        config = {
            "scenes": self.scenes,
            "global_script": self.global_script
        }
        
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)

    def create_new_scene(self):
        if not self.project_path:
            messagebox.showerror("Error", "Primero selecciona un proyecto.")
            return
            
        scene_name = simpledialog.askstring("Nueva Escena", "Nombre de la nueva escena:")
        if scene_name:
            if scene_name in self.scenes:
                messagebox.showerror("Error", "Ya existe una escena con ese nombre.")
                return
                
            self.scenes[scene_name] = []
            self.scene_combo["values"] = list(self.scenes.keys())
            self.scene_combo.set(scene_name)
            self.current_scene = scene_name
            self.objects = []
            self.update_hierarchy()
            self.draw_scene()
            self.save_project_config()
            
            # Crear archivo de escena
            scene_path = os.path.join(self.project_path, "scenes", f"{scene_name}.json")
            os.makedirs(os.path.dirname(scene_path), exist_ok=True)
            with open(scene_path, "w") as f:
                json.dump([], f, indent=4)

    def change_scene(self, event=None):
        selected_scene = self.scene_combo.get()
        if selected_scene and selected_scene != self.current_scene:
            self.current_scene = selected_scene
            self.load_scene(selected_scene)

    def load_scene(self, scene_name):
        if scene_name in self.scenes:
            scene_path = os.path.join(self.project_path, "scenes", f"{scene_name}.json")
            if os.path.exists(scene_path):
                with open(scene_path, "r") as f:
                    self.objects = json.load(f)
                    self.scenes[scene_name] = self.objects
            else:
                self.objects = []
                
            self.update_hierarchy()
            self.draw_scene()

    def save_scene(self):
        if not self.project_path or not self.current_scene:
            return
            
        scene_path = os.path.join(self.project_path, "scenes", f"{self.current_scene}.json")
        os.makedirs(os.path.dirname(scene_path), exist_ok=True)
        
        with open(scene_path, "w") as f:
            json.dump(self.objects, f, indent=4)
            
        # Actualizar en el diccionario de escenas
        self.scenes[self.current_scene] = self.objects
        self.save_project_config()

    def update_hierarchy(self):
        self.hierarchy_tree.delete(*self.hierarchy_tree.get_children())
        
        # Primero añadir objetos sin parent
        for obj in self.objects:
            if "parent" not in obj:
                self.hierarchy_tree.insert("", "end", text=obj["name"], 
                                         image=self.default_icons.get(obj["type"]))
        
        # Luego añadir hijos recursivamente
        for obj in self.objects:
            if "parent" in obj:
                parent_id = self.find_item_by_text(self.hierarchy_tree, obj["parent"])
                if parent_id:
                    self.hierarchy_tree.insert(parent_id, "end", text=obj["name"], 
                                            image=self.default_icons.get(obj["type"]))
    
    def find_item_by_text(self, tree, text, parent_item=None):
        for item in tree.get_children(parent_item):
            if tree.item(item)["text"] == text:
                return item
            # Buscar recursivamente en los hijos
            child_item = self.find_item_by_text(tree, text, item)
            if child_item:
                return child_item
        return None

    def load_project_files(self):
        self.project_browser.delete(*self.project_browser.get_children())
        if self.project_path:
            self.populate_tree(self.project_browser, self.project_path)
            
    def populate_tree(self, tree, path, parent=""):
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    # Es una carpeta
                    node = tree.insert(parent, "end", text=item, values=[item_path], open=False)
                    self.populate_tree(tree, item_path, node)
                else:
                    # Es un archivo
                    tree.insert(parent, "end", text=item, values=[item_path])
        except Exception as e:
            print(f"Error al cargar archivos: {e}")

    def project_browser_double_click(self, event):
        item = self.project_browser.selection()[0]
        path = self.project_browser.item(item, "values")[0]
        
        if os.path.isdir(path):
            # Actualizar el árbol para mostrar/ocultar contenido
            if self.project_browser.item(item, "open"):
                self.project_browser.item(item, open=False)
                self.project_browser.delete(*self.project_browser.get_children(item))
            else:
                self.populate_tree(self.project_browser, path, item)
                self.project_browser.item(item, open=True)
        else:
            # Si es un archivo .py, podríamos asignarlo como script global
            if path.endswith(".py"):
                self.global_script = os.path.relpath(path, self.project_path)
                self.save_project_config()
                messagebox.showinfo("Script Global", f"Script global asignado: {os.path.basename(path)}")

    def project_browser_right_click(self, event):
        item = self.project_browser.identify_row(event.y)
        if item:
            path = self.project_browser.item(item, "values")[0]
            is_dir = os.path.isdir(path)
            
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="Abrir", command=lambda: self.open_file(path))
            
            if path.endswith(".py"):
                menu.add_command(label="Establecer como Script Global", 
                               command=lambda: self.set_global_script(path))
            
            if is_dir:
                menu.add_command(label="Nuevo Script", 
                               command=lambda: self.create_script_in_folder(path))
                menu.add_command(label="Nueva Carpeta", 
                               command=lambda: self.create_folder_in_folder(path))
            
            menu.tk_popup(event.x_root, event.y_root)
            
    def open_file(self, path):
        if os.path.isfile(path):
            if sys.platform == "win32":
                os.startfile(path)
            else:
                opener = "open" if sys.platform == "darwin" else "xdg-open"
                subprocess.call([opener, path])

    def set_global_script(self, path):
        self.global_script = os.path.relpath(path, self.project_path)
        self.save_project_config()
        messagebox.showinfo("Script Global", f"Script global asignado: {os.path.basename(path)}")

    def create_script_in_folder(self, folder_path):
        name = simpledialog.askstring("Nuevo Script", "Nombre del script (.py):")
        if name:
            path = os.path.join(folder_path, f"{name}.py")
            with open(path, "w") as f:
                f.write("# Nuevo script\n")
            self.load_project_files()

    def create_folder_in_folder(self, folder_path):
        name = simpledialog.askstring("Nueva Carpeta", "Nombre de la carpeta:")
        if name:
            path = os.path.join(folder_path, name)
            os.makedirs(path, exist_ok=True)
            self.load_project_files()

    def hierarchy_right_click(self, event):
        item = self.hierarchy_tree.identify_row(event.y)
        menu = tk.Menu(self.root, tearoff=0)
        
        menu.add_command(label="Crear EmptyObject", command=self.create_empty)
        menu.add_command(label="Crear Sprite2D", command=self.create_sprite2d)
        
        if item:
            menu.add_separator()
            menu.add_command(label="Eliminar", command=lambda: self.delete_object_by_name(self.hierarchy_tree.item(item, "text")))
            menu.add_command(label="Asignar Script", command=lambda: self.assign_script_to_object(self.hierarchy_tree.item(item, "text")))
            menu.add_command(label="Duplicar", command=lambda: self.duplicate_object(self.hierarchy_tree.item(item, "text")))
            
        menu.tk_popup(event.x_root, event.y_root)
        
    def delete_object_by_name(self, name):
        confirm = messagebox.askyesno("Confirmar", f"¿Eliminar el objeto '{name}'?")
        if confirm:
            # Eliminar también todos los hijos
            def delete_children(parent_name):
                children = [obj for obj in self.objects if obj.get("parent") == parent_name]
                for child in children:
                    delete_children(child["name"])
                    self.objects.remove(child)
            
            delete_children(name)
            
            # Eliminar el objeto principal
            self.objects = [obj for obj in self.objects if obj["name"] != name]
            self.save_scene()
            self.update_hierarchy()
            self.draw_scene()
            
    def assign_script_to_object(self, obj_name):
        script_path = filedialog.askopenfilename(
            title="Seleccionar Script",
            filetypes=[("Python Files", "*.py")],
            initialdir=self.project_path
        )
        
        if script_path:
            rel_path = os.path.relpath(script_path, self.project_path)
            for obj in self.objects:
                if obj["name"] == obj_name:
                    obj["script"] = rel_path
                    break
            self.save_scene()

    def duplicate_object(self, obj_name):
        original = next((obj for obj in self.objects if obj["name"] == obj_name), None)
        if original:
            new_obj = original.copy()
            new_obj["name"] = self.get_unique_name(original["name"])
            new_obj["x"] += 30  # Desplazar un poco para que no se solape
            new_obj["y"] += 30
            
            self.objects.append(new_obj)
            self.save_scene()
            self.update_hierarchy()
            self.draw_scene()
            
    def get_unique_name(self, base_name):
        counter = 1
        new_name = f"{base_name}_{counter}"
        
        while any(obj["name"] == new_name for obj in self.objects):
            counter += 1
            new_name = f"{base_name}_{counter}"
            
        return new_name

    def create_empty(self):
        name = self.get_unique_name("EmptyObject")
        self.objects.append({
            "type": "EmptyObject",
            "name": name,
            "x": 100,
            "y": 100,
            "rotation": 0,
            "scale_x": 1,
            "scale_y": 1
        })
        self.save_scene()
        self.update_hierarchy()
        self.draw_scene()

    def create_sprite2d(self):
        sprite_file = filedialog.askopenfilename(
            title="Seleccionar Sprite",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")]
        )
        
        if sprite_file:
            name = self.get_unique_name("Sprite")
            
            # Copiar el sprite al proyecto
            assets_dir = os.path.join(self.project_path, "assets")
            os.makedirs(assets_dir, exist_ok=True)
            
            sprite_name = os.path.basename(sprite_file)
            dest_path = os.path.join(assets_dir, sprite_name)
            
            try:
                shutil.copy2(sprite_file, dest_path)
                
                self.objects.append({
                    "type": "Sprite2D",
                    "name": name,
                    "sprite": os.path.join("assets", sprite_name),
                    "x": 100,
                    "y": 100,
                    "rotation": 0,
                    "scale_x": 1,
                    "scale_y": 1,
                    "opacity": 1.0
                })
                
                self.save_scene()
                self.update_hierarchy()
                self.draw_scene()
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo copiar el sprite: {e}")

    def change_sprite(self, obj_index):
        sprite_file = filedialog.askopenfilename(
            title="Seleccionar Sprite",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")],
            initialdir=self.project_path
        )
        
        if sprite_file and 0 <= obj_index < len(self.objects):
            # Copiar el sprite al proyecto
            assets_dir = os.path.join(self.project_path, "assets")
            os.makedirs(assets_dir, exist_ok=True)
            
            sprite_name = os.path.basename(sprite_file)
            dest_path = os.path.join(assets_dir, sprite_name)
            
            try:
                shutil.copy2(sprite_file, dest_path)
                
                self.objects[obj_index]["sprite"] = os.path.join("assets", sprite_name)
                self.save_scene()
                self.draw_scene()
                self.setup_inspector()  # Actualizar el inspector para mostrar la nueva imagen
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo copiar el sprite: {e}")

    def start_drag(self, event):
        x, y = self.screen_to_world(event.x, event.y)
        
        # Buscar el objeto más cercano al punto de clic
        closest_obj = None
        min_dist = float('inf')
        
        for idx, obj in enumerate(self.objects):
            obj_x, obj_y = self.get_world_position(obj)
            dist = math.sqrt((x - obj_x)**2 + (y - obj_y)**2)
            
            if dist < 30 and dist < min_dist:  # Radio de 30 píxeles
                min_dist = dist
                closest_obj = idx
                
        if closest_obj is not None:
            self.dragging_object = closest_obj
            obj = self.objects[closest_obj]
            obj_x, obj_y = self.get_world_position(obj)
            self.drag_offset = (obj_x - x, obj_y - y)
            
            # Seleccionar el objeto
            self.selected_object_index = closest_obj
            self.update_hierarchy_selection()
            self.setup_inspector()

    def do_drag(self, event):
        if self.dragging_object is not None:
            x, y = self.screen_to_world(event.x, event.y)
            offset_x, offset_y = self.drag_offset
            
            obj = self.objects[self.dragging_object]
            
            # Si el objeto tiene un padre, ajustamos la posición relativa
            if "parent" in obj:
                parent = next((o for o in self.objects if o["name"] == obj["parent"]), None)
                if parent:
                    parent_x, parent_y = self.get_world_position(parent)
                    obj["x"] = (x + offset_x) - parent_x
                    obj["y"] = (y + offset_y) - parent_y
                else:
                    obj["x"] = x + offset_x
                    obj["y"] = y + offset_y
            else:
                obj["x"] = x + offset_x
                obj["y"] = y + offset_y
                
            self.save_scene()
            self.draw_scene()

    def stop_drag(self, event):
        self.dragging_object = None

    def start_camera_drag(self, event):
        self.camera_drag_start = (event.x, event.y)

    def move_camera(self, event):
        if self.camera_drag_start:
            dx = event.x - self.camera_drag_start[0]
            dy = event.y - self.camera_drag_start[1]
            
            self.camera_offset[0] += dx
            self.camera_offset[1] += dy
            
            self.camera_drag_start = (event.x, event.y)
            self.draw_scene()

    def stop_camera_drag(self, event):
        self.camera_drag_start = None

    def zoom_camera(self, event):
        # Factor de zoom basado en la dirección de la rueda del mouse
        zoom_factor = 1.1 if event.delta > 0 else 0.9
        
        # Obtener la posición del mouse en coordenadas del mundo antes del zoom
        mouse_x, mouse_y = self.screen_to_world(event.x, event.y)
        
        # Aplicar el zoom
        self.camera_offset[0] = mouse_x - (mouse_x - self.camera_offset[0]) * zoom_factor
        self.camera_offset[1] = mouse_y - (mouse_y - self.camera_offset[1]) * zoom_factor
        
        self.draw_scene()

    def screen_to_world(self, screen_x, screen_y):
        return (
            screen_x - self.camera_offset[0],
            screen_y - self.camera_offset[1]
        )

    def world_to_screen(self, world_x, world_y):
        return (
            world_x + self.camera_offset[0],
            world_y + self.camera_offset[1]
        )

    def get_world_position(self, obj):
        """Obtiene la posición global de un objeto, teniendo en cuenta la jerarquía de parenting"""
        x, y = obj["x"], obj["y"]
        
        if "parent" in obj:
            parent = next((o for o in self.objects if o["name"] == obj["parent"]), None)
            if parent:
                parent_x, parent_y = self.get_world_position(parent)
                x += parent_x
                y += parent_y
                
        return x, y

    def update_hierarchy_selection(self):
        if self.selected_object_index is not None:
            obj_name = self.objects[self.selected_object_index]["name"]
            item_id = self.find_item_by_text(self.hierarchy_tree, obj_name)
            if item_id:
                self.hierarchy_tree.selection_set(item_id)
                self.hierarchy_tree.focus(item_id)

    def draw_scene(self):
        self.scene_canvas.delete("all")
        
        # Dibujar una cuadrícula de fondo
        self.draw_grid()
        
        # Dibujar todos los objetos
        for obj in self.objects:
            if "parent" not in obj:  # Dibujar solo los objetos raíz, los hijos se dibujarán recursivamente
                self.draw_object(obj)
                
        # Dibujar selección
        if self.selected_object_index is not None:
            obj = self.objects[self.selected_object_index]
            x, y = self.world_to_screen(*self.get_world_position(obj))
            
            # Dibujar un rectángulo de selección
            self.scene_canvas.create_rectangle(
                x - 30, y - 30, x + 30, y + 30,
                outline="#00ffff", dash=(4, 2), width=2
            )

    def draw_grid(self):
        # Configuración de la cuadrícula
        grid_size = 50
        width = self.scene_canvas.winfo_width()
        height = self.scene_canvas.winfo_height()
        
        # Calcular las coordenadas iniciales
        start_x = -self.camera_offset[0] % grid_size
        start_y = -self.camera_offset[1] % grid_size
        
        # Dibujar líneas verticales
        for x in range(int(start_x), width, grid_size):
            self.scene_canvas.create_line(
                x, 0, x, height,
                fill="#333333", width=1
            )
        
        # Dibujar líneas horizontales
        for y in range(int(start_y), height, grid_size):
            self.scene_canvas.create_line(
                0, y, width, y,
                fill="#333333", width=1
            )

    def draw_object(self, obj):
        x, y = self.world_to_screen(*self.get_world_position(obj))
        
        if obj["type"] == "EmptyObject":
            # Dibujar un círculo para EmptyObject
            self.scene_canvas.create_oval(
                x - 15, y - 15, x + 15, y + 15,
                fill="#ffffff", outline="#aaaaaa"
            )
            self.scene_canvas.create_text(
                x, y, text=obj["name"],
                fill="#000000", font=("Arial", 8)
            )
        elif obj["type"] == "Sprite2D":
            # Dibujar el sprite o un placeholder si no hay sprite
            if obj.get("sprite"):
                sprite_path = os.path.join(self.project_path, obj["sprite"])
                if os.path.exists(sprite_path):
                    # Usar imagen en caché o cargarla
                    if sprite_path not in self.object_images:
                        try:
                            img = Image.open(sprite_path)
                            
                            # Aplicar rotación y escala
                            if obj.get("rotation", 0) != 0:
                                img = img.rotate(-obj["rotation"], expand=True)
                                
                            scale_x = obj.get("scale_x", 1)
                            scale_y = obj.get("scale_y", 1)
                            if scale_x != 1 or scale_y != 1:
                                new_width = int(img.width * scale_x)
                                new_height = int(img.height * scale_y)
                                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                                
                            # Aplicar opacidad
                            opacity = obj.get("opacity", 1.0)
                            if opacity < 1.0:
                                img = self.apply_opacity(img, opacity)
                                
                            self.object_images[sprite_path] = ImageTk.PhotoImage(img)
                        except:
                            pass
                    
                    if sprite_path in self.object_images:
                        img = self.object_images[sprite_path]
                        self.scene_canvas.create_image(
                            x, y, image=img,
                            anchor=tk.CENTER
                        )
                        return
            
            # Dibujar un placeholder si no hay sprite o no se pudo cargar
            self.scene_canvas.create_rectangle(
                x - 25, y - 25, x + 25, y + 25,
                fill="#888888", outline="#555555"
            )
            self.scene_canvas.create_text(
                x, y, text=obj["name"],
                fill="#ffffff", font=("Arial", 8)
            )
        
        # Dibujar hijos recursivamente
        children = [o for o in self.objects if o.get("parent") == obj["name"]]
        for child in children:
            self.draw_object(child)

    def apply_opacity(self, img, opacity):
        """Aplica opacidad a una imagen PIL"""
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        alpha = img.split()[3]
        alpha = alpha.point(lambda p: int(p * opacity))
        
        img.putalpha(alpha)
        return img

    def play_simulation(self):
        if self.running_simulation:
            self.running_simulation = False
            self.play_btn.config(text="▶ Play")
        else:
            if not self.project_path:
                messagebox.showerror("Error", "Primero selecciona un proyecto.")
                return
                
            self.running_simulation = True
            self.play_btn.config(text="■ Stop")
            
            # Guardar la escena antes de ejecutar
            self.save_scene()
            
            # Ejecutar en un hilo separado
            self.simulation_thread = threading.Thread(target=self.run_simulation)
            self.simulation_thread.start()

    def run_simulation(self):
        pygame.init()
        width, height = map(int, self.resolution_combo.get().split("x"))
        screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("SparEngine Game")
        
        clock = pygame.time.Clock()
        
        # Cargar el script global si existe
        global_module = None
        if self.global_script:
            global_script_path = os.path.join(self.project_path, self.global_script)
            if os.path.exists(global_script_path):
                try:
                    spec = importlib.util.spec_from_file_location("global_script", global_script_path)
                    global_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(global_module)
                    
                    # Llamar a la función de inicialización si existe
                    if hasattr(global_module, "init"):
                        global_module.init(self.objects)
                except Exception as e:
                    print(f"Error al cargar script global: {e}")

        # Cargar scripts de los objetos y sprites
        object_sprites = {}
        object_modules = {}
        
        for obj in self.objects:
            # Cargar sprite si es un Sprite2D
            if obj["type"] == "Sprite2D" and obj.get("sprite"):
                sprite_path = os.path.join(self.project_path, obj["sprite"])
                if os.path.exists(sprite_path):
                    try:
                        object_sprites[obj["name"]] = pygame.image.load(sprite_path).convert_alpha()
                    except:
                        pass
            
            # Cargar script si tiene uno
            if obj.get("script"):
                script_path = os.path.join(self.project_path, obj["script"])
                if os.path.exists(script_path):
                    try:
                        spec = importlib.util.spec_from_file_location(obj["name"], script_path)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        object_modules[obj["name"]] = module
                    except Exception as e:
                        print(f"Error al cargar script de {obj['name']}: {e}")

        while self.running_simulation:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running_simulation = False

            # Ejecutar update global si existe
            if global_module and hasattr(global_module, "update"):
                try:
                    global_module.update(self.objects)
                except Exception as e:
                    print(f"Error en update global: {e}")

            # Ejecutar updates de los objetos
            for obj in self.objects:
                if obj["name"] in object_modules and hasattr(object_modules[obj["name"]], "update"):
                    try:
                        object_modules[obj["name"]].update(obj, events)
                    except Exception as e:
                        print(f"Error en update de {obj['name']}: {e}")

            # Dibujar
            screen.fill("black")
            
            # Dibujar objetos
            for obj in self.objects:
                if "parent" not in obj:  # Dibujar solo objetos raíz
                    self.draw_pygame_object(screen, obj, object_sprites)
            
            pygame.display.flip()
            clock.tick(60)
        
        pygame.quit()
        self.running_simulation = False
        self.play_btn.config(text="▶ Play")

    def draw_pygame_object(self, screen, obj, object_sprites):
        # Calcular posición global (teniendo en cuenta parenting)
        x, y = self.get_world_position(obj)
        
        if obj["type"] == "Sprite2D" and obj["name"] in object_sprites:
            sprite = object_sprites[obj["name"]]
            
            # Aplicar escala
            scale_x = obj.get("scale_x", 1)
            scale_y = obj.get("scale_y", 1)
            if scale_x != 1 or scale_y != 1:
                new_width = int(sprite.get_width() * scale_x)
                new_height = int(sprite.get_height() * scale_y)
                sprite = pygame.transform.scale(sprite, (new_width, new_height))
            
            # Aplicar rotación
            rotation = obj.get("rotation", 0)
            if rotation != 0:
                sprite = pygame.transform.rotate(sprite, -rotation)
            
            # Aplicar opacidad
            opacity = obj.get("opacity", 1.0)
            if opacity < 1.0:
                sprite.fill((255, 255, 255, int(255 * opacity)), None, pygame.BLEND_RGBA_MULT)
            
            # Dibujar
            sprite_rect = sprite.get_rect(center=(x, y))
            screen.blit(sprite, sprite_rect)
        else:
            # Dibujar placeholder
            pygame.draw.rect(screen, (100, 100, 100), (x - 25, y - 25, 50, 50))
        
        # Dibujar hijos recursivamente
        children = [o for o in self.objects if o.get("parent") == obj["name"]]
        for child in children:
            self.draw_pygame_object(screen, child, object_sprites)

if __name__ == "__main__":
    root = tk.Tk()
    editor = SparEngineEditor(root)
    root.mainloop()