#!/usr/bin/env python3
"""
YOLO Dataset Label Editor
A GUI tool for editing YOLO format labels (bounding boxes) on images.

Features:
- Load dataset from yolov11/dataset directory
- Display images with overlaid labels
- Add new labels by drawing bounding boxes
- Delete labels by clicking on them
- Move/reposition labels by dragging
- Save changes to label files
- Navigate through images
- Support for multiple image variants (density, mean, std, etc.)
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk, ImageDraw
import glob


class YOLOLabelEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("YOLO Label Editor")
        self.root.geometry("1400x900")
        
        # Dataset paths - now configurable
        self.images_dir = ""
        self.labels_dir = ""
        
        # State variables
        self.image_files = []
        self.current_image_index = 0
        self.current_image = None
        self.current_image_path = None
        self.current_label_path = None
        self.labels = []  # List of [class_id, center_x, center_y, width, height]
        self.display_image = None
        self.photo_image = None
        
        # Drawing state
        self.drawing = False
        self.start_x = 0
        self.start_y = 0
        self.current_rect = None
        self.selected_label_idx = None
        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        
        # Colors for bounding boxes
        self.bbox_color = "red"
        self.bbox_width = 2
        self.selected_bbox_color = "yellow"
        
        # Canvas scale
        self.canvas_width = 1000
        self.canvas_height = 700
        self.scale = 1.0
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        # Top control panel for paths
        path_frame = ttk.LabelFrame(self.root, text="Dataset Paths", padding="5")
        path_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Images directory
        img_frame = ttk.Frame(path_frame)
        img_frame.pack(fill=tk.X, pady=2)
        ttk.Label(img_frame, text="Images:", width=8).pack(side=tk.LEFT, padx=5)
        self.images_path_label = ttk.Label(img_frame, text="Not selected", foreground="gray")
        self.images_path_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(img_frame, text="Browse...", command=self.browse_images_dir, width=12).pack(side=tk.RIGHT, padx=5)
        
        # Labels directory
        lbl_frame = ttk.Frame(path_frame)
        lbl_frame.pack(fill=tk.X, pady=2)
        ttk.Label(lbl_frame, text="Labels:", width=8).pack(side=tk.LEFT, padx=5)
        self.labels_path_label = ttk.Label(lbl_frame, text="Not selected", foreground="gray")
        self.labels_path_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(lbl_frame, text="Browse...", command=self.browse_labels_dir, width=12).pack(side=tk.RIGHT, padx=5)
        
        # Load button
        btn_frame = ttk.Frame(path_frame)
        btn_frame.pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="📁 Load Dataset", command=self.load_dataset, width=20).pack(pady=5)
        
        # Control panel
        control_frame = ttk.Frame(self.root, padding="5")
        control_frame.pack(side=tk.TOP, fill=tk.X)
        
        # Navigation buttons
        ttk.Button(control_frame, text="◀ Previous", command=self.prev_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Next ▶", command=self.next_image).pack(side=tk.LEFT, padx=5)
        
        # Image counter
        self.image_counter_label = ttk.Label(control_frame, text="0/0")
        self.image_counter_label.pack(side=tk.LEFT, padx=10)
        
        # Save button
        ttk.Button(control_frame, text="💾 Save", command=self.save_labels).pack(side=tk.LEFT, padx=5)
        
        # Main content area
        main_frame = ttk.Frame(self.root)
        main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Canvas for image display
        canvas_frame = ttk.LabelFrame(main_frame, text="Image Canvas", padding="5")
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, width=self.canvas_width, height=self.canvas_height,
                               bg="gray20", cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Bind mouse events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Button-3>", self.on_right_click)  # Right click to delete
        
        # Right panel - Controls and label list
        right_frame = ttk.Frame(main_frame, width=350)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
        right_frame.pack_propagate(False)
        
        # Instructions
        instructions_frame = ttk.LabelFrame(right_frame, text="Instructions", padding="5")
        instructions_frame.pack(fill=tk.X, pady=(0, 5))
        
        instructions_text = """
• Left Click + Drag: Draw new bounding box
• Left Click on box: Select/move box
• Right Click on box: Delete box
• Save: Write changes to label file

Navigate: Use Previous/Next buttons
or keyboard arrows ← →
        """
        ttk.Label(instructions_frame, text=instructions_text, justify=tk.LEFT).pack()
        
        # Current file info
        info_frame = ttk.LabelFrame(right_frame, text="Current File", padding="5")
        info_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.filename_label = ttk.Label(info_frame, text="No file loaded", wraplength=320)
        self.filename_label.pack()
        
        # Label list
        list_frame = ttk.LabelFrame(right_frame, text="Labels", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Scrollbar for label list
        list_scroll = ttk.Scrollbar(list_frame)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.label_listbox = tk.Listbox(list_frame, yscrollcommand=list_scroll.set, height=15)
        self.label_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scroll.config(command=self.label_listbox.yview)
        self.label_listbox.bind("<<ListboxSelect>>", self.on_label_selected)
        
        # Label management buttons
        button_frame = ttk.Frame(list_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(button_frame, text="Delete Selected", command=self.delete_selected_label).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Clear All", command=self.clear_all_labels).pack(side=tk.LEFT, padx=2)
        
        # Resize button (new row)
        resize_frame = ttk.Frame(list_frame)
        resize_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(resize_frame, text="📏 Resize All to 16x16", command=self.resize_all_to_16x16).pack(fill=tk.X, padx=2)
        
        # Class ID selector for new labels
        class_frame = ttk.LabelFrame(right_frame, text="New Label Class", padding="5")
        class_frame.pack(fill=tk.X)
        
        ttk.Label(class_frame, text="Class ID:").pack(side=tk.LEFT, padx=5)
        self.class_id_var = tk.IntVar(value=0)
        ttk.Spinbox(class_frame, from_=0, to=10, textvariable=self.class_id_var, width=10).pack(side=tk.LEFT)
        
        # Keyboard bindings
        self.root.bind("<Left>", lambda e: self.prev_image())
        self.root.bind("<Right>", lambda e: self.next_image())
        self.root.bind("<Delete>", lambda e: self.delete_selected_label())
        self.root.bind("<Control-s>", lambda e: self.save_labels())
        
    def browse_images_dir(self):
        """Browse for images directory"""
        directory = filedialog.askdirectory(title="Select Images Directory")
        if directory:
            self.images_dir = directory
            self.images_path_label.config(text=directory, foreground="black")
    
    def browse_labels_dir(self):
        """Browse for labels directory"""
        directory = filedialog.askdirectory(title="Select Labels Directory")
        if directory:
            self.labels_dir = directory
            self.labels_path_label.config(text=directory, foreground="black")
    
    def load_dataset(self):
        """Load image files from the selected directories"""
        if not self.images_dir:
            messagebox.showwarning("No Images Directory", 
                                  "Please select an images directory first.")
            return
        
        if not self.labels_dir:
            messagebox.showwarning("No Labels Directory", 
                                  "Please select a labels directory first.")
            return
        
        if not os.path.exists(self.images_dir):
            messagebox.showerror("Directory Not Found", 
                                f"Images directory not found:\n{self.images_dir}")
            return
        
        # Get all image files (jpg, png, jpeg)
        self.image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']:
            self.image_files.extend(glob.glob(os.path.join(self.images_dir, ext)))
        
        self.image_files = sorted(self.image_files)
        
        if not self.image_files:
            messagebox.showinfo("No Images", 
                               f"No images found in:\n{self.images_dir}")
            return
        
        self.current_image_index = 0
        self.load_current_image()
        messagebox.showinfo("Success", f"Loaded {len(self.image_files)} images!")
        
    def load_current_image(self):
        """Load and display the current image with its labels"""
        if not self.image_files:
            return
        
        self.current_image_path = self.image_files[self.current_image_index]
        
        # Construct label path
        image_filename = os.path.basename(self.current_image_path)
        label_filename = os.path.splitext(image_filename)[0] + ".txt"
        
        # Use the selected labels directory
        self.current_label_path = os.path.join(self.labels_dir, label_filename)
        
        # Create labels directory if it doesn't exist
        if not os.path.exists(self.labels_dir):
            os.makedirs(self.labels_dir, exist_ok=True)
        
        # Load image
        self.current_image = Image.open(self.current_image_path)
        
        # Load labels
        self.load_labels()
        
        # Update display
        self.update_display()
        self.update_info()
        
    def load_labels(self):
        """Load labels from the label file"""
        self.labels = []
        
        if os.path.exists(self.current_label_path):
            with open(self.current_label_path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) == 5:
                        class_id = int(parts[0])
                        center_x = float(parts[1])
                        center_y = float(parts[2])
                        width = float(parts[3])
                        height = float(parts[4])
                        self.labels.append([class_id, center_x, center_y, width, height])
        
        self.update_label_list()
        
    def save_labels(self):
        """Save labels to the label file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.current_label_path), exist_ok=True)
            
            with open(self.current_label_path, 'w') as f:
                for label in self.labels:
                    class_id, cx, cy, w, h = label
                    f.write(f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")
            
            messagebox.showinfo("Saved", f"Labels saved to:\n{self.current_label_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save labels:\n{str(e)}")
    
    def update_display(self):
        """Update the canvas with the current image and labels"""
        if self.current_image is None:
            return
        
        # Calculate scale to fit canvas
        img_width, img_height = self.current_image.size
        scale_w = self.canvas_width / img_width
        scale_h = self.canvas_height / img_height
        self.scale = min(scale_w, scale_h, 1.0)  # Don't scale up
        
        # Resize image for display
        new_width = int(img_width * self.scale)
        new_height = int(img_height * self.scale)
        self.display_image = self.current_image.copy()
        self.display_image = self.display_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Draw labels on image
        draw = ImageDraw.Draw(self.display_image)
        
        for idx, label in enumerate(self.labels):
            class_id, cx, cy, w, h = label
            
            # Convert normalized coords to pixel coords
            x1 = int((cx - w/2) * new_width)
            y1 = int((cy - h/2) * new_height)
            x2 = int((cx + w/2) * new_width)
            y2 = int((cy + h/2) * new_height)
            
            # Choose color based on selection
            color = self.selected_bbox_color if idx == self.selected_label_idx else self.bbox_color
            
            # Draw rectangle
            draw.rectangle([x1, y1, x2, y2], outline=color, width=self.bbox_width)
            
            # Draw label text
            text = f"#{idx} cls:{class_id}"
            draw.text((x1, y1-15), text, fill=color)
        
        # Convert to PhotoImage and display
        self.photo_image = ImageTk.PhotoImage(self.display_image)
        self.canvas.delete("all")
        
        # Center image on canvas
        x_offset = (self.canvas_width - new_width) // 2
        y_offset = (self.canvas_height - new_height) // 2
        self.canvas.create_image(x_offset, y_offset, anchor=tk.NW, image=self.photo_image)
        
    def update_label_list(self):
        """Update the label listbox"""
        self.label_listbox.delete(0, tk.END)
        if self.current_image is None:
            return
        
        img_width, img_height = self.current_image.size
        
        for idx, label in enumerate(self.labels):
            class_id, cx, cy, w, h = label
            # Convert normalized size to actual pixel size
            pixel_w = int(w * img_width)
            pixel_h = int(h * img_height)
            self.label_listbox.insert(tk.END, 
                f"#{idx}: Class {class_id} | pos:({cx:.3f},{cy:.3f}) | size: {pixel_w}x{pixel_h}px ({w:.3f}x{h:.3f})")
    
    def update_info(self):
        """Update the info labels"""
        if self.image_files:
            filename = os.path.basename(self.current_image_path)
            self.filename_label.config(text=f"{filename}")
            self.image_counter_label.config(
                text=f"{self.current_image_index + 1}/{len(self.image_files)}")
        
    def pixel_to_normalized(self, px, py):
        """Convert canvas pixel coordinates to normalized image coordinates"""
        if self.current_image is None:
            return 0, 0
        
        img_width, img_height = self.current_image.size
        new_width = int(img_width * self.scale)
        new_height = int(img_height * self.scale)
        
        x_offset = (self.canvas_width - new_width) // 2
        y_offset = (self.canvas_height - new_height) // 2
        
        # Convert to image pixel coords
        img_px = (px - x_offset) / self.scale
        img_py = (py - y_offset) / self.scale
        
        # Normalize
        norm_x = img_px / img_width
        norm_y = img_py / img_height
        
        return norm_x, norm_y
    
    def find_label_at_position(self, px, py):
        """Find label index at the given canvas position"""
        norm_x, norm_y = self.pixel_to_normalized(px, py)
        
        for idx, label in enumerate(self.labels):
            class_id, cx, cy, w, h = label
            if (abs(norm_x - cx) <= w/2 and abs(norm_y - cy) <= h/2):
                return idx
        return None
    
    def on_canvas_click(self, event):
        """Handle canvas click event"""
        if self.current_image is None:
            return
        
        # Check if clicking on existing label
        label_idx = self.find_label_at_position(event.x, event.y)
        
        if label_idx is not None:
            # Start dragging existing label
            self.selected_label_idx = label_idx
            self.dragging = True
            norm_x, norm_y = self.pixel_to_normalized(event.x, event.y)
            cx, cy = self.labels[label_idx][1], self.labels[label_idx][2]
            self.drag_offset_x = norm_x - cx
            self.drag_offset_y = norm_y - cy
            self.label_listbox.selection_clear(0, tk.END)
            self.label_listbox.selection_set(label_idx)
            self.update_display()
        else:
            # Start drawing new label
            self.drawing = True
            self.start_x = event.x
            self.start_y = event.y
            self.selected_label_idx = None
    
    def on_canvas_drag(self, event):
        """Handle canvas drag event"""
        if self.current_image is None:
            return
        
        if self.dragging and self.selected_label_idx is not None:
            # Move existing label
            norm_x, norm_y = self.pixel_to_normalized(event.x, event.y)
            self.labels[self.selected_label_idx][1] = norm_x - self.drag_offset_x
            self.labels[self.selected_label_idx][2] = norm_y - self.drag_offset_y
            
            # Clamp to valid range
            self.labels[self.selected_label_idx][1] = max(0, min(1, self.labels[self.selected_label_idx][1]))
            self.labels[self.selected_label_idx][2] = max(0, min(1, self.labels[self.selected_label_idx][2]))
            
            self.update_display()
            self.update_label_list()
        elif self.drawing:
            # Preview new bounding box (could be implemented with canvas rectangles)
            pass
    
    def on_canvas_release(self, event):
        """Handle canvas release event"""
        if self.current_image is None:
            return
        
        if self.drawing:
            # Finish drawing new label
            end_x = event.x
            end_y = event.y
            
            # Convert to normalized coordinates
            start_norm_x, start_norm_y = self.pixel_to_normalized(self.start_x, self.start_y)
            end_norm_x, end_norm_y = self.pixel_to_normalized(end_x, end_y)
            
            # Calculate center position (average of start and end points)
            cx = (start_norm_x + end_norm_x) / 2
            cy = (start_norm_y + end_norm_y) / 2
            
            # FIXED SIZE: 16x16 pixels converted to normalized coordinates
            img_width, img_height = self.current_image.size
            fixed_pixel_size = 16
            w = fixed_pixel_size / img_width
            h = fixed_pixel_size / img_height
            
            # Only add if click was detected (some movement occurred)
            if abs(end_x - self.start_x) > 2 or abs(end_y - self.start_y) > 2:
                # Clamp center to valid range, accounting for box size
                cx = max(w/2, min(1 - w/2, cx))
                cy = max(h/2, min(1 - h/2, cy))
                
                class_id = self.class_id_var.get()
                self.labels.append([class_id, cx, cy, w, h])
                self.update_display()
                self.update_label_list()
            
            self.drawing = False
        elif self.dragging:
            self.dragging = False
    
    def on_right_click(self, event):
        """Handle right click to delete label"""
        if self.current_image is None:
            return
        
        label_idx = self.find_label_at_position(event.x, event.y)
        if label_idx is not None:
            self.labels.pop(label_idx)
            self.selected_label_idx = None
            self.update_display()
            self.update_label_list()
    
    def on_label_selected(self, event):
        """Handle label selection from listbox"""
        selection = self.label_listbox.curselection()
        if selection:
            self.selected_label_idx = selection[0]
            self.update_display()
    
    def delete_selected_label(self):
        """Delete the currently selected label"""
        if self.selected_label_idx is not None and self.selected_label_idx < len(self.labels):
            self.labels.pop(self.selected_label_idx)
            self.selected_label_idx = None
            self.update_display()
            self.update_label_list()
    
    def clear_all_labels(self):
        """Clear all labels after confirmation"""
        if messagebox.askyesno("Clear All", "Are you sure you want to delete all labels?"):
            self.labels = []
            self.selected_label_idx = None
            self.update_display()
            self.update_label_list()
    
    def resize_all_to_16x16(self):
        """Resize all labels to 16x16 pixels"""
        if self.current_image is None:
            messagebox.showwarning("No Image", "Please load an image first.")
            return
        
        if not self.labels:
            messagebox.showinfo("No Labels", "There are no labels to resize.")
            return
        
        # Ask for confirmation
        if not messagebox.askyesno("Resize All Labels", 
                                   f"This will resize all {len(self.labels)} labels to 16x16 pixels.\n"
                                   "The center positions will remain the same.\n\n"
                                   "Continue?"):
            return
        
        # Get image dimensions
        img_width, img_height = self.current_image.size
        fixed_pixel_size = 16
        
        # Calculate normalized size for 16x16 pixels
        new_w = fixed_pixel_size / img_width
        new_h = fixed_pixel_size / img_height
        
        # Update all labels
        for label in self.labels:
            # Keep class_id, center_x, center_y the same
            # Only update width and height
            label[3] = new_w
            label[4] = new_h
        
        # Update display
        self.update_display()
        self.update_label_list()
        
        messagebox.showinfo("Resize Complete", 
                           f"Successfully resized {len(self.labels)} labels to 16x16 pixels.")
    
    def next_image(self):
        """Navigate to next image"""
        if self.image_files and self.current_image_index < len(self.image_files) - 1:
            self.current_image_index += 1
            self.load_current_image()
    
    def prev_image(self):
        """Navigate to previous image"""
        if self.image_files and self.current_image_index > 0:
            self.current_image_index -= 1
            self.load_current_image()
    


def main():
    """Main entry point"""
    root = tk.Tk()
    app = YOLOLabelEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
